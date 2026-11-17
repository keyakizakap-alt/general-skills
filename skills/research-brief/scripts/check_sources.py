#!/usr/bin/env python3
"""調査メモの出典まわりを検査する。標準ライブラリのみ。

    python3 check_sources.py brief.md
    python3 check_sources.py brief.md --strict   # 注意も不合格にする
    cat brief.md | python3 check_sources.py -

不合格（終了コード1）にするもの:
    出典の節が無い / 出典の行に URL・取得日・公式/非公式が無い / 本文の [n] が出典に無い / 範囲の宣言が無い
注意として表示するもの:
    本文で使っていない出典 / 出典番号の無い数字の行 / 出典の節の外にある URL / 取得日が古い出典

制約: 行の形で判定する。内容が正しいか、情報源が独立しているかは判定できない。
出典は「1. タイトル／URL／公式・非公式／取得日 YYYY-MM-DD」の番号付きの行で書く。取得日は「取得日」の語の直後の日付で判定する。
本文の引用は [1]、[1, 2]、[1-3] の形。出典の節は、次の見出しが来るまで続く（後ろに文章を足すときは見出しを付ける）。
コードブロックとインラインコードは検査しない。
"""

import argparse
import datetime
import re
import sys
from pathlib import Path

URL = re.compile(r"https?://[^\s)>\]」』）／]+")
DATE = re.compile(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})")
KIND = re.compile(r"公式|非公式|一次情報")
SOURCE_HEAD = re.compile(r"^(?:#{1,6}\s*)?(?:出典|参考(?:資料|文献)?|Sources?|References?)\s*[:：]?\s*$")
ENTRY = re.compile(r"^(?:[-*]\s*)?\[?(\d+)[\].)]\s*(.+)$")
CITE = re.compile(r"\[(\d+(?:\s*[,，、\-–]\s*\d+)*)\]")
ACQUIRED = re.compile(r"取得日\s*[:：]?\s*(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})")
# 単位つきの数字（出典が要る可能性が高いもの）
FIGURE = re.compile(r"\d[\d,.]*\s*(?:%|％|円|ドル|USD|JPY|件|社|人|倍|万|億|GB|MB|トークン|リージョン)")
LABEL = re.compile(r"推測|未確認|試算|推定|古い可能性|前提")
SCOPE = re.compile(r"想定した範囲|調査範囲|対象範囲")


def body_lines(raw):
    out, fence = [], False
    for i, line in enumerate(raw.splitlines(), 1):
        if re.match(r"^\s*(```|~~~)", line):
            fence = not fence
            continue
        if not fence:
            out.append((i, re.sub(r"`[^`]*`", "", line).strip()))
    return [(i, l) for i, l in out if l]


def check(raw, today, max_age_days):
    errors, warns = [], []
    lines = body_lines(raw)
    if not lines:
        return None, None

    src_start = next((n for n, (_, l) in enumerate(lines) if SOURCE_HEAD.match(l)), None)
    body = lines if src_start is None else lines[:src_start]
    src = [] if src_start is None else lines[src_start + 1:]

    if not any(SCOPE.search(l) for _, l in body[:8]):
        errors.append((0, "範囲の宣言が無い", "冒頭に「想定した範囲: 問い / 時点 / 対象外」を1行で書く"))

    entries = {}
    if src_start is None:
        errors.append((0, "出典の節が無い", "末尾に「## 出典」を置き、番号付きで並べる"))
    for i, l in src:
        if l.startswith("#"):
            break
        m = ENTRY.match(l)
        if not m:
            if URL.search(l):
                errors.append((i, "出典に番号が無い", "「1. タイトル／URL／公式・非公式／取得日」の形にする"))
            continue
        num, rest = int(m.group(1)), m.group(2)
        entries[num] = i
        missing = [name for name, ok in (("URL", URL.search(rest)), ("公式/非公式", KIND.search(rest)),
                                         ("取得日", ACQUIRED.search(rest))) if not ok]
        if missing:
            errors.append((i, f"出典 {num} の書式不足", "不足: " + "・".join(missing)))
        d = ACQUIRED.search(rest)
        if d and max_age_days:
            try:
                got = datetime.date(int(d.group(1)), int(d.group(2)), int(d.group(3)))
                if (today - got).days > max_age_days:
                    warns.append((i, f"出典 {num} の取得日が {(today - got).days} 日前", "変わりうる情報なら取得し直す"))
            except ValueError:
                errors.append((i, f"出典 {num} の取得日が不正", "YYYY-MM-DD で書く"))
    if src_start is not None and not entries:
        errors.append((lines[src_start][0], "出典が空", "使った情報源を番号付きで書く"))

    cited = set()
    for i, l in body:
        for group in CITE.findall(l):
            nums = []
            for part in re.split(r"\s*[,，、]\s*", group):
                ends = [int(x) for x in re.split(r"\s*[\-–]\s*", part)]
                nums += range(ends[0], ends[-1] + 1) if len(ends) > 1 else ends
            for n in nums:
                cited.add(n)
                if n not in entries and src_start is not None:
                    errors.append((i, f"[{n}] が出典に無い", "出典に追加するか、番号を直す"))
        if URL.search(l):
            warns.append((i, "出典の節の外に URL", "本文は [番号] にし、URL は出典にまとめる"))
        if (FIGURE.search(l) and not CITE.search(l) and not LABEL.search(l)
                and not l.startswith("#") and not SCOPE.search(l)):
            warns.append((i, "出典番号の無い数字", l[:40] + " → [番号] を付けるか、試算・推測と明記する"))
    for n in sorted(set(entries) - cited):
        warns.append((entries[n], f"出典 {n} が本文で使われていない", "本文に [番号] を付けるか、出典から外す"))
    return errors, warns


def main():
    ap = argparse.ArgumentParser(description="調査メモの出典の検査")
    ap.add_argument("target", help="ファイル、または - （標準入力）")
    ap.add_argument("--strict", action="store_true", help="注意も不合格にする")
    ap.add_argument("--max-age-days", type=int, default=0, help="取得日がこの日数より古い出典を注意にする（既定は検査しない）")
    ap.add_argument("--today", help="基準日 YYYY-MM-DD（既定は実行日）")
    a = ap.parse_args()
    if a.target == "-":
        raw = sys.stdin.read()
    else:
        p = Path(a.target)
        if not p.is_file():
            print(f"{a.target} が見つかりません")
            return 2
        raw = p.read_text(encoding="utf-8", errors="replace")
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()

    errors, warns = check(raw, today, a.max_age_days)
    if errors is None:
        print("本文が空")
        return 2
    print(f"出典の検査: {a.target}")
    for title, items in (("不合格", errors), ("注意", warns)):
        if items:
            print(f"\n【{title}】")
        for ln, key, fix in items:
            print(f"  ● {f'{ln}行目 ' if ln else ''}{key}\n    → {fix}")
    if not errors and not warns:
        print("問題は検出されませんでした。")
    print(f"\n不合格 {len(errors)} 件 / 注意 {len(warns)} 件")
    print("内容の正しさと情報源の独立性は、この検査では分からない。")
    return 1 if errors or (a.strict and warns) else 0


if __name__ == "__main__":
    sys.exit(main())
