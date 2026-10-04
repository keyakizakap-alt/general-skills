---
name: agent-harness-kit
description: リポジトリにAIコーディングエージェント用の「ハーネス」を入れる。AGENTS.md/CLAUDE.md（コンテキスト設計）、完了の定義となる検証コマンド、Claude Code フック（編集後の自動検証・検証が通るまで終わらせない Stop ゲート・セッション開始時の進捗復元）、進捗ファイル、レビュー用サブエージェント、CI を一式で導入する。「ハーネスを入れて」「ハーネスエンジニアリング」「ループエンジニアリング」「コンテキストエンジニアリング」「エージェントが自分で検証して直すようにしたい」「Claude Code/Codex 向けに開発環境を整えて」「CLAUDE.md/AGENTS.md を作って」といった依頼で使う。Use when setting up a repository so coding agents can verify and correct their own work across sessions.
---

# agent-harness-kit

**目的**: エージェントが「自分で確かめ、自分で直し、次のセッションへ引き継げる」状態をリポジトリに作る。
モデルを賢くするのではなく、モデルの周り（指示・検証・フィードバック・記憶）を整える。考え方と出典は `references/concepts.md`。

## 導入の手順

### 1. 完了の定義を決める（最重要）

ハーネスの中心は **終了コード0/非0を返す1本の検証コマンド**。フック・CI・レビューはすべてこれを呼ぶ。

- `install.py` が既存の仕組みから自動判定する（Makefile の check/test → package.json の check/test → go → cargo → pytest）。判定結果が妥当かを確認し、違えば `--check` で指定する。
- 速さの目安: 編集のたびに走るので **数秒〜30秒**。重いE2Eは CI 側に分ける。
- なければ作る。最低限: 構文チェック（lint / typecheck）＋ 単体テスト ＋ リポジトリ固有の整合性チェック（設定とドキュメントのずれなど）。
- 決められない（テストが一切なく、何を合格とすべきか不明）場合だけユーザーに聞く。

### 2. まず dry-run で予定を見せる

```bash
python3 <このスキル>/scripts/install.py --dry-run          # カレントディレクトリが導入先
```

既存ファイルは上書きしない（`SKIP` と出る）。`.claude/settings.json` は既存の設定にフックと権限を**追記マージ**する。
`UPDATE` が出るファイルがある場合は、内容をユーザーに伝えてから実行する。

### 3. 実行して中身を埋める

```bash
python3 <このスキル>/scripts/install.py [--check "<検証コマンド>"] [--ci]
```

- `AGENTS.md` の `<...>` を、コードを読んで埋める。**短く**: 毎回必要なことだけ。詳細はパスで指す。
- 既に `CLAUDE.md` がある場合は上書きされない。先頭に `@AGENTS.md` を足すか、内容を AGENTS.md に寄せる（Claude Code 以外のエージェントも読めるようにするため）。
- `--ci` は GitHub Actions を使っている場合だけ付ける。

このスキルのファイルが手元にない環境では、clone せずに1行で同じことができる（Python 3 と git か curl が必要）:

```bash
curl -fsSL https://raw.githubusercontent.com/keyakizakap-alt/general-skills/main/tools/install-harness.sh | sh -s -- --dry-run
```

### 4. 動作を確かめる

```bash
echo '{}' | CLAUDE_PROJECT_DIR=$PWD python3 .claude/hooks/session_start.py       # 進捗と検証結果が出る
echo '{"session_id":"t","stop_hook_active":false}' | CLAUDE_PROJECT_DIR=$PWD python3 .claude/hooks/stop_gate.py
```

フックは次のセッション（または `/hooks` を開いたあと）から有効になる。

## 入るもの

| ファイル | 役割 | 考え方 |
|---|---|---|
| `AGENTS.md` + `CLAUDE.md`(`@AGENTS.md`) | 毎回読む最小限の指示。完了の定義・進め方・禁止事項 | コンテキスト |
| `.claude/harness.json` | 検証コマンド・差し戻し上限などの設定 | ハーネス |
| `.claude/hooks/session_start.py` | 開始時に PROGRESS.md・git status・検証結果を注入 | コンテキスト（外部記憶） |
| `.claude/hooks/post_edit.py` | Edit/Write の直後に検証し、失敗なら即差し戻す | ループ（イベント駆動） |
| `.claude/hooks/stop_gate.py` | 検証が通るまで終わらせない。差し戻しは上限回数まで | ループ＋安全装置 |
| `.claude/settings.json` | 上記フックの登録、危険操作の deny | ハーネス（制約） |
| `PROGRESS.md` | セッションをまたぐ進捗メモ | コンテキスト（外部記憶） |
| `.claude/hooks/harness_ctl.py` | 状態確認・一時停止・再開・更新の入口（`/harness` の実体。ターミナルからも使える） | 運用 |
| `.claude/commands/next.md` | `/next` で「次にやること」を1つ進め、検証・引き継ぎまで | ループ（1手ずつ前進） |
| `.claude/commands/harness.md` | `/harness [status\|on\|off\|update]` | 運用 |
| `.claude/agents/reviewer.md` | 実装者と分けた読み取り専用レビュアー | 生成と評価の分離 |
| `.claude/commands/handoff.md` | `/handoff` で検証→PROGRESS 更新→引き継ぎ | ループの区切り |
| `.github/workflows/check.yml`（任意） | PR ごとに同じ検証を実行 | ハーネス（検証） |

配布物の実体は `assets/hooks/`（フック本体）と `assets/templates/`（雛形）。`scripts/install.py` がこれらをコピー・マージする。

## 日々の使い方（導入後にユーザーへ伝える）

- `/next` — 次の作業を1つ進めて検証・引き継ぎまで。`/next <やること>` で指定
- `/harness` — 状態確認。`off` で一時停止（作業コピー単位・コミットされない）、`on` で再開、`update` で更新
- `/handoff` — 途中で区切って PROGRESS.md を更新
- 終了前フックは、ファイルを変えたのに進捗ファイルが未更新なら1回だけ更新を促す（`remind_progress: false` で無効）

## 運用の原則

- **検証は1本に集約する**。フック・CI・人間が同じコマンドを使うので、「ローカルでは通るのに」が起きない。
- **差し戻しには上限を置く**（既定3回）。上限に達したら止まり、原因をユーザーに報告する。検証を無効化して通すのは禁止。
- **指示書は増やすより削る**。エージェントが同じ失敗を繰り返したら、指示を足す前に「検証で機械的に検出できないか」を先に考える。
- **進捗はファイルに書く**。チャットの記憶に頼らない。`/handoff` で区切る。
- フックは Python 3 標準ライブラリだけで動く。`python3` がない環境（Windows の一部など）では settings.json の `python3` を `python` に変える。
