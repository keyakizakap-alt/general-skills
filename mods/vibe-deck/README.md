# vibe-deck — 個人開発者向け Claude Code mod

Claude Code の画面とチャットを、開発者コミュニティで定番の配色テーマで整える mod（function hooks プラグイン）。

## 何が変わるか

| 場所 | 変化 |
|---|---|
| プロンプト上のバンド | `◆ VIBE` バッジ ＋ 状態（working / ready）・経過時間・ターン数・ツール呼び出し数・編集数・直前ターンの所要時間。幅に応じて項目を自動で間引く |
| 自分の発言行 | テーマのアクセント色の縦バー `▍` 付きで表示（ctrl+o の展開表示では元の表示） |
| チャット回答 | system prompt に回答スタイルを追加：結論を太字1行で先頭 → 根拠、短い見出し、6項目程度までの箇条書き、比較は表、`✅ ⚠️ ❌` は控えめ、残作業があれば `Next →` で締める |
| ステータスライン | 現在のテーマ名 |
| トースト | 90秒を超えたターンの完了時に `✦ Done in 2m 05s` |
| テーマギャラリー | `/vibe` でペインを開き、スウォッチを見ながら 1〜5 キーで切替、b / c / p で各機能を ON/OFF |

テーマと設定は `$.store` に保存され、次のセッションでも引き継がれる。

## テーマ

| id | 名前 | 出典 |
|---|---|---|
| `mocha` | Catppuccin Mocha（既定） | 公式 [catppuccin/palette](https://github.com/catppuccin/palette) |
| `tokyo` | Tokyo Night | 公式 [folke/tokyonight.nvim](https://github.com/folke/tokyonight.nvim) |
| `rose` | Rosé Pine | 公式 [rose-pine/palette](https://github.com/rose-pine/palette) |
| `ember` | Ember | 本 mod 独自の暖色パレット |
| `latte` | Catppuccin Latte | 公式 [catppuccin/palette](https://github.com/catppuccin/palette)（明るい背景のターミナル向け） |

## コマンド

```
/vibe                 テーマギャラリーを開く
/vibe theme <id>      テーマ切替（mocha, tokyo, rose, ember, latte）
/vibe next            次のテーマへ
/vibe band on|off     バンドの表示
/vibe chat on|off     回答スタイルの追加
/vibe prompts on|off  自分の発言行の装飾
/vibe reset           セッションのカウンターをリセット
```

## インストール

```
/plugin marketplace add keyakizakap-alt/general-skills
/plugin install vibe-deck@keyakizakap-skills
```

ローカルで試すだけなら `claude --plugin-dir ./mods/vibe-deck`。

## 前提と制約

- Claude Code の function hooks（mods）は **early access** で、API はリリース間で変わりうる。2.1.289 で検証済み（`claude plugin validate` / `claude plugin test` / `tsc`）。
- 色は 24bit カラー（truecolor）対応ターミナルで意図どおりに出る。明るい背景なら `latte` を使う。
- `chat` を ON にすると system prompt に数行が加わる（セッション側、プロンプトキャッシュ境界の後ろ）。不要なら `/vibe chat off`。

## 開発

```bash
claude plugin validate mods/vibe-deck
claude plugin test mods/vibe-deck
```
