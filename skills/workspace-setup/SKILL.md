---
name: workspace-setup
description: 開いているプロジェクトに、AIエージェント（Claude Code ほか）が作業しやすい環境を実際に構築する。既存の指示書・設定を壊さずに、AGENTS.md と CLAUDE.md の分割、パス限定ルール、作業手順と検査のスキル、読み取り専用の確認役、秘密ファイルの deny、構造検査の Stop hook、作業記録のひな形を作り、検査して報告する。「Claude Code の環境を整えて」「このリポジトリをAIで作業しやすくして」「CLAUDE.md を作って/整理して」「AGENTS.md を用意して」「プロジェクトのAI用セットアップ」といった依頼で使う。Use when asked to set up or tidy a project for AI coding agents (CLAUDE.md, AGENTS.md, .claude settings, rules, skills, subagents, hooks).
---

# workspace-setup

**目的**: 説明で終わらせず、対象プロジェクトに設定ファイルを実際に作り、既存設定へ安全に統合し、検査して報告する。
何度実行しても同じルール・Hook・フォルダが増えない状態にする。

## 0. 実行環境を見分ける

| 環境 | できること |
|---|---|
| Claude Code（ローカル / クラウド / Cowork）でプロジェクトを開いている | 手順 1〜8 をすべて行う |
| claude.ai などのチャット（プロジェクトのファイルに触れない） | 手順 1 の質問で用途を聞き、手順 3〜6 のファイル一式を**成果物として出力**し、置き場所と手順 7 の確認方法を案内する。検査は「未実行」と明記する |

仕様は記憶で書かない。`references/spec-notes.md`（参照日つき）を読み、可能なら公式資料の最新版で再確認する。
確認できない機能・設定キーは使わず、「未確認」と報告する。

## 1. 調べる（書き込む前に）

- 作業ディレクトリ、OS、シェル、Claude Code のバージョン（`claude --version`）、Git の有無と未コミット変更
- 既存の `CLAUDE.md`、`.claude/CLAUDE.md`、`CLAUDE.local.md`、`AGENTS.md`、`AGENTS.override.md`、`.claude/` 配下（settings、skills、agents、rules、hooks）、テストと検査コマンド
- 秘密を含み得る設定は全文を表示しない（構造とキー名だけ見る）。既存の Hook やスクリプトを無条件に実行しない
- ホーム直下・システム領域・複数案件を含む親フォルダなら、書き込まずに対象フォルダを聞く
- 用途（開発 / 文章制作 / 調査 / 事務 / 混在）を判断する。判断できなければ共通部分だけ進める

## 2. 境界を決めて計画を示す

短い計画（作るもの・変えるもの・触らないもの）を示してから進める。詳細は `references/procedure.md` の「変更の境界」。

- してよい: プロジェクト内の可逆な作成・追記
- 承認が必要: 移動・削除、大規模な再編、グローバル設定、パッケージ追加、外部送信・公開、commit / push、本番操作
- 既存ファイルは必要箇所だけ変える。JSON の未知のキーを消さない。配列と Hooks は丸ごと置換せず、重複なく足す
- 変更前のファイルを Git 追跡外のバックアップ（例 `.claude/setup-backup/<日付>/`）に置く。`git reset --hard` と `git clean` は使わない

## 3. 指示書を分ける

- `AGENTS.md`（60〜100行目安）: ツール共通の正本。ひな形 `assets/AGENTS.template.md`。既存の重要ルールは残す
- Claude の入口: `CLAUDE.md` から `@AGENTS.md` を独立行で import する。**リポジトリがプラグインのルートを兼ねる場合は `.claude/CLAUDE.md` に置き `@../AGENTS.md`**（ルートの CLAUDE.md は `claude plugin validate` が警告する）。ひな形 `assets/CLAUDE.template.md`
- 長い背景・進捗は `docs/ai/` と `tasks/` に分け、import せず用途付きで参照する。ひな形 `assets/doc-templates.md`

## 4. ルール・スキル・確認役を作る

- `.claude/rules/`: 用途に必要なものだけ。`paths` で対象を限定する（`paths` 無しは常時読み込み）。日本語文書用のひな形 `assets/rules/ja-writing.md`
- `.claude/skills/project-work/`、`.claude/skills/project-check/`: ひな形 `assets/project-work.SKILL.md`、`assets/project-check.SKILL.md`。既存名や組み込みコマンドと衝突するなら改名する
- `.claude/agents/project-reviewer.md`: tools は Read, Grep, Glob のみ。ひな形 `assets/project-reviewer.md`

## 5. 権限を緩めずに設定する

- `.claude/settings.json` に秘密ファイルの Read / Edit deny を統合する。ひな形 `assets/settings.template.json`
- `bypassPermissions`、Bash 全許可、広い `allowed-tools` は使わない。既存の過剰権限は報告だけする
- `.gitignore` に `CLAUDE.local.md`、`.claude/settings.local.json`、バックアップ、作業記録を必要に応じて足す。既に追跡済みのものは ignore で非公開にならないので報告する
- Sandbox と MCP は自動で変えない（`references/spec-notes.md` の限界を報告に書く）

## 6. 構造検査と Stop hook

1. `assets/check_setup.py` を `.claude/hooks/` にコピーし、プロジェクト固有の対象を `.claude/hooks/check_setup.json` に書く（例 `assets/check_setup.example.json`）
2. 一時ディレクトリの複製で、正常・異常・`stop_hook_active: true`・タイムアウトを試す（手順は `references/procedure.md`）
3. 合格してから Stop hook を登録する。`check_setup.py` を含む登録が既にあれば追加しない
4. Python が無いなど適切な環境が無ければ登録せず、手動検査に切り替えて理由を報告する

## 7. 確認して報告する

- 作成したファイルを読み直し、import 先、JSON 構文、Skills と Subagent の形式（`claude plugin validate .claude/skills` / `.claude/agents` が使えれば実行）、Hook のテスト、差分、依頼外の変更を点検する
- 既存の検査コマンドは、定義と副作用を確認してから必要分だけ実行する
- 実機での読み込みは自己申告と区別し、利用者に新しいセッションでの `/memory`、`/hooks`、`/agents`、`/permissions`、`/context` を案内する
- 報告: 作成・変更したファイル、採用した構成、検査と結果（成功 / 失敗 / 未実行）、未適用・未確認、復元手順、最初に送る依頼例。同じ内容を `docs/ai/setup-report.md` に残す
