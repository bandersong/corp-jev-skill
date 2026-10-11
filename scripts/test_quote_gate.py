"""Unit tests for quote-gate (pure code: no Jev, no network).

Run with: python3 -m unittest test_quote_gate -v   (from this directory)
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
QUOTE_GATE = os.path.join(HERE, "quote-gate")

LETTER = ("DECISION NOTICE - PARTIAL DENIAL.\n"
          "10003 Standard service without modification — From 3/04/26 Thru 9/02/26 — Total Units:\n"
          "Approved 240. Review Outcome: Modified.\f"
          "Page two. The member’s “authori-\nzation” was reﬁled on 3/1/26 for a follow-\n"
          "up visit.  Reviewer:   Dr.  Smith.\f")


class QuoteGateTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="quote_gate_")
        self.addCleanup(self.tmp.cleanup)
        with open(os.path.join(self.tmp.name, "letter.txt"), "w", encoding="utf-8") as fh:
            fh.write(LETTER)
        self.docs = os.path.join(self.tmp.name, "map.json")
        with open(self.docs, "w") as fh:
            json.dump({"letter": "letter.txt", "gone": "missing.txt"}, fh)   # relative to map.json's folder

    def gate(self, rows, docs=None, raw=None):
        text = raw if raw is not None else "".join(json.dumps(r) + "\n" for r in rows)
        r = subprocess.run([sys.executable, QUOTE_GATE, "--docs", docs or self.docs], input=text,
                           capture_output=True, text=True, timeout=30)
        lines = [json.loads(line) for line in r.stdout.splitlines() if line.strip()]
        return r, {row["id"]: row for row in lines if "id" in row}, (lines[-1] if lines else {})

    def row(self, rid, quote, page=1, doc="letter"):
        return {"id": rid, "claim": "…", "doc": doc, "page": page, "quote": quote}

    def test_exact_and_normalized_quotes_pass(self):
        r, out, summary = self.gate([
            self.row("a", "Total Units: Approved 240."),
            self.row("b", "10003 Standard service without modification - From 3/04/26"),   # em dash vs hyphen
            self.row("c", "The member's \"authorization\" was refiled on 3/1/26", page=2),     # curly, hyphen, ligature
            self.row("d", "for a follow-up visit. Reviewer: Dr. Smith.", page=2),              # kept hyphen, NBSP, spaces
            self.row("e", '"Review Outcome: Modified."'),                                         # wrapping quotes
            self.row(7, "Approved 240", page="1"),                                               # int id, page as text
        ])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual({k: v["status"] for k, v in out.items()}, {k: "QUOTE_OK" for k in ("a", "b", "c", "d", "e", 7)})
        self.assertEqual(summary, {"summary": True, "total": 6, "quote_ok": 6, "miscited": 0, "payer": False})

    def test_quote_on_another_page_names_that_page(self):
        r, out, summary = self.gate([self.row("w", "was refiled on 3/1/26", page=1)])
        self.assertEqual(r.returncode, 1)
        self.assertEqual((out["w"]["status"], out["w"]["found_on_page"]), ("MISCITED", 2))
        self.assertIn("not page 1", out["w"]["reason"])
        self.assertEqual(summary["miscited"], 1)

    def test_a_near_miss_never_passes_and_carries_the_closest_span(self):
        r, out, _ = self.gate([self.row("n", "Review Outcome: Reversed."),
                               self.row("c", "review outcome: modified.")])            # case differs
        self.assertEqual(r.returncode, 1)
        for rid in ("n", "c"):
            self.assertEqual(out[rid]["status"], "MISCITED")
            self.assertEqual(out[rid]["near_match"]["page"], 1)
        self.assertIn("Review Outcome", out["n"]["near_match"]["text"])
        self.assertGreater(out["c"]["near_match"]["ratio"], 0.8)
        self.assertLess(out["n"]["near_match"]["ratio"], 1.0)

    def test_nothing_close_gives_a_null_near_match(self):
        r, out, _ = self.gate([self.row("z", "zebra quantum lattice")])
        self.assertEqual((r.returncode, out["z"]["status"], out["z"]["near_match"]), (1, "MISCITED", None))

    def test_a_page_that_does_not_exist_and_an_unmapped_doc(self):
        r, out, _ = self.gate([self.row("p", "Approved 240", page=3), self.row("u", "Approved 240", doc="other")])
        self.assertEqual(r.returncode, 1)
        self.assertIn("page 3 does not exist (letter has 2 pages)", out["p"]["reason"])   # the trailing \f is not a page
        self.assertEqual(out["p"]["found_on_page"], 1)
        self.assertEqual(out["u"]["status"], "MISCITED")
        self.assertIn("not in the --docs map", out["u"]["reason"])

    def test_bad_input_exits_2(self):
        good = self.row("a", "Approved 240")
        cases = [
            self.gate([], raw="{not json\n")[0],
            self.gate([good, dict(good)])[0],                                  # duplicate id
            self.gate([dict(good, page=0)])[0],
            self.gate([dict(good, quote="  ")])[0],
            self.gate([dict(good, doc="gone")])[0],                            # mapped, but the text file is missing
            self.gate([good], docs=os.path.join(self.tmp.name, "nope.json"))[0],
            self.gate([], raw="")[0],
        ]
        for i, r in enumerate(cases):
            self.assertEqual(r.returncode, 2, f"case {i}: {r.stderr}")



DENIAL = "10003 Total Units: Approved 240 Denied 2,400 of 2,640 requested. Review Outcome: Modified.\f"
TRACKER = "10003 authorized 2,000 for the period\f"
CLAIMS = "code,date,units\n103,2026-03-01,8\n103,2026-03-02,8\n105,2026-03-02,4\n"


class RoleValueAndReceiptTestCase(unittest.TestCase):
    """CEO decisions E1 (receipts are chains: every input carries its own pointer and role) and E2 (authority class)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="quote_gate_e1_")
        self.addCleanup(self.tmp.cleanup)
        for name, text in (("denial.txt", DENIAL), ("tracker.txt", TRACKER), ("claims.csv", CLAIMS)):
            with open(os.path.join(self.tmp.name, name), "w", encoding="utf-8") as fh:
                fh.write(text)
        self.docs = os.path.join(self.tmp.name, "map.json")
        with open(self.docs, "w") as fh:
            json.dump({"denial": {"text": "denial.txt", "class": "LETTER"},
                       "tracker": {"text": "tracker.txt", "class": "TRACKER"},
                       "claims": {"text": "claims.csv", "class": "CLAIMS"}}, fh)

    def run_gate(self, *args, rows=None):
        text = "".join(json.dumps(r) + "\n" for r in rows) if rows is not None else ""
        r = subprocess.run([sys.executable, QUOTE_GATE, "--docs", self.docs, *args], input=text,
                           capture_output=True, text=True, timeout=30, cwd=self.tmp.name)
        lines = [json.loads(line) for line in r.stdout.splitlines() if line.strip()]
        return r, lines

    def receipt(self, name, body):
        path = os.path.join(self.tmp.name, "receipts", name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        return path

    def test_value_and_role_on_a_quote_catch_the_role_swap(self):
        q = "Total Units: Approved 240 Denied 2,400 of 2,640 requested"
        # map.json carries classes, so --payer is on by itself (F12): every quote row carries its drafted sentence
        rows = [{"id": "ok_auth", "claim": "The plan approved 240 units.", "doc": "denial", "page": 1, "quote": q,
                 "role": "authorized", "value": "240"},
                {"id": "swap", "claim": "The plan approved 2,400 units.", "doc": "denial", "page": 1, "quote": q,
                 "role": "authorized", "value": "2,400"},
                {"id": "ok_denied", "claim": "2,400 units were denied.", "doc": "denial", "page": 1, "quote": q,
                 "role": "denied", "value": "2400"},
                {"id": "ok_req", "claim": "The provider requested 2,640 units.", "doc": "denial", "page": 1, "quote": q,
                 "role": "requested", "value": "2,640"},
                {"id": "not_held", "claim": "The plan approved 1,200 units.", "doc": "denial", "page": 1, "quote": q,
                 "role": "authorized", "value": "1,200"},
                {"id": "no_word", "claim": "The units were denied.", "doc": "denial", "page": 1,
                 "quote": "Review Outcome: Modified.", "role": "denied"}]
        r, lines = self.run_gate(rows=rows)
        out = {x["id"]: x for x in lines if "id" in x}
        self.assertEqual(r.returncode, 1)
        self.assertEqual({k: v["status"] for k, v in out.items()},
                         {"ok_auth": "QUOTE_OK", "swap": "MISCITED", "ok_denied": "QUOTE_OK", "ok_req": "QUOTE_OK",
                          "not_held": "MISCITED", "no_word": "MISCITED"})
        self.assertIn("gives '2,400' as denied", out["swap"]["reason"])
        self.assertIn("does not hold the value", out["not_held"]["reason"])
        self.assertIn("carries no denied word", out["no_word"]["reason"])

    def unclassed_map(self):
        path = os.path.join(self.tmp.name, "plain.json")
        with open(path, "w") as fh:
            json.dump({"denial": "denial.txt", "tracker": "tracker.txt", "claims": "claims.csv"}, fh)
        return path

    def test_payer_mode_takes_an_authorized_figure_only_from_a_letter(self):
        row = {"id": "t", "claim": "The tracker shows 2,000 authorized.", "doc": "tracker", "page": 1,
               "quote": "10003 authorized 2,000", "role": "authorized", "value": "2,000"}
        r = subprocess.run([sys.executable, QUOTE_GATE, "--docs", self.unclassed_map()], input=json.dumps(row) + "\n",
                           capture_output=True, text=True, timeout=30)
        lines = [json.loads(x) for x in r.stdout.splitlines() if x.strip()]
        self.assertEqual((r.returncode, lines[0]["status"], lines[-1]["payer"]), (0, "QUOTE_OK", False))   # the quote IS on the page …
        r, lines = self.run_gate("--payer", rows=[row])
        self.assertEqual((r.returncode, lines[0]["status"]), (1, "MISCITED"))          # … but a tracker is no letter
        self.assertIn("TRACKER", lines[0]["reason"])

    def test_payer_mode_quotes_the_letters_own_determination_verb(self):
        # doctrine rule 2 / E8: "modified" recorded as "reversed" for a day -- the claim's verb must be the quote's
        rows = [{"id": "rev", "claim": "Acme Review Org reversed the reduction at reconsideration.", "doc": "denial", "page": 1,
                 "quote": "Review Outcome: Modified."},
                {"id": "mod", "claim": "At reconsideration the outcome was modified.", "doc": "denial", "page": 1,
                 "quote": "Review Outcome: Modified."},
                {"id": "auth", "claim": "The plan authorized 240 units.", "doc": "denial", "page": 1,
                 "quote": "Total Units: Approved 240", "role": "authorized", "value": "240"},
                {"id": "part", "claim": "The request was partially approved.", "doc": "denial", "page": 1,
                 "quote": "Denied 2,400 of 2,640 requested"}]
        r, lines = self.run_gate("--payer", rows=rows)
        out = {x["id"]: x for x in lines if "id" in x}
        self.assertEqual({k: v["status"] for k, v in out.items()},
                         {"rev": "MISCITED", "mod": "QUOTE_OK", "auth": "QUOTE_OK", "part": "MISCITED"})
        self.assertIn("the claim says reduced, reversed but the quote's own verb is modified", out["rev"]["reason"])
        r = subprocess.run([sys.executable, QUOTE_GATE, "--docs", self.unclassed_map()],     # no classes, no --payer:
                           input=json.dumps(rows[0]) + "\n", capture_output=True, text=True, timeout=30)   # not checked
        self.assertEqual(json.loads(r.stdout.splitlines()[0])["status"], "QUOTE_OK")
        r, lines = self.run_gate(rows=rows[:1])                                         # classes: --payer is on (F12)
        self.assertEqual((lines[0]["status"], lines[-1]["payer"], lines[-1]["payer_auto"]), ("MISCITED", True, True))

    def test_claims_export_rows_prove_delivery_never_entitlement(self):
        rows = [{"id": "one", "doc": "claims", "row": 2, "role": "used", "value": "8"},
                {"id": "range", "doc": "claims", "row": "2-3", "role": "used"},
                {"id": "entitled", "doc": "claims", "row": 2, "role": "authorized", "value": "8"},
                {"id": "gone", "doc": "claims", "row": 9, "role": "used"},
                {"id": "wrong", "doc": "claims", "row": 4, "role": "used", "value": "8"}]
        r, lines = self.run_gate(rows=rows)
        out = {x["id"]: x for x in lines if "id" in x}
        self.assertEqual({k: v["status"] for k, v in out.items()},
                         {"one": "ROW_OK", "range": "ROW_OK", "entitled": "MISCITED", "gone": "MISCITED",
                          "wrong": "MISCITED"})
        self.assertIn("proves delivery, never entitlement", out["entitled"]["reason"])
        self.assertIn("row 9 does not exist", out["gone"]["reason"])

    def test_a_receipt_is_a_chain_every_input_checked(self):
        good = self.receipt("util.md", "# util-10003\n## inputs\n- used: [src: claims:2-3]\n"
                            "- authorized: 240 [src: denial p.1 \"Total Units: Approved 240\"]\n"
                            "## formula\nsum(units of the rows) / authorized × 100\n## result\n5.1%\n")
        r, lines = self.run_gate("--receipts", good, "--payer")
        recs = [x for x in lines if "sourced" in x]
        self.assertEqual((r.returncode, recs[0]["status"], recs[0]["sourced"]), (0, "RECEIPT_OK", 3), lines)
        self.assertEqual(lines[-1], {"summary": True, "receipts": 1, "receipts_ok": 1, "miscited": 0,
                                     "not_computation": 0, "inputs": 2, "inputs_ok": 2, "payer": True})

    def test_the_tracker_denominator_never_ships_under_payer(self):
        # FA-01's walk: 1,384 / 2,000 with the 2,000 copied from the practice tracker
        bad = self.receipt("util.md", "## inputs\n- used: 1,384 [src: claims:2]\n"
                           "- authorized: 2,000 [src: tracker p.1 \"10003 authorized 2,000\"]\n"
                           "## formula\nused / authorized × 100\n## result\n69.2%\n")
        r, lines = self.run_gate("--receipts", bad, "--payer")
        recs = [x for x in lines if "sourced" in x]
        self.assertEqual((r.returncode, recs[0]["status"]), (1, "MISCITED"))
        joined = " ".join(recs[0]["reasons"])
        self.assertIn("does not hold the value '1,384'", joined)                      # row 2 holds 8, not 1,384
        self.assertIn("TRACKER", joined)

    def test_a_look_up_is_not_a_computation(self):
        lookup = self.receipt("auth.md", "## inputs\n- authorized: 240 [src: denial p.1 \"Approved 240\"]\n"
                              "## formula\nauthorized\n## result\n312\n")
        r, lines = self.run_gate("--receipts", lookup)
        rec = [x for x in lines if "sourced" in x][0]
        self.assertEqual((r.returncode, rec["status"]), (1, "NOT_A_COMPUTATION"))
        self.assertIn("carries [src:", rec["reasons"][-1])
        dated = self.receipt("dated.md", "## inputs\n- authorized: 240 [src: denial p.1 \"Approved 240\"]\n"
                             "- used: [src: claims:2-3]\n## formula\nauthorized for 3/04/26-9/02/26, rows 2-40, p.1\n")
        rec = [x for x in self.run_gate("--receipts", dated)[1] if "sourced" in x][0]
        self.assertEqual(rec["status"], "NOT_A_COMPUTATION")                    # a date, a range or a page is no operation

    def test_every_input_line_must_parse_and_carry_its_pointer(self):
        cases = {"nopointer.md": "## inputs\n- authorized: 240 (from the letter)\n- used: [src: claims:2-3]\n## formula\na+b\n",
                 "norole.md": "## inputs\n- 240 [src: denial p.1 \"Approved 240\"]\n- used: [src: claims:2-3]\n## formula\na+b\n",
                 "badrole.md": "## inputs\n- allowed: 240 [src: denial p.1 \"Approved 240\"]\n- used: [src: claims:2-3]\n## formula\na+b\n",
                 "novalue.md": "## inputs\n- authorized: [src: denial p.1 \"Approved 240\"]\n- used: [src: claims:2-3]\n## formula\na+b\n",
                 "noinputs.md": "## formula\n312 + 8\n"}
        for name, body in cases.items():
            with self.subTest(name=name):
                r, lines = self.run_gate("--receipts", self.receipt(name, body))
                rec = [x for x in lines if "sourced" in x][0]
                self.assertEqual((r.returncode, rec["status"]), (1, "MISCITED"), rec)

    def test_a_calc_input_is_checked_recursively_and_must_equal_its_result(self):
        self.receipt("used.md", "## inputs\n- used: 8 [src: claims:2]\n- used: 8 [src: claims:3]\n"
                     "## formula\n8 + 8\n## result\n16\n")
        ok = self.receipt("util.md", "## inputs\n- used: 16 [calc: receipts/used.md]\n"
                          "- authorized: 240 [src: denial p.1 \"Approved 240\"]\n## formula\nused / authorized\n")
        r, lines = self.run_gate("--receipts", ok)
        self.assertEqual(r.returncode, 0, lines)
        self.assertTrue(any(x.get("status") == "CALC_OK" for x in lines))
        wrong = self.receipt("util2.md", "## inputs\n- used: 17 [calc: receipts/used.md]\n"
                             "- authorized: 240 [src: denial p.1 \"Approved 240\"]\n## formula\nused / authorized\n")
        r, lines = self.run_gate("--receipts", wrong)
        rec = [x for x in lines if "sourced" in x and x["receipt"].endswith("util2.md")][0]
        self.assertEqual((r.returncode, rec["status"]), (1, "MISCITED"))
        self.assertIn("is not the result of", " ".join(rec["reasons"]))
        self.receipt("a.md", "## inputs\n- used: 1 [calc: receipts/b.md]\n- used: 8 [src: claims:2]\n## formula\na+b\n")
        cyc = self.receipt("b.md", "## inputs\n- used: 1 [calc: receipts/a.md]\n- used: 8 [src: claims:3]\n## formula\na+b\n")
        r, lines = self.run_gate("--receipts", cyc)
        self.assertEqual(r.returncode, 1)
        self.assertTrue(any("cycle" in " ".join(x.get("reasons", [])) for x in lines if "sourced" in x), lines)

    # --- INTEGRATION 3: re-gate FABLE-A RG-04 (F12), RG-06, RG-07, RG-08; OPUS RG-06 (F11) ---------------------------

    def test_f12_payer_turns_itself_on_when_the_map_carries_classes(self):
        # FABLE-A RG-04: the a domain skill core, departments and COMMON named the receipts check without the flag; a tracker
        # denominator was RECEIPT_OK whenever the flag was forgotten
        bad = self.receipt("util.md", "## inputs\n- used: [src: claims:2-3]\n"
                           "- authorized: 2,000 [src: tracker p.1 \"10003 authorized 2,000\"]\n"
                           "## formula\nsum / authorized × 100\n## result\n0.8%\n")
        r, lines = self.run_gate("--receipts", bad)                                   # no --payer on the command line
        self.assertEqual((r.returncode, lines[-1]["payer"], lines[-1]["payer_auto"]), (1, True, True))
        self.assertIn("--payer is on (F12)", r.stderr)
        self.assertIn("TRACKER", " ".join(x for rec in lines if "sourced" in rec for x in rec["reasons"]))

    def test_rg06_under_payer_every_quote_row_carries_its_claim(self):
        # FABLE-A repro-d: {"id": "noclaim", ...} was QUOTE_OK while the same row with its sentence was MISCITED
        noclaim = {"id": "noclaim", "doc": "denial", "page": 1, "quote": "Review Outcome: Modified."}
        withclaim = dict(noclaim, id="withclaim", claim="Acme Review Org reversed the reduction.")
        blank = dict(noclaim, id="blank", claim="  ")
        r, lines = self.run_gate("--payer", rows=[noclaim, withclaim, blank])
        out = {x["id"]: x for x in lines if "id" in x}
        self.assertEqual({k: v["status"] for k, v in out.items()},
                         {"noclaim": "MISCITED", "withclaim": "MISCITED", "blank": "MISCITED"})
        self.assertIn("no claim on the row", out["noclaim"]["reason"])
        self.assertIn("the quote's own verb is modified", out["withclaim"]["reason"])
        ok = dict(noclaim, id="ok", claim="At reconsideration the outcome was modified.")
        r, lines = self.run_gate("--payer", rows=[ok])
        self.assertEqual((r.returncode, lines[0]["status"]), (0, "QUOTE_OK"))
        # a receipt input is a figure in a chain, not a drafted sentence: it never needs a claim
        rec = self.receipt("ok.md", "## inputs\n- used: [src: claims:2-3]\n- authorized: 240 [src: denial p.1 "
                           "\"Approved 240\"]\n## formula\nsum / authorized\n## result\n5.1%\n")
        self.assertEqual(self.run_gate("--receipts", rec, "--payer")[0].returncode, 0)

    def test_rg07_a_denied_figure_comes_from_the_letter_too(self):
        # FABLE-A repro-e: a denied 1,300 from the tracker was QUOTE_OK as a row and RECEIPT_OK as an input
        tracker2 = os.path.join(self.tmp.name, "tracker.txt")
        with open(tracker2, "w", encoding="utf-8") as fh:
            fh.write("10003 authorized 2,000 denied 1,300 for the period\f")
        row = {"id": "den_tracker", "claim": "The tracker shows 1,300 units denied.", "doc": "tracker", "page": 1,
               "quote": "10003 authorized 2,000 denied 1,300", "role": "denied", "value": "1,300"}
        r, lines = self.run_gate("--payer", rows=[row])
        self.assertEqual((r.returncode, lines[0]["status"]), (1, "MISCITED"))
        self.assertIn("authorized or denied figure comes from the payer's LETTER", lines[0]["reason"])
        cut = self.receipt("cut.md", "## inputs\n- denied: 1,300 [src: tracker p.1 \"10003 authorized 2,000 denied "
                           "1,300\"]\n- authorized: 240 [src: denial p.1 \"Approved 240\"]\n## formula\n"
                           "denied / (denied + authorized) × 100\n## result\n81.2%\n")
        r, lines = self.run_gate("--receipts", cut, "--payer")
        rec = [x for x in lines if "sourced" in x][0]
        self.assertEqual((r.returncode, rec["status"]), (1, "MISCITED"))
        self.assertIn("TRACKER", " ".join(rec["reasons"]))

    def test_opus_rg06_an_inferred_figure_passes_only_as_role_other(self):
        # OPUS's inferred/ fixture: the doctrine's INFERRED sentence attributes the tracker and names the missing letter
        claim = ("The practice tracker shows 2,000 authorized hours for 10003 (the letter for this cycle is not in "
                 "our file).")
        with open(os.path.join(self.tmp.name, "tracker.txt"), "w", encoding="utf-8") as fh:
            fh.write("Acme tracker export 09/2026\nClient A 10003 Authorized hours 2,000 for 04/01-09/30\f")
        rows = [{"id": "inferred-other", "claim": claim, "doc": "tracker", "page": 1,
                 "quote": "10003 Authorized hours 2,000", "value": "2,000", "role": "other"},
                {"id": "inferred-authorized", "claim": claim, "doc": "tracker", "page": 1,
                 "quote": "10003 Authorized hours 2,000", "value": "2,000", "role": "authorized"}]
        r, lines = self.run_gate("--payer", rows=rows)
        out = {x["id"]: x["status"] for x in lines if "id" in x}
        self.assertEqual(out, {"inferred-other": "QUOTE_OK", "inferred-authorized": "MISCITED"})

    def test_rg08_the_drafted_figure_is_its_receipts_result(self):
        self.receipt("util.md", "## inputs\n- used: [src: claims:2-3]\n- authorized: 240 [src: denial p.1 "
                     "\"Approved 240\"]\n## formula\nsum / authorized × 100\n## result\n5.1%\n")
        rows = [{"id": "right", "calc": "receipts/util.md", "value": "5.1%"},
                {"id": "transposed", "calc": "receipts/util.md", "value": "1.5%"},
                {"id": "gone", "calc": "receipts/none.md", "value": "5.1%"}]
        r, lines = self.run_gate(rows=rows)
        out = {x["id"]: x for x in lines if "id" in x}
        self.assertEqual({k: v["status"] for k, v in out.items()},
                         {"right": "CALC_OK", "transposed": "MISCITED", "gone": "MISCITED"})
        self.assertIn("'1.5%' is not the result of receipts/util.md ('5.1%')", out["transposed"]["reason"])
        self.assertEqual(r.returncode, 1)
        # --drafts: the code finds every "<figure> [calc: …]" itself, so no row can be forgotten
        drafts = os.path.join(self.tmp.name, "drafts.jsonl")
        with open(drafts, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"id": "u1", "draft": "Utilization was 5.1% [calc: receipts/util.md] of the "
                                                    "authorization."}) + "\n")
            fh.write(json.dumps({"id": "u2", "draft": "Utilization was 7.9% [calc: receipts/util.md] of it."}) + "\n")
            fh.write(json.dumps({"id": "u3", "draft": "Utilization [calc: receipts/util.md] was low."}) + "\n")
        r, lines = self.run_gate("--drafts", drafts)
        out = {x["id"]: x for x in lines if "id" in x}
        self.assertEqual({k: v["status"] for k, v in out.items()},
                         {"u1#calc1": "CALC_OK", "u2#calc1": "MISCITED", "u3#calc1": "MISCITED"})
        self.assertIn("no figure right before it", out["u3#calc1"]["reason"])
        self.assertEqual((r.returncode, lines[-1]["total"], lines[-1]["miscited"]), (1, 3, 2))
        # a receipt that fails its own checks fails the figure
        self.receipt("look.md", "## inputs\n- authorized: 240 [src: denial p.1 \"Approved 240\"]\n## formula\n"
                     "authorized\n## result\n312\n")
        r, lines = self.run_gate(rows=[{"id": "lookup", "calc": "receipts/look.md", "value": "240"}])
        self.assertEqual((r.returncode, lines[0]["status"], lines[0]["receipt_status"]), (1, "MISCITED", "NOT_A_COMPUTATION"))
        # bad input: a calc row with no value, and two modes at once
        r, _ = self.run_gate(rows=[{"id": "x", "calc": "receipts/util.md"}])
        self.assertEqual(r.returncode, 2)
        r, _ = self.run_gate("--drafts", drafts, "--receipts", os.path.join(self.tmp.name, "receipts"))
        self.assertEqual(r.returncode, 2)

    def test_a_folder_of_receipts_and_bad_input(self):
        self.receipt("util.md", "## inputs\n- used: [src: claims:2-3]\n- authorized: 240 [src: denial p.1 \"Approved 240\"]\n"
                     "## formula\nsum / authorized\n")
        r, lines = self.run_gate("--receipts", os.path.join(self.tmp.name, "receipts"))
        self.assertEqual((r.returncode, lines[-1]["receipts"]), (0, 1))
        self.assertEqual(self.run_gate("--receipts", os.path.join(self.tmp.name, "nope"))[0].returncode, 2)
        with open(self.docs, "w") as fh:
            json.dump({"denial": {"text": "denial.txt", "class": "PAYER"}}, fh)            # not an E2 class
        self.assertEqual(self.run_gate("--receipts", os.path.join(self.tmp.name, "receipts"))[0].returncode, 2)


if __name__ == "__main__":
    unittest.main()
