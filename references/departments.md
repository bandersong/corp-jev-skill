# Departments — the spine in full, synthesis, the round loop

Contents: Roster · 1 PMO / recon · 2 Ground truth · 3 Builders → quote gate → §CASCADE · 4 Claim audit · 5 Panel and
upward verification · 6 Integrator · 7 Apply + verify · 8 Synthesis and delivery · Round loop

The order is load-bearing (ground truth before drafts, the claim audit before the panel); the class file supplies each
department's content. Tiers and efforts: `model.md`. Jev at each step: `jev.md`.

## Roster — fixed, so a department cannot vanish by not being thought of
Containment preflight (PASS / PARK / N/A) · PMO · ground truth (a synthetic test corpus, for software) · builders · QA
in the guest · red team over QA's output · claim audit · panel · integrator · apply + verify · upward verification ·
synthesis. No waste: skip any department with an empty backlog and report it SKIPPED with its reason, in your first
message and in the ledger. An unmentioned department reads as covered.

## 1. PMO / recon (read-only; sonnet, `high`)
Read the memory index first, then interview the owner for org ground truth: systems of record, who signs, house numbering, who
else edits these files. Enumerate every surface exhaustively up front, not in reaction to the last panel (after an
incident in which two correctness reds stayed open for several waves while the budget went to polish). `INPUTS.md` — each
source, its extraction method, its addressing scheme, its known-lossy paths, and its **authority class**: LETTER (the
counterparty's own letter or decision) / CLAIMS (a system-of-record export) / TRACKER (a practice or project tracker) /
DRAFT (ours or a colleague's) / OTHER, with HELD or INFERRED for every figure the doctrine ties to a letter (CEO decision
E2; the class also goes into quote-gate's `map.json`, and a map that carries classes turns on quote-gate's `--payer`
rules — the LETTER rule, the determination verb, a `claim` on every row — in any class, F12) — opens every later brief.
Then the blocker matrix, one row per item: CLOSED (evidence) / OPEN (what remains) / OWNER_GATED (the named decision) /
UNKNOWN (conflicting sources), plus the merge queue and the critical-path ship chain. Where a clock exists, deadline
arithmetic is a PMO deliverable computed in code, not a footnote. The repo is truth and the plan is dated — truth being
the copy the counterparty holds, not your build.

## 2. Ground truth
The synthetic corpus, the cite bank or evidence canon, or the claims allowlist (`TRUTH.md`) that every later department
checks against. No draft exists before it does.

## 3. Builders (parallel, one unit each; documents: opus `xhigh` — software: sonnet, `model.md`)
Correctness reds first: a standing red on the core promise outranks every polish item and is scoped to a named builder,
never carried. Work the owner scoped to themselves is flagged, never built. Declare the size budget up front (words, pages,
reviewer-minutes; diff size, API surface): every department's schema is additive, so without a budget the artifact grows
every round. Drafters carry `[src: <doc> p.N "<quoted sentence>"]` pointers — a computed figure
`[calc: <receipt path>]`, its inputs pointered inside the receipt (`cascade-gate.md` §CASCADE step 2) — until the build
strips them in a named, counted step (`scripts/census --strip --out-dir <dir> --stamp '<stamp>'`: apply-edits' engine,
copies only, never in place; CEO decision E3) whose residual `[src:` / `[calc:` count is 0. From round 2 on drafters
emit anchored edits and never touch the built file. Drafted prose then passes the quote gate (`scripts/quote-gate`, plus
`--receipts` over every receipt and `--drafts` over the drafts, which ties each drafted `[calc:]` figure to its receipt's
result) and §CASCADE (`cascade-gate.md`) before the claim audit.

## 4. Claim / citation audit (chunked; sonnet, `high`; the brief ends "Think the problem through before you answer.")
Before the panel, because ship blockers are repeatedly prose, not code. Every claim → VERIFIED (source + page + quote) /
INFERRED / MISMATCH / MISCITED / UNSUPPORTED / ARITHMETIC (recomputed in code — every `[calc: <receipt path>]` figure is
re-derived here from its receipt's inputs, each of which passed `quote-gate --receipts` on its own pointer and declared
role; never by Jev): every promised element exists, every id is the right id, every number traces to a receipt, every
citation is checked against a primary source or the cite bank. A figure whose authority is a letter (an authorized or
denied figure, doctrine rules 1–2) is VERIFIED only against a LETTER row of INPUTS.md. Against any other class it is
**INFERRED** when its sentence is the doctrine's INFERRED form — it attributes the source it rests on and names the
missing letter in the same paragraph ("this provider's claims record shows …", the doctrine's rule-1 form) and the cited
source says what the sentence says — and UNSUPPORTED otherwise (CEO decisions E2, F11). INFERRED is never VERIFIED: its
quote-gate row or receipt input declares role `other`, never `authorized` or `denied`; `claimSeverity` keeps it `high` (a
verifier reads it); and it stays out of page-1 facts. Its `jev second` row's state is ONLY the attributed sentence plus
the source sentence it is attributed to — never the "letter not in our file" gap clause, which is a fact about our file
inventory, verified by code against INPUTS.md (no LETTER row for that cycle), never by Jev (CEO decision, 09-29; `jev.md`
§7). Unverifiable = cut; no fabrication; flag, never guess (`evidence.md`). Work order: the cascade's `DOUBLE_FAIL` units
first (both drafts, both verdicts — the audit decides: cut, MISMATCH for the integrator, or a confirmed source gap as
`[OWNER VERIFY: …]`), then its flagged units, then the pre-screen's worst-first order. Each auditor seconds its
statuses with one `jev second` at the end (pre-screened claims are joined, not asked again). Expect ~⅓ false positives —
the integrator's problem, not a reason to audit less. Every audit and panel return carries `status` and
`could_not_check[]`; a blocked part returns `partial` or `failed`, never empty.

## 5. Hostile panel and verification pointed upward (`playbook.md` §PANEL, §ORCHESTRATOR)
Fresh critics over artifacts only: per-class seats, always a purpose seat, the closure checker with the enumerated
contract and the known-held list. Each seat calls every failure it lists blocking or not; its verdict is the worst of
its own calls, seconded by one `jev second` (a `blocker` row per failure) and never lowered by Jev. Aimed at the CEO:
the ledger red-team, the pre-wave claim audit (from round 2) and the independent recount. The two adversarial layers are
never cut for budget.

## 6. Integrator (opus, `xhigh`; trusts nothing)
Re-derives every central claim and hunts the two recurring classes — no-op fixes, and gates green through their own
defect. Resolves conflicts semantically; verifies that the artifact its predecessor was ordered to write exists; runs
`git status` itself. Expect ~⅓ of incoming flags to be wrong: re-derivation is mandatory, not paranoid. Emits the
`EDIT_LIST` — `{id, closes[], file, old, new, rationale, kind}` plus `deferred[]` and `rejected[]`, each rejection with
the evidence that killed it (a falsified-artifact row) — every change classified `mechanical` (determined by the record)
or `judgment` (a named human decides: both conflicting values and their locations go to the owner queue, and it never
enters the edit list), with `size_before` / `size_after`. Before returning, it runs `scripts/apply-edits <list> --dry-run`
against the files and ships the list only at `MISSES (0)` — the anchor check becomes deterministic. The integrator's own
output is builder output for gating.

## 7. Apply + verify
Code applies the edit list — a fully determined plan does not need a model:
`scripts/apply-edits EDIT_LIST.json --out-dir <work>/v2 --stamp '<build stamp>'` writes edited copies and never opens an
original for writing (never `--in-place` on a submitted copy); `--in-place` makes a verified dated backup of every
changed file first and refuses on a Word lock, a read-only file or a file that changed on disk; `--dry-run` checks the
list against the files. **`--stamp`** sets `<cp:lastModifiedBy>` (and `<dcterms:modified>`, the build time) in
`docProps/core.xml` on every `.docx` it writes, and the md5 receipts come from the stamped bytes, so a build made from a
human's draft no longer carries that human's name (doctrine rule 20): a `.docx` write without it exits 2 and names the
choices (a `--dry-run` needs none); for an Acme payer build it must be one of `share-check.sh`'s exact `BUILD_STAMPS`
(the script reads them from share-check.sh); any other stamp runs with a warning that share-check will read it as a
human's. Matching is exact (no whitespace, Unicode or case normalization; a miss carries a hint that is never applied)
and atomic (one miss writes nothing), post-checked on disk; `judgment` rows and `new == old` no-ops are misses, never
applied; a `.docx` match that spans runs is reported under `formatting_risk`. Stdout is one JSON report (`outputs[]`
carries `md5_before`/`md5_after` — the md5 receipt of every output); the last stderr line is `MISSES (n)` — non-zero is a
build failure. It edits UTF-8 text and `.docx` only and does not render, so page counts still need the render step. A
change it cannot express (a structural `.docx` change: moving or inserting a table or section) is listed separately by
the integrator and applied by a sonnet agent at `medium` — it never rides in `edits[]` as `judgment`, which means a human
decides. **A matched anchor is not proof:** a fresh agent gets `formatting_risk[]` and `warnings[]`, re-extracts the
rebuilt artifact and asserts the CLAIM, not the patch; on the rebuilt artifact run the residual sweep (original vs final
count per defect token), the pointer strip (a named, counted step) and `scripts/census` (CEO decisions E3, E4, F4): every
part of every file — every XML part of a .docx, .xlsx or .pptx from raw XML (body, tables, text boxes, headers, footers,
footnotes, endnotes, comments, and the text of charts, drawings, SmartArt and WordArt), embedded packages part by part,
Strict-format OOXML too, plus PDF and .md/.txt text — counted for gated markers, catch-all hits and leftover `[src:` /
`[calc:` pointers, per file and part; exit 1 on any, or on anything it cannot read (a page with no text layer, a main
document part that yields no text, an embedded object that is not a package: UNCHECKED). A bracketed URL, `mailto:` or
DOI is a citation, not a pointer. `pandoc -t plain` misses headers and footers: it serves must-have strings, never the
census.

## 8. Synthesis and delivery (the CEO — never delegated; the one delegated CEO agent ran degraded)
The blocker matrix, what changed with receipts, results against ground truth, falsified claims, spend per pass, the
merge-queue depth (every pass; the loop never merges), a **NOT CHECKED — by anyone, ever** section built from every
agent's `could_not_check[]`, and the owner queue. Before it
ships: the RELAYED and STALE sweeps (`evidence.md`) and one `jev second` over every classified list it reports. Write it
for the owner: the outcome and what they must decide first, then complete sentences — no arrow chains, campaign tags or
labels they have not seen. Then the final gate on the final build (2 Fable + 1 Opus 5.5, all at `max`; all three always run — the
`corp-final-fable` and `corp-final-opus` agent types, or a Workflow `agent()` with `effort: 'max'`; never a bare
Agent-tool spawn, which cannot set effort, `model.md` Law 2): Fable A the hostile recipient and the purpose, Fable B
process and evidence, Opus whole-artifact coherence and the single most important defect (`model.md` §The final gate).
Any P0 → back to the integrator and the round repeats — up to the round ceiling declared at intake (CEO decision E14:
full 3, hard 5, deadline = the clock). A round that yields no P0 ends the loop; the ceiling reached with a P0 open
ends it too — STAGED (the P0 and its fix in the owner queue) or PARKED, never another round. A P1 is fixed or queued
with its fix; a Fable seat down after one probe runs on opus at `max`, said in the report. Then §GATE before any GO'd
outward act (`cascade-gate.md`), and §DELIVERY (`playbook.md`).

## Round loop
Read state (after a compaction, re-invoke /corp first) → preflight → one department pass on the Workflow tool (pipeline;
no cross-department barrier where outputs allow; seats return `jev_agree` / `jev_margin` / `jev_clear` from
`jev second`) → `mustEscalate()` on each return, then `ladder()`: agree-and-clear on a measured question stands with no
discretionary verifier, the rest — every disagreement, every provisional question, every null, empty, `partial` or
`failed` return — escalates; verifiers spend only on that list and the round logs verifies skipped → ledger red-team → commit the work folder, then the round-log paragraph per
department in CORP_STATE.md, Jev tally included (it gates the next round) → report → stop (a round with no P0, or the
round ceiling) or schedule. Failures resume with cached prefixes, never blind.
A turn that ends with a plan or "next I'll…" is not an exit: run it, or name the exit that applies and why.
