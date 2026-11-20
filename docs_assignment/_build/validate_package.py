# -*- coding: utf-8 -*-
"""Проверка собранного комплекта: файлы, DOCX, XLSX, схемы и скриншоты."""
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from docx import Document
from docx.shared import Cm
from openpyxl import load_workbook

import assign_data as D

PLACEHOLDERS = ("TODO", "TBD", "Lorem ipsum", "заглушка", "placeholder",
                "XXX", "???", "Шаблон", "шаблонный текст")
errors = []
warnings = []


def check(cond, msg):
    if cond:
        print("  OK  ", msg)
    else:
        print("  FAIL", msg)
        errors.append(msg)


def check_docx(path):
    name = os.path.basename(path)
    with open(path, "rb") as f:
        head = f.read(4)
    check(head == b"PK\x03\x04", f"{name}: файл DOCX открывается как ZIP")
    doc = Document(path)
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    check(len(doc.paragraphs) >= 10, f"{name}: содержит текст ({len(doc.paragraphs)} абзацев)")
    check(len(doc.inline_shapes) >= 0, f"{name}: изображений {len(doc.inline_shapes)}")
    check(len(doc.sections) >= 1, f"{name}: секций {len(doc.sections)}")

    sec = doc.sections[0]
    check(abs(sec.page_width.cm - 21.0) < 0.1 and abs(sec.page_height.cm - 29.7) < 0.1,
          f"{name}: первый раздел A4")
    check(all(abs(x.cm - 2.0) < 0.1 for x in
              (sec.left_margin, sec.right_margin, sec.top_margin, sec.bottom_margin)),
          f"{name}: поля 2 см")

    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
        footers = [n for n in z.namelist()
                   if n.startswith("word/footer") and n.endswith(".xml")]
        footer_xml = "".join(z.read(n).decode("utf-8", "ignore") for n in footers)
    check("TOC" in xml and "instrText" in xml,
          f"{name}: поле оглавления TOC")
    check("PAGE" in footer_xml, f"{name}: поле номера страницы в нижнем колонтитуле")

    hits = [p for p in PLACEHOLDERS if p.lower() in text.lower()]
    check(not hits, f"{name}: нет маркеров-заглушек" + (f" ({hits})" if hits else ""))

    # Заголовок 1 уровня должен быть хотя бы один.
    h1 = sum(1 for p in doc.paragraphs if p.style.name == "Heading 1")
    check(h1 >= 3, f"{name}: разделов Heading 1 — {h1}")

    # Титульные данные в core properties.
    cp = doc.core_properties
    check(bool(cp.title), f"{name}: заполнено свойство title")
    check(cp.author == D.AUTHOR, f"{name}: автор в свойствах")
    return len(doc.inline_shapes), len(doc.tables)


def main():
    print("ПАКЕТ:", D.OUT)
    print("\n1. Файлы манифеста")
    docx_count = 0
    xlsx_count = 0
    for num, folder, fname, _what in D.MANIFEST:
        path = os.path.join(D.OUT, folder, fname)
        check(os.path.exists(path), f"{num}: {folder}\\{fname}")
        if fname.lower().endswith(".docx"):
            docx_count += 1
        elif fname.lower().endswith(".xlsx"):
            xlsx_count += 1
    check(docx_count == 21, f"документов DOCX: {docx_count}")
    check(xlsx_count == 1, f"книг XLSX: {xlsx_count}")

    print("\n2. Открытие и оформление DOCX")
    images = tables = 0
    for _num, folder, fname, _what in D.MANIFEST:
        if not fname.lower().endswith(".docx"):
            continue
        path = os.path.join(D.OUT, folder, fname)
        if not os.path.exists(path):
            continue
        img, tab = check_docx(path)
        images += img
        tables += tab

    print("\n3. Диаграммы")
    for key, fname in D.DIAGRAMS.items():
        png = os.path.join(D.DIAG, fname)
        drawio = png[:-4] + ".drawio"
        check(os.path.exists(png) and os.path.getsize(png) > 20000,
              f"{fname}: PNG существует и не пуст")
        check(os.path.exists(drawio) and os.path.getsize(drawio) > 3000,
              f"{fname[:-4]}.drawio: редактируемая схема существует")
        if os.path.exists(png):
            with open(png, "rb") as f:
                sig = f.read(8)
            check(sig == b"\x89PNG\r\n\x1a\n", f"{fname}: сигнатура PNG")
        if os.path.exists(drawio):
            with open(drawio, encoding="utf-8") as f:
                head = f.read(2000)
            check("<mxfile" in head or "<mxGraphModel" in head,
                  f"{fname[:-4]}.drawio: корректный XML Draw.io")

    print("\n4. Скриншоты")
    for _src, dst, _cap in D.SCREENSHOTS:
        for folder in (D.MAT, D.SHOTS):
            path = os.path.join(folder, dst)
            check(os.path.exists(path) and os.path.getsize(path) > 10000,
                  f"{os.path.basename(folder)}\\{dst}")
    perf = os.path.join(D.MAT, "12_Производительность.png")
    check(os.path.exists(perf) and os.path.getsize(perf) > 10000,
          "01_Общая информация\\Материалы\\12_Производительность.png")

    print("\n5. XLSX")
    xlsx = os.path.join(D.F06, "16_Тест-кейсы.xlsx")
    if os.path.exists(xlsx):
        wb = load_workbook(xlsx)
        check(wb.sheetnames == ["Сводка", "Тест-кейсы", "Ошибки", "Среда", "Покрытие"],
              f"листы: {wb.sheetnames}")
        ws = wb["Тест-кейсы"]
        rows = sum(1 for row in ws.iter_rows(min_row=5, values_only=True) if row[0])
        check(rows == 30, f"строк тест-кейсов: {rows}")
        ws = wb["Ошибки"]
        bugs = sum(1 for row in ws.iter_rows(min_row=5, values_only=True) if row[0])
        check(bugs == 12, f"строк дефектов: {bugs}")
    else:
        check(False, "16_Тест-кейсы.xlsx отсутствует")

    print("\n6. Исходный код")
    src = D.SRC_OUT
    check(os.path.isdir(src), "папка 09_Исходный_код существует")
    for rel in ("game.py", "progression.py", "prog_ui.py", "test_smoke.py",
                "_meta_test.py", "taran/config.py", "taran/ui/hud.py",
                "taran/world.py", "mobile/game_app.py", "mobile/build_apk.py",
                "tests/_tools/verify_content.py", "_СПИСОК_ФАЙЛОВ.txt"):
        path = os.path.join(src, *rel.split("/"))
        check(os.path.exists(path), "исходники: %s" % rel)

    py_files = []
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fname in filenames:
            py_files.append(os.path.join(dirpath, fname))
    bad_compile = []
    py_count = 0
    for path in py_files:
        ext = os.path.splitext(path)[1].lower()
        if ext in (".apk", ".pyc", ".idsig") or "__pycache__" in path:
            bad_compile.append(os.path.relpath(path, src))
            continue
        if ext != ".py":
            continue
        py_count += 1
        # utf-8-sig: в части файлов проекта есть BOM, и Python запускает их штатно.
        with open(path, encoding="utf-8-sig") as f:
            code = f.read()
        try:
            compile(code, path, "exec")
        except SyntaxError as e:
            bad_compile.append("%s: %s" % (os.path.relpath(path, src), e))
    check(py_count >= 20, "в комплект вложено Python-файлов: %d" % py_count)
    check(not bad_compile,
          "все .py компилируются, двоичных артефактов нет"
          + (" (%s)" % bad_compile[:3] if bad_compile else ""))

    copied_lines = 0
    for rel in D.MODULE_FILES:
        with open(os.path.join(src, *rel.split("/")), encoding="utf-8") as f:
            copied_lines += sum(1 for _ in f)
    check(copied_lines == D.REAL_TOTAL,
          "строк в 17 модулях совпадает с документами: %d" % copied_lines)

    print("\n7. Ссылки на исходный код в документах 14 и 19")
    for folder, fname in ((D.F05, "14_Документация_кода.docx"),
                          (D.F07, "19_Руководство_разработчика.docx")):
        path = os.path.join(folder, fname)
        if not os.path.exists(path):
            check(False, "%s отсутствует" % fname)
            continue
        doc = Document(path)
        text = "\n".join(p.text for p in doc.paragraphs)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    text += "\n" + cell.text
        check("09_Исходный_код" in text, "%s: есть ссылка на 09_Исходный_код" % fname)
        rows = text.count("09_Исходный_код/")
        check(rows >= len(D.MODULE_FILES),
              "%s: строк таблицы «модуль → файл»: %d" % (fname, rows))
        check(all(p in text for p in ("taran/ui/hud.py", "game.py", "progression.py")),
              "%s: в таблице есть ключевые модули" % fname)

    print("\n8. Итоги")
    print(f"  DOCX: {docx_count}, XLSX: {xlsx_count}, "
          f"PNG: {len(D.DIAGRAMS) + len(D.SCREENSHOTS) * 2 + 1}, "
          f"drawio: {len(D.DIAGRAMS)}")
    print(f"  В DOCX вставлено изображений: {images}, таблиц: {tables}")
    if errors:
        print(f"\nОШИБОК: {len(errors)}")
        for e in errors:
            print("  -", e)
        return 1
    print("\nВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
