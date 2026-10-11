#!/bin/bash
# corp preflight — do the rails this run depends on EXIST in durable storage and FUNCTION?
# Usage:  preflight.sh <class> [target] [work folder]   classes: software-release software-build
#                                                       software-audit document document-set data-product
#         The work folder is where CORP_STATE.md lives (E17): ~/<project>-audits/<date>-<slug>/ for the software
#         classes -- never the product repo; for the document classes it defaults to the target.
#         preflight.sh --self-test             asserts the verdict logic (no side effects)
#
# Env:  CORP_EXECUTION=guest|host   declare where this pass executes things (default host)
#       CORP_BUILD_TREE=<dir>       the build-products tree the watchdog patterns cover
#       CORP_WATCHDOG_LABEL=<label> pin the enforcing launchd job by label
#       CORP_GUEST_CHECK=<cmd>     with CORP_EXECUTION=guest: a command that exits 0 only when the guest is up
#       CORP_TODAY=YYYY-MM-DD      pin "today" for the [fresh] date math (self-tests; default: the local date)
#
# READ-ONLY. It never loads, unloads, repoints or edits a launchd job, a plist, or the watchdog
# script — that is owner work. It reports and prints the one-line remediation.

set -u

CLASS="${1:-}"
TARGET="${2:-$PWD}"
WORK="${3:-}"
EXECUTION="${CORP_EXECUTION:-host}"
PARKS=()
WARNS=()
NOTES=()

park() { PARKS+=("$1"$'\n      FIX: '"$2"); }
warn() { WARNS+=("$1"); }
note() { NOTES+=("$1"); }

# A path is durable if it survives a session-scratchpad wipe — AND safe to put campaign state in.
# Durable and safe are different predicates, so this one answers both: rail 1's enforcer died because a
# permanent launchd job pointed into /private/tmp, Desktop/Documents/Downloads are personal folders,
# and /Volumes/* is somebody's live share.
is_durable() {
  case "$1" in
    /private/tmp/*|/tmp/*|/var/folders/*|*/scratchpad/*) return 1 ;;
    "$HOME"/Desktop|"$HOME"/Desktop/*|"$HOME"/Documents|"$HOME"/Documents/*|"$HOME"/Downloads|"$HOME"/Downloads/*) return 1 ;;
    /Volumes|/Volumes/*) return 1 ;;
    /*) return 0 ;;
    *) return 1 ;;
  esac
}
why_not_durable() {
  case "$1" in
    /private/tmp/*|/tmp/*|/var/folders/*|*/scratchpad/*) echo "a session scratchpad — a wipe took one campaign's entire ledger, its 139 verified specs and its whole build chain" ;;
    "$HOME"/Desktop|"$HOME"/Desktop/*|"$HOME"/Documents|"$HOME"/Documents/*|"$HOME"/Downloads|"$HOME"/Downloads/*) echo "Desktop/Documents/Downloads are personal folders, not campaign storage" ;;
    /Volumes|/Volumes/*) echo "a mounted share — other people's live files, and it disappears when the VPN drops" ;;
    *) echo "not an absolute path under a durable root" ;;
  esac
}

# Decoy kill test as a function so --self-test can prove it distinguishes the four outcomes.
# Echoes: BITES | "NO BITE — ..." | "INCONCLUSIVE — ..." | "NOT RUN — ..."
# $1 = tree the enforcer should be watching, $2 = seconds to wait for the kill, $3 = decoy source
#      ('cc' compiles one — the only kind that runs here; 'copy' reproduces the old broken test).
run_decoy() {
  local tree="$1" wait_s="$2" kind="${3:-cc}" stage decoy pid rc=1 i
  [ -d "$tree" ] || { echo "NOT RUN — no build-products tree at $tree"; return 0; }
  stage=$(mktemp -d "$tree/.corp-preflight.XXXXXX" 2>/dev/null) || { echo "NOT RUN — cannot stage a decoy under $tree (permissions?)"; return 0; }
  decoy="$stage/corp-preflight-decoy"
  trap 'rm -rf "$stage" 2>/dev/null' EXIT INT TERM
  if [ "$kind" = "cc" ]; then
    [ -x /usr/bin/cc ] || { rm -rf "$stage"; trap - EXIT INT TERM; echo "NOT RUN — no /usr/bin/cc to build a decoy that actually executes here"; return 0; }
    # pause(), not a spin loop: this runs on the owner's machine, and the watchdog matches the executable path,
    # never CPU. The old spin burned a full core for 15s inside the rail that exists to keep the owner's box quiet.
    printf '#include <unistd.h>\nint main(void){for(;;)pause();return 0;}\n' > "$stage/d.c" 2>/dev/null
    /usr/bin/cc -o "$decoy" "$stage/d.c" >/dev/null 2>&1
  else
    cp /bin/sleep "$decoy" 2>/dev/null; chmod +x "$decoy" 2>/dev/null
  fi
  [ -x "$decoy" ] || { rm -rf "$stage"; trap - EXIT INT TERM; echo "NOT RUN — could not build/stage a decoy in $tree"; return 0; }
  if [ "$kind" = "cc" ]; then "$decoy" >/dev/null 2>&1 & else "$decoy" 300 >/dev/null 2>&1 & fi
  pid=$!
  sleep 1
  if ! kill -0 "$pid" 2>/dev/null; then
    rm -rf "$stage"; trap - EXIT INT TERM
    echo "INCONCLUSIVE — the decoy never ran (died within 1s); nothing was proven about the enforcer"
    return 0
  fi
  i=0
  while [ "$i" -lt "$wait_s" ]; do
    sleep 1; i=$((i+1))
    kill -0 "$pid" 2>/dev/null || { rc=0; break; }
  done
  kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; rm -rf "$stage"; trap - EXIT INT TERM
  [ "$rc" -eq 0 ] && echo "BITES" || echo "NO BITE — the decoy survived ${wait_s}s under $tree"
}

# Two different host risks, two different checks.
# (a) build-products binaries and gate runners — what the launchd watchdog is patterned for.
runs_build_binaries() { case "$1" in software-release|software-build) return 0 ;; *) return 1 ;; esac; }
# (b) host GUI launches — LibreOffice for the PDF/page-image pass, Playwright/Chromium for a portal lane.
#     The watchdog does NOT cover these (its patterns are anchored to build products, and must stay that
#     way), so they get the presence rule instead of a decoy. Saying "N/A, this class launches nothing"
#     for a class that opens LibreOffice on the owner's desktop is skipping by inference.
launches_host_gui() { case "$1" in document|document-set|data-product) return 0 ;; *) return 1 ;; esac; }

# §MODEL tier map (D17): what each alias runs is INFERRED from the harness version against Anthropic's published floors —
# Sonnet 5.5 from Claude Code 2.1.284, Opus 5.5 from 2.1.280 (Claude Code docs, 09-28) — never resolved by a call, and
# never a hard-coded model id. Builders are set per class in the kit (document classes: opus at xhigh): no DOC_BUILD.
# The harness exports its version as AI_AGENT=claude-code_2-1-281_agent and inside CLAUDE_CODE_EXECPATH (.../2.1.281/...).
SONNET55_MIN=2.1.284
OPUS55_MIN=2.1.280
# Haiku 5.5 from 2.1.293 on the Anthropic API (Claude Code model-config docs, 10-07); Bedrock / Vertex / Foundry keep
# the haiku alias on Haiku 4.5 — corp-mech pins haiku, so on either a mech seat is spawned with model 'sonnet' (H1).
HAIKU55_MIN=2.1.293
model_line() {   # $1 = harness version (may be empty) → the [model] line
  local v="$1" s o h
  if [ -z "$v" ]; then
    printf '%s' "harness version unreadable (no AI_AGENT / CLAUDE_CODE_EXECPATH) — what sonnet and opus run is unknown"
    return 0
  fi
  if ver_ge "$v" "$SONNET55_MIN"; then s="Sonnet 5.5 or later (harness >= $SONNET55_MIN)"; else s="Sonnet 5 (harness < $SONNET55_MIN)"; fi
  if ver_ge "$v" "$OPUS55_MIN"; then o="Opus 5.5 or later (harness >= $OPUS55_MIN)"; else o="an Opus before 5.5 (harness < $OPUS55_MIN)"; fi
  if ver_ge "$v" "$HAIKU55_MIN"; then h="Haiku 5.5 or later on the Anthropic API (harness >= $HAIKU55_MIN)"; else h="Haiku 4.5 (harness < $HAIKU55_MIN)"; fi
  printf '%s' "harness $v · sonnet → $s · opus → $o · haiku → $h — inferred from the version, not resolved"
}

# H1: corp-mech pins haiku. haiku_warn <harness version> → one WARN line (empty when haiku is Haiku 5.5): below
# HAIKU55_MIN, or off the plain Anthropic API (a cloud provider, a gateway, another base URL, an alias override).
haiku_warn() {
  local v="$1"
  [ -z "$v" ] && return 0
  if ! ver_ge "$v" "$HAIKU55_MIN"; then
    printf '%s' "harness $v < $HAIKU55_MIN: haiku is Haiku 4.5 (unmeasured on /corp work) — run mech seats as a Workflow agent() with model 'sonnet', effort 'low' (MODEL_MECH / EFFORT_MECH), or run 'claude update' (H1)."
  elif [ -n "${CLAUDE_CODE_USE_BEDROCK:-}${CLAUDE_CODE_USE_VERTEX:-}${CLAUDE_CODE_USE_FOUNDRY:-}${CLAUDE_CODE_USE_MANTLE:-}${CLAUDE_CODE_USE_GATEWAY:-}${ANTHROPIC_DEFAULT_HAIKU_MODEL:-}" ] \
       || { [ -n "${ANTHROPIC_BASE_URL:-}" ] && ! printf '%s' "$ANTHROPIC_BASE_URL" | grep -qE '^https://api\.anthropic\.com(/|$)'; }; then
    printf '%s' "not the plain Anthropic API (a cloud provider, gateway, ANTHROPIC_BASE_URL or ANTHROPIC_DEFAULT_HAIKU_MODEL is set): haiku may not be Haiku 5.5 here (Bedrock / Vertex / Foundry / Platform on AWS keep Haiku 4.5) — run mech seats as a Workflow agent() with model 'sonnet', effort 'low', unless a seat reports claude-haiku-5-5 (H1)."
  fi
}

# D19: a core SKILL.md over budget can silently lose its tail after a compaction (Claude Code re-attaches only the first
# ~5,000 tokens of a skill). Prints one [core] line per file; returns 1 when any is over CORE_MAX bytes or missing.
CORE_MAX=12000
core_budget_report() {
  local f n rc=0
  for f in "$@"; do
    if [ ! -f "$f" ]; then echo "[core]      MISSING $f"; rc=1; continue; fi
    n=$(wc -c < "$f" | tr -d ' ')
    if [ "$n" -gt "$CORE_MAX" ]; then echo "[core]      OVER BUDGET $n > $CORE_MAX bytes: $f"; rc=1
    else echo "[core]      $n / $CORE_MAX bytes: $f"; fi
  done
  return "$rc"
}

# D3: the campaign's start stamp for share-check.sh (YYYYMMDDhhmm, local — what `touch -t` takes), written ONCE into
# CORP_STATE.md when the campaign is created (or corp_state.json's campaign_start). Never a round's RUN_START.
# $1 = the state dir → the recorded 12-digit stamp, or nothing.
campaign_start_of() {
  local d="$1" v=""
  if [ -f "$d/CORP_STATE.md" ]; then
    v=$(grep -m1 'CAMPAIGN_START' "$d/CORP_STATE.md" 2>/dev/null | grep -oE '(^|[^0-9])[0-9]{12}([^0-9]|$)' | head -1 | tr -cd '0-9')
  fi
  if [ -z "$v" ] && [ -f "$d/corp_state.json" ] && command -v python3 >/dev/null 2>&1; then
    v=$(python3 -c 'import json,sys
try:
    s = str(json.load(open(sys.argv[1])).get("campaign_start") or "")
except Exception:
    s = ""
print(s if len(s) == 12 and s.isdigit() else "")' "$d/corp_state.json" 2>/dev/null)
  fi
  printf '%s' "$v"
}
# valid_stamp YYYYMMDDhhmm — true when it is a real local date and time (touch -t would take it).
valid_stamp() { [ "${#1}" -eq 12 ] && date -j -f '%Y%m%d%H%M' "$1" +%s >/dev/null 2>&1; }

# D8: rule #1 is mechanical when the campaign's work folder is a git repo (commit before every state write; appends
# count). $1 = the state dir → "git <toplevel>" | "none" | "missing".
work_git() {
  [ -d "$1" ] || { printf 'missing'; return 0; }
  if git -C "$1" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    printf 'git %s' "$(git -C "$1" rev-parse --show-toplevel 2>/dev/null)"
  else
    printf 'none'
  fi
}
harness_version() {
  local v
  v=$(printf '%s' "${AI_AGENT:-}" | sed -n 's/^claude-code_\([0-9][0-9]*\)-\([0-9][0-9]*\)-\([0-9][0-9]*\)_.*/\1.\2.\3/p')
  [ -n "$v" ] || v=$(printf '%s' "${CLAUDE_CODE_EXECPATH:-}" | sed -n 's#.*/claude-code/\([0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\)/.*#\1#p')
  printf '%s' "$v"
}
# ver_ge A B — true when dotted version A >= B, numeric per field (2.1.1000 > 2.1.284).
ver_ge() { [ "$(printf '%s\n%s\n' "$1" "$2" | sort -t. -k1,1n -k2,2n -k3,3n | head -1)" = "$2" ]; }

# [fresh] — is what /corp absorbed from outside still current? corp/sources.json lists each source with last_absorbed
# and refresh_days (its "_format" key documents the fields). Informational, never a PARK. A row is DUE once the days
# since last_absorbed exceed refresh_days. fresh_report prints "[fresh]" lines plus at most one "NOTE: ..." line (the
# due list) that the caller turns into a note(). $1 = sources.json, $2 = today as YYYY-MM-DD.
corp_today() { printf '%s' "${CORP_TODAY:-$(date +%Y-%m-%d)}"; }
fresh_report() {
  command -v python3 >/dev/null 2>&1 || { echo "[fresh]     python3 not found — sources freshness not checked"; return 0; }
  PYTHONIOENCODING=utf-8 python3 - "$1" "$2" <<'PY'
import json, sys
from datetime import date
path, today_s = sys.argv[1], sys.argv[2]
TAG = "[fresh]    "
FAMILIES = {"typesafe", "openrouter", "anthropic", "community", "internal"}
try:
    today = date.fromisoformat(today_s)
except ValueError:
    print(f"{TAG} today {today_s!r} is not YYYY-MM-DD — freshness not checked"); sys.exit(0)
try:
    with open(path) as fh:
        rows = json.load(fh).get("sources")
except FileNotFoundError:
    print(f"{TAG} no sources registry at {path} — nothing to check"); sys.exit(0)
except (OSError, ValueError, AttributeError) as e:
    print(f"{TAG} {path} unreadable ({e}) — freshness not checked"); sys.exit(0)
if not isinstance(rows, list):
    print(f'{TAG} {path} has no "sources" list — freshness not checked'); sys.exit(0)
good, due, warns, seen = [], [], [], set()
for i, r in enumerate(rows):
    rid = r.get("id") if isinstance(r, dict) else None
    try:
        if not isinstance(rid, str) or not rid.strip():
            raise ValueError("no id")
        if rid in seen:
            raise ValueError("duplicate id")
        seen.add(rid)
        if r.get("family") not in FAMILIES:
            raise ValueError(f"family {r.get('family')!r} is not one of {'|'.join(sorted(FAMILIES))}")
        for field in ("url", "what"):
            if not isinstance(r.get(field), str) or not r[field].strip():
                raise ValueError(f"no {field}")
        last = date.fromisoformat(r["last_absorbed"])
        every = r["refresh_days"]
        if isinstance(every, bool) or not isinstance(every, int) or every < 1:
            raise ValueError(f"refresh_days {every!r} is not a positive integer")
    except (TypeError, KeyError, ValueError) as e:
        warns.append(f"row {i} ({rid or '?'}): {e}"); continue
    days = (today - last).days
    if days < 0:
        warns.append(f"row {i} ({rid}): last_absorbed {last} is after today {today}"); continue
    good.append((days, rid, last, every))
    if days > every:
        due.append(f"{rid} ({days}d > {every}d)")
print(f"{TAG} {len(rows)} sources in {path}")
if good:
    days, rid, last, every = max(good, key=lambda g: g[0])   # the first row wins a tie
    print(f"{TAG} oldest: {rid} — {days} day(s) since {last} (refresh every {every})")
for w in warns:
    print(f"{TAG} WARN {w}")
if due:
    print(f"{TAG} due: {len(due)} past refresh_days")
    print("NOTE: sources past refresh_days: " + ", ".join(due) + " — run `/corp refresh` (re-read these, propose diffs).")
else:
    print(f"{TAG} none past refresh_days")
PY
}

# E15: the Jev hooks were tuned on hooks_config.json's build; a reply from any other build makes every hook warn-only
# (the airlock stops denying: rule #1 loses its mechanical deny). $1 = tuned build, $2 = the build jev-latest answers
# with → the [jev] line, or nothing when they match or either is unknown. The re-gate itself is owner configuration.
hooks_drift_line() {
  [ -n "$1" ] && [ -n "$2" ] && [ "$1" != "$2" ] || return 0
  printf '%s' "HOOKS WARN-ONLY — hooks tuned on $1, jev-latest → $2: the airlock, belay, tier guard and jev-gate warn instead of deny/block"
}
hooks_tuned_build() {   # $1 = hooks_config.json → its tuned_build, or nothing
  python3 -c 'import json,sys
try: print(json.load(open(sys.argv[1])).get("tuned_build") or "")
except Exception: print("")' "$1" 2>/dev/null
}
# E11: the Agent tool has no effort field, so a /corp seat spawned through it takes its model AND effort from a corp-*
# agent type (~/.claude/agents/corp-*.md). $1 = the agents dir → one [model] line; returns 1 when a type is missing or
# pins another model / effort than E11's table.
corp_agents_report() {
  python3 - "$1" <<'PY'
import os, re, sys
d = sys.argv[1]
want = {"corp-final-fable": ("fable", "max"), "corp-final-opus": ("opus", "max"), "corp-judge": ("opus", "xhigh"),
        "corp-doc-builder": ("opus", "xhigh"), "corp-sw-builder": ("sonnet", "high"), "corp-auditor": ("sonnet", "high"),
        "corp-mech": ("haiku", "medium")}
bad = []
for name, (m, e) in want.items():
    try:
        with open(os.path.join(d, name + ".md"), encoding="utf-8") as fh:
            text = fh.read(8000)
    except OSError:
        bad.append(f"{name} missing"); continue
    fm = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    kv = dict(l.split(": ", 1) for l in fm.group(1).split("\n") if ": " in l) if fm else {}
    if (kv.get("model"), kv.get("effort")) != (m, e):
        bad.append(f"{name} pins {kv.get('model')}/{kv.get('effort')}, not {m}/{e}")
if bad:
    print("[model]     corp agent types (E11): " + "; ".join(bad)); sys.exit(1)
print(f"[model]     corp agent types (E11): {len(want)}/{len(want)} in {d} pin model + effort — spawn /corp seats as these types")
PY
}
# F7 (re-gate OPUS RG-05): a software campaign's work folder is never the target repo NOR inside it. $1 work folder,
# $2 target → prints why and returns 0 when it is: the same folder, a folder under the target, or a folder inside the
# target's git work tree (a work folder not created yet is judged by its nearest existing parent).
nearest_dir() { local d="$1"; while [ -n "$d" ] && [ ! -d "$d" ]; do d=$(dirname "$d"); done; printf '%s' "${d:-/}"; }
work_inside_target() {
  local w t wd tt wt
  wd=$(nearest_dir "$1")
  w=$(cd "$wd" 2>/dev/null && pwd -P)${1#"$wd"}
  w=${w%/}
  t=$(cd "$2" 2>/dev/null && pwd -P || printf '%s' "${2%/}")
  if [ "$w" = "$t" ]; then printf 'it is the target itself (%s)' "$t"; return 0; fi
  case "$w/" in "$t/"*) printf 'it is inside the target (%s)' "$t"; return 0 ;; esac
  tt=$(git -C "$2" rev-parse --show-toplevel 2>/dev/null)
  wt=$(git -C "$wd" rev-parse --show-toplevel 2>/dev/null)
  if [ -n "$tt" ] && [ "$wt" = "$tt" ]; then printf "it is inside the target's git repo (%s)" "$tt"; return 0; fi
  return 1
}
# F7 (re-gate FABLE-B RG-05, OPUS RG-07): the committed corp/agents/ copies are the SOURCE; the harness, the tier guard
# and this preflight read ~/.claude/agents/. $1 source dir, $2 installed dir → one [model] line, or one line per
# difference with the exact reinstall command (the installed copy is versioned first, rule #1); returns 1 on any.
corp_agents_drift() {
  python3 - "$1" "$2" <<'PY'
import hashlib, os, shlex, sys
src, dst = sys.argv[1], sys.argv[2]
names = sorted(f for f in os.listdir(src) if f.startswith("corp-") and f.endswith(".md")) if os.path.isdir(src) else []
if not names:
    print(f"[model]     corp agent sources: none in {src}"); sys.exit(1)
md5 = lambda p: hashlib.md5(open(p, "rb").read()).hexdigest()
bad = []
for n in names:
    a, b = os.path.join(src, n), os.path.join(dst, n)
    if not os.path.isfile(b):
        bad.append((n, "missing from " + dst, f"mkdir -p {shlex.quote(dst)} && cp -p -n {shlex.quote(a)} {shlex.quote(b)}"))
    elif md5(a) != md5(b):
        bad.append((n, f"differs from its committed source (installed md5 {md5(b)[:8]}, source {md5(a)[:8]})",
                    f"cp -p {shlex.quote(b)} {shlex.quote(b)}.bak-$(date +%Y%m%d-%H%M%S) && cp -p {shlex.quote(a)} {shlex.quote(b)}"))
if not bad:
    print(f"[model]     corp agent types = their committed source ({src}), md5, {len(names)}/{len(names)}"); sys.exit(0)
for n, why, cmd in bad:
    print(f"[model]     {n} {why} -- reinstall: {cmd}")
sys.exit(1)
PY
}
# E17: where the campaign's state lives. $1 class, $2 target, $3 work folder (may be empty) → the state dir, or nothing
# when a software class names no work folder (never the product repo).
state_dir_for() {
  if [ -n "$3" ]; then printf '%s' "$3"; return 0; fi
  case "$1" in software-release|software-build|software-audit) return 0 ;; *) printf '%s' "$2" ;; esac
}
# E17: a fresh CAMPAIGN_START only for a genuinely new campaign -- no state file and no round output yet.
# $1 = the state dir → "fresh" | "rounds-without-state" | "has-state"
campaign_stage() {
  if [ -f "$1/CORP_STATE.md" ] || [ -f "$1/corp_state.json" ]; then printf 'has-state'
  elif [ -d "$1/corp" ] && [ -n "$(ls -A "$1/corp" 2>/dev/null)" ]; then printf 'rounds-without-state'
  else printf 'fresh'; fi
}

# ---------------------------------------------------------------- self-test
if [ "$CLASS" = "--self-test" ]; then
  fail=0
  is_durable /Users/example/.claude/bin/w.sh || { echo "FAIL durable(home)"; fail=1; }
  is_durable /private/tmp/x/scratchpad/w.sh && { echo "FAIL durable(scratchpad)"; fail=1; }
  is_durable /var/folders/ab/w.sh           && { echo "FAIL durable(var-folders)"; fail=1; }
  is_durable "$HOME/Desktop/case/x.md"      && { echo "FAIL durable(Desktop)"; fail=1; }
  is_durable "$HOME/Documents/case/x.md"    && { echo "FAIL durable(Documents)"; fail=1; }
  is_durable "$HOME/Downloads/x.md"         && { echo "FAIL durable(Downloads)"; fail=1; }
  is_durable "$HOME/Documents"              && { echo "FAIL durable(Documents, bare)"; fail=1; }
  is_durable /Volumes                       && { echo "FAIL durable(/Volumes, bare)"; fail=1; }
  is_durable /Volumes/ShareDocs/case/x.md   && { echo "FAIL durable(client share)"; fail=1; }
  is_durable ./w.sh                         && { echo "FAIL durable(relative)"; fail=1; }
  runs_build_binaries software-release || { echo "FAIL exec(release)"; fail=1; }
  runs_build_binaries document         && { echo "FAIL exec(document)"; fail=1; }
  launches_host_gui document           || { echo "FAIL gui(document)"; fail=1; }
  launches_host_gui software-audit     && { echo "FAIL gui(audit)"; fail=1; }
  park "x" "y"; [ "${#PARKS[@]}" -eq 1 ] || { echo "FAIL park collects"; fail=1; }
  case "$(run_decoy /nonexistent-tree-for-selftest 1)" in "NOT RUN"*) ;; *) echo "FAIL decoy(no tree)"; fail=1 ;; esac
  st=$(mktemp -d)
  # No watchdog watches $st, so a decoy that RUNS must come back NO BITE — never BITES.
  r=$(run_decoy "$st" 2 cc)
  case "$r" in "NO BITE"*) ;; *) echo "FAIL decoy(unwatched tree) — must not read as a bite, got: $r"; fail=1 ;; esac
  # The old test copied /bin/sleep; on arm64 the OS SIGKILLs it, which used to read as a watchdog kill.
  case "$(run_decoy "$st" 2 copy)" in "INCONCLUSIVE"*|"NO BITE"*) ;;
    *) echo "FAIL decoy(copied platform binary) must never report BITES"; fail=1 ;; esac
  [ -z "$(find "$st" -name '.corp-preflight.*' 2>/dev/null)" ] || { echo "FAIL decoy leaves staging behind"; fail=1; }
  rm -rf "$st"
  ver_ge 2.1.284 2.1.284  || { echo "FAIL ver_ge(equal)"; fail=1; }
  ver_ge 2.1.281 2.1.284  && { echo "FAIL ver_ge(older)"; fail=1; }
  ver_ge 2.1.1000 2.1.284 || { echo "FAIL ver_ge(numeric, not lexical)"; fail=1; }
  ver_ge 2.2.0 2.1.284    || { echo "FAIL ver_ge(minor bump)"; fail=1; }
  [ "$(AI_AGENT=claude-code_2-1-281_agent CLAUDE_CODE_EXECPATH= harness_version)" = 2.1.281 ] || { echo "FAIL harness_version(AI_AGENT)"; fail=1; }
  [ "$(AI_AGENT= CLAUDE_CODE_EXECPATH='/x/claude-code/2.1.290/claude.app/y' harness_version)" = 2.1.290 ] || { echo "FAIL harness_version(EXECPATH)"; fail=1; }
  [ -z "$(AI_AGENT= CLAUDE_CODE_EXECPATH= harness_version)" ] || { echo "FAIL harness_version(unreadable)"; fail=1; }
  # [fresh] date math — "today" always comes from the CORP_TODAY override here, never the wall clock.
  has() { printf '%s\n' "$1" | grep -qF -- "$2"; }
  [ "$(CORP_TODAY=2026-10-06 corp_today)" = 2026-10-06 ] || { echo "FAIL corp_today(override)"; fail=1; }
  case "$(CORP_TODAY= corp_today)" in [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) ;; *) echo "FAIL corp_today(default)"; fail=1 ;; esac
  fx=$(mktemp -d)
  row() { printf '{"id": "%s", "family": "internal", "url": "u", "what": "w", "last_absorbed": "%s", "refresh_days": %s}' "$1" "$2" "$3"; }
  printf '{"sources": [%s, %s, %s]}\n' "$(row wk 2026-09-28 7)" "$(row mo 2026-09-28 30)" "$(row old 2026-09-01 14)" > "$fx/s1.json"
  fr=$(fresh_report "$fx/s1.json" "$(CORP_TODAY=2026-10-05 corp_today)")
  has "$fr" "3 sources in"                                           || { echo "FAIL fresh(count)"; fail=1; }
  has "$fr" "oldest: old — 34 day(s) since 2026-09-01"               || { echo "FAIL fresh(oldest, 34 days)"; fail=1; }
  has "$fr" "NOTE: sources past refresh_days: old (34d > 14d) — run \`/corp refresh\`" || { echo "FAIL fresh(due note)"; fail=1; }
  has "$fr" "wk ("                                                   && { echo "FAIL fresh(7 days on a 7-day cadence is not past it)"; fail=1; }
  fr=$(fresh_report "$fx/s1.json" "$(CORP_TODAY=2026-10-06 corp_today)")
  has "$fr" "past refresh_days: wk (8d > 7d), old (35d > 14d)"       || { echo "FAIL fresh(day 8 is due, registry order)"; fail=1; }
  printf '{"sources": [%s, %s]}\n' "$(row ny 2026-12-25 14)" "$(row leap 2028-02-28 1)" > "$fx/s2.json"
  has "$(fresh_report "$fx/s2.json" "$(CORP_TODAY=2027-01-08 corp_today)")" "ny (" && { echo "FAIL fresh(year boundary: 14 days is not past 14)"; fail=1; }
  has "$(fresh_report "$fx/s2.json" "$(CORP_TODAY=2027-01-09 corp_today)")" "ny (15d > 14d)" || { echo "FAIL fresh(year boundary: day 15 is due)"; fail=1; }
  has "$(fresh_report "$fx/s2.json" "$(CORP_TODAY=2028-03-01 corp_today)")" "leap (2d > 1d)" || { echo "FAIL fresh(leap year: Feb 28 to Mar 1 is 2 days)"; fail=1; }
  printf '{"sources": [%s, %s, %s, %s]}\n' "$(row bad 2026-13-01 7)" "$(row zero 2026-09-28 0)" "$(row fut 2026-12-01 7)" "$(row wk 2026-09-28 7)" > "$fx/s3.json"
  fr=$(fresh_report "$fx/s3.json" "$(CORP_TODAY=2026-10-01 corp_today)")
  [ "$(printf '%s\n' "$fr" | grep -c 'WARN row')" -eq 3 ]           || { echo "FAIL fresh(bad date, zero cadence, future date each WARN)"; fail=1; }
  has "$fr" "none past refresh_days"                                 || { echo "FAIL fresh(bad rows are never due)"; fail=1; }
  printf '{not json' > "$fx/broken.json"
  has "$(fresh_report "$fx/broken.json" 2026-10-01)" "unreadable"    || { echo "FAIL fresh(broken json is reported, not fatal)"; fail=1; }
  has "$(fresh_report "$fx/missing.json" 2026-10-01)" "no sources registry" || { echo "FAIL fresh(missing file is reported, not fatal)"; fail=1; }
  # the shipped registry: every row well-formed as of the real today (families, ids, urls, dates, cadences)
  SELF_SOURCES="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/sources.json"
  fr=$(fresh_report "$SELF_SOURCES" "$(CORP_TODAY= corp_today)")
  has "$fr" "sources in $SELF_SOURCES"                               || { echo "FAIL fresh(shipped sources.json readable)"; fail=1; }
  has "$fr" "WARN"                                                   && { echo "FAIL fresh(shipped sources.json has a malformed row): $(printf '%s\n' "$fr" | grep WARN | head -3)"; fail=1; }
  # D17: [model] prints the harness and what each alias runs — inferred, no hard-coded model id, no DOC_BUILD
  ml=$(model_line 2.1.290)
  has "$ml" "sonnet → Sonnet 5.5 or later"                            || { echo "FAIL model_line(new harness): $ml"; fail=1; }
  has "$ml" "opus → Opus 5.5 or later"                                || { echo "FAIL model_line(opus): $ml"; fail=1; }
  has "$(model_line 2.1.281)" "sonnet → Sonnet 5 (harness < 2.1.284)" || { echo "FAIL model_line(old harness)"; fail=1; }
  has "$(model_line '')" "unknown"                                    || { echo "FAIL model_line(unreadable)"; fail=1; }
  has "$ml" "haiku → Haiku 4.5 (harness < 2.1.293)"                     || { echo "FAIL model_line(haiku, 2.1.290)"; fail=1; }
  has "$(model_line 2.1.293)" "haiku → Haiku 5.5 or later"              || { echo "FAIL model_line(haiku, new harness)"; fail=1; }
  hw() { env -u CLAUDE_CODE_USE_BEDROCK -u CLAUDE_CODE_USE_VERTEX -u CLAUDE_CODE_USE_FOUNDRY -u CLAUDE_CODE_USE_MANTLE \
          -u CLAUDE_CODE_USE_GATEWAY -u ANTHROPIC_DEFAULT_HAIKU_MODEL -u ANTHROPIC_BASE_URL "$@" bash -c "$(declare -f ver_ge haiku_warn); HAIKU55_MIN=$HAIKU55_MIN; haiku_warn 2.1.293"; }
  [ -z "$(hw)" ]                                                      || { echo "FAIL haiku_warn(plain API)"; fail=1; }
  [ -z "$(hw ANTHROPIC_BASE_URL=https://api.anthropic.com)" ]         || { echo "FAIL haiku_warn(anthropic base url)"; fail=1; }
  [ -z "$(hw ANTHROPIC_BASE_URL=https://api.anthropic.com/)" ]        || { echo "FAIL haiku_warn(anthropic base url /)"; fail=1; }
  for e in ANTHROPIC_BASE_URL=http://localhost:4000 ANTHROPIC_BASE_URL=https://api.anthropic.com.evil.io \
           ANTHROPIC_BASE_URL=https://api.anthropic.com@proxy.io CLAUDE_CODE_USE_BEDROCK=1 ANTHROPIC_DEFAULT_HAIKU_MODEL=x; do
    has "$(hw "$e")" "not the plain Anthropic API"                    || { echo "FAIL haiku_warn($e)"; fail=1; }
  done
  has "$(bash -c "$(declare -f ver_ge haiku_warn); HAIKU55_MIN=$HAIKU55_MIN; haiku_warn 2.1.289")" "Haiku 4.5" || { echo "FAIL haiku_warn(old harness)"; fail=1; }
  printf '%s\n%s\n%s\n' "$ml" "$(model_line 2.1.281)" "$(model_line '')" | grep -qE 'claude-[a-z]+-[0-9]|DOC_BUILD' \
                                                                      && { echo "FAIL model_line names a model id or DOC_BUILD"; fail=1; }
  SELF_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
  grep -nE '^[[:space:]]*(echo|note|warn|park)[[:space:]].*(DOC_BUILD|claude-sonnet-|claude-opus-|~60k tokens|there is no model fallback)' "$SELF_SCRIPT" \
                                                                      && { echo "FAIL preflight still prints a retired DOC_BUILD / model id / probe note / no-fallback line"; fail=1; }
  # D19: a core SKILL.md over 12,000 bytes fails loudly
  fx2=$(mktemp -d)
  head -c 12000 /dev/zero | tr '\0' 'a' > "$fx2/at.md"; head -c 12001 /dev/zero | tr '\0' 'a' > "$fx2/over.md"
  core_budget_report "$fx2/at.md" >/dev/null                         || { echo "FAIL core budget(12,000 bytes is within budget)"; fail=1; }
  core_budget_report "$fx2/at.md" "$fx2/over.md" >/dev/null          && { echo "FAIL core budget(12,001 bytes must fail)"; fail=1; }
  core_budget_report "$fx2/gone.md" >/dev/null                       && { echo "FAIL core budget(a missing core must fail)"; fail=1; }
  SELF_SKILLS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  cb=$(core_budget_report "$SELF_SKILLS/corp/SKILL.md") || { echo "FAIL shipped core over budget: $(printf '%s' "$cb" | grep -E 'OVER|MISSING' | tr '\n' ' ')"; fail=1; }
  # D3: CAMPAIGN_START comes from CORP_STATE.md (or corp_state.json), never RUN_START; the template placeholder is not a stamp
  mkdir -p "$fx2/filled" "$fx2/tmpl" "$fx2/json" "$fx2/none"
  printf '**Author:** /corp\n**Campaign start (CAMPAIGN_START):** `202609281405` — share-check start\nRUN_START=2026-09-29T01:00:00+00:00\n' > "$fx2/filled/CORP_STATE.md"
  printf '**Campaign start (CAMPAIGN_START):** `<YYYYMMDDhhmm, local — date +%%Y%%m%%d%%H%%M, written once>`\n' > "$fx2/tmpl/CORP_STATE.md"
  printf '{"campaign_start": "202609010930"}\n' > "$fx2/json/corp_state.json"
  [ "$(campaign_start_of "$fx2/filled")" = 202609281405 ]              || { echo "FAIL campaign_start(filled line): $(campaign_start_of "$fx2/filled")"; fail=1; }
  [ -z "$(campaign_start_of "$fx2/tmpl")" ]                            || { echo "FAIL campaign_start(template placeholder is not a stamp)"; fail=1; }
  [ "$(campaign_start_of "$fx2/json")" = 202609010930 ]                || { echo "FAIL campaign_start(corp_state.json fallback)"; fail=1; }
  [ -z "$(campaign_start_of "$fx2/none")" ]                            || { echo "FAIL campaign_start(no state)"; fail=1; }
  valid_stamp 202609281405                                             || { echo "FAIL valid_stamp(real)"; fail=1; }
  valid_stamp 202613011200                                             && { echo "FAIL valid_stamp(month 13)"; fail=1; }
  valid_stamp 2026092814                                               && { echo "FAIL valid_stamp(10 digits)"; fail=1; }
  # D8: the work folder is a git repo, or preflight says how to make it one
  [ "$(work_git "$fx2/none")" = none ]                                 || { echo "FAIL work_git(plain folder)"; fail=1; }
  [ "$(work_git "$fx2/nope")" = missing ]                              || { echo "FAIL work_git(missing folder)"; fail=1; }
  git -C "$fx2/none" init -q 2>/dev/null && { case "$(work_git "$fx2/none")" in "git "*) ;; *) echo "FAIL work_git(repo)"; fail=1 ;; esac; }
  # E15: hooks drift is loud; a match (or an unknown build) prints nothing
  has "$(hooks_drift_line typesafe/jev-1.13 typesafe/jev-1.14)" "HOOKS WARN-ONLY — hooks tuned on typesafe/jev-1.13, jev-latest → typesafe/jev-1.14" \
                                                                       || { echo "FAIL hooks_drift_line(drift)"; fail=1; }
  [ -z "$(hooks_drift_line typesafe/jev-1.13 typesafe/jev-1.13)" ]     || { echo "FAIL hooks_drift_line(match is silent)"; fail=1; }
  [ -z "$(hooks_drift_line '' typesafe/jev-1.14)" ]                    || { echo "FAIL hooks_drift_line(unknown tuned build)"; fail=1; }
  printf '{"tuned_build": "typesafe/jev-9.9"}\n' > "$fx2/hc.json"
  [ "$(hooks_tuned_build "$fx2/hc.json")" = typesafe/jev-9.9 ]         || { echo "FAIL hooks_tuned_build(read)"; fail=1; }
  [ -z "$(hooks_tuned_build "$fx2/gone.json")" ]                       || { echo "FAIL hooks_tuned_build(missing file)"; fail=1; }
  SELF_HC="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/jev/scripts/hooks_config.json"
  [ ! -f "$SELF_HC" ] || [ -n "$(hooks_tuned_build "$SELF_HC")" ]                             || { echo "FAIL hooks_tuned_build(shipped hooks_config.json)"; fail=1; }
  # E17: software state never lands in the product repo; a work folder always wins; no per-round CAMPAIGN_START
  [ -z "$(state_dir_for software-build /repo/app '')" ]                || { echo "FAIL state_dir_for(software, no work folder)"; fail=1; }
  [ "$(state_dir_for software-audit /repo/app /w/app-audits/2026-09-28-x)" = /w/app-audits/2026-09-28-x ] || { echo "FAIL state_dir_for(work folder)"; fail=1; }
  [ "$(state_dir_for document /w/case '')" = /w/case ]                 || { echo "FAIL state_dir_for(document defaults to target)"; fail=1; }
  mkdir -p "$fx2/stage/fresh" "$fx2/stage/rounds/corp"; : > "$fx2/stage/rounds/corp/r1-audit.md"
  [ "$(campaign_stage "$fx2/stage/fresh")" = fresh ]                   || { echo "FAIL campaign_stage(fresh)"; fail=1; }
  [ "$(campaign_stage "$fx2/stage/rounds")" = rounds-without-state ]   || { echo "FAIL campaign_stage(rounds, no state: never mint)"; fail=1; }
  [ "$(campaign_stage "$fx2/filled")" = has-state ]                    || { echo "FAIL campaign_stage(has state)"; fail=1; }
  # E11: the corp-* agent types pin model and effort
  mkdir -p "$fx2/agents"
  for t in corp-final-fable:fable:max corp-final-opus:opus:max corp-judge:opus:xhigh corp-doc-builder:opus:xhigh \
           corp-sw-builder:sonnet:high corp-auditor:sonnet:high corp-mech:haiku:medium; do
    n=${t%%:*}; r=${t#*:}; printf -- '---\nname: %s\nmodel: %s\neffort: %s\n---\nbody\n' "$n" "${r%%:*}" "${r#*:}" > "$fx2/agents/$n.md"
  done
  corp_agents_report "$fx2/agents" >/dev/null                          || { echo "FAIL corp_agents_report(seven good types)"; fail=1; }
  printf -- '---\nname: corp-judge\nmodel: opus\neffort: high\n---\nbody\n' > "$fx2/agents/corp-judge.md"
  corp_agents_report "$fx2/agents" >/dev/null                          && { echo "FAIL corp_agents_report(wrong effort must fail)"; fail=1; }
  rm "$fx2/agents/corp-mech.md"
  has "$(corp_agents_report "$fx2/agents")" "corp-mech missing"         || { echo "FAIL corp_agents_report(missing type named)"; fail=1; }
  grep -nE '^[[:space:]]*(echo|note|warn|park)[[:space:]].*its PARENT, and assert the target' "$SELF_SCRIPT" >/dev/null \
                                                                       && { echo "FAIL preflight still says share-check the PARENT of a NEW folder (E7)"; fail=1; }
  # F7 (re-gate OPUS RG-05, its om05/ receipt): a work folder inside the target repo PARKs, not only the repo itself
  mkdir -p "$fx2/repo/app" "$fx2/repo/corp-audits/2026-09-29-x" "$fx2/elsewhere"
  git -C "$fx2/repo" init -q 2>/dev/null
  work_inside_target "$fx2/repo" "$fx2/repo" >/dev/null                          || { echo "FAIL work_inside_target(the repo itself)"; fail=1; }
  has "$(work_inside_target "$fx2/repo/corp-audits/2026-09-29-x" "$fx2/repo")" "inside the target" || { echo "FAIL work_inside_target(a subfolder: om05)"; fail=1; }
  has "$(work_inside_target "$fx2/repo/corp-audits/2026-09-29-y" "$fx2/repo/app")" "git repo" || { echo "FAIL work_inside_target(same git repo, not yet created)"; fail=1; }
  work_inside_target "$fx2/elsewhere/2026-09-29-x" "$fx2/repo" >/dev/null       && { echo "FAIL work_inside_target(outside the repo)"; fail=1; }
  mkdir -p "$fx2/plain/app/audits"                                               # a target that is not a git repo
  has "$(work_inside_target "$fx2/plain/app/audits/x" "$fx2/plain/app")" "it is inside the target (" || { echo "FAIL work_inside_target(a subfolder of a plain target)"; fail=1; }
  grep -qE '^elif case "\$CLASS" in software-\*\) true ;; \*\) false ;; esac && WHY_IN=\$\(work_inside_target' "$SELF_SCRIPT" \
                                                                       || { echo "FAIL preflight parks a software work folder inside the target"; fail=1; }
  # F7 (re-gate FABLE-B RG-04): a software campaign with no work folder PARKs (never a note + WARN)
  grep -qE '^  park "No work folder given for a software campaign' "$SELF_SCRIPT" || { echo "FAIL no work folder must PARK (F7)"; fail=1; }
  # F7 (re-gate FABLE-B RG-05, OPUS RG-07): the installed agent types are compared with the committed source by md5
  mkdir -p "$fx2/agsrc" "$fx2/agdst"
  for n in corp-judge corp-mech; do printf -- '---\nname: %s\n---\nbody\n' "$n" > "$fx2/agsrc/$n.md"; cp -p "$fx2/agsrc/$n.md" "$fx2/agdst/"; done
  has "$(corp_agents_drift "$fx2/agsrc" "$fx2/agdst")" "2/2"                     || { echo "FAIL corp_agents_drift(identical copies)"; fail=1; }
  printf 'drifted\n' >> "$fx2/agdst/corp-judge.md"
  dr=$(corp_agents_drift "$fx2/agsrc" "$fx2/agdst") && { echo "FAIL corp_agents_drift(a drifted copy must fail)"; fail=1; }
  has "$dr" "corp-judge.md differs from its committed source" || { echo "FAIL corp_agents_drift(names the drifted type): $dr"; fail=1; }
  has "$dr" "reinstall: cp -p $fx2/agdst/corp-judge.md $fx2/agdst/corp-judge.md.bak-\$(date +%Y%m%d-%H%M%S) && cp -p $fx2/agsrc/corp-judge.md $fx2/agdst/corp-judge.md" \
                                                                       || { echo "FAIL corp_agents_drift(the exact reinstall command, versioning first): $dr"; fail=1; }
  mv "$fx2/agdst/corp-mech.md" "$fx2/corp-mech.md.moved"
  has "$(corp_agents_drift "$fx2/agsrc" "$fx2/agdst")" "corp-mech.md missing from" || { echo "FAIL corp_agents_drift(a missing type)"; fail=1; }
  # F7 (re-gate OPUS RG-08): every printed deploy copy is recursive, and --record names the act (F1)
  grep -nE '^[[:space:]]*(echo|note|warn|park)[[:space:]].*rsync ' "$SELF_SCRIPT" | grep -vE 'rsync -a --update --backup' \
                                                                       && { echo "FAIL a printed rsync is not recursive (rsync -a, F7)"; fail=1; }
  grep -qE 'note "Rail 6 default:.*rsync -a --update --backup <act.src>/ <dest>/.*--record <dest> <act.src> <campaign> .*--action <action.json>' "$SELF_SCRIPT" \
                                                                       || { echo "FAIL the rail-6 note prints the recursive copy and --record --action"; fail=1; }
  rm -rf "$fx2"
  rm -rf "$fx"
  [ "$fail" -eq 0 ] && echo "self-test OK" || echo "self-test FAILED"
  exit "$fail"
fi

case "$CLASS" in
  software-release|software-build|software-audit|document|document-set|data-product) ;;
  *) echo "usage: preflight.sh <class> [target] [work folder]   (or --self-test)"; exit 2 ;;
esac
case "$EXECUTION" in host|guest) ;; *) echo "CORP_EXECUTION must be host or guest"; exit 2 ;; esac

echo "=== corp preflight — class=$CLASS execution=$EXECUTION target=$TARGET${WORK:+ work=$WORK}  $(date '+%Y-%m-%d %H:%M:%S') ==="

# ---------------------------------------------------------------- 1. cwd / repo
if git -C "$PWD" rev-parse --git-dir >/dev/null 2>&1; then
  note "cwd IS a repo ($PWD) — isolation:'worktree' would work, but agents self-managing worktrees is still the safe default."
else
  note "cwd is NOT a repo ($PWD) — NEVER pass isolation:'worktree'; it hard-fails every agent at spawn, 0 tokens. Have agents run: git -C <repo> worktree add /private/tmp/corp-<round>-<label> <branch>"
fi
if [ -d "$TARGET/.git" ] || git -C "$TARGET" rev-parse --git-dir >/dev/null 2>&1; then
  note "target repo tip: $(git -C "$TARGET" log -1 --format='%h %ad %s' --date=short 2>/dev/null | cut -c1-90)"
  dirty=$(git -C "$TARGET" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  [ "$dirty" != "0" ] && warn "target has $dirty uncommitted paths — never trust a 'tree clean' claim; check git status yourself before dispatching builders."
fi

# ---------------------------------------------------------------- 2. durable state location
# E17: the campaign's work folder holds CORP_STATE.md and its commits — for the software classes
# ~/<project>-audits/<date>-<slug>/, never the product repo (no commits straight to the working branch).
STATE_DIR=$(state_dir_for "$CLASS" "$TARGET" "$WORK")
if [ -z "$STATE_DIR" ]; then
  park "No work folder given for a software campaign: CORP_STATE.md has no durable home and CAMPAIGN_START cannot be read (E17, F7)." \
       "Re-run with a work folder outside the repo: preflight.sh $CLASS $TARGET ~/$(basename "$TARGET")-audits/$(date +%Y-%m-%d)-<slug>/"
elif case "$CLASS" in software-*) true ;; *) false ;; esac && WHY_IN=$(work_inside_target "$STATE_DIR" "$TARGET"); then
  park "The work folder $STATE_DIR is not outside the target: $WHY_IN — CORP_STATE.md and its commits would land on the product's branch (E17, F7)." \
       "Pass a work folder outside the repo: preflight.sh $CLASS $TARGET ~/$(basename "$TARGET")-audits/$(date +%Y-%m-%d)-<slug>/"
elif is_durable "$STATE_DIR"; then
  note "CORP_STATE.md goes in $STATE_DIR (durable)."
else
  park "State-file location '$STATE_DIR' is not a safe durable home: $(why_not_durable "$STATE_DIR")." \
       "Pick a durable working folder (~/<project>-audits/<date>-<slug>/, ~/<project>/) and mirror there BEFORE dispatching the first agent."
fi
if [ -n "$STATE_DIR" ] && { [ -f "$STATE_DIR/CORP_STATE.md" ] || [ -f "$STATE_DIR/AUTOLOOP_STATE.md" ]; }; then
  warn "A state file already exists in $STATE_DIR. RESUME KEYS ON AUTHORSHIP: if /corp did not write it, it is evidence to verify, NOT a queue to adopt. No Author line = not yours — verify by content and deliverable match, then stamp the Author line the first time you touch it."
fi
# D3: share-check.sh's <start> is the CAMPAIGN's start (written once), never a round's RUN_START.
echo
if [ -z "$STATE_DIR" ]; then
  echo "[state]     no work folder given — PARK: pass ~/$(basename "$TARGET")-audits/<date>-<slug>/ as the third argument (never the target repo); CAMPAIGN_START and git are read there"
  CS=""
else
  CS=$(campaign_start_of "$STATE_DIR")
fi
if [ -z "$STATE_DIR" ]; then
  :
elif [ -n "$CS" ] && valid_stamp "$CS"; then
  echo "[state]     CAMPAIGN_START=$CS   # from the state file: share-check.sh's <start> at assembly and at deploy (never RUN_START)"
elif [ -n "$CS" ]; then
  echo "[state]     CAMPAIGN_START=$CS   # NOT a valid YYYYMMDDhhmm"
  warn "CAMPAIGN_START=$CS in $STATE_DIR is not a real local YYYYMMDDhhmm (touch -t would reject it, and share-check.sh would skip its mtime lane): fix it to the campaign's real start."
elif [ -f "$STATE_DIR/CORP_STATE.md" ]; then
  echo "[state]     CAMPAIGN_START=<not recorded>"
  warn "CORP_STATE.md in $STATE_DIR has no CAMPAIGN_START: record the campaign's REAL start (its first round, YYYYMMDDhhmm local) — a later stamp shrinks share-check's window and reads a reviewer's earlier saves as the base."
elif [ "$(campaign_stage "$STATE_DIR")" = rounds-without-state ]; then
  echo "[state]     CAMPAIGN_START=<not recorded>"
  warn "$STATE_DIR/corp/ holds round output but there is no CORP_STATE.md: this is not a new campaign — find its first round's start (git log, the oldest corp/ file) and record THAT; never mint a new stamp per round (E17)."
else
  echo "[state]     CAMPAIGN_START=$(date +%Y%m%d%H%M)   # a new campaign: write it ONCE into CORP_STATE.md — share-check.sh's <start> (never RUN_START)"
fi
# D8: rule #1 covers the state files too — appends and edits. The work folder is a git repo with a commit before every
# state write (CORP_STATE.md, corp_state.json, OWNER_NOTES.md, INPUTS.md).
WG=$([ -n "$STATE_DIR" ] && work_git "$STATE_DIR" || printf 'skipped')
case "$WG" in
  skipped) : ;;
  git\ *) echo "[state]     work folder under git (${WG#git }): commit before every state write — rule #1, appends count" ;;
  none)   echo "[state]     work folder NOT under git"
          warn "Rule #1 (appends count): $STATE_DIR is not a git repo. Run once, outside any client share and any target repo: git -C \"$STATE_DIR\" init -q && git -C \"$STATE_DIR\" add -A && git -C \"$STATE_DIR\" commit -qm 'corp: campaign start' — then commit before every round block and state edit (where git cannot be used: cp -p X X.bak-\$(date +%Y%m%d) first)." ;;
  *)      echo "[state]     work folder $STATE_DIR does not exist yet — create it, then git init it (rule #1)" ;;
esac

# ---------------------------------------------------------------- 3. is the owner using the host RIGHT NOW?
# This runs BEFORE anything is executed on the owner's machine. The decoy below is a built binary in a build tree —
# exactly the object class rail 1 names — so asking after running it would be the rail breaking itself.
IDLE=$(ioreg -c IOHIDSystem 2>/dev/null | awk '/HIDIdleTime/ {print int($NF/1000000000); exit}')
PRESENT=0
echo
if [ -n "${IDLE:-}" ]; then
  echo "[host]      owner idle ${IDLE}s"
  [ "$IDLE" -lt 120 ] && PRESENT=1
else
  echo "[host]      idle time unreadable — assume the owner is present"
  PRESENT=1
fi
if [ "$PRESENT" = "1" ]; then
  if runs_build_binaries "$CLASS" && [ "$EXECUTION" = "host" ]; then
    park "The owner is at the keyboard (idle ${IDLE:-?}s) and this class runs build products and gate scripts on the owner's host." \
         "Either wait, or move every execution lane into the guest and re-run with CORP_EXECUTION=guest (record that declaration in CORP_STATE.md — it is the assumption the whole pass rests on). Rail 1 opens 'the owner works on this machine'; ask whether he is using it NOW."
  elif launches_host_gui "$CLASS"; then
    warn "Owner is at the keyboard (idle ${IDLE:-?}s). This class launches host GUI processes (LibreOffice for PDF/page-image QA, Playwright/Chromium for a portal lane): defer those lanes, run them in the guest, or ask. Do not open apps, Finder windows or grab focus."
  fi
else
  launches_host_gui "$CLASS" && note "Owner is away: a GUI launch is not free either — unattended .app launches trigger a keychain prompt storm. A host GUI launch is never routine; declare it in CORP_STATE.md or run it in the guest."
fi

# ---------------------------------------------------------------- 4. rail 1 enforcer: exists, durable, BITES
# Pin the job by LABEL. `grep -i watchdog | head -1` pins nothing: this box has two watch-ish plists and
# would happily pronounce another project's job healthy.
WD_ROWS=$(launchctl list 2>/dev/null | awk 'tolower($3) ~ /watchdog/ {print $0}')
if [ -n "${CORP_WATCHDOG_LABEL:-}" ]; then
  WD_JOB=$(printf '%s\n' "$WD_ROWS" | awk -v L="$CORP_WATCHDOG_LABEL" '$3 == L {print; exit}')
else
  WD_JOB=$(printf '%s\n' "$WD_ROWS" | sed '/^$/d')
  [ "$(printf '%s\n' "$WD_JOB" | sed '/^$/d' | wc -l | tr -d ' ')" -gt 1 ] && WD_JOB="AMBIGUOUS"
fi

echo
if ! runs_build_binaries "$CLASS"; then
  echo "[watchdog]  N/A — class '$CLASS' runs no build products or gate scripts on this host."
  launches_host_gui "$CLASS" && echo "            (it CAN still launch LibreOffice/Chromium — the watchdog does not cover those; see [host] above.)"
  [ -n "$WD_ROWS" ] && note "A watchdog job is loaded anyway: $(printf '%s' "$WD_ROWS" | head -1) (not this run's problem; do not touch it)."
elif [ "$EXECUTION" = "guest" ]; then
  if [ -z "${CORP_GUEST_CHECK:-}" ]; then
    park "CORP_EXECUTION=guest is declared, but nothing verifies a guest exists, is booted, or is reachable." \
         "Re-run with CORP_GUEST_CHECK='<command that exits 0 only when the guest is up, e.g. tart list | grep -q \"guestvm.*running\", or ssh <guest> true>'. A declaration is not a check."
  elif bash -c "$CORP_GUEST_CHECK" >/dev/null 2>&1; then
    echo "[watchdog]  N/A — every execution lane is DECLARED guest-side and the guest check passed: $CORP_GUEST_CHECK"
    note "That declaration is load-bearing: write it and the guest-check command into CORP_STATE.md; if any lane turns out to need the host, stop and re-run this preflight."
  else
    park "CORP_EXECUTION=guest is declared, but the guest check FAILED: $CORP_GUEST_CHECK" \
         "Boot/provision the guest (see references/software-release.md §Guest runner), or run host-side only with a proven enforcer and the owner away."
  fi
elif [ "$WD_JOB" = "AMBIGUOUS" ]; then
  park "More than one watchdog-ish launchd job is loaded; this preflight will not guess which one enforces rail 1." \
       "Re-run with CORP_WATCHDOG_LABEL=<the enforcing job's label>. Loaded: $(printf '%s' "$WD_ROWS" | awk '{print $3}' | tr '\n' ' ')"
elif [ -z "$WD_JOB" ]; then
  park "No containment watchdog is loaded${CORP_WATCHDOG_LABEL:+ under label $CORP_WATCHDOG_LABEL}, and class '$CLASS' runs binaries on this host." \
       "Owner work: install/load the enforcer from a DURABLE path (~/.claude/bin/), or re-run with CORP_EXECUTION=guest and every execution lane in the guest. Until then: PARK."
else
  WD_STATUS=$(echo "$WD_JOB" | awk '{print $2}')
  WD_LABEL=$(echo "$WD_JOB" | awk '{print $3}')
  WD_PLIST="$HOME/Library/LaunchAgents/$WD_LABEL.plist"
  # Skip the interpreter argv[0] — the enforcer is the SCRIPT, and /bin/zsh always exists,
  # which is exactly how a job pointing at a wiped scratchpad reads as healthy.
  WD_PROG=$(plutil -extract ProgramArguments xml1 -o - "$WD_PLIST" 2>/dev/null \
            | grep -o '<string>[^<]*</string>' | sed 's/<[^>]*>//g' | grep '^/' \
            | grep -vE '^(/bin/sh|/bin/bash|/bin/zsh|/usr/bin/env|.*/python[0-9.]*)$' | head -1)
  echo "[watchdog]  label=$WD_LABEL last-exit=$WD_STATUS script=${WD_PROG:-<unreadable plist>}"

  [ "$WD_STATUS" != "0" ] && [ "$WD_STATUS" != "-" ] && \
    warn "watchdog last exit status = $WD_STATUS (127 = its script is missing; KeepAlive respawns it forever, so 'the job is loaded' means nothing)."
  if [ -n "$WD_PROG" ] && [ ! -f "$WD_PROG" ]; then
    park "Watchdog script does not exist: $WD_PROG — the job is loaded and failing on every respawn." \
         "Owner work: move the script to a durable path (~/.claude/bin/) and update $WD_PLIST, or bootout the job and drop rail 1's mechanical-enforcement promise. Do not edit launchd from inside a pass."
  elif [ -n "$WD_PROG" ] && ! is_durable "$WD_PROG"; then
    park "Watchdog script lives at $WD_PROG, which is not durable: $(why_not_durable "$WD_PROG"). A permanent job pointed at an ephemeral directory is how this rail died silently for three weeks." \
         "Owner work: relocate to ~/.claude/bin/ and update $WD_PLIST."
  fi

  # --- the functional proof. A PID check is not a kill test ("Watchdog 91162 alive" proved nothing), and a
  # --- decoy that never ran is INCONCLUSIVE, not a bite: `cp /bin/sleep` under a new path is SIGKILLed by the
  # --- OS itself on arm64 (rc=137), which reads as a watchdog kill.
  # --- So: compile a decoy, assert it is ALIVE at t=1s, and only then believe a later death.
  if [ -n "${CORP_BUILD_TREE:-}" ]; then
    BUILD_TREE="$CORP_BUILD_TREE"
  else
    BUILD_TREE=""
    for c in build .build DerivedData dist target out; do
      [ -d "$TARGET/$c" ] && { BUILD_TREE="$TARGET/$c"; break; }
    done
    [ -z "$BUILD_TREE" ] && BUILD_TREE="$TARGET/build"
    note "build-products tree guessed as $BUILD_TREE — Swift builds into DerivedData, python into dist; set CORP_BUILD_TREE if that is the wrong tree, because the decoy proves nothing outside the patterns' reach."
  fi
  if [ "$PRESENT" = "1" ]; then
    echo "[watchdog]  decoy SKIPPED — the owner is at the keyboard (PARK above); existence, durability and last-exit were still checked."
    bite="NOT RUN — owner present"
  else
    bite=$(run_decoy "$BUILD_TREE" 15 cc)
  fi
  if [ "$bite" = "BITES" ]; then
    echo "[watchdog]  DECOY KILLED in <15s — the enforcer bites on $BUILD_TREE."
  else
    echo "[watchdog]  decoy kill test: $bite"
    park "Rail 1's enforcer is NOT PROVEN to bite ($bite). An unproven enforcer is an unenforced rail, whatever launchctl says." \
         "Set CORP_BUILD_TREE=<the tree the watchdog patterns match> and re-run; if it still does not kill the decoy, that is owner work: check the patterns are ANCHORED TO THE EXECUTABLE and cover this tree. Until it bites: CORP_EXECUTION=guest, or PARK."
  fi
fi

# ---------------------------------------------------------------- 5. rail 6: is this a human surface?
LOCKS=$(find "$TARGET" -maxdepth 3 -name '~$*' 2>/dev/null | head -3)
if [ -n "$LOCKS" ]; then
  echo
  warn "Word lock file(s) under the target: $(printf '%s' "$LOCKS" | tr '\n' ' ') — someone has these open. A LOCKFILE IS A RED LIGHT FOR THE WHOLE FOLDER: do not write into it, write to an isolated folder and hand the owner the path."
fi
case "$CLASS" in
  document|document-set)
    note "Rail 6 default: build in an isolated folder and hand the owner a path. Before ANY write to a shared folder — at ASSEMBLY time and again at deploy — run: scripts/share-check.sh <destination folder> \"\$CAMPAIGN_START\"; never a round's RUN_START. A NEW folder (E7): mkdir \"<target>\" WITHOUT -p (it fails if anything is there — the atomic absent-check), then share-check that new, empty folder — never the parent client tree. Archive first (mkdir -p the _ARCHIVE folder, then move; adopted human bases stay in place), never delete; copy the act's src, which §GATE listed (only the row's files, F1), recursively: rsync -a --update --backup <act.src>/ <dest>/ (never --delete, F7); after the copy, scripts/share-check.sh --record <dest> <act.src> <campaign> '<build stamp>' --action <action.json> writes .corp-deployed.json for the row's files only, so the next check reads them as ours (E16, F1). A human edit is the base: share-check.sh --adopt-human <file> records it (F3); a rebuild on it is a new version file beside it." ;;
esac

# ---------------------------------------------------------------- 6. capacity
echo
CORES=$(sysctl -n hw.ncpu 2>/dev/null || echo '?')
LOAD=$(uptime | sed 's/.*load averages*: //')
FREE=$(df -g "$TARGET" 2>/dev/null | awk 'NR==2 {print $4}')
echo "[capacity]  cores=$CORES  load=$LOAD  free-on-target=${FREE:-?}Gi"
[ -n "${FREE:-}" ] && [ "$FREE" -lt 5 ] && \
  park "Only ${FREE}Gi free on the target volume." "Free space before dispatching; a guest hit 2.0 GiB mid-campaign and voided the round."
note "Serialize heavy lanes strictly one at a time; state the concurrency ceiling in CORP_STATE.md. Concurrent gate runs on one shared machine voided a whole corpus verification run."
note "Probe top-tier access with ONE throwaway agent before any fan-out over ~10 and before the final gate's Fable seats — a bad \`model:\` hard-fails with no fallback (26 agents once died in 56ms); Claude Code's safety classifiers can still re-run a flagged request on a fallback model: record any in the round's model mix."

# ---------------------------------------------------------------- 7. §JEV gate — every class, no exceptions
# §JEV: "nothing stands in for it." This is a reachability probe only — on failure it never substitutes
# another checker, it PARKs and names the fix per §JEV's own exit codes.
echo
# §JEV: /corp runs on jev-latest. A JEV_MODEL left in the environment would silently pin another build.
if [ -n "${JEV_MODEL:-}" ] && [ "$JEV_MODEL" != "jev-latest" ]; then
  park "JEV_MODEL=$JEV_MODEL is set in the environment; /corp runs on jev-latest." \
       "unset JEV_MODEL (or set it to jev-latest) and re-run preflight."
fi
JEV_T0=$(date +%s%N 2>/dev/null || echo 0)
JEV_ERR=$(jev ping 2>&1 >/tmp/.corp-preflight-jev-out.$$)
JEV_RC=$?
JEV_OUT=$(cat /tmp/.corp-preflight-jev-out.$$ 2>/dev/null); rm -f /tmp/.corp-preflight-jev-out.$$ 2>/dev/null
JEV_T1=$(date +%s%N 2>/dev/null || echo 0)
JEV_MS=$(( (JEV_T1 - JEV_T0) / 1000000 ))
if [ "$JEV_RC" -eq 0 ]; then
  JEV_BUILD=$(printf '%s' "$JEV_OUT" | grep -o '"model"[^,}]*' | head -1 | sed 's/.*: *"//; s/"$//')
  echo "[jev]       PASS — jev-latest → ${JEV_BUILD:-unknown build} responded in ${JEV_MS}ms."
  echo "[jev]       JEV_BUILD=${JEV_BUILD:-unknown}   # record in CORP_STATE.md and SLOTS.JEV_BUILD; a different build than last round = RAIL NOTE (§JEV)"
  echo "[jev]       build check: no export needed — the CLI flags any reply from a build with no re-gate PASS for the current questions (\"build_mismatch\": true → it escalates, ladder off)"
  HOOKS_CFG="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/jev/scripts/hooks_config.json"
  HOOKS_TUNED=$(hooks_tuned_build "$HOOKS_CFG")
  HOOKS_DRIFT=$(hooks_drift_line "$HOOKS_TUNED" "${JEV_BUILD:-}")
  if [ -n "$HOOKS_DRIFT" ]; then
    echo "[jev]       $HOOKS_DRIFT"
    warn "Hooks are warn-only: run \`python3 ~/.claude/skills/jev/scripts/hooks-regate.py --apply\` (four hook suites on the new build; it versions hooks_config.json first — owner configuration) and log a RAIL NOTE. Until it passes, rule #1's airlock denies nothing (E15)."
  else
    echo "[jev]       hooks tuned on ${HOOKS_TUNED:-unknown} = the build answering now: the airlock, belay, tier guard and jev-gate deny/block as tuned"
  fi
  echo "[jev]       RUN_START=$(date -u +%Y-%m-%dT%H:%M:%S+00:00)   # record in CORP_STATE.md; the round block's \$ = jev usage --since \"\$RUN_START\" (machine-wide); never share-check's start"
  # §JEV re-gate: the 1.1 clear bar holds only on a build that passed the golden set (cached per build; ~10 s on a new one).
  REGATE_BIN="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/jev-regate"
  REGATE_OUT=$("$REGATE_BIN" 2>&1); REGATE_RC=$?
  REGATE_SUM=$(printf '%s' "$REGATE_OUT" | tail -1 | python3 -c 'import json,sys
try:
    d=json.loads(sys.stdin.read()); print("clear %s/%s, clear-and-wrong %s%s" % (d.get("clear"), d.get("n"), d.get("clear_wrong"), " (cached)" if d.get("cached") else ""))
except Exception: print("no summary")' 2>/dev/null)
  if [ "$REGATE_RC" -eq 0 ]; then
    echo "[jev]       REGATE PASS on ${JEV_BUILD:-unknown} — ${REGATE_SUM}."
    echo "[jev]       JEV_LADDER=on   # SLOTS.JEV_LADDER; record in CORP_STATE.md"
  else
    echo "[jev]       REGATE $([ "$REGATE_RC" -eq 5 ] && echo FAIL || echo "COULD NOT RUN (exit $REGATE_RC)") on ${JEV_BUILD:-unknown} — ${REGATE_SUM}."
    echo "[jev]       JEV_LADDER=off  # SLOTS.JEV_LADDER; the ladder skips no verifier this run — Jev still orders and seconds; floors unchanged"
    warn "Jev re-gate did not pass on ${JEV_BUILD:-unknown} (exit $REGATE_RC): JEV_LADDER=off — every Jev-compared item escalates. Log a RAIL NOTE; every plain preflight re-runs it (a failed build is not cached as a pass)."
  fi
else
  case "$JEV_RC" in
    127)
      if [ -x "$HOME/.local/bin/jev" ]; then
        park "jev exists at ~/.local/bin/jev but \`jev ping\` exit 127 (not on PATH, or python3 not found by its shebang)." \
             "export PATH=\"\$HOME/.local/bin:\$PATH\" and confirm \`command -v python3\`; do not re-link"
      else
        park "jev is not installed (\`jev ping\` exit 127 — command not found)." \
             "ln -s ~/.claude/skills/corp/scripts/jev ~/.local/bin/jev"
      fi
      ;;
    2)
      park "jev ping exit 2 = bad call." \
           "fix scripts/preflight.sh's invocation, not the key — $(printf '%s' "$JEV_ERR" | tail -5)"
      ;;
    3)
      if printf '%s' "$JEV_ERR$JEV_OUT" | grep -q "credits exhausted"; then
        park "OpenRouter credits exhausted (\`jev ping\` exit 3, HTTP 402)." \
             "owner adds credits at https://openrouter.ai/settings/credits (or raises the key's credit limit); do not substitute a local model"
      else
        park "jev has no usable OpenRouter key (\`jev ping\` exit 3: no key, or 401/403)." \
             "no OpenRouter key: owner runs 'jev setkey'"
      fi
      ;;
    4)
      park "jev/OpenRouter UNAVAILABLE after jev's own retries (\`jev ping\` exit 4)." \
           "OpenRouter unreachable — retry later; do not substitute a local model"
      ;;
    *)
      park "jev ping failed (exit $JEV_RC)." \
           "$(printf '%s' "$JEV_ERR" | tail -5)"
      ;;
  esac
  echo "[jev]       PARK — see remediation below."
fi

# ---------------------------------------------------------------- 8. §MODEL — the harness and what each alias runs (D17)
# Informational, never a PARK. Copy the line into CORP_STATE.md; a change between rounds is a RAIL NOTE. Builders are set
# per class in the kit (document / document-set: opus at xhigh; software: sonnet) — nothing here switches them.
echo
CC_VER=$(harness_version)
echo "[model]     $(model_line "$CC_VER")"
AG_OUT=$(corp_agents_report "$HOME/.claude/agents"); AG_RC=$?
printf '%s\n' "$AG_OUT"
AG_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/agents"
[ "$AG_RC" -ne 0 ] && warn "E11: a seat spawned through the Agent tool cannot set effort without its corp-* type — restore them from the committed source (F7): mkdir -p ~/.claude/agents && cp -p -n \"$AG_SRC\"/corp-*.md ~/.claude/agents/ (restart Claude Code if ~/.claude/agents/ is new), or spawn the seats through a Workflow agent() with model and effort set."
DR_OUT=$(corp_agents_drift "$AG_SRC" "$HOME/.claude/agents"); DR_RC=$?
printf '%s\n' "$DR_OUT"
[ "$DR_RC" -ne 0 ] && warn "F7: an installed corp-* agent type is not its committed source ($AG_SRC): a seat runs at what the installed copy says — run each reinstall line above (it versions the installed copy first), then restart Claude Code."
if [ -z "$CC_VER" ]; then
  warn "Claude Code's version is unreadable, so preflight cannot say what each alias runs: write a RAIL NOTE and record the model a seat reports."
elif ! ver_ge "$CC_VER" "$SONNET55_MIN"; then
  warn "harness $CC_VER < $SONNET55_MIN: the sonnet seats (software builders, extraction, claim audits, PMO) run Sonnet 5, not 5.5 — update the Claude app, or record it as a RAIL NOTE."
fi
HW=$(haiku_warn "$CC_VER"); [ -n "$HW" ] && warn "$HW"

# ---------------------------------------------------------------- 8b. the cores fit the compaction budget (D19)
SKILLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CORE_OUT=$(core_budget_report "$SKILLS_DIR/corp/SKILL.md"); CORE_RC=$?
printf '%s\n' "$CORE_OUT"
if [ "$CORE_RC" -ne 0 ]; then
  park "A core SKILL.md is over the $CORE_MAX-byte budget or missing: $(printf '%s' "$CORE_OUT" | grep -E 'OVER BUDGET|MISSING' | tr '\n' ' ')" \
       "Trim that core back to <= $CORE_MAX bytes (wc -c) before any dispatch — never drop a rail, move detail to references/. After a compaction Claude Code re-attaches only the first ~5,000 tokens of a skill, so text past the budget can silently fall off."
fi

# ---------------------------------------------------------------- 9. [fresh] — is what /corp absorbed still current?
# Informational, never a PARK: corp/sources.json registers every outside source /corp absorbed and its re-read cadence.
echo
SOURCES_JSON="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/sources.json"
FRESH_OUT=$(fresh_report "$SOURCES_JSON" "$(corp_today)")
printf '%s\n' "$FRESH_OUT" | grep -v '^NOTE: '
FRESH_NOTE=$(printf '%s\n' "$FRESH_OUT" | sed -n 's/^NOTE: //p')
[ -n "$FRESH_NOTE" ] && note "$FRESH_NOTE"

# ---------------------------------------------------------------- verdict
echo
for n in "${NOTES[@]:-}"; do [ -n "$n" ] && echo "  note: $n"; done
for w in "${WARNS[@]:-}"; do [ -n "$w" ] && echo "  WARN: $w"; done
echo
if [ "${#PARKS[@]}" -eq 0 ]; then
  echo "PREFLIGHT: PASS — dispatch. Paste this block into CORP_STATE.md § Campaign."
  exit 0
fi
echo "PREFLIGHT: PARK — ${#PARKS[@]} blocking condition(s). Do not dispatch."
for p in "${PARKS[@]}"; do echo "  - $p"; done
echo
echo "Write the PARK and its remediation into CORP_STATE.md, tell the owner what is needed to"
echo "resume, and stop. PARK has never fired in this skill's history; it is the honest exit."
exit 1
