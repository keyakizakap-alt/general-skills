# 作業環境の構成と復元手順

最終更新: 2026-10-05 / Claude Code 2.1.289 で確認。経緯の詳細は PR #7 の説明を参照。

## 構成

| 役割 | 場所 |
|---|---|
| 共通ルール（正本） | `AGENTS.md` |
| Claude の入口 | `.claude/CLAUDE.md`（`@../AGENTS.md`。ルートに置くと plugin validate が警告するため） |
| パス限定ルール | `.claude/rules/`（`skills/**`、`mods/**`、`**/*.md`） |
| このリポジトリ用の手順・確認役 | `.claude/skills/project-{work,check}`、`.claude/agents/project-reviewer.md` |
| 権限 | `.claude/settings.json`（秘密ファイルの Read/Edit deny のみ。allow なし） |
| 設定の構造検査 | `.claude/hooks/check_setup.py`（Stop hook、timeout 20秒）＋テスト |
| 完了の定義 / CI | `tools/check.py`、`.github/workflows/check.yml`、`Makefile` |
| 配布物 | `skills/`、`workflows/`、`agents/`（README の一覧を参照） |

PR #5（agent harness）から移植したもの: `tools/check.py`（このリポジトリ用に書き直し）、CI、`Makefile`、配布内容を変えたら version を上げる約束（PR #4 由来）。
移植しなかったもの: 編集のたびに検証する PostToolUse（重い）、`PROGRESS.md`（`tasks/` と重複）、独自コマンド群（スキルとワークフローで代替）。

## 未確認・制約

- **ワークフローは模擬実行のみ**。本物の実行（Workflow ツール）はこのセッションで行っていない。最初は小さな args で試す
- 新しいセッションでの読み込み確認（`/memory`、`/hooks`、`/agents`、`/permissions`、`/workflows`）は未実施
- Read/Edit deny は Python/Node スクリプト内の読み書きや `grep -r` を防げない。OS レベルの制限は Sandbox（このクラウドコンテナには bubblewrap が無く未使用）
- `tasks/` は Git 追跡外。クラウドセッションは使い捨てなので、持ち越す引き継ぎは PR の説明か `docs/` に書く

## 復元手順

`git reset --hard` / `git clean` は使わない。PR #7 をマージしなければ main は変わらない。マージ後に戻す場合は、該当コミットを `git revert` する。
