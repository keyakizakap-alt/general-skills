#!/usr/bin/env python3
"""PowerPoint 資料の体裁を機械的に検査する。

確認すること:
  1. 枚数（--slides を渡したとき）
  2. 各スライドに発表者ノートがあるか（--min-notes 文字以上。0 で検査しない）
  3. ページ表記「i / N」が各スライドにあるか（--no-page-label で検査しない）
  4. ゼロ埋めの番号（01、02 など）や「0 / N」が無いか。数量としての 0（0件、0時間）は対象外
  5. 同じ名前の PDF があれば、ページ数が一致するか（pdfinfo が無ければ簡易な数え方）

必要なもの: python-pptx。PDF の検査は pdfinfo（poppler-utils）があれば使う。
終了コード: 0 = 問題なし、1 = 問題あり、2 = 実行できない（python-pptx が無い等）。

例:
    python3 check_deck.py output/report.pptx --slides 9
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ZERO_PAD = re.compile(r'(?<![\d.:/\-])0\d(?![\d.:])')
ZERO_PAGE = re.compile(r'(?<!\d)0\s*/\s*\d+')


def slide_texts(slide):
    texts = []
    for shape in slide.shapes:
        if shape.has_text_frame:
            texts.append(shape.text_frame.text)
        if getattr(shape, 'has_table', False) and shape.has_table:
            for row in shape.table.rows:
                for cell in row.cells:
                    texts.append(cell.text)
    return texts


def pdf_pages(pdf):
    try:
        out = subprocess.run(['pdfinfo', str(pdf)], capture_output=True, text=True, check=True).stdout
        return int(re.search(r'Pages:\s+(\d+)', out).group(1))
    except (FileNotFoundError, subprocess.CalledProcessError, AttributeError):
        return len(re.findall(rb'/Type\s*/Page(?!s)', pdf.read_bytes()))


def check(path, slides=None, min_notes=30, page_label=True):
    from pptx import Presentation
    prs = Presentation(str(path))
    total = len(prs.slides)
    problems = []
    if slides is not None and total != slides:
        problems.append(f'枚数が {total} 枚（想定 {slides} 枚）')
    for i, slide in enumerate(prs.slides, start=1):
        texts = slide_texts(slide)
        if min_notes:
            notes = slide.notes_slide.notes_text_frame.text.strip() if slide.has_notes_slide else ''
            if len(notes) < min_notes:
                problems.append(f'{i} 枚目: 発表者ノートが {len(notes)} 文字（{min_notes} 文字以上にする）')
        if page_label and not any(t.strip() == f'{i} / {total}' for t in texts):
            problems.append(f'{i} 枚目: ページ表記「{i} / {total}」が無い')
        for t in texts:
            m = ZERO_PAD.search(t) or ZERO_PAGE.search(t)
            if m:
                problems.append(f'{i} 枚目: ゼロ埋め・0始まりらしき表記「{m.group(0)}」: {t[:40]!r}')
    pdf = path.with_suffix('.pdf')
    if pdf.exists():
        pages = pdf_pages(pdf)
        if pages != total:
            problems.append(f'{pdf.name} が {pages} ページ（PowerPoint は {total} 枚）。PDF を作り直す')
    return total, problems


def main(argv=None):
    ap = argparse.ArgumentParser(description='PowerPoint 資料の体裁を検査する')
    ap.add_argument('pptx', type=Path)
    ap.add_argument('--slides', type=int, help='想定する枚数')
    ap.add_argument('--min-notes', type=int, default=30, help='発表者ノートの最小文字数（0 で検査しない）')
    ap.add_argument('--no-page-label', action='store_true', help='ページ表記「i / N」を検査しない')
    args = ap.parse_args(argv)
    try:
        import pptx  # noqa: F401
    except ImportError:
        print('実行できない: python-pptx が無い。導入は利用者の承認を得てから行う（pip install python-pptx）')
        return 2
    if not args.pptx.is_file():
        print(f'実行できない: {args.pptx} が無い')
        return 2
    total, problems = check(args.pptx, args.slides, args.min_notes, not args.no_page_label)
    print(f'{args.pptx.name}: {total} 枚')
    for p in problems:
        print(f'  - {p}')
    print('問題なし' if not problems else f'問題 {len(problems)} 件')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
