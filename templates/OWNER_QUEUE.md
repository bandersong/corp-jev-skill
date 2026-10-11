# OWNER QUEUE — <deliverable>, <date>

Only decisions a human can make: a secret, a name, a price, a signature, a merge, a clinical or
legal judgment. Ordered by my judgment, security and irreversibility first. If it is a number that
exists somewhere on this machine, it is **LOOP-CLOSABLE** and it does not belong here — I close it
before I report.

Every decision row about something in the artifact is tied to its gated marker (`[OWNER VERIFY: …]`
/ `[OWNER DECISION NEEDED: …]`; in a domain-specific sibling skill, its own markers such as
`[REVIEWER TO CONFIRM]` / `[DATA NEEDED]`), named in the
Marker column, so the queue and the artifact cannot drift. Open markers this round: `<h>` census hits
(`scripts/census`, every file and part) · `<m>` rows with a Marker. The two counts are not meant to
be equal: one gated assertion repeated as its twin in every enclosure that makes it (doctrine rule
15) is several hits and one row. The rule is a mapping (CEO decision F10): **every census hit maps to
one row** — a twin maps to its original's row, named by the file and part in the census `hits` (which
lists every gated marker; other classes list 25 and count the rest in `hits_omitted`) — and **every
row with a Marker has at least one hit**. A hit no row claims, or a marker row with no hit, is the
drift; a twin repeated across enclosures is expected and is never a mismatch. Rows with no marker in
the artifact — a §GATE review, a declined cascade unit with no marker yet, the E0 act rows below —
carry `n/a`.

Rows also arrive from the Jev floors, never decided by them: a §CASCADE **declined** unit (the
sources don't cover the task — for a payer document, usually a letter not yet in the folder), a
source gap the claim audit confirmed on a cascade double failure, and a §GATE **review** (the full
gate record attached). A cascade double failure itself is a drafting dispute: the claim audit
decides it, and it never lands here unless the audit confirms a source gap.

| # | Decision | Marker | Kind | Owner | Deadline | If unanswered | Default at T-minus |
|---|---|---|---|---|---|---|---|
| 1 | <one sentence, decision-ready> | <`[OWNER VERIFY: …]` as it stands in the artifact, or n/a> | HUMAN-ONLY | <who> | <when> | <consequence> | <fallback, or NONE — blocks ship> |
| 2 | | | | | | | |

## E0 batch — answer these together, one GO
Everything below that I can execute inline the moment you say go. N interrupt points become 1.
Each row that would run an act names the act in full, written before you answer — your GO adopts
exactly these rows, and I run nothing a row does not name. **A send is never a row here:**
uploading, faxing, e-mailing or e-filing anything to a payer, plan, agency or other third party —
through a portal or otherwise — is yours to do; I stage it in `SEND TO`.

Act rows continue the decision table's numbers (decisions 1–n, acts n+1 …), so one number never means
two rows: a GO is read as act-row numbers only. The Verb cell is exactly one verb from the list, bare
— nothing added: the gate compares it with the E0 verbs ("handover (draft)" blocks), so "draft for
signature" goes in the Act column. A deploy's files are the copies in its staging folder (the
`SEND TO` folder the act copies, `act.src`), and that folder holds nothing else: the gate lists it
and blocks on any file this row does not name (CEO decision F1).

| # | Act | Verb | Target path | Recipient | Record id | Files + md5 |
|---|---|---|---|---|---|---|
| <n+1> | <one sentence; a handover says "draft for signature" here> | <deploy / handover / portal write / browse write / config change> | <abs path or URL> | <who, or n/a — a portal or browse write into our own system names none> | <id, or n/a> | <abs path> · `<md5>` — one pair per file the act writes or sends |

Say `GO <n+1>,<n+3>` and I run those rows at the next dispatch. A reply that names no row — and not
the act itself — runs nothing: I will ask "GO which rows?". Your words and the rows they name are
copied into `CORP_STATE.md` § DECISIONS the same turn; each act passes §GATE against its row first,
and anything a rail forbids gets a RAIL NOTE at that moment, naming the rail, your authority, and
what stays your work.

## Split by clock (when a clock exists)
- **Before <event>:** items <n, n>.
- **After <event>, regardless:** items <n, n>.

## Not asked
Decisions I made for you rather than queue, with the basis, are in `CORP_STATE.md` § DECISIONS,
recorded **as inferred**. Reverse any of them and I will re-run the affected department.
