# general-skills

業務で使える汎用スキル集。

## スキル一覧

| スキル | 概要 |
|---|---|
| [`prompt-architect`](skills/prompt-architect/) | どの生成AI・AIエージェントにも移植できる実務用プロンプトを、ヒアリングなしで一発設計する。9ブロック構成 + 実務アーキタイプ + ターゲット別調整 + 機械リンター。 |

## 使い方

Claude Code から利用する場合は、このリポジトリをスキルの探索対象に置く（`.claude/skills/` 配下に配置、またはプラグインとして読み込む）。
各スキルは `SKILL.md` に手順、`references/` に詳細、`assets/` にテンプレート、`scripts/` に検証ツールを持つ。

```bash
# プロンプトの機械チェック
python3 skills/prompt-architect/scripts/lint_prompt.py path/to/prompt.txt
```
