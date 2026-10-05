---
paths:
  - "mods/**"
---

# mod の作法（`mods/` を編集するとき）

- function hooks（mods）は early access。API は Claude Code のリリース間で変わりうるため、記憶ではなくインストール済み版の型定義（`types/`）と公式資料で確認してから書く。
- 変更後は `claude plugin test mods/<name>` を実行し、結果を報告する。テストが無い挙動を追加したら `tests/` にテストを足す。
- README の「検証済みバージョン」は、実際に validate / test を通したバージョンだけを書く。
- テーマの配色など外部由来の値は、公式パレットの出典を README に残す。独自の値は独自と明記する。
- `mods/*/tsconfig.json` と `mods/*/.claude-plugin/types/` はGit追跡外（`.gitignore` 済み）。コミット対象に含めない。
