# -*- coding: utf-8 -*-
"""Рисовалка схем и графиков для документации «ТАРАН-ЭКСПРЕСС».

Использует pygame (уже зависимость игры) и системный шрифт с кириллицей.
Все схемы рисуются в 2x и сохраняются как PNG для вставки в .docx/.pptx.
"""
import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

BG = (13, 15, 24)
SURFACE = (27, 31, 45)
SURFACE2 = (35, 40, 57)
LINE = (52, 60, 82)
TEXT = (232, 238, 252)
DIM = (150, 162, 192)
MUTED = (110, 120, 148)
BLUE = (104, 160, 255)
GOLD = (255, 208, 112)
GREEN = (118, 226, 158)
RED = (255, 116, 104)
PURPLE = (170, 140, 255)

_fonts = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont("Segoe UI", size, bold=bold)
    return _fonts[key]


class Canvas:
    def __init__(self, w=1600, h=900, bg=BG):
        self.w, self.h = w, h
        self.s = pygame.Surface((w, h))
        self.s.fill(bg)

    # ---------- примитивы ----------
    def rect(self, x, y, w, h, fill=SURFACE, border=None, r=16, bw=2, alpha=None):
        if alpha is not None:
            layer = pygame.Surface((int(w), int(h)), pygame.SRCALPHA)
            pygame.draw.rect(layer, (*fill, alpha), layer.get_rect(), border_radius=r)
            if border:
                pygame.draw.rect(layer, (*border, 255), layer.get_rect(), width=bw, border_radius=r)
            self.s.blit(layer, (x, y))
            return
        pygame.draw.rect(self.s, fill, pygame.Rect(x, y, w, h), border_radius=r)
        if border:
            pygame.draw.rect(self.s, border, pygame.Rect(x, y, w, h), width=bw, border_radius=r)

    def line(self, p1, p2, color=LINE, width=3, dashed=False, dash=14):
        x1, y1 = p1
        x2, y2 = p2
        if not dashed:
            pygame.draw.line(self.s, color, p1, p2, width)
            return
        dx, dy = x2 - x1, y2 - y1
        dist = max(1.0, (dx * dx + dy * dy) ** 0.5)
        ux, uy = dx / dist, dy / dist
        pos = 0.0
        while pos < dist:
            end = min(dist, pos + dash)
            pygame.draw.line(self.s, color,
                             (x1 + ux * pos, y1 + uy * pos),
                             (x1 + ux * end, y1 + uy * end), width)
            pos += dash * 2

    def arrow(self, p1, p2, color=BLUE, width=3, dashed=False, head=14):
        self.line(p1, p2, color, width, dashed)
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        dist = max(1.0, (dx * dx + dy * dy) ** 0.5)
        ux, uy = dx / dist, dy / dist
        px, py = -uy, ux
        tip = p2
        b1 = (tip[0] - ux * head + px * head * 0.55, tip[1] - uy * head + py * head * 0.55)
        b2 = (tip[0] - ux * head - px * head * 0.55, tip[1] - uy * head - py * head * 0.55)
        pygame.draw.polygon(self.s, color, [tip, b1, b2])

    def text(self, s, x, y, size=20, color=TEXT, bold=False, anchor="topleft", wrap=None, lh=None):
        f = font(size, bold)
        lines = [s]
        if wrap:
            lines = self._wrap(s, f, wrap)
        lh = lh or int(size * 1.35)
        total = lh * len(lines)
        for i, ln in enumerate(lines):
            img = f.render(ln, True, color)
            r = img.get_rect()
            if anchor == "topleft":
                r.topleft = (x, y + i * lh)
            elif anchor == "center":
                r.center = (x, y - total // 2 + lh // 2 + i * lh)
            elif anchor == "midleft":
                r.midleft = (x, y - total // 2 + lh // 2 + i * lh)
            elif anchor == "topright":
                r.topright = (x, y + i * lh)
            else:
                r.topleft = (x, y + i * lh)
            self.s.blit(img, r)
        return total

    def _wrap(self, s, f, maxw):
        out = []
        for para in s.split("\n"):
            words = para.split(" ")
            cur = ""
            for wd in words:
                probe = wd if not cur else cur + " " + wd
                if f.size(probe)[0] <= maxw or not cur:
                    cur = probe
                else:
                    out.append(cur)
                    cur = wd
            out.append(cur)
        return out

    def header(self, title, sub=None, accent=BLUE):
        pygame.draw.rect(self.s, accent, pygame.Rect(0, 0, self.w, 6))
        self.text(title, 64, 44, 38, TEXT, True)
        if sub:
            self.text(sub, 64, 96, 19, DIM)
        return 150

    def footer(self, s):
        self.text(s, 64, self.h - 44, 15, MUTED)

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        pygame.image.save(self.s, path)
        return path


# ---------- готовые блоки схем ----------
def node(cv, x, y, w, h, title, lines=(), accent=BLUE, fill=SURFACE, tsize=21, lsize=16):
    cv.rect(x, y, w, h, fill=fill, border=(accent[0] // 2 + 20, accent[1] // 2 + 24, accent[2] // 2 + 34), r=14)
    pygame.draw.rect(cv.s, accent, pygame.Rect(x, y + 14, 5, h - 28), border_radius=3)
    cv.text(title, x + 22, y + 16, tsize, TEXT, True, wrap=w - 40)
    ty = y + 16 + int(tsize * 1.35) * max(1, len(cv._wrap(title, font(tsize, True), w - 40)))
    for i, ln in enumerate(lines):
        cv.text(ln, x + 22, ty + 4 + i * int(lsize * 1.35), lsize, DIM, wrap=w - 40)


def table(cv, x, y, col_w, rows, header=True, row_h=40, size=16, head_color=GOLD):
    total = sum(col_w)
    yy = y
    for ri, row in enumerate(rows):
        h = row_h
        bg = SURFACE2 if (header and ri == 0) else (SURFACE if ri % 2 else (23, 27, 39))
        cv.rect(x, yy, total, h, fill=bg, border=None, r=0)
        xx = x
        for ci, cell in enumerate(row):
            col = head_color if (header and ri == 0) else TEXT
            bold = header and ri == 0
            cv.text(str(cell), xx + 12, yy + h // 2, size, col, bold, anchor="midleft", wrap=col_w[ci] - 24)
            xx += col_w[ci]
        pygame.draw.line(cv.s, LINE, (x, yy + h), (x + total, yy + h), 1)
        yy += h
    pygame.draw.line(cv.s, LINE, (x, y), (x, yy), 2)
    pygame.draw.line(cv.s, LINE, (x + total, y), (x + total, yy), 2)
    return yy


def bar_chart(cv, x, y, w, h, items, maxv=None, color=BLUE, label_color=DIM, fmt="{:.0f}"):
    """items: [(label, value), ...] — горизонтальные полосы."""
    maxv = maxv or max(v for _, v in items) or 1
    n = len(items)
    gap = h / max(1, n)
    bh = min(30, gap * 0.55)
    for i, (lab, v) in enumerate(items):
        yy = y + i * gap
        cv.text(lab, x, yy + gap / 2, 16, label_color, anchor="midleft", wrap=int(w * 0.32))
        bx = x + int(w * 0.34)
        bw = int((w * 0.56) * (v / maxv))
        cv.rect(bx, int(yy + gap / 2 - bh / 2), max(4, bw), int(bh), fill=SURFACE2, r=bh // 2)
        cv.rect(bx, int(yy + gap / 2 - bh / 2), max(4, bw), int(bh), fill=color, r=bh // 2)
        cv.text(fmt.format(v), bx + bw + 12, yy + gap / 2, 16, TEXT, True, anchor="midleft")


def donut(cv, cx, cy, r, parts, thickness=38, hole=None):
    """parts: [(label, value, color)]"""
    total = sum(v for _, v, _ in parts) or 1
    start = -90.0
    for _, v, col in parts:
        span = 360.0 * v / total
        steps = max(4, int(span / 3))
        pts = [(cx, cy)]
        for i in range(steps + 1):
            a = math.radians(start + span * i / steps)
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
        pygame.draw.polygon(cv.s, col, pts)
        start += span
    pygame.draw.circle(cv.s, hole or BG, (int(cx), int(cy)), int(r - thickness))

