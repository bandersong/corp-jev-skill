# Class: document

One artifact a human signs and sends: a letter, a brief, an assessment, a memo. Exercised: C4, C6,
C7. **Domain-specific clinical/payer documents go to a domain-specific sibling skill** (not included in this repo) — it
carries that domain's rails and personas.

Model tiering flips here: **the builder writes the deliverable text and is the judgment-heavy step —
builders run opus at `xhigh`, the argument text included; the edit list is applied by `scripts/apply-edits`,
not a model.** `model.md` (Law 3: no measured tie with Sonnet 5.5 at lower cost).

## Recon writes two files before anything fans out

- **`INPUTS.md` — the source contract.** Every source file, its extraction method, its addressing
  scheme (page N = the Nth `\f` chunk), and its **known-lossy paths**. Name the lossy tool and forbid
  it for the feature it loses: *`pdftotext` silently DROPS the checked-box glyph — never call a box
  unchecked from the .txt alone.* One line like that overturned a blocker-severity red-team finding
  that was exactly backwards. Each row also names the source's **authority class** — LETTER (the
  counterparty's own letter or decision) / CLAIMS / TRACKER / DRAFT / OTHER — and marks every figure
  the doctrine ties to a letter HELD (the letter is in the folder) or INFERRED (CEO decision E2): a
  tracker or a prior draft never makes an authorized figure VERIFIED — at best the claim audit's
  INFERRED status (F11), which stays off page 1. "Read `INPUTS.md` FIRST" is the
  first line of every brief.
- **The evidence canon / cite bank.** A numbered claim table, one row per fact, each with its source
  document and location, marked "every entry independently read from source this session". Critics
  check the artifact **against the canon, not against the world**. A verified verbatim-quote bank is
  the *sole* source for any regulatory lane; paraphrase presented as a quote is forbidden; an
  unverifiable citation is **cut, not softened**. **No draft exists before the canon does** — C4's v1
  was written one minute before it and its lead argument was false.

Carry the previous similar campaign's cite bank and state file forward into `ref/` as prior art.

## Adversary before the draft, not only after

Run the opposing decision-maker *first*: their 12 best attacks, honest answers, a **DO-NOT-SAY list**,
and the deal they would actually accept. Paste that into the drafter's brief. The adversary is never
"a hostile critic" — it is the specific person with the specific mandate, reading **our own record**
for contradictions to quote back at us. Give drafters the canon's supporting and contradicting passages
in two separate blocks, so the draft can say where the record cuts against us instead of missing it.

## Panel seats

hostile counterparty · **procedural / regulatory** (standing, deadlines, service rules, citation
form — it produced blockers no other seat found) · **audience/persuasion** (the purpose seat) ·
writing critic (does page 1 carry the argument) · closure-checker against the enumerated contract.
Add one **self-incrimination** critic handed the artifact's known weak lines to weaponize, paired
with one unseeded critic so unnamed surfaces still get explored.

## Edits: drafters never touch the file

Drafters emit edit rows `{id, file, old (exact, unique, ≤ 90 chars of anchor), new}`; the
integrator's `EDIT_LIST` is applied by `scripts/apply-edits` — exact matching, the expected
occurrence count asserted, atomic (one miss writes nothing), dated backups or edited copies, every
`.docx` stamped with a build identity (`--stamp`), and a final `MISSES (n)` line where non-zero is a
build failure. An edit that needs document-structure
judgment goes to a sonnet applier at `medium`. **Named ceiling: an anchor that matched is not proof.**
Both silent no-ops in one campaign passed a green `MISSES (0)`; the closure-checker seat caught them,
the general critics did not.

## Proof recipe

Build → `pandoc -t plain` → **flatten newlines** (wrapped lines produced 3 false alarms in one
session) → assert must-have strings → sweep the banned-string list, counts as **required fields of
the return schema**, all zero. Then the **residual sweep** on the rebuilt artifact: `<name> orig:8
final:0`, side by side. MD5 the as-submitted original before and after. Convert to PDF and **read
the pages as images** — schema-valid is not looks-right, and page count is only true in a font that
exists on the target (ship a `QA_FONT` override).

**The census is code, and it reads every part (CEO decisions E3, E4, F4).** `pandoc -t plain` serves the must-have
strings only: on a five-marker fixture it found 3 (it missed the header and the footer), python-docx's paragraphs and
tables 2, a raw-XML sweep 5 (final gate FA-04). So the gated-marker count is `scripts/census` — every XML part of a
.docx, .xlsx or .pptx from raw XML (body, tables, text boxes, headers, footers, footnotes, endnotes, comments, and the
DrawingML text of charts, drawings, SmartArt and WordArt), embedded packages opened and counted part by part (an embedded
workbook or document), Strict-format OOXML as well as Transitional, plus PDF and .md/.txt text — counting gated markers,
catch-all hits and leftover `[src:` / `[calc:` pointers, case-insensitive, per file and part (CEO decision F4: the
re-gate's fixtures put a `[DATA NEEDED]` in a chart title, a SmartArt node, an embedded workbook cell and a Strict body,
and each read CLEAN before). Exit 1 on any hit, or on a file or page it cannot read — a scan with no text layer, a main
document part that yields no text, or an embedded object that is not a package (an OLE object) is UNCHECKED, never CLEAN.
A bracketed web or mail address or DOI (`[https://…]`, `[http://…]`, `[mailto:…]`, `[doi:…]`) is a citation, not a
pointer. The pointer strip before it is a named, counted step
(`scripts/census --strip --out-dir <dir> --stamp '<stamp>'`: apply-edits' engine into copies, never in place; the census
then runs on the copies). Anything a third party receives: census 0.

**Never mutate an artifact the counterparty already holds.** Corrections ship as a separate signed,
dated delta; the corrected master is a visibly marked twin that never enters the package.

## Size

Declare the ceiling up front in words / pages / reviewer-minutes. Every department's schema is
additive, so without a budget the pass makes the document **longer** (C7: 3,484 → 4,807 words before
three manual trim cycles). The integrator reports `size_before / size_after` and enforces it.

**Jev in this class** (`jev.md`): **Job 1** — `jev rank` over the located sources at Recon, before the two recon files
are written (order only — every located source is read; a list short enough to order by eye skips it, logged);
`scripts/quote-gate` on every quoted pointer, LOCATE for page-only pointers (it points at a line; the auditor reads the
value and its role there), then the pre-screen — one `filter --all` before the claim audit (auditors get the order,
never p). **Cascade** — every drafted unit goes through `jev verify` against its canon excerpts with its `task` before
the claim audit, computed figures masked with their receipts inside `sources`; a unit resting on one goes to the ARITHMETIC lane (`cascade-gate.md`). **Job 2** — one
`jev second` per seat seconds every claim-audit status and each panel seat's per-failure blocker calls before they reach
the integrator. **Never Jev:** generating, selecting or computing figures, dates, counts, units, word count and the size
budget, writing text.

## Rails (paste into the kit's `CLASS_RAILS`)

Builders on opus at `xhigh` (the argument text included); edits applied by `scripts/apply-edits` with `--stamp`. No
draft before the canon exists. Every claim carries `[src: <doc> p.N "<quoted sentence>"]` until the build strips them in
a named, counted step — a figure code computed carries `[calc: <receipt path>]` right after it instead, every input of
its receipt carrying its own pointer and role (`quote-gate --receipts`) — and every drafted unit passes the quote gate
and `jev verify` before the claim audit. An unverifiable citation is CUT, not softened; paraphrase presented as a quote
is forbidden. Never fabricate a record of a past event and never backdate. Never mutate an artifact the counterparty
already holds. Drafters emit anchored edit specs; they do not touch the file. Gated markers (`[OWNER VERIFY:`,
`[… TO COMPLETE]`, `TBD`) and leftover `[src:` / `[calc:` pointers are counted by `scripts/census` every round: **zero
in anything a third party receives**; a draft built for a named human to complete and sign keeps its markers, counted
and listed, and is handed over as a draft for signature (an E0 `handover` row: `census --for-signature`, then
`share-check.sh --record`) — when it comes back, their copy is adopted as the base first (`share-check.sh --adopt-human
<file>`, CEO decision F3), then `scripts/census` (strict) on it, an md5 manifest diff (`share-check.sh --diff`, every
file's md5 against the manifest: all UNCHANGED after the adoption) and share-check run before it is sent (CEO decision
E9); a version rebuilt on their copy is a new file beside it, never over it.
