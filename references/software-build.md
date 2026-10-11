# Class: software-build

Build something new — a site, an app, a feature area — from a brief. Exercised: C2 (a product website).

## Ground truth comes first: `TRUTH.md`

Before any writing, the orchestrator compiles a **claims allowlist** from repo docs, ledgers and
measured numbers. It wins every conflict with the design and copy specs: *every sentence in the
build must be derivable from this file.* Owner rulings are appended to it as dated law **before**
the rework is dispatched. Without it, builders invent product claims and the panel has no oracle.

## Department contents

- **Recon** — enumerate every surface exhaustively up front (screens, states, breakpoints, themes,
  empty/error paths, copy blocks), plus the reference pack this thing has to beat.
- **Builders** (sonnet at `medium` for well-specified units, `high` for harder or longer ones; opus for genuinely hard
  multi-file semantic work — `model.md`) — one branch per surface.
- **Claim audit** — every sentence against `TRUTH.md`; every promised link, asset and integration
  exists; every number has a committed receipt.
- **Panel seats:** visual/consistency · **message/purpose** · a11y (keyboard, contrast) ·
  truth-vs-`TRUTH.md` · regression.
  The purpose seat is not optional here: it is the seat that caught the product's whole point buried
  past three opus critics and a full integrator pass, because **truthfulness graded one-directionally
  makes "be more cautious" the safe move for every graded agent.** Burying the promise is a P0.
- **Integrator** — plus a size budget: declare the ceiling up front (diff size, API surface, page
  weight, word count) and report `size_before / size_after` against it.

**Jev in this class** (`jev.md`): **Job 1** — `jev rank` triages which files a change touches first (edit-kind
mechanical/judgment, sets sonnet vs opus) before a builder brief is written; batch point is one pass over the
surface list in Recon, before builders spawn. **Cascade** — drafted site or product copy goes through `jev verify`
against its `TRUTH.md` rows before the claim audit (`cascade-gate.md`). **Job 2** — one `jev second` per seat seconds
every claim-audit VERIFIED/MISMATCH against `TRUTH.md` and every panel seat's regression call before it reaches the
integrator. **Never Jev:** word counts, diff-size numbers, the size budget itself — those stay mechanical and receipted.

## Capture rig — CAPNOTE

Any capture tool must **report back the geometry and state it was asked for**. Print `innerWidth`
(and theme, and scroll position) with every screenshot; a shot whose reported geometry ≠ requested
geometry is **quarantined, not analysed**. Headless Chrome clamps sub-500px window widths to
`innerWidth=500` while still writing the PNG at the requested size — 2 of 7 defect tickets in C2
were the instrument, and got dispatched to a fixer as real work.

Define the capture procedure **once** as a script constant interpolated into every brief, so all
agents measure the same way.

## Proof

In-render proof is the whole game in this class: host-side rendered before/after with sampled pixel
values in the report, byte-diffed against the prior round's capture. Source-level assertion is not
done. Builders never self-grade.

## Rails (paste into the kit's `CLASS_RAILS`)

Every sentence must be derivable from `TRUTH.md`; owner rulings are appended to it as dated law before rework
is dispatched. In-render proof or the hunk is reverted; builders never self-grade. Any capture rig prints the
geometry it was asked for, and a mismatch is quarantined, not analysed. Declare the size budget up front. Ship
discipline: **one coherent change per branch** off the campaign base, merge-base asserted before the first line,
never `git stash`; **a draft PR is allowed — merging, publishing and deploying live are the owner's**, and
repo/account configuration is a named GO-only class. The work folder (state, receipts, evidence) is
`~/<project>-audits/<date>-<slug>/`, never the product repo, passed as preflight's third argument (CEO decision E17);
without one, or with one inside the repo, preflight PARKs (F7).

## Departments this class usually skips — name them, do not silently drop them

A greenfield build has no shipped product to test against, so say so explicitly, one line each with the reason:
**synthetic test corpus — SKIPPED** (no data pipeline under test; ground truth here is `TRUTH.md`);
**QA in the guest — SKIPPED** unless the build produces a binary to run (a site's checks are host-side lint,
link and a11y passes in the browser harness — say which);
**red team over QA's output — SKIPPED**, folded into the panel's regression and truth seats.
Anything you do run, name too. An unmentioned department reads as covered.
