// corp-kit.test.js — node --test corp/templates/corp-kit.test.js (or: node corp/templates/corp-kit.test.js)
// No deps. corp-kit.js has no exports (plain paste-in JS), so we load its source and eval it into scope.
const fs = require('node:fs')
const path = require('node:path')
const assert = require('node:assert')
const test = require('node:test').test

const src = fs.readFileSync(path.join(__dirname, 'corp-kit.js'), 'utf8')
// Wrap in a Function that returns everything we need — new Function(...) runs in non-strict global-ish scope,
// which is enough for these top-level `const`/`function` declarations without touching the filesystem again.
const load = new Function(`${src}\nreturn { ladder, JEV_CLEAR, ledgerParagraph, assertSlots, SLOTS, FINDING, CLAIM_AUDIT, PMO_BLOCKER, EDIT_LIST, PANEL_VERDICT, PANEL_FAILURE, STATUS, common, JEV_DEFECT_TRUE, JEV_DEFECT_FALSE, CASCADE_CRITERIA, cascadeRoute, cascadeStep, gateDecision, CASCADE_ITEM, GATE_DECISION, JEV_REGISTRY, JEV_ITEM, THINK_FIRST, mustEscalate, panelVerdict, checkPanelSeat, panelFloor, parseGo, goActBlocks, goActionJson, isClear, claimSeverity, ROLE_CLAIM, rowFiles, replyNamesAct }`)
const kit = load()
kit.SLOTS.JEV_LADDER = 'on'   // preflight PASS; tests below that need 'off' or unfilled set it themselves
const M = { jev_q: 'claim_support', jev_clear: true, jev_reread: 'none' }   // a measured, clear, un-re-read second (D5, E13: only these may stand)

test('ladder: agree + clear + measured + non-blocker/high stands', () => {
  const { stands, escalate, receipts } = kit.ladder([{ id: 'a', severity: 'medium', jev_agree: 'agree', jev_margin: 1.2, ...M }])
  assert.strictEqual(stands.length, 1)
  assert.strictEqual(escalate.length, 0)
  assert.strictEqual(receipts.length, 0)
})

test('ladder: blocker severity escalates even when agree and clear (F1: floor-only item is never bad)', () => {
  const { stands, escalate, bad } = kit.ladder([{ id: 'b', severity: 'blocker', jev_agree: 'agree', jev_margin: 5, jev_reread: 'none', ...M }])
  assert.strictEqual(stands.length, 0)
  assert.strictEqual(escalate.length, 1)
  assert.strictEqual(bad.length, 0)
})

test('ladder: high severity escalates even when agree and clear (F1: floor-only item is never bad)', () => {
  const { stands, escalate, bad } = kit.ladder([{ id: 'b2', severity: 'high', jev_agree: 'agree', jev_margin: 5, jev_reread: 'none', ...M }])
  assert.strictEqual(stands.length, 0)
  assert.strictEqual(escalate.length, 1)
  assert.strictEqual(bad.length, 0)
})

test('ladder: not clear (jev_clear false at margin 1.09) escalates', () => {
  const { stands, escalate } = kit.ladder([{ id: 'c', severity: 'low', jev_agree: 'agree', jev_margin: 1.09, jev_q: 'claim_support', jev_clear: false }])
  assert.strictEqual(stands.length, 0)
  assert.strictEqual(escalate.length, 1)
})

test('ladder: unavailable escalates', () => {
  const { stands, escalate } = kit.ladder([{ id: 'd', severity: 'low', jev_agree: 'unavailable', jev_margin: 0, jev_clear: false }])
  assert.strictEqual(stands.length, 0)
  assert.strictEqual(escalate.length, 1)
})

test('ladder: disagree escalates (once the owning seat re-read it)', () => {
  const { stands, escalate } = kit.ladder([{ id: 'e', severity: 'low', jev_agree: 'disagree', jev_margin: 3, ...M, jev_reread: 'upheld_seat' }])
  assert.strictEqual(stands.length, 0)
  assert.strictEqual(escalate.length, 1)
})

test('ladder: not_compared goes to receipts, not stands or escalate', () => {
  const { stands, escalate, receipts } = kit.ladder([{ id: 'f', severity: 'low', jev_agree: 'not_compared', jev_margin: 0 }])
  assert.strictEqual(stands.length, 0)
  assert.strictEqual(escalate.length, 0)
  assert.strictEqual(receipts.length, 1)
})

test('JEV_CLEAR constant is 1.1', () => {
  assert.strictEqual(kit.JEV_CLEAR, 1.1)
})

const LEDGER = { round: 'r1', dept: 'x', runId: 'w1', agents: 1, tokens: 1, wall: '1m', what: 'w', why: 'y', receipts: [] }
const LEDGER_FULL = { ...LEDGER, jev: 'jev: calls 3', jevSpend: '0.0001', verifiesSkipped: 2, escalated: 1, cascade: 'n/a', gates: 'n/a' }

test('ledgerParagraph throws without o.jev', () => {
  assert.throws(() => kit.ledgerParagraph(LEDGER), /Jev tally/)
})

test('ledgerParagraph prints verifies-skipped, the ladder escalations, Jev spend with its scope, cascade and gates', () => {
  const p = kit.ledgerParagraph({ ...LEDGER_FULL, cascade: 'cascade: units 4 · sent 3 · escalated 1 → sent 1', gates: 'gates: 1 → approve 1' })
  assert.match(p, /verifies skipped 2/)
  assert.match(p, /escalated \(ladder\) 1/)
  assert.match(p, /Jev \$0\.0001 \(all Jev spend on this machine since RUN_START\)/)   // S1-18: machine-wide, labeled
  assert.match(p, /\ncascade: cascade: units 4/)
  assert.match(p, /\ngates: gates: 1 → approve 1/)
})

test('assertSlots throws on any value still shaped like <...>', () => {
  assert.throws(() => kit.assertSlots({ WORK: '<abs durable work folder, never a scratchpad>' }), /unfilled SLOTS/)
})

test('assertSlots passes when every slot is filled', () => {
  assert.doesNotThrow(() => kit.assertSlots({ WORK: '/tmp/x', CLASS: 'software-audit', ROUND: 'r1', DEADLINE: 'none', MODEL_BUILD: 'sonnet', EFFORT_BUILD: 'medium' }))
  assert.doesNotThrow(() => kit.assertSlots({ WORK: '/tmp/x', CLASS: 'document', ROUND: 'r1', DEADLINE: 'none', MODEL_BUILD: 'opus', EFFORT_BUILD: 'xhigh' }))
})

test('assertSlots: document builders run opus at xhigh (D17); software builders keep sonnet', () => {
  for (const CLASS of ['document', 'document-set'])
    for (const [MODEL_BUILD, EFFORT_BUILD] of [['sonnet', 'high'], ['opus', 'high'], ['sonnet', 'xhigh']])
      assert.throws(() => kit.assertSlots({ WORK: '/w', CLASS, ROUND: 'r1', DEADLINE: 'none', MODEL_BUILD, EFFORT_BUILD }), /opus.*xhigh/, `${CLASS} ${MODEL_BUILD}/${EFFORT_BUILD}`)
  assert.doesNotThrow(() => kit.assertSlots({ WORK: '/w', CLASS: 'software-build', ROUND: 'r1', DEADLINE: 'none', MODEL_BUILD: 'sonnet', EFFORT_BUILD: 'high' }))
})

test('SLOTS: claim audit / PMO slots are sonnet at high with the think-first line (D11)', () => {
  const fresh = load()
  assert.strictEqual(fresh.SLOTS.MODEL_AUDIT, 'sonnet')
  assert.strictEqual(fresh.SLOTS.EFFORT_AUDIT, 'high')
  assert.strictEqual(fresh.THINK_FIRST, 'Think the problem through before you answer.')
  assert.strictEqual(fresh.SLOTS.MODEL_JUDGE, 'opus')
  assert.strictEqual(fresh.SLOTS.EFFORT_JUDGE, 'xhigh')
})

test('SLOTS: mechanical seats are haiku at medium; haiku on a build, audit or judgment slot throws (H1)', () => {
  const fresh = load()
  assert.strictEqual(fresh.SLOTS.MODEL_MECH, 'haiku')
  assert.strictEqual(fresh.SLOTS.EFFORT_MECH, 'medium')
  const base = { WORK: '/w', CLASS: 'software-build', ROUND: 'r1', DEADLINE: 'none', MODEL_BUILD: 'sonnet', EFFORT_BUILD: 'high', MODEL_MECH: 'haiku' }
  assert.doesNotThrow(() => kit.assertSlots(base))
  for (const k of ['MODEL_BUILD', 'MODEL_AUDIT', 'MODEL_JUDGE']) assert.throws(() => kit.assertSlots({ ...base, [k]: 'haiku' }), /on haiku/)
})

test('sketch: the claim audit and PMO run MODEL_AUDIT at EFFORT_AUDIT and end with THINK_FIRST; no stale pointer; no sliced blob', () => {
  const sketch = src.split('// ---- Usage sketch')[1]
  const pmo = sketch.split('\n').find(l => l.includes("label: 'pmo'"))
  assert.match(pmo, /model: SLOTS\.MODEL_AUDIT, effort: SLOTS\.EFFORT_AUDIT/)
  assert.match(pmo, /\$\{THINK_FIRST\}/)
  const audit = sketch.split('\n').find(l => l.includes('label: `audit:'))
  assert.match(audit, /model: SLOTS\.MODEL_AUDIT, effort: SLOTS\.EFFORT_AUDIT/)
  assert.match(audit, /\$\{THINK_FIRST\}/)
  assert.doesNotMatch(src, /§JEV:238/)
  for (const line of src.split('\n'))   // S1-19: harness.md's pre-launch lint — never .slice( on the same line as JSON.stringify(
    assert.ok(!(line.includes('JSON.stringify(') && line.includes('.slice(')), line.slice(0, 120))
  assert.match(sketch, /mustEscalate\(a, \{ nonEmpty: 'claims' \}\)/)   // D7: an empty or failed return escalates
})

test('every schema requires status + jev, and its item schema requires jev_agree + jev_margin + jev_reread + jev_clear', () => {
  const cases = [
    [kit.FINDING, 'findings'],
    [kit.CLAIM_AUDIT, 'claims'],
    [kit.PMO_BLOCKER, 'blockers'],
    [kit.EDIT_LIST, 'edits'],
    [kit.PANEL_VERDICT, 'failures'],
  ]
  for (const [schema, key] of cases) {
    assert.ok(schema.required.includes('jev'), `${key} schema must require jev`)
    assert.ok(schema.required.includes('status'), `${key} schema must require status (D7)`)
    assert.deepStrictEqual(schema.properties.status.enum, ['complete', 'partial', 'failed'])
    const itemReq = schema.properties[key].items.required
    for (const f of ['jev_agree', 'jev_margin', 'jev_reread', 'jev_clear']) assert.ok(itemReq.includes(f), `${key} item must require ${f}`)
    assert.ok(!itemReq.includes('jev_build_mismatch'), `${key}: jev_build_mismatch stays optional`)
  }
})

test('PANEL_VERDICT (D5): per-failure blocks + Jev rows; the holistic pick is display only, never seat-level jev_agree', () => {
  assert.ok(kit.PANEL_VERDICT.required.includes('failures'))
  assert.ok(!('blockers' in kit.PANEL_VERDICT.properties))
  assert.ok(!('jev_agree' in kit.PANEL_VERDICT.properties), 'no seat-level jev_agree: the pick never fills it')
  assert.strictEqual(kit.PANEL_VERDICT.properties.jev_pick.type, 'string')
  assert.ok(kit.PANEL_FAILURE.required.includes('blocks'))
  assert.strictEqual(kit.PANEL_FAILURE.properties.blocks.type, 'boolean')
})

test('ladder: throws when severity is missing and no opts.severityOf is given (§JEV floor, TE-04)', () => {
  assert.throws(() => kit.ladder([{ id: 'g', jev_agree: 'agree', jev_margin: 5, ...M }]), /no severity/)
})

test('ladder: PMO_BLOCKER floor (severityOf => blocker) escalates a closed, agreed, clear item (TE-04)', () => {
  const items = [{ id: 'pmo1', status: 'CLOSED', jev_agree: 'agree', jev_margin: 5, jev_q: 'pmo_status', jev_clear: true }]
  const { stands, escalate } = kit.ladder(items, { severityOf: () => 'blocker' })
  assert.strictEqual(stands.length, 0)
  assert.strictEqual(escalate.length, 1)
})

test('ladder: PMO_BLOCKER floor, agree, clear, jev_reread "none" still escalates, never bad (F1)', () => {
  const items = [{ id: 'pmo2', status: 'CLOSED', jev_agree: 'agree', jev_margin: 3, jev_reread: 'none', jev_q: 'pmo_status', jev_clear: true }]
  const { escalate, bad } = kit.ladder(items, { severityOf: () => 'blocker' })
  assert.strictEqual(escalate.length, 1)
  assert.strictEqual(bad.length, 0)
})

test('ladder: non-clear item with jev_reread "none" goes to bad, not escalate (TE-02)', () => {
  const { escalate, bad } = kit.ladder([{ id: 'h', severity: 'low', jev_agree: 'disagree', jev_margin: 3, jev_reread: 'none', ...M }])
  assert.strictEqual(escalate.length, 0)
  assert.strictEqual(bad.length, 1)
})

test('ladder: non-clear item re-read (jev_reread upheld_seat) still escalates, not bad (TE-02, floors unchanged)', () => {
  const { escalate, bad } = kit.ladder([{ id: 'i', severity: 'low', jev_agree: 'disagree', jev_margin: 3, ...M, jev_reread: 'upheld_seat' }])
  assert.strictEqual(escalate.length, 1)
  assert.strictEqual(bad.length, 0)
})

test('ledgerParagraph throws when o.jevSpend is missing (TE-10)', () => {
  assert.throws(() => kit.ledgerParagraph({ ...LEDGER, jev: 'jev: calls 3', verifiesSkipped: 2 }), /Jev spend/)
})

test('ledgerParagraph throws when o.verifiesSkipped is missing (TE-10)', () => {
  assert.throws(() => kit.ledgerParagraph({ ...LEDGER, jev: 'jev: calls 3', jevSpend: '0.0001' }), /verifies skipped/)
})

test('ledgerParagraph requires the ladder count, the cascade line and the gates line (S1-19, S2-23, S3-12)', () => {
  for (const [k, re] of [['escalated', /escalated count/], ['cascade', /cascade line/], ['gates', /gates line/]]) {
    const o = { ...LEDGER_FULL }
    delete o[k]
    assert.throws(() => kit.ledgerParagraph(o), re, k)
    assert.throws(() => kit.ledgerParagraph({ ...LEDGER_FULL, [k]: '' }), re, `${k} empty`)
  }
  assert.doesNotThrow(() => kit.ledgerParagraph(LEDGER_FULL))   // 'n/a' is allowed
})

test('ladder: ARITHMETIC with agree, margin 2 goes to receipts, not stands (F6)', () => {
  const { stands, receipts, escalate } = kit.ladder([{ id: 'j', status: 'ARITHMETIC', jev_agree: 'agree', jev_margin: 2, severity: 'low', ...M }])
  assert.strictEqual(receipts.length, 1)
  assert.strictEqual(stands.length, 0)
  assert.strictEqual(escalate.length, 0)
})

test('sketch guard: a unit whose claims are all not_compared must not stand — dispatches the skeptic (PS-01)', () => {
  const L = kit.ladder([
    { id: 'k1', jev_agree: 'not_compared', jev_margin: 0, severity: 'low' },
    { id: 'k2', status: 'ARITHMETIC', jev_agree: 'not_compared', jev_margin: 0, severity: 'low' },
  ])
  assert.strictEqual(L.escalate.length, 0)
  assert.ok(L.receipts.length > 0)
  // the fixed sketch guard is `!L.escalate.length && !L.receipts.length` — with receipts non-empty it must be false
  const guardWouldStand = !L.escalate.length && !L.receipts.length
  assert.strictEqual(guardWouldStand, false)
})

test('sketch guard: a unit with bad items must fail, never stand (PS-02)', () => {
  const L = kit.ladder([{ id: 'l1', severity: 'low', jev_agree: 'disagree', jev_margin: 3, jev_reread: 'none', ...M }])
  assert.strictEqual(L.bad.length, 1)
  // the fixed sketch checks L.bad.length before the stands guard and fails the unit instead
  const guardFailsUnit = L.bad.length > 0
  assert.strictEqual(guardFailsUnit, true)
})

test('COMMON JEV line: unfolded claim question, a list never through bare ask, no local substitute (final gate F2/F3, S2-20)', () => {
  const c = kit.common(kit.SLOTS, 'rails')
  assert.match(c, /Does the source sentence support the claim as worded\?/)
  assert.match(c, /'ask' without --all = several questions over ONE state; a list goes through filter, rank, second or 'ask --all'/)
  assert.doesNotMatch(c, /jev ask' or 'jev filter --all' over the whole list/)
  assert.doesNotMatch(c, /qwen|local model/i)
})

test('ladder: ladderOff (failed re-gate) — nothing stands, clear agrees escalate', () => {
  const L = kit.ladder([{ id: 'o1', severity: 'low', jev_agree: 'agree', jev_margin: 4, ...M }], { ladderOff: true })
  assert.strictEqual(L.stands.length, 0)
  assert.strictEqual(L.escalate.length, 1)
  assert.strictEqual(L.bad.length, 0)
})

test("ladder: 'unclear' escalates and is never bad (no re-read against a coin flip)", () => {
  const L = kit.ladder([{ id: 'u1', severity: 'low', jev_agree: 'unclear', jev_margin: 0.2, jev_reread: 'none', jev_q: 'keep_reject', jev_clear: false }])
  assert.strictEqual(L.stands.length, 0)
  assert.strictEqual(L.escalate.length, 1)
  assert.strictEqual(L.bad.length, 0)
})

test('schemas accept jev_agree unclear', () => {
  assert.ok(kit.FINDING.properties.findings.items.properties.jev_agree.enum.includes('unclear'))
})

test('COMMON JEV line: abstract verdicts unfolded with measured criteria, UNCLEAR option, lean state (09-28)', () => {
  const c = kit.common(kit.SLOTS, 'rails')
  assert.match(c, /Is this flag a real defect in the deliverable\?/)
  // 09-28 super-skill: the measured criteria travel with the registry's keep_reject question ('jev second' / --q keep_reject),
  // not in every brief; COMMON names the question and must never re-grow the hand-computed agreement rules (R4 F04).
  assert.strictEqual(kit.JEV_REGISTRY.keep_reject.criteria.true, kit.JEV_DEFECT_TRUE)
  assert.strictEqual(kit.JEV_REGISTRY.keep_reject.criteria.false, kit.JEV_DEFECT_FALSE)
  assert.match(c, /'jev second < rows\.jsonl'/)
  assert.doesNotMatch(c, /agree = p_yes on your verdict's side|\|margin\| < 0\.4|delete what you built|SAY SO LOUDLY/)
  assert.doesNotMatch(c, /Seat's verdict: KEEP|Is the seat's verdict correct/)
  assert.match(c, /no notes, no 'checked', no asides/)
})

test('SLOTS.JEV_LADDER ships unfilled so assertSlots forces the copy from preflight', () => {
  const fresh = load()
  assert.match(fresh.SLOTS.JEV_LADDER, /^<.*>$/)
  assert.throws(() => fresh.assertSlots(fresh.SLOTS), /JEV_LADDER/)
  assert.throws(() => fresh.ladder([{ id: 'z', severity: 'low', jev_agree: 'agree', jev_margin: 3, ...M }]), /JEV_LADDER is unfilled/)
})

test("ladder reads SLOTS.JEV_LADDER='off' with no opts.ladderOff — a failed re-gate is enforced by default", () => {
  const k2 = load()
  k2.SLOTS.JEV_LADDER = 'off'
  const L = k2.ladder([{ id: 'o2', severity: 'low', jev_agree: 'agree', jev_margin: 4, ...M }])
  assert.strictEqual(L.stands.length, 0)
  assert.strictEqual(L.escalate.length, 1)
})

test('COMMON: severity not Jev-seconded, edit kind and PMO status batched, non-English → unclear', () => {
  const c = kit.common(kit.SLOTS, 'rails')
  assert.match(c, /Severity is NOT Jev-seconded/)
  assert.match(c, /Is this edit mechanical/)
  assert.match(c, /pmo_status: "Is this item still open according to the evidence shown\?"/)
  assert.doesNotMatch(c, /'jev rate'/)
  assert.match(c, /not in English → jev_agree 'unclear'/)
})

// ---- D5: Jev never decides a verdict; only a measured question's agree + clear stands; a re-ask never erases a disagreement
test('ladder (D5): agree + clear on an unmeasured question escalates — keep/reject, edit kind, blocker, PMO', () => {
  for (const q of ['keep_reject', 'edit_kind', 'blocker', 'pmo_status', 'panel_verdict', 'class_pick']) {
    const L = kit.ladder([{ id: q, severity: 'low', jev_agree: 'agree', jev_margin: 5, jev_q: q, jev_clear: true }])
    assert.strictEqual(L.stands.length, 0, q)
    assert.strictEqual(L.escalate.length, 1, q)
  }
  for (const q of ['claim_support', 'determination']) {
    const L = kit.ladder([{ id: q, severity: 'low', jev_agree: 'agree', jev_margin: 5, jev_q: q, jev_clear: true, jev_reread: 'none' }])
    assert.strictEqual(L.stands.length, 1, q)
  }
})

test('ladder (D5): the question comes from the item, else opts.q; none, or an unknown id, never stands', () => {
  const base = { id: 'q', severity: 'low', jev_agree: 'agree', jev_margin: 5, jev_clear: true, jev_reread: 'none' }
  assert.strictEqual(kit.ladder([base]).stands.length, 0)                                        // no question named
  assert.strictEqual(kit.ladder([base], { q: 'claim_support' }).stands.length, 1)                // opts.q fills it
  assert.strictEqual(kit.ladder([{ ...base, jev_q: 'keep_reject' }], { q: 'claim_support' }).stands.length, 0)   // the item's own wins
  assert.strictEqual(kit.ladder([{ ...base, jev_q: 'no_such_q' }]).stands.length, 0)
  assert.throws(() => kit.ladder([base], { q: 'no_such_q' }), /not a JEV_REGISTRY id/)
})

test('ladder (D5): jev_clear is required — a big margin with no flag is not clear (no fallback)', () => {
  const L = kit.ladder([{ id: 'nc', severity: 'low', jev_agree: 'agree', jev_margin: 9, jev_q: 'claim_support' }])
  assert.strictEqual(L.stands.length, 0)
  assert.strictEqual(L.escalate.length, 1)
  assert.strictEqual(kit.isClear({ jev_margin: 9 }), false)
  assert.strictEqual(kit.isClear({ clear: true }), true)                  // `clear` straight from jev second
  assert.strictEqual(kit.isClear({ jev_clear: false, clear: true }), false)   // the item's own flag wins
})

test('ladder (D5, S3-04): a re-ask never turns a disagreement (or an abstention) into a stand; only unavailable may be replaced', () => {
  const reasked = { id: 'r', severity: 'low', jev_agree: 'agree', jev_margin: 4, ...M }
  let L = kit.ladder([{ ...reasked, jev_first: 'disagree', jev_reread: 'upheld_seat' }])
  assert.deepStrictEqual([L.stands.length, L.escalate.length, L.bad.length], [0, 1, 0])   // to the verifier
  L = kit.ladder([{ ...reasked, jev_first: 'disagree', jev_reread: 'none' }])
  assert.deepStrictEqual([L.stands.length, L.bad.length], [0, 1])                          // re-asked without a re-read: bad
  L = kit.ladder([{ ...reasked, jev_first: 'unclear', jev_reread: 'none' }])
  assert.deepStrictEqual([L.stands.length, L.escalate.length, L.bad.length], [0, 1, 0])
  L = kit.ladder([{ ...reasked, jev_first: 'unavailable', jev_reread: 'none' }])
  assert.strictEqual(L.stands.length, 1)                                                     // a failed call, answered on re-ask
})

test("ladder: an item's own jev_clear decides clarity (a pick needs a concentrated winner too)", () => {
  const L = kit.ladder([
    { id: 'p1', severity: 'low', jev_agree: 'agree', jev_margin: 2.0, jev_clear: false },   // margin passes, winner < 0.75
    { id: 'p2', severity: 'low', jev_agree: 'agree', jev_margin: 0.9, jev_clear: true, jev_reread: 'none' },
    { id: 'p3', severity: 'low', jev_agree: 'agree', jev_margin: 1.2 },                      // no flag: not clear (D5)
    { id: 'p4', severity: 'low', jev_agree: 'agree', jev_margin: 1.2, clear: false },         // `clear` straight from jev second
  ], { q: 'claim_support' })
  assert.deepStrictEqual(L.stands.map(it => it.id), ['p2'])
  assert.deepStrictEqual(L.escalate.map(it => it.id), ['p1', 'p3', 'p4'])
})

test('ladder: a build mismatch escalates that item, turns the ladder off for the round, and says so', () => {
  const k2 = load()
  k2.SLOTS.JEV_LADDER = 'on'
  const L = k2.ladder([
    { id: 'm1', severity: 'low', jev_agree: 'agree', jev_margin: 3, jev_build_mismatch: true, ...M },
    { id: 'm2', severity: 'low', jev_agree: 'agree', jev_margin: 3, ...M },
  ])
  assert.strictEqual(L.stands.length, 0)                        // nothing stands this call either
  assert.deepStrictEqual(L.escalate.map(it => it.id), ['m1', 'm2'])
  assert.strictEqual(L.ladderOff, true)
  assert.strictEqual(L.buildMismatch, 1)
  assert.strictEqual(k2.SLOTS.JEV_LADDER, 'off')                // the rest of the round
  const later = k2.ladder([{ id: 'm3', severity: 'low', jev_agree: 'agree', jev_margin: 3, ...M }])
  assert.strictEqual(later.stands.length, 0)
  const L2 = k2.ladder([{ id: 'm4', severity: 'low', jev_agree: 'agree', jev_margin: 3, build_mismatch: true, ...M }], { ladderOff: false })
  assert.strictEqual(L2.stands.length, 0)                       // a mismatch overrides an explicit ladderOff: false
})

test('JEV_ITEM carries jev_q, jev_first, jev_clear and jev_build_mismatch', () => {
  assert.strictEqual(kit.JEV_ITEM.jev_clear.type, 'boolean')
  assert.strictEqual(kit.JEV_ITEM.jev_build_mismatch.type, 'boolean')
  assert.strictEqual(kit.JEV_ITEM.jev_q.type, 'string')
  assert.deepStrictEqual(kit.JEV_ITEM.jev_first.enum, kit.JEV_ITEM.jev_agree.enum)
})

test('panel (D5): a seat verdict is the worst of its own blocks calls; the panel verdict is a floor', () => {
  const f = (id, blocks, extra = {}) => ({ id, title: id, evidence: 'e', blocks, jev_agree: 'agree', jev_margin: 2, jev_reread: 'none', jev_clear: true, ...extra })
  assert.strictEqual(kit.panelVerdict([]), 'READY')
  assert.strictEqual(kit.panelVerdict([f('a', false)]), 'NEEDS_EDITS')
  assert.strictEqual(kit.panelVerdict([f('a', false), f('b', true)]), 'NOT_READY')
  assert.strictEqual(kit.panelVerdict([{ id: 'x' }]), 'NOT_READY')   // only an explicit blocks:false is non-blocking
  // Jev's answers never change the verdict: a Jev "not a blocker" on a failure the seat calls blocking stays NOT_READY
  const seat = { seat: 'hostile', verdict: 'NOT_READY', failures: [f('a', true, { jev_agree: 'disagree', jev_margin: 3 })] }
  const c = kit.checkPanelSeat(seat)
  assert.deepStrictEqual([c.ok, c.derived, c.jev.jev_agree], [true, 'NOT_READY', 'not_all'])
  assert.strictEqual(kit.checkPanelSeat({ seat: 's', verdict: 'READY', failures: [f('a', false)] }).ok, false)   // must be NEEDS_EDITS
  const two = [{ seat: 'a', verdict: 'READY', failures: [] }, { seat: 'b', verdict: 'NEEDS_EDITS', failures: [f('x', false)] }]
  assert.deepStrictEqual(kit.panelFloor(two), { verdict: 'NEEDS_EDITS', notReady: [], mismatched: [] })
  const liar = [{ seat: 'a', verdict: 'READY', failures: [f('x', true)] }]
  assert.deepStrictEqual(kit.panelFloor(liar), { verdict: 'NOT_READY', notReady: ['a'], mismatched: ['a'] })   // sent back, counted NOT_READY
  assert.strictEqual(kit.panelFloor([]).verdict, 'NOT_READY')   // no seat returned: never READY
  const agg = kit.checkPanelSeat({ seat: 's', verdict: 'NEEDS_EDITS', failures: [f('a', false, { jev_margin: 0.5, jev_clear: false }), f('b', false)] })
  assert.deepStrictEqual([agg.jev.jev_agree, agg.jev.jev_margin, agg.jev.jev_clear], ['agree', 0.5, false])   // the weakest row
})

// ---- D7: no silent stops
test('mustEscalate (D7): null, failed, partial, not-complete, or an empty required list escalates; a complete return does not', () => {
  assert.match(kit.mustEscalate(null), /no return/)
  assert.match(kit.mustEscalate({ status: 'failed', could_not_check: ['INPUTS.md missing'] }), /failed: INPUTS\.md missing/)
  assert.match(kit.mustEscalate({ status: 'partial', could_not_check: [] }), /partial/)
  assert.match(kit.mustEscalate({ claims: [{ claim: 'x' }] }), /not complete/)   // a return without status is not a pass
  assert.match(kit.mustEscalate({ status: 'complete', claims: [] }, { nonEmpty: 'claims' }), /empty claims/)
  assert.strictEqual(kit.mustEscalate({ status: 'complete', findings: [] }), null)   // an empty findings list is a valid answer
  assert.strictEqual(kit.mustEscalate({ status: 'complete', claims: [{ claim: 'x' }] }, { nonEmpty: 'claims' }), null)
})

test('COMMON (D7): a missing input never stops the run silently — finish the rest, status partial/failed, could_not_check', () => {
  const c = kit.common(kit.SLOTS, 'rails')
  assert.doesNotMatch(c, /missing, say so first in notes and stop/)
  assert.match(c, /A missing input never stops the run silently/)
  assert.match(c, /status 'partial' \(some parts done\) or 'failed' \(nothing could be done\)/)
  assert.match(c, /never an empty result that reads as a pass/)
})

test('COMMON (D9, D19, D1, D5): no export, jev <subcommand> --q, CEO-only state files, no value extraction, Jev never decides', () => {
  const c = kit.common({ ...kit.SLOTS, JEV_BUILD: 'typesafe/jev-1.13-20260917' }, 'rails')
  assert.doesNotMatch(c, /export JEV_EXPECT_BUILD/)                       // an export dies with its Bash call (S1-01)
  assert.match(c, /no export needed/)
  assert.match(c, /"build_mismatch": true/)
  assert.match(c, /'jev <filter\|yes\|pick\|rank\|rate> --q <id>'/)      // S2-08: --q is a subcommand flag
  assert.doesNotMatch(c, /'jev --q/)
  assert.match(c, /never write CORP_STATE\.md or corp_state\.json — the CEO is their only writer/)
  assert.match(c, /value extraction \(never select or read a value with Jev/)
  assert.doesNotMatch(c, /select(ing)? a value among spans/)
  assert.match(c, /YOU decide every verdict; Jev only seconds it and routes escalation — it never decides one/)
  assert.match(c, /jev_first to 'disagree' — that item goes to a verifier/)
  assert.match(c, /the holistic pick \(panel_verdict\) is display only: jev_pick, never jev_agree/)
  assert.match(c, /Only a measured question \(claim_support, determination\) can let an item stand/)
  assert.match(c, /Does this defect stop the deliverable from being sent, filed or shipped as it stands\?/)
  assert.match(c, /cp -p X X\.bak-<YYYYMMDD>/)                            // rule #1 for workers too (D8)
})

// ---- cascade + gate (09-28, OpenRouter's Jev cookbooks)
const SPEC_CRITERIA = {
  supported: 'The draft addresses `task`, and every fact, number, date, name, and policy in it is stated in `sources`.',
  unsupported: 'The draft states at least one fact, number, date, name, or policy that `sources` do not contain or that contradicts them, or it addresses something other than `task`.',
  declined: 'The draft says `sources` do not cover `task` and does not assert facts of its own.',
}

test('CASCADE_CRITERIA: the three pinned strings, in order, and the CLI sends the same ones', () => {
  assert.deepStrictEqual(kit.CASCADE_CRITERIA, SPEC_CRITERIA)
  assert.deepStrictEqual(Object.keys(kit.CASCADE_CRITERIA), ['supported', 'unsupported', 'declined'])
  const cli = fs.readFileSync(path.join(__dirname, '..', 'scripts', 'jev'), 'utf8')
  for (const [label, text] of Object.entries(SPEC_CRITERIA)) assert.ok(cli.includes(`"${label}": "${text}"`), `scripts/jev VERIFY_CRITERIA lacks ${label}: ${text}`)
  assert.ok(cli.includes(`VERIFY_TASK_INSTRUCTIONS = "${kit.JEV_REGISTRY.addresses_task.text}"`), 'scripts/jev lacks the addresses_task noul (D16)')
})

test('cascadeRoute: supported at or above accept sends; below, unsupported or no confidence escalates; declined hands off', () => {
  assert.strictEqual(kit.cascadeRoute({ choice: 'supported', confidence: 0.8 }), 'send')          // exactly accept
  assert.strictEqual(kit.cascadeRoute({ choice: 'supported', confidence: 0.79 }), 'escalate')
  assert.strictEqual(kit.cascadeRoute({ choice: 'supported' }), 'escalate')                         // missing confidence = 0
  assert.strictEqual(kit.cascadeRoute({ choice: 'supported', confidence: '0.95' }), 'escalate')     // a string is not a confidence
  assert.strictEqual(kit.cascadeRoute({ choice: 'unsupported', confidence: 1 }), 'escalate')
  assert.strictEqual(kit.cascadeRoute({ choice: 'declined', confidence: 0.2 }), 'handoff')         // at any confidence
  assert.strictEqual(kit.cascadeRoute({ choice: 'unavailable', confidence: 0 }), 'escalate')
  assert.strictEqual(kit.cascadeRoute(null), 'escalate')                                             // no verdict never sends
  assert.strictEqual(kit.cascadeRoute({ choice: 'supported', confidence: 0.75 }, { accept: 0.7 }), 'send')
  assert.throws(() => kit.cascadeRoute({ choice: 'supported', confidence: 1 }, { accept: 80 }), /accept must be a number in \[0, 1\]/)
})

test('cascadeStep: one escalation, enforced — a failing re-draft hands off (a DOUBLE_FAIL for the claim audit), and the first tier is cascadeRoute exactly', () => {
  // first tier (escalated: false) — identical to cascadeRoute
  assert.strictEqual(kit.cascadeStep({ choice: 'supported', confidence: 0.9 }), 'send')
  assert.strictEqual(kit.cascadeStep({ choice: 'unsupported', confidence: 1 }), 'escalate')
  assert.strictEqual(kit.cascadeStep({ choice: 'declined', confidence: 0.9 }), 'handoff')
  // the stronger tier's re-draft (escalated: true) — never a second escalation
  assert.strictEqual(kit.cascadeStep({ choice: 'unsupported', confidence: 1 }, { escalated: true }), 'handoff')
  assert.strictEqual(kit.cascadeStep({ choice: 'supported', confidence: 0.79 }, { escalated: true }), 'handoff')
  assert.strictEqual(kit.cascadeStep({ choice: 'supported' }, { escalated: true }), 'handoff')   // no confidence
  assert.strictEqual(kit.cascadeStep(null, { escalated: true }), 'handoff')                       // no verdict
  assert.strictEqual(kit.cascadeStep({ choice: 'supported', confidence: 0.8 }, { escalated: true }), 'send')
  assert.strictEqual(kit.cascadeStep({ choice: 'supported', confidence: 0.75 }, { accept: 0.7, escalated: true }), 'send')
  // a two-tier loop driven only by cascadeStep terminates: tier 2 never returns 'escalate'
  for (const choice of ['supported', 'unsupported', 'declined', 'unavailable', undefined])
    for (const confidence of [0, 0.5, 0.79, 0.8, 1, undefined])
      assert.notStrictEqual(kit.cascadeStep({ choice, confidence }, { escalated: true }), 'escalate', `${choice}@${confidence}`)
  assert.match(src, /DOUBLE_FAIL; D15\), never the owner queue/)   // D15: where a double failure goes
})

test('gateDecision: approve / block / review at the threshold edges', () => {
  assert.strictEqual(kit.gateDecision({ a: 0.9, b: 0.95 }), 'approve')      // exactly approveAt
  assert.strictEqual(kit.gateDecision({ a: 0.89, b: 0.95 }), 'review')
  assert.strictEqual(kit.gateDecision({ a: 0.1, b: 0.99 }), 'block')        // exactly blockAt
  assert.strictEqual(kit.gateDecision({ a: 0.11, b: 0.99 }), 'review')
  assert.strictEqual(kit.gateDecision({ a: 0.05, b: 0.5 }), 'block')        // block beats an unclear check
  assert.strictEqual(kit.gateDecision({ a: 0.85, b: 0.82 }, { approveAt: 0.8, blockAt: 0.2 }), 'approve')
  assert.strictEqual(kit.gateDecision({ a: 0.2, b: 0.99 }, { approveAt: 0.8, blockAt: 0.2 }), 'block')
})

test('gateDecision: a broken check or no checks throws — never approve or review on it', () => {
  assert.throws(() => kit.gateDecision({}), /no checks/)
  assert.throws(() => kit.gateDecision(null), /no checks/)
  assert.throws(() => kit.gateDecision({ a: 0.99, b: undefined }), /no valid p for b/)
  assert.throws(() => kit.gateDecision({ a: 0.99, b: 1.5 }), /no valid p for b/)
  assert.throws(() => kit.gateDecision({ a: 0.99, b: '0.99' }), /no valid p for b/)
  assert.throws(() => kit.gateDecision({ a: 0.5 }, { approveAt: 0.5, blockAt: 0.5 }), /blockAt \(0.5\) must be below approveAt/)
})

test('CASCADE_ITEM and GATE_DECISION: required fields and enums', () => {
  assert.deepStrictEqual(kit.CASCADE_ITEM.required, ['id', 'choice', 'confidence', 'route'])
  assert.deepStrictEqual(kit.CASCADE_ITEM.properties.route.enum, ['send', 'escalate', 'handoff', 'audit'])   // F5
  assert.deepStrictEqual(kit.CASCADE_ITEM.properties.lang_hint.enum, ['non_en'])
  assert.deepStrictEqual(kit.CASCADE_ITEM.properties.choice.enum, ['supported', 'unsupported', 'declined', 'unavailable'])
  assert.deepStrictEqual(kit.CASCADE_ITEM.properties.failed_half.enum, ['grounding', 'task'])
  for (const k of ['escalated_to', 'final_choice', 'failed_half']) assert.ok(k in kit.CASCADE_ITEM.properties && !kit.CASCADE_ITEM.required.includes(k), k)
  assert.deepStrictEqual(kit.GATE_DECISION.required, ['action', 'decision', 'checks', 'deterministic_blocks'])
  assert.deepStrictEqual(kit.GATE_DECISION.properties.decision.enum, ['approve', 'block', 'review'])
  assert.deepStrictEqual(kit.GATE_DECISION.properties.mode.enum, ['all', 'veto'])
  assert.strictEqual(kit.GATE_DECISION.properties.deterministic_blocks.type, 'array')
})

test('COMMON: names jev verify / jev gate --q go_act and says to act on the field, not the exit code', () => {
  const c = kit.common(kit.SLOTS, 'rails')
  assert.match(c, /'jev verify -f draft\.json' \(route send \| escalate \| handoff; failed_half names grounding or task/)
  assert.match(c, /'jev gate --q go_act --veto -f action\.json' naming "receipts": \{"share_check", "census"\}/)
  assert.match(c, /the CLI recomputes every deterministic check itself/)
  assert.match(c, /a hand-written "deterministic_blocks": \[\] asserts nothing/)
  assert.match(c, /verify escalates and gate reviews a unit not in English without asking Jev \(OM-08\)/)
  assert.match(c, /ride inside sources as a labelled 'Computation receipt' entry — run it from the work folder or pass --calc-root/)
  assert.doesNotMatch(c, /computed_from/)
  assert.match(c, /never on exit 0 alone/)
})

// ---- D2: what the owner's GO adopts, checked in code before any Jev call
test('parseGo: a plain GO names row numbers; the owner\'s own words return null (Jev authorized judges them)', () => {
  assert.deepStrictEqual(kit.parseGo('GO 1,3,4'), ['1', '3', '4'])
  assert.deepStrictEqual(kit.parseGo('  go 2 , 5. '), ['2', '5'])
  assert.deepStrictEqual(kit.parseGo('GO 7'), ['7'])
  assert.strictEqual(kit.parseGo('yes, deploy the appeal'), null)
  assert.strictEqual(kit.parseGo('GO'), null)
  assert.strictEqual(kit.parseGo(null), null)
})

const H1 = 'a'.repeat(32), H2 = 'b'.repeat(32), H0 = 'c'.repeat(32)   // md5s
test('goActBlocks: the act must be the adopted row, field for field, every file at its md5 (FB-04)', () => {
  const row = { id: 3, verb: 'deploy', target: '/Volumes/S/SEND TO', recipient: 'n/a', record_id: 'n/a', files: { '/w/v2/a.pdf': H1, '/w/v2/b.pdf': H2 } }
  const act = { verb: 'deploy', target: '/Volumes/S/SEND TO', recipient: 'n/a', record_id: 'n/a', src: '/w/v2', files: ['/w/v2/a.pdf', '/w/v2/b.pdf'] }
  const md5s = { '/w/v2/a.pdf': H1, '/w/v2/b.pdf': H2 }
  const srcFiles = ['/w/v2/a.pdf', '/w/v2/b.pdf']
  assert.deepStrictEqual(kit.goActBlocks({ reply: 'GO 1,3', row }, act, { md5s, srcFiles }), [])           // two files, both named
  const blocks = kit.goActBlocks({ reply: 'GO 1,4', row }, { ...act, target: '/Volumes/S/Other', files: ['/w/v1/a.pdf'] }, { md5s: { '/w/v1/a.pdf': H0 }, srcFiles })
  assert.ok(blocks.some(b => /does not name row 3/.test(b)), blocks)
  assert.ok(blocks.some(b => /act\.target/.test(b)), blocks)
  assert.ok(blocks.some(b => /the row's file \/w\/v2\/a\.pdf is not among act\.files/.test(b)), blocks)
  assert.ok(blocks.some(b => /\/w\/v1\/a\.pdf is not among the row's files/.test(b)), blocks)
  assert.ok(kit.goActBlocks({ reply: 'GO 3', row }, act, { md5s: { '/w/v2/a.pdf': H1 }, srcFiles }).some(b => /not computed/.test(b)))   // an uncomputed md5 never passes
  assert.ok(kit.goActBlocks({ reply: 'GO 3', row: { ...row, files: { '/w/v2/a.pdf': '', '/w/v2/b.pdf': H2 } } }, act, { md5s, srcFiles }).some(b => /names no md5/.test(b)))
  assert.ok(kit.goActBlocks({ reply: 'GO 3', row: { ...row, files: undefined } }, act, { md5s, srcFiles }).some(b => /names no file and md5/.test(b)))
  assert.match(kit.goActBlocks({ reply: 'GO 3' }, act)[0], /no adopted row/)                              // OM-07: no row, no act
  // the older single artifact + md5 still reads
  assert.deepStrictEqual(kit.rowFiles({ artifact: '/w/a.docx', md5: H1 }), { '/w/a.docx': H1 })
  // the OWNER_QUEUE column form and a list of objects read the same as the map (as `jev gate` reads them)
  assert.deepStrictEqual(kit.rowFiles({ files: ['/w/a.pdf · `' + H1 + '`', '/w/b.pdf · ' + H2] }), { '/w/a.pdf': H1, '/w/b.pdf': H2 })
  assert.deepStrictEqual(kit.rowFiles({ files: [{ path: '/w/a.pdf', md5: H1 }] }), { '/w/a.pdf': H1 })
})

test('goActBlocks (E5): an unparseable GO authorizes nothing; words adopt a row only by naming its act', () => {
  const row = { id: 3, verb: 'deploy', target: '/Volumes/S/Appeal 10.2026', recipient: 'n/a', record_id: 'n/a', files: { '/w/a.pdf': H1 } }
  const act = { verb: 'deploy', target: '/Volumes/S/Appeal 10.2026', recipient: 'n/a', record_id: 'n/a', src: '/w', files: ['/w/a.pdf'] }
  const md5s = { '/w/a.pdf': H1 }, srcFiles = ['/w/a.pdf']
  assert.ok(kit.goActBlocks({ reply: 'yeah go ahead and put it on the server', row }, act, { md5s, srcFiles }).some(b => /GO which rows\?/.test(b)))
  assert.deepStrictEqual(kit.goActBlocks({ reply: 'deploy it to /Volumes/S/Appeal 10.2026, yes', row }, act, { md5s, srcFiles }), [])
  assert.strictEqual(kit.replyNamesAct('Deploy  it to /Volumes/S/Appeal 10.2026', row), true)            // case and spacing folded
  assert.strictEqual(kit.replyNamesAct('deploy it', row), false)                                           // no target named
})

test('goActBlocks (E6): a send is HUMAN-ONLY — a send verb, or a browse / portal write addressed to a recipient', () => {
  const row = { id: 2, verb: 'upload', target: 'https://portal.example', recipient: 'n/a', record_id: 'PA 1234' }
  assert.ok(kit.goActBlocks({ reply: 'GO 2', row }, { ...row }).some(b => /HUMAN-ONLY/.test(b)))
  const portal = { id: 2, verb: 'browse write', target: 'https://portal.example/appeals', recipient: 'Acme Review Org', record_id: 'PA 1234' }
  assert.ok(kit.goActBlocks({ reply: 'GO 2', row: portal }, { ...portal }).some(b => /send to a third party/.test(b)))
  const op = { id: 4, verb: 'portal write', target: 'https://portal.example/client/7', recipient: 'n/a', record_id: 'session 09/12' }
  assert.deepStrictEqual(kit.goActBlocks({ reply: 'GO 4', row: op }, { ...op }), [])                     // an internal write stays GO-able
})

// ---- wave 2 (09-28): the registry, pick clarity and the build check
const registryFile = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'jev-registry.json'), 'utf8'))

test('JEV_REGISTRY is corp/jev-registry.json, verbatim (type, text, criteria/options/checks, state_format, thresholds, measured)', () => {
  const want = {}
  for (const q of registryFile.questions) {
    const p = { type: q.type, text: q.text }
    for (const k of ['criteria', 'options', 'dynamic_options', 'checks']) if (k in q) p[k] = q[k]
    p.state_format = q.state_format === undefined ? null : q.state_format
    p.thresholds = q.thresholds || {}
    if ('mode' in q) p.mode = q.mode
    p.measured = q.measured
    want[q.id] = p
  }
  assert.deepStrictEqual(kit.JEV_REGISTRY, want)
  assert.strictEqual(kit.JEV_REGISTRY.keep_reject.criteria.true, kit.JEV_DEFECT_TRUE)
  assert.strictEqual(kit.JEV_REGISTRY.keep_reject.criteria.false, kit.JEV_DEFECT_FALSE)
  assert.deepStrictEqual(kit.JEV_REGISTRY.verify_cascade.options, kit.CASCADE_CRITERIA)
  assert.strictEqual(kit.JEV_REGISTRY.claim_support.thresholds.clear_bar, kit.JEV_CLEAR)
  assert.deepStrictEqual(Object.keys(kit.JEV_REGISTRY).filter(k => kit.JEV_REGISTRY[k].measured), ['claim_support', 'determination'])
  assert.strictEqual(kit.JEV_REGISTRY.go_act.mode, 'veto')   // decision G: adopted-row acts run in veto mode
})

// ---- decision G: veto mode for an act the owner adopted field for field
test('gateDecision veto mode: only a check at or below blockAt blocks; no approve bar; broken input still throws', () => {
  assert.strictEqual(kit.gateDecision({ a: 0.7, b: 0.6 }, { mode: 'veto' }), 'approve')
  assert.strictEqual(kit.gateDecision({ a: 0.7, b: 0.6 }), 'review')                   // the default keeps the 0.9-all bar
  assert.strictEqual(kit.gateDecision({ a: 0.11, b: 0.99 }, { mode: 'veto' }), 'approve')
  assert.strictEqual(kit.gateDecision({ a: 0.1, b: 0.99 }, { mode: 'veto' }), 'block')   // exactly blockAt
  assert.strictEqual(kit.gateDecision({ a: 0.25, b: 0.99 }, { mode: 'veto', blockAt: 0.3 }), 'block')
  assert.throws(() => kit.gateDecision({}, { mode: 'veto' }), /no checks/)
  assert.throws(() => kit.gateDecision({ a: 0.9, b: undefined }, { mode: 'veto' }), /no valid p for b/)
  assert.throws(() => kit.gateDecision({ a: 0.9 }, { mode: 'lenient' }), /mode must be 'all' or 'veto'/)
})

test('goActionJson (E12): the action.json names the receipts; the row checks ride as planning, never as deterministic_blocks', () => {
  const row = { id: 3, verb: 'deploy', target: '/Volumes/S/SEND TO', recipient: 'n/a', record_id: 'n/a', files: { '/w/v2/a.docx': H1 } }
  const act = { verb: 'deploy', target: '/Volumes/S/SEND TO', recipient: 'n/a', record_id: 'n/a', src: '/w/v2', files: ['/w/v2/a.docx'] }
  const deliverable = { name: 'appeal', description: 'the appeal letter' }
  const srcFiles = ['/w/v2/a.docx']
  const ok = kit.goActionJson({ reply: 'GO 3', row }, act, deliverable, { md5s: { '/w/v2/a.docx': H1 }, srcFiles, receipts: { share_check: 'sc.txt', census: 'census.jsonl' } })
  assert.deepStrictEqual(ok.planning, [])
  assert.ok(!('deterministic_blocks' in ok), 'a caller-written list is never the receipt (E12)')
  assert.deepStrictEqual(ok.receipts, { share_check: 'sc.txt', census: 'census.jsonl' })
  assert.deepStrictEqual(ok.checks, ['authorized', 'right_artifact'])          // the row names no recipient: no recipient_matches
  assert.deepStrictEqual(ok.state, { go: { reply: 'GO 3', row }, act, deliverable })
  assert.strictEqual(ok.action, 'deploy /Volumes/S/SEND TO')
  // RG-09: recipient_matches is asked for an act whose row names a recipient (a handover to a named human), not a `send` flag
  const handRow = { ...row, verb: 'handover', recipient: 'Alex Reviewer, Reviewer' }
  const hand = kit.goActionJson({ reply: 'GO 3', row: handRow }, { ...act, verb: 'handover', recipient: 'Alex Reviewer, Reviewer' }, deliverable, { md5s: { '/w/v2/a.docx': H1 }, srcFiles })
  assert.deepStrictEqual(hand.checks, ['authorized', 'right_artifact', 'recipient_matches'])
  assert.deepStrictEqual(hand.receipts, { share_check: null, census: null })   // missing receipts: the CLI blocks on them …
  assert.ok(hand.planning.some(b => /receipts\.share_check is not named/.test(b)) && hand.planning.some(b => /receipts\.census is not named/.test(b)), hand.planning)   // … and planning says so (F2)
  const bad = kit.goActionJson({ reply: 'GO 3', row }, act, deliverable, { md5s: { '/w/v2/a.docx': H0 }, srcFiles })
  assert.ok(bad.planning.some(b => /md5 of \/w\/v2\/a\.docx/.test(b)), bad.planning)
})

// ---- INTEGRATION 2 (CEO decisions E1, E2, E8, E10, E12, E13, FB-08, FA-08, OM-11, OM-12)
test('ladder (E13, FB-03): a re-read item never stands, even when the seat left jev_first out', () => {
  const reasked = { id: 'r2', severity: 'low', jev_agree: 'agree', jev_margin: 4, jev_q: 'claim_support', jev_clear: true }
  const L = kit.ladder([{ ...reasked, jev_reread: 'upheld_seat' }])          // re-asked after a disagreement, no jev_first
  assert.deepStrictEqual([L.stands.length, L.escalate.length, L.bad.length], [0, 1, 0])
  assert.strictEqual(kit.ladder([{ ...reasked, jev_reread: 'upheld_jev' }]).stands.length, 0)
  assert.strictEqual(kit.ladder([{ ...reasked }]).stands.length, 0)             // no jev_reread at all: never stands (fail closed)
  assert.strictEqual(kit.ladder([{ ...reasked, jev_reread: 'none' }]).stands.length, 1)
})

test('ladder (E13, OM-04): an unavailable item escalates to the verifier and never fails the unit', () => {
  const L = kit.ladder([{ id: 'u', jev_q: 'claim_support', jev_agree: 'unavailable', jev_margin: 0, jev_reread: 'none', jev_clear: false }],
    { severityOf: () => 'low' })
  assert.deepStrictEqual([L.stands.length, L.escalate.length, L.bad.length], [0, 1, 0])
  const D = kit.ladder([{ id: 'd', jev_q: 'claim_support', jev_agree: 'disagree', jev_margin: 2, jev_reread: 'none', jev_clear: true }],
    { severityOf: () => 'low' })
  assert.deepStrictEqual([D.escalate.length, D.bad.length], [0, 1])          // a disagreement is still owed a re-read
})

test('claimSeverity (E10, FA-16, FA-08, E2): role figures, determination verbs, OCR, non-letter authority and page-1 claims are high', () => {
  const high = ['The plan authorized 1,200 units of 10003.', 'Acme Review Org reversed the reduction at reconsideration.',
    'The request for 40 hours per week was reduced to 20.', 'Services were denied for the period 3/04/26 to 9/02/26.',
    'The member used 1,384 units.', 'The determination was upheld.', 'The request was partially approved.']
  for (const claim of high) assert.strictEqual(kit.claimSeverity({ claim }), 'high', claim)
  assert.strictEqual(kit.claimSeverity({ claim: 'The Reviewer observed the session.' }), 'low')
  assert.strictEqual(kit.claimSeverity({ claim: 'The Reviewer observed the session.', ocr: true }), 'high')          // FA-08
  assert.strictEqual(kit.claimSeverity({ claim: 'The Reviewer observed the session.', central: true }), 'high')
  const L = kit.ladder([{ id: 'c', claim: 'The plan authorized 1,200 units.', jev_agree: 'agree', jev_margin: 3, ...M }],
    { severityOf: kit.claimSeverity })
  assert.deepStrictEqual([L.stands.length, L.escalate.length], [0, 1])          // agree + clear on a role figure: still the verifier
  const floor = kit.ladder([{ id: 'c', claim: 'Acme Review Org reversed the reduction.', jev_agree: 'agree', jev_margin: 3, ...M },
    { id: 'd', claim: 'The Reviewer observed the session.', jev_agree: 'agree', jev_margin: 3, ...M }], { severityOf: () => 'low' })
  assert.deepStrictEqual([floor.stands.map(x => x.id), floor.escalate.map(x => x.id)], [['d'], ['c']])   // a hard floor: 'low' cannot lower it
  const sketch = src.split('// ---- Usage sketch')[1]
  assert.match(sketch, /ladder\(a\.claims, \{ severityOf: claimSeverity, q: 'claim_support' \}\)/)
  assert.deepStrictEqual(kit.CLAIM_AUDIT.properties.claims.items.properties.source_class.enum, ['LETTER', 'CLAIMS', 'TRACKER', 'DRAFT', 'OTHER'])
  assert.strictEqual(kit.CLAIM_AUDIT.properties.claims.items.properties.ocr.type, 'boolean')
})

test("ledgerParagraph (FB-08): the CLI's unfilled 'upheld seat ? / jev ?' never gates a round", () => {
  assert.throws(() => kit.ledgerParagraph({ ...LEDGER_FULL, jev: 'jev: calls 3 · disagreements c2 → upheld seat ? / jev ? · unavailable 0' }), /placeholder/)
  assert.doesNotThrow(() => kit.ledgerParagraph({ ...LEDGER_FULL, jev: 'jev: calls 3 · disagreements c2 → upheld seat 1 / jev 0 · unavailable 0' }))
})

test('COMMON (E1, E2, E8, FA-08, FB-09, OM-11, OM-12): receipts are chains, source class, OCR, build check, no share, no scratchpad', () => {
  const c = kit.common(kit.SLOTS, 'rails')
  assert.match(c, /'<role>: <figure> \[src: <doc> p\.N "<quote>"\]'/)
  assert.match(c, /scripts\/quote-gate --docs map\.json --receipts <receipts> --payer' must pass every input/)
  assert.match(c, /--payer: an authorized or denied input cites a LETTER, and it turns itself on when map\.json carries classes \(F12\)/)
  assert.match(c, /'quote-gate --drafts <drafts>' checks every drafted '<figure> \[calc: r\]' against r's '## result', RG-08/)
  assert.match(c, /INFERRED, never VERIFIED, and never a page-1 fact, F11/)
  assert.match(c, /an authorized figure is VERIFIED only against a LETTER, E2/)
  assert.match(c, /ocr: true when that source's text came from OCR \(FA-08\)/)
  assert.match(c, /every statement of what a payer decided carries its own \[src:\] quoting the letter's verb \(E8\)/)
  assert.match(c, /"build_check": "unavailable"/)
  assert.match(c, /never write into a shared folder or anything under \/Volumes/)
  assert.match(c, /never a session scratchpad/)
})

// ---- INTEGRATION 3 (CEO decisions F1, F5, F9, F11, RG-09)
test('cascadeStep (F5): a unit not in English goes to the claim audit on either tier — never a redraft, never a DOUBLE_FAIL', () => {
  // re-gate FABLE-B RG-01: the CLI's non-English row came back route 'escalate' and a Workflow spent an opus redraft on it
  const nonEn = { choice: null, confidence: null, route: 'escalate', lang_hint: 'non_en' }
  assert.strictEqual(kit.cascadeRoute(nonEn), 'audit')
  assert.strictEqual(kit.cascadeStep(nonEn, {}), 'audit')
  assert.strictEqual(kit.cascadeStep(nonEn, { escalated: true }), 'audit')
  assert.strictEqual(kit.cascadeStep({ ...nonEn, choice: 'supported', confidence: 0.99 }), 'audit')   // the hint wins over any label
  assert.strictEqual(kit.cascadeStep({ choice: 'supported', confidence: 0.9, lang_hint: 'en' }), 'send')
})

test('claimSeverity (F9, re-gate OPUS RG-04): role words floor document, document-set and payer work; software claims are not floored by them', () => {
  const software = ['The PR modified 3 files in src/auth', 'Unit tests pass on main (412/412)', 'The request handler returns 404 for a missing id',
    'Latency was reduced from 120 ms to 80 ms', 'The build takes about 2 hours on CI']
  for (const claim of software) {
    for (const cls of ['software-release', 'software-build', 'software-audit', 'data-product']) assert.strictEqual(kit.claimSeverity({ claim }, cls), 'low', `${cls}: ${claim}`)
    for (const cls of ['document', 'document-set', '<unfilled>', 'something-new']) assert.strictEqual(kit.claimSeverity({ claim }, cls), 'high', `${cls}: ${claim}`)
  }
  // the class-free floors hold in every class: OCR, page-1/central, a non-LETTER authorized source
  assert.strictEqual(kit.claimSeverity({ claim: 'The build takes 2 hours.', ocr: true }, 'software-build'), 'high')
  assert.strictEqual(kit.claimSeverity({ claim: 'The build takes 2 hours.', central: true }, 'software-build'), 'high')
  assert.strictEqual(kit.claimSeverity({ claim: 'The plan authorized 1,200 units.', source_class: 'TRACKER' }, 'data-product'), 'high')
  // the default reads SLOTS.CLASS; an unfilled slot fails closed
  const was = kit.SLOTS.CLASS
  try {
    kit.SLOTS.CLASS = 'software-build'
    assert.strictEqual(kit.claimSeverity({ claim: software[0] }), 'low')
    const L = kit.ladder([{ id: 's', claim: software[0], jev_agree: 'agree', jev_margin: 3, ...M }], { severityOf: kit.claimSeverity })
    assert.deepStrictEqual([L.stands.length, L.escalate.length], [1, 0])        // a software claim can stand on a measured agree + clear
    kit.SLOTS.CLASS = 'document'
    const D = kit.ladder([{ id: 'd', claim: software[0], jev_agree: 'agree', jev_margin: 3, ...M }], { severityOf: kit.claimSeverity })
    assert.deepStrictEqual([D.stands.length, D.escalate.length], [0, 1])
  } finally { kit.SLOTS.CLASS = was }
})

test('INFERRED (F11, re-gate OPUS RG-06): a claim-audit status, always high, never stands', () => {
  assert.ok(kit.CLAIM_AUDIT.properties.claims.items.properties.status.enum.includes('INFERRED'))
  const inferred = { id: 'i', claim: 'The practice tracker shows 2,000 authorized hours (the letter is not in our file).', status: 'INFERRED', jev_agree: 'agree', jev_margin: 3, ...M }
  for (const cls of ['document', 'software-build', 'data-product']) assert.strictEqual(kit.claimSeverity({ ...inferred, claim: 'x' }, cls), 'high', cls)
  const L = kit.ladder([inferred], { severityOf: kit.claimSeverity })
  assert.deepStrictEqual([L.stands.length, L.escalate.length], [0, 1])
})

test('goActBlocks (RG-12): the row verb is one bare E0 verb', () => {
  const base = { id: 5, target: 'https://portal.example/client/7', recipient: 'n/a', record_id: 'n/a' }
  for (const verb of ['handover (a draft for signature)', 'copy', 'deploy it'])
    assert.ok(kit.goActBlocks({ reply: 'GO 5', row: { ...base, verb } }, { ...base, verb }).some(b => /is not an E0 verb/.test(b)), verb)
  assert.deepStrictEqual(kit.goActBlocks({ reply: 'GO 5', row: { ...base, verb: 'Portal  Write' } }, { ...base, verb: 'Portal  Write' }), [])
})

test('goActBlocks (F1, re-gate OPUS RG-01): the folder the executor copies holds only the row\'s files', () => {
  const row = { id: 3, verb: 'deploy', target: '/Volumes/S/Appeal 10.2026', recipient: 'n/a', record_id: 'n/a', files: { '/w/SEND TO/03 Enclosure v2.pdf': H1 } }
  const act = { verb: 'deploy', target: '/Volumes/S/Appeal 10.2026', recipient: 'n/a', record_id: 'n/a', src: '/w/SEND TO', files: ['/w/SEND TO/03 Enclosure v2.pdf'] }
  const md5s = { '/w/SEND TO/03 Enclosure v2.pdf': H1 }
  assert.deepStrictEqual(kit.goActBlocks({ reply: 'GO 3', row }, act, { md5s, srcFiles: ['/w/SEND TO/03 Enclosure v2.pdf', '/w/SEND TO/.DS_Store'] }), [])
  const stale = kit.goActBlocks({ reply: 'GO 3', row }, act, { md5s, srcFiles: ['/w/SEND TO/03 Enclosure v1.pdf', '/w/SEND TO/03 Enclosure v2.pdf'] })
  assert.ok(stale.some(b => /act\.src holds \/w\/SEND TO\/03 Enclosure v1\.pdf, which the row does not name/.test(b)), stale)
  assert.ok(kit.goActBlocks({ reply: 'GO 3', row }, { ...act, src: undefined }, { md5s, srcFiles: [] }).some(b => /act\.src is missing/.test(b)))
  assert.ok(kit.goActBlocks({ reply: 'GO 3', row }, { ...act, src: '/w/other' }, { md5s, srcFiles: [] }).some(b => /is not under act\.src/.test(b)))
  assert.ok(kit.goActBlocks({ reply: 'GO 3', row }, act, { md5s }).some(b => /srcFiles not given/.test(b)))   // planning never assumes the folder is clean
  const op = { id: 4, verb: 'portal write', target: 'https://portal.example/client/7', recipient: 'n/a', record_id: 'n/a', files: { '/w/a.pdf': H1 } }
  assert.deepStrictEqual(kit.goActBlocks({ reply: 'GO 4', row: op }, { ...op, files: ['/w/a.pdf'] }, { md5s: { '/w/a.pdf': H1 } }), [])   // a URL target copies no folder
})

test('goActBlocks + goActionJson (closure check CC-01): a deploy or handover that names no files never passes; act.src is listed and the census required whenever files or act.src is set', () => {
  const stale = ['/w/SEND TO/03 Enclosure v1.pdf', '/w/SEND TO/03 Enclosure v2.pdf']
  const T = '/Volumes/S/Appeal 10.2026'
  for (const verb of ['deploy', 'handover']) {
    // the three cli_cc01 shapes: row Files a string, row Files {}, no files key at all
    for (const [label, rowFiles, actFiles] of [['string', 'the SEND TO folder', []], ['empty map', {}, []], ['no key', undefined, undefined]]) {
      const row = { id: 4, verb, target: T, recipient: 'n/a', record_id: 'n/a', files: rowFiles }
      const act = { verb, target: T, recipient: 'n/a', record_id: 'n/a', src: '/w/SEND TO', files: actFiles }
      const b = kit.goActBlocks({ reply: 'GO 4', row }, act, { srcFiles: stale })
      assert.ok(b.some(x => /names every file it writes/.test(x)), `${verb}/${label}: ${b}`)
      assert.ok(b.some(x => /act\.src holds \/w\/SEND TO\/03 Enclosure v1\.pdf, which the row does not name/.test(x)), `${verb}/${label}: ${b}`)
      assert.ok(b.some(x => /act\.src holds \/w\/SEND TO\/03 Enclosure v2\.pdf, which the row does not name/.test(x)), `${verb}/${label}: ${b}`)
      assert.ok(b.some(x => /srcFiles not given/.test(x)) === false)
      assert.ok(kit.goActBlocks({ reply: 'GO 4', row }, act).some(x => /srcFiles not given/.test(x)), 'planning never assumes the folder is clean')
      const j = kit.goActionJson({ reply: 'GO 4', row }, act, { name: 'appeal' }, { srcFiles: stale, receipts: { share_check: 'sc.txt' } })
      assert.ok(j.planning.some(x => /receipts\.census is not named/.test(x)), `${verb}/${label}: census required when act.src is set: ${j.planning}`)
    }
  }
  // no files and no act.src at all: still blocked (a deploy or handover names every file it writes)
  const bare = { id: 4, verb: 'handover', target: T, recipient: 'n/a', record_id: 'n/a' }
  assert.ok(kit.goActBlocks({ reply: 'GO 4', row: bare }, { ...bare }).some(x => /names every file it writes/.test(x)))
  // files named and clean still pass, with both receipts
  const row = { id: 3, verb: 'deploy', target: T, recipient: 'n/a', record_id: 'n/a', files: { '/w/SEND TO/03 Enclosure v2.pdf': H1 } }
  const act = { verb: 'deploy', target: T, recipient: 'n/a', record_id: 'n/a', src: '/w/SEND TO', files: ['/w/SEND TO/03 Enclosure v2.pdf'] }
  const ok = kit.goActionJson({ reply: 'GO 3', row }, act, { name: 'appeal' }, { md5s: { '/w/SEND TO/03 Enclosure v2.pdf': H1 }, srcFiles: ['/w/SEND TO/03 Enclosure v2.pdf'], receipts: { share_check: 'sc.txt', census: 'c.jsonl' } })
  assert.deepStrictEqual(ok.planning, [])
})

test('goActBlocks + goActionJson (closure check P2-a): a config verb aimed at a path or share is checked exactly like a deploy', () => {
  const stale = ['/w/SEND TO/03 Enclosure v1.pdf', '/w/SEND TO/03 Enclosure v2.pdf']
  const f = '/w/SEND TO/03 Enclosure v2.pdf'
  for (const target of ['/Volumes/TeamShare/ORG/X/Appeal 10.2026', 'smb://server/TeamShare/X/A', 'TeamShare/ORG/X/A']) {
    const row = { id: 3, verb: 'config change', target, recipient: 'n/a', record_id: 'n/a', files: { [f]: H1 } }
    const act = { verb: 'config change', target, recipient: 'n/a', record_id: 'n/a', src: '/w/SEND TO', files: [f] }
    const b = kit.goActBlocks({ reply: 'GO 3', row }, act, { md5s: { [f]: H1 }, srcFiles: stale })
    assert.ok(b.some(x => /act\.src holds \/w\/SEND TO\/03 Enclosure v1\.pdf, which the row does not name/.test(x)), `${target}: ${b}`)
    const j = kit.goActionJson({ reply: 'GO 3', row }, act, { name: 'x' }, { md5s: { [f]: H1 }, srcFiles: [f] })
    assert.ok(j.planning.some(x => /receipts\.share_check is not named/.test(x)), `${target}: ${j.planning}`)
    assert.ok(j.planning.some(x => /receipts\.census is not named/.test(x)), `${target}: ${j.planning}`)
    const clean = kit.goActionJson({ reply: 'GO 3', row }, act, { name: 'x' }, { md5s: { [f]: H1 }, srcFiles: [f], receipts: { share_check: 's', census: 'c' } })
    assert.deepStrictEqual(clean.planning, [], target)        // checked like a deploy: passes when it would pass as one
    const none = { ...row }; delete none.files
    assert.ok(kit.goActBlocks({ reply: 'GO 3', row: none }, { ...act, files: [] }, { srcFiles: [] }).some(x => /names every file it writes/.test(x)), target)
  }
  // a config verb whose target is a URL (or empty) stays exempt: no folder rails, no receipts
  for (const target of ['https://console.example/settings', '']) {
    const row = { id: 3, verb: 'config change', target, recipient: 'n/a', record_id: 'n/a', files: { [f]: H1 } }
    const act = { verb: 'config change', target, recipient: 'n/a', record_id: 'n/a', files: [f] }
    assert.deepStrictEqual(kit.goActBlocks({ reply: 'GO 3', row }, act, { md5s: { [f]: H1 } }), [], JSON.stringify(target))
    assert.deepStrictEqual(kit.goActionJson({ reply: 'GO 3', row }, act, { name: 'x' }, { md5s: { [f]: H1 } }).planning, [], JSON.stringify(target))
  }
})

// ---- OM-03: kit-run runs these same functions from Bash, for seats spawned through the Agent tool (corp-* types, E11)
test('kit-run: the same kit, one function over JSON on stdin; a kit throw exits 2', () => {
  const { spawnSync } = require('node:child_process')
  const run = (args, input) => spawnSync('node', [path.join(__dirname, '..', 'scripts', 'kit-run'), ...args], { input: JSON.stringify(input), encoding: 'utf8' })
  let r = run(['ladder', '--ladder', 'on'], { args: [[{ id: 'c1', claim: 'The plan authorized 1,200 units.', jev_agree: 'agree', jev_margin: 3, ...M },
    { id: 'c2', claim: 'The Reviewer observed the session.', jev_agree: 'agree', jev_margin: 3, ...M }], { severityOf: 'claimSeverity', q: 'claim_support' }] })
  assert.strictEqual(r.status, 0, r.stderr)
  const L = JSON.parse(r.stdout)
  assert.deepStrictEqual([L.stands.map(x => x.id), L.escalate.map(x => x.id)], [['c2'], ['c1']])   // E10 through kit-run
  r = run(['mustEscalate'], { args: [{ status: 'partial', could_not_check: ['INPUTS.md'] }] })
  assert.match(JSON.parse(r.stdout), /partial: INPUTS\.md/)
  r = run(['panelFloor'], { args: [[{ seat: 'a', verdict: 'READY', failures: [{ id: 'x', blocks: true }] }]] })
  assert.deepStrictEqual(JSON.parse(r.stdout).verdict, 'NOT_READY')
  r = run(['ladder'], { args: [[{ id: 'z', severity: 'low', jev_agree: 'agree', jev_margin: 3, ...M }]] })   // no --ladder: the kit refuses
  assert.strictEqual(r.status, 2)
  assert.match(r.stderr, /JEV_LADDER is unfilled/)
  assert.strictEqual(run(['eval'], { args: [] }).status, 2)                                    // only the kit's functions
})

test('kit-run (F8, re-gate OPUS OM-03): COMMON and a schema for an Agent-tool brief; --class sets the F9 floor', () => {
  const { spawnSync } = require('node:child_process')
  const os = require('node:os')
  const KR = path.join(__dirname, '..', 'scripts', 'kit-run')
  const run = (args, input) => spawnSync('node', [KR, ...args], { input: input === undefined ? '' : JSON.stringify(input), encoding: 'utf8' })
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'kitrun-'))
  const slots = { WORK: '/Users/x/work/case-1', CLASS: 'document', ROUND: 'r2', DEADLINE: 'none', MODEL_BUILD: 'opus', EFFORT_BUILD: 'xhigh',
    JEV_LADDER: 'on', JEV_BUILD: 'typesafe/jev-1.13-20260917' }
  const write = (name, obj) => { const f = path.join(dir, name); fs.writeFileSync(f, JSON.stringify(obj)); return f }
  // the re-gate's receipt was `kit-run common` exiting 2 with unknown function "common"
  let r = run(['common', write('slots.json', slots)])
  assert.strictEqual(r.status, 0, r.stderr)
  assert.ok(r.stdout.startsWith('CONTEXT: corp round r2, class document, work folder /Users/x/work/case-1'), r.stdout.slice(0, 120))
  for (const must of ['EVIDENCE LAW:', 'PERIMETER:', 'JEV (corp references/jev.md', 'UNATTENDED:', 'HARD RAILS: Builders on opus at `xhigh`'])
    assert.ok(r.stdout.includes(must), must)                                           // the class rails: references/document.md's paste block
  const fullDoc = kit.common({ ...kit.SLOTS, ...slots }, 'X').replace(/^\n/, '')   // the whole preamble, not a digest:
  assert.strictEqual(r.stdout.slice(0, r.stdout.indexOf('HARD RAILS: ')), fullDoc.slice(0, fullDoc.indexOf('HARD RAILS: ')))
  assert.strictEqual(r.stdout.slice(r.stdout.indexOf('\nEVIDENCE LAW:')), fullDoc.slice(fullDoc.indexOf('\nEVIDENCE LAW:')))
  const sibling = path.join(dir, 'sibling-skill.md'); fs.writeFileSync(sibling, '# A sibling skill\n\n## Rails (one line each)\n1. **The server share is human territory:** read freely; write only final deliverables.\n\n## Next section\n')
  r = run(['common', write('slots.json', slots), path.join(__dirname, '..', 'references', 'document.md'), sibling])
  assert.ok(r.status === 0 && r.stdout.includes('The server share is human territory'), r.stderr)   // a sibling skill's class rails
  r = run(['common', write('given.json', { ...slots, CLASS_RAILS: 'RAILS GIVEN VERBATIM' })])
  assert.ok(r.status === 0 && r.stdout.includes('HARD RAILS: RAILS GIVEN VERBATIM'), r.stderr)
  const { MODEL_BUILD, EFFORT_BUILD, ...sonnet } = slots
  r = run(['common', write('sonnet.json', sonnet)])                                    // D17: a document class needs opus builders
  assert.strictEqual(r.status, 2); assert.match(r.stderr, /MODEL_BUILD 'opus'/)
  r = run(['common', write('unfilled.json', { ...slots, ROUND: '<r1>' })])
  assert.strictEqual(r.status, 2); assert.match(r.stderr, /unfilled SLOTS: ROUND/)
  r = run(['common', write('typo.json', { ...slots, WROK: '/w' })])
  assert.strictEqual(r.status, 2); assert.match(r.stderr, /unknown slot\(s\) WROK/)
  for (const name of ['FINDING', 'CLAIM_AUDIT', 'PMO_BLOCKER', 'PANEL_VERDICT', 'EDIT_LIST', 'CASCADE_ITEM', 'GATE_DECISION']) {
    r = run(['schema', name])
    assert.strictEqual(r.status, 0, r.stderr)
    assert.deepStrictEqual(JSON.parse(r.stdout), JSON.parse(JSON.stringify(kit[name])), name)
  }
  assert.strictEqual(run(['schema', 'NOPE']).status, 2)
  const claim = { args: [{ claim: 'The PR modified 3 files in src/auth' }] }
  assert.strictEqual(JSON.parse(run(['claimSeverity', '--class', 'software-build'], claim).stdout), 'low')
  assert.strictEqual(JSON.parse(run(['claimSeverity'], claim).stdout), 'high')           // an unset class fails closed (F9)
  fs.rmSync(dir, { recursive: true, force: true })
})
