# AGENTS.md

AIコーディングエージェント（Claude Code / Codex / Cursor など）向けの作業指示。人間向けの説明は README.md。
**短く保つ**: ここには毎回必要なことだけを書き、詳細はファイルパスで指して必要なときに読ませる。

## このリポジトリ

- 目的: 業務で使える汎用スキル集。Claude Code プラグイン兼マーケットプレイス、および claude.ai 用スキルZIPとして配布する。
- `skills/<name>/` — 配布するスキル本体。`SKILL.md`（手順）＋ `references/`（詳細）＋ `assets/`（雛形）＋ `scripts/`（検証ツール）
- `.claude-plugin/` — プラグインとマーケットプレイスの定義
- `tools/check.py` — 全体の検証。`tools/build_skill_zip.py` — claude.ai 用ZIPの生成
- `.claude/` — このリポジトリ自身のハーネス（`skills/agent-harness-kit` から導入。フック本体は直接編集しない）

## 完了の定義

- `make check`（= `python3 tools/check.py`）が終了コード0で通ること。通らない状態で「完了」と報告しない。
- 新しいチェックが必要になったら `tools/check.py` の `CHECKS` に足す。指示書に注意書きを足すより先に、機械的に検出できないかを考える。

## 日々の使い方（Claude Code）

- `/next` — PROGRESS.md の「次にやること」を1つ進め、検証・引き継ぎまで済ませる。`/next <やること>` で指定もできる
- `/harness` — 状態確認。`/harness off` で一時停止（この作業コピーだけ）、`on` で再開、`update` で最新版に更新
- `/handoff` — 作業を区切って PROGRESS.md を更新する

Claude Code 以外では `make status` / `python3 .claude/hooks/harness_ctl.py [status|on|off|update]` が同じ操作になる。

## 進め方

1. 着手前に `PROGRESS.md` を読み、続きかどうかを判断する。
2. 1回の作業単位は小さく（1スキル・1修正）。終わるたびに `make check` を通す。
3. 作業を終える前に `PROGRESS.md` を更新する（何をした／次に何をするか／未解決の問題）。`/handoff` で一括実行できる。
4. 設計判断をしたら `docs/decisions/` に短く残す（何を選び、何を捨てたか、なぜか）。

## スキルを追加・変更するとき

- `skills/<name>/SKILL.md` を作り、README のスキル一覧表に1行足す（検証が不足を検出する）。
- `SKILL.md` は500行以内。詳細は `references/` に分け、SKILL.md からパスで指す。
- モデル名・バージョン・機能ステータスなど腐る情報は、出典URLと参照日を付けて1か所にまとめる。
- フック本体を変えるときは `skills/agent-harness-kit/assets/hooks/` を編集し、`make harness` で `.claude/hooks/` に反映する。

## 禁止・要確認

- 削除・上書き・force push・本番/課金/外部公開を伴う操作は、実行前にユーザーへ確認する。
- APIキー・トークン等をコミットしない（検証が代表的な形式を検出する）。
- 検証を通すためにテストやチェックを無効化・削除しない。
