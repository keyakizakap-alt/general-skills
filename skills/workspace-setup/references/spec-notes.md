# 仕様メモ（参照日 2026-10-05 / すべて公式 code.claude.com/docs）

腐る情報。使う前に可能なら最新版を確認し、食い違えば公式を優先してこのメモを更新する。
確認時の Claude Code バージョン: 2.1.289。

## 指示書（https://code.claude.com/docs/en/memory）

- プロジェクト指示は `./CLAUDE.md` または `./.claude/CLAUDE.md`。個人用は `./CLAUDE.local.md`（gitignore 推奨）
- `@path` で import。相対パスは import を書いたファイル基準。再帰は最大4ホップ。コードスパンとフェンスコード内は import されない。パスに空白がある場合は `\ ` でエスケープ
- import したファイルも起動時に読み込まれるため、コンテキスト量は減らない。CLAUDE.md は200行未満が目安
- プロジェクト外を指す import は、初回に承認ダイアログが出る
- AGENTS.md: CLAUDE.md / .claude/CLAUDE.md / CLAUDE.local.md のどれも無いときだけ直接読まれる（v2.1.277 以降）。CLAUDE.md がある場合は `@AGENTS.md` で import する。`AGENTS.override.md`、`AGENTS.local.md` は Claude Code では読まれない
- `.claude/rules/*.md`: frontmatter の `paths`（glob のリスト）で対象を限定。`paths` 無しは常時読み込み
- 確認: `/memory`。指示の監査: `/doctor prompt-audit`（v2.1.283 以降）

## スキル（https://code.claude.com/docs/en/skills）

- プロジェクト用は `.claude/skills/<name>/SKILL.md`。`name` は省略時フォルダ名
- `disable-model-invocation: true` で利用者の明示起動専用。`allowed-tools` は起動したターンで承認なしに使えるツールを増やす
- `$ARGUMENTS`、`$0`… で引数を受け取る
- フォルダ名 `synced` と `anthropic-skills` は予約
- claude.ai アカウントで有効にしたスキルは、Cowork、クラウドセッション、claude.ai でログインしたターミナル（v2.1.273 以降）に同期される。同期スキルをローカルのターミナルで使うと `@` 参照と `${CLAUDE_PROJECT_DIR}` は展開されない
- リポジトリの `.claude/settings.json` で宣言したプラグインは、クラウドセッションでは読み込まれない。クラウドでは `.claude/skills/` にコミットしたスキルが読まれる

## サブエージェント（https://code.claude.com/docs/en/sub-agents）

- `.claude/agents/*.md`。frontmatter の `name` と `description` が必須（無いと黙って読み飛ばされる）
- `tools` は許可リスト（カンマ区切りかリスト）。**省略すると全ツールを継承する**
- 検証: `claude plugin validate .claude/agents`（v2.1.233 以降）

## 権限（https://code.claude.com/docs/en/permissions）

- 優先順位は deny > ask > allow。allow で deny の例外は作れない
- ファイルのルールは `Read(...)` と `Edit(...)` だけが参照される（`Write(...)` のパスルールは無視される）
- パターンは gitignore 形式。`Read(.env)` は任意の深さの `.env`。`//` は絶対パス、`~/` はホーム、`/` は設定ファイルの場所基準
- `!` で始まる deny は、同じリスト内で前にあるルールから除外する（例 `Read(.env.*)` の後に `Read(!.env.example)`）
- 限界: Read/Edit deny はファイルツールと、`cat` など認識できる Bash コマンドに効く。`grep -r` のようにファイル名を指定しない読み取りや、Python/Node スクリプト内の読み書きは防げない。OS レベルで止めるには Sandbox
- `.claudeignore` は効果なし

## Hooks（https://code.claude.com/docs/en/hooks）

- 構造: `{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "...", "timeout": 20}]}]}}`。Stop は matcher 非対応
- `timeout` は秒。既定 600 秒。タイムアウトした hook の出力は破棄される
- Stop の入力に `stop_hook_active`（hook による継続中なら true）。これを見て再ブロックしない
- 停止を止める: 終了コード0で `{"decision": "block", "reason": "..."}`、または終了コード2と stderr。それ以外の終了コードは非ブロッキングのエラー
- 連続継続は8回で打ち切られる（`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` で変更可）
- `${CLAUDE_PROJECT_DIR}` はプロジェクトのルート。設定ファイルの直接編集は通常自動で再読み込みされる。確認は `/hooks`

## Dynamic workflows（https://code.claude.com/docs/en/workflows）

- 多数のサブエージェントを JavaScript のスクリプトで動かす。保存先は `.claude/workflows/`（プロジェクト）か `~/.claude/workflows/`（個人）。プラグインは `workflows/` に置くと `/<plugin>:<name>` で起動できる
- 有料プランで利用可能。Pro は `/config` の Dynamic workflows で有効化する。規模の目安（workflowSizeGuideline）の既定は medium、Pro では small（5エージェント未満を目安、v2.1.271 以降）
- 実行中は利用者の入力を受けられない。承認が必要な区切りではワークフローを分ける
- スクリプト内で `Date.now()`、`Math.random()`、引数なしの `new Date()`、`import()` は使えない
- `/deep-research` は組み込みのワークフロー（Web 検索で多角的に調べ、出典を突き合わせる）

## Sandbox（https://code.claude.com/docs/en/sandboxing）

- macOS、Linux、WSL2 で動作。ネイティブ Windows は非対応。既定はオフ。`/sandbox` か `sandbox.enabled: true`
- Linux / WSL2 は `bubblewrap` と `socat` が必要
- 囲うのはシェルコマンド（Bash、PowerShell、Monitor）とその子プロセスだけ。Read/Edit などのファイルツール、hooks、MCP サーバー、ステータスラインは対象外
