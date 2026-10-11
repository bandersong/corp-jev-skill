# Class: software-release

Ship an existing product. The one class the old skill was written for. Exercised: C1 (a desktop app release).

Contents: Extra rails (VM serialization, guest runner, capacity, exit teardown) · Department contents · Gates · Perf,
claims and the operator contract · Host-quiet, the full doctrine · Rails (paste into `CLASS_RAILS`) · Jev in this class

## Extra rails (orchestrator-checked; `scripts/preflight.sh software-release <repo> <work folder>` covers the watchdog, presence, state location, capacity and `CORP_GUEST_CHECK` — not the three below)

- **The work folder is never the repo** (CEO decision E17): `~/<project>-audits/<date>-<slug>/` holds CORP_STATE.md,
  `corp_state.json`, the receipts and their git history; a state commit on the product branch is a commit straight to
  the working branch. Pass it as preflight's third argument: without one, or with one equal to or anywhere inside the
  repo, preflight PARKs (CEO decision F7); preflight reads an existing campaign's `CAMPAIGN_START` back and never
  mints a new one per round.

- **VM serialization.** UI/perf capture lanes are exclusive: one driver, no builds in flight during
  timing. **Concurrent guest gate runs are NOT fine** — 8 shard operators each "in its own shard"
  all hammered one VM (~9 concurrent scrubs, load 15–25 on 6 cores, one sheet at 16 GB, kernel
  killed the runner) and voided the corpus verification run — **0 plants verified of ~81k** (the
  ledger said 81,112, the manifest 81,099; that discrepancy is itself one of the four falsified
  numbers, so do not quote either as a receipt). State a concurrency ceiling, serialize
  heavy lanes strictly one at a time with the whole machine, cap per item, and pull evidence
  host-side every 10 items so a guest death costs nothing.
- **Guest runner provisioned and proven** before any department depends on it: uv-managed python
  matching the host venv, mirrored deps + models, synced tree + host-built products. Prove with an
  import sweep, one gate of each class, then the FULL registry — guest-vs-host tally deltas are
  provisioning bugs, diagnose before proceeding. **Keep the recipe out of tree** (`~/<project>-audits/`
  or the state file): the loop never merges, so a doc committed on a campaign branch is stranded by
  construction. Before rewriting one, check whether it already exists on another ref —
  `docs/VM_GATE_RUNNER.md` is 17 KB on 135 of 782 refs and on none a fresh checkout of the default branch sees, and four later
  scripts cited it as authority anyway.
- **Capacity:** free disk on host and guest before dispatch (a guest hit 2.0 GiB mid-campaign),
  cores vs planned concurrency, top-tier access probe before a fan-out over ~10 agents.
- **Exit teardown:** the campaign's watchdog stays loaded only while the campaign runs. Unloading or
  repointing a launchd job is **owner work** — report the state, hand the owner the one-line command, never run it.

## Department contents

- **Recon/PMO** — blocker matrix from the release plan, issues/PRs, ledger, registry receipt,
  signing/license docs. Plus the merge-queue depth and the critical-path ship chain. Enumerate the whole
  release chain, not just the code: every gate in the registry, build, sign, notarize, store metadata,
  licensing, privacy strings, install / first-run / uninstall. That is where C1's five certain-rejection
  ship blockers lived, and all five were document-truth.
- **Builders** — correctness reds first, then feature/design lanes, one branch per unit.
- **Ground truth = test-data dept** (host, pure file generation): a difficult, convincing synthetic
  corpus — the classes this project was ever burned by, plus precision stressors — with a
  **machine-checkable ground-truth manifest `{doc, plants:[{type,value,part}]}`, every plant
  byte-verified** (unzip/grep proof), **deterministic one-command regeneration, generators
  committed**. State the known gaps out loud (a header-only JPEG makes EXIF gates pass vacuously).
- **QA** (guest, serialized): end-to-end product workflows against the corpus — process → verify
  output against EVERY manifest plant (grep all parts including metadata and media) → restore /
  roundtrip → refusal and edge lanes → keyboard-only pass. Every row reached or an enumerated
  deviation. A lane that cannot run **prints its exclusion and reason** — prefer the harness's own
  SKIP vocabulary to a new filter that can self-trip other gates.
- **Claim audit** — artifact-vs-reality on the shipping surfaces, not just the code: bundle id vs
  IAP product id, promised links that exist, stated system requirements against the code path that
  actually refuses, every marketing number against a committed receipt with a repro command. The
  five certain-rejection blockers in C1 were all document-truth, found *after* the pass.
- **Red team** (host, over QA's OUTPUT files): adversarially re-extract from processed artifacts —
  encodings, residual metadata, auxiliary parts. Fresh eyes, no builder rationale.
- **Integrator, this class** (core rules plus): runs the **FULL registry in the guest** and names every red
  vs baseline; **new reds get fixed or escalated, never skip-listed**; **orphan (unregistered) gate sweep with
  a set-difference proof**; **amendment / label uniqueness** checked.
- **Panel seats:** correctness · truth/claims · **decision-usefulness** (purpose seat: can the
  owner act on this report?) · regression-vs-prior-round.
- **Parity audit** before believing a corpus score: enumerate every lane of the validated reference
  implementation against the shipped one — `PRESENT / MISSING / PARTIAL / NA` × risk ×
  `PORT_NOW / PORT_LATER / OWNER_DECISION`, evidence per row. Then hand-craft 2–3 probes per
  newly-covered class; a corpus score is silent about what it never tested.

## Gates

Every gate ships a **bite proof**: a critic injects a violation → gate goes RED → restore
byte-identically (`git diff` empty) → GREEN, both outputs pasted. A gate that cannot go red is
itself a P0; a proof that *passes* under the mutation is worse than none — throw it away. Sweep for
orphan (unregistered) gates with a set-difference proof.

## Perf, claims and the operator contract — full forms

- **Perf: paired same-session A/B only** (alternate bundles, wiped state, n≥4/side). Baselines are COMMITTED
  DATA with per-lane provenance (round, tree, runs); a same-tree baseline is refused; a cross-session move is a
  rig observation, never a code-attributable regression. A 4× "cold-launch regression" died as a VM-session
  artifact this way, and a long-quoted model-load figure died against n=6/n=5 with proven eviction.
- **Claims lexicon + claims gate + gate self-check:** an explicit ALLOWED/FORBIDDEN phrase law in every
  doc-builder brief, plus a stdlib grep gate over docs, site copy and string literals, wired into CI. The first
  version was blind to "planned", multiline strings and negation, and was wired into nothing — so the gate ships
  with its own self-check.
- **Operator contract, full form:** capture/QA operators may not end their turn before the run's manifest exists
  on disk and is read back (poll with sleep loops; subagents get no notifications — say so in the brief).
  **Web-health precheck before capture** (assert the app's render mark fires; dead → one named deviation, not 26
  rows of corpse frames). Stale output dirs are quarantined, never blended. Incremental writes every N items,
  host-side evidence pulls every ~10. **A lane that cannot run PRINTS its exclusion and reason — prefer the
  harness's SKIP vocabulary to a new filter that can self-trip other gates.** Exit-0-with-a-silent-gap is the
  one unacceptable outcome; five operator bails were caught only because a manifest had to exist on disk.

## Host-quiet — the full doctrine (core rail 1 points here)

The rail: **nothing this campaign builds or runs may register with the owner's WindowServer.** What breaks it,
observed: gate scripts, the registry runner, freshly built binaries, render/capture harnesses, and any
`open`/`.app` launch — several of them "headless" in name and Dock-flashing in fact. Written doctrine
alone was breached again within the hour it was written. **Only the mechanical enforcer
stopped it**, and then there was no further breach in ten days of continuous agent activity.

- **The enforcer** is a launchd watchdog that kills (a) any executable under a build-products tree and
  (b) host python running gate / registry / red-team scripts. **Patterns are ANCHORED TO THE EXECUTABLE**
  — a v2 that matched on arguments would have killed a developer's own `xcodebuild`.
  Never match the user's installed apps.
- **It must live in durable storage.** The live job has pointed at a wiped session scratchpad since some
  cleanup, `KeepAlive=true`, exit 127 on every respawn, unnoticed for ~3 weeks. That is why the preflight
  proves a **kill**, not a PID.
- **The host does:** git, builds (xcodebuild/gradle), pure file generation (python-docx/openpyxl/PIL — never
  AppKit/Quartz/tkinter imports), ssh/scp to the guest. Nothing else executes on it.
- **Where the work runs:** every execution lane in the guest (`CORP_EXECUTION=guest` plus a `CORP_GUEST_CHECK`
  command that proves the guest is up), or you are on the host — in which case the enforcer must be proven, and
  the owner must not be at the keyboard.
- **A GUI launch is never routine**, watchdog or no watchdog: it is guest-side, or a step declared in
  `CORP_STATE.md`. Unattended `.app` launches trigger a keychain prompt storm on the host.
- **Teardown at exit:** the campaign's watchdog stays loaded only while the campaign runs. Unloading or
  repointing a launchd job is **owner work** — report the state and hand the owner the one-line command;
  never edit launchd from inside a pass.

## Rails (paste into the kit's `CLASS_RAILS`)

Host-quiet binds: nothing you build or run touches the owner's WindowServer — guest-side, or it waits; no `open`, no
`.app`, no Finder. Concurrent guest gate runs are NOT fine: one heavy lane at a time, with a stated ceiling, a
per-item cap, and evidence pulled host-side every ~10 items. In-render proof or the hunk is reverted; every gate
ships a bite proof (revert→RED, restore→GREEN, both pasted) and its own self-check. Perf claims are paired
same-session A/B, n≥4/side, against COMMITTED baselines. One coherent change per branch off the campaign base,
merge-base asserted before the first line; **a draft PR is allowed, merging and publishing are the owner's**;
repo/account configuration only on an explicit GO. A lane that cannot run PRINTS its exclusion and reason. Host-safe
verbs only: git, build, pure file generation, ssh/scp, `jev` judgment calls — every gate, runner, binary and render harness runs in the guest.

**Jev in this class** (`jev.md`): **Job 1** — a CEO-written, order-only `jev rank` (its question logged in CORP_STATE,
`jev.md` §3) orders the registry's red list and the CI log lines before a reader opens logs, and orders the diff hunks
against the marketing/spec claims before the claim audit opens the shipping surfaces — every item is still read;
labeling a red flake vs real, and routing a claim to its hunk, wait for registry entries (a red is read, never labeled).
Batch point: one pass over the whole red/claim list before that department's reads start. **Job 2** — one `jev second`
per seat seconds keep/reject (the unfolded defect question) on every new red and the claim status of every claim-audit
verdict that reaches the integrator's registry tally; severity is floor-governed, never Jev-seconded. **Gate** — a GO'd
repository or account configuration change passes §GATE. **Never Jev:** version numbers, build and signing identifiers,
byte counts, perf n-values — those stay mechanical and receipted.
