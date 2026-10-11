# Class: data-product

A deliverable plus writes into a live system of record — a portal, a database, a scheduler.
Exercised: C8 (46 agents, 29 live-portal writes, document + data). The riskiest class: the writes
are other people's operational truth and most of them are not undoable by you.

Read `document.md` for the artifact half. This file covers the writes.

## Rails

- **Writes are GO-only and gated.** Each write batch is an E0 row that names its record ids, fields and
  values before the owner answers; the owner's GO adopts the row by its number (a reply that names no row runs
  nothing — CEO decision E5). It passes §GATE first (`cascade-gate.md`): the deterministic checks,
  recomputed by `jev gate` itself (the record id and the fields string-equal the adopted row's — E12),
  then `jev gate --veto` with `authorized` and `right_artifact` (the fields change only the values the
  row names; on a row the owner's reply named by number Jev can only block). Only an `approve` writes; the
  decision is the RAIL NOTE. A write into the owner's own system of record is GO-able; filing,
  uploading or submitting anything to a third party through its portal is a send — HUMAN-ONLY, never a
  GO'd write (E6).
- **The system of record is truth, and the write is not done until it is read back.** Every write is
  verified **intent vs outcome** by re-reading the record, not by trusting the tool's success return.
  Report the pair. A write whose read-back differs is a defect, not a retry.
- **Prefer the system's own export for any figure whose authority comes from the system.** A chart the portal
  produced and a chart you rendered are different artifacts with different authority; if you render, say so.
- **Chart / exhibit provenance split.** Every figure carries a provenance class — source-system
  export vs generated probes-only render — and the deliverable **states the classes in a methods
  sentence**. Byte-verify every embedded asset against its source before shipping (C8: 34/34
  SHA-checked). The objection to avoid is never "you generated a chart", it is "you made it seem
  like there was data where there was none".
- **Host GUI is not free.** The portal lane drives Playwright/Chromium on the owner's machine and the artifact
  lane may drive LibreOffice; the watchdog covers neither. Run them guest-side, or declare the lane in
  `CORP_STATE.md` and do not start it while the owner is at the keyboard (preflight prints the idle time).
- **Two-lane campaign.** Background Workflow runs the artifact lane while the main thread drives the
  live-system lane, synchronising on notifications. Arm `until [ -f <output> ]; do sleep 5; done` in
  the background and keep working — poll-with-sleep is a subagent rule, not the orchestrator's. When
  the journal shows no progress, do adjacent hand-work, never status prose.
- **Windows, staleness and the portal's own lies.** Name the data window the source actually returns (a
  6-month default that looks like "all") and refuse a short pull mechanically, not by eye. Then check for
  **future-dated rows, duplicate rows, and metrics that are percentages rather than counts**. **A `0` in a
  portal usually means three different things — find out which.**

## Verification: a stage that refutes nothing is broken

C8's round-2 spec verification passed **139 of 139**. The orchestrator noted the smell in the ledger
and shipped anyway; the panel then found 30 issues in that same output, 3 of them blockers.

**Rule: record the per-stage refute rate in `CORP_STATE.md`. A stage at ~100% pass is reported as a
finding about the harness, and the next stage is told not to trust it.** Do not ship past it.

Pair with the **closure-checker** seat: one panel seat exists solely to verify *claimed* closure item
by item against the prior round's report — "not half-done, not watered down" — handed a numbered list
of the exact texts, numbers and tables that must now be true, plus the known-held list not to
re-litigate, and told "report only failures". Both of C8's silent no-ops were caught by this seat;
the general-purpose critics missed both.

## Durability

This is the class that lost the most. C8's whole machinery — `CORP_STATE.md` with six rounds of
receipts, `specs.json` with 139 verified specs, the entire build chain — lived in a session
scratchpad and is gone, and a memory file still points a future session at the dead path.

`CORP_STATE.md`, the specs, the generators and the receipts live **beside the deliverable in a
durable folder**, mirrored out of `/tmp` before the first agent is dispatched. Any volatile evidence
the report cites is copied into that folder. A memory index line goes in the same turn.

**Jev in this class** (`jev.md`): **Job 1** — `jev filter --all` to triage row-level or stage flags in one batched
pass before a verifier reads them; `jev-browse` for read-only portal lookups. **Job 2** — one `jev second` per stage
seconds each refute/keep verdict. **Gate** — every GO'd write batch passes §GATE. **Never Jev:** row counts, join keys,
computing numeric values, schema and units.

## Rails (paste into the kit's `CLASS_RAILS`)

Everything in `document.md`, plus: writes are GO-only and pass §GATE first; the system of record is truth and **a
write is not done until it is read back** — report intent vs outcome per write, and a read-back that differs is a
defect, not a retry. Prefer the
system's own export for any figure whose authority comes from the system; every figure carries its provenance
class (source-system export vs generated render) and the deliverable states the classes in a methods sentence.
Byte-verify every embedded asset against its source. Name the data window the source actually returns and refuse
a short pull mechanically. A portal `0` means three different things — find out which. No GUI launch on the host
without a declared lane.
