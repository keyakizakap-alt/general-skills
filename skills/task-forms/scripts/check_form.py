#!/usr/bin/env python3
"""回答・文書が「そのまま使える形」になっているかを検査する。標準ライブラリのみ。

    python3 check_form.py answer.md
    python3 check_form.py answer.md --max-chars 800   # 長さの上限も検査
    python3 check_form.py answer.md --strict          # 注意も不合格にする
    cat answer.md | python3 check_form.py -

不合格（終了コード1）にするもの:
    冒頭の前置き / 締めの定型 / 穴埋めの残り / 出典の書式不足 / 長さの上限超過
注意として表示するもの:
    結論が冒頭に無い疑い / 見出しの過多 / 箇条書きへの偏り / 量を数字で書いていない語 / ラベルの無い推測

制約: 語句と行の形で判定する。雛形として穴埋めを残す文書には --allow-placeholders を付ける。
コードブロックとインラインコードは検査しない。
"""

import argparse
import re
import sys
from pathlib import Path

PREAMBLE = re.compile(
    r"^(承知(?:いた)?しました|かしこまりました|了解(?:です|しました)|ご質問ありがとう|お問い合わせありがとう"
    r"|素晴らしい(?:質問|ご質問|視点)|良い質問|以下(?:に|の通り|のとおり)|それでは|まず(?:は)?結論から"
    r"|.{0,30}について(?:説明|解説|回答|ご説明|ご紹介|お答え)(?:し|いたし)ます)")
CLOSING = re.compile(
    r"お役に立て|ご不明(?:な)?点|お気軽に|いかがでし(?:ょうか|たか)|何かあれば|ご質問があれば|参考になれば"
    r"|お手伝いでき")
PLACEHOLDER = re.compile(r"TODO|TBD|XXX|Lorem ipsum|〇〇|○○|◯◯|\{\{[^}]*\}\}|［[^］]*を入力[^］]*］|\[[^\]]*を入力[^\]]*\]")
VAGUE = re.compile(r"多くの|大幅に|かなりの|数多くの|一般的に|よく言われ|最近では|近年")
GUESS = re.compile(r"と思われ|おそらく|はずです|はずだ|可能性が高い|と見られ")
LABEL = re.compile(r"推測|未確認|推定|仮説|試算")
URL = re.compile(r"https?://[^\s)>\]」』）]+")
SOURCE_HEAD = re.compile(r"^(?:#{1,6}\s*)?(?:出典|参考(?:資料|文献)?|Sources?|References?)\s*[:：]?\s*$")
NOTE_HEAD = re.compile(r"^(?:前提|未確認|出典)\s*[:：]")  # 成果物の後ろに付ける注記（長さの上限に含めない）
ACQUIRED = re.compile(r"取得日\s*[:：]?\s*\d{4}[-/年]\d{1,2}[-/月]\d{1,2}")


def body_lines(raw):
    """コードブロックとインラインコードを除いた (行番号, 行) を返す。"""
    out, fence = [], False
    for i, line in enumerate(raw.splitlines(), 1):
        if re.match(r"^\s*(```|~~~)", line):
            fence = not fence
            continue
        if not fence:
            out.append((i, re.sub(r"`[^`]*`", "", line)))
    return out


def check(raw, max_chars=None, allow_placeholders=False):
    errors, warns = [], []
    lines = body_lines(raw)
    filled = [(i, l.strip()) for i, l in lines if l.strip()]
    if not filled:
        return ["本文が空"], []
    prose = [(i, l) for i, l in filled if not l.startswith("#")]
    headings = [(i, l) for i, l in filled if re.match(r"^#{1,6}\s", l)]
    bullets = [(i, l) for i, l in filled if re.match(r"^([-*・]|\d+[.)])\s", l)]

    # 冒頭の前置き
    if prose:
        i, first = prose[0]
        first = re.sub(r"^[>\-*\s]+", "", first)
        if PREAMBLE.search(first):
            errors.append((i, "冒頭の前置き", first[:50], "削って、1文目に答えを書く"))
        elif len(first) > 200 and not headings:
            warns.append((i, "結論が冒頭に無い疑い", f"最初の段落が {len(first)} 字", "答えを1〜2文で先に出す"))

    # 締めの定型（末尾3行。出典の見出しと URL の行は除く）
    tail = [(i, l) for i, l in filled if not SOURCE_HEAD.match(l) and not NOTE_HEAD.match(l) and not URL.search(l)]
    for i, l in tail[-3:]:
        if CLOSING.search(l):
            errors.append((i, "締めの定型", l[:50], "削るか、相手の次の一手を具体的に書く"))

    # 穴埋めの残り
    if not allow_placeholders:
        for i, l in filled:
            m = PLACEHOLDER.search(l)
            if m:
                errors.append((i, "穴埋めの残り", m.group(0), "実際の値を入れる。分からなければ「未確認」と書く"))

    # 出典の書式（出典の節にある URL 行は、取得日と公式/非公式を持つ）
    in_src, has_src, urls_outside = False, False, 0
    for i, l in filled:
        if SOURCE_HEAD.match(l) or re.match(r"^出典\s*[:：]", l):
            in_src, has_src = True, True
            if not URL.search(l):
                continue
        elif in_src and l.startswith("#"):
            in_src = False
        if URL.search(l):
            if in_src:
                missing = [n for n, ok in (("取得日", ACQUIRED.search(l)), ("公式/非公式", re.search(r"公式|非公式|一次情報", l))) if not ok]
                if missing:
                    errors.append((i, "出典の書式不足", l[:50], "不足: " + "・".join(missing) + "（タイトル／URL／公式・非公式／取得日）"))
            else:
                urls_outside += 1
    if urls_outside and not has_src:
        warns.append((0, "出典の節が無い", f"本文に URL が {urls_outside} 件", "末尾に「出典」としてまとめ、取得日と公式/非公式を付ける"))

    # 構造の偏り
    n = len(filled)
    if len(headings) >= 4 and len(headings) * 3 > n:
        warns.append((0, "見出しの過多", f"見出し {len(headings)} / 全 {n} 行", "3節未満なら見出しを外し、文章でつなぐ"))
    if n >= 10 and len(bullets) / n > 0.7:
        warns.append((0, "箇条書きへの偏り", f"箇条書き {len(bullets)} / 全 {n} 行", "理由と因果は文章で書く"))

    # 量を数字で書いていない語、ラベルの無い推測
    for i, l in filled:
        m = VAGUE.search(l)
        if m and not re.search(r"\d", l):
            warns.append((i, "量を数字で書いていない", m.group(0), "件数・割合・時期を書く。書けなければ削る"))
        m = GUESS.search(l)
        if m and not LABEL.search(l):
            warns.append((i, "ラベルの無い推測", m.group(0), "確かめるか、「推測」と明記する"))

    # 長さ
    if max_chars:
        cut = next((n for n, (_, l) in enumerate(filled) if NOTE_HEAD.match(l) or SOURCE_HEAD.match(l)), len(filled))
        size = sum(len(l) for _, l in filled[:cut])
        if size > max_chars:
            errors.append((0, "長さの上限超過", f"{size} 字（上限 {max_chars}）", "足す前に削る。経緯と重複から落とす"))
    return errors, warns


def main():
    ap = argparse.ArgumentParser(description="回答・文書の型の検査")
    ap.add_argument("target", help="ファイル、または - （標準入力）")
    ap.add_argument("--max-chars", type=int, help="本文の文字数の上限（空行・コードブロック・末尾の前提/未確認/出典を除く）")
    ap.add_argument("--allow-placeholders", action="store_true", help="雛形として穴埋めを残す文書")
    ap.add_argument("--strict", action="store_true", help="注意も不合格にする")
    a = ap.parse_args()
    if a.target == "-":
        raw = sys.stdin.read()
    else:
        p = Path(a.target)
        if not p.is_file():
            print(f"{a.target} が見つかりません")
            return 2
        raw = p.read_text(encoding="utf-8", errors="replace")

    errors, warns = check(raw, a.max_chars, a.allow_placeholders)
    if errors and isinstance(errors[0], str):
        print(errors[0])
        return 2
    print(f"型の検査: {a.target}")
    for title, items in (("不合格", errors), ("注意", warns)):
        if items:
            print(f"\n【{title}】")
        for ln, key, ex, fix in items:
            where = f"{ln}行目 " if ln else ""
            print(f"  ● {key}: {where}{ex}\n    → {fix}")
    if not errors and not warns:
        print("問題は検出されませんでした。")
    print(f"\n不合格 {len(errors)} 件 / 注意 {len(warns)} 件")
    print("機械検査で分かるのは形だけ。冒頭だけ読んで行動できるかは、読み直して確かめる。")
    return 1 if errors or (a.strict and warns) else 0


if __name__ == "__main__":
    sys.exit(main())
