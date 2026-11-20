# -*- coding: utf-8 -*-
"""Обёртка над python-docx: единый стиль документов «ТАРАН-ЭКСПРЕСС».

Документы сохраняются в .docx — такой файл Google Диск открывает как
Google Документ с сохранением заголовков, таблиц и рисунков.
"""
import os
import re

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

NAVY = RGBColor(0x1B, 0x3B, 0x6F)
INK = RGBColor(0x1A, 0x1F, 0x2B)
GREY = RGBColor(0x5A, 0x64, 0x78)
LIGHT = RGBColor(0x8A, 0x93, 0xA6)
GOLD = RGBColor(0xB0, 0x7A, 0x14)
BLUE = RGBColor(0x2F, 0x6F, 0xD0)
GREEN = RGBColor(0x1E, 0x7A, 0x4B)
RED = RGBColor(0xB3, 0x2D, 0x2D)

BODY_FONT = "Arial"
MONO_FONT = "Consolas"


def _shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _cell_margins(table, top=60, bottom=60, left=100, right=100):
    tblPr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, val in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblPr.append(mar)


def _borders(table, color="D5DBE6", size=4):
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(size))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tblPr.append(borders)


def _repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def _para_shading(par, hex_color):
    pPr = par._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    pPr.append(shd)


def _add_field(par, instr):
    run = par.add_run()
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), instr)
    run._r.addnext(fld)
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "1"
    r.append(t)
    fld.append(r)


class Doc:
    def __init__(self, title, subtitle, doc_no, version, date_str):
        self.title = title
        self.doc = Document()
        self._setup_page()
        self._setup_styles()
        self._footer()
        self._cover(title, subtitle, doc_no, version, date_str)

    # ------------------------------------------------------------------ база
    def _setup_page(self):
        sec = self.doc.sections[0]
        sec.page_width = Cm(21.0)
        sec.page_height = Cm(29.7)
        sec.left_margin = Cm(2.2)
        sec.right_margin = Cm(2.0)
        sec.top_margin = Cm(2.0)
        sec.bottom_margin = Cm(1.9)
        sec.header_distance = Cm(1.0)
        sec.footer_distance = Cm(0.9)

    def _setup_styles(self):
        st = self.doc.styles["Normal"]
        st.font.name = BODY_FONT
        st.font.size = Pt(10.5)
        st.font.color.rgb = INK
        st.paragraph_format.space_after = Pt(6)
        st.paragraph_format.line_spacing = 1.15
        rpr = st.element.get_or_add_rPr()
        rf = rpr.find(qn("w:rFonts"))
        if rf is None:
            rf = OxmlElement("w:rFonts")
            rpr.append(rf)
        for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rf.set(qn(attr), BODY_FONT)

        for name, size, color, before, after in (
            ("Heading 1", 18, NAVY, 20, 8),
            ("Heading 2", 13.5, NAVY, 14, 5),
            ("Heading 3", 11.5, RGBColor(0x33, 0x4E, 0x7A), 10, 4),
        ):
            s = self.doc.styles[name]
            s.font.name = BODY_FONT
            s.font.size = Pt(size)
            s.font.bold = True
            s.font.color.rgb = color
            s.paragraph_format.space_before = Pt(before)
            s.paragraph_format.space_after = Pt(after)
            s.paragraph_format.keep_with_next = True

    def _footer(self):
        sec = self.doc.sections[0]
        par = sec.footer.paragraphs[0]
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = par.add_run("ТАРАН-ЭКСПРЕСС 3.2  ·  документация проекта  ·  стр. ")
        r.font.size = Pt(8)
        r.font.color.rgb = LIGHT
        r.font.name = BODY_FONT
        _add_field(par, "PAGE")

    def _cover(self, title, subtitle, doc_no, version, date_str):
        for _ in range(3):
            self.doc.add_paragraph()
        p = self.doc.add_paragraph()
        r = p.add_run("ТАРАН-ЭКСПРЕСС")
        r.font.size = Pt(11)
        r.font.bold = True
        r.font.color.rgb = BLUE
        r.font.name = BODY_FONT
        p.paragraph_format.space_after = Pt(2)

        p = self.doc.add_paragraph()
        r = p.add_run(title)
        r.font.size = Pt(30)
        r.font.bold = True
        r.font.color.rgb = NAVY
        r.font.name = BODY_FONT
        p.paragraph_format.space_after = Pt(10)

        p = self.doc.add_paragraph()
        r = p.add_run(subtitle)
        r.font.size = Pt(12.5)
        r.font.color.rgb = GREY
        r.font.name = BODY_FONT
        p.paragraph_format.space_after = Pt(26)

        bar = self.doc.add_table(rows=1, cols=1)
        bar.autofit = False
        cell = bar.rows[0].cells[0]
        cell.width = Cm(16.8)
        _shade(cell, "1B3B6F")
        pr = cell.paragraphs[0]
        pr.paragraph_format.space_before = Pt(8)
        pr.paragraph_format.space_after = Pt(8)
        rr = pr.add_run("  Документ %s   ·   версия игры 3.2   ·   %s" % (doc_no, date_str))
        rr.font.size = Pt(10)
        rr.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        rr.font.name = BODY_FONT
        self.doc.add_paragraph()

        meta = [
            ("Проект", "«ТАРАН-ЭКСПРЕСС» — кликер-аркада на Pygame про машиниста вокзала"),
            ("Платформы", "Windows / Linux / macOS (pygame-ce), Android (APK), браузер (WebAssembly / PWA)"),
            ("Исходный код", "game.py, progression.py, prog_ui.py, пакет taran/, mobile/"),
            ("Статус", "версия 3.2 — функционально завершена, идёт тестирование и полировка"),
            ("Дата", date_str),
        ]
        for k, v in meta:
            p = self.doc.add_paragraph()
            p.paragraph_format.space_after = Pt(5)
            r1 = p.add_run(k + ":  ")
            r1.font.bold = True
            r1.font.size = Pt(9.5)
            r1.font.color.rgb = GREY
            r1.font.name = BODY_FONT
            r2 = p.add_run(v)
            r2.font.size = Pt(9.5)
            r2.font.color.rgb = INK
            r2.font.name = BODY_FONT

        self.page_break()

    # --------------------------------------------------------------- разметка
    def h1(self, text):
        p = self.doc.add_heading(text, level=1)
        for r in p.runs:
            r.font.name = BODY_FONT
            r.font.color.rgb = NAVY
        self._hrule(NAVY)
        return p

    def h2(self, text):
        p = self.doc.add_heading(text, level=2)
        for r in p.runs:
            r.font.name = BODY_FONT
            r.font.color.rgb = NAVY
        return p

    def h3(self, text):
        p = self.doc.add_heading(text, level=3)
        for r in p.runs:
            r.font.name = BODY_FONT
        return p

    def _hrule(self, color, size=12):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(8)
        pPr = p._p.get_or_add_pPr()
        bdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), str(size))
        bottom.set(qn("w:space"), "1")
        bottom.set(qn("w:color"), str(color))
        bdr.append(bottom)
        pPr.append(bdr)

    def _runs(self, text, size=None, color=None, bold=False, italic=False):
        """Мини-разметка: **жирный**, `код`."""
        out = []
        parts = re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text)
        for part in parts:
            if not part:
                continue
            if part.startswith("**") and part.endswith("**"):
                out.append((part[2:-2], True, False, False))
            elif part.startswith("`") and part.endswith("`"):
                out.append((part[1:-1], False, True, True))
            else:
                out.append((part, bold, italic, False))
        return out

    def p(self, text, lead=None, space=6, align=None, size=None, color=None, italic=False):
        par = self.doc.add_paragraph()
        par.paragraph_format.space_after = Pt(space)
        if align == "center":
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif align == "just":
            par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if lead:
            r = par.add_run(lead + " ")
            r.font.bold = True
            r.font.size = Pt(size or 10.5)
            r.font.color.rgb = color or INK
            r.font.name = BODY_FONT
        for txt, bold, mono, code in self._runs(text, bold=italic):
            r = par.add_run(txt)
            r.font.bold = bold
            r.font.italic = code
            r.font.size = Pt((size or 10.5) - (0.5 if mono else 0))
            r.font.name = MONO_FONT if mono else BODY_FONT
            r.font.color.rgb = color or INK
        return par

    def bullets(self, items, size=10.5):
        for it in items:
            par = self.doc.add_paragraph(style="List Bullet")
            par.paragraph_format.space_after = Pt(2)
            par.paragraph_format.left_indent = Cm(0.7)
            for txt, bold, mono, code in self._runs(it):
                r = par.add_run(txt)
                r.font.bold = bold
                r.font.italic = code
                r.font.size = Pt(size - (0.5 if mono else 0))
                r.font.name = MONO_FONT if mono else BODY_FONT
                r.font.color.rgb = INK

    def steps(self, items):
        for i, it in enumerate(items, 1):
            par = self.doc.add_paragraph()
            par.paragraph_format.left_indent = Cm(0.8)
            par.paragraph_format.first_line_indent = Cm(-0.8)
            par.paragraph_format.space_after = Pt(3)
            r = par.add_run("%d.  " % i)
            r.font.bold = True
            r.font.color.rgb = BLUE
            r.font.size = Pt(10.5)
            r.font.name = BODY_FONT
            for txt, bold, mono, code in self._runs(it):
                rr = par.add_run(txt)
                rr.font.bold = bold
                rr.font.italic = code
                rr.font.size = Pt(10.5 - (0.5 if mono else 0))
                rr.font.name = MONO_FONT if mono else BODY_FONT
                rr.font.color.rgb = INK

    def table(self, headers, rows, widths=None, caption=None, size=8.6, header_fill="1B3B6F",
              align_center=None, zebra=True):
        if caption:
            p = self.doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(3)
            r = p.add_run(caption)
            r.font.size = Pt(8.6)
            r.font.bold = True
            r.font.color.rgb = GREY
            r.font.name = BODY_FONT
        t = self.doc.add_table(rows=1, cols=len(headers))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        _borders(t)
        _cell_margins(t)
        if widths:
            for i, w in enumerate(widths):
                t.columns[i].width = Cm(w)
            tblPr = t._tbl.tblPr
            tblW = OxmlElement("w:tblW")
            tblW.set(qn("w:type"), "dxa")
            tblW.set(qn("w:w"), str(int(sum(widths) * 567)))
            tblPr.append(tblW)
        hdr = t.rows[0]
        _repeat_header(hdr)
        for i, h in enumerate(headers):
            cell = hdr.cells[i]
            cell.width = Cm(widths[i]) if widths else Cm(16.8 / len(headers))
            _shade(cell, header_fill)
            par = cell.paragraphs[0]
            par.paragraph_format.space_after = Pt(0)
            r = par.add_run(str(h))
            r.font.bold = True
            r.font.size = Pt(size)
            r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            r.font.name = BODY_FONT
        for ri, row in enumerate(rows):
            cells = t.add_row().cells
            for i, val in enumerate(row):
                cell = cells[i]
                cell.width = Cm(widths[i]) if widths else Cm(16.8 / len(headers))
                if zebra and ri % 2 == 1:
                    _shade(cell, "F2F5FA")
                par = cell.paragraphs[0]
                par.paragraph_format.space_after = Pt(0)
                par.paragraph_format.line_spacing = 1.0
                if align_center and i in align_center:
                    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for txt, bold, mono, code in self._runs(str(val)):
                    r = par.add_run(txt)
                    r.font.bold = bold
                    r.font.italic = code
                    r.font.size = Pt(size - (0.4 if mono else 0))
                    r.font.name = MONO_FONT if mono else BODY_FONT
                    r.font.color.rgb = INK
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)
        return t

    def callout(self, text, kind="note"):
        colors = {"note": ("EAF2FD", "2F6FD0"), "warn": ("FDF3E3", "B07A14"),
                  "ok": ("EAF7EF", "1E7A4B"), "risk": ("FBECEC", "B32D2D")}
        fill, bar = colors.get(kind, colors["note"])
        t = self.doc.add_table(rows=1, cols=1)
        t.autofit = False
        cell = t.rows[0].cells[0]
        cell.width = Cm(16.8)
        _shade(cell, fill)
        tcPr = cell._tc.get_or_add_tcPr()
        borders = OxmlElement("w:tcBorders")
        for edge, sz, col in (("left", 24, bar), ("top", 4, fill), ("bottom", 4, fill), ("right", 4, fill)):
            el = OxmlElement(f"w:{edge}")
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), str(sz))
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), col)
            borders.append(el)
        tcPr.append(borders)
        par = cell.paragraphs[0]
        par.paragraph_format.space_after = Pt(2)
        for txt, bold, mono, code in self._runs(text):
            r = par.add_run(txt)
            r.font.size = Pt(9.5)
            r.font.bold = bold
            r.font.italic = code
            r.font.name = MONO_FONT if mono else BODY_FONT
            r.font.color.rgb = INK
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def code(self, text):
        t = self.doc.add_table(rows=1, cols=1)
        t.autofit = False
        cell = t.rows[0].cells[0]
        cell.width = Cm(16.8)
        _shade(cell, "F4F6FA")
        par = cell.paragraphs[0]
        par.paragraph_format.space_after = Pt(0)
        par.paragraph_format.line_spacing = 1.0
        for i, line in enumerate(text.strip("\n").split("\n")):
            if i:
                par.add_run().add_break()
            r = par.add_run(line)
            r.font.size = Pt(8)
            r.font.name = MONO_FONT
            r.font.color.rgb = RGBColor(0x24, 0x2C, 0x3A)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def figure(self, path, caption, width=16.4):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
        p.add_run().add_picture(path, width=Cm(width))
        cap = self.doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_after = Pt(10)
        r = cap.add_run(caption)
        r.font.size = Pt(8.5)
        r.font.italic = True
        r.font.color.rgb = GREY
        r.font.name = BODY_FONT

    def toc(self, items):
        """Ручное оглавление: пары (уровень, текст)."""
        self.h2("Содержание")
        for lvl, text in items:
            par = self.doc.add_paragraph()
            par.paragraph_format.space_after = Pt(1.5)
            par.paragraph_format.left_indent = Cm(0.0 if lvl == 1 else 0.7)
            r = par.add_run(text)
            r.font.size = Pt(9.5 if lvl == 1 else 9)
            r.font.bold = lvl == 1
            r.font.color.rgb = NAVY if lvl == 1 else INK
            r.font.name = BODY_FONT
        self.page_break()

    def page_break(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.doc.save(path)
        return path
