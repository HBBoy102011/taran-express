# -*- coding: utf-8 -*-
"""Собирает все девять документов .docx.

Запуск:  py docs/_tools/build_docs.py
"""
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import docs_common  # noqa: E402


def main():
    docs_common.prep()
    import docs_a
    import docs_b

    jobs = [("01", docs_a.build_01), ("02", docs_a.build_02), ("03", docs_a.build_03),
            ("04", docs_a.build_04), ("05", docs_a.build_05), ("06", docs_b.build_06),
            ("07", docs_b.build_07), ("08", docs_b.build_08), ("09", docs_b.build_09)]
    ok = 0
    for num, fn in jobs:
        try:
            path = fn()
            size = os.path.getsize(path) / 1024.0
            print("ok %s  %6.1f KB  %s" % (num, size, os.path.basename(path)))
            ok += 1
        except Exception:
            print("FAIL %s" % num)
            traceback.print_exc()
    print("\nbuilt %d/%d" % (ok, len(jobs)))
    return 0 if ok == len(jobs) else 1


if __name__ == "__main__":
    sys.exit(main())
