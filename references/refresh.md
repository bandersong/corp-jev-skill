# /corp refresh — keep what /corp absorbed current

`corp/sources.json` lists every outside source /corp
has absorbed — `url`, `last_absorbed`, `refresh_days`, and what /corp took from it (the file's `_format` key documents
the fields). A row is due once the days since `last_absorbed` exceed its cadence. Preflight's `[fresh]` lines report the
count, the oldest row and the due rows, and suggest `/corp refresh`; they never PARK.

Run it when the owner types `/corp refresh`, or when preflight lists due rows and the owner agrees. It is a documentation pass: no
experiments or benchmarks unless the owner asks, and it follows every /corp rail (rule #1, the perimeter, Jev seconds).

1. **Re-read.** Every due row, plus — always — the Anthropic models overview and Claude Code model-config pages and the
   TypeSafe and OpenRouter `llms.txt` indexes (new pages appear there first). Fetch raw Markdown where the site offers
   it (`curl <page>.md`); save every raw copy under `<work folder>/<date>-corp-refresh/raw/` so each claim stays
   checkable; use `jev-browse` for pages that need navigation. Save third-party files under safe names (`harness.md`
   §Third-party material).
2. **Digest.** Write `DIGEST.md` there: per source, what changed since `last_absorbed`, with the URL, a locator into the
   raw copy, and the /corp text it touches; graded *changes a rule* · *changes a number* · *wording only* · *nothing new*.
   One `jev second` batch over the digest's claims against their source lines before it goes to the owner.
3. **Propose.** The diffs for /corp, any sibling skill, the jev skill doc, your global CLAUDE.md and memory, as one
   numbered E0 batch — each with before/after and its source line. A change that would move a Jev question, a criterion or
   a threshold names the re-gate it triggers: a reworded `claim_support` or `determination` re-gates automatically at the
   next preflight (the gate's fingerprint carries their registry text); any other question has no gate, so it stays
   provisional until a labeled slice measures it; a new bar needs its labeled slice.
4. **Apply on the owner's GO,** in one pass: version every file first (commit, or a dated copy), bump `last_absorbed` only for
   rows actually re-read, add a row for any new source, write the CHANGELOG entry (what changed, why, before/after,
   sources), and run the kit tests and `scripts/preflight.sh --self-test` (hygiene, not an experiment).

**Propagation is part of every /corp change, not only a refresh:** the same pass updates sibling skills, the jev skill doc,
your CLAUDE.md and memory — or records why one of them needs no change.

**At every Claude model release,** re-audit the model-specific lines (`model.md`: the tier map, effort per role, the
unattended clause, the think-first line) one component at a time; Anthropic's guidance is that prompts are per-model
artifacts and a line that is load-bearing on one generation is cruft on the next. Tag each model-specific line with the
model it was written for. Keep the core `SKILL.md` of /corp (and of any sibling skill) at or under 12,000 bytes (`wc -c`) so the whole
contract survives compaction; preflight PARKs when one is over.
