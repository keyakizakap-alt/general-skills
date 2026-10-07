# CLAUDE.md

共通ルールの正本はリポジトリ直下の AGENTS.md。ここには Claude Code 固有のことだけを書く。

@../AGENTS.md

## Claude Code 固有

- 定型作業は `/project-work <依頼>`、成果物の検査は `/project-check <対象>` で始める（どちらも明示起動専用）。
- 作成者とは別視点の確認が必要なときは `project-reviewer` サブエージェントに、合格条件・差分・元資料・検査結果を渡す。読み取り専用なので、テストは自分で実行して結果を渡す。
- 編集対象に応じて `.claude/rules/` の規約が自動で読み込まれる（`skills/`、`mods/`、日本語文書）。
- 資料・アプリ開発の大きな作業は `workflows/` のワークフロー（`deck-build`、`app-design`、`app-implement`、`verify-fix`）を使える。ワークフローを変えたら `skills/workspace-setup/assets/workflows/` にもコピーし、`node tools/test_workflows.mjs` を通す。
- Stop 時に `.claude/hooks/check_setup.py` が設定ファイルの構造だけを検査する。成果物の品質検査ではない。
- 個人用の指示は `CLAUDE.local.md`、個人用設定は `.claude/settings.local.json` に置く（どちらもGit追跡外）。
