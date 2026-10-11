#!/usr/bin/env python3
"""Builds the synthetic re-gate golden set: regate_items.jsonl + regate_truth.jsonl, deterministic, fictional facts only.

This is a STARTER set so the re-gate (scripts/jev-regate) and the test suite run out of the box. Every fact below is
invented (a fictional city's permits, grants and fines). Replace it with pairs from YOUR domain before you trust the
gate: see golden/README.md. Run: python3 build_golden.py   (rewrites both files next to this script)
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
Q_CLAIM = "Does the source sentence support the claim as worded?"
Q_DET = "Does the draft sentence carry the letter's determination (same verb meaning, same service, same period)?"

# (id, subject, verb_ok, verb_bad, thing, amount, amount_bad, date, date_bad)
BASES = [
    ("permit_a", "The Harbor City planning office", "approved", "denied", "building permit BP-2041", "$4,200", "$2,400", "03/14/2026", "03/14/2025"),
    ("permit_b", "The Harbor City planning office", "denied", "approved", "variance request VR-318", "$150", "$1,500", "05/02/2026", "05/20/2026"),
    ("grant_a", "The Lakeview arts council", "awarded", "declined", "grant G-77", "$12,000", "$21,000", "07/01/2026", "07/01/2027"),
    ("grant_b", "The Lakeview arts council", "declined", "awarded", "grant G-91", "$8,500", "$5,800", "08/19/2026", "08/09/2026"),
    ("fine_a", "The Maple County library", "waived", "assessed", "late fee on account L-5520", "$36", "$63", "02/11/2026", "02/11/2025"),
    ("fine_b", "The Maple County library", "assessed", "waived", "replacement fee on account L-8801", "$24", "$42", "04/28/2026", "04/18/2026"),
    ("util_a", "The Pinecrest water authority", "refunded", "billed", "overpayment on meter M-330", "$118", "$181", "06/06/2026", "06/06/2025"),
    ("util_b", "The Pinecrest water authority", "billed", "refunded", "excess usage on meter M-412", "$92", "$29", "09/12/2026", "09/21/2026"),
    ("lic_a", "The Riverbend licensing board", "renewed", "revoked", "food-vendor license FV-205", "$75", "$57", "01/05/2026", "01/05/2027"),
    ("lic_b", "The Riverbend licensing board", "revoked", "renewed", "taxi permit TX-613", "$200", "$20", "10/30/2026", "10/03/2026"),
    ("park_a", "The Elmwood parks department", "granted", "refused", "pavilion reservation R-1190", "$60", "$600", "05/23/2026", "05/23/2025"),
    ("park_b", "The Elmwood parks department", "refused", "granted", "fireworks request R-1204", "$300", "$30", "07/04/2026", "07/14/2026"),
    ("tax_a", "The Granite Falls assessor", "reduced", "increased", "assessment on parcel P-9001", "$1,950", "$9,150", "03/01/2026", "03/01/2025"),
    ("tax_b", "The Granite Falls assessor", "increased", "reduced", "assessment on parcel P-9044", "$2,300", "$3,200", "11/15/2026", "11/05/2026"),
    ("bus_a", "The Cedar Valley transit agency", "extended", "cancelled", "route 14 service", "$0", "$10", "08/31/2026", "08/31/2025"),
    ("bus_b", "The Cedar Valley transit agency", "cancelled", "extended", "route 22 service", "$0", "$20", "12/01/2026", "12/10/2026"),
    ("school_a", "The Oakdale school board", "approved", "rejected", "field-trip budget FT-6", "$3,400", "$4,300", "09/09/2026", "09/09/2025"),
    ("school_b", "The Oakdale school board", "rejected", "approved", "vending contract VC-2", "$5,000", "$500", "02/27/2026", "02/17/2026"),
]

INF = {"approved": "approve", "denied": "deny", "awarded": "award", "declined": "decline", "waived": "waive",
       "assessed": "assess", "refunded": "refund", "billed": "bill", "renewed": "renew", "revoked": "revoke",
       "granted": "grant", "refused": "refuse", "reduced": "reduce", "increased": "increase", "extended": "extend",
       "cancelled": "cancel", "rejected": "reject"}

NAME_SWAPS = [("Harbor City", "Harbor Bay"), ("Lakeview", "Lakeside"), ("Maple County", "Maple Grove"),
              ("Pinecrest", "Pinehurst"), ("Riverbend", "Riverdale"), ("Elmwood", "Elmhurst"),
              ("Granite Falls", "Granite Ridge"), ("Cedar Valley", "Cedar Hills"), ("Oakdale", "Oakmont")]


def swap_name(subject):
    for a, b in NAME_SWAPS:
        if a in subject:
            return subject.replace(a, b)
    return subject + " of Springfield"


def claim_rows():
    rows = []
    n = 0
    for (bid, subj, ok, bad, thing, amt, amt_bad, d, d_bad) in BASES:
        src = f"{subj} {ok} {thing} for {amt} effective {d}."
        variants = [
            ("yes", "faithful restatement", f"{ok.capitalize()} was the outcome on {thing}, with {amt} effective {d}."),
            ("yes", "faithful restatement", f"{subj} {ok} {thing}; the amount was {amt} and it took effect {d}."),
            ("no", f"perturbation=verb: '{ok}' -> '{bad}'", f"{subj} {bad} {thing} for {amt} effective {d}."),
            ("no", f"perturbation=amount: '{amt}' -> '{amt_bad}'", f"{subj} {ok} {thing} for {amt_bad} effective {d}."),
            ("no", f"perturbation=date: '{d}' -> '{d_bad}'", f"{subj} {ok} {thing} for {amt} effective {d_bad}."),
            ("no", "perturbation=actor", f"{swap_name(subj)} {ok} {thing} for {amt} effective {d}."),
            ("no", "perturbation=negation", f"{subj} did not {INF[ok]} {thing} for {amt} effective {d}."),
        ]
        for label, detail, claim in variants:
            n += 1
            rows.append((f"c{n}", label, detail, bid, f"Claim: {claim} Source sentence: {src}"))
    return rows


def det_rows():
    rows = []
    n = 0
    for (bid, subj, ok, bad, thing, amt, amt_bad, d, d_bad) in BASES:
        letter = f"{subj} {ok} {thing} for {amt}, effective {d}."
        variants = [
            ("yes", "same verb meaning", f"The {thing} was {ok} for {amt}, effective {d}."),
            ("no", f"perturbation=verb: '{ok}' -> '{bad}'", f"The {thing} was {bad} for {amt}, effective {d}."),
            ("no", f"perturbation=period: '{d}' -> '{d_bad}'", f"The {thing} was {ok} for {amt}, effective {d_bad}."),
        ]
        for label, detail, draft in variants:
            n += 1
            rows.append((f"d{n}", label, detail, bid, f"Letter sentence: {letter} Draft sentence: {draft}"))
    return rows


def main():
    items, truth = [], []
    for kind, rows, q in (("claim", claim_rows(), Q_CLAIM), ("determination", det_rows(), Q_DET)):
        for rid, label, detail, base, state in rows:
            items.append({"id": rid, "state": state, "question": q})
            tag = "SUPPORTED" if label == "yes" else "NOT_SUPPORTED"
            truth.append({"id": rid, "label": label, "method": "construction", "detail": f"{tag}; base={base}; {detail}"})
    for name, rows in (("regate_items.jsonl", items), ("regate_truth.jsonl", truth)):
        with open(os.path.join(HERE, name), "w") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(items)} rows ({sum(1 for t in truth if t['label']=='yes')} yes, {sum(1 for t in truth if t['label']=='no')} no)")


if __name__ == "__main__":
    main()
