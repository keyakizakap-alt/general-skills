#!/usr/bin/env python3
"""プロンプトの機械チェッカー。

使い方:
    python3 lint_prompt.py prompt.txt
    cat prompt.txt | python3 lint_prompt.py
    python3 lint_prompt.py prompt.txt --agent          # エージェント用の追加チェック
    python3 lint_prompt.py prompt.txt --tier T2        # 能力ティア適合（古い足場の検出）

ティア: T0 軽量 / T1 標準 / T2 推論内蔵 / T3 自律エージェント
T2以上では、古い世代向けの足場（CoT指示・強い語調・お守り文字列）が残っていることを不適合として検出する。
必須項目(REQUIRED)が1つでも落ちたら終了コード1。日本語/英語どちらのプロンプトにも対応。

制約: 語句の出現で判定するため、「〜と書かない」のように禁止表現を説明した文も検出する。
プロンプト本体だけを渡すこと（解説文を含むドキュメントを渡すと誤検出する）。
"""

import argparse
import re
import sys

# (ラベル, 必須か, 判定関数) -> (ok, 補足メッセージ)
VAGUE = [
    "適切に", "適宜", "いい感じ", "良い感じ", "よい感じ", "うまく", "なるべく",
    "できるだけ", "必要に応じて", "しっかり", "ちゃんと", "丁寧に",
    "appropriately", "as needed", "as appropriate", "nicely", "properly", "good quality",
]
FLUFF = [
    "世界最高", "最高峰", "天才", "深呼吸", "ステップバイステップで考えて",
    "あなたならできる", "world-class", "take a deep breath", "you are the best",
]
PLACEHOLDER = ["TBD", "TODO", "XXX", "ここに記入", "ここに入力", "（未定）", "<ここ", "FIXME"]
OUTPUT_HINT = ["出力形式", "出力は", "形式:", "フォーマット", "output format", "respond in", "json", "スキーマ", "schema", "出力する", "# 出力", "出力（", "出力:", "出力は次"]
GOAL_HINT = ["完了条件", "成功条件", "目的", "ゴール", "goal", "objective", "definition of done", "達成"]
UNCERTAIN_HINT = ["要確認", "不明", "推測", "根拠", "出典", "needs_info", "確定できない", "捏造", "わからない場合", "記載がありません"]
INPUT_HINT = ["{{", "--- 入力", "入力ここから", "<input", "<documents", "```", "以下の入力", "###入力", "# 入力"]
EXAMPLE_HINT = ["<例>", "<example", "例:", "例）", "## 例", "# 例", "example:", "入力例"]
NEG_PAT = re.compile(r"(しないでください|してはいけない|するな(?![ぞ])|禁止|避けてください|使わないで|do not|don't|never |avoid )", re.I)
POS_PAT = re.compile(r"(代わりに|その場合は|〜せよ|してください|書く|使う|出力する|明記|instead|use |write )", re.I)
CONCISE = ["簡潔", "短く", "以内", "concise", "brief"]
VERBOSE = ["網羅的", "詳細に", "余さず", "できる限り多く", "comprehensive", "exhaustive", "in detail"]
# --- ティア適合（モデル世代が上がったときに外すべき足場） ---
COT_HINT = ["段階的に考え", "ステップバイステップ", "順を追って考え", "一歩ずつ考え",
            "think step by step", "let's think", "step-by-step reasoning"]
PUSHY_HINT = ["絶対に", "いかなる場合も", "必ず必ず", "CRITICAL", "厳守すること", "手を抜",
              "迷ったら", "とにかく", "何があっても", "you must always", "if in doubt", "at all costs"]
EAGER_HINT = ["徹底的に", "可能な限り多く", "常にツールを使", "できる限り詳細に",
              "be as thorough as possible", "always use the tool"]
LEN_SPEC = re.compile(r"(\d+\s*(文字|字|文|語|項目|点|行|ページ|words?|sentences?|bullets?)|以内|以下に収め)")
SCOPE_HINT = ["範囲だけ", "依頼された範囲", "スコープ", "範囲外", "責務外", "責務は", "余計な",
              "勝手に", "追加しない", "beyond what was asked", "only what was asked"]
STATE_HINT = ["進捗", "記録する", "保存", "作業メモ", "計画を提示", "再開", "state", "progress"]

AGENT_HINT = ["ツール", "tool", "エージェント", "agent", "自律", "実行する", "api", "mcp"]
STOP_HINT = ["停止", "中断", "確認を取る", "完了とみなす", "エスカレーション", "stop", "escalate", "ask the user", "確認する条件"]
IRREVERSIBLE_HINT = ["不可逆", "取り消しが困難", "削除", "上書き", "本番", "公開", "送信", "課金", "irreversible", "destructive"]


def has_any(text, words):
    low = text.lower()
    return [w for w in words if w.lower() in low]


def check(text, agent_mode):
    results = []   # (level, label, ok, detail)
    n = len(text)

    def add(level, label, ok, detail=""):
        results.append((level, label, ok, detail))

    hits = has_any(text, VAGUE)
    add("REQUIRED", "曖昧語がない", not hits,
        "検出: " + ", ".join(hits[:5]) + " → 検証可能な表現に置換" if hits else "")

    add("REQUIRED", "成功条件/目的が書かれている", bool(has_any(text, GOAL_HINT)),
        "「完了条件」または「目的」の節を追加" )

    add("REQUIRED", "出力形式が指定されている", bool(has_any(text, OUTPUT_HINT)),
        "構造・長さ・語調、または JSON スキーマを明示")

    add("REQUIRED", "不確実性プロトコルがある", bool(has_any(text, UNCERTAIN_HINT)),
        "根拠なしの記述禁止・「要確認」の出し方を追加")

    ph = has_any(text, PLACEHOLDER)
    add("REQUIRED", "未確定プレースホルダが残っていない", not ph,
        "検出: " + ", ".join(ph[:5]) if ph else "")

    neg = len(NEG_PAT.findall(text))
    pos = len(POS_PAT.findall(text))
    add("REQUIRED", "禁止に代替行動が伴っている", not (neg >= 3 and pos < neg),
        f"否定表現 {neg} 件に対し行動指定 {pos} 件 → Do 形式に書き換え" if neg >= 3 and pos < neg else "")

    c, v = has_any(text, CONCISE), has_any(text, VERBOSE)
    add("REQUIRED", "矛盾する指示がない", not (c and v),
        f"「{c[0]}」と「{v[0]}」が同居 → 優先順位か適用範囲を明示" if c and v else "")

    add("RECOMMENDED", "入力データが分離されている", bool(has_any(text, INPUT_HINT)),
        "区切り（--- 入力ここから ---）または {{変数}} で指示と分離")

    add("RECOMMENDED", "例がある", bool(has_any(text, EXAMPLE_HINT)),
        "3〜5件、境界事例を1つ含める")

    add("RECOMMENDED", "再利用可能な変数がある", "{{" in text,
        "毎回変わる箇所を {{VAR}} に切り出す")

    fl = has_any(text, FLUFF)
    add("RECOMMENDED", "お守り文字列がない", not fl,
        "検出: " + ", ".join(fl[:3]) if fl else "")

    add("RECOMMENDED", "長さが妥当", 200 <= n <= 12000,
        f"{n} 文字（短すぎ: 決定事項が不足 / 長すぎ: 指示が埋もれる）" if not (200 <= n <= 12000) else f"{n} 文字")

    if agent_mode or len(has_any(text, AGENT_HINT)) >= 2:
        add("REQUIRED", "[Agent] 停止・確認条件がある", bool(has_any(text, STOP_HINT)),
            "完了条件 / 人間に確認する条件 / 失敗停止条件 の3種を定義")
        add("RECOMMENDED", "[Agent] 不可逆操作の扱いがある", bool(has_any(text, IRREVERSIBLE_HINT)),
            "削除・送信・公開・本番反映は事前確認を必須に")
    return results


def tier_checks(text, tier):
    """能力ティア別の適合チェック。返り値は check() と同形式。"""
    out = []
    if not tier:
        return out
    tier = tier.upper()

    def add(level, label, ok, detail=""):
        out.append((level, label, ok, detail))

    if tier == "T0":
        neg = len(NEG_PAT.findall(text))
        add("TIER", "[T0] 否定形が少ない（2件以下）", neg <= 2,
            f"否定表現 {neg} 件 → 小型モデルは否定を守りにくい。やってほしい行動に書き換え")
        ex = sum(text.count(w) for w in ("<例>", "<example", "入力例", "例:"))
        add("TIER", "[T0] 例が3件以上ある", ex >= 3, f"例 {ex} 件 → 5件以上を推奨")
        add("TIER", "[T0] 長すぎない（3000字以内）", len(text) <= 3000,
            f"{len(text)} 文字 → 指示が埋もれる。1文1命令に分解して短縮")
        steps = len(re.findall(r"^\s*\d+[.)、]", text, re.M))
        add("TIER", "[T0] 手順が5つ以内", steps <= 5, f"手順 {steps} 件 → 5つ以内に圧縮")

    if tier in ("T2", "T3"):
        cot = has_any(text, COT_HINT)
        add("TIER", "[T2+] CoT指示が残っていない", not cot,
            "検出: " + ", ".join(cot[:3]) + " → 推論内蔵世代では二重思考になる。削除" if cot else "")
        pushy = has_any(text, PUSHY_HINT)
        add("TIER", "[T2+] 過度に強い語調が残っていない", not pushy,
            "検出: " + ", ".join(pushy[:3]) + " → 過剰発火を招く。通常の指示文に戻す" if pushy else "")
        eager = has_any(text, EAGER_HINT)
        add("TIER", "[T2+] 旧世代向けの煽り（徹底的に等）が残っていない", not eager,
            "検出: " + ", ".join(eager[:3]) + " → 過剰探索・過剰ツール呼び出しの原因" if eager else "")
        add("TIER", "[T2+] 出力長が数値で指定されている", bool(LEN_SPEC.search(text)),
            "既定の饒舌さは世代ごとに変わる。文字数・文数・項目数で縛る")
        add("TIER", "[T2+] スコープ固定がある", bool(has_any(text, SCOPE_HINT)),
            "賢い世代ほど範囲を広げ過剰実装する。「依頼された範囲だけを扱う」を追加")

    if tier == "T3":
        add("TIER", "[T3] 停止・確認条件がある", bool(has_any(text, STOP_HINT)),
            "完了 / 人間に確認 / 失敗停止 の3条件を定義")
        add("TIER", "[T3] 不可逆操作の扱いがある", bool(has_any(text, IRREVERSIBLE_HINT)),
            "削除・送信・公開・本番反映は事前確認を必須に")
        add("TIER", "[T3] 状態・進捗の記録がある", bool(has_any(text, STATE_HINT)),
            "長時間タスクは進捗の外部化が必須")
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("file", nargs="?", help="プロンプトのファイル（省略時は標準入力）")
    p.add_argument("--agent", action="store_true", help="エージェント用の追加チェックを強制する")
    p.add_argument("--tier", choices=["T0", "T1", "T2", "T3", "t0", "t1", "t2", "t3"],
                   help="宛先モデルの能力ティア。T2以上では古い足場の残存を検出する")
    a = p.parse_args()

    text = open(a.file, encoding="utf-8").read() if a.file else sys.stdin.read()
    if not text.strip():
        print("入力が空です")
        return 2

    results = check(text, a.agent or (a.tier or "").upper() == "T3")
    tiers = tier_checks(text, a.tier)
    req = [r for r in results if r[0] == "REQUIRED"]
    rec = [r for r in results if r[0] == "RECOMMENDED"]
    failed_req = [r for r in req if not r[2]] + [r for r in tiers if not r[2]]

    def show(title, rows):
        print(f"\n{title}")
        for _, label, ok, detail in rows:
            mark = "OK  " if ok else "NG  "
            line = f"  {mark}{label}"
            if detail and (not ok or "長さ" in label):
                line += f"\n        → {detail}"
            print(line)

    print("=" * 60)
    print("プロンプト検査結果")
    print("=" * 60)
    show("必須", req)
    show("推奨", rec)
    if tiers:
        show(f"ティア適合 ({a.tier.upper()})", tiers)

    base = (sum(r[2] for r in req) / max(len(req), 1) * 0.7
            + sum(r[2] for r in rec) / max(len(rec), 1) * 0.3)
    if tiers:
        base = base * 0.75 + sum(r[2] for r in tiers) / len(tiers) * 0.25
    score = round(100 * base)
    print("\n" + "-" * 60)
    print(f"スコア: {score}/100   判定: {'PASS' if not failed_req else 'FAIL'}")
    if failed_req:
        print(f"未達 {len(failed_req)} 件。修正してから納品してください。")
        if any(r[1].startswith("[T2+]") or r[1].startswith("[T0]") for r in failed_req):
            print("ティア不適合は references/model-growth.md の減算リストを参照。")
    print("-" * 60)
    return 1 if failed_req else 0


if __name__ == "__main__":
    sys.exit(main())
