# PROGRESS

セッションをまたぐ作業の外部記憶。新しいセッションは最初にここを読む（SessionStart フックが先頭を自動注入する）。
**上ほど新しい。完了したものは「完了」へ移し、古いものは要約して短く保つ。**

## 進行中

- （なし）

## 次にやること

- スキルの評価（eval）ループ: 各スキルの「起動すべき依頼／すべきでない依頼」と期待出力の要件を `evals/` に置き、skill-creator で回す。
- 定期メンテナンス: 各スキル内の腐る情報（モデル名・ベンダーのガイド）を定期確認する Routine / cron。実行環境に依存するため未導入。

## 完了

- 2026-10-03: 導入を簡単にした。`curl … install-harness.sh | sh` の1行導入（clone 不要）、検証コマンドの自動判定（Makefile / package.json / go / cargo / pytest）、`make` でコマンド一覧、`make install-harness TARGET=…`。
- 2026-10-03: ハーネスを導入（AGENTS.md / CLAUDE.md / `make check` / フック3種 / reviewer サブエージェント / `/handoff` / CI）。`agent-harness-kit` スキルを追加。詳細は `docs/decisions/0001-agent-harness.md`。
