# -*- coding: utf-8 -*-
"""Сборка документов комплекта «ТАРАН-ЭКСПРЕСС» по требованиям оформления.

A4, Times New Roman 14 pt, интервал 1,5, выравнивание по ширине, поля 2 см,
титульный лист, автоматическое оглавление (поле TOC), нумерация страниц,
подписи к таблицам и рисункам.
"""
import os

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONT = "Times New Roman"
MONO = "Consolas"
BLACK = RGBColor(0x00, 0x00, 0x00)
NAVY = RGBColor(0x1F, 0x36, 0x5D)
GREY = RGBColor(0x44, 0x4A, 0x55)
LIGHT = RGBColor(0x6B, 0x72, 0x80)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

AUTHOR = "Серик Жанторе Батырханулы"
GROUP = "3-26п"
PROJECT = "«ТАРАН-ЭКСПРЕСС»"
VERSION = "3.2"
YEAR = "2026"


def _set_run_font(run, name=FONT, size=None, bold=None, italic=None, color=None):
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(attr), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color


def _shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _cell_margins(table, top=50, bottom=50, left=90, right=90):
    tblPr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, val in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblPr.append(mar)


def _borders(table, color="7F7F7F", size=4):
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


def _para_border(par, side="left", color="1F365D", size=18, space=6):
    pPr = par._p.get_or_add_pPr()
    bdr = pPr.find(qn("w:pBdr"))
    if bdr is None:
        bdr = OxmlElement("w:pBdr")
        pPr.append(bdr)
    el = OxmlElement(f"w:{side}")
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), str(size))
    el.set(qn("w:space"), str(space))
    el.set(qn("w:color"), color)
    bdr.append(el)


def _field(par, instr, placeholder="1"):
    run = par.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    run._r.append(fld_begin)

    run2 = par.add_run()
    instr_el = OxmlElement("w:instrText")
    instr_el.set(qn("xml:space"), "preserve")
    instr_el.text = instr
    run2._r.append(instr_el)

    run3 = par.add_run()
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    run3._r.append(fld_sep)

    run4 = par.add_run(placeholder)

    run5 = par.add_run()
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run5._r.append(fld_end)
    return run4


class Doc:
    def __init__(self, title, subtitle, doc_no, date_str="ноябрь 2026", short="документация"):
        self.title = title
        self.short = short
        self.doc_no = doc_no
        self.tcount = 0
        self.fcount = 0
        self.content_width = 17.0
        self.doc = Document()
        self.doc.core_properties.title = title
        self.doc.core_properties.author = AUTHOR
        self.doc.core_properties.subject = "Проектная документация «ТАРАН-ЭКСПРЕСС» 3.2"
        self.doc.core_properties.category = "Учебная проектная документация"
        self.doc.core_properties.comments = "Документ подготовлен по материалам проекта"
        self._setup_page()
        self._setup_styles()
        self._setup_footer()
        self._update_fields()
        self._cover(subtitle, doc_no, date_str)
        self.page_break()
        self._toc_page()
        self.page_break()

    # ------------------------------------------------------------------ база
    def _setup_page(self):
        sec = self.doc.sections[0]
        sec.orientation = WD_ORIENT.PORTRAIT
        sec.page_width = Cm(21.0)
        sec.page_height = Cm(29.7)
        sec.left_margin = Cm(2.0)
        sec.right_margin = Cm(2.0)
        sec.top_margin = Cm(2.0)
        sec.bottom_margin = Cm(2.0)
        sec.header_distance = Cm(1.0)
        sec.footer_distance = Cm(1.0)

    def _setup_styles(self):
        st = self.doc.styles["Normal"]
        st.font.name = FONT
        st.font.size = Pt(14)
        st.font.color.rgb = BLACK
        rpr = st.element.get_or_add_rPr()
        rf = rpr.find(qn("w:rFonts"))
        if rf is None:
            rf = OxmlElement("w:rFonts")
            rpr.insert(0, rf)
        for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rf.set(qn(attr), FONT)
        lang = OxmlElement("w:lang")
        lang.set(qn("w:val"), "ru-RU")
        lang.set(qn("w:eastAsia"), "ru-RU")
        lang.set(qn("w:bidi"), "ar-SA")
        rpr.append(lang)

        pf = st.paragraph_format
        pf.line_spacing = 1.5
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.first_line_indent = Cm(1.25)

        for name, size, before, after, center in (
            ("Heading 1", 18, 12, 8, True),
            ("Heading 2", 16, 12, 4, False),
            ("Heading 3", 14, 8, 2, False),
        ):
            s = self.doc.styles[name]
            s.font.name = FONT
            s.font.size = Pt(size)
            s.font.bold = True
            s.font.color.rgb = BLACK
            s.font.italic = False
            s.paragraph_format.space_before = Pt(before)
            s.paragraph_format.space_after = Pt(after)
            s.paragraph_format.line_spacing = 1.5
            s.paragraph_format.first_line_indent = Cm(0)
            s.paragraph_format.keep_with_next = True
            s.paragraph_format.alignment = (
                WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT)
            srpr = s.element.get_or_add_rPr()
            srf = srpr.find(qn("w:rFonts"))
            if srf is None:
                srf = OxmlElement("w:rFonts")
                srpr.insert(0, srf)
            for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
                srf.set(qn(attr), FONT)

        for name in ("Caption", "List Bullet", "List Number"):
            try:
                s = self.doc.styles[name]
                s.font.name = FONT
                s.font.size = Pt(12)
            except KeyError:
                pass

    def _setup_footer(self):
        sec = self.doc.sections[0]
        sec.different_first_page_header_footer = True
        par = sec.footer.paragraphs[0]
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.first_line_indent = Cm(0)
        par.paragraph_format.line_spacing = 1.0
        r = par.add_run(f"{PROJECT} 3.2  ·  {self.short}  ·  стр. ")
        _set_run_font(r, FONT, 10, color=LIGHT)
        _field(par, "PAGE", "2")
        for rr in par.runs:
            _set_run_font(rr, FONT, 10, color=LIGHT)

    def _update_fields(self):
        settings = self.doc.settings.element
        update = OxmlElement("w:updateFields")
        update.set(qn("w:val"), "true")
        settings.append(update)

    def _cover(self, subtitle, doc_no, date_str):
        # Верхняя строка
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(36)
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run("ПРОЕКТНАЯ ДОКУМЕНТАЦИЯ")
        _set_run_font(r, FONT, 12, bold=True, color=GREY)

        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(PROJECT)
        _set_run_font(r, FONT, 28, bold=True, color=BLACK)

        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_after = Pt(40)
        r = p.add_run("кликер-аркада на Pygame")
        _set_run_font(r, FONT, 14, italic=True, color=GREY)

        # Линия
        p = self.doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_after = Pt(26)
        _para_border(p, "bottom", "1F365D", 12, 1)

        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_after = Pt(10)
        r = p.add_run(self.title)
        _set_run_font(r, FONT, 24, bold=True, color=BLACK)

        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_after = Pt(56)
        r = p.add_run(subtitle)
        _set_run_font(r, FONT, 14, italic=True, color=GREY)

        # Данные документа
        meta = [
            ("Документ", f"№ {doc_no}"),
            ("Версия игры", VERSION),
            ("Дата", date_str),
            ("Выполнил", AUTHOR),
            ("Группа", GROUP),
            ("Проект", "train_game_v3.0"),
        ]
        t = self.doc.add_table(rows=0, cols=2)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        for k, v in meta:
            cells = t.add_row().cells
            cells[0].width = Cm(4.6)
            cells[1].width = Cm(11.4)
            p0 = cells[0].paragraphs[0]
            p0.paragraph_format.first_line_indent = Cm(0)
            p0.paragraph_format.line_spacing = 1.15
            p0.paragraph_format.space_after = Pt(2)
            r0 = p0.add_run(k)
            _set_run_font(r0, FONT, 12, bold=True, color=GREY)
            p1 = cells[1].paragraphs[0]
            p1.paragraph_format.first_line_indent = Cm(0)
            p1.paragraph_format.line_spacing = 1.15
            p1.paragraph_format.space_after = Pt(2)
            r1 = p1.add_run(v)
            _set_run_font(r1, FONT, 12, color=BLACK)

        # Низ титульного листа
        p = self.doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(96)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(YEAR)
        _set_run_font(r, FONT, 12, color=LIGHT)

    def _toc_page(self):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_after = Pt(12)
        r = p.add_run("СОДЕРЖАНИЕ")
        _set_run_font(r, FONT, 16, bold=True, color=BLACK)

        p = self.doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.line_spacing = 1.5
        _field(p, 'TOC \\o "1-3" \\h \\z \\u',
               "Оглавление обновляется при открытии документа в Word (Ctrl+A → F9).")

        p = self.doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(18)
        r = p.add_run("Примечание. В Word оглавление обновляется автоматически при открытии; "
                      "если этого не произошло, выделите всё (Ctrl+A) и нажмите F9.")
        _set_run_font(r, FONT, 11, italic=True, color=LIGHT)

    # --------------------------------------------------------------- разметка
    def h1(self, text):
        p = self.doc.add_heading(text, level=1)
        for r in p.runs:
            _set_run_font(r, FONT, 18, bold=True, color=BLACK)
        return p

    def h2(self, text):
        p = self.doc.add_heading(text, level=2)
        for r in p.runs:
            _set_run_font(r, FONT, 16, bold=True, color=NAVY)
        return p

    def h3(self, text):
        p = self.doc.add_heading(text, level=3)
        for r in p.runs:
            _set_run_font(r, FONT, 14, bold=True, italic=True, color=BLACK)
        return p

    def p(self, text, align="just", size=14, bold=False, italic=False, color=None,
          indent=True, space_after=0, space_before=0, line=1.5):
        par = self.doc.add_paragraph()
        pf = par.paragraph_format
        pf.line_spacing = line
        pf.space_after = Pt(space_after)
        pf.space_before = Pt(space_before)
        pf.first_line_indent = Cm(1.25) if indent else Cm(0)
        pf.alignment = {"just": WD_ALIGN_PARAGRAPH.JUSTIFY,
                        "left": WD_ALIGN_PARAGRAPH.LEFT,
                        "center": WD_ALIGN_PARAGRAPH.CENTER,
                        "right": WD_ALIGN_PARAGRAPH.RIGHT}.get(align, WD_ALIGN_PARAGRAPH.JUSTIFY)
        for chunk, b, mono in self._runs(text, bold):
            r = par.add_run(chunk)
            _set_run_font(r, MONO if mono else FONT, (size - 2) if mono else size,
                          bold=b, italic=italic, color=color)
        return par

    def _runs(self, text, base_bold=False):
        """Мини-разметка: **жирный** и `код`."""
        import re
        out = []
        for part in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text):
            if not part:
                continue
            if part.startswith("**") and part.endswith("**"):
                out.append((part[2:-2], True, False))
            elif part.startswith("`") and part.endswith("`"):
                out.append((part[1:-1], True, True))
            else:
                out.append((part, base_bold, False))
        return out

    def bullets(self, items, size=14):
        for it in items:
            par = self.doc.add_paragraph(style="List Bullet")
            pf = par.paragraph_format
            pf.line_spacing = 1.5
            pf.space_after = Pt(0)
            pf.first_line_indent = Cm(0)
            pf.left_indent = Cm(1.0)
            pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            for chunk, b, mono in self._runs(it):
                r = par.add_run(chunk)
                _set_run_font(r, MONO if mono else FONT, (size - 2) if mono else size,
                              bold=b, color=BLACK)

    def steps(self, items, size=14):
        for i, it in enumerate(items, 1):
            par = self.doc.add_paragraph()
            pf = par.paragraph_format
            pf.line_spacing = 1.5
            pf.space_after = Pt(2)
            pf.left_indent = Cm(1.0)
            pf.first_line_indent = Cm(-1.0)
            pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = par.add_run(f"{i}.  ")
            _set_run_font(r, FONT, size, bold=True, color=NAVY)
            for chunk, b, mono in self._runs(it):
                rr = par.add_run(chunk)
                _set_run_font(rr, MONO if mono else FONT, (size - 2) if mono else size,
                              bold=b, color=BLACK)

    def caption(self, text):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(8)
        r = p.add_run(text)
        _set_run_font(r, FONT, 12, italic=True, color=BLACK)

    def table(self, headers, rows, widths=None, caption=None, size=11,
              align_center=None, header_fill="DCE6F1", first_col_bold=False):
        if caption:
            self.tcount += 1
            p = self.doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = True
            r = p.add_run(f"Таблица {self.tcount} — {caption}")
            _set_run_font(r, FONT, 12, bold=False, italic=True, color=BLACK)
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
            cell.width = Cm(widths[i]) if widths else Cm(self.content_width / len(headers))
            _shade(cell, header_fill)
            par = cell.paragraphs[0]
            par.paragraph_format.first_line_indent = Cm(0)
            par.paragraph_format.space_after = Pt(0)
            par.paragraph_format.line_spacing = 1.0
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = par.add_run(str(h))
            _set_run_font(r, FONT, size, bold=True, color=BLACK)
        for ri, row in enumerate(rows):
            cells = t.add_row().cells
            for i, val in enumerate(row):
                cell = cells[i]
                cell.width = Cm(widths[i]) if widths else Cm(self.content_width / len(headers))
                if ri % 2 == 1:
                    _shade(cell, "F2F2F2")
                par = cell.paragraphs[0]
                par.paragraph_format.first_line_indent = Cm(0)
                par.paragraph_format.space_after = Pt(0)
                par.paragraph_format.line_spacing = 1.0
                if align_center and i in align_center:
                    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for chunk, b, mono in self._runs(str(val)):
                    r = par.add_run(chunk)
                    _set_run_font(
                        r,
                        MONO if mono else FONT,
                        (size - 2) if mono else size,
                        bold=(b or (first_col_bold and i == 0)),
                        color=BLACK,
                    )
        # Небольшой отступ после таблицы
        p = self.doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.0
        return t

    def figure(self, path, caption, width=None):
        self.fcount += 1
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.keep_with_next = True
        p.add_run().add_picture(path, width=Cm(width or self.content_width))
        self.caption(f"Рисунок {self.fcount} — {caption}")

    def figure_fit(self, path, caption, max_w=None, max_h=21.5):
        """Вставляет рисунок целиком: ширина ограничена полем, высота — страницей."""
        from docx.image.image import Image as DocxImage
        img = DocxImage.from_file(path)
        w_cm = img.width.cm
        h_cm = img.height.cm
        width = max_w or self.content_width
        if w_cm > 0 and width * h_cm / w_cm > max_h:
            width = max_h * w_cm / h_cm
        return self.figure(path, caption, width=width)

    def callout(self, text, kind="note"):
        fill = {"note": "E8EEF7", "warn": "FBF0DC", "ok": "E6F2E9", "risk": "F8E4E4"}.get(kind, "E8EEF7")
        t = self.doc.add_table(rows=1, cols=1)
        t.autofit = False
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = t.rows[0].cells[0]
        cell.width = Cm(self.content_width)
        _shade(cell, fill)
        tcPr = cell._tc.get_or_add_tcPr()
        borders = OxmlElement("w:tcBorders")
        for edge, sz, col in (("left", 24, "1F365D"), ("top", 4, fill),
                              ("bottom", 4, fill), ("right", 4, fill)):
            el = OxmlElement(f"w:{edge}")
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), str(sz))
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), col)
            borders.append(el)
        tcPr.append(borders)
        par = cell.paragraphs[0]
        par.paragraph_format.first_line_indent = Cm(0)
        par.paragraph_format.line_spacing = 1.15
        par.paragraph_format.space_after = Pt(2)
        par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        for chunk, b, mono in self._runs(text):
            r = par.add_run(chunk)
            _set_run_font(r, MONO if mono else FONT, 12 - (1 if mono else 0),
                          bold=b, color=BLACK)
        p = self.doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.0

    def code(self, text, size=9):
        t = self.doc.add_table(rows=1, cols=1)
        t.autofit = False
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = t.rows[0].cells[0]
        cell.width = Cm(self.content_width)
        _shade(cell, "F2F2F2")
        par = cell.paragraphs[0]
        par.paragraph_format.first_line_indent = Cm(0)
        par.paragraph_format.space_after = Pt(0)
        par.paragraph_format.line_spacing = 1.0
        par.alignment = WD_ALIGN_PARAGRAPH.LEFT
        lines = text.strip("\n").split("\n")
        for i, line in enumerate(lines):
            if i:
                par.add_run().add_break()
            r = par.add_run(line)
            _set_run_font(r, MONO, size, color=BLACK)
        p = self.doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.0

    # -------------------------------------------------------------- страницы
    def page_break(self):
        self.doc.add_page_break()

    def landscape(self):
        sec = self.doc.add_section(WD_SECTION.NEW_PAGE)
        sec.orientation = WD_ORIENT.LANDSCAPE
        sec.page_width = Cm(29.7)
        sec.page_height = Cm(21.0)
        sec.left_margin = Cm(2.0)
        sec.right_margin = Cm(2.0)
        sec.top_margin = Cm(2.0)
        sec.bottom_margin = Cm(2.0)
        sec.footer_distance = Cm(1.0)
        self.content_width = 25.7
        return sec

    def portrait(self):
        sec = self.doc.add_section(WD_SECTION.NEW_PAGE)
        sec.orientation = WD_ORIENT.PORTRAIT
        sec.page_width = Cm(21.0)
        sec.page_height = Cm(29.7)
        sec.left_margin = Cm(2.0)
        sec.right_margin = Cm(2.0)
        sec.top_margin = Cm(2.0)
        sec.bottom_margin = Cm(2.0)
        sec.footer_distance = Cm(1.0)
        self.content_width = 17.0
        return sec

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.doc.save(path)
        return path
