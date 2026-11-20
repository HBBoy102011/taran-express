# -*- coding: utf-8 -*-
"""Проверка геометрии презентации: выход за границы слайда и переполнение текста."""
import os
import sys

from PIL import ImageFont
from pptx import Presentation
from pptx.util import Emu

EMU_IN = 914400
FONT_REG = r"C:\Windows\Fonts\segoeui.ttf"
FONT_BOLD = r"C:\Windows\Fonts\segoeuib.ttf"

_cache = {}


def _font(pt, bold):
    key = (round(pt, 1), bold)
    if key not in _cache:
        path = FONT_BOLD if bold and os.path.exists(FONT_BOLD) else FONT_REG
        # PIL: 1 pt = 1 px at 72 dpi; переводим в px при 96 dpi для ширины в дюймах
        _cache[key] = ImageFont.truetype(path, max(6, int(round(pt * 96 / 72))))
    return _cache[key]


def wrap_lines(txt, pt, bold, width_px):
    f = _font(pt, bold)
    total = 0
    for para in txt.split("\n"):
        words = para.split(" ")
        line = ""
        n = 1
        for w in words:
            probe = (line + " " + w).strip()
            if f.getlength(probe) <= width_px or not line:
                line = probe
            else:
                n += 1
                line = w
        total += n
    return total


def main():
    path = sys.argv[1]
    prs = Presentation(path)
    W = prs.slide_width / EMU_IN
    H = prs.slide_height / EMU_IN
    problems = 0
    for i, slide in enumerate(prs.slides, 1):
        for sh in slide.shapes:
            x, y = sh.left / EMU_IN, sh.top / EMU_IN
            w, h = sh.width / EMU_IN, sh.height / EMU_IN
            if x < -0.02 or y < -0.02 or x + w > W + 0.02 or y + h > H + 0.02:
                print("slide %02d: фигура вне слайда  (%.2f, %.2f, %.2f, %.2f)"
                      % (i, x, y, w, h))
                problems += 1
            if not sh.has_text_frame:
                continue
            tf = sh.text_frame
            need = 0.0
            for p in tf.paragraphs:
                txt = "".join(r.text for r in p.runs)
                if not txt.strip():
                    continue
                pt = max([r.font.size.pt for r in p.runs if r.font.size] or [18])
                bold = any(r.font.bold for r in p.runs)
                lines = wrap_lines(txt, pt, bold, max(10, w * 96 - 4))
                need += lines * pt * 1.22 / 72.0
                if p.space_after:
                    need += p.space_after.pt / 72.0
            if need > h + 0.08:
                print("slide %02d: возможно переполнение текста (нужно %.2f in, есть %.2f in): %s"
                      % (i, need, h, t1(tf)))
                problems += 1
    print("\nslides=%d problems=%d" % (len(prs.slides), problems))
    return 0


def t1(tf):
    for p in tf.paragraphs:
        s = "".join(r.text for r in p.runs).strip()
        if s:
            return s[:60]
    return ""


if __name__ == "__main__":
    sys.exit(main())
