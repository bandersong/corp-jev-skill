# §MODEL — tiers, effort per role, and what they cost

Contents: Law 2 in full · Tier map · Effort per role · Haiku 5.5 — where it runs, and where it never does · Law 3:
quality first, no waste · Pricing a topology · Vendor numbers (09-28, Haiku 10-07) · Old patterns

## Law 2 in full — explicit model and effort on every agent call
A bad `model:` hard-fails the agent; an omitted model inherits the session tier (on a Fable session every worker runs
at Fable's list price); an omitted effort runs Opus 5.5 and Sonnet 5.5 at `medium` in Claude Code. The bundled
`workflow-authoring` skill says to omit `model:` — override it here and say why in the script. Separately, Claude Code's
safety classifiers can re-run a flagged request on a fallback model (Opus 5.5 → Opus 5 or Opus 4.8; Sonnet 5.5 →
Sonnet 5): record any fallback notice in the round's model mix. The `jev-tier-guard` hook (not included in this repo)
warns on a spawn with no model or a mis-tiered one.

**Two dispatch paths, and only two set effort (CEO decision E11).** A Workflow `agent()` takes `model:` and `effort:`
directly. The Agent tool takes only a `model` and a `subagent_type`: effort comes from the agent type's definition
(Claude Code's subagent docs: a definition's `effort` "Overrides the session effort level"). So a seat spawned through
the Agent tool MUST use its `corp-*` type from `~/.claude/agents/` (the table below maps role → type); each definition
sets `model:` and `effort:` in its frontmatter and carries the perimeter and the unattended clause. Pass the type's own
model as `model` too — a per-invocation `model` overrides the definition's, so a different one re-tiers the seat (the
tier guard warns on it, and on a /corp-jev seat spawned without its `corp-*` type). A bare Agent spawn runs at the session's
effort, which the report must disclose, and the round block records the effort each seat
actually ran at (`/tasks` names each subagent's model and, when its definition sets one, its effort; Claude Code ≥
2.1.242), never the one intended. If a session that started before `~/.claude/agents/` existed cannot find the types,
restart Claude Code (the same docs: a running session may not detect a newly created agents directory). Preflight's
`[model]` lines report whether all seven definitions pin a model and an effort (`7/7`).

**The versioned source is `corp/agents/` (CEO decision F7).** `~/.claude/agents/` is what the harness, the tier guard
and preflight read, but it sits outside the skills repo, so the committed copies in `~/.claude/skills/corp-jev/agents/`
are the source: edit there, commit, then install into `~/.claude/agents/` (version what is there first; never overwrite).
Preflight compares each `corp/agents/corp-*.md` with its `~/.claude/agents/` twin by md5: `[model] corp agent types =
their committed source …, md5, 7/7`, or one `[model]` line per drifted or missing type with the exact reinstall command
(it copies the installed file aside with a dated name first, then `cp -p` from `corp/agents/`) and a WARN — run them,
then restart Claude Code. A seat whose installed definition drifted from the source runs at whatever the drifted copy
says. Every definition also tells its seat that the brief opens with COMMON and ends with a schema
to return as JSON — the orchestrator pastes both (`kit-run common`, `kit-run schema`; `harness.md`, F8).

| Agent type | Model | Effort | Seats |
|---|---|---|---|
| `corp-final-fable` | fable | `max` | the final gate's two Fable seats |
| `corp-final-opus` | opus | `max` | the final gate's Opus 5.5 seat (and a Fable seat's fallback) |
| `corp-judge` | opus | `xhigh` | critics, skeptics, red teams, panel, integrator, verifiers, ledger red-team, cascade redraft |
| `corp-doc-builder` | opus | `xhigh` | document builders (the text a human signs and sends) |
| `corp-sw-builder` | sonnet | `high` | software builders; a structural edit `apply-edits` cannot express (a Workflow `agent()` may set `medium` for a well-specified unit) |
| `corp-auditor` | sonnet | `high` | claim audit, extraction, reconciliation, OCR sweeps, grading, recon / PMO (its prompt ends with the think-first line) |
| `corp-mech` | haiku | `medium` | mechanical work with no judgment: applies supplied edits, runs named commands, collects files and outputs, locates code (anything needing a judgment comes back unapplied). Haiku 5.5 since 10-07 on a measured tie; fallback below (§ Haiku 5.5) |

## Tier map (Claude Code ≥ 2.1.284)
`opus` = Opus 5.5 (default effort `medium`) · `sonnet` = Sonnet 5.5 (Claude Code default `medium`; API default `high`) ·
`fable` = Fable 5.1 (default `high`) · `haiku` = Haiku 5.5 from Claude Code 2.1.293 on the Anthropic API (default
`medium`; all five effort levels; Haiku 4.5 below 2.1.293 and on Bedrock / Vertex / Foundry). Preflight's `[model]` lines print the harness version and what each alias runs
on it — inferred from the harness version and Anthropic's published floors, not resolved by a call; copy them into
CORP_STATE, and a change between rounds is a RAIL NOTE. Never pin a full model ID in `model:` (a bad one hard-fails
with no fallback). Probe top-tier access with one throwaway agent before a fan-out of ~10 or more agents (an access
failure once killed 26 agents in 56 ms; a probe costs ~60k tokens), and before the final gate's Fable seats.

## Effort per role
Quality first: the greatest possible output, always.

| Role | Model | Effort | Note |
|---|---|---|---|
| CEO — this thread | the session's model (Opus 5.5 or Fable 5.1) | the owner's session setting | raise it for a hard synthesis step if needed; an effort change keeps the cache on the 5.5 models and Fable 5.1 |
| Recon / PMO | sonnet | `high` | extraction plus classification; opus only when the analysis is the deliverable (a read-only audit) |
| Document builders — the text a human signs and sends, argument text included | opus | `xhigh` | the judgment-heavy step that writes the deliverable (Law 3 below); declared in the topology line |
| Software builders | sonnet | `medium` for well-specified units, `high` for harder or longer ones | opus for hard multi-file semantic work; Sonnet never at `max` (it starts its own review subagents there) |
| Claim audit, extraction, OCR sweeps, grading | sonnet | `high` | the brief's last line: "Think the problem through before you answer." (the kit's `SLOTS.EFFORT_AUDIT`; Sonnet 5.5 often answers structured multi-step tasks without thinking first at `low`/`medium`; at `high` that line brings it close to `xhigh`) |
| Mechanical edit application | none | — | `scripts/apply-edits`: a fully determined plan belongs to code |
| An edit that needs document-structure judgment | sonnet | `medium` | |
| Critics, skeptics, integrators, panel, ledger red-team, cascade redraft | opus | `xhigh` | judgment is the product; never moved down for cost |
| Final gate | 2 × fable + 1 × opus | `max`, all three | three lenses, below; all three always run; added, never swapped; `corp-final-fable` / `corp-final-opus` or a Workflow `agent()` at `max` — never a bare Agent spawn |
| Mechanical seats: fully specified old→new edits, short named commands, collecting files, locating code | haiku | `medium` | `corp-mech` / `SLOTS.MODEL_MECH`; the brief says "return each output verbatim — the output string only" |
| Typed labels | `jev` | — | below haiku, not a fallback to it — Haiku 5.5 included: no haiku agent ever takes a label or a second opinion |

**The final gate** reads the final build after the panel; each seat returns `PANEL_VERDICT` against the closure contract.
Its lenses are fixed: **Fable A** — the hostile recipient and the purpose: would it survive the payer, the reviewer or the
user it goes to, and does it do the job the owner stated? **Fable B** — process and evidence: would a long autonomous campaign
on this reach a true exit — every receipt real, every gate biting, nothing relayed or stale? **Opus 5.5 at `max`** —
whole-artifact coherence, and the single most important defect left. Any P0 → back to the integrator, and the round
repeats, up to the round ceiling declared at intake (CEO decision E14; a domain-specific sibling skill may count it in its own rail) — at the ceiling
the P0 goes to the owner queue with its fix (STAGED) or the campaign PARKs; a P1 → fixed, or queued with its fix. A
Fable seat that still fails on access after one probe runs on opus at `max` (`corp-final-opus`), and the report says so.

Fable runs the main thread when the owner picks it, and the final-gate seats; builders never run on Fable, and any other
Fable worker needs the owner's explicit authorization for a bounded round. Anthropic reserves
`xhigh` and `max` for measured gains; here they are the owner's quality-first rule, unmeasured against `medium` on our
work — log them as such, never cite them as measured. At low or medium effort on long agentic work Sonnet 5.5 may stop to
check in; inside a workflow no one can answer, which is why the kit COMMON carries the unattended clause.

## Haiku 5.5 — where it runs, and where it never does (H1, 10-07)
Goal (10-07): adopt the new Haiku judiciously, never in place of Jev, and stretch tokens as far as quality allows. Law 3 lets cost decide only on a measured tie, so Haiku runs where one was measured and nowhere else.
- **Measured** (bench harness, graders and cost script not included in this repo; code-graded against ground truth; Haiku 5.5 named in every Haiku transcript): 27 runs on the `corp-mech`
  type, n = 3 per cell (a direction, not a decimal) — fully specified old→new edits with three traps (ambiguous,
  absent, judgment), five short named commands, file collection with a missing file, and four locate-in-code
  questions plus a collected table. **Haiku `medium` tied Sonnet `low` on every graded check** (6 of 6 runs, all with
  COMMON). Haiku `low`: 2 of 3 scout runs wrote files the brief forbade (Jev rows outside the named file), and 1 of 3
  runs without COMMON wrapped a correct md5 in an annotation; Haiku `high` (no COMMON) did the same once. With COMMON and
  "the output string only" in the brief together: 0 of 6 annotated (the phrase alone is untested). Haiku `medium`
  returned `partial` on 2 of 3 scout runs (it could not run the verifier its own Jev disagreement asked for) against 0
  of 3 for Sonnet — honest under COMMON, but more CEO follow-up. Cost (list price, prompts under 100k): Haiku
  $0.007–0.020 a seat vs Sonnet `low` $0.128–0.206, means 1/12.5. Haiku seats peaked at 89k prompt tokens: above 100k
  Haiku bills 5× ($0.50 / $2.50) and the ratio falls to about 1/2.5 — keep mech briefs short.
- **Runs on haiku:** `corp-mech` and `SLOTS.MODEL_MECH`, and nothing else, for what was measured: fully specified
  old→new edits `apply-edits` is not run on, short named commands returned verbatim, collecting files with a manifest,
  locating code to file:line. Structural edits stay `corp-sw-builder` / sonnet `medium`; test suites stay sonnet until
  benched. `assertSlots` throws when a build, audit or judgment slot names haiku.
- **Fallback** (harness < 2.1.293, or preflight's not-the-Anthropic-API WARN): a Workflow `agent()` with `model:
  'sonnet', effort: 'low'` (set `MODEL_MECH` / `EFFORT_MECH`), the measured baseline; through the Agent tool,
  `corp-mech` with `model: 'sonnet'` — it runs at the type's `medium`, and the tier guard's override warning is expected.
- **Never on haiku:** Jev's two jobs (labels, the second opinion: Haiku never replaces Jev, at any version); builders,
  claim audit, extraction, OCR sweeps, PMO / recon, critics, the panel, the integrator, verifiers, the final gate, and
  any payer seat of a domain-specific sibling skill other than `corp-mech`, and the recall-critical greps of a software audit's lanes
  (`software-audit.md`). Vendor ceiling: Terminal-Bench 4.0 39.2% vs Sonnet 5.5's 70.6%.
- **Admitted later only on a bench of its own** (a seeded-recall bench for anything whose miss is invisible downstream):
  the condense lane between audit lanes and synthesis, a first-draft rung under sonnet in the non-payer cascade, and
  non-payer extraction behind `quote-gate`. Until then they stay on their current tiers.

## Law 3 — quality first, no waste
The best output always. Cost only breaks a tie where quality is measured equal — and no such tie exists for document
builders. Anthropic's Sonnet 5.5 page reports parity at the top of its effort range ("Sonnet 5.5 at Max effort even
performs comparably to Opus 5.5"; "At higher settings, it can perform comparably at a similar cost") and says "Opus 5.5
remains clearly stronger at complex, open-ended work requiring sustained judgment": no tie at lower cost, and none
measured on our work (/corp-jev bars Sonnet from `max`). So the builder that writes a deliverable's text runs opus at
`xhigh`; Sonnet 5.5 at `high` keeps software builders, extraction, claim audits (with the think-first line) and PMO.
(CEO decision 09-28 under the owner's quality-first rule.) Judgment seats stay on the top tier. A typed label over short states is a `jev`
call, never an agent. No waste means the smallest topology that closes the question — a 3-agent pass that answers beats
a 30-agent pass that also answers — and breadth is not waste: with a wide backlog, fan out wide on the right tiers. The
CEO reads, decides, eyeballs worker output and writes the synthesis itself, and never spawns an agent to verify what it
can check by reading.

## Pricing a topology
Before any fan-out, state the topology (agents × tier × effort) and the expected token cost; after it, record the
actual `budget.spent()` in CORP_STATE for that pass. Price from this campaign's measured spend per agent by tier; in
round 1 say "unmeasured on the 5.5 models — estimate from the last campaign's ledger". The old anchor (~134k tokens per
agent-pass: 2.27M over 17 agents in an all-opus Opus 4.x run) is historical; both 5.5 models finish the same work in
fewer tokens. Claude Code's "Large workflow" warning (more than 25 agents, or more than 1.5M projected tokens) is advice,
not a cap.

## Vendor numbers (09-28) — rationale, not instructions
From Anthropic's launch pages (raw copies not included in this repo).
Opus 5.5 results are at `max` effort unless noted.

| | Sonnet 5.5 | Opus 5.5 | Fable 5.1 | Haiku 5.5 (10-07, at `max`) |
|---|---|---|---|---|
| List price per MTok, in / out | $2 / $10 | $4 / $20 | $10 / $50 | $0.10 / $0.50 (prompts ≤ 100k; $0.50 / $2.50 over) |
| GDPval-AA v2.1 (knowledge work) | 1844 | 1846 | 1735 | 1620 (1277 at `medium`) |
| FrontierCode 1.1 (hard coding) | 52.1% at `xhigh` (46.2% at `max`) | 54.4% | 50.3% | 46.4% |
| Terminal-Bench 4.0 | 70.6% | 66.4% (at `xhigh`) | 55.8% | 39.2% |
| CursorBench 4.0 | 55.5% | 57.8% | 51.8% |
| OSWorld 2.1 | 80.1% | 81.8% | 80.7% |

Sonnet 5.5's `max` score is lower than its `xhigh` score because at `max` it more often ran Claude Code's code-review
skill across many subagents (Anthropic's footnote), so the Sonnet-vs-Opus gap on hard coding is ~2 points, not ~8.
Anthropic positions Opus 5.5 for complex work requiring careful judgment and Sonnet 5.5 for well-scoped everyday tasks
and polished documents; it reports that 16 of 18 Opus 5.5 research reports cleared a bar where any invented figure or
quote failed, and that Fable 5.1 and Opus 5 cleared it in no attempt. These numbers are the vendor's, not ours; our own
09-28 rerun had a Sonnet 5 seat flip 45% of abstract labels against opus's 6% (`jev.md` §13).

## Old patterns
Before harness 2.1.284 the `sonnet` alias ran Sonnet 5 and document builders ran on opus (CHANGELOG, not included
in this repo, 2026-09-28 evening). That branch is closed: the flip was confirmed on 2.1.284 (a `sonnet` probe quoted `claude-sonnet-5-5`), and
preflight no longer prints a `DOC_BUILD` line. For a few hours on 09-28 the rewrite had document builders on Sonnet 5.5
at `high`, on a misread of the launch page ("≈ Opus 5.5 on knowledge work at half the price"); the same night's
integration moved them back to opus `xhigh` (CHANGELOG).
