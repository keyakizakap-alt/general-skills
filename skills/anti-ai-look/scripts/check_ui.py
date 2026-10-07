#!/usr/bin/env python3
"""UIコードから「AIが作った」と判定される兆候を検出する。

    python3 check_ui.py index.html
    python3 check_ui.py src/
    python3 check_ui.py src/ --strict     # 弱い兆候も不合格にする

判定は「重なりの数」で行う（references/ui-tells.md の基準）:
    1〜2個 = 問題なし / 3〜4個 = テンプレっぽい / 5個以上 = AI判定

制約: 文字列の出現で判定するため、意図して使っている場合も検出する。
指摘は「やめろ」ではなく「意図して選んだか確認しろ」という意味。
"""

import argparse
import re
import sys
from pathlib import Path

EXTS = {".html", ".htm", ".css", ".scss", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".astro"}
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", "out", "vendor", "__pycache__"}

# 絵文字（矢印 U+2190–21FF や ✓ 等の記号は日本語の本文で普通に使うため対象外）
EMOJI = re.compile("[\U0001F300-\U0001FAFF\U0001F000-\U0001F0FF\U00002B50\U00002728\U000026A1]")

# (キー, 重大度, 正規表現, 説明, 代替案)
RULES = [
    ("紫青グラデーション", "strong",
     r"(?:from|via|to)-(?:purple|indigo|violet|fuchsia)-\d{2,3}"
     r"|#(?:6366f1|818cf8|8b5cf6|a855f7|7c3aed|4f46e5|c084fc)\b"
     r"|linear-gradient\([^)]*(?:purple|indigo|violet|#6366f1|#8b5cf6)",
     "訓練データで最も出現数が多い配色", "単色背景 + 基準色のアクセント。奥行きは明度差で作る"),

    ("グラデーション文字", "strong", r"bg-clip-text",
     "見出しを目立たせる手段の中央値", "単色。強調は大きさ・太さ・余白で作る"),

    ("すりガラス", "strong",
     r"backdrop-blur|backdrop-filter\s*:\s*blur",
     "重なりの表現の中央値", "実体のある面で区切る。半透明を使わない"),

    ("ぼかし装飾玉", "strong", r"blur-[23]xl|blur-\[\d+px\]",
     "情報量ゼロの背景装飾", "削除する"),

    ("拡大ホバー", "strong", r"hover:scale-\d|transform:\s*scale\(1\.0[2-9]",
     "インタラクションの中央値", "色または枠線の変化に留める"),

    ("絵文字アイコン", "strong", None,  # 専用処理
     "アイコン素材がないときの穴埋め", "記号・番号・図版。用意できないならアイコンなしで成立させる"),

    ("常套句コピー", "strong",
     r"Transform your|Build the future|Supercharge|Unlock the power|Seamlessly\s|Take .{1,20} to the next level"
     r"|次世代の|を、もっと自由に|を再定義|革新的な|シームレスに|圧倒的な",
     "コピーの中央値", "主語・目的語・数字を入れた具体文にする"),

    ("AI訴求バッジ", "strong", r"Powered by AI|AI-powered|AI搭載|AIを活用",
     "技術名は機能の説明にならない", "何ができるかを書く"),

    ("Inter単独", "weak", r"Inter['\"]?\s*,|font-family:\s*Inter|--font-inter",
     "無指定時の定番書体", "見出しと本文で別書体を選ぶ。日本語なら和文を先に決める"),

    ("大きい角丸", "weak", r"rounded-(?:2xl|3xl|\[1[6-9]px\]|\[[2-9]\dpx\])|border-radius:\s*(?:1[6-9]|[2-9]\d)px",
     "既定の丸みの中央値", "4〜8px に抑えるか、四角のままにする"),

    ("強い影", "weak", r"shadow-(?:xl|2xl)",
     "浮遊感の付けすぎ", "影を弱めるか、枠線に置き換える"),

    ("3カラムグリッド", "weak", r"grid-cols-3|repeat\(3,\s*(?:minmax|1fr)",
     "「特徴を3つ」の最頻出レイアウト", "数を変える / 重みを変える / 表・図に置き換える"),

    ("既定ダーク", "weak", r"bg-slate-900|bg-gray-900|#0f172a\b|#111827\b",
     "ダークモードの既定値", "背景に僅かに色味を入れる。明度関係を設計し直す"),

    ("紫系の基調色", "weak", r"(?:bg|text|border|ring)-(?:indigo|violet|purple)-\d{2,3}",
     "Tailwind の既定色", "業種と印象から基準色を選び直す"),

    ("中央揃えの多用", "weak", None,  # 専用処理（出現回数で判定）
     "全セクション中央揃えは強い兆候", "本文は左揃え。中央揃えは3行以内の短文に限る"),
]


def iter_files(target):
    p = Path(target)
    if p.is_file():
        yield p
        return
    for f in sorted(p.rglob("*")):
        if f.is_file() and f.suffix in EXTS and not any(d in SKIP_DIRS for d in f.parts):
            yield f


def scan(files):
    """{キー: [(file, lineno, 抜粋), ...]} を返す。"""
    hits = {}
    center_count = 0
    center_samples = []

    for f in files:
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            excerpt = line.strip()[:90]
            for key, _sev, pat, _why, _fix in RULES:
                if pat and re.search(pat, line, re.I):
                    hits.setdefault(key, []).append((f, i, excerpt))
            # 絵文字: 表示テキストに含まれるもの（コメント行は除外）
            if EMOJI.search(line) and not excerpt.startswith(("//", "*", "/*", "#")):
                hits.setdefault("絵文字アイコン", []).append((f, i, excerpt))
            # 中央揃え: 総出現回数で判定
            n = len(re.findall(r"text-center|text-align:\s*center", line, re.I))
            if n:
                center_count += n
                if len(center_samples) < 2:
                    center_samples.append((f, i, excerpt))

    if center_count >= 5:
        hits["中央揃えの多用"] = center_samples + [(None, 0, f"全体で {center_count} 箇所")]
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="検査するファイルまたはディレクトリ")
    ap.add_argument("--strict", action="store_true", help="弱い兆候も不合格にする")
    a = ap.parse_args()

    if not Path(a.target).exists():
        print(f"{a.target} が見つかりません")
        return 2

    files = list(iter_files(a.target))
    if not files:
        print("検査対象のファイルがありません（.html .css .jsx .tsx .vue .svelte など）")
        return 2

    hits = scan(files)
    meta = {k: (sev, why, fix) for k, sev, _p, why, fix in RULES}
    strong = [k for k in hits if meta[k][0] == "strong"]
    weak = [k for k in hits if meta[k][0] == "weak"]

    print("=" * 62)
    print(f"AIっぽさ検査: {len(files)} ファイル")
    print("=" * 62)

    if not hits:
        print("\n兆候は検出されませんでした。")
    for group, title in ((strong, "強い兆候"), (weak, "弱い兆候")):
        if not group:
            continue
        print(f"\n【{title}】")
        for key in group:
            places = hits[key]
            print(f"\n  ● {key}  ({len(places)} 箇所) — {meta[key][1]}")
            print(f"    → {meta[key][2]}")
            for f, ln, ex in places[:2]:
                print(f"      {f}:{ln}" if f else f"      {ex}")
                if f:
                    print(f"        {ex}")

    overlap = len(hits)
    if overlap >= 5:
        verdict, note = "AI判定", "即座に「AIが作った」と判定される水準"
    elif overlap >= 3:
        verdict, note = "テンプレ寄り", "「テンプレっぽい」と言われる水準"
    elif overlap >= 1:
        verdict, note = "許容", "単体では問題にならない範囲"
    else:
        verdict, note = "問題なし", ""

    print("\n" + "-" * 62)
    print(f"重なり: {overlap} 種類（強 {len(strong)} / 弱 {len(weak)}）  判定: {verdict}")
    if note:
        print(f"  {note}")
    print("  個別の兆候を潰すより、重なりを減らすことを優先する。")
    print("  決定が漏れている項目は references/decisions.md で固定する。")
    print("-" * 62)

    if a.strict:
        return 1 if hits else 0
    return 1 if (strong or overlap >= 3) else 0


if __name__ == "__main__":
    sys.exit(main())
