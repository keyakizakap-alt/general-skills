---
description: ハーネスの状態確認・一時停止・再開・更新（/harness, /harness off, /harness on, /harness update）
---

`python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/harness_ctl.py" $ARGUMENTS` を実行し、結果を日本語で3〜6行に要約する。

- 引数なし・`status`: 有効/無効、検証結果、進行中と次にやること、未コミット件数を伝える。検証が失敗していれば原因を1行で添え、直すか聞く。
- `off` / `on`: 切り替えた結果を1行で伝える。`off` のときは「この作業コピーだけで、コミットされない」ことも伝える。
- `update`: 作成・更新されたファイルを伝え、フックの変更は次のセッション（または /hooks を開いた後）から有効になると伝える。
- それ以外の引数: 使い方（status / on / off / update）を示す。
