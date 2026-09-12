# general-skills

業務で使える汎用スキル集。

## スキル一覧

| スキル | 概要 |
|---|---|
| [`prompt-architect`](skills/prompt-architect/) | どの生成AI・AIエージェントにも移植できる実務用プロンプトを、ヒアリングなしで一発設計する。9ブロック構成 + 実務アーキタイプ + 能力ティア適合 + 機械リンター。モデル世代が上がるほどプロンプトを「引く」方向に更新する仕組みを内蔵。 |

## 使い方

Claude Code から利用する場合は、このリポジトリをスキルの探索対象に置く（`.claude/skills/` 配下に配置、またはプラグインとして読み込む）。
各スキルは `SKILL.md` に手順、`references/` に詳細、`assets/` にテンプレート、`scripts/` に検証ツールを持つ。

```bash
# プロンプトの機械チェック
python3 skills/prompt-architect/scripts/lint_prompt.py path/to/prompt.txt

# 能力ティア適合（T2以上では、旧世代向けの足場が残っていないかを検出）
python3 skills/prompt-architect/scripts/lint_prompt.py path/to/prompt.txt --tier T2
```

## 設計上の方針

- **腐る情報と腐らない情報を分離する**: モデル名・バージョン固有の記述は `references/targets.md` にのみ置き、出典と参照日を付ける。原則・型・失敗モードはモデル非依存で書く。
- **モデル名ではなく能力ティアで分岐する**: 名前は陳腐化するが、能力の階段（軽量 / 標準 / 推論内蔵 / 自律エージェント）は残る。未知のモデルは `assets/capability-probe.md` で判定する。
- **世代が上がったら足さずに引く**: 古い世代向けの足場（CoT指示、強い語調、大量の例）を削除してから再測定する。
