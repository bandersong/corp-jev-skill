#!/bin/bash
# corp share-check — is a human working in this folder RIGHT NOW, or since I last looked?
# Rail 6 is the only rail in this skill whose breach is irreversible: a blind `rsync -a` onto a
# shared folder can destroy other people's in-progress work. Rail 1's answer to "people do not
# comply with instructions" was a mechanical enforcer; this is rail 6's.
#
# Usage:  share-check.sh <folder> [campaign-start, anything `touch -t` understands, e.g. 202609071400]
#         share-check.sh --record <dest> <src> <campaign> [<stamp>] --action <action.json>
#                                                  after a deploy: write <dest>/.corp-deployed.json for the row's files
#         share-check.sh --adopt-human <file>      a human edit becomes the base (CEO decision F3)
#         share-check.sh --diff <folder>           the manifest, file by file, against the folder now
#         share-check.sh --self-test
#
# Run it TWICE: at ASSEMBLY time (the send folder was once built from a stale copy of a letter a
# reviewer had already edited) and again immediately before any authorized write.
#
# CHECK (the default) is READ-ONLY. It never copies, moves, archives or deletes. It prints the archive-first
# command for the owner to authorize, and exits non-zero if anything human is in the folder. Its last line is
# machine-readable for §GATE (`jev gate --q go_act` reads it from the file action.json names):
#   SHARE-CHECK-RESULT {"exit": 0|1, "folder": <abs>, "since": <stamp>, "epoch": <s>, "ts": <iso>, "manifest": <n>|null, "hits": <n>}
#
# OUR OWN DEPLOYS ARE NOT HUMANS (CEO decision E16). A deploy leaves <dest>/.corp-deployed.json (written by
# --record, never by hand): {relative path: md5, stamp, ts, campaign}. CHECK exempts a file whose current md5 equals
# its manifest md5 (ours), reports a changed md5 as a HUMAN EDIT and a missing one as GONE (both stop), and treats a
# directory as ours only when nothing changed in it after the manifest was written. A file not in the manifest follows
# the lanes below. A NEW, EMPTY folder (CEO decision E7: `mkdir "<target>"` WITHOUT -p is the atomic absent-check) has
# nothing to protect and passes; never share-check the parent client tree.
#
# --record <dest> <src> <campaign> [<stamp>] --action <action.json>  after the copy (CEO decision F1: it never vouches
#   for a file the row did not name): <src> must be the act's src (state.act.src, the folder §GATE listed), every file
#   under <src> must be one the adopted row (state.go.row) names, and every row file must sit at the same relative path
#   under <dest> with the row's md5 (else exit 1, nothing written). Records those files, keeps the previous manifest's
#   entries that are still byte-identical where they were, and recognizes our earlier bytes moved within <dest> (the
#   archive-first move, rsync --backup's `~` copies) by md5. An earlier entry that is neither is UNEXPLAINED, and a row
#   file that landed over a human edit adopted as the base is OVER_ADOPTED: exit 1, nothing written. It writes ONE file,
#   <dest>/.corp-deployed.json (atomic rename), after copying the previous one aside as
#   .corp-deployed.json.bak-<YYYYMMDD-HHMMSS> (rule #1). <stamp> = the build stamp for files that carry none (a
#   .docx/.xlsx/.pptx records its own lastModifiedBy).
# --adopt-human <file>  (CEO decision F3: human edits are the BASE) records the file's current md5 in the nearest
#   .corp-deployed.json at or above it, marked "adopted" with who (its lastModifiedBy) and when (its mtime), after
#   versioning the manifest; prints a RAIL NOTE line for the ledger. Later checks read it as ours while it is unchanged;
#   the printed archive-first move leaves it in place, and §GATE and --record refuse any file that would land over it --
#   a rebuild on the reviewer's edit is a NEW version file beside it. Refused while a Word lock is anywhere in that folder. E9: a
#   draft back from signature is adopted this way before its census and md5 checks.
# --diff <folder>  (CEO decision E9: a draft back from signature) every manifest file UNCHANGED / CHANGED / GONE, and
#   every other file NEW; exit 0 when nothing differs, 1 when something does, 2 with no manifest. Read-only.

set -u
MANIFEST_NAME=".corp-deployed.json"

# The one Python pass behind CHECK lanes 2-3, --record and --diff. argv: mode folder [...]
corp_py() {
  python3 - "$@" <<'PY'
import sys, os, re, json, time, zipfile, hashlib, shutil, xml.etree.ElementTree as ET
BUILD_STAMPS = {'Acme Org reconsideration build', 'Acme Org assessment build', 'Acme Org P2P brief build', 'Acme Org appeal build'}   # exact match only — identities no human uses; python-docx builds set this
MANIFEST = '.corp-deployed.json'
SLACK_S = 5          # a directory changed within this many seconds after the manifest was written changed with it
OFFICE = ('.docx', '.xlsx', '.pptx')

def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def core_props(p):
    """(lastModifiedBy, modified) from docProps/core.xml; raises on an unreadable package."""
    with zipfile.ZipFile(p) as z:
        r = ET.fromstring(z.read('docProps/core.xml'))
    lmb = mod = ''
    for el in r.iter():
        tag = el.tag.split('}')[-1]
        if tag == 'lastModifiedBy': lmb = (el.text or '').strip()
        elif tag == 'modified': mod = (el.text or '').strip()
    return lmb, mod

def is_manifest_file(name):
    return name == MANIFEST or name.startswith(MANIFEST + '.')     # the manifest, its .bak- copies, a stray .tmp-

def skip_name(name):
    return name == '.DS_Store' or name.startswith('~$')

def load_manifest(folder):
    """-> (files {rel: md5}, raw dict, mtime) | (None, None, None) when absent. Raises ValueError when unreadable."""
    mp = os.path.join(folder, MANIFEST)
    if not os.path.exists(mp):
        return None, None, None
    with open(mp, encoding='utf-8') as fh:
        d = json.load(fh)
    files = d.get('files') if isinstance(d, dict) else None
    if not isinstance(files, dict):
        raise ValueError('no "files" object')
    out = {}
    for rel, e in files.items():
        want = e.get('md5') if isinstance(e, dict) else None
        if not isinstance(rel, str) or not rel or os.path.isabs(rel) or '..' in rel.split('/') \
                or not isinstance(want, str) or not re.fullmatch(r'[0-9a-f]{32}', want):
            raise ValueError(f'entry {rel!r} is not a relative path with an md5')
        out[rel] = want
    return out, d, os.stat(mp).st_mtime

def walk_files(folder):
    """Every regular file under folder as a relative path (no lockfiles, .DS_Store or manifest files at the root)."""
    rels = []
    for root, dirs, files in os.walk(folder):
        dirs.sort()
        for f in sorted(files):
            if skip_name(f):
                continue
            rel = os.path.relpath(os.path.join(root, f), folder)
            if root == folder and is_manifest_file(f):
                continue
            if os.path.isfile(os.path.join(root, f)) and not os.path.islink(os.path.join(root, f)):
                rels.append(rel)
    return rels

def action_files(action_path):
    """F1: (act.src absolute, {real path of a row file: its md5}) from action.json -- the adopted row's files in any
    form the gate reads ({path: md5}, [{path, md5}], ["<path> · <md5>"], or artifact + md5); paths resolve against
    action.json's folder. Raises ValueError when there is no row."""
    with open(action_path, encoding='utf-8') as fh:
        req = json.load(fh)
    base = os.path.dirname(os.path.abspath(action_path))
    state = req.get('state') if isinstance(req, dict) else None
    state = state if isinstance(state, dict) else {}
    act = state.get('act') if isinstance(state.get('act'), dict) else {}
    go = state.get('go') if isinstance(state.get('go'), dict) else {}
    row = go.get('row') if isinstance(go.get('row'), dict) else None
    if not row:
        raise ValueError('no state.go.row: no adopted row, nothing it names')

    def expand(q):
        q = os.path.expanduser(str(q))
        return q if os.path.isabs(q) else os.path.join(base, q)
    files, want = row.get('files'), {}
    if isinstance(files, dict):
        want = {str(k): str(v or '') for k, v in files.items()}
    elif isinstance(files, list):
        for f in files:
            if isinstance(f, dict) and f.get('path'):
                want[str(f['path'])] = str(f.get('md5') or '')
            elif isinstance(f, str):
                m = re.match(r'^\s*(.+?)\s*[·|]\s*`?([0-9a-f]{32})`?\s*$', f)
                want[m.group(1) if m else f.strip()] = m.group(2) if m else ''
    elif row.get('artifact'):
        want = {str(row['artifact']): str(row.get('md5') or '')}
    src = act.get('src')
    return (expand(src) if isinstance(src, str) and src.strip() else None), \
        {os.path.realpath(expand(k)): v for k, v in want.items()}

def adopted_of(raw):
    return {rel for rel, e in ((raw or {}).get('files') or {}).items() if isinstance(e, dict) and e.get('adopted')}

def unreadable(e):   # os.walk's onerror: a folder it could not list is a skipped check, never a pass
    print(f"UNREADABLE\t{getattr(e, 'filename', '?')}\t{e.__class__.__name__}\t")

def check(folder, since, ref):
    since8 = re.sub(r'\D', '', since)[:8]
    ref_t = os.stat(ref).st_mtime if ref else None
    try:
        man, raw, man_t = load_manifest(folder)
    except (OSError, ValueError) as e:
        print(f"MANIFEST_UNREADABLE\t{os.path.join(folder, MANIFEST)}\t{e}")
        man, raw, man_t = None, None, None
    ours, flagged = set(), set()
    if man is not None:
        print(f"MANIFEST\t{len(man)}")
        adopted = adopted_of(raw)
        for rel, want in sorted(man.items()):
            p = os.path.join(folder, rel)
            if not os.path.isfile(p):
                print(f"GONE\t{p}\t{want}"); flagged.add(os.path.realpath(p)); continue
            try:
                got = md5(p)
            except OSError as e:
                print(f"UNREADABLE\t{p}\t{e.__class__.__name__}\t"); flagged.add(os.path.realpath(p)); continue
            if got == want:
                ours.add(os.path.realpath(p))
                if rel in adopted:
                    a = raw['files'][rel].get('adopted') or {}
                    print(f"ADOPTED\t{p}\t{a.get('by', '?')}\t{a.get('ts', '?')}")
            else:
                print(f"CHANGED\t{p}\t{got}\t{want}"); flagged.add(os.path.realpath(p))
        print(f"OURS\t{len(ours)}")
    # lane 2: <cp:lastModifiedBy> in docProps/core.xml — Word stamps a person's name there; python-docx does not.
    for root, dirs, files in os.walk(folder, onerror=unreadable):
        dirs.sort()
        for f in sorted(files):
            if f.startswith('~$') or not f.lower().endswith(OFFICE): continue
            p = os.path.join(root, f)
            if os.path.realpath(p) in ours or os.path.realpath(p) in flagged: continue   # the manifest already spoke
            try:
                lmb, mod = core_props(p)
            except Exception as e:
                print(f"UNREADABLE\t{p}\t{e.__class__.__name__}\t"); continue
            if not lmb: continue
            if lmb in BUILD_STAMPS: print(f"BUILD\t{p}\t{lmb}\t{mod}"); continue
            m8 = re.sub(r'\D', '', mod)[:8]
            if since8 and m8 and m8 < since8: print(f"PRESTAMP\t{p}\t{lmb}\t{mod}"); continue   # saved before the campaign: the base, not an edit
            print(f"HUMAN\t{p}\t{lmb}\t{mod}")
    # lane 3: anything modified since the campaign started (catches xlsx, pptx, pdf, renames) — minus our own bytes.
    if ref_t is None:
        return
    root_entries = [e for e in os.listdir(folder) if not skip_name(e)]
    for root, dirs, files in os.walk(folder, onerror=unreadable):
        dirs.sort()
        entries = [(root, True)] if root == folder else []
        entries += [(os.path.join(root, d), True) for d in dirs] + [(os.path.join(root, f), False) for f in sorted(files)]
        for p, is_dir in entries:
            name = os.path.basename(p)
            if name == '.DS_Store' or (not is_dir and os.path.dirname(p) == folder and is_manifest_file(name)):
                continue
            try:
                t = os.lstat(p).st_mtime
            except OSError:
                continue
            if t <= ref_t:
                continue
            if is_dir:
                if p == folder and not root_entries:
                    print(f"EMPTY\t{p}"); continue                       # a NEW folder: nothing in it to protect
                if man_t is not None and t <= man_t + SLACK_S:
                    continue                                              # changed only by our deploy
            else:
                rp = os.path.realpath(p)
                if rp in ours or rp in flagged:
                    continue
            print(f"NEWER\t{p}")

def record(dest, src, campaign, stamp, action):
    anomalies, entries, now = [], {}, time.strftime('%Y-%m-%dT%H:%M:%S%z')
    try:
        prev, prev_raw, _ = load_manifest(dest)
    except (OSError, ValueError) as e:
        print(f"REFUSED\tthe existing manifest is unreadable ({e}): move it aside by hand, then record again"); return 1
    prev = prev or {}
    prev_entries = (prev_raw or {}).get('files') or {}
    adopted = adopted_of(prev_raw)
    # F1: --record vouches only for the files the adopted row names, copied from the act's own src
    try:
        a_src, want = action_files(action)
    except (OSError, ValueError, AttributeError) as e:
        print(f"REFUSED\tcannot read the act from {action} ({e}): --record records only the files the GO'd row names (F1)")
        return 1
    if not a_src or os.path.realpath(a_src) != os.path.realpath(src):
        print(f"REFUSED\tthe copied folder {src} is not the act's src ({a_src or 'none named'}): --record vouches only "
              f"for the folder §GATE listed (F1)")
        return 1
    if not want:
        print("REFUSED\tthe row names no files: nothing to vouch for (F1)"); return 1
    real_src = os.path.realpath(src).rstrip(os.sep)
    rows = {}
    for rp, row_md5 in sorted(want.items()):
        if not rp.startswith(real_src + os.sep):
            anomalies.append(f"OUTSIDE_SRC\t{rp}\ta row file outside {src}: it was never copied"); continue
        rows[os.path.relpath(rp, real_src)] = row_md5
    for rel in walk_files(src):
        if os.path.realpath(os.path.join(src, rel)) not in want:
            anomalies.append(f"NOT_NAMED\t{os.path.join(src, rel)}\t{src} holds a file the row does not name: --record "
                             f"never vouches for it -- quarantine it and deploy again (F1)")

    def stamp_of(p):
        if p.lower().endswith(OFFICE):
            try:
                return core_props(p)[0] or stamp
            except Exception:
                return stamp
        return stamp
    # 1. the deploy itself: every row file landed intact, at the row's md5, at the same relative path under dest
    for rel, row_md5 in sorted(rows.items()):
        s, d = os.path.join(src, rel), os.path.join(dest, rel)
        if rel in adopted:
            anomalies.append(f"OVER_ADOPTED\t{d}\ta human edit adopted as the base: the deploy wrote over it -- rsync "
                             f"--backup kept the reviewer's copy beside it (\"{rel}~\"): restore it; a rebuild goes to a NEW version "
                             f"file beside the reviewer's, never over it (F3)"); continue
        if not os.path.isfile(s) or md5(s) != row_md5:
            anomalies.append(f"SRC_CHANGED\t{s}\tnot the bytes the row names (md5 {row_md5})"); continue
        if not os.path.isfile(d):
            anomalies.append(f"NOT_DEPLOYED\t{d}\tmissing (src {s})"); continue
        got = md5(d)
        if got != row_md5:
            anomalies.append(f"MISMATCH\t{d}\tmd5 {got} != the row's {row_md5}"); continue
        entries[rel] = {'md5': got, 'stamp': stamp_of(d), 'ts': now, 'campaign': campaign}
    # 2. earlier entries still byte-identical where they were
    carried = 0
    for rel, want in prev.items():
        if rel in entries: continue
        p = os.path.join(dest, rel)
        if os.path.isfile(p) and md5(p) == want:
            entries[rel] = dict(prev_entries.get(rel) or {}, md5=want); carried += 1
    # 3. our earlier bytes, moved inside dest (the archive-first move, rsync --backup's `~` copy)
    by_md5 = {}
    for rel, want in prev.items():
        by_md5.setdefault(want, rel)
    moved, found = 0, set()
    for rel in walk_files(dest):
        if rel in entries: continue
        got = md5(os.path.join(dest, rel))
        if got in by_md5:
            entries[rel] = {'md5': got, 'stamp': (prev_entries.get(by_md5[got]) or {}).get('stamp', ''), 'ts': now,
                            'campaign': campaign, 'moved_from': by_md5[got]}
            found.add(got); moved += 1
    # 4. an earlier entry that is neither redeployed, nor unchanged in place, nor found moved: a human did something
    for rel, want in sorted(prev.items()):
        if rel in entries or want in found: continue
        p = os.path.join(dest, rel)
        anomalies.append(f"UNEXPLAINED\t{p}\t{'changed' if os.path.isfile(p) else 'gone'} since the previous record "
                         f"(md5 {want}) and not found moved: a human trace — run share-check and pull it as the base")
    if anomalies:
        for a in anomalies: print(a)
        print(f"REFUSED\t{len(anomalies)} problem(s): nothing written"); return 1
    new = sum(1 for rel in entries if rel not in prev and 'moved_from' not in entries[rel])
    mp = os.path.join(dest, MANIFEST)
    if os.path.exists(mp):
        base = f"{mp}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
        bak, n = base, 1
        while os.path.exists(bak):
            n += 1; bak = f"{base}-{n}"
        shutil.copy2(mp, bak)
        print(f"VERSIONED\t{bak}")
    tmp = f"{mp}.tmp-{os.getpid()}"
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump({'corp_deploy_manifest': 1, 'campaign': campaign, 'updated': now,
                   'files': dict(sorted(entries.items()))}, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    os.replace(tmp, mp)
    print(f"RECORDED\t{mp}\t{len(entries)} file(s): {new} new or redeployed, {carried} unchanged from the previous "
          f"record, {moved} of our earlier bytes moved inside the folder")
    return 0

def adopt(path):
    """F3: a human edit becomes the base -- its current md5 goes into the nearest manifest, marked adopted."""
    p = os.path.abspath(path)
    if not os.path.isfile(p):
        print(f"REFUSED\t{p}: no such file"); return 2
    name = os.path.basename(p)
    if skip_name(name) or is_manifest_file(name):
        print(f"REFUSED\t{p}: a lockfile or the manifest itself is never a base"); return 1
    dest = os.path.dirname(p)
    while not os.path.isfile(os.path.join(dest, MANIFEST)):
        parent = os.path.dirname(dest)
        if parent == dest:
            print(f"REFUSED\t{p}: no {MANIFEST} in its folder or above -- this campaign never deployed there, so there is "
                  "nothing to adopt against"); return 1
        dest = parent
    for root, dirs, files in os.walk(dest):
        for f in files:
            if f.startswith('~$'):
                print(f"REFUSED\t{os.path.join(root, f)}: a Word lock -- someone has a document open in this folder; "
                      "adopt after it closes"); return 1
    try:
        _, raw, _ = load_manifest(dest)
    except (OSError, ValueError) as e:
        print(f"REFUSED\tthe manifest in {dest} is unreadable ({e})"); return 1
    rel = os.path.relpath(p, dest)
    prev = raw['files'].get(rel) if isinstance(raw['files'].get(rel), dict) else None
    new_md5, now = md5(p), time.strftime('%Y-%m-%dT%H:%M:%S%z')
    if prev and prev.get('md5') == new_md5:
        print(f"UNCHANGED\t{p}\t{new_md5}: the manifest already holds these bytes -- nothing to adopt"); return 0
    who = ''
    if name.lower().endswith(OFFICE):
        try:
            who = core_props(p)[0]
        except Exception:
            who = ''
    who = who or 'unknown (no lastModifiedBy: not an Office file)'
    when = time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime(os.stat(p).st_mtime))
    entry = dict(prev or {}, md5=new_md5, ts=now, campaign=(prev or {}).get('campaign') or raw.get('campaign') or '')
    entry['stamp'] = who
    entry['adopted'] = {'by': who, 'at': when, 'prev_md5': (prev or {}).get('md5'), 'ts': now}
    raw['files'][rel] = entry
    raw['updated'] = now
    mp = os.path.join(dest, MANIFEST)
    base = f"{mp}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
    bak, n = base, 1
    while os.path.exists(bak):
        n += 1; bak = f"{base}-{n}"
    shutil.copy2(mp, bak)
    print(f"VERSIONED\t{bak}")
    tmp = f"{mp}.tmp-{os.getpid()}"
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(raw, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    os.replace(tmp, mp)
    print(f"ADOPTED\t{p}\t{who}\t{when}\t{(prev or {}).get('md5') or 'none'}\t{new_md5}")
    print(f"RAIL NOTE — rail 6 (F3): adopted {rel} in {dest} as the base -- a human edit by \"{who}\" saved {when}; md5 "
          f"{(prev or {}).get('md5') or 'none (not deployed by us)'} -> {new_md5}. Later share-checks read it as ours while "
          "it is unchanged; a rebuild on it goes to a NEW version file beside it, never over it.")
    return 0

def archive_excludes(folder):
    """The printed archive-first move leaves every adopted human base in place (F3): one `! -name` per top-level entry
    holding one."""
    try:
        _, raw, _ = load_manifest(folder)
    except (OSError, ValueError):
        return
    import shlex
    for top in sorted({rel.split('/')[0] for rel in adopted_of(raw)}):
        print(f"! -name {shlex.quote(top)}", end=' ')

def diff(folder):
    try:
        man, _, _ = load_manifest(folder)
    except (OSError, ValueError) as e:
        print(f"MANIFEST_UNREADABLE\t{e}"); return 2
    if man is None:
        print(f"NO_MANIFEST\t{os.path.join(folder, MANIFEST)}"); return 2
    changes = 0
    for rel, want in sorted(man.items()):
        p = os.path.join(folder, rel)
        if not os.path.isfile(p):
            print(f"GONE\t{rel}\t{want}"); changes += 1; continue
        got = md5(p)
        if got == want:
            print(f"UNCHANGED\t{rel}\t{got}")
        else:
            print(f"CHANGED\t{rel}\t{got}\t(manifest {want})"); changes += 1
    for rel in walk_files(folder):
        if rel not in man:
            print(f"NEW\t{rel}\t{md5(os.path.join(folder, rel))}"); changes += 1
    return 1 if changes else 0

mode = sys.argv[1]
if mode == 'check':
    check(sys.argv[2], sys.argv[3], sys.argv[4])
elif mode == 'record':
    sys.exit(record(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6]))
elif mode == 'adopt':
    sys.exit(adopt(sys.argv[2]))
elif mode == 'excludes':
    archive_excludes(sys.argv[2])
elif mode == 'diff':
    sys.exit(diff(sys.argv[2]))
PY
}

scan() {
  local folder="$1" since="$2" hits=0 ref=""
  # 1. Word lock files, ANY depth. A lockfile is a red light for the WHOLE folder, not just its file.
  local locks
  locks=$(find "$folder" -name '~$*' 2>/dev/null)
  if [ -n "$locks" ]; then
    echo "LOCKED — someone has a document open in this folder:"
    printf '%s\n' "$locks" | sed 's/^/    /'
    hits=$((hits+1))
  fi

  # 3's reference time. touch -t parses the stamp exactly as it always has; an unparseable one is a skipped check.
  if [ -n "$since" ]; then
    ref=$(mktemp -t corpshare) || return 3
    if ! touch -t "$since" "$ref" 2>/dev/null; then
      echo "NOTE — could not parse '$since' (want e.g. 202609071400); mtime check skipped, and a skipped check is not a pass."
      hits=$((hits+1))
      rm -f "$ref"; ref=""
    fi
  else
    echo "NOTE — no campaign-start timestamp given, so the mtime lane did not run. Pass one."
  fi

  # 2 + 3 + the deploy manifest, in one pass (stdlib XML parse, namespace-agnostic — a `tr '>' '>\n'` pipeline here
  # was a silent no-op once: tr truncates SET2).
  local out newer="" pyrc
  out=$(corp_py check "$folder" "$since" "$ref"); pyrc=$?
  [ -n "$ref" ] && rm -f "$ref"
  if [ "$pyrc" -ne 0 ]; then
    echo "UNREADABLE — the scan of $folder failed (python3 exit $pyrc): a skipped check is not a pass"
    hits=$((hits+1))
  fi
  if [ -n "$out" ]; then
    while IFS=$'\t' read -r kind f who when; do
      [ -n "$kind" ] || continue
      case "$kind" in
        HUMAN)    echo "HUMAN EDIT — $f: last saved in Office by \"$who\"${when:+ at $when}"; hits=$((hits+1)) ;;
        BUILD)    echo "build stamp — $f: \"$who\"${when:+ at $when} (allow-listed build identity, not a human trace)" ;;
        PRESTAMP) echo "pre-campaign author stamp — $f: \"$who\"${when:+ at $when} (saved before campaign start: the base, not an edit)" ;;
        MANIFEST) echo "deploy manifest — $folder/$MANIFEST_NAME lists $f file(s) this campaign deployed" ;;
        OURS)     echo "ours — $f of them unchanged since our deploy (md5 = the manifest's): not a human trace" ;;
        ADOPTED)  echo "adopted base — $f: a human edit by \"$who\", adopted ${when} (F3): ours while unchanged; a rebuild goes to a NEW version file beside it, never over it" ;;
        CHANGED)  echo "HUMAN EDIT — $f: changed since our deploy (md5 $who, the manifest says $when) — pull it as the base"; hits=$((hits+1)) ;;
        GONE)     echo "GONE — $f: this campaign deployed it (md5 $who) and it is no longer there — moved, renamed or deleted by someone"; hits=$((hits+1)) ;;
        MANIFEST_UNREADABLE) echo "UNREADABLE manifest — $f ($who): a skipped check is not a pass"; hits=$((hits+1)) ;;
        EMPTY)    echo "empty folder — $f holds nothing to protect (a NEW folder: mkdir without -p, then this check)" ;;
        NEWER)    newer="$newer$f"$'\n' ;;
        *)        echo "UNREADABLE — $f ($who): a skipped check is not a pass"; hits=$((hits+1)) ;;
      esac
    done <<<"$out"
  fi
  if [ -n "$newer" ]; then
    local n; n=$(printf '%s' "$newer" | grep -c .)
    echo "TOUCHED SINCE $since — not necessarily yours, and not ours by the deploy manifest:"
    printf '%s' "$newer" | head -20 | sed 's/^/    /'
    [ "$n" -gt 20 ] && echo "    … and $((n-20)) more"
    hits=$((hits+1))
  fi
  return "$hits"
}

result_line() {  # exit folder since hits
  python3 - "$@" <<'PY'
import json, os, sys, time
rc, folder, since, hits = int(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4])
m = os.path.join(folder, '.corp-deployed.json')
try:
    n = len(json.load(open(m, encoding='utf-8')).get('files') or {}) if os.path.exists(m) else None
except Exception:
    n = None
print('SHARE-CHECK-RESULT ' + json.dumps({"exit": rc, "folder": os.path.realpath(folder), "since": since,
      "epoch": int(time.time()), "ts": time.strftime('%Y-%m-%dT%H:%M:%S%z'), "manifest": n, "hits": hits}))
PY
}

case "${1:-}" in
  --record)
    shift; POS=(); ACTION=""
    while [ $# -gt 0 ]; do
      case "$1" in
        --action) ACTION="${2:-}"; shift 2 ;;
        --action=*) ACTION="${1#--action=}"; shift ;;
        *) POS+=("$1"); shift ;;
      esac
    done
    DEST="${POS[0]:-}"; SRC="${POS[1]:-}"; CAMP="${POS[2]:-}"; STAMP="${POS[3]:-}"
    { [ -d "$DEST" ] && [ -d "$SRC" ] && [ -n "$CAMP" ] && [ -f "$ACTION" ] && [ "${#POS[@]}" -le 4 ]; } || {
      echo "usage: share-check.sh --record <dest folder> <src folder that was copied> <campaign> [<build stamp>] --action <action.json>"
      echo "       --action names the act §GATE approved: --record vouches only for the files its row names (F1)"; exit 2; }
    corp_py record "$DEST" "$SRC" "$CAMP" "$STAMP" "$ACTION"
    exit $? ;;
  --adopt-human)
    [ -f "${2:-}" ] && [ $# -eq 2 ] || { echo "usage: share-check.sh --adopt-human <file>   (a human edit becomes the base, F3)"; exit 2; }
    corp_py adopt "$2"
    exit $? ;;
  --diff)
    [ -d "${2:-}" ] || { echo "usage: share-check.sh --diff <folder>"; exit 2; }
    corp_py diff "$2"
    exit $? ;;
esac

FOLDER="${1:-}"
SINCE="${2:-}"

if [ "$FOLDER" = "--self-test" ]; then
  d=$(mktemp -d); fail=0
  mkdir -p "$d/clean" "$d/human"
  python3 - "$d" <<'PY' 2>/dev/null || { echo "self-test needs python3 to build the fixtures"; exit 3; }
import sys, zipfile
d = sys.argv[1]
core = '<?xml version="1.0"?><cp:coreProperties xmlns:cp="x" xmlns:dcterms="y">%s</cp:coreProperties>'
with zipfile.ZipFile(d + '/clean/a.docx', 'w') as z:      # python-docx style: no lastModifiedBy
    z.writestr('docProps/core.xml', core % '<dcterms:modified>2026-09-01T00:00:00Z</dcterms:modified>')
with zipfile.ZipFile(d + '/human/b.docx', 'w') as z:      # saved in Word by a person
    z.writestr('docProps/core.xml', core % '<cp:lastModifiedBy>Reviewer Name</cp:lastModifiedBy><dcterms:modified>2026-09-06T12:00:00Z</dcterms:modified>')
import os; os.makedirs(d + '/stamps', exist_ok=True)
with zipfile.ZipFile(d + '/stamps/c.docx', 'w') as z:     # allow-listed build identity
    z.writestr('docProps/core.xml', core % '<cp:lastModifiedBy>Acme Org reconsideration build</cp:lastModifiedBy><dcterms:modified>2026-09-08T15:35:22Z</dcterms:modified>')
with zipfile.ZipFile(d + '/stamps/d.docx', 'w') as z:     # a person's save BEFORE campaign start
    z.writestr('docProps/core.xml', core % '<cp:lastModifiedBy>Old Author</cp:lastModifiedBy><dcterms:modified>2026-08-01T00:00:00Z</dcterms:modified>')
os.makedirs(d + '/src/SEND TO', exist_ok=True)            # a local build to deploy: our stamp, a PDF in a subfolder
with zipfile.ZipFile(d + '/src/01 Appeal.docx', 'w') as z:
    z.writestr('docProps/core.xml', core % '<cp:lastModifiedBy>Acme Org appeal build</cp:lastModifiedBy><dcterms:modified>2026-09-28T21:00:00Z</dcterms:modified>')
open(d + '/src/SEND TO/01 Appeal.pdf', 'wb').write(b'%PDF-1.4 appeal v1\n')
PY
  out=$(scan "$d/clean" ""); rc=$?
  [ "$rc" -eq 0 ] || { echo "FAIL clean folder must pass (rc=$rc): $out"; fail=1; }
  out=$(scan "$d/human" ""); rc=$?
  who=$(printf '%s' "$out" | sed -n 's/.*by "\([^"]*\)".*/\1/p' | head -1)
  [ "$who" = "Reviewer Name" ] || { echo "FAIL lastModifiedBy extraction not exact: got '$who' in: $out"; fail=1; }
  [ "$rc" -gt 0 ] || { echo "FAIL human edit must exit non-zero"; fail=1; }
  out=$(scan "$d/stamps" "209901010000"); rc=$?
  case "$out" in *"build stamp"*) ;; *) echo "FAIL build stamp not allow-listed: $out"; fail=1 ;; esac
  case "$out" in *"pre-campaign author stamp"*) ;; *) echo "FAIL pre-campaign stamp not classified: $out"; fail=1 ;; esac
  [ "$rc" -eq 0 ] || { echo "FAIL build stamp + pre-campaign stamp must pass with since set (rc=$rc): $out"; fail=1; }
  out=$(scan "$d/stamps" ""); rc=$?
  case "$out" in *"HUMAN EDIT"*"Old Author"*) ;; *) echo "FAIL without since, an author stamp must stay HUMAN: $out"; fail=1 ;; esac
  [ "$rc" -gt 0 ] || { echo "FAIL without since, author stamp must exit non-zero"; fail=1; }
  : > "$d/clean/~\$a.docx"
  out=$(scan "$d/clean" ""); rc=$?
  case "$out" in *LOCKED*) ;; *) echo "FAIL lockfile not detected: $out"; fail=1 ;; esac
  [ "$rc" -gt 0 ] || { echo "FAIL lockfile must exit non-zero"; fail=1; }

  # E7 + E16: the deploy manifest. The campaign started an hour ago; everything below is written "now".
  START=$(date -v-1H +%Y%m%d%H%M)
  mkaction() {   # $1 = the act's src, $2 = action.json to write, [$3 ...] = only these files (relative to src)
    python3 - "$@" <<'PY'
import hashlib, json, os, sys
src, out, only = sys.argv[1], sys.argv[2], sys.argv[3:]
files = {}
for root, dirs, names in os.walk(src):
    for n in names:
        p = os.path.join(root, n)
        if n == '.DS_Store' or (only and os.path.relpath(p, src) not in only):
            continue
        with open(p, 'rb') as fh:
            files[p] = hashlib.md5(fh.read()).hexdigest()
with open(out, 'w') as fh:
    json.dump({"state": {"go": {"reply": "GO 3", "row": {"id": 3, "verb": "deploy", "files": files}},
                         "act": {"verb": "deploy", "src": src, "files": sorted(files)}}}, fh)
PY
  }
  back() { python3 -c 'import os,sys,time
t = time.time() - int(sys.argv[1])
for p in sys.argv[2:]: os.utime(p, (t, t))' "$@"; }   # as if a minute had passed since the deploy
  mkdir "$d/dest" || { echo "FAIL mkdir of a NEW folder"; fail=1; }
  mkdir "$d/dest" 2>/dev/null && { echo "FAIL mkdir without -p must fail on an existing folder (E7)"; fail=1; }
  out=$(scan "$d/dest" "$START"); rc=$?
  case "$out" in *"empty folder"*) ;; *) echo "FAIL a NEW empty folder is named as such: $out"; fail=1 ;; esac
  [ "$rc" -eq 0 ] || { echo "FAIL a NEW empty folder must pass (E7) (rc=$rc): $out"; fail=1; }
  cp -R "$d/src/" "$d/dest/"                                      # the deploy (no manifest yet)
  out=$(scan "$d/dest" "$START"); rc=$?
  [ "$rc" -gt 0 ] || { echo "FAIL a deploy with no manifest must still stop (nothing vouches for it): $out"; fail=1; }
  out=$(bash "$0" --record "$d/dest" "$d/src" camp-selftest "Acme Org appeal build"); rc=$?
  [ "$rc" -eq 2 ] || { echo "FAIL --record without --action must refuse: it records only the row's files (F1) (rc=$rc): $out"; fail=1; }
  mkaction "$d/src" "$d/a1.json"
  out=$(bash "$0" --record "$d/dest" "$d/src" camp-selftest "Acme Org appeal build" --action "$d/a1.json"); rc=$?
  [ "$rc" -eq 0 ] && [ -f "$d/dest/.corp-deployed.json" ] || { echo "FAIL --record after a clean deploy (rc=$rc): $out"; fail=1; }
  back 60 "$d/dest" "$d/dest/SEND TO" "$d/dest/.corp-deployed.json"
  out=$(scan "$d/dest" "$START"); rc=$?                                    # first deploy, checked after (doctrine h)
  case "$out" in *"ours — 2 of them unchanged"*) ;; *) echo "FAIL first deploy: our 2 files must read as ours: $out"; fail=1 ;; esac
  [ "$rc" -eq 0 ] || { echo "FAIL first deploy must pass after --record (rc=$rc): $out"; fail=1; }
  line=$(bash "$0" "$d/dest" "$START" | tail -1)
  case "$line" in 'SHARE-CHECK-RESULT {"exit": 0,'*'"manifest": 2'*) ;; *) echo "FAIL machine-readable last line: $line"; fail=1 ;; esac
  # an unchanged redeploy, archive-first: move everything but earlier archives and the manifest, copy v2, record
  printf '%%PDF-1.4 appeal v2\n' > "$d/src/SEND TO/01 Appeal.pdf"
  A="$d/dest/_ARCHIVE 2026-09-28 r2"; mkdir -p "$A"
  find "$d/dest" -mindepth 1 -maxdepth 1 ! -name '_ARCHIVE *' ! -name '.corp-deployed.json*' -exec mv -n {} "$A/" \;
  cp -R "$d/src/" "$d/dest/"
  mkaction "$d/src" "$d/a2.json"
  out=$(bash "$0" --record "$d/dest" "$d/src" camp-selftest "Acme Org appeal build" --action "$d/a2.json"); rc=$?
  case "$out" in *"2 of our earlier bytes moved"*) ;; *) echo "FAIL --record must recognize the archived v1 by md5: $out"; fail=1 ;; esac
  [ "$rc" -eq 0 ] && ls "$d/dest/.corp-deployed.json.bak-"* >/dev/null 2>&1 || { echo "FAIL --record versions the old manifest (rc=$rc): $out"; fail=1; }
  back 60 "$d/dest" "$d/dest/SEND TO" "$A" "$A/SEND TO" "$d/dest/.corp-deployed.json"
  out=$(scan "$d/dest" "$START"); rc=$?
  [ "$rc" -eq 0 ] || { echo "FAIL an archive-first redeploy must pass after --record (rc=$rc): $out"; fail=1; }
  out=$(scan "$d/dest" "$START"); rc=$?                                    # and again, nothing changed: still ours
  [ "$rc" -eq 0 ] || { echo "FAIL an unchanged redeploy must pass (rc=$rc): $out"; fail=1; }
  out=$(bash "$0" --diff "$d/dest"); rc=$?
  [ "$rc" -eq 0 ] && [ "$(printf '%s\n' "$out" | grep -c '^UNCHANGED')" -eq 4 ] || { echo "FAIL --diff of an untouched deploy (rc=$rc): $out"; fail=1; }
  # a human edit after the deploy: the md5 moves -> HUMAN EDIT, stop; --diff names it; --record refuses
  printf '%%PDF-1.4 appeal v2, signed\n' > "$d/dest/SEND TO/01 Appeal.pdf"
  out=$(scan "$d/dest" "$START"); rc=$?
  case "$out" in *"HUMAN EDIT"*"changed since our deploy"*) ;; *) echo "FAIL a human edit after deploy must read as one: $out"; fail=1 ;; esac
  [ "$rc" -gt 0 ] || { echo "FAIL a human edit after deploy must stop (rc=$rc)"; fail=1; }
  out=$(bash "$0" --diff "$d/dest"); rc=$?
  case "$out" in *"CHANGED	SEND TO/01 Appeal.pdf"*) ;; *) echo "FAIL --diff names the changed file: $out"; fail=1 ;; esac
  [ "$rc" -eq 1 ] || { echo "FAIL --diff exits 1 on a change (rc=$rc)"; fail=1; }
  out=$(bash "$0" --record "$d/dest" "$d/src" camp-selftest --action "$d/a2.json"); rc=$?
  [ "$rc" -eq 1 ] || { echo "FAIL --record refuses when a deployed copy is not the source's (rc=$rc): $out"; fail=1; }
  mkdir -p "$d/src2"; cp "$d/src/01 Appeal.docx" "$d/src2/"               # a redeploy that leaves the edited PDF alone
  mkaction "$d/src2" "$d/a3.json"
  out=$(bash "$0" --record "$d/dest" "$d/src2" camp-selftest --action "$d/a3.json"); rc=$?
  case "$out" in *UNEXPLAINED*"SEND TO/01 Appeal.pdf"*) ;; *) echo "FAIL --record names an earlier file a human changed: $out"; fail=1 ;; esac
  [ "$rc" -eq 1 ] || { echo "FAIL --record refuses on an UNEXPLAINED earlier file (rc=$rc)"; fail=1; }
  printf '%%PDF-1.4 appeal v2\n' > "$d/dest/SEND TO/01 Appeal.pdf"; back 60 "$d/dest/SEND TO"
  # a deployed file gone -> stop; a lockfile beside our files -> stop; a human's new file with an OLD mtime -> the
  # folder's own mtime moved after the manifest -> stop
  mv "$d/dest/01 Appeal.docx" "$d/moved.docx"
  out=$(scan "$d/dest" "$START"); rc=$?
  case "$out" in *"GONE"*) ;; *) echo "FAIL a deployed file that vanished must read as GONE: $out"; fail=1 ;; esac
  [ "$rc" -gt 0 ] || { echo "FAIL GONE must stop"; fail=1; }
  mv "$d/moved.docx" "$d/dest/01 Appeal.docx"; back 60 "$d/dest"
  : > "$d/dest/~\$Appeal.docx"
  out=$(scan "$d/dest" "$START"); rc=$?
  case "$out" in *LOCKED*) ;; *) echo "FAIL a lockfile beside our deployed files: $out"; fail=1 ;; esac
  [ "$rc" -gt 0 ] || { echo "FAIL a lockfile must stop even when every file is ours"; fail=1; }
  rm -f "$d/dest/~\$Appeal.docx"; back 60 "$d/dest"
  out=$(scan "$d/dest" "$START"); rc=$?
  [ "$rc" -eq 0 ] || { echo "FAIL restored deploy must pass again (rc=$rc): $out"; fail=1; }
  printf 'notes\n' > "$d/dest/Alex notes.txt"; touch -t 202601010000 "$d/dest/Alex notes.txt"
  out=$(scan "$d/dest" "$START"); rc=$?
  case "$out" in *"TOUCHED SINCE"*"$d/dest"*) ;; *) echo "FAIL a folder changed after the manifest must stop: $out"; fail=1 ;; esac
  [ "$rc" -gt 0 ] || { echo "FAIL a human's file added after the deploy must stop"; fail=1; }

  # F1 (re-gate OPUS RG-01, its sendto/ receipt): a stale v1 in the copied folder -- the row names only v2
  ST="$d/stage/SEND TO Example Plan (final)"; mkdir -p "$ST"
  printf '%%PDF-1.4 enclosure v1 (stale)\n' > "$ST/03 Enclosure v1.pdf"; printf '%%PDF-1.4 enclosure v2\n' > "$ST/03 Enclosure v2.pdf"
  mkaction "$ST" "$d/a-send.json" "03 Enclosure v2.pdf"
  mkdir "$d/appeal"; cp -R "$ST/" "$d/appeal/"                             # the whole folder copied
  out=$(bash "$0" --record "$d/appeal" "$ST" camp-selftest --action "$d/a-send.json"); rc=$?
  case "$out" in *NOT_NAMED*"03 Enclosure v1.pdf"*) ;; *) echo "FAIL --record must refuse a file the row does not name (F1): $out"; fail=1 ;; esac
  [ "$rc" -eq 1 ] && [ ! -f "$d/appeal/.corp-deployed.json" ] || { echo "FAIL --record vouched for a stale v1 (rc=$rc)"; fail=1; }
  out=$(bash "$0" --record "$d/appeal" "$d/src" camp-selftest --action "$d/a-send.json"); rc=$?
  case "$out" in *"is not the act's src"*) ;; *) echo "FAIL --record must refuse a folder that is not the act's src (F1): $out"; fail=1 ;; esac
  mkdir -p "$d/quarantine"; mv "$ST/03 Enclosure v1.pdf" "$d/quarantine/"   # quarantined: the act's src holds only v2
  mkdir "$d/appeal2"; cp -R "$ST/" "$d/appeal2/"
  out=$(bash "$0" --record "$d/appeal2" "$ST" camp-selftest --action "$d/a-send.json"); rc=$?
  [ "$rc" -eq 0 ] || { echo "FAIL --record of the row's files only (rc=$rc): $out"; fail=1; }

  # F3 (re-gate OPUS RG-02, its e9/ receipt): a draft handed over, signed in place -- adopted as the base
  mkdir -p "$d/e9src"
  python3 - "$d/e9src" <<'PY'
import sys, zipfile
core = '<?xml version="1.0"?><cp:coreProperties xmlns:cp="x" xmlns:dcterms="y">%s</cp:coreProperties>'
with zipfile.ZipFile(sys.argv[1] + '/01 Review.docx', 'w') as z:
    z.writestr('docProps/core.xml', core % '<cp:lastModifiedBy>Acme Org assessment build</cp:lastModifiedBy>')
open(sys.argv[1] + '/02 Graphs.pdf', 'wb').write(b'%PDF-1.4 graphs\n')
PY
  mkdir "$d/e9"; cp -R "$d/e9src/" "$d/e9/"; mkaction "$d/e9src" "$d/a-e9.json"
  out=$(bash "$0" --record "$d/e9" "$d/e9src" camp-selftest --action "$d/a-e9.json"); rc=$?
  [ "$rc" -eq 0 ] || { echo "FAIL handover --record (rc=$rc): $out"; fail=1; }
  back 60 "$d/e9" "$d/e9/.corp-deployed.json"
  python3 - "$d/e9" <<'PY'
import sys, zipfile
core = '<?xml version="1.0"?><cp:coreProperties xmlns:cp="x" xmlns:dcterms="y">%s</cp:coreProperties>'
with zipfile.ZipFile(sys.argv[1] + '/01 Review.docx', 'w') as z:      # the Reviewer signs it in Word, in place
    z.writestr('docProps/core.xml', core % '<cp:lastModifiedBy>Alex Reviewer</cp:lastModifiedBy>')
    z.writestr('word/document.xml', '<w:document xmlns:w="w"><w:body>signed</w:body></w:document>')
PY
  out=$(scan "$d/e9" "$START"); rc=$?
  case "$out" in *"HUMAN EDIT"*"changed since our deploy"*) ;; *) echo "FAIL the reviewer's signature reads as a human edit: $out"; fail=1 ;; esac
  [ "$rc" -gt 0 ] || { echo "FAIL a signed copy stops the folder until it is adopted"; fail=1; }
  : > "$d/e9/~\$Reassessment.docx"
  out=$(bash "$0" --adopt-human "$d/e9/01 Review.docx"); rc=$?
  case "$out" in *REFUSED*"Word lock"*) ;; *) echo "FAIL --adopt-human while a Word lock is open must refuse: $out"; fail=1 ;; esac
  mv "$d/e9/~\$Reassessment.docx" "$d/quarantine/"
  out=$(bash "$0" --adopt-human "$d/e9/01 Review.docx"); rc=$?
  case "$out" in *"RAIL NOTE — rail 6 (F3): adopted 01 Review.docx"*'"Alex Reviewer"'*) ;; *) echo "FAIL --adopt-human prints the RAIL NOTE with who: $out"; fail=1 ;; esac
  [ "$rc" -eq 0 ] && ls "$d/e9/.corp-deployed.json.bak-"* >/dev/null 2>&1 || { echo "FAIL --adopt-human versions the manifest first (rc=$rc)"; fail=1; }
  out=$(scan "$d/e9" "$START"); rc=$?
  case "$out" in *"adopted base — "*"Alex Reviewer"*) ;; *) echo "FAIL an adopted base is named as one: $out"; fail=1 ;; esac
  [ "$rc" -eq 0 ] || { echo "FAIL the folder passes once the reviewer's edit is adopted (rc=$rc): $out"; fail=1; }
  out=$(bash "$0" --diff "$d/e9"); rc=$?
  [ "$rc" -eq 0 ] || { echo "FAIL --diff after the adoption: every file UNCHANGED (rc=$rc): $out"; fail=1; }
  out=$(bash "$0" "$d/e9" "$START"); rc=$?
  case "$out" in *"! -name '01 Review.docx'"*) ;; *) echo "FAIL the printed archive move leaves the reviewer's adopted file in place: $out"; fail=1 ;; esac
  line=$(printf '%s\n' "$out" | grep 'rsync ')
  case "$line" in *"rsync -a --update --backup"*) ;; *) echo "FAIL the printed deploy copy is recursive (rsync -a, F7): $line"; fail=1 ;; esac
  case "${line%%#*}" in *--delete*) echo "FAIL the printed deploy copy never deletes: $line"; fail=1 ;; esac
  printf '%%PDF-1.4 graphs, edited\n' > "$d/e9/02 Graphs.pdf"                # another file changed: still a stop
  out=$(scan "$d/e9" "$START"); rc=$?
  [ "$rc" -gt 0 ] || { echo "FAIL adopting one file never exempts another human edit (rc=$rc)"; fail=1; }
  printf '%%PDF-1.4 graphs\n' > "$d/e9/02 Graphs.pdf"
  mkdir -p "$d/e9r"; cp "$d/e9src/01 Review.docx" "$d/e9r/"; mkaction "$d/e9r" "$d/a-over.json"
  out=$(bash "$0" --record "$d/e9" "$d/e9r" camp-selftest --action "$d/a-over.json"); rc=$?
  case "$out" in *OVER_ADOPTED*) ;; *) echo "FAIL --record refuses a file over the reviewer's adopted edit (F3): $out"; fail=1 ;; esac
  mkdir -p "$d/e9v2"; cp "$d/e9src/01 Review.docx" "$d/e9v2/01 Reassessment v2.docx"; mkaction "$d/e9v2" "$d/a-v2.json"
  cp "$d/e9v2/01 Reassessment v2.docx" "$d/e9/"                              # a NEW version file beside the reviewer's
  out=$(bash "$0" --record "$d/e9" "$d/e9v2" camp-selftest --action "$d/a-v2.json"); rc=$?
  [ "$rc" -eq 0 ] && grep -q '"adopted"' "$d/e9/.corp-deployed.json" || { echo "FAIL a new version beside the reviewer's records and keeps the reviewer's adoption (rc=$rc): $out"; fail=1; }
  rm -rf "$d"
  [ "$fail" -eq 0 ] && echo "self-test OK" || echo "self-test FAILED"
  exit "$fail"
fi

[ -d "$FOLDER" ] || { echo "usage: share-check.sh <folder> [campaign-start e.g. 202609071400]  (or --record … --action <action.json>, --adopt-human <file>, --diff, --self-test)"; exit 2; }

echo "=== corp share-check — $FOLDER  $(date '+%Y-%m-%d %H:%M:%S') ==="
scan "$FOLDER" "$SINCE"
HITS=$?
echo
if [ "$HITS" -eq 0 ]; then
  echo "SHARE-CHECK: no human trace found. That is a green light for ONE authorized write, not standing permission."
  echo "The write the owner authorizes, archive-first, never deleting (server-side, then mirror that archive locally):"
  KEEP=$(corp_py excludes "$FOLDER")
  echo "    A=\"$FOLDER/_ARCHIVE $(date '+%Y-%m-%d') <label>\"; mkdir -p \"\$A\" && find \"$FOLDER\" -mindepth 1 -maxdepth 1 ! -name '_ARCHIVE *' ! -name '$MANIFEST_NAME*' ${KEEP}-exec mv -n {} \"\$A/\" \\;"
  [ -n "$KEEP" ] && echo "      (the move leaves the human edits adopted as the base in place, F3: a rebuild on one is a NEW version file beside it)"
  echo "    rsync -a --update --backup <act.src>/ \"$FOLDER/\"   # act.src = the staging folder §GATE listed: only the row's files; recursive; never --delete"
  echo "    share-check.sh --record \"$FOLDER\" <act.src> <campaign> '<build stamp>' --action <action.json>   # writes $MANIFEST_NAME for the row's files only (F1)"
  echo "    then count files both ways and report the two numbers."
  result_line 0 "$FOLDER" "$SINCE" 0
  exit 0
fi
echo "SHARE-CHECK: STOP — $HITS human-trace condition(s). Do not write into this folder."
echo "Human edits are the BASE, not the conflict: pull them, diff them, preserve them verbatim, and build"
echo "this round on top. A lock is a red light for the whole folder — write to an isolated folder and hand"
echo "the owner the path instead."
result_line 1 "$FOLDER" "$SINCE" "$HITS"
exit 1
