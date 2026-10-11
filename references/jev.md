# Jev — the full contract for /corp-jev and its domain sibling

Both skills point here (corp `SKILL.md` law 6; a domain-specific sibling skill's rail 1, not included in this repo).
The core carries the essentials; this file carries the rules, the thresholds, the failure contract and the measured record behind them.

Contents: 1 What and why · 2 Tools · 3 The registry · 4 Question design · 5 Reading answers: confidence and bars ·
6 Job 1: replace Claude spend · 7 Job 2: second every verdict that propagates · 8 The ladder · 9 Never Jev ·
10 Failure · 11 Tally and logs · 12 The build: float, check, re-gate · 13 Measured record · 14 Commands

## 1. What and why
Jev = `jev` (`~/.local/bin/jev` → `corp/scripts/jev`): TypeSafe's System One model `jev-latest` on OpenRouter
(`/api/v1/systemone`) under the owner's paid key, ~0.4 s and ~$0.00002 a call. It returns typed answers only: the
probability of yes, one option out of a set, or a position on ordered levels. It never writes text.
The owner's rule: use Jev judiciously, both to cut token cost and as a fast second opinion that is not an LLM ·
Jev for every typed judgment, straight Jev. Nothing stands in for it: no local model, no
haiku agent doing Jev's job. It is on from the first step of every class and mode; preflight PARKs if `jev ping` fails.
Every call does one of two jobs or is skipped: **Job 1** replaces Claude spend on a typed label; **Job 2** seconds a
verdict that propagates. TypeSafe's own model of the work: code owns control flow, rules and side effects; each Jev
question is one narrow judgment a knowledgeable person could make in seconds; anything larger is split into atomic
questions and recombined in code.

## 2. Tools
- `jev yes | pick | rate | ask | filter | rank` — the primitives. `ask` = several questions over ONE state;
  `jev ask --all questions.json < rows.jsonl` = one question set over many `{id, state}` rows (one request per row, every
  question riding it).
- `jev second < verdicts.jsonl` — Job 2 in one call (stdin, no `--all`). Rows `{id, kind, state, verdict}` with `kind`
  one of `claim | determination | keep_reject | blocker | edit_kind | pmo_status | panel | arithmetic`; it asks each
  kind's registry question over `state` only (one request per row, input order kept), compares Jev's answer with
  `verdict` (which Jev never sees), and returns per row
  `{id, kind, q, measured, jev_agree, jev_margin, clear, p_yes | choice + probabilities + p_top, status, build_mismatch?, lang_hint?, display_only?}`,
  plus the §11 tally on stderr and in the summary (fill "upheld seat s / jev j" after your re-reads —
  `ledgerParagraph()` refuses the unfilled `seat ? / jev ?`). `arithmetic` rows are `not_compared` with no call; a row
  Jev never judged is `unavailable`, status `UNKNOWN`. Exit 0 = every row accounted for; 3 = no key, auth or credits; 2
  = bad input.
- `jev verify` — the cascade verdict and route; `jev gate` — approve / block / review over named yes-checks. Both:
  `cascade-gate.md`.
- `jev <yes | pick | rate | filter | rank | gate> --q <id>` — ask a registry question by id (§3); `--q` is a flag of
  those subcommands, never of bare `jev`; an `ask` request names one as `{"q": "<id>"}`.
- Object state: `-f state.json` (a file named `.json` holding one object), or `--json-state -f -` fed by a quoted heredoc
  (`<<'EOF'`); a row's `"state"` may be an object. **Never `-s`** for a state (your global CLAUDE.md: the state goes in
  a file) — apostrophes and backticks in payer or code text break or rewrite shell quoting. `.txt` files and `-f -` without
  `--json-state` are sent as text, so the hooks' calibrated text states stay text.
- `jev ping` (preflight's gate) · `jev usage --since <ISO> [--session <id>]` (spend; without `--session` it sums every call
  on this machine, hooks and other open sessions included — its `scope` field says which).
- `scripts/quote-gate --docs map.json < rows.jsonl` — code, no Jev, no network: every pointer's quoted sentence must
  appear on the cited page before any Jev call (§6). Rows `{id, claim, doc, page, quote}`; `map.json` =
  `{doc: path to its extracted text}`, page N = the Nth form-feed chunk (INPUTS.md addressing). Matching folds only what
  extraction mangles (NFKC, curly quotes, dashes, soft hyphens, whitespace runs, a word hyphenated across a line break);
  case and every other character must match. Per row `QUOTE_OK`, or `MISCITED` with `found_on_page` or the closest
  `near_match` as the receipt a human judges — a near miss never passes. Exit 0 = every quote on its page, 1 = any
  MISCITED, 2 = bad input. A row may also name the `value` it takes from the quote and its `role` (authorized / denied /
  requested / used / other): the value must be in the quote and the role word nearest it must be that role ("Approved 240
  Denied 2,400" never gives 2,400 as authorized); a claims-export row `{id, doc, row}` must exist and is only ever `used`
  or `other`. `map.json` may give each document its INPUTS.md class (`{"text": …, "class": "LETTER"}`), and `--payer`
  (the domain sibling) requires an `authorized` or `denied` row or input to cite a LETTER (doctrine rules 1–2, re-gate RG-07),
  requires every quote row to carry its drafted sentence as `claim` (a row without one is MISCITED, RG-06), and refuses a
  claim whose determination verb (approved, denied, modified, reduced, reversed, overturned, upheld …) its quote does not
  carry (doctrine rule 2, E8). **`--payer` switches on by itself whenever `map.json` carries a class** (CEO decision F12:
  the LETTER rule never depends on a flag a pasted brief can omit; the summary then reads
  `"payer": true, "payer_auto": true`). `--receipts <receipt files or folders>` runs the same checks over every input of
  a `[calc:]` receipt, and a receipt with no operation over two sourced inputs is `NOT_A_COMPUTATION` (CEO decision E1;
  `cascade-gate.md` §CASCADE step 2). **The drafted figure is checked against its receipt's result too (RG-08):** a
  computed-figure row `{"id", "calc": "<receipt>", "value": "<the figure as drafted>"}` is `CALC_OK` only when the
  receipt passes and its `## result` holds that figure, and `--drafts <draft files>` builds one such row from every
  `<figure> [calc: …]` in the drafts ("79.2% [calc: r]" over a result of 69.2% is MISCITED; a `[calc:]` with no figure
  before it is too).
- `jev-browse` (its own skill) — Jev drives a headless browser for read-only web and portal lookups; Claude writes the
  steps and reads one JSON result; writes only with `--allow-writes` on an explicit GO, behind §GATE, and only into the
  owner's own systems: an upload, fax, e-mail or e-filing to a payer or any third party is a send — HUMAN-ONLY, never
  `--allow-writes` (E6).
- Hooks (`HOOKS.md` in the separate `jev` skill, not included in this repo): `jev-airlock` (rule #1 on every Bash call; a repeat of a denied
  operation is denied again; a `>>` append onto an unversioned file warns), `jev-edit-guard` (rule #1 on Write and Edit,
  warn only, no Jev: editing an existing file that is neither git-tracked-and-clean, backed up today, nor scratch warns
  with the one-line fix), `jev-tier-guard` (tier advice on every agent spawn, plus E11's code-only warnings: a /corp-jev
  seat not on its `corp-*` type, a spawn asking for `xhigh`/`max` whose type pins no effort, a `corp-*` type whose model
  the spawn overrides), `jev-belay` (sends back an unevidenced "done" once — facts from the transcript first, on
  subagents and on the main thread), `jev-gate` (a findings reply that made no Jev call is blocked once; `second`,
  `verify`, `gate` and every `--q` form count), `jev-notice` (the per-turn Jev summary the owner sees). The hooks that
  call Jev share a circuit breaker (3 Jev failures in 2 min → skip Jev for 5 min), go warn-only when the Jev build
  drifts from the one they were tuned on, and log every fail-open. That drift is loud (CEO decision E15): preflight
  prints `HOOKS WARN-ONLY` and WARNs "Hooks are warn-only: run
  `python3 ~/.claude/skills/jev/scripts/hooks-regate.py --apply`", and `jev-notice` adds "⚠️ hooks warn-only (Jev build
  changed)" to every turn's line until the hooks are re-gated (§12) — meanwhile the airlock denies nothing. Names and
  wiring: HOOKS.md.

## 3. The registry — `corp/jev-registry.json`
Every Jev question /corp-jev and its domain sibling ask lives in one registry: id, type, instructions, criteria or options, its
bars (per question and per verdict side) and whether it is **measured**. **Workers never write Jev question text**:
briefs name registry ids (`jev <subcommand> --q <id>`), and `jev second` picks the question by `kind`. A question may
enter the registry unmeasured, marked **provisional**: a provisional question adds work and never removes it — its
agree + clear never lets an item stand (§8). Only a labeled slice and a measured bar make a question measured; today
two are: `claim_support` and `determination`. The re-gate fingerprint includes the registry text and criteria of those
two, so rewording either re-gates at the next preflight; rewording any other question changes nothing the gate measures
(§12). TypeSafe's guidance is the reason for one registry: agents write poor questions, and the questions and thresholds
are what humans must review. The kit's `JEV_REGISTRY` carries the same texts and bars, and both test suites fail on
drift.

| id | type | used for | bar | measured? |
|---|---|---|---|---|
| `claim_support` | noul | the pre-screen; Job 2 claim status (`kind: claim`) | margin 1.1 | yes — 139 golden pairs, 09-28 |
| `determination` | noul | the domain sibling's determination-word check, after the grep for the letter's own verb | margin 1.1 | yes — 40 golden pairs, 09-28 |
| `keep_reject` | noul + measured criteria | keep/reject of a flag (`kind: keep_reject`) | margin 1.1 (provisional); unclear below 0.4 | ranking yes (AUROC 0.82–0.84, 31 items); the 1.1 bar no — 0–1 items per rep reached it |
| `blocker` | noul | a panel seat's per-failure blocker calls (`kind: blocker`; class-neutral: sent, filed or shipped) | margin 1.1 (carried) | no |
| `edit_kind` | noul | EDIT_LIST `kind`, mechanical vs judgment (`kind: edit_kind`) | margin 1.1 (carried) | no |
| `pmo_status` | noul | PMO blocker-matrix status: "Is this item still open according to the evidence shown?" (`kind: pmo_status`) | margin 1.1 (carried) | no |
| `locate_line` + `locate_any` | choice over the page's line ids + `NONE`, and an independent noul, in one `ask` request | LOCATE: point at the line that holds a fact (§6) | pointing only | no |
| `panel_verdict` | choice + UNCLEAR | a seat's holistic pick, display only (`kind: panel`, never compared) | `clear` | no |
| `class_pick` | choice + PAYER_DOC / OTHER / UNCLEAR | the class in your first message | `clear` | no |
| `verify_cascade` | choice | `jev verify` | accept 0.8 | cookbook value |
| `addresses_task` | noul | `jev verify`'s second question: names the failed half (`failed_half`), never changes the route | split 0.5 | no |
| `go_act` | gate | §GATE's checks `authorized`, `right_artifact`, `recipient_matches` (`jev gate --q go_act`, `cascade-gate.md`) | veto mode (a row the owner's reply named by number; the CLI recomputes the deterministic checks): block ≤ 0.1, else approve; full mode (a row adopted in the owner's own words): 0.9 / 0.1 | cookbook bars; checks unmeasured |
| `triage_payer_letter` | noul | the domain sibling's intake `jev rank` (order only, `-k` = all) | none | ordering only |

The registry file is the record of truth (exact ids included); this table is a reading aid. The measured bars were
measured on packing v1 (items inside the question); packing v2 (each row as its own state) passed the re-gate on 09-28
(§12).

**Scope of the rule.** Every question whose answer decides, routes, merges, points or seconds anything comes from the
registry — no exceptions. The one carve-out is Job-1 ordering: when no registry id fits, the CEO (never a worker) may
write a triage question for `rank` whose answer only orders a list that is read in full or cut with a logged skip; it
logs the question text in CORP_STATE so a reused one can be registered. **Pending registry entries** (listed for the code
lane): the near-duplicate Score, the domain sibling's track and mode picks, the three-way determination split, document-set's owner
routing and software-release's flake-vs-real label. Until each lands, its step runs the old way: near-duplicates stay
unmerged, the track and mode are recorded as decisions the owner can see, owners are assigned by hand and a red is read, never
labeled. **Value selection is not pending — it is not Jev's job** (§9): extending Jev to it is an owner-queue
question.

## 4. Question design — TypeSafe's rules, as /corp-jev applies them
- **Pick the primitive by the shape of the answer.** Noul = one independent yes/no (the value is the probability of
  yes; it has no separate confidence; 0.5 is an even split, not "medium"). Choice = one of N unordered options (it is
  relative: some option always wins). Score = ordered outcomes with a real middle, 2–10 levels, each describing a
  situation rather than a degree; read its `confidence` with it. Never carry a bar from one type to another without
  marking it provisional; a provisional bar may add work, never remove it.
- **One narrow judgment per question.** Two conditions are two Nouls combined in code with `max` (any one fires). A
  holistic "should this escalate?" head is displayed, never the gate — in TypeSafe's extraction cascade the holistic head
  read 0.56 while the per-field heads read 0.95 and 0.85. Phrase so a high p means yes; no double negatives; no
  inverted criteria.
- **The question is a complete sentence about the idea.** Ids and option keys are labels for code and are never sent to
  the model. Name the narrowest fact that decides, and ask about the reader's action, not the topic ("Does this page
  state the authorized units for this cycle?", not "Is this page about the authorization?").
- **Always a way out.** Every Job-2 pick carries `UNCLEAR="cannot tell from this state"` (09-28: without it 10 of 10
  undecidable states went to `NOT_SUPPORTED` at 0.99; with it 10 of 10 → `UNCLEAR`, decidable items within noise).
  Routing picks carry `OTHER` or `NONE`; LOCATE's line pick carries `NONE`. The absence of `UNCLEAR` is no proof the
  state was decidable: in a community study an "unknown" option under-fired when a needed fact was missing.
- **State = the content and its evidence, verbatim; the judgment lives in the question.** A measured question keeps the
  plain-text `state_format` it was measured on (`Claim: … Source sentence: …`, `Letter sentence: … Draft sentence: …`,
  `Flag: …`) — the bar holds only for that shape. Named JSON fields are for new or unmeasured questions whose context has
  several parts (verify's draft vs sources, the gate's GO row vs act), referenced in the question by backticked paths;
  a plain string for one simple text. Only what the question needs: accuracy falls as unrelated state grows. Never a
  verdict, rationale, reviewer note, "checked", or an actor's own framing — text that argues for its own classification
  moves p (09-28: "drafter: checked and correct" moved 15 of 139 items by > 0.1, q8491 0.17 → 0.64; OpenRouter's gate
  cookbook: a model-written reason moved a check from 0.41 to 0.26).
- **Items ride as their own state, keyed by id — never positional.** `filter`/`rank`/`ask --all` send each row as its
  own state; never ask about "item 3 of the list" (community measurement: positional references 86 of 320 wrong at 150
  items; keyed or embedded items 0 of 320).
- **Batch.** Independent questions over one state go in one request (speculative fan-out: an unneeded question is
  close to free, and answers are independent); a second request only when its questions need the first answer. One
  Bash turn per list, never one per item — the Claude turn around a call costs orders of magnitude more than the call.
  `pick` and `rate` are one call per seat or per run, never one per item: lists go through `filter`, `rank`, `ask --all`
  or `second`.
- **State budget.** 32k tokens for the state plus the longest question (TypeSafe); in practice a sentence pair or one
  paragraph per row, about 4,000 characters at most. Pages go through LOCATE (§6), never whole.
- **English only is trusted.** A state not in English is `unclear` whatever its margin (the vendor reports lower
  accuracy; a community study −3 to −6 points in Spanish; translating the input moved answers 3–5× more than repeat
  noise). `jev second` flags one with `lang_hint`, a function-word heuristic; `jev verify` (over a unit's draft, task
  and sources) and `jev gate` (over its whole state) run the same check before any call — a non-English unit routes
  `escalate` with `lang_hint: non_en`, which the kit's `cascadeStep()` turns into `audit` (the claim audit, no
  redraft; CEO decision F5), and a non-English gate state is review (OM-08). File paths, URLs and hex digests are
  stripped before the words are scored, so a path or an md5 never reads as a language (F6). It can miss a short
  foreign phrase inside English and can misread quoted Spanish, so judge the state yourself when it matters.
- **Criteria only where measured to help.** The claim and determination questions stay short and plain: doctrine written
  into the question (0.971 → 0.93), contrastive criteria on claim rows (0.967 → 0.93, clear-and-wrong 1 → 4) and
  structured state (no gain) were each tried and rejected on 09-28. Keep/reject uses the kit's measured contrast texts
  `JEV_DEFECT_TRUE` / `JEV_DEFECT_FALSE`.
- **Shell quoting.** Single-quote any question that contains backticks — zsh runs backticks inside double quotes and the
  question silently loses words (example in §14).

## 5. Reading answers — confidence and bars
- **Margin** = ln(p / (1 − p)) on a Noul; the CLI prints it. TypeSafe trains p to be calibrated across groups of
  answers, never as a guarantee for one answer, and on our abstract labels it showed no direction. So p ranks and
  routes: its margin decides only whether a discretionary verifier runs — never a verdict, never a drop, never an
  irreversible act. Agreement is not evidence.
- **Choice and Score `confidence`** measures how concentrated the distribution is — not the probability the answer is
  right and not permission to act (as published it is a rescaled top probability, (n·p_max − 1)/(n − 1)). A `pick` is
  `clear` only when its margin is ≥ 1.1 **and** the winner's p is ≥ 0.75: margin alone reads "clear" with the winner at
  0.50 on a four-option pick. `pick` prints `clear` and `p_top`; `pick --q <id>` applies that question's own bars.
- **Bars are per question and per verdict side** (the registry holds them):

  | Question | Bar | Status |
  |---|---|---|
  | `claim_support`, `determination` (Job 2) | margin ≥ 1.1 (p ≥ 0.76 or ≤ 0.24; p 0.75 is ln 3 = 1.0986 and escalates) | measured 09-28 on the 179-pair golden set (these two questions only): Jev alone clear-and-right 160 of 161 (packing v1; v2: 163 of 164, `~/.cache/jev/regate.json`) — optimistic: the wording and the pass bar were chosen on the same rows (§12) |
  | `keep_reject` | margin ≥ 1.1 | provisional: ranking measured (AUROC 0.82–0.84, 31 Claude-adjudicated items), but only 0–1 items per rep ever reached 1.1 |
  | non-claim unclear band | margin < 0.4 (p 0.4–0.6) → `unclear` | observed 09-28 on keep/reject (31 items) |
  | `pick` | `clear` = margin ≥ 1.1 and winner p ≥ 0.75 | provisional |
  | blocker, edit kind, PMO status, LOCATE | margin ≥ 1.1 (carried) | provisional, no slice yet |
  | `verify` | accept at confidence ≥ 0.8 | OpenRouter's cookbook value; tuned per `cascade-gate.md` |
  | `gate`, full mode (a row adopted in the owner's own words; `--q go_act` recomputes the deterministic checks first, as in veto mode) | approve if every check ≥ 0.9, block if any ≤ 0.1 | OpenRouter's cookbook value |
  | `gate --veto` (a row the owner's reply named by number; the CLI recomputes every deterministic check first) | block if any check ≤ 0.1, else approve (scores logged) | CEO decisions G, E5, E12 (09-28): an exact match is decided by code |

- **The 1.1 bar is never an action threshold** — not for a send, a gate, a write or a drop.
- **Measured bars remove work; provisional ones never do.** Only an item seconded by a question the registry marks
  measured can stand on agree + clear (`ladder()` enforces it, §8). Every other question — provisional bars included —
  orders and escalates, never skips a verifier.
- **Scale by risk.** Once a slice exists, the side whose error ships (VERIFIED, REJECT of a flag, CLOSED, `mechanical`,
  READY) earns a stricter bar than the side whose error only costs a fix. Until then both sides use the base bar.
- **Tune from live traffic, never the golden set.** `~/.cache/jev/judgments.jsonl` (every answered question) joined to
  outcomes (claim-audit statuses, owner reviews, reversed verdicts) is the tuning source; `corp/golden/` stays the
  untouched gate. Sweep, pick per question, and record the bar in the registry with its date and counts. When precision is
  poor at every cut, fix the question or the policy text, not the bar; when a gate's review queue fills with approvals,
  the GO wording is ambiguous — fix the wording, not the 0.9.
- **Expect noise near a line.** Repeats move p by ~0.01–0.03 here (0.03–0.13 in the cookbooks), so an item next to a
  bar can land on either side; the ladder sends those to a verifier.

## 6. Job 1 — replace Claude spend
The test before any agent spawn, haiku included: is the output a typed label over short states? Then it is a Jev call —
never an agent, and never your own read of the whole pile.
- **Order, never drop.** On findings, flags and claims use `filter --all`, or `rank -k` = the list's length; a threshold
  or a short `-k` is for triage lists only. A row Jev could not judge comes back `unavailable` and is read, never dropped.
- **Triage before reading.** One `jev rank` (or `filter --all`) over files, pages, grep hits or sources; readers get
  the head and the skip is logged (no silent caps). A LOCATED-source list (intake, payer letters, claims pages) is
  ordered, never cut: every one is still read. Over such a list the rank buys only the reading order (INPUTS.md rows
  and reader briefs follow it — for a payer document, the payer's own letter first); it saves no read, so a list short
  enough to order by eye skips it, and the skip is logged. A rank orders only what intake located — the missing-letter
  check stays a separate mechanical step, and an empty result is a finding to chase.
- **Routing.** The class `pick` in your first message: the six classes plus `PAYER_DOC` (stop: hand off to the domain sibling), `OTHER` and
  `UNCLEAR` (`class_pick` — its wording is new and unmeasured). Not clear, with the top two sharing a parent (the three
  `software-*`, or `document` and `document-set`) → load both class files; never force the narrow class. The owning
  department of a flag (with `NONE`; a flag whose runner-up owner has a real share is copied to both, never moved). Edit
  kind, mechanical or judgment (sets sonnet vs opus).
- **Near-duplicates** (registry entry pending, §3). Candidate pairs come from code (same location, a shared quote or
  id), never all against all. One Score per pair: *different defects* · *related, keep both* · *the same defect at the
  same place*. Only the top level merges, keeping both ids; nothing is dropped — a wrong merge costs more than a missed
  one.
- **Quote gate, then the pre-screen.** `scripts/quote-gate` checks each pointer's quoted sentence against the cited
  page's text (whitespace and curly quotes normalized); a miss is MISCITED with the failed match as its receipt and
  never reaches Jev. A draft sentence that asserts several facts is split in code into one row per fact first; the
  sentence clears only if every fact does. A figure code computed (a total, a per-code × per-period utilization, a
  percentage) carries `[calc: <receipt path>]` right after it in place of a pointer on the figure itself — its inputs
  still carry theirs, inside the receipt, each with its declared role, and `quote-gate --receipts` checks every one (the
  quote on its page, the role word in the quoted line; CEO decision E1), and `quote-gate --drafts` checks the drafted
  figure against the receipt's `## result` (RG-08). The figure has no source sentence, never reaches Jev, and goes to
  the claim audit's ARITHMETIC lane, which recomputes it from those pointered inputs. A figure
  looked up rather than computed takes `[src:]`: a receipt that is not an operation over at least two sourced inputs is
  not a computation. Matched claim rows get one `filter --all` (the
  registry claim question) that orders the claim audit worst-first. Auditors get the order and the tier, never p — a
  first-pass reader shown p stops being a second opinion; after they return, the orchestrator joins each row's answer to
  their status. Anything Jev produces for a Claude seat — a reading order, a routing hint — reaches it as advice ("a
  suggested order; read everything"), says "nothing flagged" when that is so, and comes after the fixed brief text so
  the prompt cache still hits.
- **LOCATE** — point at the line that holds a fact; registered, unmeasured, pointing only (§3). Use it for a pointer
  that names a page but no sentence, and for a drafter looking for the line that states a figure. Code prefixes each
  line of that page with an id; one Choice over the line ids plus `NONE`, and one independent Noul, "Does any line of
  the page address or answer this claim?", in one request. The picked line is a candidate, never a verdict: the reader
  (the drafter, or the auditor for a claim) reads that line and the page, and takes the value AND its role — authorized,
  denied or requested — from the source itself; code then string-compares the copied figure against the located line,
  and the pointer passes the quote gate like any other. `NONE` or a low Noul flags the claim for the auditor, first in
  the worst-first order — Jev never routes a claim to UNSUPPORTED (a whole page is the long state where Jev degrades).
  One `jev ask` request carries both (`{"q": "locate_line", "options": {line ids}}` and `{"q": "locate_any"}`;
  `jev ask --help`). Over 254 lines: pick a window first, then the line.
- **Not Jev: selecting a value** (§9). TypeSafe treats extraction as a judgment ("Extraction is a judgment"); the
  the rule is that Jev never computes and never extracts values. The span Jev would pick can sit
  in the letter in the wrong role — a denied or requested figure string-matches an authorized claim (golden q4956) — so the reader takes value and
  role from the source, and extending Jev to selection is an owner-queue question, not a loop decision.

## 7. Job 2 — second every verdict that propagates
A verdict propagates when it gates a round, reaches the deliverable, or goes to the owner: claim status, PMO status,
keep/reject of a flag, edit kind, each panel seat's per-failure blocker calls, the class. Each worker makes **one**
`jev second < rows.jsonl` call at the end of its pass over all of them, copies `jev_q` (the row's `q`: the question that
answered), `jev_agree`, `jev_margin` and `jev_clear` (required on every item) into its schema and the tally line into its
`jev` field. Row state = the item and its evidence,
verbatim, in the registry's `state_format` (the claim plus its source sentence; the flag as written; the defect; the
edit; the PMO item and its evidence); the verdict goes in its own field, never in the state.
- **Claims:** the measured Noul "Does the source sentence support the claim as worded?" over
  `Claim: … Source sentence: …`. Whole drafted units and sections use `verify`'s labels instead (`cascade-gate.md`). A
  `[calc: …]` figure is `kind: arithmetic` — `not_compared`, the receipt lane. **An INFERRED claim (F11)** is a
  `kind: claim` row whose state is ONLY the attributed sentence plus the source sentence it is attributed to — never the
  "letter not in our file" gap clause: the gap is a fact about our file inventory, verified by code against INPUTS.md (no
  LETTER row for that cycle), never by Jev (CEO decision, 09-29).
- **Keep/reject:** "Is this flag a real defect in the deliverable?" with the measured contrast texts (AUROC 0.44 when
  the verdict was folded into the question; 0.82–0.84 unfolded, 09-28). Its 1.1 bar is provisional (§5): a keep/reject
  never stands on Jev's agreement.
- **PMO status:** the `pmo_status` Noul, "Is this item still open according to the evidence shown?", over the item and
  its evidence; CLOSED is the no side, OPEN / OWNER_GATED / UNKNOWN the yes side. Unmeasured, and every PMO row is a
  filing blocker (a floor), so a second here orders and flags — it never closes a row.
- **Panel:** each seat decides, for every failure it lists, whether that failure blocks — its own judgment, never Jev's.
  Its verdict is the worst of its own calls: any blocking → NOT_READY; failures, none blocking → NEEDS_EDITS; none →
  READY (the kit's `panelVerdict()`; `PANEL_VERDICT.failures[]` carries each failure's `blocks` call). Its one
  `jev second` carries one `kind: blocker` row per failure (state `Defect: …`, its call as `verdict`); Jev's answers
  route escalation only and never change the verdict. Panel verdicts are floors: Jev never lowers one and the ladder
  never skips a seat — `checkPanelSeat()` sends back a seat whose verdict is not the worst of its own calls, and
  `panelFloor()` takes the worst seat as the panel's verdict. The holistic pick (`panel_verdict`, unmeasured) is display
  only (`not_compared`, kept in `jev_pick`) and never fills `jev_agree`.
- **Severity** is floor-governed and never seconded: blocker/high always escalate, and `rate` has no measured bar. When
  `rate` orders anything (Job 1 only), its levels describe situations, not degrees ("the deliverable cannot be sent as
  it stands", not "high"), and its `confidence` is read with it.
- **A verdict seconded by several Jev answers** (a seat's per-failure rows, a multi-fact sentence) is only as sure as its
  weakest: `jev_agree` is agree only if every row agrees, `jev_margin` is the minimum, `jev_clear` only if every row is
  clear — never a mean or a product.
- Claims that went through the pre-screen are joined, never asked again.
- The orchestrator seconds its own outputs too: the class pick, and every flag list or classified list it reports
  (one batched second opinion before any findings leave your hands).
- What `jev second` computes, for the record: agree = Jev on the verdict's side of 0.5 (VERIFIED, a claim's INFERRED,
  KEEP, blocker, mechanical, an open PMO status ↔ p ≥ 0.5; MISMATCH / MISCITED / UNSUPPORTED, REJECT, CLOSED ↔ p < 0.5; a
  pick agrees on the same option); `unclear` = a non-claim margin < 0.4, an `UNCLEAR` pick, or a state not in English;
  ARITHMETIC and other never-Jev items are `not_compared` and go to the receipt lane. Its `clear` is the bar only;
  whether an item may stand is `ladder()`'s call (§8).

## 8. The ladder — where Job 2 pays for itself
The kit's `ladder()` splits items by `jev_agree`, `jev_clear` (required on every item), `jev_reread` and the registry's
measured flag:
- **agree and clear on a measured question** (today `claim_support` and `determination`), **never re-read by its seat**
  (`jev_reread: 'none'`) → the seat's verdict stands on its receipt. No discretionary verifier: no N-vote refute panel,
  no second skeptic, no re-audit. Those four conditions together are the only way an item stands (CEO decision E13): a
  re-read only ever follows a disagreement or an abstention, so an item its seat re-read goes to the verifier whatever a
  re-ask returned — with or without `jev_first` on the row.
- **agree and clear on any other question** → escalates like the rest: a provisional bar orders the verifier's queue,
  it never skips the verifier.
- **disagree** → the owning seat re-reads the source and keeps or flips (`jev_reread` records the side the re-read
  upheld), then the item goes to one opus adversarial verifier — a different seat — whatever the re-read found. **A
  re-ask never turns a disagreement into a stand**; it is allowed only when the state itself changed after the re-read
  (fuller evidence, a corrected claim), both answers are recorded (`jev_first` keeps the first), and the item still goes
  to the verifier. A split P0 → the full panel.
- **unavailable** (the call failed; no answer arrived) → one re-ask on the same state is allowed: it can turn
  `unavailable` into an answer, which then takes its own branch here; still unavailable → the verifier. No re-read is
  owed on an item Jev never answered, and an unavailable item never fails the unit (E13).
- **agree but not clear** → straight to that verifier.
- **unclear** (non-claim margin < 0.4, an `UNCLEAR` pick, a non-English state, a `build_mismatch`) → the verifier, with
  no re-read against a coin flip.
- **Floors never move.** Blocker/high severity always escalates; mandatory seats always run — the panel floor (every
  seat's verdict reaches the integrator; a NOT_READY is a P0), the domain sibling's hostile-payer and cross-document seats, the
  doctrine read of every page-1 fact, the final gate. Every PMO row escalates. **Role and determination claims are floors
  (CEO decision E10) in document, document-set and payer work (F9):** a claim that carries a role-bearing figure
  (authorized, denied, requested, approved) or a determination verb is severity `high` by default, so it always reaches a
  verifier and never stands on Jev plus one auditor — the one class where Jev's misses cluster (§13). Software and
  data-product claims are not floored by role words ("the PR modified 3 files", "latency was reduced" are not payer
  figures; the re-gate found the word floor sending every software claim to a verifier). The kit's
  `claimSeverity(c, cls)` reads the class from `SLOTS.CLASS` (or its second argument): `document` and `document-set` —
  the domain sibling runs as `document` — apply the word floor, and so does an unfilled or unknown class (it fails closed). It is a
  hard floor inside `ladder()` — a claim item is never below it, whatever `severityOf` says — and, in every class, it
  also marks `high` a claim whose source was OCR'd (`ocr`), an authorized figure cited to a non-LETTER `source_class`, a
  page-1 or central claim (`central`), and a claim the audit marked INFERRED (F11): fields every claim-audit item
  carries. In the domain sibling a figure or verb read from OCR text also goes to the verifier, with the page image (its
  `rails.md` §5, not included in this repo). Jev orders their queue; it never shortens it.
- A disagreeing item the seat never re-read is a bad return (`ladder().bad`): fail the unit or send it back, never
  treat it as standing. An unavailable, unclear or agree-but-not-clear item goes to the verifier with no re-read — it is
  never a bad return (OM-04). A null, empty, `partial` or `failed` return from a seat is an ESCALATE, never
  `stands` (the kit's `mustEscalate()`; COMMON: a blocked part comes back `partial` or `failed` with `could_not_check[]`).
- `JEV_LADDER=off` (a failed re-gate, or a build change mid-round) → nothing stands on Jev's word that round; Jev still
  orders and seconds.
- Where it saves (09-28, 179 concrete claim and determination pairs × 3 reps — the measured questions): agree-and-clear
  88–89% of items; the seat right 160 of 160 behind opus and sonnet (which made 0–1 errors, so that measures the set, not
  the ladder) and 158 of 159 behind haiku (the one shared role-swap miss cleared). Every other kind escalates, so its
  second buys an order and a disagreement signal, not a skipped verifier.

## 9. Never Jev
Generating a value, **value extraction** (selecting a value, even among spans code found — for a payer document the
authorized figure comes from the payer's letter, read by a person or a Claude reader), arithmetic, totals, counts, date
math, units, numeric comparison, writing text, round-level stop tests and budgets, and any owner item: code, a receipt
or a human settles those, and Jev never "confirms" a computed number (`[calc: …]` figures are masked before `verify`,
the CLI adding each receipt's inputs and formula to `sources` as a labelled entry; a unit resting on a computed
figure skips the cascade for the ARITHMETIC lane,
`cascade-gate.md`). Comparing a claim sentence with its source sentence **is** Jev's job, figures and dates included; so
is LOCATE — pointing at the line that holds a fact, never reading its value or role (§6). Extending Jev to value
selection is the owner's decision, not yet made. **Jev output is never training or distillation data** — TypeSafe's
customer agreement (clause 2.3(b), live 2026-09-23) bars using it to train or distill a model; `judgments.jsonl` exists
for threshold tuning only.

## 10. Failure — loud, never substituted
- **Exit 4 UNAVAILABLE** (single calls, after the CLI's own retries: 408, 429, 5xx and OpenRouter's transient in-flight
  402 are retried, each attempt capped at 20 s with jittered backoff, `Retry-After` honored; a malformed 200 is also 4) →
  that item is `unavailable` and escalates.
- **Bulk modes** (`filter`, `rank`, `verify --all`, `ask --all`, `second`) send one request per row, 6 in flight, each row
  with its own `--deadline`, and print every row in input order. A row Jev never judged prints `keep: null`,
  `status: UNKNOWN` with an
  `error` code (`unavailable`, `bad_answer`, `bad_call`, `auth`, `credits`, `no_key`) — it is `unavailable`, read, never
  dropped. After 6 unavailable rows in a row a breaker reports the unsent rows as `not sent` without calling the API. The
  batch exits 0 when it completes, however many rows are unavailable; the summary carries `unknown`, `unavailable`,
  `complete` and `build_mismatch`.
- **Exit 3** → stop the run and tell the owner: no key or auth (they run `jev setkey`), or OpenRouter credits exhausted
  (they add credits).
- **Exit 2** → a bad call (empty state, duplicate ids, bad `ask` JSON): fix it and re-ask; never invent a value.
- **Exit 127** → re-run once as `~/.local/bin/jev`; still 127 → stop, as preflight would.
- **`build_mismatch`** — a reply from a build the re-gate did not pass (§12) → the item escalates and the ladder is off
  for the rest of the round (RAIL NOTE). A re-gate cache or registry the CLI cannot read is not a build change: it says
  so on stderr once and every reply carries `"build_check": "unavailable"` (in `jev second` the row reads
  `unavailable`), so it escalates — never `build_mismatch` (FB-09).
- `verify` and `gate`: a draft Jev did not verify never routes `send`; a gate failure is `review`, never re-asked into an
  approval. Act on the `route` or `decision` field, never on exit 0 alone.

## 11. Tally and logs
Every kit schema's `jev` field and the state template carry:
`jev: calls <c> · agree <a>/<n> · clear <cl> · escalated <e> · disagreements <ids> → upheld <seat s / jev j> · unavailable <u>`
`n` counts compared verdicts only — triage `rank` and thresholded `filter` calls are calls, not comparisons; never-Jev
items are `not_compared`. In the round block, `escalated` is `ladder()`'s count (`escalate` plus `bad`), never the
CLI's tally figure: the CLI counts only measured questions as able to stand, but it cannot see the severity floors
(blocker/high) or `JEV_LADDER=off`.
The round block adds `· verifies skipped <v> · Jev $<x>`, x = `jev usage --since "$RUN_START"` (the stamp this round's
preflight printed; every round runs preflight) — all Jev spend on this machine since that stamp, hooks and other open
sessions included, so label it that way, or pass `--session <id>` for one Claude session's calls — its subagents share its id (the
output's `scope` says which); the campaign's Jev $ is the sum of its round blocks. Any reply in which
Jev ran ends with one `jev:` line. Logs: `~/.cache/jev/usage.jsonl` (per call: build, cost, request id,
session) and `~/.cache/jev/judgments.jsonl` (per answered question, joined on the request id) — re-route and re-tune
from them; never re-ask to re-route. Past 50 MB each moves aside to a dated name (nothing is deleted).
`jev second` warns on stderr when a verdict token appears inside a state — take it out and rebuild the row.

## 12. The build — float, check, re-gate
Always `jev-latest` (owner, 09-28): never pass `--model`, never set `JEV_MODEL` — preflight PARKs on a stray one.
TypeSafe warns that an alias can change answers with no change on your side and advises pinning a tuned version; the
owner chose to float, and two checks narrow the gap — for two questions only:
1. **Per round.** Preflight prints `JEV_BUILD` and runs `scripts/jev-regate`: the 179-pair golden set in `corp/golden/`,
   cached per build and per fingerprint (the golden set, the packing, the pass bar, and the registry text and criteria of
   the two questions it gates), ~10 s and < $0.01 on a new one. PASS (clear-and-wrong ≤ 2, clear coverage ≥ 80%; 09-28 on
   1.13-20260917: 1 and 161/179 on packing v1, 1 and 164/179 on packing v2) prints `JEV_LADDER=on`; anything else prints
   `JEV_LADDER=off`. Copy it into `SLOTS.JEV_LADDER`; the kit refuses to run `ladder()` without it. `jev-regate --help`
   prints help and exits; `--force` re-runs a cached build.
2. **Per reply.** Every reply's build is compared with a gated build, with no export needed: when `JEV_EXPECT_BUILD` is
   unset, the CLI accepts any build that has a PASS entry in `~/.cache/jev/regate.json` for the current question
   fingerprint, and a reply from any other build is `build_mismatch`. Copy preflight's `JEV_BUILD` into `SLOTS.JEV_BUILD`
   for the record; a reply or row carrying `"build_mismatch": true` goes into the item's `jev_build_mismatch` (§10). (An
   `export` in one Bash call is gone by the next; the CLI's own check is why nothing depends on one.)
**What the gate does not cover.** It checks `claim_support` and `determination` — 2 of the registry's questions. Every
other question is provisional on every build: it adds work and never removes it (§5). Its wording and its pass bar were
chosen on these same 179 rows (R1 X17; `corp/golden/README.md` says never to tune on them), so its numbers are
optimistic until a separate tune slice exists.
A build change between rounds is a RAIL NOTE and **two** re-gates (CEO decision E15): the CLI's (`jev-regate`, which
preflight runs) and the hooks' (`python3 ~/.claude/skills/jev/scripts/hooks-regate.py --apply`, which preflight names in
its WARN but never runs: the CEO runs it — it versions `hooks_config.json`, the owner's configuration, before
rewriting it — and logs the RAIL NOTE). Until the hooks' re-gate passes, every Jev hook is
warn-only: the airlock denies nothing, belay and `jev-gate` never block, and `jev-notice` says so on every turn. The
1.1 bar holds only on a build that passed.

## 13. Measured record (09-28, build `typesafe/jev-1.13-20260917`)
Source: an internal benchmark folder (not included in this repo) — 179 concrete and 31 abstract labeled items; Jev × 3 identical reps;
opus, sonnet and haiku seats × 2 runs in different orders; two adversarial critics; the web's practice in its
research notes. The Claude seats had the owner's domain doctrine and project memory in context and Jev did
not; `sonnet` was Sonnet 5 (harness < 2.1.284) and `opus` Opus 5.5 (inferred). n is small: directions, not decimals.
- **Cost and speed — Jev, by ≥ 3 orders of magnitude.** 1,493 judgments cost $0.0124 in 2 min 15 s (p50 417 ms); a
  Claude seat spent 240k–1.0M tokens and 52–282 s per ~121 items.
- **It can't cut corners.** Every item gets the model (1,493 of 1,493). Two of five haiku seats did cut corners (one
  swapped judgment for a regex script and reported "judged"; one left 2 items at a default); 0 of 14 opus/sonnet seats did.
- **It holds still.** Identical input moves p 0.013–0.033 on average; shuffled options changed 0 of 32 picks; batch vs
  single, 0 flips. Rerun in a new order, sonnet flipped 45% of abstract labels, haiku 26%, opus 6%.
- **It abstains instead of guessing wrong.** On abstract calls Jev made 0 confident calls; sonnet made 7–8 and haiku 12–14
  confident-and-wrong ones; opus both abstains and commits usefully (17 of 20 confident calls right). Abstention, not
  calibration: Jev's p there is no better than a constant 0.5.
- **Haiku-grade accuracy at ~1/1000 the cost** on concrete pairs: claim/source 97%, determination 95%, vs haiku 96–100%.
  Jev replaces haiku reads; it never replaces an opus or sonnet seat. (The 09-28 haiku seats ran before Claude Code
  2.1.293, so on Haiku 4.5. Haiku 5.5 (10-07) runs /corp-jev's mechanical seats only, `model.md` H1, and the rule stands:
  no haiku agent of any version takes a label or a second opinion.)
- **Claude is better at** accuracy on concrete pairs (opus 100%, sonnet 99–100%; Jev's misses cluster on determination
  verbs, modified ↔ reversed, and role swaps, provider ↔ caregiver — why the doctrine floors stay) and at framing (an
  assertion in the state moves Jev's p, not opus's or sonnet's — why states stay bare). A clear agreement can hide a
  shared miss: behind haiku, one role swap cleared with Jev at p 0.94.
- **Abstract judgment:** asked folded, only opus beat chance (AUROC 0.74); asked unfolded, Jev reaches 0.82–0.84, with no
  Claude counterpart run yet. Jev stays a disagreement signal there, never the judge.
- **Community corroboration (R3, 09-28):** a done-check that computes transcript facts first and then asks Jev scored
  AUROC 0.976 against 0.777 for the same judge on wording alone — facts go to code, judgments to Jev.

## 14. Commands
```bash
jev second < verdicts.jsonl              # Job 2: {"id","kind":"claim|determination|keep_reject|blocker|edit_kind|pmo_status|panel|arithmetic","state","verdict"} per line
jev filter --q claim_support --all < claims.jsonl        # the pre-screen; {"id","state":"Claim: … Source sentence: …"} per line
jev filter --q keep_reject --all < flags.jsonl           # keep/reject with the measured criteria; "Flag: …" rows (the 1.1 bar is provisional)
jev rank   --q triage_payer_letter -k "$(wc -l < sources.jsonl)" < sources.jsonl   # order only; -k = the list's length
jev pick   --q class_pick -f request.txt                 # the class, in your first message (new wording, unmeasured)
jev pick   --q panel_verdict -f seat-state.txt          # display only (unmeasured, never compared); the verdict is the worst of the seat's own per-failure calls
jev ask --all questions.json < rows.jsonl   # one question set over many {"id","state"} rows; see --help for questions.json
jev yes 'Does `request` comply with `policy`?' -f case.json      # backticks → single quotes; case.json = {"policy": "…", "request": "…"}
jev verify --all < drafts.jsonl          # {"id","sources","task","draft"}; [calc: …] figures masked, each receipt's inputs added to sources (run from the work folder, or --calc-root); re-drafts: add --escalated
jev gate --q go_act --veto -f action.json   # §GATE on a row the owner's reply named by number: the CLI recomputes fields, md5s and the share-check/census receipts first; Jev can only block
jev gate --q go_act -f action.json       # §GATE on a row adopted in the owner's own words: same recompute, then the full 0.9 / 0.1 gate; action.json = {state: {go: {reply, row}, act (with src, the staging folder), deliverable}, receipts: {share_check, census}}
scripts/quote-gate --docs map.json < rows.jsonl   # every quoted pointer on its page (code, no Jev); --receipts: every [calc:] receipt input, quote + role word; --drafts: every drafted [calc:] figure vs its receipt's result
scripts/census <files…>                  # every part of every file a third party receives: gated markers + leftover [src:/[calc: = 0
jev ask locate.json                      # LOCATE: one request, locate_line (line ids + NONE) + locate_any; see jev ask --help
jev ping; jev usage --since "$RUN_START" # preflight gate; the round block's $ figure (machine-wide)
```
The CLI's `--help` for each verb is the interface of record; the registry ids (LOCATE's and the gate checks' included)
live in `corp/jev-registry.json`.
