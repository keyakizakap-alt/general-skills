# 作業環境セットアップ報告

実施日: 2026-10-05 / 基準コミット: `b64ff89` / Claude Code 2.1.289 / Linux（クラウドコンテナ）/ bash / Python 3.11.15 / Node 22.22.0

## 採用した構成

| 役割 | ファイル | 方針 |
|---|---|---|
| 共通ルール（正本） | `AGENTS.md`（68行） | ツール非依存。`@import` やスラッシュコマンドを前提にしない |
| Claude の入口 | `.claude/CLAUDE.md` | `@../AGENTS.md` で共通ルールを読み込み、Claude 固有の事項だけを書く |
| パス限定ルール | `.claude/rules/skill-authoring.md`（`skills/**`）、`mod-authoring.md`（`mods/**`）、`japanese-writing.md`（`**/*.md`） | 該当ファイルを扱うときだけ読み込まれる |
| 作業手順 | `.claude/skills/project-work/` | 明示起動専用。同じ失敗2回 / 修正3巡で停止（本プロジェクトの運用上限） |
| 検査手順 | `.claude/skills/project-check/` | 明示起動専用。ファイルは修正しない |
| 確認役 | `.claude/agents/project-reviewer.md` | tools は Read, Grep, Glob のみ |
| 権限 | `.claude/settings.json` | 秘密ファイルの Read / Edit deny のみ。allow は追加していない |
| 構造検査 | `.claude/hooks/check_setup.py` + テスト | Stop hook（timeout 20秒）として登録 |
| 文脈・合格条件 | `docs/ai/context.md`、`docs/ai/checks.md` | 必要なときに読む参照先 |
| 作業記録 | `tasks/active.md`、`tasks/handoff.md` | Git追跡外（ローカルのみ） |
| 成果物置き場 | `outputs/` | 中身はGit追跡外（`.gitkeep` のみ追跡） |

### 入口を `.claude/CLAUDE.md` にした理由

このリポジトリはルートがそのままプラグイン（`.claude-plugin/marketplace.json` の `source: "./"`）。
ルートに `CLAUDE.md` を置くと `claude plugin validate .claude-plugin/plugin.json` が
「プラグインルートの CLAUDE.md はコンテキストとして読まれない」と警告した（実測）。
`./.claude/CLAUDE.md` は公式にプロジェクト指示の配置場所として扱われるため、こちらに置いて警告を解消した。

## 既存との関係

| 区分 | 内容 |
|---|---|
| 既存と重複 | `ryo-product-delivery` の「事実の優先順位・未確認の明記・検証」と共通ルールが重なる → スキルは配布物なので変更せず、AGENTS.md は短い原則だけにした。`tools/build_skill_zip.py` の frontmatter 検証とは重複させず、`check_setup.py` は `.claude/` 側だけを見る |
| そのまま追加 | AGENTS.md / CLAUDE.md、docs/ai、tasks、Rules、Skills、Subagent、settings.json（既存の .claude/ は無かった） |
| 効果が大きい | パス限定ルール（スキルの claude.ai 制約、腐る情報の分離を編集時に自動適用）、合格条件の一覧化（既存の5種類の検査を作業別に整理）、Stop hook による設定破損の検出、読み取り専用の確認役 |
| ついでの改善 | `.claude-plugin/plugin.json` と `marketplace.json` の説明文が「prompt-architect のみ収録」のままだったため、`ryo-product-delivery` を追記 |

## 変更したファイル

- 変更: `.gitignore`（8行追記）、`.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`（説明文のみ）
- 新規: `AGENTS.md`、`.claude/CLAUDE.md`、`.claude/settings.json`、`.claude/rules/*.md`（3）、`.claude/skills/project-{work,check}/SKILL.md`、`.claude/agents/project-reviewer.md`、`.claude/hooks/check_setup.py`、`.claude/hooks/tests/test_check_setup.py`、`docs/ai/*.md`（3）、`outputs/.gitkeep`
- ローカルのみ（Git追跡外）: `tasks/active.md`、`tasks/handoff.md`、`.claude/setup-backup/2026-10-05/`

## 実行した検査と結果

| 検査 | 結果 |
|---|---|
| 変更前ベースライン: validate ×3、build_skill_zip、`claude plugin test mods/vibe-deck`（2 pass） | 成功 |
| `claude plugin validate`（marketplace / plugin / skills / .claude/agents / .claude/skills） | 成功（plugin は `--strict` でも成功） |
| `python3 .claude/hooks/check_setup.py` | 成功（警告0） |
| `python3 -m unittest discover -s .claude/hooks/tests`（16件: 正常、異常、import循環・重複・コード内除外、権限、秘密非出力、再ブロック防止、タイムアウト） | 成功 |
| 登録した hook コマンドをダミー入力で実行 | 成功（出力なし＝通過） |
| 独立レビュー（project-reviewer） | 未実施。このセッションの開始後に作成したため起動対象に含まれない。主担当が観点を変えて自己確認した |

## 未適用・未確認

- **実機での読み込み確認は未実施**。新しいセッションで次を確認すること:
  `/memory`（`.claude/CLAUDE.md` と `AGENTS.md` が読まれているか）、`/hooks`（Stop に1件）、`/agents`（project-reviewer）、`/permissions`（deny 15件）、`/context`、`/project-work` と `/project-check` が `/` メニューに出るか
- **Sandbox**: このコンテナには bubblewrap / socat が無く、有効化していない。ローカルの macOS / Linux / WSL2 で使う場合は `/sandbox` で状態を確認して有効化する（グローバル設定のため本作業では変更しない）。Sandbox は Bash 等のシェルコマンドだけを囲い、Read/Edit などのファイルツール、hooks、MCP サーバーは対象外（公式 sandboxing, 2026-10-05 参照）
- **権限の限界**: Read/Edit deny は Claude のファイルツールと、`cat` などClaude Code が認識するBashコマンドには効くが、`grep -r` のようにファイル名を指定しない読み取りや、Python/Node スクリプト内での読み書きは防げない（公式 permissions）。`.gitignore` や CLAUDE.md の記述はアクセス制御ではない
- **既存の過剰権限**: プロジェクトには無し。ユーザー設定 `~/.claude/settings.json` は空ファイル（構文上は無効なJSON。中身は無く、秘密情報も無し）。変更していない
- **Codex**: 未導入。`AGENTS.override.md` は存在しない。Codex での読み込みは未検証
- **YAML**: frontmatter は簡易パーサーで必須キーのみ検査。完全な構文検証は `claude plugin validate` に依存
- **MCP**: 追加していない
- **Git**: commit / push は行っていない

## 復元手順（今回の差分だけを戻す）

`git reset --hard` / `git clean` は使わない。

```bash
# 変更したファイルを作業前の状態に戻す（バックアップから。git checkout -- <file> でも同じ）
cp .claude/setup-backup/2026-10-05/.gitignore .gitignore
cp .claude/setup-backup/2026-10-05/.claude-plugin/plugin.json .claude-plugin/plugin.json
cp .claude/setup-backup/2026-10-05/.claude-plugin/marketplace.json .claude-plugin/marketplace.json

# 今回新規に作ったものを削除（.claude/ は今回が初作成）
rm -r AGENTS.md docs/ai tasks outputs .claude
rmdir docs 2>/dev/null || true
```

## 追加: どのチャットでも使えるようにした（2026-10-05）

最初のセットアップはこのリポジトリ専用（`.claude/`）だったため、同じ仕組みを配布スキルとして `skills/` に汎用化した。

| 配布物 | 中身 | 使える場所 |
|---|---|---|
| `skills/workspace-setup/` | このセットアップ手順そのもの＋ひな形一式（AGENTS / CLAUDE / settings / Rules / Skills / 確認役 / 検査スクリプト / docs）と仕様メモ（参照日つき） | claude.ai 登録で全環境。チャットのみの環境ではファイル一式を出力 |
| `skills/work-loop/` | 合格条件→小さく実行→検査→修正→引き継ぎ、停止条件（同じ失敗2回 / 3巡） | 同上 |
| `skills/deliverable-check/` | 証拠つきの検品（成果物は直さない）。合格条件が無ければ種類別の既定観点を使う | 同上 |
| `agents/deliverable-reviewer.md` | 読み取り専用の確認役（Read / Grep / Glob） | プラグイン導入時のみ（スキルではないので claude.ai から同期されない） |

- 既存の claude.ai スキル `japanese-productivity-engineering-assistant`（作業種別ごとの型）と重ならないよう、`work-loop` は進め方・停止条件・証拠だけを扱う
- `check_setup.py` は設定ファイル（`.claude/hooks/check_setup.json`）方式の汎用版にし、配布物とこのリポジトリのコピーが同一であることをテストで検査する
- 配布スキルの frontmatter は claude.ai で確実に通る `name` と `description` だけにした。そのため `disable-model-invocation` を付けず、自動起動前提で description の起動条件を絞った
- ひな形からゼロのプロジェクトを組み立てる e2e テストで、①ひな形のコメント内の `@` が import と誤判定される、②日本語の句読点がパスに含まれる、の2件を発見・修正した
- README の「スキルは surface 間で同期しない」は現行仕様と異なるため訂正した（公式 skills, 参照日 2026-10-05）

追加分の復元: `rm -r skills/workspace-setup skills/work-loop skills/deliverable-check agents` と、README / `.claude-plugin/` は `git checkout -- README.md .claude-plugin/`（説明文の最初の修正も戻る）。

## 再実行時の扱い

同じ手順を再実行しても増えないように、Stop hook は `check_setup.py` を含む登録が無い場合だけ追加し、
`.gitignore` は既存行を確認し、無い行だけを追記する（今回も既存行との重複なし）。`check_setup.py` は Stop hook の重複、
CLAUDE.md の二重入口、AGENTS.md の重複 import を検出してブロックする。
