# /corp-jev — a corporation of departments for Claude Code

`/corp-jev` is a [Claude Code](https://claude.com/claude-code) **skill** that turns one big deliverable (a release, a
document packet, an audit, a data product) into a staffed process instead of a single long chat:

> builders → claim audit → hostile panel → trust-nothing integrator → fresh verification → owner queue

and keeps going until the result is **EVIDENCED** — every claim backed by a receipt you can re-check — not merely
"looks good to the model that wrote it".

## Why use it

A single agent that writes, checks and approves its own work will happily ship a wrong number with total confidence.
`/corp-jev` is built around the failures that actually happen when agents do long work:

| Problem | What /corp-jev does |
|---|---|
| The agent asserts success it never verified | **Evidence law**: a claim with no receipt (command + output, quote + page, test) "did not happen". |
| The author is the only reviewer | Separate **claim-audit**, **hostile-panel** and **integrator** seats that default to *refuted* and re-derive everything. |
| Cheap labels burn expensive tokens | **Jev** (a small typed-judgment model, ~0.4 s, ~$0.00002/call) does triage and gives a fast, non-LLM **second opinion** on every verdict before it ships. |
| Agents overwrite other people's files | **Rail 6 / share-check**: shared folders are read-only until a lock/mtime check passes; deploys are archive-first, never delete. |
| Agents act outward on their own | **Gate**: sends, merges, uploads and signatures are human-only; every "GO" must name the exact verb, target, recipient and file hashes (md5). |
| Long runs lose their place after compaction | A durable `CORP_STATE.md` ledger, a round log, and a core `SKILL.md` kept under 12,000 bytes so it survives re-attachment. |
| "Done" is a feeling | Three exits only: **REPORT DELIVERED**, **STAGED** (everything left needs a human), **PARKED** (a rail or the rig is broken). |

Use it for work where being wrong is expensive and you would rather pay for verification than for a recall: shipping
software, assembling a document/packet that someone will sign, auditing a repo, producing numbers other people will
rely on. **Don't** use it for a quick edit or a chat answer — it is deliberately heavy.

## What is in this repo

```
SKILL.md                 the core contract (laws, rails, departments, exits) — the file Claude Code loads
references/              detail per class and topic (jev, cascade-gate, evidence, harness, model, playbook, patterns, …)
agents/                  seven `corp-*` subagent types that pin model + effort per seat
templates/               corp-kit.js (Workflow helpers: SLOTS, COMMON preamble, schemas, ladder()), CORP_STATE, OWNER_QUEUE
scripts/                 preflight.sh, jev (CLI), jev-regate, quote-gate, census, apply-edits, share-check.sh, kit-run, + tests
golden/                  a synthetic starter set for the Jev re-gate (replace with your own — see golden/README.md)
jev-registry.json        every Jev question the skill asks, with bars and what each was measured on
sources.json             outside docs the skill absorbed, for `/corp-jev refresh`
```

**Classes** it can run: `software-release`, `software-build`, `software-audit`, `document`, `document-set`,
`data-product` (details in `references/<class>.md`).

## Requirements — read before installing

- **Claude Code** with the **Workflow** tool and subagents (the multi-agent fan-out uses it). A Max/Team-class plan is
  realistic: a full run launches dozens of agents. Cost is not minimized; quality is.
- **macOS** is the tested platform (Keychain key storage, a `launchd` host-quiet watchdog, Word/LibreOffice handling).
  The scripts are Python 3 / bash / Node with no third-party runtime dependencies except `python-docx` for the
  `.docx` tools (`census`, `apply-edits`).
- **An OpenRouter API key with credits.** The bundled `scripts/jev` calls TypeSafe's **System One / `jev-latest`**
  model through OpenRouter's `/api/v1/systemone` endpoint. The skill treats Jev as mandatory (rail 2): `preflight`
  PARKs if `jev ping` fails. Typical spend is a fraction of a cent per run of labels.
- This is **one person's working system, published as-is**. It is opinionated (it encodes a strict "never overwrite,
  never send, always version" workflow) and some rails assume tools you may not have (see *Not included* below).

## Install

```bash
# 1. the skill (the folder MUST be named `corp`: preflight finds its siblings relative to it)
git clone https://github.com/bandersong/corp-jev-skill ~/.claude/skills/corp-jev

# 2. the seven subagent types (they pin model + effort; the Agent tool cannot set effort on its own)
mkdir -p ~/.claude/agents && cp -n ~/.claude/skills/corp-jev/agents/corp-*.md ~/.claude/agents/

# 3. the jev CLI on your PATH, and your OpenRouter key
mkdir -p ~/.local/bin && ln -s ~/.claude/skills/corp-jev/scripts/jev ~/.local/bin/jev
export PATH="$HOME/.local/bin:$PATH"
jev setkey            # stores the key in the macOS Keychain; or: export OPENROUTER_API_KEY=sk-or-...
jev ping              # must succeed

# 4. self-test (no side effects)
bash ~/.claude/skills/corp-jev/scripts/preflight.sh --self-test    # expect: self-test OK
```

Restart Claude Code once so it picks up the new skill and agent types.

### Seed the Jev gate with your own data (recommended)

`golden/` ships a small **synthetic** set so the re-gate runs out of the box. Its pass/fail only proves the plumbing.
Before you let Jev's "clear-agree" stand in for a human re-read, replace it with ~150 pairs from your own domain
(format and rules in [`golden/README.md`](golden/README.md)). Until a build passes the gate the ladder is simply off and
every Jev-compared item gets a verifier — slower, never less safe.

## Use

In Claude Code, describe the deliverable in plain words. There is no flag grammar; your words are the dial:

```
/corp-jev release the 2.4 build of ~/code/myapp                       # software-release
/corp-jev audit this repo for security and correctness, adversarial   # software-audit, hard mode
/corp-jev fan out: assemble the board packet in ~/work/board-q4       # document-set, wider wave
/corp-jev just vibe it: first draft of the migration guide            # lighter mode
/corp-jev refresh                                                     # re-read the outside sources and update the skill
```

What happens, in order:

1. **Class** is named and seconded by Jev (`jev pick --q class_pick`).
2. **Preflight** runs: `scripts/preflight.sh <class> <target> <work folder>`. **PARK means PARK** — if a rail or the
   Jev gate is broken, nothing is dispatched.
3. A **work folder** (never your repo, a scratchpad, or Desktop/Documents/Downloads) gets `CORP_STATE.md`,
   `corp_state.json`, a git history, and an `INPUTS.md` the PMO department fills in.
4. **Departments** run in order — PMO/recon, ground truth, builders, claim audit, hostile panel, integrator, apply,
   synthesis + final gate — each as Workflow `agent()` seats with explicit model and effort.
5. Every verdict is **seconded by Jev** (`jev second`); a clear agreement on a *measured* question stands on its receipt,
   everything else goes to a verifier.
6. You get one of the three exits and a **founder/owner queue** (`OWNER_QUEUE.md`) of the decisions only a human can
   make, each with its artifact pre-written.

Nothing the loop does merges, publishes, sends, signs or deploys on its own. A deploy to a shared folder happens only on
your explicit `GO <row numbers>` against a row that names verb, target, recipient and file md5s.

## Run the tests

```bash
cd ~/.claude/skills/corp-jev/scripts && for t in test_agents test_apply_edits test_census test_jev test_quote_gate test_regate; do python3 $t.py 2>&1 | tail -2; done
cd ../templates && node corp-kit.test.js | tail -8
```

The tests run against local stub servers and never call the real OpenRouter API; `test_jev.py` takes ~100 s.

## Not included (and what that means)

- **Sibling skills** the core mentions: a domain-specific payer/clinical-documents skill, a `jev` skill with Claude Code
  **hooks** (`jev-gate`, `jev-airlock`, `jev-notice`), an "overseer" routing skill. Rails that reference them degrade to
  "if you have one". The `scripts/jev` CLI itself is fully included.
- The author's private audit folders, benchmarks and changelog. `references/patterns.md` and `jev.md` cite them by
  name as provenance; they are not needed to run anything.
- Any real documents. All fixtures and the golden set are synthetic.

## Honest limits

- Jev is a **second opinion, not a judge**. Its "clear" bar was measured only on two question types (claim-vs-source and
  determination); everything else is provisional and adds work rather than removing it. It never computes, extracts a
  value, or confirms a number — code does that.
- The measured numbers quoted in `references/jev.md` come from the original author's data and a small sample. Treat
  them as directions, not guarantees, and re-measure on your own domain.
- Heavy by design. If a task fits in one reviewed pass, don't use it.

## License

MIT — see [LICENSE](LICENSE). Jev / System One is a TypeSafe model reached through OpenRouter under your own account
and their terms; this repo contains only the client.
