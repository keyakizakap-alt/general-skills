"""python-pptx で業務資料を組むための共通部品（16:9、白地、主色1色）。

- テキスト・図形・表は、すべて PowerPoint 上で編集できる形で置く（画像に焼き込まない）。
- ページ表記は保存時に「1 / N」の形で入れる（1始まり・ゼロ埋めなし）。
- 必要なもの: python-pptx（`pip install python-pptx`。導入は利用者の承認を得てから）。

使い方:
    import sys; sys.path.insert(0, '<このファイルのあるフォルダ>')
    from slide_kit import Deck, txt, table, note, MX, CW
    d = Deck('資料名', accent='0F5132', tint='E8F0EC', font='BIZ UDPGothic')
    s = d.page('章の名前', 'そのページで言いたいこと（1文）', '補足の1行')
    txt(s, MX, 2.0, CW, 1.0, '本文')
    note(s, '発表者ノート')
    d.save('output/deck.pptx')
"""
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt
from lxml import etree

# 既定は BIZ UDPゴシック（Windows 10 以降に標準搭載、OFL 版あり）。Deck(font=...) で変えられる。
# PDF を作る環境に同じフォントが無いと、別のフォントで描画され改行位置が変わる。
FONT = 'BIZ UDPGothic'
INK = '1E2430'
SUB = '5B6472'
LINE = 'DCE1E8'
SOFT = 'F4F6F9'
WHITE = 'FFFFFF'
WARN = 'B4441C'
WARN_TINT = 'FBEEE8'

W, H = 13.333, 7.5
MX = 0.6            # 左右の安全余白
CW = W - MX * 2     # 本文の最大幅

ALIGN = {'l': PP_ALIGN.LEFT, 'c': PP_ALIGN.CENTER, 'r': PP_ALIGN.RIGHT}
ANCHOR = {'t': MSO_ANCHOR.TOP, 'm': MSO_ANCHOR.MIDDLE, 'b': MSO_ANCHOR.BOTTOM}


def rgb(c):
    return RGBColor.from_string(c)


class Deck:
    def __init__(self, name, accent, tint, font=None):
        global FONT
        if font:
            FONT = font
        self.prs = Presentation()
        self.prs.slide_width = Inches(W)
        self.prs.slide_height = Inches(H)
        self.name = name
        self.accent = accent
        self.tint = tint
        self._pages = []

    # ---- ページ枠 -------------------------------------------------------
    def page(self, section, title, lead=None, footer=True):
        s = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = rgb(WHITE)
        if section:
            rect(s, MX, 0.46, 0.09, 0.22, self.accent)
            txt(s, MX + 0.2, 0.42, 9, 0.3, section, 12, self.accent, True)
        if title:
            txt(s, MX, 0.76, CW, 0.62, title, 26, INK, True)
        if lead:
            txt(s, MX, 1.42, CW, 0.4, lead, 15, SUB)
        if footer:
            rect(s, MX, 6.98, CW, 0.012, LINE)
            txt(s, MX, 7.06, 9, 0.25, self.name, 10, SUB)
            label = txt(s, W - MX - 1.5, 7.06, 1.5, 0.25, '', 10, SUB, align='r')
            self._pages.append((s, label))
        else:
            self._pages.append((s, None))
        return s

    def save(self, path):
        total = len(self._pages)
        for i, (_, label) in enumerate(self._pages, start=1):
            if label is not None:
                p = label.text_frame.paragraphs[0]
                r = p.add_run()
                r.text = f'{i} / {total}'
                style_run(r, 10, SUB, False)
        self.prs.save(path)


# ---- 基本図形 ------------------------------------------------------------
def _strip_style(shape):
    # テーマ既定の影・効果を外す。
    for el in list(shape._element):
        if el.tag.endswith('}style'):
            shape._element.remove(el)


def rect(s, x, y, w, h, fill, line=None, radius=None, line_w=0.75, dash=False):
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    q = s.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    _strip_style(q)
    if radius:
        q.adjustments[0] = radius
    if fill:
        q.fill.solid()
        q.fill.fore_color.rgb = rgb(fill)
    else:
        q.fill.background()
    if line:
        q.line.color.rgb = rgb(line)
        q.line.width = Pt(line_w)
        if dash:
            from pptx.enum.dml import MSO_LINE
            q.line.dash_style = MSO_LINE.DASH
    else:
        q.line.fill.background()
    return q


def oval(s, x, y, d, fill, label='', size=14, color=WHITE):
    q = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    _strip_style(q)
    q.fill.solid()
    q.fill.fore_color.rgb = rgb(fill)
    q.line.fill.background()
    if label:
        tf = q.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = label
        style_run(r, size, color, True)
    return q


def arrow(s, x, y, w, h, fill):
    q = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y), Inches(w), Inches(h))
    _strip_style(q)
    q.fill.solid()
    q.fill.fore_color.rgb = rgb(fill)
    q.line.fill.background()
    return q


def down_arrow(s, x, y, w, h, fill):
    q = s.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(x), Inches(y), Inches(w), Inches(h))
    _strip_style(q)
    q.fill.solid()
    q.fill.fore_color.rgb = rgb(fill)
    q.line.fill.background()
    return q


def hline(s, x, y, w, color=LINE, weight=0.012):
    return rect(s, x, y, w, weight, color)


def vline(s, x, y, h, color=LINE, weight=0.012):
    return rect(s, x, y, weight, h, color)


# ---- 文字 ----------------------------------------------------------------
def style_run(r, size, color, bold):
    f = r.font
    f.name = FONT
    f.size = Pt(size)
    f.bold = bold
    f.color.rgb = rgb(color)
    # 東アジア文字にも同じフォントを指定する。
    rPr = r._r.get_or_add_rPr()
    for tag in ('a:ea', 'a:cs'):
        el = rPr.find(qn(tag))
        if el is None:
            el = etree.SubElement(rPr, qn(tag))
        el.set('typeface', FONT)


def txt(s, x, y, w, h, content, size=16, color=INK, bold=False, align='l', anchor='t',
        gap=4, line=None):
    """content: 文字列（\\n で段落）または段落のリスト。

    段落は文字列か、(文字列, {'c': 色, 'b': 太字, 's': サイズ}) のリスト。
    """
    q = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = q.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = ANCHOR[anchor]
    paras = content.split('\n') if isinstance(content, str) else content
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = ALIGN[align]
        p.space_after = Pt(gap)
        if line:
            p.line_spacing = line
        runs = [(para, {})] if isinstance(para, str) else ([para] if isinstance(para, tuple) else para)
        for text, st in runs:
            if text == '':
                continue
            r = p.add_run()
            r.text = text
            style_run(r, st.get('s', size), st.get('c', color), st.get('b', bold))
    return q


def note(s, text):
    s.notes_slide.notes_text_frame.text = text


# ---- 表 ------------------------------------------------------------------
def _border(cell, side, color, w=9525):
    tcPr = cell._tc.get_or_add_tcPr()
    tag = {'b': 'a:lnB', 't': 'a:lnT', 'l': 'a:lnL', 'r': 'a:lnR'}[side]
    for old in tcPr.findall(qn(tag)):
        tcPr.remove(old)
    ln = etree.SubElement(tcPr, qn(tag), w=str(w if color else 0))
    if color:
        sf = etree.SubElement(ln, qn('a:solidFill'))
        etree.SubElement(sf, qn('a:srgbClr'), val=color)
    else:
        etree.SubElement(ln, qn('a:noFill'))


def table(s, x, y, col_w, rows, row_h=0.5, size=14, head_fill=None, head_color=INK,
          col_style=None, head_h=None, valign='m'):
    """rows[0] は見出し行。セルは文字列か txt() と同じ段落リスト。

    col_style: 列番号→{'c': 色, 'b': 太字, 'a': 'l'|'c'|'r'}。
    """
    col_style = col_style or {}
    n_r, n_c = len(rows), len(col_w)
    heights = [head_h or row_h] + [row_h] * (n_r - 1)
    gf = s.shapes.add_table(n_r, n_c, Inches(x), Inches(y), Inches(sum(col_w)), Inches(sum(heights)))
    tbl = gf.table
    # 既定の表スタイル（青い帯）を外す。
    tblPr = tbl._tbl.tblPr
    tblPr.set('firstRow', '0')
    tblPr.set('bandRow', '0')
    style_id = tblPr.find(qn('a:tableStyleId'))
    if style_id is None:
        style_id = etree.SubElement(tblPr, qn('a:tableStyleId'))
    style_id.text = '{2D5ABB26-0587-4C30-8999-92F81FD0307C}'
    for j, cw in enumerate(col_w):
        tbl.columns[j].width = Inches(cw)
    for i, hh in enumerate(heights):
        tbl.rows[i].height = Inches(hh)
    for i, row in enumerate(rows):
        for j in range(n_c):
            cell = tbl.cell(i, j)
            val = row[j] if j < len(row) else ''
            cs = col_style.get(j, {})
            is_head = i == 0
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb(head_fill if (is_head and head_fill) else WHITE)
            cell.margin_left = Inches(0.12)
            cell.margin_right = Inches(0.12)
            cell.margin_top = Inches(0.05)
            cell.margin_bottom = Inches(0.05)
            cell.vertical_anchor = ANCHOR[valign]
            tf = cell.text_frame
            tf.word_wrap = True
            paras = val.split('\n') if isinstance(val, str) else val
            for k, para in enumerate(paras):
                p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
                p.alignment = ALIGN[cs.get('a', 'l')]
                p.space_after = Pt(2)
                p.line_spacing = 1.1
                runs = [(para, {})] if isinstance(para, str) else ([para] if isinstance(para, tuple) else para)
                for text, st in runs:
                    if text == '':
                        continue
                    r = p.add_run()
                    r.text = text
                    if is_head:
                        style_run(r, st.get('s', size - 1), st.get('c', head_color), True)
                    else:
                        style_run(r, st.get('s', cs.get('s', size)), st.get('c', cs.get('c', INK)),
                                  st.get('b', cs.get('b', False)))
            for side in 'lrt':
                _border(cell, side, None)
            _border(cell, 'b', INK if is_head else LINE, 12700 if is_head else 9525)
    return gf


# ---- 構成図（階段） --------------------------------------------------------
def roadmap(s, accent, tint, steps, top=1.98, bottom=6.8, gap=0.18):
    """右に行くほど高くなる階段で、学ぶ順番を示す。

    steps: (ラベル, 見出し, 項目のリスト, ページ表記) のリスト。
    """
    n = len(steps)
    cw = (CW - gap * (n - 1)) / n
    rise = 0.45
    for i, (label, head, items, pages) in enumerate(steps):
        x = MX + i * (cw + gap)
        y = top + (n - 1 - i) * rise
        h = bottom - y
        rect(s, x, y, cw, h, tint)
        rect(s, x, y, cw, 0.07, accent)
        txt(s, x + 0.22, y + 0.25, cw - 0.44, 0.3, label, 12, accent, True)
        txt(s, x + 0.22, y + 0.58, cw - 0.44, 0.5, head, 20, INK, True)
        hline(s, x + 0.22, y + 1.18, cw - 0.44, accent, 0.015)
        txt(s, x + 0.22, y + 1.32, cw - 0.44, h - 1.9, ['・' + it for it in items], 14, INK, gap=5)
        txt(s, x + 0.22, bottom - 0.45, cw - 0.44, 0.3, pages, 12, SUB, align='r')
