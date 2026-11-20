# -*- coding: utf-8 -*-
"""Сборка полного комплекта документации «ТАРАН-ЭКСПРЕСС» 3.2.

Порядок:
1. prepare() копирует скриншоты и график производительности.
2. Собираются документы 01–22 и книга XLSX.
3. При флаге --diagrams пересобираются 8 схем PNG + .drawio.

Запуск из корня проекта:
    py docs_assignment/_build/build_all.py
    py docs_assignment/_build/build_all.py --diagrams
"""
import os
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import assign_data  # noqa: E402
import build_xlsx  # noqa: E402
import docs_01_04  # noqa: E402
import docs_05_12  # noqa: E402
import docs_13_14  # noqa: E402
import docs_15_17  # noqa: E402
import docs_18_22  # noqa: E402


def make_zip():
    """Пересобирает ZIP комплекта в корне проекта."""
    archive = os.path.join(assign_data.ROOT,
                           "ТАРАН-ЭКСПРЕСС_документация_v%s.zip" % assign_data.VERSION)
    root_name = os.path.basename(assign_data.OUT)
    count = 0
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for dirpath, dirnames, filenames in os.walk(assign_data.OUT):
            dirnames.sort()
            for fname in sorted(filenames):
                full = os.path.join(dirpath, fname)
                rel = os.path.relpath(full, assign_data.OUT)
                z.write(full, os.path.join(root_name, rel))
                count += 1
    print("ZIP: %s — %d файлов, %.1f МБ" % (
        os.path.relpath(archive, assign_data.ROOT), count,
        os.path.getsize(archive) / 1024 / 1024))
    return archive


def main():
    started = time.time()
    assign_data.prepare()
    src_files, src_lines = assign_data.prepare_sources()
    print("Комплект:", assign_data.OUT)
    print("Исходный код:", src_files, "файлов,", src_lines, "строк Python")

    if "--diagrams" in sys.argv:
        import diagrams_build
        print("Схемы: пересборка 8 PNG + 8 .drawio")
        diagrams_build.build_all()

    stages = [
        ("Документы 01–04", docs_01_04.build_all),
        ("Документы 05–12 (UML и блок-схемы)", docs_05_12.build_all),
        ("Документы 13–14 (интерфейс и код)", docs_13_14.build_all),
        ("Документы 15 и 17 (тестирование)", docs_15_17.build_all),
        ("Документы 18–22 (руководства и итоги)", docs_18_22.build_all),
        ("Документ 16 (XLSX)", lambda: [build_xlsx.build()]),
    ]

    made = []
    for label, builder in stages:
        print("\n—", label)
        paths = builder()
        for path in paths:
            size = os.path.getsize(path) // 1024
            print(f"  OK  {os.path.relpath(path, assign_data.OUT)}  ({size} КБ)")
        made.extend(paths)

    print("\nГотово: %d файлов за %.1f с" % (len(made), time.time() - started))
    if "--zip" in sys.argv:
        make_zip()
    return made


if __name__ == "__main__":
    main()
