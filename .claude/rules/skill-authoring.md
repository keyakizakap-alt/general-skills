---
paths:
  - "skills/**"
---

# 配布スキルの作法（`skills/` を編集するとき）

- `SKILL.md` の先頭は `---` で囲んだ YAML frontmatter。`name` はフォルダ名と一致させ、小文字・数字・ハイフンのみ64文字以内、`claude` / `anthropic` を含めない（claude.ai へのアップロード制約。`tools/build_skill_zip.py` が検証する）。
- `description` は1024文字以内、XMLタグを入れない。「何をするか」と「どんな依頼で使うか（起動フレーズ）」を書く。英語の1文を末尾に添える既存の書き方に合わせる。
- `SKILL.md` は手順の本体だけにし、詳細は `references/`、テンプレートは `assets/`、検査は `scripts/` に分ける。`SKILL.md` から用途付きで参照する。
- モデル名・バージョン・料金・提供状況は腐る情報。出典URLと参照日を付け、置き場所を1か所に集める。原則・型はモデル非依存で書く。
- **どのチャットでも動くように書く**（claude.ai のチャット、Claude Code のローカル / クラウド / Cowork）。frontmatter は `name` と `description` だけにする。本文で `@` 参照、`${CLAUDE_PROJECT_DIR}`、`!` コマンド、`$ARGUMENTS` に依存しない（claude.ai から同期したスキルをローカルで使うと `@` 参照と `${CLAUDE_PROJECT_DIR}` は展開されない。公式 skills, 参照日 2026-10-05）。ファイルを書けない環境での代替（成果物として出力する等）を書く。
- このリポジトリ専用のパス・コマンド・`.claude/` の存在を前提にしない。
- スクリプトは標準ライブラリのみで動かす。追加依存が必要なら、利用者に確認してから導入し、README に明記する。
- 追加・改名したら `README.md` のスキル一覧と `.claude-plugin/` の説明文を同じ変更で更新する。
