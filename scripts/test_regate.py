"""Unit tests for jev-regate against the local stub server from test_jev (never the real OpenRouter API).

Run with: python3 -B test_regate.py   (from this directory)
"""
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
from test_jev import StubHandler, StubServer  # noqa: E402

REGATE = os.path.join(HERE, "jev-regate")
JEV = os.path.join(HERE, "jev")


def load_regate():
    loader = importlib.machinery.SourceFileLoader("jev_regate_under_test", REGATE)
    spec = importlib.util.spec_from_loader("jev_regate_under_test", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def registry(gated_text="Supported?", golden="Supported?", extra=()):
    """A minimal registry: one gated noul (the golden rows' question) plus any extra (ungated) entries."""
    qs = [{"id": "claim_support", "type": "noul", "text": gated_text, "criteria": None, "state_format": "Claim: …",
           "thresholds": {"clear_bar": 1.1, "split": 0.5, "unclear_band": None}, "measured": True,
           "regate": {"golden_question": golden}, "measured_on": "test", "used_by": "test"}]
    return {"questions": qs + list(extra)}


UNGATED = {"id": "keep_reject", "type": "noul", "text": "Is this flag real?", "criteria": None,
           "thresholds": {}, "measured": False, "measured_on": "test", "used_by": "test"}


class RegateTest(unittest.TestCase):
    def setUp(self):
        self.server = StubServer(("127.0.0.1", 0), StubHandler)
        self.server.behavior = {"requests": [], "resolved_model": "typesafe/jev-test-1"}
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.tmp = tempfile.mkdtemp(prefix="regate_")
        self.gold = os.path.join(self.tmp, "golden")
        os.makedirs(self.gold)
        self.cache = os.path.join(self.tmp, "regate.json")
        self.registry = os.path.join(self.tmp, "jev-registry.json")
        self.write_registry(registry())

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def write_registry(self, reg):
        with open(self.registry, "w") as fh:
            json.dump(reg, fh)

    def write_gold(self, n=10, flip=False, question="Supported?"):
        # the stub answers a noul with the P=<x> it finds in the row's state
        items, truth = [], []
        for i in range(n):
            yes = i % 2 == 0
            p = 0.99 if (yes != flip) else 0.01
            items.append({"id": f"g{i}", "state": f"Claim {i}. P={p}", "question": question})
            truth.append({"id": f"g{i}", "label": "yes" if yes else "no"})
        for name, rows in (("regate_items.jsonl", items), ("regate_truth.jsonl", truth)):
            with open(os.path.join(self.gold, name), "w") as fh:
                fh.write("".join(json.dumps(r) + "\n" for r in rows))

    def env(self):
        env = dict(os.environ)
        for var in ("JEV_MODEL", "JEV_EXPECT_BUILD"):
            env.pop(var, None)
        env.update({"JEV_BASE_URL": f"http://127.0.0.1:{self.server.server_address[1]}",
                    "JEV_USAGE_LOG": os.path.join(self.tmp, "usage.jsonl"),
                    "JEV_JUDGMENTS_LOG": os.path.join(self.tmp, "judgments.jsonl"), "JEV_NO_KEYCHAIN": "1",
                    "OPENROUTER_API_KEY": "test-key", "JEV_REGATE_GOLD": self.gold, "JEV_REGATE_CACHE": self.cache,
                    "JEV_REGISTRY": self.registry})
        return env

    def run_regate(self, *args):
        r = subprocess.run([sys.executable, REGATE, *args], capture_output=True, text=True, env=self.env(), timeout=60)
        return r, json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip().startswith("{") else {}

    def module(self):
        """jev-regate as a module, reading THIS test's golden set, registry and cache (as the CLI would, D9)."""
        old = {k: os.environ.get(k) for k in ("JEV_REGATE_GOLD", "JEV_REGATE_CACHE", "JEV_REGISTRY")}
        os.environ.update({"JEV_REGATE_GOLD": self.gold, "JEV_REGATE_CACHE": self.cache, "JEV_REGISTRY": self.registry})
        try:
            return load_regate()
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_pass_is_cached_per_build(self):
        self.write_gold()
        r, d = self.run_regate()
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertTrue(d["pass"])
        self.assertEqual((d["clear"], d["clear_wrong"], d["build"]), (10, 0, "typesafe/jev-test-1"))
        self.assertEqual((d["gated"], d["reworded"]), (["claim_support"], []))
        n_before = len(self.server.behavior["requests"])
        r2, d2 = self.run_regate()
        self.assertEqual(r2.returncode, 0)
        self.assertTrue(d2.get("cached"))
        self.assertEqual(len(self.server.behavior["requests"]), n_before + 1)  # only the ping

    def test_fail_exits_5_and_is_not_a_cached_pass(self):
        self.write_gold(flip=True)
        r, d = self.run_regate()
        self.assertEqual(r.returncode, 5, r.stdout)
        self.assertFalse(d["pass"])
        self.assertEqual(d["clear_wrong"], 10)
        r2, d2 = self.run_regate()
        self.assertEqual(r2.returncode, 5)
        self.assertFalse(d2.get("cached", False))

    def test_new_build_reruns(self):
        self.write_gold()
        self.run_regate()
        self.server.behavior["resolved_model"] = "typesafe/jev-test-2"
        r, d = self.run_regate()
        self.assertEqual(r.returncode, 0)
        self.assertFalse(d.get("cached", False))
        self.assertEqual(d["build"], "typesafe/jev-test-2")

    def test_unnamed_build_is_could_not_run_and_never_cached(self):
        self.write_gold()
        self.server.behavior["resolved_model"] = None   # stub echoes the requested alias only
        r, d = self.run_regate()
        self.assertEqual(r.returncode, 4, r.stdout)
        self.assertFalse(os.path.exists(self.cache))

    def test_missing_golden_exits_2(self):
        r, _ = self.run_regate()
        self.assertEqual(r.returncode, 2)

    # --- D14: --help, the registry's own text, and a fingerprint that moves with it --------------------------------

    def test_help_prints_and_calls_nothing(self):
        self.write_gold()
        for flag in ("--help", "-h"):
            r = subprocess.run([sys.executable, REGATE, flag], capture_output=True, text=True, env=self.env(), timeout=30)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("jev-regate", r.stdout)
            self.assertIn("2 of the", r.stdout)      # it says what it covers
        r = subprocess.run([sys.executable, REGATE, "--forse"], capture_output=True, text=True, env=self.env(), timeout=30)
        self.assertEqual(r.returncode, 2)
        self.assertIn("unknown argument", r.stderr)
        self.assertEqual(self.server.behavior["requests"], [])   # not even a ping
        self.assertFalse(os.path.exists(self.cache))

    def test_asks_the_registry_text_not_the_golden_copy(self):
        self.write_gold()
        self.write_registry(registry(gated_text="Does the source sentence support the claim?"))
        r, d = self.run_regate()
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        asked = {req["questions"]["q"]["instructions"] for req in self.server.behavior["requests"]
                 if "q" in (req.get("questions") or {}) and req.get("state") != "ping"}
        self.assertEqual(asked, {"Does the source sentence support the claim?"})
        self.assertEqual(d["reworded"], ["claim_support"])

    def test_rewording_the_registry_question_reruns_on_the_same_build(self):
        self.write_gold()
        self.run_regate()
        self.write_registry(registry(gated_text="Is the claim supported?"))
        n_before = len(self.server.behavior["requests"])
        r, d = self.run_regate()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertFalse(d.get("cached", False))                   # same build, new registry text: the gate re-runs
        self.assertGreater(len(self.server.behavior["requests"]), n_before + 1)
        r, d = self.run_regate()
        self.assertTrue(d.get("cached"))                            # and that result is cached under its own key
        self.write_registry(registry(gated_text="Is the claim supported?", extra=[UNGATED]))
        r, d = self.run_regate()
        self.assertTrue(d.get("cached"))                            # an ungated question changes nothing it measures

    def test_golden_and_registry_out_of_step_exits_2_before_any_call(self):
        self.write_gold(question="A question nobody registered?")
        r, d = self.run_regate()
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("no registry entry", d["error"])
        self.write_gold()
        self.write_registry({"questions": [UNGATED]})               # nothing gated at all
        r, d = self.run_regate()
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertEqual(self.server.behavior["requests"], [])

    def test_an_old_build_only_cache_entry_is_not_a_pass(self):
        self.write_gold()
        with open(self.cache, "w") as fh:
            json.dump({"typesafe/jev-test-1": {"pass": True, "build": "typesafe/jev-test-1"}}, fh)
        r, d = self.run_regate()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertFalse(d.get("cached", False))
        with open(self.cache) as fh:
            cache = json.load(fh)
        self.assertIn("typesafe/jev-test-1", cache)                 # the old entry is kept, never deleted
        self.assertTrue(any(k.startswith("typesafe/jev-test-1|") for k in cache))
        self.assertEqual(d["packing"], 2)                           # read from the CLI's `jev ping`

    def test_fingerprint_moves_with_packing_questions_files_bar_and_gated_text(self):
        regate = load_regate()
        self.write_gold()
        with open(os.path.join(self.gold, "regate_items.jsonl")) as fh:
            items = [json.loads(line) for line in fh if line.strip()]
        base = regate.fingerprint(self.gold, items, 2)
        self.assertEqual(base, regate.fingerprint(self.gold, items, 2))              # deterministic
        self.assertNotEqual(base, regate.fingerprint(self.gold, items, 3))           # packing
        self.assertNotEqual(base, regate.fingerprint(self.gold, items, 2, {"true": "T", "false": "F"}))   # criteria
        two = [dict(it, question="Q2?") if i == 0 else it for i, it in enumerate(items)]
        self.assertNotEqual(base, regate.fingerprint(self.gold, two, 2))             # question texts and order
        gated = registry()["questions"]
        with_gated = regate.fingerprint(self.gold, items, 2, gated=gated)
        self.assertNotEqual(base, with_gated)                                         # D14: the gated registry text
        reworded = [dict(gated[0], text="Supported, strictly?")]
        self.assertNotEqual(with_gated, regate.fingerprint(self.gold, items, 2, gated=reworded))
        recriteria = [dict(gated[0], criteria={"true": "T", "false": "F"})]
        self.assertNotEqual(with_gated, regate.fingerprint(self.gold, items, 2, gated=recriteria))
        with open(os.path.join(self.gold, "regate_truth.jsonl"), "a") as fh:
            fh.write(json.dumps({"id": "extra", "label": "no"}) + "\n")
        self.assertNotEqual(base, regate.fingerprint(self.gold, items, 2))           # the golden files
        before_bar = regate.fingerprint(self.gold, items, 2)
        regate.MAX_CLEAR_WRONG += 1
        self.assertNotEqual(before_bar, regate.fingerprint(self.gold, items, 2))     # the pass bar

    # --- D9: the CLI's per-reply build check reads what this gate cached ------------------------------------------

    def test_passing_builds_are_the_current_fingerprints_passes(self):
        self.write_gold()
        mod = self.module()
        fp = mod.current_fingerprint(2)
        with open(self.cache, "w") as fh:
            json.dump({f"typesafe/a|{fp}": {"pass": True}, f"typesafe/b|{fp}": {"pass": False},
                       "typesafe/c|0ldf1ngerpr1nt": {"pass": True}, "typesafe/d": {"pass": True}}, fh)
        self.assertEqual(mod.passing_builds(2), {"typesafe/a"})
        self.assertEqual(mod.passing_builds(3), set())                # another packing is another fingerprint
        os.unlink(self.cache)
        self.assertEqual(mod.passing_builds(2), set())                # no cache: nothing expected

    def test_cli_needs_no_export_after_a_pass_and_flags_a_reword(self):
        self.write_gold()
        r, d = self.run_regate()
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        yes = [sys.executable, JEV, "yes", "q?", "-s", "Claim 1. P=0.9"]
        out = json.loads(subprocess.run(yes, capture_output=True, text=True, env=self.env(), timeout=30).stdout)
        self.assertNotIn("build_mismatch", out)                       # the gated build, no JEV_EXPECT_BUILD needed
        self.server.behavior["resolved_model"] = "typesafe/jev-test-2"
        out = json.loads(subprocess.run(yes, capture_output=True, text=True, env=self.env(), timeout=30).stdout)
        self.assertTrue(out["build_mismatch"])                        # a build the gate never passed
        self.server.behavior["resolved_model"] = "typesafe/jev-test-1"
        self.write_registry(registry(gated_text="Is the claim supported?"))
        out = json.loads(subprocess.run(yes, capture_output=True, text=True, env=self.env(), timeout=30).stdout)
        self.assertTrue(out["build_mismatch"])                        # reworded, not re-gated: nothing stands on it


if __name__ == "__main__":
    unittest.main(verbosity=1)
