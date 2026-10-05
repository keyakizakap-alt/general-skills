# 詳細手順

`SKILL.md` の各手順で迷ったときに読む。

## 変更の境界

- 競合する箇所だけ保留し、独立して安全に作れる部分は進める
- 外部を指すシンボリックリンクには書き込まない
- 復元対象は今回の差分だけ。バックアップには機密を転記しない。ログや共有文書に秘密を書かない
- この依頼の許可に含めない: ファイルの移動・削除、大規模な再編、グローバル設定（`~/.claude/`）の変更、パッケージ追加、外部送信・公開、commit / push、本番操作、認証、課金、外部サービスへの登録

## 既存の指示書がある場合の統合

| 現状 | 対応 |
|---|---|
| CLAUDE.md だけある | 共通部分を AGENTS.md に移し、CLAUDE.md は入口として残して `@AGENTS.md` を足す。Claude 固有の記述は CLAUDE.md に残す |
| AGENTS.md だけある | AGENTS.md はそのまま正本にし、短い CLAUDE.md を足して import する |
| 両方ある | 重複を探して AGENTS.md に寄せる。既存の import を確認し、循環と二重記述を作らない |
| `.claude/CLAUDE.md` がある | そちらを入口として使い、相対パスを `@../AGENTS.md` に合わせる。入口を増やさない |
| `AGENTS.override.md` がある（Codex 用） | Codex ではこちらが優先される。内容と食い違いを報告する。Codex が無ければ「動作未確認」と書く |

AGENTS.md には Claude 専用の `@import` やスラッシュコマンド前提の指示を書かない。

## 共通ルールに必ず入れる項目

ひな形 `assets/AGENTS.template.md` の「共通ルール」節。既存ルールと重複するものは足さない。

## フォルダ構成

同等の既存構成があればそれを使う。無ければ必要分だけ作る。

| パス | 内容 | Git |
|---|---|---|
| `docs/ai/context.md` | 目的、利用者、参照資料、確定事項と未確認事項 | 追跡 |
| `docs/ai/checks.md` | 作業別の合格条件、実在する検査コマンド、手動確認 | 追跡 |
| `docs/ai/setup-report.md` | 変更、検査結果、未適用、復元手順 | 追跡 |
| `tasks/active.md`、`tasks/handoff.md` | 現在の作業と引き継ぎ | 公開リポジトリなら追跡外を推奨 |
| `outputs/` | 既存の保存先が無い場合の成果物置き場 | 用途次第 |

既存の原本を移動・上書きしない。

## Rules の選び方

- 文章制作: 文体・出典・表記（`assets/rules/ja-writing.md`）
- 開発: 既存の実装規約（Lint 設定や README から読み取れる範囲だけ。推測で規約を作らない）
- 共通ルールを複製しない。細かく分けただけの常時読み込みルールを量産しない

## Hook のテスト手順

本物の設定を使わず、一時ディレクトリに管理対象をコピーして `--root` で検査する。

```bash
tmp=$(mktemp -d) && cp -r CLAUDE.md AGENTS.md .claude .gitignore "$tmp"/ 2>/dev/null
# 正常: 何も出力せず終了コード0
echo '{"stop_hook_active": false}' | python3 .claude/hooks/check_setup.py --hook --root "$tmp"
# 異常: 設定を壊すと decision: block が出る
echo '}' >> "$tmp/.claude/settings.json"
echo '{"stop_hook_active": false}' | python3 .claude/hooks/check_setup.py --hook --root "$tmp"
# 再ブロック防止: stop_hook_active が true なら出力なし
echo '{"stop_hook_active": true}' | python3 .claude/hooks/check_setup.py --hook --root "$tmp"
# タイムアウト: 打ち切られた場合は 0/2 以外の終了コード（非ブロッキング）で、合格扱いにならない
echo '{}' | timeout 0.001 python3 .claude/hooks/check_setup.py --hook --root "$tmp"; echo "exit=$?"
rm -r "$tmp"
```

Stop hook の登録例（`.claude/settings.json` の既存 `hooks.Stop` 配列に追加する）:

```json
{"hooks": [{"type": "command",
            "command": "python3 \"${CLAUDE_PROJECT_DIR}/.claude/hooks/check_setup.py\" --hook",
            "timeout": 20,
            "statusMessage": "設定ファイルの構造を検査中"}]}
```

Windows ネイティブで `python3` が無い場合は `python` か `py -3` に置き換え、動作を確かめてから登録する。

## 報告に必ず書く限界

- `.gitignore` や CLAUDE.md の記述はアクセス制御ではない
- ファイル権限のルールだけでは任意のシェル処理を完全には防げない。Sandbox もファイルツール・Hooks・MCP は囲わない
- MCP は自動で追加しない。用途、必要な権限、接続先、送信されるデータが分かってから提案する
- 新規 Hook は設定の構造検査専用で、成果物の品質検査ではない
