# 考え方と出典

参照日: 2026-10-03。この分野は変化が速い。用語の定義は公式に固まっていないものを含む。

## 3つの考え方

| 用語 | 要点 | このキットでの実装 |
|---|---|---|
| ハーネスエンジニアリング | モデルとタスクの間にある実行系（指示・ツール・制約・検証・フィードバック）を設計する。モデルを変えずに出力の信頼性を上げる | 検証コマンドへの集約、フック、deny ルール、CI |
| コンテキストエンジニアリング | コンテキストは有限な資源。最初に入れるのは最小限にし、残りはパスで指して必要時に読ませる（just-in-time）。長い作業は外部ファイルに状態を残す | 短い AGENTS.md、PROGRESS.md、SessionStart での注入、失敗ログは末尾だけ返す |
| ループエンジニアリング | 人が毎回プロンプトを打つ代わりに「実行→検証→修正→継続」を回すループを設計する。hook（イベント駆動）/ cron（定期）/ heartbeat（常駐）。**無人のループは無人で間違え続ける**ので、検証・ログ・承認ゲート・失敗上限が必須 | PostToolUse と Stop のフック、差し戻し上限、`/handoff` |

## 長時間タスクの設計（Anthropic の知見の要約）

- 各セッションは前の記憶を持たない。**次のセッションのために成果物と進捗を残す**ことを毎回の義務にする。
- 1回の作業単位は1機能。小さく進めて毎回検証する。
- 計画・生成・評価の役割を分けると品質が上がる（評価者が自分の生成物を採点しない）。

## 出典

| 資料 | 種別 | URL |
|---|---|---|
| Effective harnesses for long-running agents | 公式（Anthropic Engineering） | https://anthropic.com/engineering/effective-harnesses-for-long-running-agents |
| Claude Code hooks リファレンス | 公式ドキュメント | https://docs.claude.com/en/docs/claude-code/hooks |
| OpenAI Harness Engineering / Codex | 非公式（InfoQ 報道） | https://www.infoq.com/news/2026/02/openai-harness-engineering-codex |
| Anthropic three-agent harness | 非公式（InfoQ 報道） | https://infoq.com/news/2026/04/anthropic-three-agent-harness-ai/ |
| Loop engineering | 非公式（The New Stack） | https://thenewstack.io/loop-engineering/ |
| Loop engineering emerges | 非公式（ADTmag） | https://adtmag.com/articles/2026/07/01/loop-engineering-emerges-as-developers-put-ai-coding-agents-on-repeat.aspx |
| Anthropic context engineering（要約） | 非公式（解説） | https://agentic-ai.readthedocs.io/en/latest/ContextEngineering/anthropic/ |

## 未検証・注意

- 「Claude Code は CLAUDE.md がない場合に AGENTS.md を読む」という情報は第三者記事のみで確認（公式リリースノート未確認）。このキットは確実に動く `CLAUDE.md` に `@AGENTS.md` と書く方式を採る。
- 「ループエンジニアリング」は2026年6月ごろ SNS 発で広まった呼び名で、公式の定義はない。
