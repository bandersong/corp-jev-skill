# CORP_STATE — <deliverable> (<target>, <class>)

<!-- Copy to the campaign's DURABLE working folder, beside the deliverable (software classes:
     ~/<project>-audits/<date>-<slug>/, never the product repo). Never a session scratchpad, never
     a live client share, never Desktop/Documents/Downloads, never ~/.claude/skills. Created on the
     first pass; each round's block is written BEFORE the next round dispatches, and the session
     never ends with one unwritten.
     Author line matters: RESUME only adopts a queue this campaign wrote. No Author line = not
     yours until content and deliverable match prove otherwise.
     After ANY compaction: re-invoke /corp-jev (and any domain-specific sibling skill), read this file's tail and corp_state.json,
     and re-read the reference for the next department — before the next dispatch.
     The CEO is the only writer of this file and of corp_state.json; workers return statuses in
     their schemas. The work folder is a git repo: commit before every write here (rule #1 —
     appends count too). -->

**Author:** /corp-jev, <date>. **Class:** <class>. **Mode:** <vibe|full|hard|deadline|cheap>.
**Deliverable:** <path>. **Clock:** <deadline or none>. **Round ceiling:** <n, declared at intake — full 3, hard 5,
deadline = the clock; a round with no P0 stops the loop (a stricter domain-specific sibling skill: no P0 and no P1); the ceiling with one open → STAGED
or PARKED, never another round>.
**Campaign start (CAMPAIGN_START):** `<YYYYMMDDhhmm, local — date +%Y%m%d%H%M, written once when this file is created>` —
`share-check.sh`'s `<start>` at every assembly and deploy for the whole campaign; never a round's RUN_START. Keep the
stamp on this line: preflight's `[state]` line reads the first line naming it.
**Machine state:** `corp_state.json` beside this file (campaign_start, queue statuses, decision ids + FROZEN, falsified
ids, refute rates, runIds + resume commands; shape in `harness.md` §State) — written by the CEO only.
Work folder under git: `yes — <path>`; last commit before this round's block: `<sha>`.

## Campaign
Run `<wf_id>`, <date> <start>–<end>, <N> agents, <errors> errors, **<tokens> subagent tokens**,
model mix <opus xN @effort / sonnet xN @effort / fable xN @effort> · classifier fallbacks: <none | which seat → which model>.
Topology declared before dispatch: <agents × tier × effort> — expected <cost>.
(One of these paragraphs per workflow run. Spend is not optional: the report states spend per pass.)
Receipts: `corp/results_by_agent.json`, journal `<.../subagents/workflows/<wf_id>/journal.jsonl>`.
Inputs map: `corp/INPUTS.md`. Source of truth: `<build script or doc path>`.
Preflight: `<PASS | PARK — which check, which remediation>`. Execution: `<host | guest — declared>`.
Jev (§JEV): `jev: calls <c> · agree <a>/<n> · clear <cl> · escalated <e> · disagreements <ids> → upheld <seat s / jev j> · unavailable <u>` — `escalated` = `ladder()`'s escalate + bad, never the CLI's tally figure.
Verifies skipped by the ladder: `<v>` (measured questions only) · Jev $`<x>` (machine-wide since RUN_START, hooks and other sessions included — or `jev usage --session <id>`, say which).
Jev build (JEV_BUILD): `<build jev-latest resolved to, as preflight printed>` — copied into `SLOTS.JEV_BUILD`; the CLI flags a reply from a build with no re-gate PASS (`build_mismatch`) → the item escalates, ladder off for the round, RAIL NOTE (an unreadable re-gate cache reads `unavailable`, not `build_mismatch`); changed since last round → RAIL NOTE + both re-gates: the CLI's (preflight runs it) and the hooks' (`hooks-regate.py --apply`; until it runs, preflight WARNs and every hook is warn-only).
Jev hooks: `<gated on JEV_BUILD | WARN-ONLY — tuned on <build>, re-gated <when>>`.
Claude tier map (preflight `[model]`): harness `<version>` · `<what each alias runs, as preflight printed>` — changed since last round → RAIL NOTE.
Jev ladder (JEV_LADDER): `<on|off, as preflight printed after the re-gate>` — copied into `SLOTS.JEV_LADDER`; off → nothing stands on Jev's word.
Round start (RUN_START): `<ISO stamp THIS round's preflight printed on PASS>` — the round's Jev $ = `jev usage --since` it; campaign $ = sum of rounds. Never share-check's start (that is CAMPAIGN_START).
Freshness (preflight `[fresh]`): `<n sources · oldest <id> <d> days · none due | due: <ids> → /corp-jev refresh proposed?>`.
Cascade (§CASCADE, `corp/cascade.jsonl`): `cascade: units <n> · sent <s> · escalated <e> → sent <s2> · double-fail → audit <f> · declined → queue <d> · n/a <x>` · accept `<0.8>` · false accepts found by the claim audit: `<n, ids>`.
Gates (§GATE): `<n GO'd acts gated → approve a / block b / review r>` — each decision is a RAIL NOTE below; each deploy wrote `<dest>/.corp-deployed.json` for its row's files only (`--record --action`, F1). SEND TO assemblies (internal staging, no GO): `<n, deterministic checks passed; the folder listed = the row's files>`. Human edits adopted as the base (`share-check.sh --adopt-human`, F3): `<n — each one's printed RAIL NOTE line copied below>`.
Size budget: `<ceiling>` — before `<n>` / after `<n>`.
Merge-queue depth: `<n open PRs, n unmerged branches>` (report every pass; do not merge).

## Department log — one paragraph each: WHAT / WHY / receipts / evidence paths
- **<dept> (<model>)** — what it did, counts, what it found, what it rejected and why, receipt paths.
- **<dept> — SKIPPED:** <reason>. (Skipped is reported, never silently dropped.)

## Refute rates — per stage
| Stage | Items | Confirmed | Overstated | Refuted | Jev agree/clear/esc | Note |
|---|---|---|---|---|---|---|
| <stage> | | | | | <a>/<k>/<e> | ~100% pass = a finding about the harness; next stage is told not to trust it |

## Falsified artifacts — do not resurrect without new evidence AND the control that killed it
- <claim> — killed by <control / measurement / page>, <date>.

## CLOSED — settled, not re-derived next round (evidence per row)
- <item> — closed <date> by <receipt path>.

## FROZEN — decided; re-litigating one is an automatic REJECT
- <decision> — frozen <date>, authority <who>.

## DECISIONS — written the turn the answer arrives, each one dated
- **D<n>** <date> — <decision> — owner's own words: "<quote>" — changed: <what> — implemented: <where>.
- **D<n>** <date> — <inference made on the owner's behalf, recorded AS INFERRED> — basis: <why>.
- **GO D<n>** <date> — the owner's words verbatim: "<GO 1,3,4>" — adopted rows, copied verbatim from OWNER_QUEUE's E0 batch:
  `<row #: verb · target path · recipient · record id · file path · md5 (one pair per file)>` (one line per row). Only
  these rows are GO'd; a reply that named no row GO'd nothing ("GO which rows?" was asked).

## RAIL NOTES — rails bent under an explicit GO (every §GATE decision is one)
- Rail <n> bent on <date> under <whose> GO to do <what>. **Stays owner work:** <what>.
- GATE <date> — act `<verb target recipient record id>` under GO D<n> row <#>: deterministic, recomputed by the CLI
  `<fields · md5 per file · share-check rc (output file) · census rc (output file)>` →
  jev gate `<veto | full>` `authorized <p> · right_artifact <p> · recipient_matches <p>` (response `<id>`, $<x>) →
  **<approve | block | review>**.

## Open queue (owner) — see OWNER_QUEUE.md
1. <item> — HUMAN-ONLY | LOOP-CLOSABLE — deadline, consequence if unanswered, fallback.

## could_not_check — NOT CHECKED, by anyone, ever
- <surface> — why nobody could check it.

## Restart handoff (write BEFORE any restart)
In-flight runId: `<id>`. Resume command: `<exact command>`. Next session's ordered job list:
1. … 2. … 3. …

## Exit gates — all must be true for REPORT DELIVERED
- `scripts/census` on everything a third party receives (every part of every file): exit `<rc>`, gated markers `<n>`,
  catch-all hits `<n>`, leftover `[src:` / `[calc:` pointers `<n>`, unchecked `<n>` (all must be 0; the pointer strip
  ran first, counted); unfilled `<slots>` by grep: `<n>`.
- LOOP-CLOSABLE owner gates still open: `<n>` (must be 0 — close them yourself first).
- RELAYED or unreceipted figures left in the report: `<n>` (must be 0); STALE outside-state sentences re-read this round: `<n>`.

## Exit
<REPORT DELIVERED | STAGED | PARKED> — <what is blocked and what is needed to resume>.
