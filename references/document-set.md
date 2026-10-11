# Class: document-set

A packet: many documents, human reviewers in the loop, a recipient with a mailbox. Exercised: C5
(13 docx + pptx + PDF pack, 5 rounds, ~130 agents). Read `document.md` first — everything there
applies. This file is what a *set* adds.

## Persona critics, not generic ones

Build a persona file from the **real** reviewer's transcript voice — how they read, what they hate,
what they know about the org's systems — and run one critic per artifact wearing it, transcript on
disk beside them. Findings in the persona's own grammar:
`{file, category, location, X_says, wants_instead}` — every finding must say what they want
**instead**. Add a **HARD LIMITS** section so the persona can never waive a legal floor.
Yield across three rounds: 201 → 131 → 327 findings.

Between personas and the floors, run a **triage** integrator with four dispositions:
ACCEPT / ACCEPT-MODIFIED (keep the obligation, move the work into a system they already use) /
REJECT (violates an enumerated floor or re-litigates a frozen decision — one-line reason) /
ANNOTATE-ONLY. The floors are enumerated in the prompt and are never cuttable. C5: 201 findings,
**0 legal floors cut**, several workload complaints solved the reviewer's way.

## The human-reviewer round

N parallel readers over overlapping transcript slices ("read past your end boundary if a decision is
mid-discussion") → one `effort:'xhigh'` editor that dedupes seams and settles reader disagreements
**by going back to the source text**. The recovered decision log becomes its own deliverable. By
round 4 the humans were reviewing the **memo**, not the artifacts — one decision per item, no menus,
no veto paths. Reviewer decisions land in `MEETING_DECISIONS.md` **before** any rebuild; a FROZEN
section builders may not touch.

Ship an **annotated review copy** per deliverable: body **byte-identical** to the shipping copy
(validator asserts identity), plus `> WHY:` under every provision the reviewer will challenge — what
requires it, what it costs in practice, who does it, where the record lives.

## Cross-document integrity

- The **integrator's own output is builder output for gating purposes.** In C5 the integrator
  fabricated a citation into a shipping policy, its annotated twin and a derived list; a bogus
  statute subsection survived builders *and* the persona panel.
- **Class-scoped residual sweep.** Designating a single source of truth does not delete contradicting
  instructions elsewhere: after file-scoped workers land, sweep every *defect class* across the whole
  tree. Four documents still carried killed instructions, one of them the approval card.
- Byte-verify every embedded asset against its source before shipping.

## Delivery — the packet is the deliverable

Three sibling trees whose names make a mis-send hard:
`SEND TO <recipient> (final)/` (numbered PDFs only, plus one merged file) ·
`OFFICE MATERIALS (not for submission)/` · `ANNOTATED/`, with an `INTERNAL - ` filename prefix.
A named `MISSING - put the signed X here.txt` placeholder so a real gap cannot be mistaken for an
enclosure. Grep counters as the exit gate.

Then verify the **recipient's** experience: C5's merged 62-page packet navigated by PDF bookmarks,
invisible in the owner's viewer and the recipient's — replaced with a printed contents page.
**Verified-correct is not verified-usable.**

## Deploy — the recipe core rail 6 points at

Deploying to a shared office folder is the one irreversible act in this whole skill (this rail exists
after an incident in which a blind `rsync -a` overwrote reviewers' annotations).

1. **Default posture is no deploy at all:** build in an isolated folder and hand the owner the path. A deploy
   is a separate step the owner authorizes, per destination, per round.
2. **Detect humans mechanically, at ASSEMBLY time and again immediately before the write** —
   `scripts/share-check.sh <folder> <CAMPAIGN_START>`: `~$` lockfiles at any depth, `<cp:lastModifiedBy>` from each
   docx's `docProps/core.xml` (Word stamps a person's name there; our builds carry a `BUILD_STAMPS` identity via
   `apply-edits --stamp`), and mtime since the campaign began. `CAMPAIGN_START` is the `YYYYMMDDhhmm` stamp CORP_STATE
   got when the campaign was created — never a round's `RUN_START`. **Our own earlier deploys are not humans (CEO
   decision E16):** every deploy leaves `<folder>/.corp-deployed.json` (step 4), and share-check exempts a file whose
   current md5 equals the manifest's, while a changed md5 is reported as a HUMAN EDIT and a missing file as GONE — stop,
   and adopt the edit as the base (step 5); a file not in the manifest follows the lanes above. **A NEW folder (E7):**
   `mkdir "<target>"` **without `-p`** — it fails if anything already exists there, which is the atomic absent-check —
   then run share-check on that new, empty folder. Never share-check the parent client tree: a colleague saving in a
   sibling folder is not a conflict, and its mtime would stop every deploy. **Non-zero exit = do not write.** C5 built
   its send folder from a stale copy of a reviewer-edited letter because the check only ran at deploy.
3. **A lockfile is a red light for the whole folder**, not an obstacle to route around, and
   `Resource busy` is a person, not an error.
4. **§GATE, then archive first, never delete** (`cascade-gate.md`): the deterministic checks, which
   `jev gate` recomputes itself (share-check and `scripts/census` exit 0 from their output files, every
   file's md5 hashed from disk equal to the md5 the row names for it, the target folder and the other
   fields string-equal to the E0 row the owner's GO adopted — E12 — and the act's `src` folder listed: nothing in
   it the row does not name, F1), then one `jev gate --veto` on a row the owner's reply named by number (Jev can
   only block; a row adopted in the owner's own words takes the full gate) — only an `approve` proceeds; `block`
   or `review` stops the write and goes back to the owner. Into an existing folder:
   `mkdir -p "<folder>/_ARCHIVE <date> <label>"` first (FA-12: without it, `mv` of a single file renames
   that file instead), then move the current contents — never an earlier `_ARCHIVE` folder or the
   manifest, never an adopted human base — into it server-side (share-check prints the exact command on a
   green light), mirror that archive locally, copy the act's `src` — the staging folder §GATE listed,
   holding only the row's files (CEO decision F1) — recursively:
   `rsync -a --update --backup <act.src>/ <folder>/` (never `--delete`; F7: the earlier printed form had
   no `-r` and copied nothing), count both ways and report the two numbers (on a share that refuses the group or mode
   change `rsync -a` can exit 23 with the bytes landed — `--record`'s md5 check is the receipt either way). Last,
   `scripts/share-check.sh --record <folder> <act.src> <campaign> [<stamp>] --action <action.json>` writes
   `.corp-deployed.json` — never by hand, and only for the files the adopted row names: it refuses (exit
   1, nothing written) unless the copied folder is the act's `src`, it holds no file the row does not
   name, and every row file landed at the row's md5 — and it versions the previous manifest (E16, F1). The
   gate decision is the deploy's RAIL NOTE.
5. **Human edits are the BASE, not the conflict:** pull them, diff them, preserve them verbatim, build
   this round on top — a file we deployed whose md5 no longer matches `.corp-deployed.json` is one.
   **Adopt it, never argue with the exit code (CEO decision F3):**
   `scripts/share-check.sh --adopt-human <file>` records that human-edited file's current md5 as the new
   base in the folder's `.corp-deployed.json` (who and when from its `lastModifiedBy` and mtime) and
   prints a RAIL NOTE line for the ledger — copy it into CORP_STATE the same turn (it versions the manifest
   first, and refuses while a Word lock is in the folder). Later checks pass while
   the reviewer's file is unchanged; a new change to it, a lock, or any other human trace still stops the folder. A
   rebuild on that edit goes to a NEW version file beside the reviewer's — never over it — deployed under its own E0
   row through §GATE. A draft handed over for signature (an E0 `handover` row) comes back this way too:
   the signed copy is adopted first, then its census and md5 checks run (E9). If the destination is
   locked, write a clearly-marked sidecar now, retry the canonical name later, reconcile, and tell the owner in
   plain words which file is live.

**Jev in this class** (`jev.md`): **Job 1** — `jev rank` over the documents in the set to order the cross-document
integrity sweep; batch point is one pass at set-assembly, before the sweep is assigned. A flag's owner is the
document its location names; only a cross-document flag's owner is routed, in the sweep's one end-of-pass
`filter --all` (a registry question per row — is this document the one to edit? — pending in the registry; until it
lands the sweep's owner assigns it by hand), never a per-flag `pick`. **Job 2** —
one `jev second` per seat seconds each persona critic's verdict and each cross-document conflict's keep/reject.
**Gate** — every GO'd deploy passes §GATE; assembling the `SEND TO` folder in the work folder is internal staging (no
GO, no `jev gate`) and runs the deterministic checks — share-check at assembly, `scripts/census`, md5s, send-set only.
**Never Jev:** manifest and enclosure counts, page and exhibit numbers, dates.

## Rails (paste into the kit's `CLASS_RAILS`)

Everything in `document.md`, plus: enumerated legal/compliance floors are never cuttable; the integrator's own
output is builder output for gating; annotated twins are byte-identical in the body; the send set holds ONLY
what gets sent. **Nothing under the shared folder is written, moved or deleted by any agent this round.** A
deploy the owner authorizes is **archive-first — never delete** — lock-checked with
`scripts/share-check.sh <folder> <CAMPAIGN_START>` (a NEW folder: `mkdir` it without `-p`, then check that new, empty
folder — never the parent tree), with the human-edit check re-run at assembly time, human edits treated as the base, not
the conflict (adopted with `share-check.sh --adopt-human <file>`; a rebuild on one is a new version file beside it,
never over it), §GATE passed immediately before the write, and `.corp-deployed.json` written after it.
