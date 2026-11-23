# Node / Web プロジェクトへの導入手順（品質ゲートスクリプト）

`assets/node-web/` の3ファイルを、対象リポジトリに意図して1つずつコピーする。コピーするまで、既存のリポジトリ・CI・設定は何も変わらない。

| コピー元 | コピー先 | 役割 |
|---|---|---|
| `assets/node-web/quality-gate.mjs` | `scripts/quality-gate.mjs` | `lint` `typecheck` `test:unit` `build` `test:e2e` を順に実行し、結果を `quality-evidence.json` に書く |
| `assets/node-web/web-quality.yml` | `.github/workflows/web-quality.yml` | PR で上のスクリプトを実行し、証拠をジョブサマリーに出す |
| `assets/node-web/smoke.spec.ts` | `tests/e2e/smoke.spec.ts` | Playwright の最小スモークテスト（Playwright を使う場合のみ） |

## 手順
1. `package.json` に `lint` `typecheck` `build` `test:e2e` の script があるか確認する。名前が違えば `quality-gate.mjs` の `run(...)` の行を合わせる。無い検査を成功扱いにしない。
2. Playwright を使うなら `npm i -D @playwright/test` と `npx playwright install chromium`（依存追加なので、利用者の承認を得てから行う）。スモークテストは**実際のルート・ボタン・期待結果**に書き換える。
3. 起動中のサーバーや秘密情報が要る検査は、`package.json` に次を書く。環境変数が無いときは実行せず `BLOCKED`（公開前モード）/ `NOT_RUN`（通常モード）と理由を記録する。値はログに出さない。

   ```json
   "qualityGate": { "requiresEnv": { "test:e2e": ["OWNER_PASSWORD"] } }
   ```
4. `quality-evidence.json` を `.gitignore` に足す。
5. 公開前は `node scripts/quality-gate.mjs --mode release`。必須の検査が欠けていると `BLOCKED` で終了コード1になる。
6. 公開URLの確認は別に行い、`references/evidence-report-template.md` に記録する。

## 結果の読み方
- `LOCAL_CHECKS_PASSED`: 機械的に判定できる検査が通っただけ。主要フローの網羅や公開URLの動作は証明しない。
- `BLOCKED`: 失敗した、または必須の検査が実行できない。理由は `checks[].reason` に書かれる。
- ビルドの成功だけで「E2E 済み」と書かない。
