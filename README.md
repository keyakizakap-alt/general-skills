# general-skills

業務で使える汎用スキル集。

## スキル一覧

| スキル | 概要 |
|---|---|
| [`prompt-architect`](skills/prompt-architect/) | どの生成AI・AIエージェントにも移植できる実務用プロンプトを、ヒアリングなしで一発設計する。9ブロック構成 + 実務アーキタイプ + 能力ティア適合 + 機械リンター。モデル世代が上がるほどプロンプトを「引く」方向に更新する仕組みを内蔵。 |
| [`agent-harness-kit`](skills/agent-harness-kit/) | リポジトリにAIコーディングエージェント用のハーネスを入れる。AGENTS.md/CLAUDE.md、完了の定義となる検証コマンド、Claude Code フック（編集後の自動検証・検証が通るまで終わらせない Stop ゲート・進捗の復元）、PROGRESS.md、レビュー用サブエージェント、CI を、既存ファイルを壊さずに一式導入する。 |
| [`ryo-product-delivery`](skills/ryo-product-delivery/) | Webアプリ・AI機能・LP・発表資料を、既存コードと実装済み機能の確認から始めて、実装→スマホ/PC表示・ボタン実動作・認証/データ分離・APIキー管理の検証まで一気通貫で仕上げる。安易なAI風デザインを避け、最新の指示とコードを優先する。 |

## インストール

### A. Claude Code — プラグインとして入れる（推奨）

このリポジトリはプラグインマーケットプレイスを兼ねている。Claude Code のセッション内で:

```
/plugin marketplace add keyakizakap-alt/general-skills
/plugin install general-skills@keyakizakap-skills
```

インストール後は `/prompt-architect` で呼び出せる（依頼文が description に合致すれば自動でも起動する）。
更新は `/plugin marketplace update keyakizakap-skills`。

### B. Claude Code — ファイルを直接置く

```bash
git clone https://github.com/keyakizakap-alt/general-skills.git ~/src/general-skills

# 個人用（全プロジェクトで有効）
mkdir -p ~/.claude/skills
ln -s ~/src/general-skills/skills/prompt-architect ~/.claude/skills/prompt-architect

# または プロジェクト用（コミットすればチーム全員が使える）
mkdir -p .claude/skills && cp -r ~/src/general-skills/skills/prompt-architect .claude/skills/
```

### C. claude.ai（Web / デスクトップ / モバイル）

ZIPを作ってアップロードする。

```bash
python3 tools/build_skill_zip.py            # dist/prompt-architect.zip を生成
```

claude.ai → Settings → Capabilities（Features）→ Skills から `dist/prompt-architect.zip` をアップロードする。

- Pro / Max / Team / Enterprise プランで、**コード実行（ファイルの作成と編集）が有効**であることが前提
- ZIPはスキルフォルダを直下に含む形式で生成される（`prompt-architect/SKILL.md` …）。ビルドスクリプトが `name` の形式・予約語・`description` の長さなど、アップロードが弾かれる条件を事前に検証する
- claude.ai の カスタムスキルは**ユーザー個人単位**。チームで使うには各自がアップロードする
- **スキルは surface 間で同期しない**。Claude Code / claude.ai / API はそれぞれ別に登録する

## 使い方

各スキルは `SKILL.md` に手順、`references/` に詳細、`assets/` にテンプレート、`scripts/` に検証ツールを持つ。
`SKILL.md` の `description` に合致する依頼をすれば自動で読み込まれ、`/prompt-architect` で明示的にも呼び出せる。

呼び出される例:

- 「問い合わせメールを自動分類するプロンプトを作って」
- 「議事録をAIに書かせたい。指示文を用意して」
- 「このプロンプト、精度が安定しないので改善して」
- 「経費チェックのエージェントのシステムプロンプトを設計して」
- 「モデルを新しくしたら出力が変わった。プロンプトを見直したい」

```bash
# プロンプトの機械チェック
python3 skills/prompt-architect/scripts/lint_prompt.py path/to/prompt.txt

# 能力ティア適合（T2以上では、旧世代向けの足場が残っていないかを検出）
python3 skills/prompt-architect/scripts/lint_prompt.py path/to/prompt.txt --tier T2
```

## 開発者向け

このリポジトリ自体も `agent-harness-kit` で整備している（AIエージェント向けの指示は [`AGENTS.md`](AGENTS.md)）。

```bash
make check     # 完了の定義。編集後・終了前のフックと CI も同じものを実行する
make zip       # claude.ai 用ZIPを dist/ に生成
make harness   # agent-harness-kit の最新版をこのリポジトリに入れ直す
```

```bash
claude plugin validate .claude-plugin/marketplace.json   # マーケットプレイス定義
claude plugin validate .claude-plugin/plugin.json        # プラグイン定義
claude plugin validate skills/                           # スキル本体
python3 tools/build_skill_zip.py                         # claude.ai 用ZIPを生成（検証つき）
```

スキルを追加するときは `skills/<skill-name>/SKILL.md` を作る。`plugin.json` は既定で `skills/` を読むため、
マニフェストの編集は不要（マーケットプレイスの説明文を更新したい場合のみ触る）。

## 設計上の方針

- **腐る情報と腐らない情報を分離する**: モデル名・バージョン固有の記述は `references/targets.md` にのみ置き、出典と参照日を付ける。原則・型・失敗モードはモデル非依存で書く。
- **モデル名ではなく能力ティアで分岐する**: 名前は陳腐化するが、能力の階段（軽量 / 標準 / 推論内蔵 / 自律エージェント）は残る。未知のモデルは `assets/capability-probe.md` で判定する。
- **世代が上がったら足さずに引く**: 古い世代向けの足場（CoT指示、強い語調、大量の例）を削除してから再測定する。
