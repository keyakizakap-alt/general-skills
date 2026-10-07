// workflows/*.js の模擬実行テスト。本物のサブエージェントを起動せず、制御の流れ（分岐・ループ・停止条件・エージェント数）を確かめる。
//   node tools/test_workflows.mjs
// agent() はスキーマから作った模擬データを返す。シナリオごとに応答を差し替えられる。
// API の形は Claude Code 同梱のワークフロー作成リファレンス（v2.1.289）に合わせている:
//   agent(prompt, opts) / pipeline(items, ...stages) / parallel(thunks) / phase(title) / log(msg) / args / budget / workflow()

import { readFileSync, readdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const DIR = join(ROOT, 'workflows')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor

// ---- スキーマから模擬データを作る ----
function fake(schema, depth = 0) {
  if (!schema) return 'x'
  if (schema.enum) return schema.enum[0]
  switch (schema.type) {
    case 'object': {
      const out = {}
      for (const [k, v] of Object.entries(schema.properties || {})) out[k] = fake(v, depth + 1)
      return out
    }
    case 'array': return depth > 6 ? [] : [fake(schema.items, depth + 1), fake(schema.items, depth + 1)]
    case 'number': case 'integer': return 1
    case 'boolean': return true
    default: return `s${depth}`
  }
}

// ---- 実行環境（禁止 API は投げる） ----
class StrictDate extends Date {
  constructor(...a) { if (!a.length) throw new Error('new Date() は使えない'); super(...a) }
  static now() { throw new Error('Date.now() は使えない') }
}
const StrictMath = Object.create(Math, { random: { value: () => { throw new Error('Math.random() は使えない') } } })

async function run(file, args, respond = () => undefined) {
  const src = readFileSync(join(DIR, file), 'utf8')
  if (!/^\s*(\/\/[^\n]*\n\s*)*export const meta = \{/.test(src)) throw new Error('先頭が export const meta ではない')
  const body = src.replace('export const meta =', 'const meta =')
  const calls = []
  const phases = []
  const logs = []
  const agent = async (prompt, opts = {}) => {
    if (typeof prompt !== 'string' || !prompt) throw new Error('agent() の prompt が空')
    const n = calls.length
    calls.push({ prompt, opts })
    if (calls.length > 50) throw new Error('エージェント数が50を超えた（ループが止まらない疑い）')
    const custom = respond(prompt, opts, n)
    if (custom !== undefined) return custom
    return opts.schema ? fake(opts.schema) : 'ok'
  }
  const parallel = async thunks => Promise.all(thunks.map(t => Promise.resolve().then(t).catch(() => null)))
  const pipeline = async (items, ...stages) => {
    if (items.length > 4096) throw new Error('pipeline の上限超過')
    return Promise.all(items.map(async (item, i) => {
      let v = item
      try { for (const s of stages) v = await s(v, item, i) } catch { return null }
      return v
    }))
  }
  // meta は純粋なリテラルなので、その部分だけを式として評価する
  const metaSrc = src.slice(src.indexOf('export const meta ='), src.indexOf('\n}\n') + 2).replace('export const meta =', 'return')
  const meta = new Function(metaSrc)()
  const wrapped = new AsyncFunction('agent', 'parallel', 'pipeline', 'phase', 'log', 'args', 'budget', 'workflow', 'Date', 'Math', body)
  const result = await wrapped(agent, parallel, pipeline, t => phases.push(t), m => logs.push(m), args,
    { total: null, spent: () => 0, remaining: () => Infinity }, async () => { throw new Error('workflow() は未使用のはず') },
    StrictDate, StrictMath)
  return { meta, result, calls, phases, logs }
}

// ---- テスト ----
const tests = []
const test = (name, f) => tests.push({ name, f })
const assert = (cond, msg) => { if (!cond) throw new Error(msg) }

function checkMeta(file, meta, phases) {
  assert(meta && meta.name === file.replace(/\.js$/, ''), `${file}: meta.name がファイル名と不一致`)
  assert(typeof meta.description === 'string' && meta.description, `${file}: description が空`)
  const titles = (meta.phases || []).map(p => p.title)
  for (const p of new Set(phases)) assert(titles.includes(p), `${file}: phase('${p}') が meta.phases に無い`)
}

for (const file of readdirSync(DIR).filter(f => f.endsWith('.js'))) {
  test(`${file}: args なしは分かりやすいエラーで止まる`, async () => {
    let err = null
    try { await run(file, undefined) } catch (e) { err = e }
    assert(err && /args\./.test(err.message), `args 不足のエラーにならない: ${err && err.message}`)
  })
}

// 事実確認役の模擬: プロンプト中の主張 id をすべて verified で返す（status を差し替え可能）
const echoVerdicts = (prompt, status = () => 'verified') =>
  ({ results: [...prompt.matchAll(/"id":"(c\d+)"/g)].map(m => ({ id: m[1], status: status(m[1]), source: 'https://example.com', note: '' })) })
const isCheck = o => o.phase === '事実確認'

test('deck-build lite: 5エージェント、全フェーズ通過', async () => {
  const r = await run('deck-build.js', { topic: 'AI導入の効果', format: 'pptx' }, (p, o) => isCheck(o) ? echoVerdicts(p) : undefined)
  checkMeta('deck-build.js', r.meta, r.phases)
  assert(r.calls.length === 5, `エージェント数 ${r.calls.length}（期待 5）`)
  assert(r.result.files.length > 0 && r.result.slides > 0, '成果物が空')
  assert(r.result.factcheck.verified === r.result.slides * 2, '模擬データで全件 verified にならない')
})

test('deck-build full: 構成案3・章ごと執筆・事実確認2系統', async () => {
  const r = await run('deck-build.js', { topic: 'x', format: 'html', depth: 'full' })
  checkMeta('deck-build.js', r.meta, r.phases)
  // 構成案3 + 統合1 + 章2（模擬は配列2件）+ 事実確認2 + 組版1 + 検査1 = 10
  assert(r.calls.length === 10, `エージェント数 ${r.calls.length}（期待 10）`)
  assert(r.calls.some(c => c.prompt.includes('index.html')), 'html の組版指示が無い')
})

test('deck-build: 1系統でも refuted があれば反映される', async () => {
  const r = await run('deck-build.js', { topic: 'x', depth: 'full' }, (p, o) => {
    if (o.label === '数値・日付・名称が正確か') return echoVerdicts(p, id => (id === 'c1' ? 'refuted' : 'verified'))
    if (isCheck(o)) return echoVerdicts(p)
  })
  assert(r.result.factcheck.refuted.length > 0, 'refuted が結果に出ない')
  assert(r.result.factcheck.refuted.length === 1 && r.result.factcheck.verified === r.result.slides * 2 - 1, JSON.stringify(r.result.factcheck))
  assert(r.calls.find(c => c.opts.label && c.opts.label.startsWith('組版')).prompt.includes('refuted'), '組版に要対応が渡っていない')
})

test('deck-build: 確認役が一部の主張を返さなければ未確認になる（黙って verified にしない）', async () => {
  const r = await run('deck-build.js', { topic: 'x' }, (p, o) => isCheck(o) ? { results: echoVerdicts(p).results.slice(1) } : undefined)
  assert(r.result.factcheck.unverified.length === 1, JSON.stringify(r.result.factcheck))
})

test('app-design lite: 4エージェント、仕様書パスを返す', async () => {
  const r = await run('app-design.js', { request: '請求書の承認フロー' })
  checkMeta('app-design.js', r.meta, r.phases)
  assert(r.calls.length === 4, `エージェント数 ${r.calls.length}（期待 4）`)
  assert(r.result.spec && r.result.next.includes('app-implement'), '次の一手が無い')
})

const PASS = { passed: true, failure_signature: '', summary: 'ok', changed_files: ['a.ts'] }
const FAIL = sig => ({ passed: false, failure_signature: sig, summary: 'ng', changed_files: ['a.ts'] })

test('app-implement: 全作業が一発で通る', async () => {
  const r = await run('app-implement.js', { spec: 'docs/spec/x.md' }, (p, o) => (o.schema && 'passed' in (o.schema.properties || {})) ? PASS : undefined)
  checkMeta('app-implement.js', r.meta, r.phases)
  assert(r.result.done.length === 2 && !r.result.blocked, '完了しない')
  assert(r.calls.length === 1 + 2 + 2, `エージェント数 ${r.calls.length}（準備1+実装2+レビュー2）`)
})

test('app-implement: 同じ失敗が2回続いたら止まる', async () => {
  const r = await run('app-implement.js', { spec: 's' }, (p, o) => (o.schema && 'passed' in (o.schema.properties || {})) ? FAIL('型エラー A') : undefined)
  assert(r.result.blocked && /同じ失敗/.test(r.result.blocked.reason), `停止理由が違う: ${JSON.stringify(r.result.blocked)}`)
  assert(r.result.done.length === 0, '失敗した作業が完了扱い')
  assert(r.result.blocked.changed_files.length > 0 && r.result.changed_files.length > 0, '止まった作業の変更ファイルが報告されない')
  assert(r.calls.filter(c => c.opts.phase === 'レビュー').length === 2, '途中まで変更したファイルがレビューされない')
})

test('app-implement: 修正で通れば次の作業へ進む', async () => {
  let n = 0
  const r = await run('app-implement.js', { spec: 's' }, (p, o) => {
    if (!(o.schema && 'passed' in (o.schema.properties || {}))) return undefined
    n++
    return n === 1 ? FAIL('A') : PASS
  })
  assert(r.result.done.length === 2 && r.result.done[0].fix_rounds === 1, `修正回数の記録が違う: ${JSON.stringify(r.result.done)}`)
})

test('app-implement: maxTasks を超える作業は黙って捨てず log に出す', async () => {
  const many = { tasks: [1, 2, 3, 4, 5].map(i => ({ id: `T${i}`, title: 't', files: [], acceptance: [] })), check_command: 'npm test' }
  const r = await run('app-implement.js', { spec: 's' }, (p, o) => {
    if (o.label === '仕様書の読み込み') return many
    if (o.schema && 'passed' in (o.schema.properties || {})) return PASS
  })
  assert(r.result.done.length === 2, `実行件数 ${r.result.done.length}（期待 2）`)
  assert(r.logs.some(l => l.includes('T3') && l.includes('T5')), '残りの作業が log に出ない')
  assert(r.result.remaining.join() === 'T3,T4,T5', '残りの作業が返らない')
  const again = await run('app-implement.js', { spec: 's', tasks: ['T3', 'T4'] }, (p, o) => {
    if (o.label === '仕様書の読み込み') return many
    if (o.schema && 'passed' in (o.schema.properties || {})) return PASS
  })
  assert(again.result.remaining.length === 0, `指定外や前回分を残りに数えている: ${again.result.remaining}`)
})

test('verify-fix: 初回で通れば修正しない', async () => {
  const r = await run('verify-fix.js', { command: 'npm test' }, () => PASS)
  checkMeta('verify-fix.js', r.meta, r.phases)
  assert(r.result.status === 'passed' && r.calls.length === 1, '余計な修正をした')
})

test('verify-fix: 同じ失敗2回で停止', async () => {
  const r = await run('verify-fix.js', { command: 'npm test' }, () => FAIL('A'))
  assert(r.result.status === 'stopped' && /同じ失敗/.test(r.result.stop_reason), r.result.stop_reason)
  assert(r.calls.length === 2, `エージェント数 ${r.calls.length}（初回1+修正1）`)
})

test('verify-fix: 失敗が変わり続けても上限で止まる', async () => {
  let n = 0
  const r = await run('verify-fix.js', { command: 'x', maxRounds: 3 }, () => FAIL(`E${n++}`))
  assert(r.result.status === 'stopped' && /上限 3/.test(r.result.stop_reason), r.result.stop_reason)
  assert(r.calls.length === 4, `エージェント数 ${r.calls.length}（初回1+修正3）`)
})

test('verify-fix: 途中で通る', async () => {
  let n = 0
  const r = await run('verify-fix.js', { command: 'x' }, () => (n++ < 2 ? FAIL(`E${n}`) : PASS))
  assert(r.result.status === 'passed' && r.result.rounds === 2, JSON.stringify(r.result))
})

test('deck-build: 事実確認役が全滅しても止まらず、全件を未確認にする', async () => {
  const r = await run('deck-build.js', { topic: 'x' }, (p, o) => (isCheck(o) ? null : undefined))
  assert(r.result.factcheck.verified === 0 && r.result.factcheck.unverified.length === r.result.slides * 2, JSON.stringify(r.result.factcheck))
  assert(r.logs.some(l => l.includes('系統が失敗')), '事実確認の失敗が log に出ない')
})

test('deck-build full: 2系統のうち1系統が失敗したら未確認に倒す', async () => {
  const r = await run('deck-build.js', { topic: 'x', depth: 'full' }, (p, o) => {
    if (o.label === '数値・日付・名称が正確か') return null
    if (isCheck(o)) return echoVerdicts(p)
  })
  assert(r.result.factcheck.verified === 0, `1系統だけで verified にしている: ${JSON.stringify(r.result.factcheck)}`)
})

test('deck-build full: 執筆に失敗した章を log で知らせる', async () => {
  let k = 0
  const r = await run('deck-build.js', { topic: 'x', depth: 'full' }, (p, o) => {
    if (o.phase === '執筆' && k++ === 0) return null  // 最初の章だけ失敗させる
    if (isCheck(o)) return echoVerdicts(p)
  })
  assert(r.logs.some(l => l.includes('執筆に失敗した章')), '章の欠落が log に出ない')
})

test('deck-build: docs 形式と未対応形式', async () => {
  const d = await run('deck-build.js', { topic: 'x', format: 'docs' }, (p, o) => (isCheck(o) ? echoVerdicts(p) : undefined))
  assert(d.calls.some(c => c.prompt.includes('document.md')) && d.result.next.includes('Docs'), 'docs 形式の指示が無い')
  const u = await run('deck-build.js', { topic: 'x', format: 'keynote' }, (p, o) => (isCheck(o) ? echoVerdicts(p) : undefined))
  assert(u.result.format === 'pptx' && u.logs.some(l => l.includes('未対応')), '未対応形式を黙って置き換えている')
})

test('app-implement: args.check を優先し、未設定なら止まる', async () => {
  const r = await run('app-implement.js', { spec: 's', check: 'make check' }, (p, o) =>
    o.label === '仕様書の読み込み' ? { tasks: [{ id: 'T1', title: 't', acceptance: [] }], check_command: 'npm test' }
      : (o.schema && 'passed' in (o.schema.properties || {})) ? PASS : undefined)
  assert(r.result.check_command === 'make check', `args.check が使われない: ${r.result.check_command}`)
  let err = null
  try {
    await run('app-implement.js', { spec: 's' }, (p, o) => (o.label === '仕様書の読み込み' ? { tasks: [{ id: 'T1', title: 't', acceptance: [] }], check_command: '未設定' } : undefined))
  } catch (e) { err = e }
  assert(err && /検査コマンド/.test(err.message), '検査コマンド未設定のまま実装に進んだ')
})

test('verify-fix: maxRounds は1〜5に制限し、log で知らせる', async () => {
  let n = 0
  const r = await run('verify-fix.js', { command: 'x', maxRounds: 100 }, () => FAIL(`E${n++}`))
  assert(r.result.rounds === 5 && r.logs.some(l => l.includes('範囲外')), JSON.stringify(r.result))
})

let failed = 0
for (const t of tests) {
  try { await t.f(); console.log(`ok   ${t.name}`) } catch (e) { failed++; console.log(`FAIL ${t.name}\n     ${e.message}`) }
}
console.log(`\n${tests.length - failed}/${tests.length} passed`)
process.exit(failed ? 1 : 0)
