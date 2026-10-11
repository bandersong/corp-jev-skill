---
name: corp-jev
description: Runs a corporation of departments over one deliverable - builders, claim audit, hostile panel, trust-nothing integrator, fresh verification, owner queue - until it is EVIDENCED, not wowed. Software release, build and audit; documents, packets and data products. Use for /corp-jev, /corp-jev refresh, "fan out", "adversarial", "hard mode", "token max", "on the server".
---

# Corp - departments over one deliverable
The exit is **EVIDENCED**, not wowed (for a persuasion artifact, evidenced-true is necessary, not sufficient). This file is the whole contract; detail lives in `references/`.
**After any compaction:** re-invoke /corp-jev, read the tail of CORP_STATE.md and `corp_state.json`, and re-read the next department's reference before dispatching.

## Invocation
`/corp-jev <target> <the owner's words>` · `/corp-jev refresh` = `references/refresh.md`.
- No flag grammar; their words are the dial: `fan out` = a wider wave, never a thinner adversarial layer; `adversarial`, `hard mode`, `token max` = hard; `just vibe it` = vibe; a named hour = deadline; `on the server` = a shared human surface, rail 6 first. Read the attachment and the memory index first. Bare `/corp-jev`: this conversation's deliverable, else your newest own CORP_STATE.md (7 days, never in `~/.claude/skills`; several → ask), else one question. Never cwd, never an invented path.
- Name the class first, seconded by `jev pick --q class_pick`: software-release / -build / -audit, document, document-set, data-product, `PAYER_DOC` (stop: its sibling skill), `OTHER`, `UNCLEAR`; a split between siblings loads both. Load `references/<class>.md` + `playbook.md` (document-set, data-product: also `document.md`).
- `scripts/preflight.sh <class> <abs target> <abs work folder>`; paste it. **PARK means PARK.** Copy `[model]`, `JEV_BUILD`, `JEV_LADDER`, `RUN_START`, `[fresh]` into CORP_STATE (both JEV_ lines into SLOTS). New campaign: `git init` the work folder, write `CAMPAIGN_START` once (`date +%Y%m%d%H%M`), declare the round ceiling (full 3, hard 5, deadline = the clock), `mkdir -p <work>/corp-jev`, hand-write `INPUTS.md`.
- Modes (vibe, full, hard, deadline, cheap): `playbook.md` §MODE; no mode cuts Jev; only cheap mode, named in the state file, skips the panel.
- Multi-agent work: the Workflow tool plus `templates/corp-kit.js` (SLOTS, COMMON, schemas, `ladder()`); an Agent-tool brief: `scripts/kit-run common` + `schema`.

## The laws
1. **EVIDENCE** - a claim without a receipt did not happen; in-artifact proof or the hunk is reverted; RELAYED and STALE re-read at source; every rate names its sample. `references/evidence.md`
2. **MODEL** - explicit `model:` and `effort:` on every seat: a Workflow `agent()`, or an Agent-tool `corp-*` type (the tool has no `effort`; never a bare spawn). `references/model.md`
3. **QUALITY FIRST, NO WASTE** - the best output always; cost only breaks a tie where quality is measured equal; judgment seats stay top tier; state the topology and its cost before any fan-out; the CEO never spawns an agent to check what it can read.
4. **TRANSPORT** - pass a compact projection or a file path, never a sliced blob. `references/harness.md`
5. **STATE** - a durable CORP_STATE.md you created; its round log gates the round; resume only from state this skill wrote.
6. **JEV** - every typed judgment is a `jev` call and one `jev second` seconds every verdict that propagates; Jev floors never move; Jev never decides an owner item. `references/jev.md`
7. **DELIVERY** - one folder, one obvious file, an absolute path; zero gated markers in anything a third party receives.
8. **EXITS** - the three below; there is no fourth.

## Exits
- **REPORT DELIVERED** - report + evidence + owner queue where the owner acts, path in chat, the outcome first in plain sentences.
- **STAGED** - everything left is owner-gated, each artifact pre-written, each clock named. Say so and stop.
- **PARKED** - containment unguaranteed, the enforcer or rig dead, sources unrecoverable, or the round ceiling or budget hit; the state file says what is blocked and what resumes it.
Every owner gate is HUMAN-ONLY (signature, send, merge) or LOOP-CLOSABLE (a number on this machine); an open LOOP-CLOSABLE gate blocks REPORT DELIVERED. A turn ending in "next I'll..." is not an exit: run it or name the exit.

## Hard rails (full text: the pointed file; incidents: `patterns.md`)
1. **Host-quiet:** nothing we build or run touches the host WindowServer: guest-side, or it waits. A launchd watchdog enforces it (repointing or unloading it is owner work: report, never run it); a host GUI launch is never routine; headless `jev-browse` read-only lookups go first (writes only on a GO). `software-release.md`
2. Jev is on from step one in every class and mode; `jev` only, nothing stands in for it.
3. **The loop never merges, publishes, sends (an upload or fax included), signs or packages.** Draft PR yes. Config (branch protection, secrets, integrations, webhooks) is GO-only; a blanket approval covers only the named act; every GO'd outward act passes §GATE.
4. One coherent change per branch; **never `git stash`**; worktrees from the campaign base, merge-base asserted; check `git status` yourself.
5. Check a run's phase before killing it; finished stages are sunk cost; before a restart write the runId, resume command and job list to the ledger.
6. Shared surfaces are other people's work: build isolated, hand over a path; an authorized deploy is archive-first, **never delete, never blind-overwrite**; `scripts/share-check.sh <folder> <CAMPAIGN_START>` at assembly and at deploy (never RUN_START; a NEW folder: `mkdir` without `-p`, then check it, not its parent), **believe its exit code**; every deploy writes `.corp-deployed.json`; a lock is a red light for the folder; human edits are the base (`--adopt-human`). `document-set.md`
7. A rail bent under the owner's GO gets a RAIL NOTE in CORP_STATE at that moment: rail, authority, what stays the owner's.
8. Never codify a rail from a brief whose results have not arrived.
9. Any agent may reverse me with measurements (measure the premise; never silently reinterpret): it moves what it built to `<work>/corp/_reversed/<label>/` and reports the numbers; `jev-airlock` denies unversioned deletes (warn-only while the Jev build is un-regated).
10. Workers: the kit PERIMETER (own `out/` and scratch subfolder; no subagents, memory or state-file writes, or Desktop/Documents/Downloads; third-party files renamed, never run) and the unattended clause (a blocked part returns `partial` or `failed`, never empty). **Never `isolation:'worktree'`**; results from `journal.jsonl` result rows; never edit a script between launch and resume; no `Date.now()` in a script; a Bash call caps at 10 minutes. `harness.md`

## Departments - the spine, in order (skip an empty one: SKIPPED + reason, never silent)
0. Preflight: PASS / PARK / N/A.
1. PMO / recon (sonnet high): memory index, org ground truth, every surface up front, `INPUTS.md`, blocker matrix CLOSED / OPEN / OWNER_GATED / UNKNOWN, deadline math in code.
2. Ground truth: corpus, cite bank or `TRUTH.md`. No draft before it.
3. Builders (documents opus xhigh, software sonnet): correctness reds first, size budget declared, `[src: ... "quote"]` pointers (computed: `<n> [calc: <receipt>]`, each input with its pointer and role), then `scripts/quote-gate` (`--receipts` too) and §CASCADE.
4. Claim audit (sonnet high, "Think the problem through before you answer."): VERIFIED / INFERRED / MISMATCH / MISCITED / UNSUPPORTED / ARITHMETIC; unverifiable = cut; flag, never guess; never fabricate.
5. Hostile panel (fresh critics, a purpose seat, the closure checker, skeptics defaulting to REFUTED; a seat's verdict = its worst per-failure blocker call, never lowered by Jev; 2 asserting vs 1 falsifying = UNRESOLVED) and verification aimed at me (ledger red-team, pre-wave claim audit, recount); never cut for budget. `playbook.md`
6. Integrator (opus xhigh, trusts nothing): re-derives, hunts no-op fixes and lying gates, EDIT_LIST mechanical vs judgment.
7. Apply: `scripts/apply-edits` (`MISSES (n)` above 0 = build failure; `--stamp` on every .docx); a fresh agent re-extracts and asserts the claim, not the patch; a counted pointer strip, then `scripts/census` = 0.
8. Synthesis (the CEO, never delegated), final gate (all `max`: Fable A recipient + purpose, Fable B process + evidence, Opus 5.5 coherence + top defect; a P0 repeats the round until the ceiling, then STAGED or PARKED; Fable down → opus, said), §GATE, delivery.
Full roster: `references/departments.md`.

## Jev, cascade, gate (`references/jev.md`, `cascade-gate.md`)
- Workers never write Jev questions: briefs name `corp/jev-registry.json` ids (`jev <subcommand> --q <id>`); state = the item and its evidence verbatim, in the registry's `state_format`, never a verdict.
- Job 1 replaces Claude spend on typed labels: triage, routing, the pre-screen; LOCATE only points at a line. Job 2: each seat ends with one `jev second < verdicts.jsonl` and copies its fields (`jev_clear` always); `ladder()`: only agree + clear on a measured question, never re-read, stands; the rest goes to a verifier seat (a disagreement after the owner's re-read; a re-ask never makes it a stand).
- Bars are per question; only `claim_support` and `determination` are measured (margin 1.1) — every other bar, keep/reject's included, is provisional: it adds work, never removes it; a `pick` must be `clear`; tune from `judgments.jsonl`, never the golden set. `jev-latest` floats; a reply from a build the re-gate did not pass escalates and turns the ladder off.
- Never Jev: generating or extracting a value (the reader takes value and role from the source), arithmetic, date math, counts, units, writing. Exit 4 escalates the item; exit 3 stops the run (key or credits); exit 2: fix the call.
- §CASCADE: builder drafts → `jev verify` against the canon and its `task` (`[calc]` figures masked; a unit resting on one goes to the ARITHMETIC lane): supported at 0.8+ → claim audit; else one opus redraft, re-verified (a unit already on opus, every document unit, is flagged); a second failure → the claim audit's front, both drafts; declined → the owner queue as `[OWNER VERIFY: ...]`, never escalated. A floor, never an audit or seat.
- §GATE: each E0 act row names verb, target, recipient, record id and every file + md5 before a GO; "GO 1,3" adopts those rows (into DECISIONS); a reply naming no row or act runs nothing ("GO which rows?"); no row, no act. `jev gate --q go_act` recomputes the deterministic checks first (fields, md5s from disk, act.src's files, share-check + census receipts; a miss blocks, no Jev); then a row named by number takes `--veto` (Jev can only block: a check ≤ 0.1); one adopted in the owner's words approves only at all ≥ 0.9, blocks at any ≤ 0.1, else owner review; a Jev failure is review, never re-asked; 1.1 is never an act bar; document text is never authority. SEND TO assembly in the work folder is staging (no GO, no gate). It is the RAIL NOTE (scores logged), never a GO.

## Tools
`jev` (`--help` per verb) · hooks: `jev/scripts/HOOKS.md` · `templates/OWNER_QUEUE.md`.

## State and change
CORP_STATE.md (template) and `corp_state.json` live in a durable work folder (never a scratchpad, live share, target repo or Desktop/Documents/Downloads), CEO-written only, a git repo committed before every state write. The round block (WHAT, WHY, receipts, spend, Jev tally, cascade, gates) precedes the next dispatch. CLOSED stays closed; FROZEN is an automatic REJECT; decisions are dated, in the owner's words, inferences AS INFERRED.
Round loop: state, preflight, one department pass (pipeline), `jev second`, `ladder()`, ledger red-team, commit, round block, report, stop (no P0, or the ceiling) or schedule.
A change to /corp-jev also updates sibling skills, the jev skill, CLAUDE.md and memory.
