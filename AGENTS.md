# AGENTS.md

AIコーディングエージェント向けの作業ガイド。人間向けの説明は `README.md` を参照。

## プロジェクト概要

業務で使える汎用スキル集。1つのリポジトリで次の3形態として配布している。

1. **Claude Code プラグインマーケットプレイス**（`.claude-plugin/marketplace.json` → `plugin.json`）
2. **スキルの直接配置**（`skills/<name>/` を `~/.claude/skills/` 等にコピー／リンク）
3. **claude.ai 用ZIP**（`tools/build_skill_zip.py` で `dist/<name>.zip` を生成）

## ディレクトリ構成

```
.claude-plugin/
  marketplace.json   # マーケットプレイス定義（name: keyakizakap-skills）
  plugin.json        # プラグイン定義（name: general-skills, version）
skills/<skill-name>/
  SKILL.md           # 必須。YAMLフロントマター（name, description）＋手順
  references/        # 詳細資料（SKILL.md から必要時に読ませる）
  assets/            # テンプレート・例
  scripts/           # 検証ツール（Python 標準ライブラリのみ）
tools/
  build_skill_zip.py # claude.ai 用ZIPのビルド（フロントマター検証つき）
dist/                # ビルド成果物（.gitignore 済み・コミットしない）
```

現在のスキル: `prompt-architect`、`ryo-product-delivery`。

## 検証コマンド

変更後は該当するものを実行し、すべて通ることを確認する。

```bash
python3 tools/build_skill_zip.py                        # 全スキルのフロントマター検証＋ZIP生成
python3 tools/build_skill_zip.py <skill-name>           # 単体
claude plugin validate .claude-plugin/marketplace.json  # Claude Code CLI がある場合
claude plugin validate .claude-plugin/plugin.json
claude plugin validate skills/

# prompt-architect のリンター（スクリプトを変更した場合の動作確認）
python3 skills/prompt-architect/scripts/lint_prompt.py skills/prompt-architect/assets/universal-template.md
```

## スキル作成・編集のルール

- 新規スキルは `skills/<skill-name>/SKILL.md` を作るだけでよい（`plugin.json` は既定で `skills/` を読む）。
- フロントマター制約（`build_skill_zip.py` が検証）:
  - `name`: 英小文字・数字・ハイフンのみ、64文字以内、ディレクトリ名と一致させる。`anthropic` / `claude` を含めない
  - `description`: 1024文字以内。**何をするか＋いつ使うか（発動する依頼文の例）** を書く。日本語本文＋英語の `Use when ...` を併記する既存の書き方に合わせる
- `SKILL.md` は手順の骨格に絞り、詳細は `references/` に分ける（コンテキスト節約のため）。
- 本文・コメントは日本語。既存スキルの見出し構成・トーンに合わせる。
- `scripts/` と `tools/` の Python は**標準ライブラリのみ**。外部パッケージを追加しない。
- スキルを追加・改名したら次も更新する:
  - `README.md` のスキル一覧表
  - 必要に応じて `plugin.json` / `marketplace.json` の `description`（現状 prompt-architect のみに言及している）
  - 配布内容が変わる場合は `plugin.json` の `version`（SemVer）

## 情報の鮮度に関する方針

- モデル名・バージョン・ベンダー固有の仕様は `references/targets.md` のような専用ファイルに隔離し、**出典URLと参照日**を付ける。
- 原則・型・失敗モードはモデル非依存で書く。モデル名ではなく能力ティア（T0〜T3）で分岐させる。
- ベンダー仕様（claude.ai のアップロード制約など）を更新する場合は、公式ドキュメントで裏取りしてから反映する。

## Git・PR

- `main` へ直接 push しない。作業ブランチ → PR で反映する。
- `dist/`・`__pycache__/` はコミットしない。
- ファイル削除、スキルの改名（利用者の呼び出し名が変わる）、マーケットプレイス名／プラグイン名の変更は、実行前に人間に確認する。
