#!/usr/bin/env python3
"""文章から「AIが書いた」と読まれやすい兆候を検出する（日本語・英語）。標準ライブラリのみ。

    python3 check_text.py draft.md
    python3 check_text.py docs/            # .md .txt .html を検査
    cat draft.txt | python3 check_text.py -
    python3 check_text.py draft.md --strict # 弱い兆候も不合格にする

判定は「重なりの数」で行う（references/writing-tells.md の基準）:
    1〜2種類 = 許容 / 3〜4種類 = テンプレ寄り / 5種類以上 = AI判定

制約: 語句の出現で判定するため、意図して使っている場合や、兆候を説明している文も検出する。
指摘は「使うな」ではなく「具体的な情報が抜けていないか確認しろ」という意味。
Markdown のコードブロック、インラインコード、HTML のタグ・script・style は検査しない。
"""

import argparse
import re
import sys
from pathlib import Path

EXTS = {".md", ".markdown", ".txt", ".html", ".htm"}
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", "out", "vendor", "__pycache__"}

# (キー, 重大度, 正規表現, 理由, 直し方)
RULES = [
    ("誇張語", "strong",
     r"革新的|画期的|圧倒的|劇的に|飛躍的に|次世代の|ゲームチェンジャー|を再定義",
     "変化の中身が書かれていない", "何がどれだけ変わるかを数字か比較で書く。書けなければ削る"),
    ("万能の形容", "strong",
     r"シームレスに?|包括的な|網羅的な|強力な|最適な(?!化)",
     "何を指すかが曖昧", "何と何がつながるか、何を含むか、何と比べてかを書く"),
    ("定型の前置き・締め", "strong",
     r"について解説します|を見ていきましょう|本記事では|いかがでしたか|参考になれば幸いです|ぜひ(?:試して|活用して|参考に)",
     "内容の無い定型文", "削る。いきなり本題に入り、締めは次の一手を書く"),
    ("英語の常套句", "strong",
     r"\b(?:delve|tapestry|testament to|game[- ]changer|cutting[- ]edge|supercharge|unlock the power)\b"
     r"|In today's fast[- ]paced|It's important to note|Let's dive in",
     "英語のAI文章で頻出", "具体的な名詞・動詞に置き換えるか削る"),
    ("空疎な抽象", "weak",
     r"様々な|多様な|幅広い|重要な役割を果たす|の鍵となる|価値を最大化|に不可欠",
     "中身を挙げていない", "中身を2〜3個挙げる。挙げられないなら削る"),
    ("断定回避", "weak",
     r"と言えるでしょう|と考えられます|ではないでしょうか|かもしれません",
     "多用すると責任を避けた文に見える", "事実は言い切り、不確かなものは「未確認」と1回だけ明示する"),
    ("英語の万能語", "weak",
     r"\b(?:leverage|seamless(?:ly)?|robust|holistic|streamline)\b",
     "何をどうするかが曖昧", "具体的な動作と対象を書く"),
    ("太字の多用", "weak", None, "強調が多いと何も強調されない", "太字は1画面に1〜2か所"),
    ("見出しの絵文字", "strong", None, "装飾の穴埋め", "見出しは内容を表す言葉だけにする"),
    ("同じ文末の連続", "weak", None, "単調で機械的に読める", "文末を変える、文をつなぐ・分ける"),
    ("em dash の多用", "weak", None, "英語のAI文章で頻出", "文を分けるか、カンマ・括弧にする"),
]
EMOJI = re.compile("[\U0001F300-\U0001FAFF\U0001F000-\U0001F0FF⭐✨⚡✅❌]")


def to_text(raw, suffix):
    """コード・タグを除いた本文の行を返す。"""
    if suffix in {".html", ".htm"}:
        raw = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", raw)
        raw = re.sub(r"(?i)<br\s*/?>|</(p|div|h[1-6]|li|tr)>", "\n", raw)
        raw = re.sub(r"<[^>]+>", " ", raw)
    lines, fence = [], False
    for line in raw.splitlines():
        if re.match(r"^\s*(```|~~~)", line):
            fence = not fence
            lines.append("")
            continue
        lines.append("" if fence else re.sub(r"`[^`]*`", "", line))
    return lines


def iter_inputs(target):
    if target == "-":
        yield "<stdin>", ".txt", sys.stdin.read()
        return
    p = Path(target)
    files = [p] if p.is_file() else sorted(
        f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in EXTS and not SKIP_DIRS & set(f.parts))
    for f in files:
        try:
            yield str(f), f.suffix.lower(), f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue


def scan(inputs):
    hits, total_lines, bold, dashes = {}, 0, [], []
    for name, suffix, raw in inputs:
        lines = to_text(raw, suffix)
        total_lines += sum(1 for l in lines if l.strip())
        run, run_end, run_start = 0, None, 0
        for i, line in enumerate(lines, 1):
            excerpt = line.strip()[:80]
            for key, _sev, pat, _why, _fix in RULES:
                if pat and re.search(pat, line, re.I):
                    hits.setdefault(key, []).append((name, i, excerpt))
            if re.match(r"^\s*#{1,6}\s", line) and EMOJI.search(line):
                hits.setdefault("見出しの絵文字", []).append((name, i, excerpt))
            bold += [(name, i, excerpt)] * len(re.findall(r"\*\*[^*\n]+\*\*|<(?:b|strong)>", line))
            dashes += [(name, i, excerpt)] * line.count("—")
            # 同じ文末の連続（文単位）
            for sent in re.findall(r"[^。！？]+[。！？]", line):
                end = re.search(r"(です|ます|でした|ました|である|だ)[。！？]$", sent)
                end = end.group(1) if end else None
                if end and end == run_end:
                    run += 1
                else:
                    run, run_end, run_start = 1, end, i
                if run == 3:
                    hits.setdefault("同じ文末の連続", []).append((name, run_start, f"「〜{end}。」が3文以上続く"))
    counts = {k: len(v) for k, v in hits.items()}
    if total_lines and len(bold) / total_lines > 0.15 and len(bold) >= 4:
        hits["太字の多用"] = list(dict.fromkeys(bold))[:2] + [(None, 0, f"太字 {len(bold)} か所 / 本文 {total_lines} 行")]
        counts["太字の多用"] = len(bold)
    if len(dashes) >= 3:
        hits["em dash の多用"] = list(dict.fromkeys(dashes))[:2] + [(None, 0, f"— が {len(dashes)} か所")]
        counts["em dash の多用"] = len(dashes)
    return hits, counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="ファイル、ディレクトリ、または - （標準入力）")
    ap.add_argument("--strict", action="store_true", help="弱い兆候も不合格にする")
    a = ap.parse_args()
    if a.target != "-" and not Path(a.target).exists():
        print(f"{a.target} が見つかりません")
        return 2
    inputs = list(iter_inputs(a.target))
    if not inputs:
        print("検査対象がありません（.md .txt .html）")
        return 2

    hits, counts = scan(inputs)
    meta = {k: (sev, why, fix) for k, sev, _p, why, fix in RULES}
    strong = [k for k in hits if meta[k][0] == "strong"]
    weak = [k for k in hits if meta[k][0] == "weak"]

    print(f"文章のAIっぽさ検査: {len(inputs)} ファイル")
    if not hits:
        print("兆候は検出されませんでした。")
    for group, title in ((strong, "強い兆候"), (weak, "弱い兆候")):
        if group:
            print(f"\n【{title}】")
        for key in group:
            print(f"  ● {key}（{counts[key]} 箇所）— {meta[key][1]}\n    → {meta[key][2]}")
            for f, ln, ex in hits[key][:3]:
                print(f"      {f}:{ln}  {ex}" if f else f"      {ex}")

    n = len(hits)
    verdict = "AI判定" if n >= 5 else "テンプレ寄り" if n >= 3 else "許容" if n else "問題なし"
    print(f"\n重なり: {n} 種類（強 {len(strong)} / 弱 {len(weak)}）  判定: {verdict}")
    print("語句を言い換える前に、数字・固有名詞・条件が無い文を探す（references/writing-tells.md）。")
    if a.strict:
        return 1 if hits else 0
    return 1 if (strong or n >= 3) else 0


if __name__ == "__main__":
    sys.exit(main())
