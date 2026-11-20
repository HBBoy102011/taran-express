# -*- coding: utf-8 -*-
"""Проверка собранных .docx: структура, картинки, заголовки, тексты."""
import glob
import os
import sys

from docx import Document
from docx.oxml.ns import qn

DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check(path):
    doc = Document(path)
    heads = {1: 0, 2: 0, 3: 0}
    for p in doc.paragraphs:
        st = p.style.name
        if st == "Heading 1":
            heads[1] += 1
        elif st == "Heading 2":
            heads[2] += 1
        elif st == "Heading 3":
            heads[3] += 1
    imgs = len(doc.inline_shapes)
    tables = len(doc.tables)
    chars = sum(len(p.text) for p in doc.paragraphs)
    for t in doc.tables:
        for row in t.rows:
            for c in row.cells:
                chars += len(c.text)
    empty = sum(1 for p in doc.paragraphs if not p.text.strip())
    missing_font = 0
    for p in doc.paragraphs:
        for r in p.runs:
            if r.font.name is None and r.text.strip():
                missing_font += 1
    return dict(name=os.path.basename(path), h1=heads[1], h2=heads[2], h3=heads[3],
                tables=tables, images=imgs, chars=chars, empty=empty,
                runs_without_font=missing_font,
                size_kb=round(os.path.getsize(path) / 1024.0, 1))


def main():
    files = sorted(glob.glob(os.path.join(DOCS, "0*", "*.docx")))
    bad = 0
    for f in files:
        r = check(f)
        print("%-58s h1=%-2d h2=%-2d tab=%-2d img=%-2d chars=%-6d %5.0f KB"
              % (r["name"][:58], r["h1"], r["h2"], r["tables"], r["images"],
                 r["chars"], r["size_kb"]))
        if r["h1"] < 5 or r["tables"] < 1 or r["chars"] < 4000:
            print("   ^^ подозрительно мало содержимого")
            bad += 1
    print("\nfiles=%d problems=%d" % (len(files), bad))
    return 0 if bad == 0 and len(files) == 9 else 1


if __name__ == "__main__":
    sys.exit(main())
