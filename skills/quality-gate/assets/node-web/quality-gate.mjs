#!/usr/bin/env node
// Node プロジェクト向けの、コードだけを対象にした品質ゲート。ここでの PASS は本番での動作確認ではない。
// 使い方: 対象リポジトリの scripts/quality-gate.mjs にコピーする（references/node-web-adoption.md）
import { readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { resolve } from 'node:path';

const modeFlag = process.argv.indexOf('--mode');
const mode = modeFlag >= 0 ? process.argv[modeFlag + 1] : 'draft';
if (!['draft', 'release'].includes(mode)) {
  console.error('使い方: node scripts/quality-gate.mjs --mode draft|release');
  process.exit(2);
}
let pkg;
try { pkg = JSON.parse(readFileSync(resolve('package.json'), 'utf8')); }
catch (e) { console.error('package.json が無いか、読めません:', e.message); process.exit(2); }
const scripts = pkg.scripts ?? {};
const checks = [];
function run(label, script, required) {
  if (!Object.hasOwn(scripts, script)) {
    checks.push({ label, script, status: required ? 'BLOCKED' : 'NOT_RUN', reason: 'package.json に該当 script が無い' });
    return;
  }
  // package.json の "qualityGate": { "requiresEnv": { "<script>": ["ENV_NAME"] } } に書いた環境変数が無いときは、
  // 実行して FAIL にせず、足りないものを明示して BLOCKED / NOT_RUN にする（製品の不具合と区別するため）。
  const missingEnv = (pkg.qualityGate?.requiresEnv?.[script] ?? []).filter(name => !process.env[name]);
  if (missingEnv.length) {
    checks.push({ label, script, status: required ? 'BLOCKED' : 'NOT_RUN', reason: `必要な環境変数が未設定: ${missingEnv.join(', ')}` });
    return;
  }
  const started = new Date().toISOString();
  const p = spawnSync('npm', ['run', script], { stdio: 'inherit', shell: process.platform === 'win32', timeout: 15 * 60 * 1000 });
  const ok = !p.error && p.status === 0;
  checks.push({ label, script, status: ok ? 'PASS' : 'FAIL', started, exitCode: p.status, error: p.error?.message });
}
// 機械的に判定できる検査だけ。ブラウザ上の意味のある確認の代わりにはならない。
run('lint', 'lint', mode === 'release');
run('typecheck', 'typecheck', mode === 'release');
run('unit', 'test:unit', false);
run('build', 'build', true);
run('e2e', 'test:e2e', mode === 'release');
const blockers = checks.filter(c => c.status === 'FAIL' || c.status === 'BLOCKED');
const report = {
  at: new Date().toISOString(), mode,
  summary: blockers.length ? 'BLOCKED' : 'LOCAL_CHECKS_PASSED',
  caveats: [
    'ローカル検査の成功は、主要フローの網羅や公開URLでの動作を証明しない。',
    '公開URLと実際の操作フローは別に確認する。',
  ],
  checks,
};
writeFileSync('quality-evidence.json', JSON.stringify(report, null, 2) + '\n');
console.log('\n' + JSON.stringify(report, null, 2));
process.exit(blockers.length ? 1 : 0);
