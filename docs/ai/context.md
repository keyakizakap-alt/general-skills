# プロジェクト文脈

AIエージェントが作業前に必要に応じて読む背景情報。常時読み込みではない。

## 目的

業務で繰り返し使える汎用スキルと Claude Code 用 mod を作り、次の3経路で配布する。

1. Claude Code プラグイン / マーケットプレイス（`.claude-plugin/`、マーケットプレイス名 `keyakizakap-skills`）
2. ファイル直接配置（`~/.claude/skills/` またはプロジェクトの `.claude/skills/`）
3. claude.ai 用ZIP（`tools/build_skill_zip.py` → `dist/`）

## 利用者・読者

- リポジトリ所有者（keyakizakap-alt）本人：資料作成、リサーチ、アプリ開発、Webサイト作成、エージェント構築を日本語で行う
- 公開リポジトリのため、第三者もプラグインとして導入しうる

## 参照すべき資料

| 資料 | 内容 |
|---|---|
| `README.md` | 収録物、インストール手順、設計方針（腐る情報の分離、能力ティア、足さずに引く） |
| `skills/prompt-architect/references/targets.md` | モデル・ベンダー固有の情報（出典・参照日つき） |
| `mods/vibe-deck/README.md` | mod の挙動と検証済みバージョン |
| `docs/ai/checks.md` | 合格条件と検査コマンド |

## 確定事項（2026-10-05 にリポジトリで確認）

- 収録スキル: `prompt-architect`、`ryo-product-delivery`、`workspace-setup`、`work-loop`、`deliverable-check`、`deck-sprint`
- 収録ワークフロー（プラグインのみ・Claude Code 専用）: `deck-build`、`app-design`、`app-implement`、`verify-fix`
- 収録サブエージェント（プラグインのみ）: `deliverable-reviewer`、`researcher`、`fact-checker`、`ui-checker`
- 利用者のプラン: Pro（2026-10-05 に利用者から回答）。Pro でのワークフローの扱いは `skills/workspace-setup/references/spec-notes.md`（出典つき）
- 資料の主な形式: pptx、claude.ai の Slides / Docs、HTML。アプリの技術スタックは案件ごとに異なる
- 収録 mod: `vibe-deck`（function hooks は early access。README に 2.1.289 で検証済みと記載）
- `plugin.json` は既定で `skills/` を読む。マーケットプレイスは `general-skills`（`./`）と `vibe-deck`（`./mods/vibe-deck`）の2プラグイン
- 検査: `tools/check.py`（CI: `.github/workflows/check.yml`）、`claude plugin validate`、`claude plugin test`、`tools/build_skill_zip.py`

## 未確認事項

- claude.ai のチャットで、スキルの frontmatter（`name` と `description` 以外）がどう扱われるか。配布スキルは2項目だけにしている
- claude.ai のチャットで、利用者がスキル名を指定して明示起動できるか（配布スキルは自動起動前提で description を書いている）
- ワークフローの本物の実行結果（このリポジトリでは模擬実行のみ。Workflow ツールはセッションで未使用）
- 第三者の利用状況・利用者数
- vibe-deck が 2.1.289 以外の Claude Code バージョンで動くか
- `.claude/` 配下のスキル・エージェントはこのリポジトリ専用。他プロジェクトへは `skills/workspace-setup` のひな形から作る（プラグインの構成要素ではないため、インストール先では読み込まれない想定。未検証）
