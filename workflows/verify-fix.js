export const meta = {
  name: 'verify-fix',
  description: '指定した検査コマンドが通るまで「実行→原因特定→最小修正」を繰り返す。同じ失敗が2回続くか上限回数で止めて報告する',
  whenToUse: 'テスト・型検査・Lint・ビルドを通したいとき。args: {command, maxRounds?, scope?}',
  phases: [
    { title: '検査', detail: '現状の失敗を記録' },
    { title: '修正', detail: '原因を特定して最小修正→再検査' },
  ],
}

const A = args || {}
if (!A.command) throw new Error('args.command（検査コマンド）が必要: {command, maxRounds?, scope?}')
const MAX = Number.isInteger(A.maxRounds) ? Math.min(Math.max(A.maxRounds, 1), 5) : 3  // 1〜5回に制限（使用量の暴走を防ぐ）
if (Number.isInteger(A.maxRounds) && MAX !== A.maxRounds) log(`maxRounds ${A.maxRounds} は範囲外のため ${MAX} 回にした`)
const SCOPE = A.scope ? `変更してよい範囲: ${A.scope}` : '変更は失敗の原因に直接関係するファイルだけ'
const RESULT = {
  type: 'object',
  required: ['passed', 'failure_signature', 'summary', 'changed_files'],
  properties: {
    passed: { type: 'boolean' },
    failure_signature: { type: 'string' },
    summary: { type: 'string' },
    changed_files: { type: 'array', items: { type: 'string' } },
  },
}

phase('検査')
let r = await agent(
  `検査コマンド「${A.command}」を実行して結果を返す。ファイルは変更しない。` +
  '失敗したら failure_signature に「失敗した検査名と主なエラーの要約」を1行で書く（同じ原因なら同じ文字列になるように）。',
  { label: '初回の検査', schema: RESULT, effort: 'low' },
)
if (!r) throw new Error('検査を実行できなかった')
if (r.passed) return { status: 'passed', rounds: 0, summary: r.summary, changed_files: [] }

phase('修正')
const history = [r.failure_signature]
const changed = new Set()
let rounds = 0
let stopReason = ''
while (true) {
  if (rounds >= MAX) { stopReason = `修正が上限 ${MAX} 回に達した`; break }
  rounds++
  r = await agent(
    `検査「${A.command}」が失敗している: ${r.failure_signature}\n${r.summary}\n${SCOPE}\n` +
    '原因を特定して最小限の修正をし、もう一度検査を実行して結果を返す。' +
    'テストの削除・スキップ、検査設定の緩和、依存パッケージの追加、秘密情報の読み取りはしない。',
    { label: `修正 ${rounds}`, schema: RESULT },
  )
  if (!r) { stopReason = 'エージェントが失敗した'; break }
  r.changed_files.forEach(f => changed.add(f))
  if (r.passed) break
  if (r.failure_signature === history[history.length - 1]) { stopReason = `同じ失敗が2回続いた: ${r.failure_signature}`; break }
  history.push(r.failure_signature)
}

return {
  status: r && r.passed ? 'passed' : 'stopped',
  rounds,
  stop_reason: stopReason || null,
  failures_seen: history,
  last_summary: r ? r.summary : '',
  changed_files: [...changed],
  next: r && r.passed ? '差分と検査結果を報告する' : '停止理由・試したこと・不足情報を利用者に報告する',
}
