"""Unit tests for jev, run against a local stub HTTP server (never the real OpenRouter API).

Run with: python3 -m unittest test_jev -v   (from this directory)

Stub controls. Server-wide: behavior["status"], ["status_sequence"], ["error_body"], ["noul_p"], ["resolved_model"],
["drop_answers"] (question names left out of the reply), ["retry_after"] (a Retry-After header on every non-200).
A noul question's p comes from "P=<x>" in its instructions.
Per request, when the state is a JSON object (verify rows pass extra fields through into state): "stub_status"
(HTTP status), "stub_delay" (seconds), "stub_choice" / "stub_conf" / "stub_no_probs" / "stub_label" (the choice
answer), "stub_tag" (recorded in behavior["completed"] in the order replies finish).
"""
import email.utils
import hashlib
import http.server
import importlib.machinery
import importlib.util
import json
import os
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.realpath(__file__))
JEV_PATH = os.path.join(HERE, "jev")
REGATE_PATH = os.path.join(HERE, "jev-regate")
CORP_KIT_PATH = os.path.join(os.path.dirname(HERE), "templates", "corp-kit.js")
# The builds the stub answers as: its default echo of the requested alias, and the production build some tests use.
STUB_BUILDS = ("jev-latest", "typesafe/jev-1.13-20260917")


def load_jev_module():
    """The CLI as a module (as jev-browse's jev_client.py loads it), for its pure helpers; main() never runs."""
    loader = importlib.machinery.SourceFileLoader("jev_cli_under_test", JEV_PATH)
    spec = importlib.util.spec_from_loader("jev_cli_under_test", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def load_regate_module():
    loader = importlib.machinery.SourceFileLoader("jev_regate_under_test_from_jev", REGATE_PATH)
    spec = importlib.util.spec_from_loader("jev_regate_under_test_from_jev", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def seed_regate_cache(path, builds=STUB_BUILDS, registry_path=None):
    """A re-gate cache holding a PASS for `builds` under the CURRENT fingerprint (the real golden set, the given or
    real registry) -- what a passed preflight leaves behind. D9: with JEV_EXPECT_BUILD unset the CLI accepts exactly
    these builds, so every stub test runs against its own cache, never the owner's ~/.cache/jev/regate.json."""
    fp = load_regate_module().current_fingerprint(2, registry_path=registry_path)
    with open(path, "w") as fh:
        json.dump({f"{b}|{fp}": {"pass": True, "build": b, "fingerprint": fp} for b in builds}, fh)
    return fp


class StubHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            req = json.loads(raw.decode("utf-8")) if raw else {}
        except ValueError:
            req = {}
        behavior = self.server.behavior
        behavior["requests"].append(req)
        ctl = req.get("state") if isinstance(req.get("state"), dict) else {}
        state_text = req.get("state") if isinstance(req.get("state"), str) else json.dumps(req.get("state"))
        if ctl.get("stub_delay"):
            time.sleep(float(ctl["stub_delay"]))
        delays = behavior.get("delay_sequence")
        if delays:
            time.sleep(float(delays.pop(0)))

        seq = behavior.get("status_sequence")
        if seq:
            status = seq.pop(0)
        else:
            status = behavior.get("status", 200)
        status = ctl.get("stub_status", status)

        if status != 200:
            body_obj = behavior.get("error_body") or {"error": {"message": "stub error", "code": status}}
            body = json.dumps(body_obj).encode("utf-8")
            self.send_response(status)
            if behavior.get("retry_after") is not None:
                self.send_header("Retry-After", str(behavior["retry_after"]))
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        answers = {}
        for name, q in (req.get("questions") or {}).items():
            if name in behavior.get("drop_answers", ()):
                continue
            qtype = q.get("type")
            instr = q.get("instructions", "") or ""
            if qtype == "noul":
                # P=<x> in the question (gate checks) or, under row-as-state packing, in the row's state
                m = re.search(r"P=([0-9]+(?:\.[0-9]+)?)", instr) or re.search(r"P=([0-9]+(?:\.[0-9]+)?)", state_text or "")
                p = float(m.group(1)) if m else behavior.get("noul_p", 0.7)
                answers[name] = {"type": "noul", "noul": p}
            elif qtype == "choice" and ("stub_choice" in ctl or "stub_label" in ctl):
                keys = list((q.get("criteria") or {}).keys())
                choice = ctl.get("stub_label") or ctl["stub_choice"]
                ans = {"type": "choice", "choice": choice}
                if "stub_conf" in ctl:
                    ans["confidence"] = ctl["stub_conf"]
                if not ctl.get("stub_no_probs"):
                    top = ctl.get("stub_conf", 0.9)
                    ans["probabilities"] = {k: (top if k == choice else (1.0 - top) / max(len(keys) - 1, 1))
                                            for k in keys}
                answers[name] = ans
            elif qtype == "choice" and behavior.get("choice_probs"):
                probs = dict(behavior["choice_probs"])
                choice = max(probs, key=probs.get)
                answers[name] = {"type": "choice", "choice": choice, "confidence": 0.5, "probabilities": probs}
            elif qtype == "choice":
                crit = q.get("criteria") or {}
                keys = list(crit.keys())
                choice = keys[0] if keys else "x"
                probs = {k: (1.0 if k == choice else 0.0) for k in keys}
                answers[name] = {"type": "choice", "choice": choice, "confidence": 0.9,
                                  "probabilities": probs}
            elif qtype == "score":
                levels = q.get("criteria") or []
                idx = min(1, len(levels) - 1) if levels else 0
                probs = {str(i): (1.0 if i == idx else 0.0) for i in range(len(levels))}
                answers[name] = {"type": "score", "score": float(idx),
                                  "legend": {str(i): lvl for i, lvl in enumerate(levels)},
                                  "probabilities": probs, "confidence": 0.5}
        body_obj = {
            "model": behavior.get("resolved_model") or req.get("model", "jev-latest"),
            "answers": answers,
            "usage": {"input_tokens": 100, "output_tokens": 10, "cost": 0.00001},
            "id": "stub-1", "provider": "stub",
        }
        body = json.dumps(body_obj).encode("utf-8")
        if behavior.get("raw_200") is not None:
            body = behavior["raw_200"].encode("utf-8")
        if "stub_tag" in ctl:
            behavior.setdefault("completed", []).append(ctl["stub_tag"])
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class StubServer(http.server.HTTPServer):
    allow_reuse_address = True


class ThreadingStubServer(socketserver.ThreadingMixIn, StubServer):
    daemon_threads = True   # concurrent replies, so a slow early request can finish after a fast later one


class StubCase(unittest.TestCase):
    """Stub server + helpers; holds no tests itself."""
    server_cls = StubServer

    def setUp(self):
        self.server = self.server_cls(("127.0.0.1", 0), StubHandler)
        self.server.behavior = {"requests": []}
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.usage_log = tempfile.NamedTemporaryFile(prefix="jev_usage_", suffix=".jsonl", delete=False)
        self.usage_log.close()
        os.unlink(self.usage_log.name)  # let jev create it fresh via log_usage's makedirs/append
        self.regate_cache = self.usage_log.name + ".regate.json"
        seed_regate_cache(self.regate_cache)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        for path in (self.usage_log.name, self.usage_log.name + ".judgments", self.regate_cache):
            if os.path.exists(path):
                os.unlink(path)

    def log_lines(self, which="usage"):
        path = self.usage_log.name + (".judgments" if which == "judgments" else "")
        if not os.path.exists(path):
            return []
        with open(path) as fh:
            return [json.loads(l) for l in fh if l.strip()]

    def base_env(self, no_key=False, extra=None):
        env = dict(os.environ)
        env["JEV_BASE_URL"] = f"http://127.0.0.1:{self.port}"
        env["JEV_USAGE_LOG"] = self.usage_log.name
        env["JEV_JUDGMENTS_LOG"] = self.usage_log.name + ".judgments"   # never the owner's real judgments log
        env["JEV_REGATE_CACHE"] = self.regate_cache                        # never the owner's real re-gate cache
        for var in ("CLAUDE_CODE_SESSION_ID", "JEV_EXPECT_BUILD", "JEV_REGISTRY", "JEV_REGATE_GOLD"):
            env.pop(var, None)   # tests that need one set it explicitly
        if no_key:
            env.pop("OPENROUTER_API_KEY", None)
            env["JEV_NO_KEYCHAIN"] = "1"
        else:
            env["OPENROUTER_API_KEY"] = "test-key-not-real"
        if extra:
            env.update(extra)
        return env

    def run_jev(self, args, env=None, input_text=None, timeout=30):
        if env is None:
            env = self.base_env()
        return subprocess.run(
            [sys.executable, JEV_PATH] + args,
            input=input_text, capture_output=True, text=True, env=env, timeout=timeout,
        )

    def write_tmp(self, name, text):
        """A new file under a per-test temp dir (removed after the test); the name's extension matters to -f."""
        if not hasattr(self, "_tmpdir"):
            self._tmpdir = tempfile.TemporaryDirectory(prefix="jev_test_")
            self.addCleanup(self._tmpdir.cleanup)
        self._tmp_n = getattr(self, "_tmp_n", 0) + 1
        path = os.path.join(self._tmpdir.name, f"{self._tmp_n}-{name}")
        with open(path, "w") as fh:
            fh.write(text)
        return path

    def sent(self, i=0):
        return self.server.behavior["requests"][i]

    def jsonl(self, stdout):
        return [json.loads(l) for l in stdout.strip().splitlines()]


class JevTestCase(StubCase):

    def test_retry_then_succeed_on_429(self):
        self.server.behavior["status_sequence"] = [429]
        r = self.run_jev(["yes", "is this true?", "-s", "some state"])
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertIn("p_yes", out)
        self.assertEqual(len(self.server.behavior["requests"]), 2)  # one 429, one success

    def test_persistent_503_exits_4(self):
        self.server.behavior["status"] = 503
        r = self.run_jev(["yes", "is this true?", "-s", "some state", "--deadline", "2"])
        self.assertEqual(r.returncode, 4, r.stderr)
        self.assertIn("UNAVAILABLE", r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out.get("ok"), False)
        self.assertEqual(out.get("error"), "unavailable")

    def test_422_exits_2(self):
        self.server.behavior["status"] = 422
        self.server.behavior["error_body"] = {"error": {"message": "state_too_long", "code": 422}}
        r = self.run_jev(["yes", "is this true?", "-s", "some state"])
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("state_too_long", r.stderr)
        self.assertEqual(r.stdout.strip(), "")

    def test_missing_key_exits_3(self):
        env = self.base_env(no_key=True)
        r = self.run_jev(["yes", "is this true?", "-s", "some state"], env=env)
        self.assertEqual(r.returncode, 3, r.stderr)
        self.assertIn("no OpenRouter key", r.stderr)
        self.assertIn("jev setkey", r.stderr)

    def test_filter_summary_line_on_zero_kept(self):
        self.server.behavior["noul_p"] = 0.1
        items = "\n".join(json.dumps({"id": i, "state": f"item {i}"}) for i in range(3))
        r = self.run_jev(["filter", "is it good?", "--threshold", "0.9"], input_text=items)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = [json.loads(l) for l in r.stdout.strip().splitlines()]
        self.assertEqual(len(lines), 4)  # 3 rows + 1 summary
        for row in lines[:3]:
            self.assertFalse(row["keep"])
        summary = lines[-1]
        self.assertTrue(summary["summary"])
        self.assertEqual(summary["kept"], 0)
        self.assertEqual(summary["total"], 3)

    def test_rank_k_ordering(self):
        items = "\n".join(json.dumps({"id": f"row{i}", "state": f"P={p}"}) for i, p in
                          enumerate([0.2, 0.9, 0.5, 0.7, 0.1, 0.6]))
        r = self.run_jev(["rank", "how good?", "-k", "3"], input_text=items)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = [json.loads(l) for l in r.stdout.strip().splitlines()]
        summary = lines[-1]
        self.assertTrue(summary["summary"])
        self.assertEqual(summary["shown"], 3)
        self.assertEqual(summary["total"], 6)
        top3 = lines[:3]
        self.assertEqual([row["id"] for row in top3], ["row1", "row3", "row5"])  # p=.9,.7,.6
        self.assertEqual([row["rank"] for row in top3], [1, 2, 3])

    def test_duplicate_id_rejected_before_http(self):
        items = "\n".join([
            json.dumps({"id": "dup", "state": "a"}),
            json.dumps({"id": "dup", "state": "b"}),
        ])
        r = self.run_jev(["filter", "q?"], input_text=items)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("duplicate item id", r.stderr)
        self.assertEqual(len(self.server.behavior["requests"]), 0)  # no HTTP call made

    def test_usage_log_appended(self):
        r = self.run_jev(["yes", "is this true?", "-s", "some state"])
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(self.usage_log.name) as fh:
            lines = [json.loads(l) for l in fh if l.strip()]
        self.assertEqual(len(lines), 1)
        rec = lines[0]
        for field in ("ts", "cmd", "model", "questions", "status", "ms", "usage"):
            self.assertIn(field, rec)
        self.assertEqual(rec["cmd"], "yes")
        self.assertEqual(rec["status"], 200)
        self.assertEqual(rec["usage"]["input_tokens"], 100)

    def test_default_model_is_jev_latest(self):
        env = self.base_env()
        env.pop("JEV_MODEL", None)
        r = subprocess.run([sys.executable, JEV_PATH, "yes", "is this true?", "-s", "some state"],
                           capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.server.behavior["requests"][0]["model"], "jev-latest")

    def test_usage_log_records_resolved_build(self):
        self.server.behavior["resolved_model"] = "typesafe/jev-9.99-test"
        env = self.base_env()
        env.pop("JEV_MODEL", None)
        r = subprocess.run([sys.executable, JEV_PATH, "yes", "is this true?", "-s", "some state"],
                           capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["model"], "typesafe/jev-9.99-test")
        with open(self.usage_log.name) as fh:
            rec = [json.loads(l) for l in fh if l.strip()][0]
        self.assertEqual(rec["model"], "jev-latest")
        self.assertEqual(rec["resolved"], "typesafe/jev-9.99-test")

    def test_filter_passes_criteria_to_every_item(self):
        rows = "".join(json.dumps({"id": f"x{i}", "state": f"flag {i}"}) + "\n" for i in range(3))
        r = self.run_jev(["filter", "Is this flag a real defect?", "--all", "--true", "T-desc", "--false", "F-desc"],
                         input_text=rows)
        self.assertEqual(r.returncode, 0, r.stderr)
        reqs = self.server.behavior["requests"]
        self.assertEqual(len(reqs), 3)                       # row-as-state: one request per row
        for req in reqs:
            self.assertEqual(req["questions"], {"q": {"type": "noul", "instructions": "Is this flag a real defect?",
                                                      "criteria": {"true": "T-desc", "false": "F-desc"}}})

    def test_filter_without_criteria_sends_none(self):
        rows = json.dumps({"id": "x0", "state": "flag"}) + "\n"
        r = self.run_jev(["filter", "q?", "--all"], input_text=rows)
        self.assertEqual(r.returncode, 0, r.stderr)
        for q in self.server.behavior["requests"][0]["questions"].values():
            self.assertNotIn("criteria", q)

    def test_usage_command_sums_log(self):
        for _ in range(2):
            r = self.run_jev(["yes", "is this true?", "-s", "some state"])
            self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_jev(["usage"])
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out["calls"], 2)
        self.assertEqual(out["questions"], 2)
        self.assertEqual(out["input_tokens"], 200)
        self.assertAlmostEqual(out["cost_usd"], 0.00002, places=8)

    def test_empty_criteria_dropped_for_noul(self):
        r = self.run_jev(["yes", "is this true?", "-s", "some state"])
        self.assertEqual(r.returncode, 0, r.stderr)
        sent = self.server.behavior["requests"][0]
        self.assertNotIn("criteria", sent["questions"]["q"])

    def test_pick_bare_options(self):
        r = self.run_jev(["pick", "which one?", "a", "b", "c", "-s", "state text"])
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertIn("choice", out)
        self.assertIn("probabilities", out)
        self.assertIn("margin", out)

    def test_ask_bad_json_exits_2_before_http(self):
        r = self.run_jev(["ask", "-"], input_text="{not valid json")
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertEqual(len(self.server.behavior["requests"]), 0)

    def test_usage_session_filter_and_scope(self):
        # S1-18: the round's Jev $ is machine-wide unless filtered; the output says which
        now = datetime.now(timezone.utc).isoformat()
        with open(self.usage_log.name, "w") as fh:
            for session, cost in (("s-a", 0.001), ("s-b", 0.002), (None, 0.004)):
                rec = {"ts": now, "cmd": "yes", "questions": 1, "status": 200, "usage": {"cost": cost}}
                if session:
                    rec["session"] = session
                fh.write(json.dumps(rec) + "\n")
        out = json.loads(self.run_jev(["usage"]).stdout)
        self.assertEqual(out["calls"], 3)
        self.assertTrue(out["scope"].startswith("machine"), out["scope"])
        out = json.loads(self.run_jev(["usage", "--session", "s-b"]).stdout)
        self.assertEqual((out["calls"], out["cost_usd"], out["scope"]), (1, 0.002, "session s-b"))

    def test_usage_since_accepts_offset_format(self):
        r = self.run_jev(["yes", "is this true?", "-s", "some state"])
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_jev(["usage", "--since", "2000-01-01T00:00:00+00:00"])
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out["calls"], 1)

    def test_usage_since_accepts_trailing_z(self):
        # Regression: under system Python 3.9, fromisoformat rejects a trailing "Z"
        # (preflight.sh's RUN_START used to print one; jev now tolerates it too).
        r = self.run_jev(["yes", "is this true?", "-s", "some state"])
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_jev(["usage", "--since", "2000-01-01T00:00:00Z"])
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out["calls"], 1)

    def test_ping_ok(self):
        r = self.run_jev(["ping"])
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertTrue(out["ok"])
        self.assertIn("model", out)
        self.assertIn("ms", out)


# --- named-field state -----------------------------------------------------------------------

class ObjectStateTestCase(StubCase):
    """TypeSafe: prefer named JSON fields. Objects go on the wire as objects; text stays byte-identical."""

    def test_json_file_state_sent_as_object(self):
        path = self.write_tmp("pair.json", json.dumps({"claim": "c", "source": "s"}) + "\n")
        r = self.run_jev(["yes", "Does `source` support `claim`?", "-f", path])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.sent()["state"], {"claim": "c", "source": "s"})

    def test_s_json_object_sent_as_object_plain_text_unchanged(self):
        r = self.run_jev(["yes", "q?", "-s", '{"policy": "p", "request": "r"}'])
        self.assertEqual(r.returncode, 0, r.stderr)
        r2 = self.run_jev(["yes", "q?", "-s", "plain words {not json}"])
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertEqual(self.sent(0)["state"], {"policy": "p", "request": "r"})
        self.assertEqual(self.sent(1)["state"], "plain words {not json}")

    def test_stdin_and_txt_json_text_stay_text(self):
        # Live hooks pipe JSON-looking text through -f - and .txt files and were calibrated on it as text.
        text = '{"command": "rm -rf build", "cwd": "/tmp"}\n'
        r = self.run_jev(["yes", "q?", "-f", "-"], input_text=text)
        self.assertEqual(r.returncode, 0, r.stderr)
        r2 = self.run_jev(["yes", "q?", "-f", self.write_tmp("reply.txt", text)])
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertEqual(self.sent(0)["state"], text)
        self.assertEqual(self.sent(1)["state"], text)

    def test_json_state_flag_forces_object_and_rejects_the_rest(self):
        r = self.run_jev(["pick", "which?", "a", "b", "-f", "-", "--json-state"], input_text='{"x": 1}')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.sent()["state"], {"x": 1})
        for bad in ("[1, 2]", "not json", "{}"):
            r = self.run_jev(["yes", "q?", "-f", "-", "--json-state"], input_text=bad)
            self.assertEqual(r.returncode, 2, bad)
        self.assertEqual(len(self.server.behavior["requests"]), 1)   # no HTTP for any bad one

    def test_empty_object_is_an_empty_state(self):
        r = self.run_jev(["yes", "q?", "-s", "{}"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("empty state", r.stderr)
        self.assertEqual(len(self.server.behavior["requests"]), 0)

    def test_json_file_not_holding_an_object_is_text_with_a_warning(self):
        r = self.run_jev(["yes", "q?", "-f", self.write_tmp("list.json", '["a", "b"]\n')])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.sent()["state"], '["a", "b"]\n')
        self.assertIn("sent as text", r.stderr)

    def test_ask_object_state_passthrough(self):
        qs = {"q": {"type": "noul", "instructions": "ok?"}}
        r = self.run_jev(["ask", "-"], input_text=json.dumps({"state": {"ticket": "t", "policy": "p"}, "questions": qs}))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.sent()["state"], {"ticket": "t", "policy": "p"})
        for bad in ({}, [], 3):
            r = self.run_jev(["ask", "-"], input_text=json.dumps({"state": bad, "questions": qs}))
            self.assertEqual(r.returncode, 2, bad)
        self.assertEqual(len(self.server.behavior["requests"]), 1)

    def test_filter_object_row_is_the_request_state(self):
        rows = [{"id": "x", "state": {"claim": "c", "source": "s"}}, {"id": "y", "state": "plain"}]
        r = self.run_jev(["filter", "q?", "--all"], input_text="".join(json.dumps(x) + "\n" for x in rows))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([row["id"] for row in self.jsonl(r.stdout)[:-1]], ["x", "y"])
        states = sorted((json.dumps(q["state"]) for q in self.server.behavior["requests"]))
        self.assertEqual(states, sorted([json.dumps({"claim": "c", "source": "s"}), json.dumps("plain")]))
        for req in self.server.behavior["requests"]:          # the question is fixed; no placeholder state
            self.assertEqual(req["questions"], {"q": {"type": "noul", "instructions": "q?"}})
        r = self.run_jev(["filter", "q?", "--all"], input_text=json.dumps({"id": "z", "state": {}}) + "\n")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(len(self.server.behavior["requests"]), 2)   # the empty-object row never reached the API


# --- jev verify (OpenRouter: Jev-Verified Cascade) ----------------------------------------

SPEC_INSTRUCTIONS = "Compare `draft` against `sources`. Which one describes it?"
SPEC_TASK_NOUL = "Does `draft` address `task`?"
SPEC_RECEIPT_LABEL = ("Computation receipt for the masked figure (inputs and formula; the result is verified separately "
                      "by code): ")   # decision C, verbatim
SPEC_CRITERIA = {
    "supported": "The draft addresses `task`, and every fact, number, date, name, and policy in it is stated in `sources`.",
    "unsupported": "The draft states at least one fact, number, date, name, or policy that `sources` do not contain or that contradicts them, or it addresses something other than `task`.",
    "declined": "The draft says `sources` do not cover `task` and does not assert facts of its own.",
}


def draft_row(**kw):
    row = {"sources": ["Free workspaces have up to 5 members and 3 projects."],
           "task": "How many people can I add on the free plan?",
           "draft": "The Free plan allows up to 5 members per workspace."}
    row.update(kw)
    return row


class VerifyTestCase(StubCase):

    def test_request_shape_and_single_output(self):
        path = self.write_tmp("draft.json", json.dumps(draft_row(id="d1", audience="customer",
                                                                   stub_choice="supported", stub_conf=0.97)))
        r = self.run_jev(["verify", "-f", path])
        self.assertEqual(r.returncode, 0, r.stderr)
        sent = self.sent()
        # the cookbook's choice, plus D16's independent addresses_task noul in the SAME request
        self.assertEqual(sent["questions"], {"support": {"type": "choice", "instructions": SPEC_INSTRUCTIONS,
                                                         "criteria": SPEC_CRITERIA},
                                             "addresses_task": {"type": "noul", "instructions": SPEC_TASK_NOUL}})
        self.assertEqual(list(sent["questions"]["support"]["criteria"]), ["supported", "unsupported", "declined"])
        self.assertEqual(list(sent["state"])[:3], ["sources", "task", "draft"])
        self.assertEqual(sent["state"]["audience"], "customer")   # extra fields pass through into state
        self.assertNotIn("id", sent["state"])                      # the id is for code, never sent
        out = json.loads(r.stdout)
        self.assertEqual((out["id"], out["choice"], out["route"], out["accept"]), ("d1", "supported", "send", 0.8))
        for field in ("confidence", "probabilities", "margin", "ms", "model", "addresses_task"):
            self.assertIn(field, out)
        self.assertEqual((out["failed_half"], out["computed_masked"]), (None, 0))   # a send names no failed half
        self.assertNotIn("calc_unanchored", out)
        with open(self.usage_log.name) as fh:
            rec = [json.loads(l) for l in fh if l.strip()][0]
        self.assertEqual((rec["cmd"], rec["questions"], rec["status"]), ("verify", 2, 200))

    def test_routes_at_the_edges(self):
        cases = [
            ("a", {"stub_choice": "supported", "stub_conf": 0.95}, "send"),
            ("b", {"stub_choice": "supported", "stub_conf": 0.8}, "send"),          # exactly --accept sends
            ("c", {"stub_choice": "supported", "stub_conf": 0.79}, "escalate"),     # just below
            ("d", {"stub_choice": "unsupported", "stub_conf": 1.0}, "escalate"),
            ("e", {"stub_choice": "declined", "stub_conf": 0.6}, "handoff"),        # at any confidence
            ("f", {"stub_choice": "supported", "stub_no_probs": True}, "escalate"),  # no confidence -> 0
        ]
        rows = "".join(json.dumps(draft_row(id=i, **ctl)) + "\n" for i, ctl, _ in cases)
        r = self.run_jev(["verify", "--all"], input_text=rows)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = self.jsonl(r.stdout)
        self.assertEqual([l["id"] for l in lines[:-1]], [c[0] for c in cases])
        self.assertEqual([l["route"] for l in lines[:-1]], [c[2] for c in cases])
        self.assertEqual((lines[5]["confidence"], lines[5]["probabilities"], lines[5]["margin"]), (0, {}, None))
        self.assertEqual(lines[-1], {"summary": True, "total": 6, "send": 2, "escalate": 3, "handoff": 1,
                                     "errors": 0, "non_en": 0, "accept": 0.8, "escalated": False,
                                     "unknown": 0, "unavailable": 0, "complete": True})

    def test_accept_flag(self):
        path = self.write_tmp("d.json", json.dumps(draft_row(stub_choice="supported", stub_conf=0.75)))
        self.assertEqual(json.loads(self.run_jev(["verify", "-f", path]).stdout)["route"], "escalate")
        self.assertEqual(json.loads(self.run_jev(["verify", "-f", path, "--accept", "0.7"]).stdout)["route"], "send")

    def test_bad_input_exits_2_before_http(self):
        bad_rows = [{k: v for k, v in draft_row().items() if k != "draft"}, draft_row(sources=[]),
                    draft_row(sources="   "), draft_row(sources=5), draft_row(task="")]
        for row in bad_rows:
            r = self.run_jev(["verify", "-f", "-"], input_text=json.dumps(row))
            self.assertEqual(r.returncode, 2, row)
        dup = "".join(json.dumps(draft_row(id="same")) + "\n" for _ in range(2))
        r = self.run_jev(["verify", "--all"], input_text=dup)
        self.assertEqual(r.returncode, 2)
        self.assertIn("duplicate item id", r.stderr)
        r = self.run_jev(["verify", "--all", "-f", self.write_tmp("d.json", json.dumps(draft_row()))],
                         input_text=json.dumps(draft_row(id="x")) + "\n")
        self.assertEqual(r.returncode, 2)
        r = self.run_jev(["verify", "-f", "-", "--accept", "1.5"], input_text=json.dumps(draft_row()))
        self.assertEqual(r.returncode, 2)
        self.assertEqual(len(self.server.behavior["requests"]), 0)

    def test_all_keeps_failed_rows_and_never_sends_them(self):
        rows = [draft_row(id="ok", stub_choice="supported", stub_conf=0.99),
                draft_row(id="bad", stub_status=422),
                draft_row(id="odd", stub_label="maybe"),
                draft_row(id="ok2", stub_choice="declined", stub_conf=0.9)]
        r = self.run_jev(["verify", "--all"], input_text="".join(json.dumps(x) + "\n" for x in rows))
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = self.jsonl(r.stdout)
        self.assertEqual([l["id"] for l in lines[:-1]], ["ok", "bad", "odd", "ok2"])
        self.assertEqual([l["route"] for l in lines[:-1]], ["send", "escalate", "escalate", "handoff"])
        self.assertEqual((lines[1]["error"], lines[2]["error"]), ("bad_call", "bad_answer"))
        self.assertTrue(lines[1]["reason"].startswith("jev_failure: bad call (http 422"), lines[1]["reason"])
        self.assertTrue(lines[2]["reason"].startswith("jev_failure: verify: expected a choice answer"), lines[2]["reason"])
        for l in lines[1:3]:
            self.assertIsNone(l["choice"])
            self.assertEqual(l["status"], "UNKNOWN")
        self.assertEqual(lines[-1]["complete"], False)
        self.assertEqual((lines[-1]["total"], lines[-1]["errors"]), (4, 2))
        self.assertNotIn("stopped", lines[-1])   # a row's own failure never stops the run

    def test_all_unavailable_rows_are_counted_and_the_run_exits_0(self):
        self.server.behavior["status"] = 503
        rows = "".join(json.dumps(draft_row(id=i)) + "\n" for i in ("a", "b", "c"))
        r = self.run_jev(["verify", "--all", "--deadline", "2"], input_text=rows)
        self.assertEqual(r.returncode, 0, r.stderr)                          # bulk: per-row, never the whole run
        lines = self.jsonl(r.stdout)
        self.assertEqual([l["id"] for l in lines[:-1]], ["a", "b", "c"])   # never dropped
        for l in lines[:-1]:
            self.assertEqual((l["route"], l["error"], l["status"], l["keep"]), ("escalate", "unavailable", "UNKNOWN", None))
            self.assertTrue(l["reason"].startswith("jev_failure: unavailable"), l["reason"])
        self.assertEqual((lines[-1]["unavailable"], lines[-1]["complete"]), (3, False))
        self.assertNotIn("stopped", lines[-1])

    def test_single_failure_prints_a_safe_route(self):
        path = self.write_tmp("d.json", json.dumps(draft_row(id="d9")))
        r = self.run_jev(["verify", "-f", path], env=self.base_env(no_key=True))
        self.assertEqual(r.returncode, 3)
        out = json.loads(r.stdout)
        self.assertEqual((out["id"], out["route"], out["choice"], out["error"]), ("d9", "escalate", None, "no_key"))
        self.assertIn("no OpenRouter key", out["reason"])
        path = self.write_tmp("d.json", json.dumps(draft_row(stub_label="maybe")))
        r = self.run_jev(["verify", "-f", path])
        self.assertEqual(r.returncode, 4)             # a malformed answer is Jev-side, not a bad call
        self.assertEqual(json.loads(r.stdout)["route"], "escalate")
        r = self.run_jev(["verify", "-f", path, "--escalated"])
        self.assertEqual((r.returncode, json.loads(r.stdout)["route"]), (4, "handoff"))

    def test_escalated_never_escalates_twice(self):
        cases = [
            ("s", {"stub_choice": "supported", "stub_conf": 0.95}, "send"),
            ("low", {"stub_choice": "supported", "stub_conf": 0.79}, "handoff"),
            ("u", {"stub_choice": "unsupported", "stub_conf": 1.0}, "handoff"),
            ("d", {"stub_choice": "declined", "stub_conf": 0.9}, "handoff"),
            ("x", {"stub_status": 422}, "handoff"),
        ]
        rows = "".join(json.dumps(draft_row(id=i, **ctl)) + "\n" for i, ctl, _ in cases)
        r = self.run_jev(["verify", "--all", "--escalated"], input_text=rows)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = self.jsonl(r.stdout)
        self.assertEqual([l["route"] for l in lines[:-1]], [c[2] for c in cases])
        self.assertEqual((lines[-1]["escalate"], lines[-1]["escalated"]), (0, True))

    # --- D16: computed figures are masked; addresses_task names the failed half ---------------------------------

    def test_computed_figures_are_masked_before_sending(self):
        draft = ("The member used 1,234 [calc: corp/receipts/util.json] units of 10003, 59.3% [calc: corp/receipts/pct"
                 ".json] of the 2,000 authorized, through 09/02/2026 [calc: corp/receipts/end.json]. A stray [calc: x].")
        path = self.write_tmp("d.json", json.dumps(draft_row(id="m1", draft=draft, stub_choice="supported",
                                                             stub_conf=0.95)))
        r = self.run_jev(["verify", "-f", path])
        self.assertEqual(r.returncode, 0, r.stderr)
        sent = self.sent()["state"]["draft"]
        self.assertEqual(sent, "The member used ⟨computed⟩ units of 10003, ⟨computed⟩ of the 2,000 authorized, "
                               "through ⟨computed⟩. A stray .")
        self.assertNotIn("[calc:", json.dumps(self.sent(), ensure_ascii=False))   # no marker ever reaches Jev
        self.assertEqual(self.sent()["state"]["sources"], draft_row()["sources"])   # none of these receipts exists
        out = json.loads(r.stdout)
        self.assertEqual((out["computed_masked"], out["calc_unanchored"]), (3, 1))
        self.assertEqual((out["calc_receipts_read"], len(out["calc_receipts_missing"])), (0, 4))
        jev = load_jev_module()   # the pure rule, directly
        self.assertEqual(jev.mask_computed("no markers here"), ("no markers here", 0, 0))
        self.assertEqual(jev.mask_computed("$1,200.50 [calc: r] and v2 [calc: r]")[1:], (1, 1))
        self.assertEqual(jev.mask_computed("2026-08-19 [calc:r]")[0], "⟨computed⟩")

    # --- decision C: what the computation read rides INSIDE sources, labelled; the figure stays masked ------------

    def receipts_dir(self):
        d = tempfile.mkdtemp(prefix="jev_receipts_")
        self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True))
        os.makedirs(os.path.join(d, "corp", "receipts"))
        return d

    def put_receipt(self, root, rel, text):
        with open(os.path.join(root, rel), "w") as fh:
            fh.write(text)

    def test_receipts_ride_inside_sources_inputs_and_formula_never_the_result(self):
        root = self.receipts_dir()
        self.put_receipt(root, "corp/receipts/util.md",
                         "# 10003 utilization 03/01-08/31\n## inputs\n- claims rows 10003, 03/01/2026-08/31/2026: 126 lines\n"
                         "- authorized: 1,700 units (letter p.1)\n## formula\nsum(units) over the rows\n## result\n1,512\n")
        self.put_receipt(root, "corp/receipts/pct.json",
                         json.dumps({"inputs": {"used": "util.md", "authorized": 1700}, "formula": "used / authorized",
                                     "result": "85.5%"}))
        self.put_receipt(root, "corp/receipts/plain.txt",
                         "\n".join(["source: claims-export.csv", "Total: 1,999"] + [f"row {i}: 10003 x 4 units"
                                                                                    for i in range(45)]) + "\n")
        draft = ("The member used 1,512 [calc: corp/receipts/util.md] units, 85.5% [calc: corp/receipts/pct.json] of the "
                 "1,700 authorized; row 7 of the export shows 1,999 [calc: corp/receipts/plain.txt] and 12 [calc: "
                 "corp/receipts/gone.md] more.")
        path = self.write_tmp("d.json", json.dumps(draft_row(id="c1", draft=draft, stub_choice="supported",
                                                             stub_conf=0.95)))
        r = self.run_jev(["verify", "-f", path, "--calc-root", root])
        self.assertEqual(r.returncode, 0, r.stderr)
        state = self.sent()["state"]
        self.assertEqual(list(state)[:3], ["sources", "task", "draft"])          # (then the stub's control fields)
        self.assertNotIn("computed_from", state)                                 # no separate field: the criteria
        self.assertEqual(self.sent()["questions"]["support"]["criteria"], SPEC_CRITERIA)   # stay the cookbook's, verbatim
        sources = state["sources"]
        self.assertEqual(sources[0], draft_row()["sources"][0])                  # the canon first, untouched
        receipts = sources[1:]
        self.assertEqual(len(receipts), 3)                                       # util, pct, plain; gone.md is missing
        self.assertTrue(all(e.startswith(SPEC_RECEIPT_LABEL) for e in receipts), receipts)
        util, pct, plain = (e[len(SPEC_RECEIPT_LABEL):] for e in receipts)
        self.assertIn("claims rows 10003", util)
        self.assertIn("sum(units)", util)                                        # the formula section too
        self.assertNotIn("## result", util)                                      # never the result section
        self.assertNotIn("1,512", json.dumps(state, ensure_ascii=False))         # the masked figure never reaches Jev
        self.assertEqual(json.loads(pct), {"inputs": {"used": "util.md", "authorized": 1700},
                                           "formula": "used / authorized"})
        lines = plain.splitlines()
        self.assertEqual((len(lines), lines[0]), (39, "source: claims-export.csv"))   # the first 40 lines, minus the
        self.assertNotIn("1,999", plain)                                             # one holding the figure itself
        out = json.loads(r.stdout)
        self.assertEqual((out["computed_masked"], out["calc_receipts_read"], out["calc_receipts_missing"]),
                         (4, 3, ["corp/receipts/gone.md"]))
        self.assertNotIn("computed_from", out)

    def test_receipt_entries_keep_the_sources_shape(self):
        jev = load_jev_module()
        e = [SPEC_RECEIPT_LABEL + "rows"]
        self.assertEqual(jev.sources_with_receipts(["a", "b"], e), ["a", "b", e[0]])
        self.assertEqual(jev.sources_with_receipts("the letter says X", e), ["the letter says X", e[0]])
        self.assertEqual(jev.sources_with_receipts({"letter": "X"}, e), {"letter": "X", "computation receipts": e})
        self.assertEqual(jev.sources_with_receipts({"computation receipts": "mine"}, e),
                         {"computation receipts": "mine", "computation receipts (2)": e})   # never overwrites a key
        self.assertEqual(jev.sources_with_receipts("unchanged", []), "unchanged")
        self.assertEqual(jev.RECEIPT_LABEL, SPEC_RECEIPT_LABEL)

    def test_calc_root_defaults_to_the_working_directory(self):
        root = self.receipts_dir()
        self.put_receipt(root, "corp/receipts/u.md", "## inputs\nclaims rows\n")
        path = self.write_tmp("d.json", json.dumps(draft_row(draft="Used 9 [calc: corp/receipts/u.md] units.",
                                                             stub_choice="supported", stub_conf=0.9)))
        r = subprocess.run([sys.executable, JEV_PATH, "verify", "-f", path], capture_output=True, text=True,
                           env=self.base_env(), cwd=root, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.sent()["state"]["sources"][-1], SPEC_RECEIPT_LABEL + "## inputs\nclaims rows")
        abs_receipt = os.path.join(root, "corp", "receipts", "u.md")      # an absolute path needs no root
        path = self.write_tmp("d.json", json.dumps(draft_row(draft=f"Used 9 [calc: {abs_receipt}] units.",
                                                             stub_choice="supported", stub_conf=0.9)))
        r = self.run_jev(["verify", "-f", path])
        self.assertEqual(json.loads(r.stdout)["calc_receipts_read"], 1, r.stdout)

    def test_failed_half_comes_from_the_addresses_task_noul(self):
        rows = [draft_row(id="send", stub_choice="supported", stub_conf=0.95),
                draft_row(id="ground", stub_choice="unsupported", stub_conf=1.0, note="P=0.9"),
                draft_row(id="task", stub_choice="unsupported", stub_conf=1.0, note="P=0.2"),
                draft_row(id="low", stub_choice="supported", stub_conf=0.6, note="P=0.9"),
                draft_row(id="decl", stub_choice="declined", stub_conf=0.9, note="P=0.2")]
        r = self.run_jev(["verify", "--all"], input_text="".join(json.dumps(x) + "\n" for x in rows))
        self.assertEqual(r.returncode, 0, r.stderr)
        got = {l["id"]: (l["route"], l["failed_half"]) for l in self.jsonl(r.stdout)[:-1]}
        self.assertEqual(got, {"send": ("send", None), "ground": ("escalate", "grounding"),
                               "task": ("escalate", "task"), "low": ("escalate", "grounding"),
                               "decl": ("handoff", None)})
        # the noul never changes a route: a missing addresses_task answer leaves route intact, failed_half unknown
        self.server.behavior["drop_answers"] = ["addresses_task"]
        path = self.write_tmp("d.json", json.dumps(draft_row(stub_choice="unsupported", stub_conf=1.0)))
        out = json.loads(self.run_jev(["verify", "-f", path]).stdout)
        self.assertEqual((out["route"], out["addresses_task"], out["failed_half"]), ("escalate", None, None))
        self.server.behavior["drop_answers"] = []
        path = self.write_tmp("d.json", json.dumps(draft_row(stub_choice="unsupported", stub_conf=1.0)))
        r = self.run_jev(["verify", "-f", path, "--escalated"])   # a double failure keeps its failed half for the audit
        out = json.loads(r.stdout)
        self.assertEqual((out["route"], out["failed_half"]), ("handoff", "grounding"))


class VerifyLanguageTestCase(StubCase):
    """OM-08: a unit not written in English is never sent to Jev -- it escalates (the claim audit reads it)."""

    SPANISH = ("La familia informa que el niño asistió a todas las sesiones y que las horas fueron aprobadas por el "
               "plan para este periodo.")

    def test_a_non_english_unit_escalates_with_no_call(self):
        path = self.write_tmp("es.json", json.dumps(draft_row(id="es", draft=self.SPANISH)))
        r = self.run_jev(["verify", "-f", path])
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual((out["route"], out["status"], out["lang_hint"], out["choice"]),
                         ("escalate", "NOT_ASKED", "non_en", None))
        self.assertNotIn("build_mismatch", out)                  # nothing was asked, so there is no build to check
        r = self.run_jev(["verify", "-f", path, "--escalated"])
        self.assertEqual(json.loads(r.stdout)["route"], "handoff")   # the re-draft is still Spanish: double failure
        r = self.run_jev(["verify", "-f", path], env=self.base_env(no_key=True))
        self.assertEqual((r.returncode, json.loads(r.stdout)["route"]), (0, "escalate"))   # no key needed to skip
        self.assertEqual(len(self.server.behavior["requests"]), 0)

    def test_all_sends_only_the_english_rows(self):
        rows = [draft_row(id="en", stub_choice="supported", stub_conf=0.95),
                draft_row(id="es", draft=self.SPANISH),
                draft_row(id="src", sources=[self.SPANISH])]
        r = self.run_jev(["verify", "--all"], input_text="".join(json.dumps(x) + "\n" for x in rows))
        self.assertEqual(r.returncode, 0, r.stderr)
        out = {x["id"]: x for x in self.jsonl(r.stdout) if "id" in x}
        self.assertEqual({k: (v["route"], v["status"]) for k, v in out.items()},
                         {"en": ("send", "JUDGED"), "es": ("escalate", "NOT_ASKED"), "src": ("escalate", "NOT_ASKED")})
        self.assertEqual(len(self.server.behavior["requests"]), 1)
        summary = [x for x in self.jsonl(r.stdout) if x.get("summary")][-1]
        self.assertEqual((summary["non_en"], summary["escalate"]), (2, 2))    # F5: the kit routes these two to 'audit' (n/a)


class VerifyConcurrencyTestCase(StubCase):
    server_cls = ThreadingStubServer

    def test_all_prints_input_order_when_replies_finish_out_of_order(self):
        ids = ["d0", "d1", "d2", "d3", "d4"]
        rows = "".join(json.dumps(draft_row(id=i, stub_tag=i, stub_delay=0.2 * (4 - n), stub_choice="supported",
                                            stub_conf=0.9)) + "\n" for n, i in enumerate(ids))
        r = self.run_jev(["verify", "--all"], input_text=rows)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([l["id"] for l in self.jsonl(r.stdout)[:-1]], ids)
        # the replies really did finish out of order, so the order assertion above is not vacuous
        self.assertNotEqual(self.server.behavior["completed"], ids)


# --- jev gate (OpenRouter: Gate Agent Tool Calls with Jev) ----------------------------------

def gate_req(**checks):
    return {"state": {"policy": "Late delivery: refund the shipping fee if the order arrived more than 5 days late.",
                      "proposed_action": {"tool": "refund", "order_id": "ORD-1234", "amount_cents": 1200},
                      "context": "Kettle ORD-1234 was promised for Sept 2 and arrived Sept 11; refund the shipping."},
            "checks": checks, "action": "refund ORD-1234 1200"}


class GateTestCase(StubCase):

    def gate(self, req, *flags):
        return self.run_jev(["gate", "-f", self.write_tmp("action.json", json.dumps(req)), *flags])

    def test_one_request_every_check_over_one_state(self):
        req = gate_req(customer_asked="The customer in `context` asks for a refund. P=0.98",
                       right_order="`proposed_action.order_id` is the order `context` is about. P=0.99",
                       policy_covers="`policy` covers `proposed_action`. P=0.96")
        r = self.gate(req)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.server.behavior["requests"]), 1)
        self.assertEqual(self.sent()["state"], req["state"])
        self.assertEqual(self.sent()["questions"], {n: {"type": "noul", "instructions": p} for n, p in req["checks"].items()})
        out = json.loads(r.stdout)
        self.assertEqual((out["decision"], out["reason"], out["action"]), ("approve", "every check clear", "refund ORD-1234 1200"))
        self.assertEqual(out["checks"], {"customer_asked": 0.98, "right_order": 0.99, "policy_covers": 0.96})
        with open(self.usage_log.name) as fh:
            rec = [json.loads(l) for l in fh if l.strip()][0]
        self.assertEqual((rec["cmd"], rec["questions"]), ("gate", 3))

    def test_decisions_at_the_threshold_edges(self):
        cases = [
            ({"a": "P=0.9", "b": "P=0.95"}, "approve", [], [], "every check clear"),   # exactly --approve-at
            ({"a": "P=0.89", "b": "P=0.95"}, "review", [], ["a"], "unclear a=0.89"),    # just below it
            ({"a": "P=0.1", "b": "P=0.99"}, "block", ["a"], [], "failed a=0.10"),       # exactly --block-at
            ({"a": "P=0.11", "b": "P=0.99"}, "review", [], ["a"], "unclear a=0.11"),    # just above it
            ({"a": "P=0.05", "b": "P=0.5"}, "block", ["a"], ["b"], "failed a=0.05"),    # block beats unclear
        ]
        for checks, decision, failed, unclear, reason in cases:
            with self.subTest(checks=checks):
                r = self.gate(gate_req(**{k: f"Check {k} holds. {v}" for k, v in checks.items()}))
                self.assertEqual(r.returncode, 0, r.stderr)
                out = json.loads(r.stdout)
                self.assertEqual((out["decision"], out["failed"], out["unclear"], out["reason"]),
                                 (decision, failed, unclear, reason))

    def test_custom_thresholds(self):
        r = self.gate(gate_req(a="P=0.85", b="P=0.82"), "--approve-at", "0.8", "--block-at", "0.2")
        self.assertEqual(json.loads(r.stdout)["decision"], "approve")
        out = json.loads(self.gate(gate_req(a="P=0.2", b="P=0.99"), "--approve-at", "0.8", "--block-at", "0.2").stdout)
        self.assertEqual((out["decision"], out["approve_at"], out["block_at"]), ("block", 0.8, 0.2))

    def test_broken_answers_review_exit_4(self):
        self.server.behavior["drop_answers"] = ["b"]
        r = self.gate(gate_req(a="P=0.99", b="P=0.99"))
        self.assertEqual(r.returncode, 4)
        out = json.loads(r.stdout)
        self.assertEqual(out["decision"], "review")
        self.assertEqual(out["reason"], "jev_failure: gate: no valid answer for check(s) b")
        self.assertEqual(out["checks"], {"a": 0.99})   # what Jev did answer, for the audit record
        self.server.behavior["drop_answers"] = []
        r = self.gate(gate_req(a="P=0.99", b="P=1.5"))   # a p outside [0, 1]
        self.assertEqual((r.returncode, json.loads(r.stdout)["decision"]), (4, "review"))

    def test_every_jev_failure_is_review_never_approve(self):
        cases = [  # (server behaviour, exit, reason prefix)
            ({"status": 503}, 4, "jev_failure: unavailable"),
            ({"status": 402, "error_body": {"error": {"code": 402, "message": "Insufficient credits",
                                                      "metadata": {"limit_source": "openrouter_credits"}}}},
             3, "jev_failure: OpenRouter credits exhausted"),
            ({"status": 401}, 3, "jev_failure: auth"),
            ({"status": 422}, 2, "jev_failure: bad call"),
        ]
        for behavior, code, prefix in cases:
            with self.subTest(behavior=behavior):
                self.server.behavior = {"requests": [], **behavior}
                r = self.gate(gate_req(a="P=0.99", b="P=0.99"), "--deadline", "2")
                self.assertEqual(r.returncode, code, r.stderr)
                out = json.loads(r.stdout)
                self.assertEqual((out["decision"], out["action"]), ("review", "refund ORD-1234 1200"))
                self.assertTrue(out["reason"].startswith(prefix), out["reason"])
        r = self.run_jev(["gate", "-f", self.write_tmp("a.json", json.dumps(gate_req(a="P=0.99")))],
                         env=self.base_env(no_key=True))
        self.assertEqual((r.returncode, json.loads(r.stdout)["decision"]), (3, "review"))
        r = self.gate({"state": {"a": 1}, "checks": {}})   # only a malformed action.json: exit 2, nothing printed
        self.assertEqual((r.returncode, r.stdout.strip()), (2, ""))

    def test_bad_input_exits_2_before_http(self):
        for req in ({"state": {"a": 1}, "checks": {}}, {"state": {"a": 1}, "checks": {"x": ""}},
                    {"state": {"a": 1}, "checks": {"x": 3}}, {"state": {}, "checks": {"x": "ok?"}},
                    {"checks": {"x": "ok?"}}):
            self.assertEqual(self.gate(req).returncode, 2, req)
        self.assertEqual(self.gate(gate_req(a="P=0.9"), "--block-at", "0.9", "--approve-at", "0.9").returncode, 2)
        self.assertEqual(self.gate(gate_req(a="P=0.9"), "--approve-at", "1.2").returncode, 2)
        self.assertEqual(len(self.server.behavior["requests"]), 0)

    # --- D2: §GATE's three checks are registry entries (go_act) ----------------------------------------------------

    def go_req(self, **extra):
        """A go_act request whose files are NOT on disk: fine for the exit-2 paths, blocked by the recomputed checks."""
        state = {"go": {"reply": "GO 1,3", "row": {"id": 3, "verb": "deploy", "target": "/Volumes/Share/SEND TO",
                                                     "recipient": "n/a", "record_id": "n/a",
                                                     "artifact": "/Users/x/v2/appeal.docx", "md5": "abc"}},
                 "act": {"verb": "deploy", "target": "/Volumes/Share/SEND TO", "recipient": "n/a",
                         "record_id": "n/a", "files": ["/Users/x/v2/appeal.docx"]},
                 "deliverable": {"name": "appeal", "description": "the appeal letter"}}
        return {"state": state, "action": "deploy appeal", **extra}

    def go_fixture(self, files=("appeal.docx",), p=0.7, since="202609281405", share=None, census=None, reply="GO 1,3",
                   verb="deploy", census_mode="strict"):
        """A real E0 act on disk (E12): the built files, the target folder, the share-check and census receipts --
        -> (action dict, paths). Every deterministic check passes unless a caller changes something."""
        d = tempfile.mkdtemp(prefix="jev_go_")
        self.addCleanup(shutil.rmtree, d, True)
        os.makedirs(os.path.join(d, "v2"))
        target = os.path.join(d, "share", "Appeal 10.2026")
        os.makedirs(target)
        paths, md5s = [], {}
        for i, name in enumerate(files):
            fp, data = os.path.join(d, "v2", name), f"built file {i} {name}".encode()
            with open(fp, "wb") as fh:
                fh.write(data)
            paths.append(fp)
            md5s[fp] = hashlib.md5(data).hexdigest()
        now = int(time.time())
        sc = share if share is not None else {"exit": 0, "folder": os.path.realpath(target), "since": since,
                                               "epoch": now, "hits": 0}
        with open(os.path.join(d, "share-check.txt"), "w") as fh:
            fh.write("=== corp share-check ===\nSHARE-CHECK: no human trace found.\nSHARE-CHECK-RESULT " + json.dumps(sc) + "\n")
        cen = census if census is not None else [{"file": fp, "md5": m, "status": "CLEAN"} for fp, m in md5s.items()] + \
            [{"summary": True, "census": 1, "exit": 0, "mode": census_mode, "gated": 0, "pointers": 0}]
        with open(os.path.join(d, "census.jsonl"), "w") as fh:
            fh.write("".join(json.dumps(r) + "\n" for r in cen))
        row = {"id": 3, "verb": verb, "target": target, "recipient": "n/a", "record_id": "n/a", "files": dict(md5s)}
        act = {"verb": verb, "target": target, "recipient": "n/a", "record_id": "n/a", "src": "v2", "files": list(paths)}
        req = {"state": {"go": {"reply": reply, "row": row}, "act": act,
                         "deliverable": {"name": "appeal", "description": f"the appeal letter. P={p}"}},
               "receipts": {"share_check": "share-check.txt", "census": "census.jsonl"}, "action": "deploy appeal"}
        return req, {"dir": d, "target": target, "files": paths, "md5s": md5s}

    def go_gate(self, req, fx, *flags):
        path = os.path.join(fx["dir"], "action.json")
        with open(path, "w") as fh:
            json.dump(req, fh)
        return self.run_jev(["gate", "-f", path, *flags])

    def test_q_go_act_asks_the_registry_checks_and_bars(self):
        reg = {q["id"]: q for q in load_registry_file()["questions"]}["go_act"]
        req, fx = self.go_fixture()
        r = self.go_gate(req, fx, "--q", "go_act")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.sent()["questions"], {n: {"type": "noul", "instructions": p}   # no recipient: RG-09
                                                    for n, p in reg["checks"].items() if n != "recipient_matches"})
        out = json.loads(r.stdout)
        self.assertEqual((out["q"], out["approve_at"], out["block_at"], out["deterministic"], out["deterministic_blocks"]),
                         ("go_act", reg["thresholds"]["approve_at"], reg["thresholds"]["block_at"], "recomputed", []))
        self.assertEqual(sorted(out["checks"]), ["authorized", "right_artifact"])
        # an act whose row names a recipient (a handover to a named human) is asked all three (RG-09)
        named = json.loads(json.dumps(req))
        for obj in (named["state"]["go"]["row"], named["state"]["act"]):
            obj.update(verb="handover", recipient="Alex Reviewer, Reviewer")
        r = self.go_gate(named, fx, "--q", "go_act")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(self.sent(1)["questions"]), ["authorized", "recipient_matches", "right_artifact"])
        # a caller may still name its subset
        r = self.go_gate(dict(named, checks=["authorized", "right_artifact"]), fx, "--q", "go_act")
        self.assertEqual(sorted(self.sent(2)["questions"]), ["authorized", "right_artifact"])
        # an explicit flag still wins over the entry's bar
        out = json.loads(self.go_gate(req, fx, "--q", "go_act", "--approve-at", "0.95").stdout)
        self.assertEqual(out["approve_at"], 0.95)

    # --- E12: the CLI recomputes every deterministic check; a hand-written [] asserts nothing ----------------------

    def assert_blocked(self, req, fx, snippet, *flags):
        n0 = len(self.server.behavior["requests"])
        r = self.go_gate(req, fx, "--q", "go_act", *flags)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual((out["decision"], out["checks"]), ("block", {}), out)
        self.assertIn(snippet, out["reason"])
        self.assertTrue(out["reason"].startswith("deterministic: "), out["reason"])
        self.assertEqual(len(self.server.behavior["requests"]), n0, "a deterministic block never asks Jev")
        return out

    def test_go_act_recomputes_the_row_the_reply_and_the_send_rule(self):
        req, fx = self.go_fixture()
        no_row = json.loads(json.dumps(req)); del no_row["state"]["go"]["row"]
        self.assert_blocked(no_row, fx, "no adopted row")                                  # OM-07: no row, no act
        words = json.loads(json.dumps(req)); words["state"]["go"]["reply"] = "yeah go ahead and put it on the server"
        self.assert_blocked(words, fx, '"GO which rows?"')                                   # E5
        other = json.loads(json.dumps(req)); other["state"]["go"]["reply"] = "GO 1,4"
        self.assert_blocked(other, fx, "does not name row 3")
        named = json.loads(json.dumps(req)); named["state"]["go"]["reply"] = f"deploy it to {fx['target']} please"
        r = self.go_gate(named, fx, "--q", "go_act")                                        # E5: words that name the act
        self.assertEqual(json.loads(r.stdout)["deterministic_blocks"], [])
        send = json.loads(json.dumps(req))
        for side in ("row", "act"):
            (send["state"]["go"]["row"] if side == "row" else send["state"]["act"])["verb"] = "upload"
        self.assert_blocked(send, fx, "HUMAN-ONLY")                                          # E6
        portal = json.loads(json.dumps(req))
        for obj in (portal["state"]["go"]["row"], portal["state"]["act"]):
            obj.update(verb="browse write", target="https://portal.example/appeals", recipient="Acme Review Org", files=None)
            obj.pop("files")
        self.assert_blocked(portal, fx, "is a send to a third party through its site")      # E6: FA-06's upload
        moved = json.loads(json.dumps(req)); moved["state"]["act"]["target"] = fx["target"] + " v2"
        self.assert_blocked(moved, fx, "act.target")

    def test_go_act_recomputes_every_file_from_disk(self):
        req, fx = self.go_fixture(files=("01 Appeal.pdf", "02 Enclosures.pdf"))
        r = self.go_gate(req, fx, "--q", "go_act")                                         # FB-04: two files, both named
        self.assertEqual(json.loads(r.stdout)["deterministic_blocks"], [], r.stdout)
        one = json.loads(json.dumps(req)); one["state"]["go"]["row"]["files"].pop(fx["files"][1])
        self.assert_blocked(one, fx, "is not among the row's files")
        short = json.loads(json.dumps(req)); short["state"]["act"]["files"] = fx["files"][:1]
        self.assert_blocked(short, fx, "is not among act.files")
        blank = json.loads(json.dumps(req)); blank["state"]["go"]["row"]["files"][fx["files"][0]] = ""
        self.assert_blocked(blank, fx, "names no md5")
        with open(fx["files"][0], "ab") as fh:                                                # rebuilt after the owner's GO
            fh.write(b" edited")
        out = self.assert_blocked(req, fx, "on disk is")
        self.assertIn("changed after the census", out["reason"])

    def test_go_act_reads_the_share_check_and_census_receipts(self):
        cases = [
            ({"share": {"exit": 1, "folder": None, "since": "202609281405", "epoch": None, "hits": 2}}, "share-check exit 1"),
            ({"share": {"exit": 0, "folder": "/Volumes/Share", "since": "202609281405", "epoch": None, "hits": 0}},
             "never its parent tree"),
            ({"share": {"exit": 0, "folder": None, "since": "", "epoch": None, "hits": 0}}, "without CAMPAIGN_START"),
            ({"share": {"exit": 0, "folder": None, "since": "202609281405", "epoch": 1, "hits": 0}}, "min old"),
            ({"census": [{"summary": True, "census": 1, "exit": 1, "mode": "strict", "gated": 2, "pointers": 0}]},
             "census exit 1"),
            ({"census": [{"file": "/elsewhere.pdf", "md5": "0" * 32}, {"summary": True, "census": 1, "exit": 0,
                                                                       "mode": "strict"}]}, "does not cover"),
            ({"census_mode": "for-signature"}, "passes only a handover row"),
        ]
        for kw, snippet in cases:
            with self.subTest(snippet=snippet):
                req, fx = self.go_fixture(**{k: v for k, v in kw.items() if k != "share"})
                if "share" in kw:
                    sc = dict(kw["share"])
                    sc["folder"] = sc["folder"] or os.path.realpath(fx["target"])
                    sc["epoch"] = sc["epoch"] or int(time.time())
                    with open(os.path.join(fx["dir"], "share-check.txt"), "w") as fh:
                        fh.write("SHARE-CHECK-RESULT " + json.dumps(sc) + "\n")
                self.assert_blocked(req, fx, snippet)
        req, fx = self.go_fixture(census_mode="for-signature", verb="handover")            # a draft for signature
        self.assertEqual(json.loads(self.go_gate(req, fx, "--q", "go_act").stdout)["deterministic_blocks"], [])
        req, fx = self.go_fixture()
        del req["receipts"]
        out = self.assert_blocked(req, fx, "no share-check receipt")
        self.assertIn("no census receipt", out["reason"])

    def test_a_hand_written_empty_list_asserts_nothing_and_a_callers_block_still_blocks(self):
        req, fx = self.go_fixture()
        del req["receipts"]
        self.assert_blocked(dict(req, deterministic_blocks=[]), fx, "no share-check receipt")   # [] is ignored
        req, fx = self.go_fixture()
        self.assert_blocked(dict(req, deterministic_blocks=["the SEND TO folder holds a preview"]), fx,
                            "caller: the SEND TO folder holds a preview")

    # --- decision G: veto mode for an act on a row the owner's reply named by number -----------------------------------------

    def test_veto_mode_blocks_only_at_the_floor_and_otherwise_approves(self):
        req, fx = self.go_fixture(p=0.7)                                                  # every check answers 0.7
        r = self.go_gate(req, fx, "--q", "go_act", "--veto")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual((out["decision"], out["mode"], out["checks"]["authorized"]), ("approve", "veto", 0.7))
        self.assertTrue(out["reason"].startswith("no veto: every check above 0.1"), out["reason"])
        self.assertEqual(sorted(out["unclear"]), ["authorized", "right_artifact"])   # the record (no recipient: RG-09)
        self.assertEqual(out["deterministic_blocks"], [])
        out = json.loads(self.go_gate(req, fx, "--q", "go_act").stdout)                  # the 0.9-all bar -> review
        self.assertEqual((out["decision"], out["mode"]), ("review", "all"))
        req, fx = self.go_fixture(p=0.1)
        out = json.loads(self.go_gate(req, fx, "--q", "go_act", "--veto").stdout)
        self.assertEqual((out["decision"], sorted(out["failed"])), ("block", ["authorized", "right_artifact"]))
        req, fx = self.go_fixture(p=0.11)
        self.assertEqual(json.loads(self.go_gate(req, fx, "--q", "go_act", "--veto").stdout)["decision"], "approve")

    def test_veto_mode_reviews_on_any_jev_failure(self):
        req, fx = self.go_fixture()
        self.server.behavior["status"] = 503
        r = self.go_gate(req, fx, "--q", "go_act", "--veto", "--deadline", "2")
        self.assertEqual(r.returncode, 4, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual((out["decision"], out["mode"]), ("review", "veto"))
        self.server.behavior = {"requests": [], "drop_answers": ["right_artifact"]}   # a missing answer: never approve
        r = self.go_gate(req, fx, "--q", "go_act", "--veto")
        self.assertEqual((r.returncode, json.loads(r.stdout)["decision"]), (4, "review"))

    def test_veto_needs_go_act_a_row_and_a_numbered_reply(self):
        req, fx = self.go_fixture()
        no_row = json.loads(json.dumps(req)); del no_row["state"]["go"]["row"]
        words = json.loads(json.dumps(req)); words["state"]["go"]["reply"] = f"deploy it to {fx['target']}"
        for bad, flags in ((no_row, ("--q", "go_act", "--veto")), (words, ("--q", "go_act", "--veto")),
                           (req, ("--q", "go_act", "--veto", "--approve-at", "0.8")),
                           (dict(req, checks={"a": "Check a holds. P=0.95"}), ("--veto",))):   # no go_act: nothing recomputed
            with self.subTest(flags=flags):
                self.assertEqual(self.go_gate(bad, fx, *flags).returncode, 2)
        self.assertEqual(len(self.server.behavior["requests"]), 0)
        # outside /corp-jev a caller's own deterministic block still blocks with no Jev call
        r = self.gate(dict(gate_req(a="P=0.99"), deterministic_blocks=["order not found"]))
        out = json.loads(r.stdout)
        self.assertEqual((r.returncode, out["decision"], out["reason"]), (0, "block", "deterministic: order not found"))
        self.assertEqual(len(self.server.behavior["requests"]), 0)

    def test_a_state_not_in_english_is_review_with_no_call(self):
        # OM-08: Jev's checks on a Spanish state are not trusted
        req, fx = self.go_fixture()
        req["state"]["deliverable"]["description"] = ("la carta de apelación para el plan, con las horas que "
                                                       "fueron aprobadas por la aseguradora y los documentos del caso")
        r = self.go_gate(req, fx, "--q", "go_act", "--veto")
        out = json.loads(r.stdout)
        self.assertEqual((r.returncode, out["decision"], out.get("lang_hint")), (0, "review", "non_en"), out)
        spanish = gate_req(a="P=0.99")
        spanish["state"]["context"] = "El cliente pide el reembolso porque el pedido llegó tarde y está dañado."
        out = json.loads(self.gate(spanish).stdout)
        self.assertEqual(out["decision"], "review")
        self.assertEqual(len(self.server.behavior["requests"]), 0)

    # --- INTEGRATION 3: F1 (the copied folder), F2 (every outward target), F3 (adopted bases), F6 (lang_hint) ---------

    def test_f1_the_copied_folder_holds_only_the_rows_files(self):
        # OPUS RG-01's sendto/ receipt: a stale "03 Enclosure v1.pdf" beside the GO'd v2 in the folder the executor
        # copies -- go_act_blocks() returned [] and --record then vouched for both
        req, fx = self.go_fixture(files=("03 Enclosure v2.pdf",))
        self.assertEqual(json.loads(self.go_gate(req, fx, "--q", "go_act").stdout)["deterministic_blocks"], [])
        with open(os.path.join(fx["dir"], "v2", ".DS_Store"), "wb") as fh:       # Finder's file is never a block
            fh.write(b"\0")
        self.assertEqual(json.loads(self.go_gate(req, fx, "--q", "go_act").stdout)["deterministic_blocks"], [])
        stale = os.path.join(fx["dir"], "v2", "03 Enclosure v1.pdf")
        with open(stale, "wb") as fh:
            fh.write(b"%PDF-1.4 stale v1 render")
        out = self.assert_blocked(req, fx, "act.src holds '03 Enclosure v1.pdf', which the row does not name")
        self.assertIn("(F1", out["reason"])
        os.rename(stale, os.path.join(fx["dir"], "stale v1 (quarantined).pdf"))  # quarantine it: the act passes again
        self.assertEqual(json.loads(self.go_gate(req, fx, "--q", "go_act").stdout)["deterministic_blocks"], [])
        os.makedirs(os.path.join(fx["dir"], "v2", "office"))
        with open(os.path.join(fx["dir"], "v2", "office", "~$Enclosure.docx"), "w") as fh:   # a lock, a subfolder
            fh.write("lock")
        self.assert_blocked(req, fx, "act.src holds 'office/~$Enclosure.docx'")
        no_src = json.loads(json.dumps(req)); del no_src["state"]["act"]["src"]
        self.assert_blocked(no_src, fx, "act.src is missing")
        outside = json.loads(json.dumps(req)); outside["state"]["act"]["src"] = "share"
        self.assert_blocked(outside, fx, "is not under act.src share")

    def test_f2_every_outward_target_needs_its_share_check_receipt(self):
        # FABLE-A RG-01's repro-a: a relative and an smb:// target passed every check with no share-check at all
        for target in ("TeamShare/ORG/X/Appeal 10.2026", "smb://server/TeamShare/ORG/X/Appeal 10.2026",
                       "afp://server/TeamShare/ORG/X/Appeal%2010.2026", "\\\\server\\TeamShare\\X\\A"):
            with self.subTest(target=target):
                req, fx = self.go_fixture()
                for obj in (req["state"]["go"]["row"], req["state"]["act"]):
                    obj["target"] = target
                del req["receipts"]["share_check"]
                self.assert_blocked(req, fx, "no share-check receipt")
        # a relative target resolves against the work folder (the folder holding CORP_STATE.md) and passes with ITS
        # receipt; a receipt on any other folder blocks
        req, fx = self.go_fixture()
        open(os.path.join(fx["dir"], "CORP_STATE.md"), "w").close()
        rel = "TeamShare/ORG/X/Appeal 10.2026"
        os.makedirs(os.path.join(fx["dir"], rel))
        for obj in (req["state"]["go"]["row"], req["state"]["act"]):
            obj["target"] = rel
        sc = {"exit": 0, "folder": os.path.realpath(os.path.join(fx["dir"], rel)), "since": "202609281405",
              "epoch": int(time.time()), "hits": 0}
        with open(os.path.join(fx["dir"], "share-check.txt"), "w") as fh:
            fh.write("SHARE-CHECK-RESULT " + json.dumps(sc) + "\n")
        self.assertEqual(json.loads(self.go_gate(req, fx, "--q", "go_act").stdout)["deterministic_blocks"], [])
        with open(os.path.join(fx["dir"], "share-check.txt"), "w") as fh:
            fh.write("SHARE-CHECK-RESULT " + json.dumps(dict(sc, folder=os.path.realpath(fx["target"]))) + "\n")
        self.assert_blocked(req, fx, "never its parent tree")
        # an smb:// target passes only with a receipt on its /Volumes mount -- never on the parent tree
        for folder, ok in (("/Volumes/TeamShare/ORG/X/Appeal 10.2026", True),
                           ("/Volumes/ORG/X/Appeal 10.2026", True),                 # the share mounted one level down
                           ("/Volumes/TeamShare/ORG/X", False),                # the parent tree
                           ("/Volumes/Other/ORG/X/Appeal 10.2026", False)):
            with self.subTest(folder=folder):
                req, fx = self.go_fixture()
                for obj in (req["state"]["go"]["row"], req["state"]["act"]):
                    obj["target"] = "smb://server/TeamShare/ORG/X/Appeal 10.2026"
                with open(os.path.join(fx["dir"], "share-check.txt"), "w") as fh:
                    fh.write("SHARE-CHECK-RESULT " + json.dumps(dict(sc, folder=folder)) + "\n")
                if ok:
                    self.assertEqual(json.loads(self.go_gate(req, fx, "--q", "go_act").stdout)["deterministic_blocks"], [])
                else:
                    self.assert_blocked(req, fx, "which is not the mount of smb://server/TeamShare")
        # an http(s) URL (a portal write into our own system) needs none; an empty target blocks
        req, fx = self.go_fixture()
        for obj in (req["state"]["go"]["row"], req["state"]["act"]):
            obj.update(verb="portal write", target="https://portal.example/client/7")
            obj.pop("files", None)
        del req["receipts"]
        self.assertEqual(json.loads(self.go_gate(req, fx, "--q", "go_act").stdout)["deterministic_blocks"], [])
        req, fx = self.go_fixture()
        for obj in (req["state"]["go"]["row"], req["state"]["act"]):
            obj["target"] = ""
        self.assert_blocked(req, fx, "act.target is empty")

    def test_f3_a_file_never_lands_over_an_adopted_human_edit(self):
        req, fx = self.go_fixture(files=("01 Review.docx",))
        with open(os.path.join(fx["target"], ".corp-deployed.json"), "w") as fh:
            json.dump({"corp_deploy_manifest": 1, "files": {"01 Review.docx": {
                "md5": "0" * 32, "adopted": {"by": "Alex Reviewer", "at": "2026-09-29T09:00:00"}}}}, fh)
        self.assert_blocked(req, fx, "is a human edit adopted as the base")
        req, fx2 = self.go_fixture(files=("01 Reassessment v2.docx",))            # a NEW version file beside the reviewer's
        with open(os.path.join(fx2["target"], ".corp-deployed.json"), "w") as fh:
            json.dump({"files": {"01 Review.docx": {"md5": "0" * 32, "adopted": {"by": "F"}}}}, fh)
        self.assertEqual(json.loads(self.go_gate(req, fx2, "--q", "go_act").stdout)["deterministic_blocks"], [])

    def stale_beside(self, fx, name="03 Enclosure v1.pdf"):
        """A stale render in the folder the executor copies (act.src = v2), not named by any row."""
        with open(os.path.join(fx["dir"], "v2", name), "wb") as fh:
            fh.write(b"%PDF-1.4 stale v1 render [DATA NEEDED: units]")

    def test_cc01_a_deploy_or_handover_that_names_no_files_never_passes(self):
        # closure check CC-01 (= OM RG-01 = FA RG-03), gate/cli_cc01.py's three shapes: the gate trusted the caller's own
        # empty "files" list to skip the act.src listing and the census -- a stale v1 and both uncensused files rode
        # the same GO
        shapes = (("row Files a string, act.files []", "the SEND TO folder", []),
                  ("row Files {}, act.files []", {}, []),
                  ("no files key on row or act", None, None))
        for verb in ("deploy", "handover"):
            for label, rowfiles, actfiles in shapes:
                with self.subTest(verb=verb, shape=label):
                    req, fx = self.go_fixture(files=("03 Enclosure v2.pdf",), verb=verb)
                    self.stale_beside(fx)
                    row, act = req["state"]["go"]["row"], req["state"]["act"]
                    if rowfiles is None:
                        row.pop("files"); act.pop("files")
                    else:
                        row["files"], act["files"] = rowfiles, actfiles
                    del req["receipts"]["census"]                       # no census receipt named either
                    out = self.assert_blocked(req, fx, "names every file it writes")
                    self.assertIn("act.src holds '03 Enclosure v1.pdf'", out["reason"])
                    self.assertIn("act.src holds '03 Enclosure v2.pdf'", out["reason"])   # unnamed: nothing is GO'd
                    self.assertIn("no census receipt", out["reason"])
        # act.src set with a census receipt named still blocks: the row names nothing
        req, fx = self.go_fixture(files=("03 Enclosure v2.pdf",))
        req["state"]["go"]["row"]["files"] = {}; req["state"]["act"]["files"] = []
        self.assert_blocked(req, fx, "names every file it writes")

    def test_cc01_files_named_but_the_census_is_still_required_and_src_listed(self):
        # the three conditions of the fix at the CLI: files OR act.src -> the listing and the census receipt
        req, fx = self.go_fixture(files=("03 Enclosure v2.pdf",))
        self.assertEqual(json.loads(self.go_gate(req, fx, "--q", "go_act").stdout)["deterministic_blocks"], [])
        no_census = json.loads(json.dumps(req)); del no_census["receipts"]["census"]
        self.assert_blocked(no_census, fx, "no census receipt")
        # a web target copies no folder: files there need the census (kept), and no act.src is asked
        web = json.loads(json.dumps(req))
        for obj in (web["state"]["go"]["row"], web["state"]["act"]):
            obj.update(verb="portal write", target="https://portal.example/client/7")
        del web["receipts"]["census"]; web["state"]["act"].pop("src")
        self.assert_blocked(web, fx, "no census receipt")

    def test_p2a_a_config_verb_aimed_at_a_folder_is_checked_like_a_deploy(self):
        # closure check P2-a (gate/harness.out "F2-probe"): 'config change' into /Volumes/... with a stale v1 in act.src
        # and no receipts gave 0 blocks
        for target in ("folder", "/Volumes/TeamShare/ORG/X/Appeal 10.2026", "smb://server/TeamShare/X/A",
                       "\\\\server\\TeamShare\\X\\A", "TeamShare/ORG/X/Appeal 10.2026"):
            with self.subTest(target=target):
                req, fx = self.go_fixture(files=("03 Enclosure v2.pdf",), verb="config change")
                self.stale_beside(fx)
                if target != "folder":
                    for obj in (req["state"]["go"]["row"], req["state"]["act"]):
                        obj["target"] = target
                else:
                    for obj in (req["state"]["go"]["row"], req["state"]["act"]):
                        obj["target"] = fx["target"]
                del req["receipts"]
                out = self.assert_blocked(req, fx, "no share-check receipt")
                self.assertIn("act.src holds '03 Enclosure v1.pdf'", out["reason"])
                self.assertIn("no census receipt", out["reason"])
        # ...and a clean config act on a folder passes exactly like a clean deploy (receipts named, nothing extra)
        req, fx = self.go_fixture(files=("03 Enclosure v2.pdf",), verb="config change")
        self.assertEqual(json.loads(self.go_gate(req, fx, "--q", "go_act").stdout)["deterministic_blocks"], [])
        # a config change that names no file into a folder is the deploy's no-files block
        req, fx = self.go_fixture(files=("03 Enclosure v2.pdf",), verb="config change")
        req["state"]["go"]["row"].pop("files"); req["state"]["act"].pop("files")
        self.assert_blocked(req, fx, "names every file it writes")
        # a config change whose target is no folder (a URL, or none) stays exempt from folder rails
        for tgt in ("https://console.example/settings", ""):
            with self.subTest(exempt=tgt):
                req, fx = self.go_fixture(files=("03 Enclosure v2.pdf",), verb="config change")
                for obj in (req["state"]["go"]["row"], req["state"]["act"]):
                    obj["target"] = tgt
                self.stale_beside(fx)
                del req["receipts"]
                r = self.go_gate(req, fx, "--q", "go_act")
                self.assertEqual(json.loads(r.stdout)["deterministic_blocks"], [], r.stdout)

    def test_rg12_the_row_verb_is_one_bare_e0_verb(self):
        # FABLE-A RG-12: the template once offered "handover (a draft for signature)" as the Verb cell
        for verb in ("handover (a draft for signature)", "copy", "deploy it"):
            with self.subTest(verb=verb):
                req, fx = self.go_fixture(verb=verb)
                self.assert_blocked(req, fx, "is not an E0 verb")
        req, fx = self.go_fixture(verb="Handover", census_mode="for-signature")   # case folds: the bare word passes
        self.assertEqual(json.loads(self.go_gate(req, fx, "--q", "go_act").stdout)["deterministic_blocks"], [])

    def test_f6_a_path_full_of_spanish_stopwords_never_turns_the_gate_into_review(self):
        # FABLE-B RG-03: a random tmp folder name read as Spanish ("el") and the veto test failed 1 run in N
        req, fx = self.go_fixture(p=0.7)
        target = os.path.join(fx["dir"], "el los las del que una por con", "Apelación 10.2026")
        os.makedirs(target)
        for obj in (req["state"]["go"]["row"], req["state"]["act"]):
            obj["target"] = target
        sc = {"exit": 0, "folder": os.path.realpath(target), "since": "202609281405", "epoch": int(time.time()),
              "hits": 0}
        with open(os.path.join(fx["dir"], "share-check.txt"), "w") as fh:
            fh.write("SHARE-CHECK-RESULT " + json.dumps(sc) + "\n")
        out = json.loads(self.go_gate(req, fx, "--q", "go_act", "--veto").stdout)
        self.assertEqual((out["decision"], out.get("lang_hint"), out["checks"]["authorized"]), ("approve", None, 0.7), out)

    def test_q_go_act_misuse_exits_2_before_http(self):
        cases = [
            (self.go_req(checks=["authorized", "nope"]), ("--q", "go_act")),         # an unknown check name
            (self.go_req(checks=["authorized", "authorized"]), ("--q", "go_act")),   # a duplicate
            (self.go_req(checks={"authorized": "my own text"}), ("--q", "go_act")),  # text beside a registry id
            (self.go_req(checks=["authorized"]), ()),                                # names without --q
            (self.go_req(), ("--q", "claim_support")),                               # not a gate entry
            (self.go_req(), ("--q", "no_such_gate")),
        ]
        for req, flags in cases:
            with self.subTest(flags=flags, checks=req.get("checks")):
                self.assertEqual(self.gate(req, *flags).returncode, 2)
        self.assertEqual(len(self.server.behavior["requests"]), 0)


# --- transport: 402 / Retry-After, observability fields, usage + judgments logs ------------------

IN_FLIGHT_402 = {"error": {"code": 402, "message": "This request would exceed your available credits given your "
                           "current in-flight requests.", "metadata": {"reason": "in_flight_budget_exhausted",
                                                                     "limit_source": "openrouter_in_flight_budget"}}}


class TransportTestCase(StubCase):

    def test_402_in_flight_budget_waits_for_retry_after(self):
        self.server.behavior.update(status_sequence=[402], retry_after="2", error_body=IN_FLIGHT_402)
        t0 = time.monotonic()
        r = self.run_jev(["yes", "q?", "-s", "state"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.server.behavior["requests"]), 2)
        self.assertGreaterEqual(time.monotonic() - t0, 1.9)   # Retry-After 2, not the 1 s backoff

    def test_402_in_flight_body_without_header_retries_on_backoff(self):
        self.server.behavior.update(status_sequence=[402], error_body=IN_FLIGHT_402)
        r = self.run_jev(["yes", "q?", "-s", "state"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.server.behavior["requests"]), 2)

    def test_402_credits_exhausted_exits_3_without_a_retry(self):
        self.server.behavior.update(status=402, error_body={"error": {"code": 402, "message": "Insufficient credits",
                                                                      "metadata": {"limit_source": "openrouter_credits"}}})
        r = self.run_jev(["yes", "q?", "-s", "state"])
        self.assertEqual(r.returncode, 3)
        self.assertIn("OpenRouter credits exhausted", r.stderr)
        self.assertEqual(len(self.server.behavior["requests"]), 1)
        r = self.run_jev(["ping"])   # preflight reads this to park on credits, not on "no key"
        self.assertEqual(r.returncode, 3)
        self.assertIn("OpenRouter credits exhausted", json.loads(r.stdout)["error"])

    def test_429_honours_retry_after_over_the_backoff(self):
        self.server.behavior.update(status_sequence=[429], retry_after="0")
        t0 = time.monotonic()
        r = self.run_jev(["yes", "q?", "-s", "state"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.server.behavior["requests"]), 2)
        self.assertLess(time.monotonic() - t0, 0.9)   # Retry-After 0 replaced the 1 s backoff

    def test_retry_after_past_the_deadline_fails_fast(self):
        self.server.behavior.update(status=429, retry_after="30")
        t0 = time.monotonic()
        r = self.run_jev(["yes", "q?", "-s", "state", "--deadline", "5"])
        self.assertEqual(r.returncode, 4)
        self.assertIn("Retry-After 30s is past the deadline", r.stderr)
        self.assertLess(time.monotonic() - t0, 4)
        self.assertEqual(len(self.server.behavior["requests"]), 1)

    def test_trace_session_id_and_usage_ids(self):
        r = self.run_jev(["yes", "q?", "-s", "state"])
        self.assertEqual(r.returncode, 0, r.stderr)
        env = self.base_env(extra={"CLAUDE_CODE_SESSION_ID": "sess-123"})
        r = self.run_jev(["gate", "-f", self.write_tmp("a.json", json.dumps(gate_req(a="P=0.95")))], env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.sent(0)["trace"], {"trace_name": "jev:yes"})
        self.assertNotIn("session_id", self.sent(0))
        self.assertEqual((self.sent(1)["session_id"], self.sent(1)["trace"]), ("sess-123", {"trace_name": "jev:gate"}))
        usage = self.log_lines()
        self.assertEqual([(u["id"], u["provider"]) for u in usage], [("stub-1", "stub")] * 2)
        self.assertEqual(usage[1]["session"], "sess-123")

    def test_a_stub_run_never_writes_the_default_judgments_log(self):
        home = tempfile.TemporaryDirectory(prefix="jev_home_")
        self.addCleanup(home.cleanup)
        env = self.base_env(extra={"HOME": home.name})
        env.pop("JEV_JUDGMENTS_LOG")   # a harness that forgot the override: JEV_BASE_URL alone must keep it silent
        r = self.run_jev(["yes", "q?", "-s", "state"], env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(os.path.join(home.name, ".cache", "jev", "judgments.jsonl")))

    def test_judgments_log_one_line_per_answered_question(self):
        env = self.base_env(extra={"CLAUDE_CODE_SESSION_ID": "sess-9"})
        r = self.run_jev(["gate", "-f", self.write_tmp("a.json", json.dumps(gate_req(a="P=0.95", b="P=0.2", c="P=0.5")))],
                         env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_jev(["verify", "-f", self.write_tmp("d.json", json.dumps(draft_row(stub_choice="declined", stub_conf=0.97)))],
                         env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = "".join(json.dumps({"id": f"x{i}", "state": f"P=0.{i + 1}"}) + "\n" for i in range(3))
        r = self.run_jev(["filter", "q?", "--all"], input_text=rows, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        j = self.log_lines("judgments")
        # verify's one request answers two questions (D16: the cookbook's choice + the addresses_task noul)
        self.assertEqual([x["cmd"] for x in j], ["gate"] * 3 + ["verify"] * 2 + ["filter"] * 3)
        self.assertEqual({x["question"]: x["noul"] for x in j[:3]}, {"a": 0.95, "b": 0.2, "c": 0.5})
        for x in j:
            self.assertEqual((x["session"], x["resolved"], x["request_id"]), ("sess-9", "jev-latest", "stub-1"))
            self.assertIn("ts", x)
        v = {x["question"]: x for x in j[3:5]}
        self.assertEqual((v["support"]["type"], v["support"]["choice"], v["support"]["confidence"]),
                         ("choice", "declined", 0.97))
        self.assertEqual(set(v["support"]["probabilities"]), {"supported", "unsupported", "declined"})
        self.assertEqual(v["addresses_task"]["type"], "noul")
        self.assertEqual({x["question"] for x in j[5:]}, {"q"})       # row-as-state: every row asks "q"
        self.assertEqual(sorted(x["noul"] for x in j[5:]), [0.1, 0.2, 0.3])


# --- the pure rules, no subprocess ----------------------------------------------------------

class PureRulesTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.jev = load_jev_module()

    def test_cascade_route(self):
        route = self.jev.cascade_route
        self.assertEqual(route("supported", 0.8, 0.8), "send")
        self.assertEqual(route("supported", 0.7999, 0.8), "escalate")
        self.assertEqual(route("supported", 0.0, 0.8), "escalate")    # a missing confidence arrives as 0
        self.assertEqual(route("unsupported", 1.0, 0.8), "escalate")
        self.assertEqual(route("declined", 0.05, 0.8), "handoff")
        self.assertEqual(route(None, 1.0, 0.8), "escalate")
        # the one escalation: a re-draft that fails hands off, and never escalates again
        self.assertEqual(route("unsupported", 1.0, 0.8, escalated=True), "handoff")
        self.assertEqual(route("supported", 0.79, 0.8, escalated=True), "handoff")
        self.assertEqual(route(None, 0.0, 0.8, escalated=True), "handoff")
        self.assertEqual(route("supported", 0.8, 0.8, escalated=True), "send")

    def test_retry_after_seconds(self):
        ra = self.jev.retry_after_seconds
        self.assertEqual(ra({"Retry-After": "2"}), 2.0)
        self.assertEqual(ra({"Retry-After": " 0 "}), 0.0)
        self.assertEqual(ra({"Retry-After": "-5"}), 0.0)
        self.assertIsNone(ra({}))
        self.assertIsNone(ra(None))
        self.assertIsNone(ra({"Retry-After": "soon"}))
        soon = email.utils.format_datetime(datetime.now(timezone.utc) + timedelta(seconds=30), usegmt=True)
        self.assertTrue(25 <= ra({"Retry-After": soon}) <= 31)                        # an HTTP-date
        self.assertEqual(ra({"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"}), 0.0)   # a date already past

    def test_gate_decision(self):
        decide = self.jev.gate_decision
        self.assertEqual(decide({"x": 0.9}, 0.9, 0.1)[0], "approve")
        self.assertEqual(decide({"x": 0.9, "y": 0.8999}, 0.9, 0.1)[0], "review")
        self.assertEqual(decide({"x": 0.1, "y": 1.0}, 0.9, 0.1)[0], "block")
        self.assertEqual(decide({"x": 0.1001}, 0.9, 0.1)[0], "review")
        self.assertEqual(decide({"x": 0.05, "y": 0.5, "z": 0.95}, 0.9, 0.1), ("block", ["x"], ["y"]))
        with self.assertRaises(ValueError):
            decide({}, 0.9, 0.1)   # no checks is no evidence: never approve
        # decision G, veto mode: only the floor decides; `unclear` stays the record
        self.assertEqual(decide({"x": 0.1001, "y": 0.5}, 0.9, 0.1, "veto"), ("approve", [], ["x", "y"]))
        self.assertEqual(decide({"x": 0.1, "y": 0.99}, 0.9, 0.1, "veto"), ("block", ["x"], []))
        with self.assertRaises(ValueError):
            decide({}, 0.9, 0.1, "veto")       # still never approves without evidence
        with self.assertRaises(ValueError):
            decide({"x": 0.5}, 0.9, 0.1, "lenient")

    def test_receipt_excerpt_rule(self):
        # decision C: inputs / formula sections, else the head minus the figure's own line; never None-unsafe
        d = tempfile.mkdtemp(prefix="jev_rcpt_")
        self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True))
        md = os.path.join(d, "r.md")
        with open(md, "w") as fh:
            fh.write("Intro line\n### Input\nrows 1-3\n### Result\n42\n")
        self.assertEqual(self.jev.receipt_excerpt(md, ["42"]), "### Input\nrows 1-3")
        head = os.path.join(d, "h.txt")
        with open(head, "w") as fh:
            fh.write("a\nanswer 42\nb\n")
        self.assertEqual(self.jev.receipt_excerpt(head, ["42"]), "a\nb")
        self.assertIsNone(self.jev.receipt_excerpt(os.path.join(d, "missing.md"), ["1"]))
        empty = os.path.join(d, "e.md")
        open(empty, "w").close()
        self.assertIsNone(self.jev.receipt_excerpt(empty, []))
        big = os.path.join(d, "big.md")
        with open(big, "w") as fh:
            fh.write("## inputs\n" + "x" * 5000 + "\n")
        self.assertTrue(self.jev.receipt_excerpt(big, []).endswith("[…]"))
        self.assertEqual(self.jev.calc_markers("1,2 [calc: a] and [calc: b]"), [("a", "1,2"), ("b", None)])

    def test_verify_contract_pinned_and_mirrored_in_corp_kit(self):
        self.assertEqual(self.jev.VERIFY_INSTRUCTIONS, SPEC_INSTRUCTIONS)
        self.assertEqual(self.jev.VERIFY_CRITERIA, SPEC_CRITERIA)
        self.assertEqual((self.jev.DEFAULT_ACCEPT, self.jev.DEFAULT_APPROVE_AT, self.jev.DEFAULT_BLOCK_AT), (0.8, 0.9, 0.1))
        with open(CORP_KIT_PATH) as fh:
            kit = fh.read()
        for label, text in SPEC_CRITERIA.items():   # corp-kit.js CASCADE_CRITERIA carries the same three strings
            self.assertTrue(f"{label}: '{text}'" in kit, f"corp-kit.js CASCADE_CRITERIA lacks {label}: {text}")


# ================================ wave 2 (2026-09-28): TypeSafe's official guidance ================================

def rows_jsonl(rows):
    return "".join(json.dumps(r) + "\n" for r in rows)


class FailureContractTestCase(StubCase):
    """M24: retry 408, cap each attempt, jitter, per-row unavailable in bulk (exit 0 + count), limits before calls."""

    def test_408_is_retried(self):
        self.server.behavior["status_sequence"] = [408]
        r = self.run_jev(["yes", "q?", "-s", "state"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.server.behavior["requests"]), 2)

    def test_one_attempt_is_capped_inside_the_deadline(self):
        self.server.behavior["delay_sequence"] = [1.5]          # the first reply comes too late
        env = self.base_env(extra={"JEV_ATTEMPT_TIMEOUT": "0.5"})
        t0 = time.monotonic()
        r = self.run_jev(["yes", "q?", "-s", "state", "--deadline", "10"], env=env)
        self.assertEqual(r.returncode, 0, r.stderr)             # the second attempt answered
        self.assertEqual(len(self.server.behavior["requests"]), 2)
        self.assertLess(time.monotonic() - t0, 5)

    def test_malformed_200_is_jev_side_exit_4(self):
        self.server.behavior["raw_200"] = "this is not json"
        r = self.run_jev(["yes", "q?", "-s", "state"])
        self.assertEqual(r.returncode, 4)
        self.assertIn("non-JSON 200", r.stderr + r.stdout)

    def test_bulk_unavailable_rows_are_unknown_counted_exit_0(self):
        self.server.behavior["status"] = 503
        r = self.run_jev(["filter", "q?", "--all", "--deadline", "1"],
                         input_text=rows_jsonl({"id": f"r{i}", "state": f"row {i}"} for i in range(3)))
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = self.jsonl(r.stdout)
        for row in lines[:-1]:
            self.assertEqual((row["keep"], row["status"], row["error"]), (None, "UNKNOWN", "unavailable"))
        self.assertEqual((lines[-1]["unavailable"], lines[-1]["unknown"], lines[-1]["complete"]), (3, 3, False))

    def test_breaker_stops_sending_to_a_dead_endpoint(self):
        self.server.behavior["status"] = 503
        rows = [{"id": f"r{i}", "state": {"text": f"row {i}", "stub_tag": f"r{i}"}} for i in range(20)]
        r = self.run_jev(["filter", "q?", "--all", "--deadline", "1"], input_text=rows_jsonl(rows))
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = self.jsonl(r.stdout)[:-1]
        not_sent = {row["id"] for row in lines if "not sent" in row["reason"]}
        self.assertTrue(not_sent, "the breaker never opened")
        reached = {req["state"]["stub_tag"] for req in self.server.behavior["requests"]}
        self.assertFalse(not_sent & reached)                     # a row reported 'not sent' never reached the API
        self.assertEqual(len(lines), 20)                         # never dropped

    def test_bulk_auth_failure_stops_sending_exit_3(self):
        self.server.behavior["status"] = 401
        rows = [{"id": f"r{i}", "state": f"row {i}"} for i in range(12)]
        r = self.run_jev(["filter", "q?", "--all"], input_text=rows_jsonl(rows))
        self.assertEqual(r.returncode, 3)
        lines = self.jsonl(r.stdout)
        self.assertEqual(len(lines), 13)                         # 12 rows + summary: every row accounted for
        self.assertLessEqual(len(self.server.behavior["requests"]), 6)
        self.assertEqual({row["error"] for row in lines[:-1]}, {"auth"})
        self.assertTrue(lines[-1]["stopped"].startswith("jev_failure: auth"))

    def test_bulk_with_no_key_prints_every_row_exit_3(self):
        r = self.run_jev(["rank", "q?", "-k", "2"], env=self.base_env(no_key=True),
                         input_text=rows_jsonl({"id": i, "state": f"row {i}"} for i in range(3)))
        self.assertEqual(r.returncode, 3)
        lines = self.jsonl(r.stdout)
        self.assertEqual([(row["id"], row["error"], row["keep"]) for row in lines[:-1]],
                         [(0, "no_key", None), (1, "no_key", None), (2, "no_key", None)])
        self.assertEqual(len(self.server.behavior["requests"]), 0)

    def test_limits_are_checked_before_any_call(self):
        many = [f"o{i}" for i in range(256)]
        ask = lambda qs: self.run_jev(["ask", "-"], input_text=json.dumps({"state": "s", "questions": qs}))
        cases = [
            self.run_jev(["pick", "which?", *many, "-s", "state"]),
            self.run_jev(["rate", "how?", "only-one", "-s", "state"]),
            self.run_jev(["rate", "how?", *[f"l{i}" for i in range(11)], "-s", "state"]),
            self.run_jev(["yes", "q?", "--true", "T", "-s", "state"]),
            self.run_jev(["filter", "q?", "--all", "--false", "F"], input_text=rows_jsonl([{"id": 1, "state": "s"}])),
            ask({"a": {"type": "noul", "instructions": "x?", "criteria": {"true": "T"}}}),
            ask({"a": {"type": "choice", "instructions": "x?", "criteria": {o: None for o in many}}}),
            ask({"a": {"type": "score", "instructions": "x?", "criteria": [f"l{i}" for i in range(11)]}}),
            ask({"a": {"type": "vibes", "instructions": "x?"}}),
        ]
        for i, r in enumerate(cases):
            self.assertEqual(r.returncode, 2, f"case {i}: {r.stderr}")
        self.assertEqual(len(self.server.behavior["requests"]), 0)
        r = self.run_jev(["pick", "which?", *many[:255], "-s", "state"])   # exactly 255 is allowed
        self.assertEqual(r.returncode, 0, r.stderr)


class PackingOrderTestCase(StubCase):
    server_cls = ThreadingStubServer

    def test_filter_keeps_input_order_when_rows_finish_out_of_order(self):
        ids = ["a", "b", "c", "d"]
        rows = [{"id": i, "state": {"text": f"P=0.{n + 1}", "stub_tag": i, "stub_delay": 0.25 * (3 - n)}}
                for n, i in enumerate(ids)]
        r = self.run_jev(["filter", "q?", "--all"], input_text=rows_jsonl(rows))
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = self.jsonl(r.stdout)
        self.assertEqual([row["id"] for row in lines[:-1]], ids)
        self.assertEqual([row["p_yes"] for row in lines[:-1]], [0.1, 0.2, 0.3, 0.4])
        self.assertNotEqual(self.server.behavior["completed"], ids)   # they really did finish out of order


class PickClarityTestCase(StubCase):
    """R1 item 3 / M6: clear = margin >= 1.1 AND the winner's probability >= 0.75."""

    def pick(self, probs):
        self.server.behavior["choice_probs"] = probs
        r = self.run_jev(["pick", "which?", *probs, "-s", "state"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_clear_needs_margin_and_a_concentrated_winner(self):
        out = self.pick({"a": 0.8, "b": 0.1, "c": 0.1})
        self.assertEqual((out["choice"], out["p_top"], out["clear"]), ("a", 0.8, True))
        out = self.pick({"a": 0.7, "b": 0.2, "c": 0.1})          # margin ln 3.5 = 1.25, but the winner holds 0.7
        self.assertGreaterEqual(out["margin"], 1.1)
        self.assertFalse(out["clear"])
        out = self.pick({"a": 0.5, "b": 0.3, "c": 0.2})          # margin 0.51
        self.assertFalse(out["clear"])

    def test_pick_clarity_rule(self):
        jev = load_jev_module()
        self.assertEqual(jev.pick_clarity({"a": 0.75, "b": 0.25})[2], False)   # margin ln 3 = 1.0986 < 1.1
        self.assertEqual(jev.pick_clarity({"a": 0.76, "b": 0.24})[2], True)    # margin 1.15, winner 0.76
        self.assertEqual(jev.pick_clarity({"a": 0.334, "b": 0.111, "c": 0.111, "d": 0.111,
                                           "e": 0.111, "f": 0.111, "g": 0.111})[2], False)
        self.assertEqual(jev.pick_clarity({}), (None, None, False))


class BuildCheckTestCase(StubCase):
    """R1 item 6 / M7: JEV_EXPECT_BUILD set -> a reply from another build carries "build_mismatch": true."""

    def test_matching_build_adds_nothing_and_a_mismatch_is_flagged(self):
        self.server.behavior["resolved_model"] = "typesafe/jev-9.99-test"
        same = self.base_env(extra={"JEV_EXPECT_BUILD": "typesafe/jev-9.99-test"})
        other = self.base_env(extra={"JEV_EXPECT_BUILD": "typesafe/jev-1.13-20260917"})
        out = json.loads(self.run_jev(["yes", "q?", "-s", "state"], env=same).stdout)
        self.assertNotIn("build_mismatch", out)
        out = json.loads(self.run_jev(["yes", "q?", "-s", "state"], env=other).stdout)
        self.assertTrue(out["build_mismatch"])
        out = json.loads(self.run_jev(["pick", "which?", "a", "b", "-s", "state"], env=other).stdout)
        self.assertTrue(out["build_mismatch"])
        r = self.run_jev(["filter", "q?", "--all"], env=other, input_text=rows_jsonl([{"id": 1, "state": "s"},
                                                                                      {"id": 2, "state": "t"}]))
        lines = self.jsonl(r.stdout)
        self.assertEqual([row.get("build_mismatch") for row in lines[:-1]], [True, True])
        self.assertEqual(lines[-1]["build_mismatch"], 2)
        out = json.loads(self.run_jev(["ping"], env=other).stdout)
        self.assertEqual((out["build_mismatch"], out["packing"]), (True, 2))

    # --- D9: no export needed -- with JEV_EXPECT_BUILD unset the re-gate cache names the expected builds ------------

    def yes_out(self, env=None):
        r = self.run_jev(["yes", "q?", "-s", "state"], env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_unset_env_accepts_a_build_that_passed_for_the_current_fingerprint(self):
        self.server.behavior["resolved_model"] = "typesafe/jev-1.13-20260917"   # seeded PASS in setUp
        self.assertNotIn("build_mismatch", self.yes_out())
        self.server.behavior["resolved_model"] = "typesafe/jev-9.99-new"          # no PASS: another build
        self.assertTrue(self.yes_out()["build_mismatch"])
        r = self.run_jev(["filter", "q?", "--all"], input_text=rows_jsonl([{"id": 1, "state": "s"}]))
        self.assertEqual(self.jsonl(r.stdout)[-1]["build_mismatch"], 1)          # bulk rows and the summary too

    def test_unset_env_fails_closed_without_a_pass_for_these_questions(self):
        self.server.behavior["resolved_model"] = "typesafe/jev-1.13-20260917"
        old = self.write_tmp("old.json", json.dumps({"typesafe/jev-1.13-20260917|0123abcd": {"pass": True},
                                                     "typesafe/jev-1.13-20260917": {"pass": True}}))
        fp = load_regate_module().current_fingerprint(2)
        fail = self.write_tmp("fail.json", json.dumps({f"typesafe/jev-1.13-20260917|{fp}": {"pass": False}}))
        for cache in (old, fail, os.path.join(self._tmpdir.name, "missing.json")):
            with self.subTest(cache=os.path.basename(cache)):
                out = self.yes_out(self.base_env(extra={"JEV_REGATE_CACHE": cache}))
                self.assertTrue(out["build_mismatch"])   # an old fingerprint, a FAIL, or no cache: nothing is expected

    def test_an_unreadable_golden_set_is_unavailable_never_a_build_change(self):
        # FB-09: the check itself could not run -- "build_check": "unavailable", one stderr line, no build_mismatch
        env = self.base_env(extra={"JEV_REGATE_GOLD": os.path.join(self._tmpdir.name if hasattr(self, "_tmpdir")
                                                                    else tempfile.gettempdir(), "no-golden-here")})
        r = self.run_jev(["yes", "q?", "-s", "state"], env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual((out.get("build_check"), out.get("build_mismatch")), ("unavailable", None))
        self.assertEqual(r.stderr.count("build check unavailable"), 1)
        r = self.run_jev(["filter", "q?", "--all"], env=env, input_text=rows_jsonl([{"id": 1, "state": "s"},
                                                                                    {"id": 2, "state": "t"}]))
        lines = self.jsonl(r.stdout)
        self.assertEqual([x.get("build_check") for x in lines[:-1]], ["unavailable", "unavailable"])
        self.assertEqual((lines[-1].get("build_check_unavailable"), lines[-1].get("build_mismatch")), (2, None))
        self.assertEqual(r.stderr.count("build check unavailable"), 1)   # once per run, not per row
        row = {"id": "c", "kind": "claim", "state": "Claim: 240 units approved. Source sentence: Approved 240. P=0.9",
               "verdict": "VERIFIED"}
        r = self.run_jev(["second"], env=env, input_text=json.dumps(row) + "\n")
        out = self.jsonl(r.stdout)[0]
        self.assertEqual((out["jev_agree"], out["build_check"]), ("unavailable", "unavailable"))   # it escalates (E13)
        self.assertNotIn("build_mismatch", out)

    def test_rewording_a_gated_question_moves_the_expectation_an_ungated_one_does_not(self):
        self.server.behavior["resolved_model"] = "typesafe/jev-1.13-20260917"
        reg = load_registry_file()
        for qid, want_mismatch in (("claim_support", True), ("keep_reject", False)):
            with self.subTest(reworded=qid):
                edited = json.loads(json.dumps(reg))
                for q in edited["questions"]:
                    if q["id"] == qid:
                        q["text"] = q["text"].rstrip("?") + ", read strictly?"
                path = self.write_tmp("reg.json", json.dumps(edited))
                out = self.yes_out(self.base_env(extra={"JEV_REGISTRY": path}))
                self.assertEqual(out.get("build_mismatch", False), want_mismatch)


class AskAllTestCase(StubCase):
    """R1 item 11 / M35: one question set over many rows, one request per row."""

    QUESTIONS = {"questions": {"supported": {"type": "noul", "instructions": "Does `source` support `claim`?"},
                               "status": {"type": "choice", "instructions": "Which status fits?",
                                          "criteria": {"VERIFIED": "same", "UNCLEAR": "cannot tell from this state"}}}}

    def test_one_request_per_row_every_question_riding_it(self):
        qfile = self.write_tmp("questions.json", json.dumps(self.QUESTIONS))
        rows = [{"id": "a", "state": {"claim": "c1", "source": "s1 P=0.9"}}, {"id": "b", "state": "plain text P=0.2"}]
        r = self.run_jev(["ask", "--all", qfile], input_text=rows_jsonl(rows))
        self.assertEqual(r.returncode, 0, r.stderr)
        reqs = self.server.behavior["requests"]
        self.assertEqual(len(reqs), 2)
        for req in reqs:
            self.assertEqual(req["questions"], self.QUESTIONS["questions"])
        self.assertEqual(sorted(json.dumps(req["state"]) for req in reqs),
                         sorted(json.dumps(row["state"]) for row in rows))
        lines = self.jsonl(r.stdout)
        self.assertEqual([(row["id"], row["status"]) for row in lines[:-1]], [("a", "JUDGED"), ("b", "JUDGED")])
        self.assertEqual((lines[0]["answers"]["supported"]["noul"], lines[1]["answers"]["supported"]["noul"]), (0.9, 0.2))
        self.assertEqual((lines[-1]["answered"], lines[-1]["complete"]), (2, True))

    def test_a_row_missing_an_answer_is_unknown_never_dropped(self):
        self.server.behavior["drop_answers"] = ["status"]
        qfile = self.write_tmp("questions.json", json.dumps(self.QUESTIONS))
        r = self.run_jev(["ask", "--all", qfile], input_text=rows_jsonl([{"id": "a", "state": "s"}]))
        self.assertEqual(r.returncode, 0, r.stderr)
        row, summary = self.jsonl(r.stdout)
        self.assertEqual((row["status"], row["keep"], row["error"]), ("UNKNOWN", None, "bad_answer"))
        self.assertIn("supported", row["answers"])             # the answers that did come back, for the record
        self.assertEqual(summary["complete"], False)

    def test_bad_calls_exit_2_before_http(self):
        with_state = dict(self.QUESTIONS, state="x")
        cases = [
            self.run_jev(["ask", "--all", self.write_tmp("q.json", json.dumps(with_state))],
                         input_text=rows_jsonl([{"id": 1, "state": "s"}])),
            self.run_jev(["ask", "--all", "-"], input_text=rows_jsonl([{"id": 1, "state": "s"}])),
            self.run_jev(["ask", "--all", self.write_tmp("q.json", json.dumps(self.QUESTIONS))],
                         input_text=rows_jsonl([{"id": 1, "state": "s"}, {"id": 1, "state": "t"}])),
        ]
        for i, r in enumerate(cases):
            self.assertEqual(r.returncode, 2, f"case {i}: {r.stderr}")
        self.assertEqual(len(self.server.behavior["requests"]), 0)


REGISTRY_PATH = os.path.join(os.path.dirname(HERE), "jev-registry.json")


def load_registry_file():
    with open(REGISTRY_PATH) as fh:
        return json.load(fh)


class RegistryTestCase(StubCase):
    """R1 item 14 / M9: one registry for every Jev question and bar; --q loads it; the kit and CLI stay in step."""

    def test_registry_is_complete_and_consistent(self):
        reg = load_registry_file()
        ids = [q["id"] for q in reg["questions"]]
        self.assertEqual(len(ids), len(set(ids)))
        for want in ("claim_support", "determination", "keep_reject", "blocker", "edit_kind", "pmo_status",
                     "locate_line", "locate_any", "panel_verdict", "class_pick", "verify_cascade", "addresses_task",
                     "go_act", "triage_payer_letter"):
            self.assertIn(want, ids)
        for q in reg["questions"]:
            for field in ("id", "type", "text", "thresholds", "measured", "measured_on", "used_by"):
                self.assertIn(field, q, f"{q.get('id')}: {field}")
            self.assertIsInstance(q["measured"], bool, q["id"])
            self.assertRegex(q["text"].strip(), r"[?.]$", f"{q['id']}: a full sentence, not a label")
            if q["type"] == "choice":
                self.assertLessEqual(len(q["options"]), 255)
        by_id = {q["id"]: q for q in reg["questions"]}
        self.assertEqual(by_id["claim_support"]["text"], "Does the source sentence support the claim as worded?")
        # D13/D14: only the two gated questions are measured, and the gated ones are exactly the golden set's
        self.assertEqual({q["id"] for q in reg["questions"] if q["measured"]}, {"claim_support", "determination"})
        gated = {q["id"]: q["regate"]["golden_question"] for q in reg["questions"] if q.get("regate")}
        self.assertEqual(set(gated), {"claim_support", "determination"})
        with open(os.path.join(os.path.dirname(HERE), "golden", "regate_items.jsonl")) as fh:
            golden_questions = {json.loads(line)["question"] for line in fh if line.strip()}
        self.assertEqual(golden_questions, set(gated.values()))
        self.assertIn("provisional", by_id["keep_reject"]["measured_on"])   # D13: the 1.1 bar is not measured
        # D1: value selection is not a Jev job; LOCATE points only
        self.assertFalse([i for i in ids if "select" in i or "extract" in i], ids)
        self.assertIn("never selects a value", by_id["locate_line"]["measured_on"])
        self.assertEqual(by_id["locate_line"]["options"], {"NONE": "No line of the page states it."})
        self.assertTrue(by_id["locate_line"].get("dynamic_options"))
        self.assertEqual(by_id["pmo_status"]["text"], "Is this item still open according to the evidence shown?")
        self.assertEqual(by_id["pmo_status"]["second"]["no"], ["CLOSED"])
        self.assertTrue(by_id["panel_verdict"]["second"]["display_only"])   # D5: the holistic pick is display only
        self.assertNotIn("unclear_band", by_id["panel_verdict"]["thresholds"])   # no noul bar carried onto a choice
        self.assertEqual(by_id["blocker"]["second"]["aliases"], {"TRUE": "BLOCKER", "FALSE": "NOT_BLOCKER"})
        jev = load_jev_module()
        self.assertEqual(by_id["verify_cascade"]["text"], jev.VERIFY_INSTRUCTIONS)
        self.assertEqual(by_id["verify_cascade"]["options"], jev.VERIFY_CRITERIA)
        self.assertEqual(by_id["verify_cascade"]["thresholds"]["accept"], jev.DEFAULT_ACCEPT)
        self.assertEqual(by_id["addresses_task"]["text"], jev.VERIFY_TASK_INSTRUCTIONS)
        self.assertEqual(jev.VERIFY_TASK_QUESTION_ID, "addresses_task")
        self.assertEqual(sorted(by_id["go_act"]["checks"]), ["authorized", "recipient_matches", "right_artifact"])
        self.assertEqual((by_id["go_act"]["thresholds"]["approve_at"], by_id["go_act"]["thresholds"]["block_at"]),
                         (jev.DEFAULT_APPROVE_AT, jev.DEFAULT_BLOCK_AT))
        self.assertEqual(reg["defaults"], {"clear_bar": jev.JEV_CLEAR, "split": 0.5, "unclear_band": jev.UNCLEAR_BAND,
                                           "pick_p_top_floor": jev.PICK_P_TOP_FLOOR})
        with open(CORP_KIT_PATH) as fh:
            kit = fh.read()
        for side in ("true", "false"):   # the measured keep/reject criteria: kit constants == registry
            self.assertIn(by_id["keep_reject"]["criteria"][side], kit)
        for q in reg["questions"]:       # the kit's JEV_REGISTRY carries every text verbatim
            self.assertTrue(json.dumps(q["text"], ensure_ascii=False) in kit, f"corp-kit.js JEV_REGISTRY lacks {q['id']}")
            for name, prop in (q.get("checks") or {}).items():
                self.assertTrue(json.dumps(prop, ensure_ascii=False) in kit, f"corp-kit.js lacks {q['id']}.{name}")
        for option in by_id["panel_verdict"]["options"]:
            self.assertIn(option, ("READY", "NEEDS_EDITS", "NOT_READY", "UNCLEAR"))
        self.assertIn("UNCLEAR", by_id["class_pick"]["options"])
        self.assertIn("PAYER_DOC", by_id["class_pick"]["options"])
        self.assertIn("OTHER", by_id["class_pick"]["options"])

    def test_q_loads_the_registry_question(self):
        reg = {q["id"]: q for q in load_registry_file()["questions"]}
        r = self.run_jev(["filter", "--q", "keep_reject", "--all"], input_text=rows_jsonl([{"id": 1, "state": "Flag: x"}]))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.sent()["questions"]["q"], {"type": "noul", "instructions": reg["keep_reject"]["text"],
                                                         "criteria": reg["keep_reject"]["criteria"]})
        self.assertEqual(self.jsonl(r.stdout)[-1]["q"], "keep_reject")
        r = self.run_jev(["pick", "--q", "panel_verdict", "-s", "Closure contract: x · Failures: NONE"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.sent(1)["questions"]["q"]["criteria"], reg["panel_verdict"]["options"])
        self.assertEqual(json.loads(r.stdout)["q"], "panel_verdict")
        r = self.run_jev(["yes", "--q", "claim_support", "-s", "Claim: a. Source sentence: b."])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.sent(2)["questions"]["q"]["instructions"], reg["claim_support"]["text"])

    def test_q_misuse_exits_2_before_http(self):
        cases = [
            self.run_jev(["yes", "some question?", "--q", "claim_support", "-s", "s"]),
            self.run_jev(["yes", "--q", "no_such_question", "-s", "s"]),
            self.run_jev(["yes", "--q", "panel_verdict", "-s", "s"]),          # a choice question on yes
            self.run_jev(["pick", "--q", "claim_support", "-s", "s"]),         # a noul question on pick
            self.run_jev(["yes", "--q", "claim_support", "--true", "T", "--false", "F", "-s", "s"]),
            self.run_jev(["yes", "--q", "claim_support", "-s", "s"],
                         env=self.base_env(extra={"JEV_REGISTRY": self.write_tmp("broken.json", "{nope")})),
        ]
        for i, r in enumerate(cases):
            self.assertEqual(r.returncode, 2, f"case {i}: {r.stderr}")
        self.assertEqual(len(self.server.behavior["requests"]), 0)

    def test_ask_names_registry_questions_locate_in_one_request(self):
        # D6: LOCATE is registered -- a Choice over the page's line ids + NONE and an independent Noul, one request
        reg = {q["id"]: q for q in load_registry_file()["questions"]}
        lines = {"L1": "Line L1 of the page.", "L2": "Line L2 of the page."}
        req = {"state": {"claim": "10003 was denied 2,400 units.", "page": "L1 DECISION NOTICE\nL2 Total Units: Denied 2,400"},
               "questions": {"line": {"q": "locate_line", "options": lines}, "any": {"q": "locate_any"}}}
        r = self.run_jev(["ask", self.write_tmp("locate.json", json.dumps(req))])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.server.behavior["requests"]), 1)
        sent = self.sent()["questions"]
        self.assertEqual(sent["line"], {"type": "choice", "instructions": reg["locate_line"]["text"],
                                        "criteria": {**lines, "NONE": reg["locate_line"]["options"]["NONE"]}})
        self.assertEqual(list(sent["line"]["criteria"])[-1], "NONE")          # the registry's own option comes last
        self.assertEqual(sent["any"], {"type": "noul", "instructions": reg["locate_any"]["text"]})
        self.assertEqual(sorted(json.loads(r.stdout)["answers"]), ["any", "line"])

    def test_ask_registry_reference_misuse_exits_2_before_http(self):
        bad = [
            {"x": {"q": "locate_line"}},                                               # dynamic options missing
            {"x": {"q": "claim_support", "options": {"A": "a"}}},                      # fixed-option entry
            {"x": {"q": "locate_line", "options": {"NONE": "mine"}}},                  # clashes with the registry's
            {"x": {"q": "locate_line", "options": {}}},
            {"x": {"q": "claim_support", "instructions": "my own words?"}},            # text beside a registry id
            {"x": {"q": "go_act"}},                                                    # a gate is not an ask question
            {"x": {"q": "no_such_id"}},
        ]
        for questions in bad:
            with self.subTest(questions=questions):
                req = {"state": "s", "questions": questions}
                r = self.run_jev(["ask", self.write_tmp("bad.json", json.dumps(req))])
                self.assertEqual(r.returncode, 2, r.stderr)
        self.assertEqual(len(self.server.behavior["requests"]), 0)


class SecondTestCase(StubCase):
    """R4 P6: `jev second` applies §JEV's agreement rules in code from the registry."""

    def second(self, rows, env=None):
        r = self.run_jev(["second"], input_text=rows_jsonl(rows), env=env)
        lines = self.jsonl(r.stdout) if r.stdout.strip() else []
        return r, {row["id"]: row for row in lines if "id" in row}, (lines[-1] if lines else {})

    def test_noul_kinds_follow_the_rules(self):
        rows = [
            {"id": "c1", "kind": "claim", "state": "Claim: a. Source sentence: a. P=0.9", "verdict": "VERIFIED"},
            {"id": "c2", "kind": "claim", "state": "Claim: a. Source sentence: b. P=0.9", "verdict": "MISMATCH"},
            {"id": "c3", "kind": "claim", "state": "Claim: a. Source sentence: c. P=0.45", "verdict": "VERIFIED"},
            {"id": "c4", "kind": "claim", "state": "Claim: 3 + 4 = 7. Source sentence: n/a", "verdict": "ARITHMETIC"},
            {"id": "k1", "kind": "keep_reject", "state": "Flag: the date is wrong. P=0.55", "verdict": "KEEP"},
            {"id": "k2", "kind": "keep_reject", "state": "Flag: the total is wrong. P=0.8", "verdict": "keep"},
            {"id": "k3", "kind": "keep_reject", "state": "Flag: the name is wrong. P=0.8", "verdict": "REJECT"},
            {"id": "b1", "kind": "blocker", "state": "Defect: a typo in a footer. P=0.3", "verdict": "NOT_BLOCKER"},
            {"id": "b2", "kind": "blocker", "state": "Defect: the wrong member id. P=0.3", "verdict": "blocker"},
            {"id": "e1", "kind": "edit_kind", "state": "Edit: replace 5 with 6 in the table. P=0.95", "verdict": "mechanical"},
            {"id": "x1", "kind": "arithmetic", "state": "Total: 12 units", "verdict": "n/a"},
        ]
        r, out, summary = self.second(rows)
        self.assertEqual(r.returncode, 0, r.stderr)
        want = {"c1": ("agree", True), "c2": ("disagree", True), "c3": ("disagree", False),
                "c4": ("not_compared", False), "k1": ("unclear", False), "k2": ("agree", True),
                "k3": ("disagree", True), "b1": ("agree", False), "b2": ("disagree", False),
                "e1": ("agree", True), "x1": ("not_compared", False)}
        self.assertEqual({i: (out[i]["jev_agree"], out[i]["clear"]) for i in want}, want)
        self.assertEqual(out["c4"]["jev_margin"], 0)
        self.assertEqual(len(self.server.behavior["requests"]), 9)          # arithmetic and ARITHMETIC: no call
        for req in self.server.behavior["requests"]:                        # only the state rides; never a verdict
            self.assertNotIn("VERIFIED", json.dumps(req["state"]))
        reg = {q["id"]: q for q in load_registry_file()["questions"]}
        sent = {req["questions"]["q"]["instructions"] for req in self.server.behavior["requests"]}
        self.assertEqual(sent, {reg[k]["text"] for k in ("claim_support", "keep_reject", "blocker", "edit_kind")})
        self.assertEqual((summary["agree"], summary["disagree"], summary["unclear"], summary["not_compared"]), (4, 4, 1, 2))

    def test_f11_an_inferred_claim_is_a_claim_verdict_on_the_supported_side(self):
        # F11 (re-gate OPUS RG-06): the claim audit's INFERRED status -- the doctrine's attributed form -- is seconded
        # like VERIFIED (the source supports the sentence as worded) and never exits 2 as an unknown verdict
        rows = [{"id": "i1", "kind": "claim", "state": "Claim: The practice tracker shows 2,000 authorized hours "
                 "(the letter is not in our file). Source sentence: 10003 Authorized hours 2,000. P=0.9",
                 "verdict": "INFERRED"},
                {"id": "i2", "kind": "claim", "state": "Claim: The tracker shows 2,000. Source sentence: 1,040. P=0.1",
                 "verdict": "inferred"}]
        r, out, _ = self.second(rows)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual({i: out[i]["jev_agree"] for i in out}, {"i1": "agree", "i2": "disagree"})
        r, _, _ = self.second([{"id": "d1", "kind": "determination", "state": "Letter sentence: a. Draft sentence: a.",
                                "verdict": "INFERRED"}])
        self.assertEqual(r.returncode, 2)                                   # a determination is the letter's or nothing

    def test_panel_pick_is_display_only_and_never_compared(self):
        # D5: a seat's verdict is the worst of its own per-failure calls; the holistic pick is shown, never compared
        rows = [
            {"id": "p1", "kind": "panel", "state": {"closure": "ship it", "stub_choice": "READY", "stub_conf": 0.9},
             "verdict": "READY"},
            {"id": "p2", "kind": "panel", "state": {"closure": "ship it", "stub_choice": "READY", "stub_conf": 0.9},
             "verdict": "NOT_READY"},
            {"id": "p3", "kind": "panel", "state": {"closure": "ship it", "stub_choice": "UNCLEAR", "stub_conf": 0.9},
             "verdict": "READY"},
        ]
        r, out, summary = self.second(rows)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([out[i]["jev_agree"] for i in ("p1", "p2", "p3")], ["not_compared"] * 3)
        self.assertTrue(all(out[i]["display_only"] for i in ("p1", "p2", "p3")))
        self.assertEqual((out["p1"]["choice"], out["p1"]["p_top"], out["p1"]["clear"]), ("READY", 0.9, True))
        self.assertEqual(out["p3"]["choice"], "UNCLEAR")
        tally = ("jev: calls 3 · agree 0/0 · clear 0 · escalated 0 · disagreements none → upheld seat 0 / jev 0 · "
                 "unavailable 0 · not_compared 3")
        self.assertEqual(summary["tally"], tally)
        self.assertIn(tally, r.stderr)

    def test_escalated_counts_only_what_can_stand_measured_questions(self):
        # D5: only an agree + clear row on a MEASURED question may stand; a clear keep/reject agreement escalates
        rows = [
            {"id": "c1", "kind": "claim", "state": "Claim: a. Source sentence: a. P=0.95", "verdict": "VERIFIED"},
            {"id": "k1", "kind": "keep_reject", "state": "Flag: the total is wrong. P=0.95", "verdict": "KEEP"},
            {"id": "e1", "kind": "edit_kind", "state": "Edit: replace 5 with 6. P=0.95", "verdict": "MECHANICAL"},
        ]
        r, out, summary = self.second(rows)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual({i: (out[i]["jev_agree"], out[i]["clear"], out[i]["measured"]) for i in ("c1", "k1", "e1")},
                         {"c1": ("agree", True, True), "k1": ("agree", True, False), "e1": ("agree", True, False)})
        self.assertIn("agree 3/3 · clear 3 · escalated 2 ·", summary["tally"])

    def test_pmo_status_kind_and_severity_words_are_not_verdicts(self):
        rows = [
            {"id": "o1", "kind": "pmo_status", "state": "Item: payer letter pulled. Evidence: not in the folder. P=0.9",
             "verdict": "OPEN"},
            {"id": "o2", "kind": "pmo_status", "state": "Item: Reviewer signature. Evidence: signed 09/27. P=0.1",
             "verdict": "CLOSED"},
            {"id": "o3", "kind": "pmo_status", "state": "Item: portal access. Evidence: none shown. P=0.8",
             "verdict": "UNKNOWN"},
            {"id": "o4", "kind": "pmo_status", "state": "Item: the md5 receipt. Evidence: matches. P=0.9",
             "verdict": "CLOSED"},
        ]
        r, out, _ = self.second(rows)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([out[i]["jev_agree"] for i in ("o1", "o2", "o3", "o4")], ["agree", "agree", "agree", "disagree"])
        reg = {q["id"]: q for q in load_registry_file()["questions"]}
        self.assertEqual(self.sent()["questions"]["q"]["instructions"], reg["pmo_status"]["text"])
        for bad in ("low", "high", "medium"):     # S2-11: severity is never Jev-seconded, so it is not a verdict
            r = self.run_jev(["second"], input_text=rows_jsonl([{"id": 1, "kind": "blocker", "state": "Defect: x",
                                                                "verdict": bad}]))
            self.assertEqual(r.returncode, 2, bad)
        r, out, _ = self.second([{"id": "t", "kind": "blocker", "state": "Defect: y. P=0.9", "verdict": True}])
        self.assertEqual(out["t"]["jev_agree"], "agree")   # a boolean blocks call still maps (TRUE → BLOCKER)

    def test_non_english_state_is_unclear(self):
        rows = [{"id": "s1", "kind": "claim", "verdict": "VERIFIED",
                 "state": "Claim: el plan gratuito permite hasta 5 miembros por espacio. Source sentence: los "
                          "espacios gratuitos tienen hasta 5 miembros y 3 proyectos. P=0.95"}]
        r, out, _ = self.second(rows)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((out["s1"]["jev_agree"], out["s1"]["lang_hint"]), ("unclear", "non_en"))

    def test_unavailable_rows_are_unknown_and_counted(self):
        self.server.behavior["status"] = 503
        rows = [{"id": i, "kind": "claim", "state": f"Claim: {i}. Source sentence: {i}.", "verdict": "VERIFIED"}
                for i in range(2)]
        r = self.run_jev(["second", "--deadline", "1"], input_text=rows_jsonl(rows))
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = self.jsonl(r.stdout)
        for row in lines[:-1]:
            self.assertEqual((row["jev_agree"], row["jev_margin"], row["keep"], row["status"]),
                             ("unavailable", 0, None, "UNKNOWN"))
        self.assertIn("unavailable 2", lines[-1]["tally"])
        self.assertEqual(lines[-1]["complete"], False)

    def test_build_mismatch_is_flagged_and_tallied(self):
        self.server.behavior["resolved_model"] = "typesafe/jev-new-build"
        env = self.base_env(extra={"JEV_EXPECT_BUILD": "typesafe/jev-1.13-20260917"})
        r, out, summary = self.second([{"id": "c", "kind": "claim", "state": "Claim: a. Source sentence: a. P=0.9",
                                        "verdict": "VERIFIED"}], env=env)
        self.assertTrue(out["c"]["build_mismatch"])
        self.assertIn("build_mismatch 1", summary["tally"])
        self.assertIn("escalated 1", summary["tally"])                     # a mismatched clear agreement still escalates

    def test_bad_rows_exit_2_before_http_and_a_verdict_in_the_state_warns(self):
        cases = [
            [{"id": 1, "kind": "vibes", "state": "s", "verdict": "KEEP"}],
            [{"id": 1, "kind": "keep_reject", "state": "s", "verdict": "MAYBE"}],
            [{"id": 1, "kind": "panel", "state": "s", "verdict": "UNCLEAR"}],
            [{"id": 1, "kind": "claim", "state": "", "verdict": "VERIFIED"}],
            [{"id": 1, "kind": "claim", "state": "s", "verdict": "VERIFIED"}, {"id": 1, "kind": "claim", "state": "t", "verdict": "VERIFIED"}],
        ]
        for i, rows in enumerate(cases):
            r = self.run_jev(["second"], input_text=rows_jsonl(rows))
            self.assertEqual(r.returncode, 2, f"case {i}: {r.stderr}")
        self.assertEqual(len(self.server.behavior["requests"]), 0)
        r = self.run_jev(["second"], input_text=rows_jsonl([{"id": 1, "kind": "claim", "verdict": "VERIFIED",
                                                            "state": "Claim: a (VERIFIED). Source sentence: a."}]))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("contains its verdict", r.stderr)


class LogRotationTestCase(StubCase):

    def test_logs_move_aside_past_the_size_limit_and_nothing_is_lost(self):
        logdir = tempfile.TemporaryDirectory(prefix="jev_rot_")
        self.addCleanup(logdir.cleanup)
        usage = os.path.join(logdir.name, "usage.jsonl")
        env = self.base_env(extra={"JEV_USAGE_LOG": usage, "JEV_LOG_ROTATE_BYTES": "300"})
        for _ in range(4):
            self.assertEqual(self.run_jev(["yes", "q?", "-s", "state"], env=env).returncode, 0)
        files = sorted(os.listdir(logdir.name))
        rotated = [f for f in files if re.match(r"usage-\d{8}-\d{6}(-\d+)?\.jsonl$", f)]
        self.assertTrue(rotated, files)
        lines = 0
        for f in files:
            with open(os.path.join(logdir.name, f)) as fh:
                lines += sum(1 for line in fh if line.strip())
        self.assertEqual(lines, 4)                                   # moved, never deleted

    def test_rotation_never_clobbers_an_earlier_rotation(self):
        jev = load_jev_module()
        d = tempfile.TemporaryDirectory(prefix="jev_rot2_")
        self.addCleanup(d.cleanup)
        path = os.path.join(d.name, "judgments.jsonl")
        stamp = time.strftime("%Y%m%d-%H%M%S")
        taken = os.path.join(d.name, f"judgments-{stamp}.jsonl")
        with open(taken, "w") as fh:
            fh.write("earlier\n")
        with open(path, "w") as fh:
            fh.write("x" * 100 + "\n")
        os.environ["JEV_LOG_ROTATE_BYTES"] = "10"
        try:
            jev._rotate_if_big(path)
        finally:
            del os.environ["JEV_LOG_ROTATE_BYTES"]
        with open(taken) as fh:
            self.assertEqual(fh.read(), "earlier\n")                 # untouched
        moved = [f for f in os.listdir(d.name) if f.startswith(f"judgments-{stamp}-")]
        if not moved:   # the clock ticked past the pre-made stamp: the plain name was free
            moved = [f for f in os.listdir(d.name) if f.startswith("judgments-") and f != os.path.basename(taken)]
        self.assertEqual(len(moved), 1)
        self.assertFalse(os.path.exists(path))


class Wave2PureRulesTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.jev = load_jev_module()

    def test_constants(self):
        self.assertEqual(self.jev.BULK_WORKERS, 6)
        self.assertIn(408, self.jev.RETRY_STATUSES)
        self.assertEqual((self.jev.ATTEMPT_TIMEOUT_S, self.jev.BACKOFF_JITTER, self.jev.PACKING_VERSION), (20.0, 0.25, 2))

    def test_jitter_takes_0_to_25_percent_off(self):
        self.assertEqual(self.jev.jittered(4.0, rnd=lambda: 0.0), 4.0)
        self.assertEqual(self.jev.jittered(4.0, rnd=lambda: 1.0), 3.0)
        for _ in range(200):
            self.assertTrue(0.75 <= self.jev.jittered(1.0) <= 1.0)

    def test_bulk_run_accounts_for_every_row(self):
        jev = self.jev

        def call(item):
            if item == "auth":
                raise jev.JevAuthError("http 401")
            if item == "bad":
                raise jev.JevError("http 422")
            return item.upper()

        results, stop = jev.bulk_run(["a", "bad", "b"], call, key="k")
        self.assertEqual([r[0] for r in results], ["A", None, "B"])
        self.assertIsNone(stop)
        self.assertEqual(jev.failure_code(results[1][1]), "bad_call")
        results, stop = jev.bulk_run(["a"] * 3, call, key=None)
        self.assertEqual([jev.failure_code(e) for _, e in results], ["no_key"] * 3)
        self.assertIsInstance(stop, jev.JevNoKey)

    def test_breaker_opens_after_a_run_of_unavailable_rows(self):
        jev = self.jev
        calls = []

        def down(item):
            calls.append(item)
            time.sleep(0.02)
            raise jev.JevUnavailable("http 503")

        results, stop = jev.bulk_run(list(range(40)), down, key="k")
        self.assertIsNone(stop)                                     # unavailable never stops the run...
        self.assertEqual(len(results), 40)
        not_sent = [i for i, (_, e) in enumerate(results) if isinstance(e, jev.JevNotSent)]
        self.assertTrue(not_sent)                                   # ...but the breaker stops sending
        self.assertFalse(set(not_sent) & set(calls))
        self.assertEqual({jev.failure_code(e) for _, e in results}, {"unavailable"})

    def test_lang_hint(self):
        hint = self.jev.lang_hint
        self.assertEqual(hint("Claim: The Free plan allows up to 5 members. Source sentence: Free workspaces have "
                              "up to 5 members and 3 projects."), "en")
        self.assertEqual(hint("El plan gratuito permite hasta 5 miembros y los proyectos son ilimitados."), "non_en")
        self.assertEqual(hint("The member lives in Los Angeles and was seen at the clinic in El Paso on Monday."), "en")
        self.assertEqual(hint("Guardian: Maria de la Cruz, who signed the consent form for the member."), "en")
        self.assertEqual(hint("会员在免费计划中最多可以添加五名成员。"), "non_en")
        self.assertEqual(hint({"claim": "Le plan est gratuit pour les membres", "source": "Les membres sont dans une équipe"}),
                         "non_en")
        self.assertEqual(hint("ok"), "en")

    def test_f6_lang_hint_ignores_paths_urls_and_digests(self):
        hint = self.jev.lang_hint
        state = {"go": {"reply": "GO 3", "row": {"target": "/var/folders/x/T/jev_go_el_los/share/Appeal 10.2026",
                                                  "files": {"/var/folders/x/T/jev_go_el_los/v2/a.pdf": "d8632b71b0eba7312db83ba78194560e"}}},
                 "act": {"src": "./el/los/las", "files": ["~/que/una/por/a.pdf", "C:\\el\\los\\a.pdf",
                                                           "smb://srv/el/los/las/del"]},
                 "deliverable": {"name": "appeal", "description": "the appeal letter for the plan"}}
        self.assertEqual(hint(state), "en")
        self.assertEqual(hint("deploy it to /var/folders/x/T/jev_go_el_los_las/share/Appeal please, see "
                              "https://agency.example/el/los/las/del and corp/el/los/receipts/util.md, md5 "
                              "d8632b71b0eba7312db83ba78194560e"), "en")
        self.assertEqual(hint({"description": "la carta de apelación para el plan con las horas", "path": "/w/a.pdf"}),
                         "non_en")                                              # the words still count

    def test_question_limits(self):
        qp = self.jev.question_problem
        self.assertIsNone(qp("a", {"type": "noul", "instructions": "x?"}))
        self.assertIsNone(qp("a", {"type": "noul", "instructions": "x?", "criteria": {}}))
        self.assertIsNotNone(qp("a", {"type": "noul", "instructions": "x?", "criteria": {"true": "T"}}))
        self.assertIsNone(qp("a", {"type": "choice", "instructions": "x?", "criteria": {f"o{i}": None for i in range(255)}}))
        self.assertIsNotNone(qp("a", {"type": "choice", "instructions": "x?", "criteria": {f"o{i}": None for i in range(256)}}))
        self.assertIsNone(qp("a", {"type": "score", "instructions": "x?", "criteria": ["l1", "l2"]}))
        self.assertIsNotNone(qp("a", {"type": "score", "instructions": "x?", "criteria": ["l1"]}))
        self.assertIsNotNone(qp("a", {"type": "score", "instructions": "x?", "criteria": [str(i) for i in range(11)]}))
        self.assertIsNotNone(qp("a", {"type": "noul", "instructions": ""}))



class GoActPureRulesTestCase(unittest.TestCase):
    """E12 / FB-04 / E5 helpers, pure: the row's file forms, the reply rules."""

    @classmethod
    def setUpClass(cls):
        cls.jev = load_jev_module()

    def test_row_files_reads_every_form_the_owner_queue_writes(self):
        h1, h2 = "a" * 32, "b" * 32
        want = {"/w/a.pdf": h1, "/w/b.pdf": h2}
        self.assertEqual(self.jev.row_files({"files": want}), want)
        self.assertEqual(self.jev.row_files({"files": [f"/w/a.pdf · `{h1}`", f"/w/b.pdf · {h2}"]}), want)
        self.assertEqual(self.jev.row_files({"files": [{"path": "/w/a.pdf", "md5": h1}, {"path": "/w/b.pdf", "md5": h2}]}), want)
        self.assertEqual(self.jev.row_files({"artifact": "/w/a.pdf", "md5": h1}), {"/w/a.pdf": h1})
        self.assertEqual(self.jev.row_files({"files": ["/w/a.pdf"]}), {"/w/a.pdf": ""})    # no md5: the gate blocks it

    def test_parse_go_and_reply_names_act(self):
        self.assertEqual(self.jev.parse_go(" go 2 , 5. "), ["2", "5"])
        self.assertIsNone(self.jev.parse_go("yes, ship it"))
        row = {"verb": "deploy", "target": "/Volumes/S/Appeal 10.2026", "recipient": "n/a", "record_id": "PA 77"}
        self.assertTrue(self.jev.reply_names_act("Deploy  it to /Volumes/S/Appeal 10.2026 for PA 77", row))
        self.assertFalse(self.jev.reply_names_act("deploy it to /Volumes/S/Appeal 10.2026", row))   # record id unnamed

if __name__ == "__main__":
    unittest.main()
