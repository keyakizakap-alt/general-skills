# general-skills

業務で使える汎用スキル集。

## スキル一覧

| スキル | 概要 |
|---|---|
| [`anti-ai-design`](skills/anti-ai-design/) | UI・LP・アプリ画面が「いかにもAIが作った見た目」（紫グラデ・Inter・角丸カード3枚・絵文字アイコン）になるのを防ぐ。実装前に5つの決定を固定し、最後に兆候を機械検査する。 |
| [`prompt-architect`](skills/prompt-architect/) | どの生成AI・AIエージェントにも移植できる実務用プロンプトを、ヒアリングなしで一発設計する。9ブロック構成 + 実務アーキタイプ + 能力ティア適合 + 機械リンター。モデル世代が上がるほどプロンプトを「引く」方向に更新する仕組みを内蔵。 |

## インストール

### A. Claude Code — プラグインとして入れる

このリポジトリはプラグインマーケットプレイスを兼ねている。Claude Code のセッション内で:

```
/plugin marketplace add keyakizakap-alt/general-skills
/plugin install general-skills@keyakizakap-skills
```

インストール後は `/prompt-architect` `/anti-ai-design` で呼び出せる（依頼文が description に合致すれば自動でも起動する）。
更新は `/plugin marketplace update keyakizakap-skills`。

> **注意**: `/plugin` はローカルの Claude Code（CLI・デスクトップアプリ）で使う。
> Claude Code on the web（リモートセッション）では利用できないため、その場合は B または C を使う。

### B. Claude Code — ファイルを直接置く

```bash
git clone https://github.com/keyakizakap-alt/general-skills.git ~/src/general-skills

# 個人用（全プロジェクトで有効）
mkdir -p ~/.claude/skills
ln -s ~/src/general-skills/skills/prompt-architect ~/.claude/skills/prompt-architect

# または プロジェクト用（コミットすればチーム全員が使える）
mkdir -p .claude/skills && cp -r ~/src/general-skills/skills/* .claude/skills/
```

このリポジトリ自体には `.claude/skills/` から `skills/` へのシンボリックリンクを置いてある。
そのため**このリポジトリをクローンして作業する場合は、設定なしで両スキルが有効になる**
（Claude Code on the web でも同様）。

### C. claude.ai（Web / デスクトップ / モバイル）

ZIPを作ってアップロードする。

```bash
python3 tools/build_skill_zip.py                    # 全スキルのZIPを dist/ に生成
python3 tools/build_skill_zip.py anti-ai-design     # 個別に生成
```

claude.ai → Settings → Capabilities（Features）→ Skills から `dist/*.zip` をアップロードする。

- Pro / Max / Team / Enterprise プランで、**コード実行（ファイルの作成と編集）が有効**であることが前提
- ZIPはスキルフォルダを直下に含む形式で生成される（`prompt-architect/SKILL.md` …）。ビルドスクリプトが `name` の形式・予約語・`description` の長さなど、アップロードが弾かれる条件を事前に検証する
- claude.ai の カスタムスキルは**ユーザー個人単位**。チームで使うには各自がアップロードする
- **スキルは surface 間で同期しない**。Claude Code / claude.ai / API はそれぞれ別に登録する

## 使い方

各スキルは `SKILL.md` に手順、`references/` に詳細、`assets/` にテンプレート、`scripts/` に検証ツールを持つ。
`SKILL.md` の `description` に合致する依頼をすれば自動で読み込まれ、`/prompt-architect` で明示的にも呼び出せる。

呼び出される例:

`prompt-architect`
- 「問い合わせメールを自動分類するプロンプトを作って」
- 「議事録をAIに書かせたい。指示文を用意して」
- 「このプロンプト、精度が安定しないので改善して」
- 「モデルを新しくしたら出力が変わった。プロンプトを見直したい」

`anti-ai-design`
- 「社内ツールの管理画面を作って」
- 「このLP、AIが作ったみたいで嫌なんだけど」
- 「もっと個性を出して」「量産型に見える」

```bash
# プロンプトの機械チェック
python3 skills/prompt-architect/scripts/lint_prompt.py path/to/prompt.txt

# 能力ティア適合（T2以上では、旧世代向けの足場が残っていないかを検出）
python3 skills/prompt-architect/scripts/lint_prompt.py path/to/prompt.txt --tier T2
```

## 開発者向け

```bash
claude plugin validate .claude-plugin/marketplace.json   # マーケットプレイス定義
claude plugin validate .claude-plugin/plugin.json        # プラグイン定義
claude plugin validate skills/                           # スキル本体
python3 tools/build_skill_zip.py                         # claude.ai 用ZIPを生成（検証つき）
```

スキルを追加するときは `skills/<skill-name>/SKILL.md` を作り、`.claude/skills/<skill-name>` から
シンボリックリンクを張る（`ln -sfn ../../skills/<skill-name> .claude/skills/<skill-name>`）。
`plugin.json` は既定で `skills/` を読むため、マニフェストの編集は不要。

## 設計上の方針

- **腐る情報と腐らない情報を分離する**: モデル名・バージョン固有の記述は `references/targets.md` にのみ置き、出典と参照日を付ける。原則・型・失敗モードはモデル非依存で書く。
- **モデル名ではなく能力ティアで分岐する**: 名前は陳腐化するが、能力の階段（軽量 / 標準 / 推論内蔵 / 自律エージェント）は残る。未知のモデルは `assets/capability-probe.md` で判定する。
- **世代が上がったら足さずに引く**: 古い世代向けの足場（CoT指示、強い語調、大量の例）を削除してから再測定する。
- **品質は決定した項目の数で決まる**: プロンプトもUIも、「決めなかった箇所」がモデルのデフォルト（＝訓練データの中央値）で埋まる。各スキルは実装前に決定を固定させ、最後に機械検査する同じ構造を持つ。
