# general-skills

業務で使える汎用スキル集。

## スキル一覧

| スキル | 概要 |
|---|---|
| [`prompt-architect`](skills/prompt-architect/) | どの生成AI・AIエージェントにも移植できる実務用プロンプトを、ヒアリングなしで一発設計する。9ブロック構成 + 実務アーキタイプ + 能力ティア適合 + 機械リンター。モデル世代が上がるほどプロンプトを「引く」方向に更新する仕組みを内蔵。 |
| [`ryo-product-delivery`](skills/ryo-product-delivery/) | Webアプリ・AI機能・LP・発表資料を、既存コードと実装済み機能の確認から始めて、実装→スマホ/PC表示・ボタン実動作・認証/データ分離・APIキー管理の検証まで一気通貫で仕上げる。安易なAI風デザインを避け、最新の指示とコードを優先する。 |
| [`workspace-setup`](skills/workspace-setup/) | 開いているプロジェクトに、AIエージェントが作業しやすい環境（AGENTS.md / CLAUDE.md の分割、パス限定ルール、作業・検査スキル、読み取り専用の確認役、秘密ファイルの deny、構造検査の Stop hook）を既存設定を壊さずに構築し、検査して報告する。チャットのみの環境ではファイル一式を出力する。 |
| [`work-loop`](skills/work-loop/) | 複数手順の作業を「合格条件→小さく実行→検査→修正→引き継ぎ」で回し、同じ失敗2回・修正3巡で止めて記録を残す。何を作るかは他スキルに任せ、進め方と停止条件だけを扱う。 |
| [`deliverable-check`](skills/deliverable-check/) | 成果物や差分を合格条件で検査し、条件ごとに成功/失敗/未実行/未確認と証拠を報告する。成果物は直さない。 |
| [`deck-sprint`](skills/deck-sprint/) | 提案書・報告資料・プレゼンを、構成案の比較→執筆→事実確認→組版→体裁検査まで一気に仕上げる。pptx / claude.ai の Slides・Docs / HTML に対応。Claude Code では `deck-build` ワークフローを使う。 |

## ワークフロー一覧（Claude Code 専用・プラグインに同梱）

多数のサブエージェントをスクリプトで動かし、複数案の比較や相互検証をする [Dynamic workflows](https://code.claude.com/docs/en/workflows)（参照日 2026-10-05）。
プラグイン導入時は `/general-skills:<名前>` で起動する。Pro プランでも収まるよう、既定の設定での1回あたりのエージェント数を抑えている（下表。修正や `depth: "full"` で増える）。

| ワークフロー | 内容 |
|---|---|
| [`deck-build`](workflows/deck-build.js) | 資料: 構成案の比較 → 執筆 → 事実確認（主張ごとに verified / unverified / refuted）→ 組版（pptx / Slides・Docs 原稿 / HTML）→ 体裁検査。既定5エージェント |
| [`app-design`](workflows/app-design.js) | 難しいアプリの設計: 現状調査 → 優先順位の違う設計案 → 比較して仕様書・設計判断記録・作業分解を作る（コードは書かない）。既定4エージェント |
| [`app-implement`](workflows/app-implement.js) | 承認済み仕様書の実装: 1作業ずつ実装 → 検査 → 修正（同じ失敗2回で停止）→ 正しさ / セキュリティ・データ分離の独立レビュー。既定は作業2件・5エージェント（修正1回ごとに+1） |
| [`verify-fix`](workflows/verify-fix.js) | 指定した検査コマンドが通るまで直す。同じ失敗2回か上限回数（既定3、最大5）で止めて報告。既定で最大4エージェント |

## サブエージェント一覧（プラグインに同梱）

| エージェント | 役割 | ツール |
|---|---|---|
| [`deliverable-reviewer`](agents/deliverable-reviewer.md) | 成果物・差分の独立レビュー | Read / Grep / Glob |
| [`researcher`](agents/researcher.md) | 一次情報中心の調査（出典・取得日・公式/非公式つき） | Read / Grep / Glob / WebSearch / WebFetch |
| [`fact-checker`](agents/fact-checker.md) | 数字・仕様・引用の事実確認（反証を探す立場） | Read / Grep / Glob / WebSearch / WebFetch |
| [`ui-checker`](agents/ui-checker.md) | Playwright でスマホ幅・PC幅の表示確認。コードを変更しないのは指示による約束（Bash を持つため仕組みでは防げない） | Read / Glob / Grep / Bash |

## mod 一覧

Claude Code の画面そのものを拡張する function hooks プラグイン（mods）。

| mod | 概要 |
|---|---|
| [`vibe-deck`](mods/vibe-deck/) | 個人開発者向けHUD。Catppuccin / Tokyo Night / Rosé Pine などの公式パレットで、プロンプト上のバンド（経過時間・ターン・ツール・編集数）、自分の発言行、テーマギャラリー（`/vibe`）を彩り、チャット回答を「結論→根拠→Next →」の読みやすい型に整える。`/plugin install vibe-deck@keyakizakap-skills` |

## インストール

**どのチャットでも使いたい場合は C（claude.ai に登録）が最短。** claude.ai アカウントで有効にしたスキルは、claude.ai のチャットに加え、
Claude Code のクラウドセッション・Cowork・claude.ai でログインしたターミナル（v2.1.273 以降）にも自動で同期される
（[公式: Skills synced from claude.ai](https://code.claude.com/docs/en/skills#how-synced-skills-behave), 参照日 2026-10-05）。
ワークフローとサブエージェントはスキルではないため同期されない。必要なら A のプラグインで入れる。
クラウドセッションではユーザー設定で有効にしたプラグインが読み込まれないため、クラウドで使うリポジトリには
`workspace-setup` スキルで `.claude/workflows/` にワークフローを置く（[公式](https://code.claude.com/docs/en/skills#skills-in-cowork-and-cloud-sessions), 参照日 2026-10-05）。

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
python3 tools/build_skill_zip.py            # skills/ の全スキルを dist/<name>.zip に生成
python3 tools/build_skill_zip.py workspace-setup work-loop deliverable-check   # 指定したものだけ
```

claude.ai → Settings → Capabilities（Features）→ Skills から `dist/<name>.zip` を1つずつアップロードする。

- Pro / Max / Team / Enterprise プランで、**コード実行（ファイルの作成と編集）が有効**であることが前提
- ZIPはスキルフォルダを直下に含む形式で生成される（`prompt-architect/SKILL.md` …）。ビルドスクリプトが `name` の形式・予約語・`description` の長さなど、アップロードが弾かれる条件を事前に検証する
- claude.ai の カスタムスキルは**ユーザー個人単位**。チームで使うには各自がアップロードする
- claude.ai に登録したスキルは Claude Code（クラウド / Cowork / claude.ai ログイン中のターミナル）に同期される。API キー認証のセッション、Bedrock 等では同期されない。Claude API で使う場合は別途登録する（同上, 参照日 2026-10-05）
- 同期されたスキルをローカルのターミナルで使うと、本文中の `@` 参照と `${CLAUDE_PROJECT_DIR}` は展開されない。本リポジトリのスキルはこれらに依存しない書き方にしている

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

## 高度な作業の始め方（Claude Code）

前提: Pro プランは `/config` の Dynamic workflows を有効にする（[公式](https://code.claude.com/docs/en/workflows), 参照日 2026-10-05）。ワークフローは使用量を多く使うため、最初は小さな範囲で試す。

```text
# 資料を一気に仕上げる
deck-build ワークフローで topic="生成AI導入の費用対効果", audience="経営会議", format="pptx" の資料を作って

# 調べ物（組み込みワークフロー）
/deep-research Amazon Bedrock と Vertex AI のエージェント機能の違い

# 難しいアプリ: 設計 → 承認 → 実装
app-design ワークフローで request="チーム単位の請求書承認フロー（権限とデータ分離あり）" を設計して
app-implement ワークフローで spec="docs/spec/invoice-approval.md" を実装して
verify-fix ワークフローで command="npm test" が通るまで直して

# マージ前の深いレビュー（クラウドで複数エージェント。課金あり・下記参照）
/code-review ultra
```

`/code-review ultra`（ultrareview）は research preview。Pro / Max は初回3回まで無料、その後は1回あたり通常 $5〜25 を利用クレジットで支払う
（[公式](https://code.claude.com/docs/en/ultrareview), 参照日 2026-10-05）。課金を伴うため、実行のたびに利用者が判断する。

ワークフローが使えない環境（claude.ai のチャット）では、`deck-sprint`・`ryo-product-delivery`・`work-loop` が同じ手順を順番に行う。

## 開発者向け

```bash
make check                                               # 完了の定義（CI と同じ。tools/check.py）
make validate                                            # claude CLI での検証（CI には無い）
claude plugin validate .claude-plugin/marketplace.json   # マーケットプレイス定義
claude plugin validate .claude-plugin/plugin.json        # プラグイン定義
claude plugin validate skills/                           # スキル本体
claude plugin validate agents/                           # サブエージェント
python3 tools/build_skill_zip.py                         # claude.ai 用ZIPを生成（検証つき）
```

このリポジトリ自体の AI 作業環境（`AGENTS.md`、`.claude/`）と合格条件は [`docs/ai/checks.md`](docs/ai/checks.md) を参照。

スキルを追加するときは `skills/<skill-name>/SKILL.md` を作る。`plugin.json` は既定で `skills/` を読むため、
マニフェストの編集は不要（マーケットプレイスの説明文を更新したい場合のみ触る）。

## 設計上の方針

- **腐る情報と腐らない情報を分離する**: モデル名・バージョン固有の記述は `references/targets.md` にのみ置き、出典と参照日を付ける。原則・型・失敗モードはモデル非依存で書く。
- **モデル名ではなく能力ティアで分岐する**: 名前は陳腐化するが、能力の階段（軽量 / 標準 / 推論内蔵 / 自律エージェント）は残る。未知のモデルは `assets/capability-probe.md` で判定する。
- **世代が上がったら足さずに引く**: 古い世代向けの足場（CoT指示、強い語調、大量の例）を削除してから再測定する。
