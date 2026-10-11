# §EVIDENCE — measurement discipline (law 1 in full)

Contents: In-artifact proof · Gates that bite · Instruments and refute rates · Receipts · RELAYED · STALE · Rates ·
Claims and unknowns · Findings · Measure the premise · Operator contract

A claim without a receipt did not happen. A receipt is a file and line or page, or a command and its output, from this
session. One campaign accumulated seven falsified "defects", and four of the orchestrator's own beliefs were fiction.

- **In-artifact proof** is mandatory on any rendered or generated surface: before/after with sampled values in the
  report; for prose, text extracted from the REBUILT artifact. The integrator reverts hunks without it — a source-level
  assertion is not done (two waves once shipped zero-pixel no-ops under green gates). Byte-diff every claimed fix against
  the prior round's capture before a panel spends a round on it.
- **A green gate contradicting reality is a worse defect than the miss.** The first deliverable of any fix is why the
  gate lied; the new gate bites on the real path — revert → RED, restore → GREEN, both outputs pasted — and ships a
  self-check, because "the repo is clean today" passes equally if the gate stopped biting.
- **Prove the instrument sees the class** before its counts mean anything (a contiguous byte-grep once scored the
  rank-1 leak as caught). A capture rig reports back the geometry it was asked for; a shot whose geometry differs from
  the request is quarantined. **Record the per-stage refute rate** in the state file: a stage passing ~100% is a finding
  about the harness, and the next stage is told not to trust it (a 139/139 verifier preceded a panel that found 30 issues).
  Perf A/B discipline: `software-release.md`.
- **Every load-bearing number needs a receipt with a repro command.** Sweep inherited numbers at the start of a pass,
  your own ledger's included (one number lived in 18 comments citing each other, 20× wrong). Counts are derived, never
  remembered. Keep the falsified-artifact list, and never resurrect an entry without the control that killed it. After a
  fix, measure every adjacent ordering and sweep the defect class tree-wide.
- **RELAYED is not a receipt.** Before a synthesis reaches the owner, code lists every number, line range, count, id
  and status sentence in it and greps each against receipts this thread itself read (tool output, captured files). A
  figure found only in a subagent's report is RELAYED: re-read it at source, or strike it. A figure found nowhere is
  UNSUPPORTED. This is string matching, not a Jev call.
- **STALE.** A sentence about state that changes on its own — a PR or merge queue, CI, a running job, a portal or
  authorization status, a share's lock or owner — is re-read in the round that reports it. Anything older is refreshed,
  or reported with its timestamp ("as of 14:02").
- **Rates.** Every rate names its sampling rule and its denominators. Only a random draw estimates accuracy; "cannot
  tell" rows are counted and kept out of both sides; a gold label is never taken from the output being graded. An
  unattended job (a re-gate, a tuning sweep) records one of `did_not_run`, `could_not_run`, `ran_nothing`,
  `ran_rejected`, `ran_committed`. A convenient number is a bug until proven; report joint metrics, never conditioned-only.
- **The quote gate.** A pointer's quoted sentence must appear on the cited page — `scripts/quote-gate`, code, before any
  Jev call; a miss is MISCITED with the failed match as its receipt (`jev.md` §6). A computed figure is a chain, not a
  source: every input of its `[calc:]` receipt carries its own pointer and declared role, and `quote-gate --receipts`
  checks each quote and role word (CEO decision E1) — an arithmetic check over an unsourced input proves nothing — and
  `quote-gate --drafts` ties the figure as drafted to its receipt's `## result` (re-gate RG-08).
- **Claims and unknowns.** Unverifiable = cut, not softened; paraphrase presented as a quote is forbidden. No
  fabrication: never invent a record of a past event, never backdate, never assert a control, log, meeting or form not
  shown to exist. Flag, never guess: `[OWNER VERIFY: …]` is the only permitted answer to an unknown, counted every
  round by `scripts/census`; audit any agent that claims it closed them — the first check is whether it invented the
  answers.
- **Findings.** Report every failure against the closure contract or the requirements, including the ones you are unsure
  of, each with a severity and a confidence (high / medium / low); report nothing else — no style preferences, no praise.
  An empty list is a valid answer. The integrator and the ladder do the filtering: a finder told to be conservative
  silently loses recall.
- **Measure the premise before obeying** (every builder brief carries this, through the kit): if your measurement
  contradicts the instruction, stop, move what you built into `<work>/corp/_reversed/<label>/` — never delete it (rule
  #1; `jev-airlock` denies an unversioned delete, but only warns while the Jev build is un-regated, `jev.md` §12) — and
  report the reversal with numbers. That is a success, not a
  refusal. Implement an unmeetable rule verbatim, let it fail, and rebut with measurements; never silently reinterpret.
- **Operator contract** (full form: `software-release.md`): no operator ends its turn before the run's manifest exists on
  disk and has been read back; incremental writes, host-side evidence pulls, stale output dirs quarantined; a lane that
  cannot run prints its exclusion and reason; exit 0 with a silent gap is the one unacceptable outcome. Your inverse: arm a
  background wait on the output file and keep working.
- **Agreement is not evidence.** A Jev agreement, or two seats agreeing, never replaces the receipt.
