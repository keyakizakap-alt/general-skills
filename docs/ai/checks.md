# 合格条件と検査

結果は「成功」「失敗」「未実行」で報告する。合格条件を勝手に緩めない。

## 検査コマンド一覧

| コマンド | 対象 | 副作用 |
|---|---|---|
| `claude plugin validate .claude-plugin/marketplace.json` | マーケットプレイス定義 | なし |
| `claude plugin validate .claude-plugin/plugin.json` | プラグイン定義 | なし |
| `claude plugin validate skills/` | 配布スキルの frontmatter | なし |
| `claude plugin validate agents/` | 配布サブエージェント | なし |
| `claude plugin validate .claude/agents` | このリポジトリ用サブエージェント | なし |
| `claude plugin validate .claude/skills` | このリポジトリ用スキル | なし |
| `python3 tools/build_skill_zip.py` | claude.ai 制約（name 形式・予約語・description 長） | `dist/` にZIPを書き出す（Git追跡外） |
| `claude plugin test mods/vibe-deck` | vibe-deck の動作テスト | なし（bun で実行） |
| `python3 skills/prompt-architect/scripts/lint_prompt.py <file>` | プロンプト本文 | なし |
| `python3 .claude/hooks/check_setup.py` | エージェント用設定の構造 | なし |
| `python3 -m unittest discover -s .claude/hooks/tests` | 上記検査スクリプト自体のテスト | 一時ディレクトリのみ |

## 作業別の合格条件

### 配布スキル（`skills/`）を追加・変更した

- [ ] `claude plugin validate skills/` 成功
- [ ] `python3 tools/build_skill_zip.py` 成功（全スキル OK）
- [ ] `name` がフォルダ名と一致し、description に用途と起動フレーズがある
- [ ] モデル名・料金など腐る情報に出典URLと参照日がある
- [ ] 追加・改名なら `README.md` の一覧と `.claude-plugin/` の説明文を更新した
- [ ] どのチャットでも動くか: frontmatter は `name` と `description` だけ、本文が `@` 参照・`${CLAUDE_PROJECT_DIR}`・このリポジトリのファイルに依存していない、ファイルを書けない環境での代替手順がある
- [ ] `workspace-setup/assets/check_setup.py` を変えたら `.claude/hooks/check_setup.py` にコピーし、テストが通る（同一性はテストで検査）
- [ ] 手動: `/<skill-name>` で起動し、description どおりの場面で使えるか確認（未実施なら未実行と書く）

### mod（`mods/`）を変更した

- [ ] `claude plugin validate mods/<name>/.claude-plugin/plugin.json` 成功
- [ ] `claude plugin test mods/<name>` 成功
- [ ] README の検証済みバージョン表記が実際に検証したバージョンと一致

### マニフェスト（`.claude-plugin/`）を変更した

- [ ] marketplace / plugin の validate が両方成功
- [ ] 説明文が実際の収録物と一致

### エージェント用設定（`.claude/CLAUDE.md`、`AGENTS.md`、`.claude/`）を変更した

- [ ] `python3 .claude/hooks/check_setup.py` 成功
- [ ] `python3 -m unittest discover -s .claude/hooks/tests` 成功
- [ ] 手動: 新しいセッションで `/memory`（読み込まれた指示）、`/hooks`（Stop hook）、`/agents`、`/permissions`（deny ルール）、`/context` を確認

## 検査スクリプトで判定できないこと（手動確認）

- YAML frontmatter の完全な構文検証（簡易パーサーで必須キーのみ確認）
- 指示が実際に守られるか、スキルが適切な場面で起動するか
- 権限ルールが実際に適用されるか（秘密ファイルを実際に開いて試さない）
