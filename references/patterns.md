# Pattern catalog — field-proven moves, with origins

Each entry: what it is, how to run it, what it paid. Origins are campaign tags: C1 desktop-app release ·
C2 product site build · C3 Codex audit (read-only) · C4 appeal letter · C5 compliance packet ·
C6 counterparty brief (deadline) · C7 second appeal letter · C8 periodic report + portal writes; "absorbed 09-28" = adopted from
TypeSafe, OpenRouter or community sources in the 2026-09-28 rewrite. Patterns promoted into SKILL.md or a core
reference are marked [core]. Use this as a menu when a department needs a shape, not as a checklist — one `jev rank`
of the pattern titles against the department's brief picks the few worth reading (order only; say which you skipped).

Contents: Adversary and critique (1–10) · Truth, claims and citations (11–22) · Gates, edits and artifacts (23–35) ·
Process, state and hand-off (36–60) · Jev (61–62) · Absorbed 2026-09-28 (63–68) · Provenance: the incidents behind the
core rails

## Adversary and critique

1. **Persona critic** — C5. Build the persona from the REAL reviewer's transcript voice (how they read, what
   they hate, what they know about the org's systems); one critic per artifact wears it, transcript on disk.
   Schema in their grammar: `{file, category, location, X_says, wants_instead}` — every finding says what they
   want INSTEAD. A HARD LIMITS section they can never waive. Yield 201 → 131 → 327 findings over three rounds.
2. **Hostile counterparty red team** — C4/C6/C7. The adversary is the specific decision-maker with the
   specific mandate (the reviewer who signed the denial and wants to uphold it), not "a hostile critic".
   They read OUR OWN record for contradictions to quote back. Produced "as drafted, this upholds" + 20 findings.
3. **Hostile lens board** — C8. Replace generic critics with N named adversarial READER roles covering the
   counterparty's org chart (clerk-completeness, data-integrity, merits, units, citations,
   contradiction-hunter, prose). One paragraph of scope and its own model tier each; "empty list, do not pad".
   143 findings on a document that had already survived a full single-agent red team the day before.
4. **Adversary-as-input (red team BEFORE the draft)** — C6. Run the opposing counsel simulation first: 12 best
   attacks, honest answers, a DO-NOT-SAY list, and the deal they would actually accept.
   Paste its output into the drafter's prompt; the shipped brief's "tough questions" and "do not say" sections
   are direct descendants.
5. **Paired critic → skeptic pipeline** — C3. Every lane's output goes to a same-tier hostile skeptic on the
   SAME slice, which re-opens every cited line, defaults to REFUTED/OVERSTATED, returns `adjusted_severity`
   including `drop`, and must also find something worse and one doc claim the code contradicts.
   112 verdicts: 33 OVERSTATED + 7 REFUTED never reached the owner.
6. **Triage against named floors** — C5. An integrator between the persona and the compliance floor:
   ACCEPT / ACCEPT-MODIFIED (keep the obligation, move the work into a system they already use) / REJECT
   (enumerated floor or frozen decision, one-line reason) / ANNOTATE-ONLY. Floors enumerated in the prompt.
   201 findings, 0 legal floors cut, several workload complaints solved the reviewer's way.
7. **Purpose / message critic seat** — C2. [core] Grades whether the artifact does its JOB: does the fold read
   as the intended promise, is the emphasis order right, was any caveat weakened (bidirectional).
   Chosen per class: message for marketing, audience/persuasion for a letter, decision-usefulness for a report.
   It caught what three opus critics and a full integrator pass had certified.
8. **Self-incrimination brief** — C4. Hand the hostile critic your own artifact's known weak lines and ask it
   to weaponize them. Two of three v1 blockers landed on seeded surfaces.
   Pair with one UNSEEDED critic so unnamed surfaces still get explored.
9. **Known-pending / known-held exclusion list** — C4/C8. [core] Tell the panel what NOT to report: items
   another department is fixing right now, and items the owner queue already holds.
   "Report ONLY items that FAIL verification." Stops a whole round re-litigating in-flight work.
10. **Panel disagreement rule** — C1. [core] 2 critics asserting vs 1 falsifying is UNRESOLVED, not a defect;
    reconcile before it becomes a brief. This exact arithmetic created the era's phantom defect.
    Cost of not having it: one builder spent, one integrator revert.

## Truth, claims and citations

11. **Claim audit vs source pages** — C7. [core] Fan out over sections; every claim gets
    `{claim, status ∈ VERIFIED|INFERRED|MISMATCH|MISCITED|UNSUPPORTED|ARITHMETIC, source: file+page/line+verbatim
    quote, correction}`. "Say UNSUPPORTED rather than guess."
    129 claims → 107 verified, 22 flagged; the integrator re-derived 7 of the 22 as false positives.
12. **Evidence canon** — C4. A numbered claim table, one row per fact with source document and location,
    marked "every entry independently read from source this session", appended per round.
    Critics check the artifact against the CANON, not the world. No draft exists before the canon does — v1
    was written one minute before its canon and its lead argument was false.
13. **Cite bank + cite-bank-only rule** — C6/C7. A verified verbatim-quote bank is the SOLE source for the
    regulatory lane; paraphrase presented as a quote is forbidden; an unverifiable citation is CUT, not softened.
    A prior campaign's cite bank was both this campaign's input and its verification oracle. 7 defects, 0 fabrications.
14. **Claims lexicon + claims gate + gate self-check** — C1. An ALLOWED/FORBIDDEN phrase law in every
    doc-builder brief, plus a stdlib grep gate over docs/site/string-literals wired into CI.
    Plus a self-check for the gate itself: "the repo is clean today" passes equally if the gate stopped biting.
    The panel found v1 blind to "planned", multiline strings and negation, and wired into nothing.
15. **TRUTH.md law layer** — C2. A claims allowlist compiled by the orchestrator from repo docs and ledgers
    BEFORE any writing, declared to win every conflict with the design and copy specs.
    "Every sentence must be derivable from this file." Owner rulings appended as dated law before rework.
16. **Receipt document per load-bearing number** — C1. [core] Every number reaching a owner- or
    customer-facing surface gets a committed doc with the repro command.
    A comment citing another comment is not measurement. Two of four falsifications that night were inherited
    numbers, one of them from the orchestrator's own ledger.
17. **Flag, never guess** — C5. [core] `[OWNER VERIFY: …]` / `[DECISION NEEDED: …]` rendered visibly in the
    artifact are the ONLY permitted response to an unknown fact.
    Grep-counted every round and driven to zero, then enumerated into the owner queue.
    Audit any agent that claims it closed such flags — first check whether it invented the answers.
18. **No-fabrication boundary block** — C5. Never fabricate a record of a past event, never backdate, never
    assert a control/log/meeting/form not shown to exist; every external citation verified or flagged.
    Ship the CONSTRUCTIVE substitute in the same block: blank template + attestation + a plan to do it for real.
    The owner never had to say this; the loop refused unprompted.
19. **Procedural / regulatory verifier** — C4/C7. A dedicated lane for standing, deadlines, service rules,
    citation form and procedural exposure, separate from the substantive merits.
    It produced blockers no other seat found in both campaigns, and most of C5's real blockers.
20. **Independent recount** — C1. [core] A final read-only agent that trusts no operator arithmetic:
    re-derives every tally from raw artifacts, re-verifies each claimed defect, and flags any work item
    appearing in no results file. Falsified an operator's Tier-C rate 38% → ~4% and found an 84-doc silent gap.
21. **Ledger red-team** — C1. [core] One read-only verifier whose entire area is the orchestrator's own
    round-log paragraph, checked against primary sources (journals, manifests, git).
    Found 5 errors including a phantom defect already in flight in a live builder brief.
    Run it BEFORE the next wave reads the ledger; land its corrections behind a write-barrier.
22. **Pre-wave claim audit** — C1. [core] Before spending builders, one auditor scores the previous round's
    claims LANDED / NOT_LANDED / PARTIAL / UNMEASURABLE from artifacts only, feeding live numbers into the
    new briefs. Caught a claimed fix that had not landed in pixels before anything was built on it.

## Gates, edits and artifacts

23. **Grep gate over the SHIPPED artifact** — C5/C7. Extract text from the RENDERED artifact (docx/PDF/HTML),
    not the source, and grep a declared forbidden-string list.
    The counts are REQUIRED fields of the agent's return schema and must be 0.
    Independently invented three times — this is the document class's gate that bites.
24. **In-artifact proof recipe for prose** — C4. Build → `pandoc -t plain` → FLATTEN newlines → assert
    must-have strings → sweep banned strings. The flatten step was learned twice (wrapped lines = 3 false alarms).
    For tracked-changes artifacts, add the accept/reject dual-view proof (`w:ins` count == `w:del` count).
    The marker census is not this recipe: `pandoc -t plain` found 3 of 5 fixture markers (it missed the header and the
    footer), so the census is `scripts/census` over every part from raw XML (final gate FA-04, CEO decision E4) — and
    every part means DrawingML too: the re-gate's chart, SmartArt, embedded-workbook and Strict fixtures each read
    CLEAN until the census read them (F4).
25. **Residual sweep gate** — C7. After apply, grep the REBUILT artifact for every defect token and print
    orig-vs-final counts side by side (`<token> orig:8 final:0`).
    The document-lane equivalent of revert→RED / restore→GREEN.
    Pair with an immutability checkpoint: MD5 the as-submitted original before and after.
26. **Class-scoped residual sweep** — C1. After file-scoped workers land, the orchestrator sweeps every DEFECT
    CLASS across the whole tree. Designating a single source of truth does not delete contradicting
    instructions elsewhere — four documents still carried killed instructions, one of them the approval card
    that would have blessed one. Closed 4 leaks the workers structurally could not reach.
27. **Gate-bite proof / mutation test** — C1/C2. [core] A critic injects a violation → run the gate → must go
    RED → restore byte-identically (`git diff` empty) → GREEN; both outputs pasted.
    A gate that cannot go red is itself a P0. A proof that PASSES under the mutation is worse than none.
28. **Extraction-fidelity rail** — C7. Name the known-lossy tool in the INPUTS contract and forbid it for the
    feature it loses: `pdftotext` silently DROPS the checked-box glyph.
    Require the verifier to read the SAME BYTES the fix was made against.
    One line overturned a blocker-severity red-team finding that was exactly backwards.
29. **Anchored edit spec + MISS counter** — C8/C7. [core] Drafters never touch the file; they emit
    `{id, file, old (exact, unique), new}` rows. `scripts/apply-edits` (09-28) asserts each occurrence count,
    applies atomically and prints `MISSES (n)`; non-zero is a build failure. Named ceiling: a matched anchor is
    NOT proof — both silent no-ops passed `MISSES (0)`.
30. **Exact-edit-list hand-off** — C7. [core] `{id, closes[], file, old (verbatim unique substring), new,
    rationale, kind}` + `deferred[]` + `rejected[]`; an opus integrator decides, code applies (`scripts/apply-edits`,
    replacing the sonnet applier on 09-28) and reports applied/missed. The single best hand-off design in the corpus.
31. **Mechanical-vs-judgment classification** — C7. [core] Every proposed change declares whether its
    replacement is determined by the record or requires a judgment only a named human holds.
    The latter returns empty find/replace plus BOTH conflicting values and their locations, and never enters
    the edit list. 58 mechanical / 19 expert / 9 rejected, 0 damage.
32. **Render-QA in the delivery environment** — C7/C5. Page count is only true in a font that exists on the
    target (Word ships fonts LibreOffice substitutes: 7pp → 9pp) — ship a `QA_FONT` override.
    Convert to PDF and READ THE PAGES AS IMAGES: caught two text collisions a schema validator called "All
    validations PASSED". Schema-valid != looks right.
33. **Capture-rig validation (CAPNOTE)** — C2. Any capture tool must report back the geometry/state it was
    asked for (print `innerWidth` with every screenshot); a shot whose reported geometry != requested is
    QUARANTINED. Define the capture procedure once as a script constant interpolated into every brief.
    Without it, 2 of 7 defect tickets were the instrument, not the artifact.
34. **Immutable-submitted-record doctrine** — C4/C7. Never mutate an artifact the counterparty already holds;
    corrections ship as a separate signed, dated delta.
    Keep the corrected master as a visibly marked twin that never enters the package.
    Checksum the original before and after and report it.
35. **Chart / exhibit provenance split** — C8. Every figure carries a provenance class (source-system export
    vs generated render) and the deliverable STATES the classes in a methods sentence.
    Byte-verify every embedded asset against its source before shipping (34/34 SHA-checked).
    The objection was never "you generated a chart" — it was "you made it seem like there was data".

## Process, state and hand-off

36. **Decision log as a build stage** — C8/C5. [core] Owner answers become a numbered, dated stage with
    receipts: decision, the owner's own words, what it changed, where implemented; delegated inference recorded AS
    INFERRED with its basis. A FROZEN section builders may not touch; re-litigating it is an automatic REJECT;
    builders are dispatched by decision id. Every figure a decision implies is asserted against data.
37. **Human-reviewer round** — C5. Four parallel readers over overlapping transcript slices ("read past your
    end boundary if a decision is mid-discussion") → one `xhigh` editor that dedupes seams and settles reader
    disagreements against the transcript text. The recovered decision log becomes its own deliverable.
    By round 4 the humans reviewed the MEMO, not the artifacts — one decision per item, no menus.
38. **Annotated review copy** — C5. A parallel `ANNOTATED-` file per deliverable: body BYTE-IDENTICAL to the
    shipping copy, plus `> WHY:` under every provision the reviewer will challenge (what requires it, what it
    costs, who does it, where the record lives). A validator asserts body identity.
    The reviewer's next session is spent reading answers, not writing questions.
39. **Owner queue with a schema** — all campaigns. [core] Only decisions a human can make — a secret, a
    name, a price, a signature, a merge — ordered by the orchestrator's judgment, security first, each with
    owner, deadline, consequence-if-unanswered, and a fallback if unanswered by T-minus.
    Mechanically tied to the artifact's gated placeholders so queue and artifact cannot drift.
40. **E0 decision batch + RAIL NOTE carve-out** — C1. [core] Collect owner-gated decisions into one numbered
    batch, take a single GO, execute inline at dispatch — N interrupt points become 1.
    When a GO authorizes something a rail forbids, write the exception into the ledger AT THAT MOMENT, naming
    the rail, the authority, and what stays owner work.
41. **Ground-truth preflight file / INPUTS contract** — C6/C7. [core] Before fanning out, hand-write the facts
    file and the source map: every source, its extraction method, its addressing scheme (page N = the Nth `\f`
    chunk), its lossy paths; "read these FIRST" opens every brief.
    Nine agents on one verified fact base beat nine readings of a 148-page PDF. 11 minutes, paid immediately.
42. **Ship-a-floor-first + declared ship gate** — C6. [core] Under a clock, deliver a shippable interim
    artifact as early as possible so the campaign becomes fail-safe; every later minute is upside.
    State the gate in advance with a NAMED fallback: "at 15:12 I ship whichever is best".
    Delivered at T-40 and again at T-13.
43. **Out-of-tree ledger + WORKING mirror** — C3/C5. [core] When the target isn't yours to write, campaign
    state goes to `~/<project>-audits/<date>-<slug>/` plus a memory index line in the SAME turn (every software
    class since 09-28: the work folder is never the product repo, CEO decision E17).
    Mirror the session scratchpad into a durable project folder so nothing load-bearing lives only in /tmp.
    Its absence killed the watchdog and one campaign's entire build chain.
44. **Archive-first deploy + human-edit detector** — C5/C4. [core] Before any write to a shared folder: move
    current contents server-side into `_ARCHIVE <date> <label>/`, mirror locally, copy, verify counts both
    ways. Never delete. Detect humans mechanically (`<cp:lastModifiedBy>`, `~$` lockfiles, mtime); a lockfile
    ABORTS the whole deploy. If locked: write a marked sidecar now, retry later, reconcile, say which is live.
    09-28 (final gate FA-07, FA-12, OM-01): `mkdir -p` the archive before the move; a NEW folder is `mkdir` without
    `-p` (the atomic absent-check) and share-check runs on it, never the parent tree; every deploy writes
    `.corp-deployed.json` so the campaign's own files never read as a human's (`document-set.md` §Deploy).
    09-29 (re-gate, CEO decisions F1–F3): a human's edit is adopted as the new base (`share-check.sh --adopt-human`),
    never argued with, and a rebuild on it is a new version file beside theirs; the gate lists the folder the act
    copies from and blocks on any file the adopted row does not name (the re-gate's fixture — a stale v1 beside v2 —
    passed every gate and `--record` vouched for it); every target outside the work folder needs its share-check
    receipt.
45. **Send-set separation + packaging department** — C5. Three sibling trees whose names make a mis-send hard:
    `SEND TO <recipient> (final)/` (numbered PDFs + one merged file), `OFFICE MATERIALS (not for submission)/`,
    `ANNOTATED/`, `INTERNAL - ` prefix. A named `MISSING - put the signed X here.txt` so a gap can't pass as an
    enclosure; six grep counters as the exit gate. Then verify the RECIPIENT's experience.
46. **Deliverable / scaffolding split** — C7. [core] The delivery location holds ONLY what gets delivered;
    previews, notes, state files and receipts go in one clearly-named subfolder.
    List the folder before and after when it is shared with humans. Retrofitted after the owner found a
    shared delivery folder cluttered with scaffolding.
47. **Read-only contract preamble + post-hoc containment proof** — C3. One shared string in every brief:
    pinned working directory, pinned commit, forbidden verbs, an allow-list of git/gh subcommands, "no writes
    anywhere, including sibling scratch trees". Then prove it: grep your own subagents' transcripts for
    mutating tool calls and paste the `tool_use` histogram in the report.
48. **Pin-the-tip + adversary-agent behaviour audit** — C3. When another agent is writing the target: pin the
    commit in every brief, never trigger their CI, re-fetch at synthesis, publish `"tip audited" != "tip now"`
    as its own row. A cheap sonnet lane reads their transcripts and scheduled automations against a fixed
    forbidden-action pattern set, plus "is any automation still armed". Produced the owner's #2 action.
49. **Measure-the-premise license / rebuttal law** — C1. [core] "Measure the premise before obeying. If the
    measurement contradicts my instruction, stop, move what you built into `<work>/corp/_reversed/<label>/` (never
    delete), and report the reversal with numbers. That is a success, not a refusal." Implement an unmeetable rule
    verbatim, let it fail, rebut with measurements; never silently reinterpret. Produced the two best outcomes of w40
    night. (The original wording said "delete what you built"; 09-28 it became "move aside" — the owner's never-delete rule.)
50. **Restart handoff block + orphan recovery** — C1. [core] On "I have to restart", write the in-flight
    `runId`, the exact resume command and the next session's ordered job list into the durable ledger BEFORE
    the restart. `resumeFromRunId` then replays completed agents from cache; only the missing phase re-runs.
    Turned a client restart into a non-event (7 agents replayed).
51. **Owner-wall / STAGED exit** — C1. [core] Stop when everything remaining is owner-gated and say so
    plainly rather than running more passes. Enumerate the items, each with its artifact pre-written and its
    clock identified. "Running more passes on top of a owner wall would be the dishonest kind of busy."
52. **Pacing doctrine + no silent caps** — C1. [core] Heavy lanes strictly one at a time with the whole shared
    resource; normal lanes at a stated concurrency ceiling; per-item timeouts; evidence pulled host-side every
    10 items. A lane that cannot run PRINTS its exclusion and reason.
    Prefer the harness's existing SKIP vocabulary to a new filter that can self-trip other gates.
53. **Intent-match lane** — C3. One lane exists purely to compare the owner's LITERAL words (pasted into the
    brief) against what was delivered. It produced the run's #1 P0: the feature the owner asked for shipped in the
    free extension, not the paid app. Auditing intent, not just correctness.
54. **`could_not_check[]` + "NOT CHECKED — by anyone, ever"** — C3. [core] A required field on every agent
    schema and a named section in every report. The only honest substitute for a department that structurally
    could not run, and what makes "0 verified / 20 partial / 36 unverified" legible to a owner.
55. **Parity audit + adversarial probes for unplanted classes** — C1. Enumerate every lane of the validated
    reference implementation against the shipped one: `PRESENT/MISSING/PARTIAL/NA` × risk ×
    `PORT_NOW/PORT_LATER/OWNER_DECISION`, evidence per row. Then hand-craft 2-3 probes per newly covered
    class. The campaign's highest-value pass; the only reason "871/871 clean" stopped being false confidence.
56. **Two-lane campaign + file-arrival wait** — C8/C6/C7. [core] Background Workflow runs the artifact lane
    while the main thread drives a foreground lane (live-system writes, greps, staging), synchronising on
    notifications. Arm `until [ -f <output> ]; do sleep 5; done` in the BACKGROUND and keep working.
    When the journal shows no progress, do adjacent hand-work — never status prose.
57. **Enumerated closure contract + closure-checker seat** — C8. [core] One panel seat exists solely to verify
    CLAIMED closure item by item against the prior round's report — "not half-done, not watered down".
    It is handed a NUMBERED list of the exact texts/numbers/tables that must now be true, plus the known-held
    list, and told "report only failures". Caught both silent no-ops the general critics missed.
58. [retired 2026-09-27]
59. **Overlapping-slice readers + seam-dedupe editor** — C5/C7. N readers over overlapping ranges of one large
    source ("read a little past your end boundary"), then one high-effort editor that dedupes seams and, where
    readers disagree, goes back to the source and settles it with the actual text.
    3,241 transcript lines → 57 raw → 32 clean decisions; 8 page-range readers over a 55-page record.
60. **Compact projection / path-not-content hand-off** — post-w40. [core]
    `integ.edits.map(e => ({id, file, new: e.new.slice(0,300)}))`, `deferred.map(d => d.id + ': ' + d.question)`.
    Where a PATH was passed instead of content, no truncation failure is recorded anywhere in the evidence.
    Applied by hand in 3 late scripts because the lesson propagated through a memory file, not the skill.

## Jev — owner directive 2026-09-27; measured 09-28 (`jev.md` §13)

61. **Jev triage before readers** — 2026-09-27. [core] One batched `jev rank`/`filter --all` over files, pages, grep
    hits or near-duplicate flags BEFORE any agent (haiku included) opens them; readers get the head, skips are logged,
    never a silent cap. Job 1: replaces an LLM read, not a second opinion.
62. **Jev ladder (agreement buys no extra verify; disagreement buys it)** — 2026-09-27. [core] `jev_agree`=agree and
    a clear margin on a non-blocker/high item, seconded by a question the registry marks measured, lets the seat's
    verdict stand with no discretionary verifier; a provisional question never does (09-28 integration), nor does an
    item its seat re-read (`jev_reread` ≠ 'none', CEO decision E13). A
    disagreement buys a re-read and then an opus verifier, always — a re-ask never turns it into a stand;
    `unavailable` or an unclear margin buys the verifier; a split P0 buys the full panel. Floors (blocker/high,
    mandatory seats, panel verdicts, the final gate) never move. Job 2, one `jev second` at the round's end.

## Absorbed 2026-09-28 — TypeSafe, OpenRouter and community practice (research/R1–R3, not included in this repo)

63. **Jev-verified cascade** — OpenRouter cookbook, absorbed 09-28. [core] A cheap tier drafts from sources, Jev
    verifies with a relevance clause, the unit is sent, escalated once to a stronger drafter, or handed to a human when
    the sources don't cover the task. `cascade-gate.md` §CASCADE.
64. **Gate a GO'd act** — OpenRouter cookbook, absorbed 09-28. [core] Deterministic checks first (a failure blocks with
    no model call), then named yes-propositions over one state: approve only if every one is ≥ 0.9, block if any is
    ≤ 0.1, else a human reviews. The static check list, not the threshold, is the security boundary. /corp's own form:
    on a row the owner's reply named by number, veto mode (Jev can only block), and the CLI recomputes the checks itself rather
    than trusting a caller's list (CEO decisions G, E12). `cascade-gate.md` §GATE.
65. **Quote gate + LOCATE** — TypeSafe citation-check and semantic-find cookbooks, absorbed 09-28. [core] A quote not
    found on its page is fabricated and needs no model; a page-only pointer gets a Choice over line ids (with `NONE`)
    plus an independent "does any line answer this?" Noul — registered, unmeasured, pointing only: the reader takes the
    value and its role from the located line, and `NONE` flags the claim for the auditor. `jev.md` §6.
66. **Extraction by selection — NOT adopted** (TypeSafe value-extraction cookbooks, read 09-28). Code over-finds
    candidate spans, Jev picks one or `NONE`, code copies it verbatim. The rewrite adopted it; the 09-28 integration
    reverted it: a span match cannot tell a denied or requested figure from the authorized one (golden q4956), and the
    owner's rule "Jev never computes: … value extraction" is theirs to change. A owner-queue question. `jev.md` §9.
67. **RELAYED and STALE** — community (clear-head), absorbed 09-28. [core] A figure found only in a subagent's report is
    re-read at source or struck; a sentence about self-changing outside state is re-read in the round that reports it.
    One rule caught the one real miss and fired on nothing else in 1,585 logged sentences. `evidence.md`.
68. **Facts first, then Jev** — community (jev-belay, Canny), absorbed 09-28. A done-check that computes transcript
    facts in code (did anything change? did a check pass since?) and only then asks Jev scored AUROC 0.976, against
    0.777 for the same judge on the closing message's wording alone. Facts decide whether Jev is asked; Jev's judgment
    blocks only when the facts show a change with no passing check since. (Canny's own rule is stricter — only facts
    block; the measured jev-belay design blocks on Jev's p after the fact gate, and so does ours, `HOOKS.md`, not included in this repo.)

## Provenance — the incidents behind the core rails (moved out of SKILL.md on 2026-09-28)
The core now states each rule with its reason in a clause; the incident that paid for it lives here (and in a CHANGELOG
and the 09-07 corp-on-corp campaign's NOTES.md and TRACE.md, moved out of the skill directory on 09-28; not included
in this repo).
- **Read the skill in full before the first dispatch** — an orchestrator that read from line 60 skipped the invocation and
  four rails. The 09-28 rewrite goes further: the core is kept at or under 12,000 bytes — about 3.2k–4.8k tokens by
  Anthropic's published character and word ratios, an estimate, not a `claude -p` probe — to fit the 5,000 tokens Claude
  Code re-attaches after a compaction; preflight PARKs past 12,000 bytes, and the core says to re-invoke after a
  compaction.
- **No flag grammar** — ten of ten real invocations were a literal `/corp` plus prose; bare `/corp` was 2 of the 10.
- **Use the kit** — four campaigns re-derived one topology; 30 scripts hand-rolled 26 preambles and 72 schema shapes;
  0 of them wrote a ledger.
- **Explicit model on every agent** — 160 of 160 sites complied once it was a law, the most successful line the skill
  has had; all 23 effort omissions were in the class the old skill ignored.
- **Host-quiet is enforced mechanically** — after repeated host-quiet breaches in one afternoon, the written
  doctrine was breached again within the hour; only the launchd watchdog stopped it (`software-release.md` §Host-quiet).
- **Shared surfaces are other people's work** — a blind one-way `rsync -a` to a shared folder destroyed human
  reviewers' annotations, the only irreversible harm in the corpus; a Word lock saved one file
  (`document-set.md` §Deploy).
- **Never codify a rail from a brief whose results have not arrived** — the old rail 3 was written 3 h 39 min before the
  provisioner reported, and that report qualified its central claim. Hence `Exercised: Cn` on every class file.
- **PARK means PARK** — PARK had never fired in eight campaigns, including a night containment broke twice; when the
  preflight fails, PARK is the exit.
- **Evidence** — one campaign accumulated seven falsified "defects", and four of the orchestrator's own beliefs were
  fiction, across five correction rounds (`evidence.md`).
