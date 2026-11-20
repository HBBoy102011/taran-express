# -*- coding: utf-8 -*-
"""Мини-движок UML-схем: одна модель -> PNG (pygame) и .drawio (mxGraph)."""
import math
import os
import sys
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TOOLS = os.path.join(ROOT, "docs", "_tools")
sys.path.insert(0, TOOLS)

from draw import (BG, BLUE, DIM, GOLD, GREEN, LINE, MUTED, PURPLE, RED,  # noqa: E402
                  SURFACE, SURFACE2, TEXT, Canvas, font)

FONT = "Segoe UI"


class Node:
    def __init__(self, nid, kind, x, y, w, h, title="", lines=None, attrs=None,
                 methods=None, color=BLUE, fill=SURFACE, font_size=20, title_size=24,
                 align="center", parent=None, dashed=False, extra=None):
        self.id = nid
        self.kind = kind
        self.x, self.y, self.w, self.h = x, y, w, h
        self.title = title
        self.lines = lines or []
        self.attrs = attrs or []
        self.methods = methods or []
        self.color = color
        self.fill = fill
        self.font_size = font_size
        self.title_size = title_size
        self.align = align
        self.parent = parent
        self.dashed = dashed
        self.extra = extra or {}


class Edge:
    def __init__(self, src, dst, label="", points=None, color=LINE, width=2,
                 dashed=False, arrow=True, kind="association", label_pos=0.5,
                 start_marker=None, end_marker=None):
        self.src = src
        self.dst = dst
        self.label = label
        self.points = points or []
        self.color = color
        self.width = width
        self.dashed = dashed
        self.arrow = arrow
        self.kind = kind
        self.label_pos = label_pos
        self.start_marker = start_marker
        self.end_marker = end_marker


def _mix(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _text_lines(cv, text, x, y, size, color, bold=False, width=None, align="left", lh=None):
    """Рисует текст с переносами, возвращает высоту."""
    f = font(size, bold)
    lines = [text]
    if width:
        lines = []
        for para in str(text).split("\n"):
            words = para.split(" ")
            cur = ""
            for wd in words:
                probe = wd if not cur else cur + " " + wd
                if f.size(probe)[0] <= width or not cur:
                    cur = probe
                else:
                    lines.append(cur)
                    cur = wd
            lines.append(cur)
    lh = lh or int(size * 1.28)
    for i, ln in enumerate(lines):
        img = f.render(ln, True, color)
        r = img.get_rect()
        if align == "center":
            r.midtop = (x + width // 2, y + i * lh)
        elif align == "right":
            r.topright = (x + width, y + i * lh)
        else:
            r.topleft = (x, y + i * lh)
        cv.s.blit(img, r)
    return len(lines) * lh


def _center_text(cv, text, cx, cy, size, color, bold=False):
    img = font(size, bold).render(str(text), True, color)
    r = img.get_rect(center=(int(cx), int(cy)))
    cv.s.blit(img, r)


def _arrow_head(cv, p1, p2, color, size=17, filled=True, open_=False):
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    dist = max(1.0, math.hypot(dx, dy))
    ux, uy = dx / dist, dy / dist
    px, py = -uy, ux
    b1 = (x2 - ux * size + px * size * 0.55, y2 - uy * size + py * size * 0.55)
    b2 = (x2 - ux * size - px * size * 0.55, y2 - uy * size - py * size * 0.55)
    if filled:
        import pygame
        pygame.draw.polygon(cv.s, color, [(x2, y2), b1, b2])
    elif open_:
        import pygame
        pygame.draw.lines(cv.s, color, False, [b1, (x2, y2), b2], 2)


def _diamond(cv, cx, cy, w, h, fill, border):
    import pygame
    pts = [(cx, cy - h // 2), (cx + w // 2, cy), (cx, cy + h // 2), (cx - w // 2, cy)]
    pygame.draw.polygon(cv.s, fill, pts)
    pygame.draw.polygon(cv.s, border, pts, 2)


def _actor(cv, n):
    import pygame
    x, y = n.x, n.y
    cx = x + n.w // 2
    col = n.color
    pygame.draw.circle(cv.s, col, (cx, y + 22), 13, 2)
    pygame.draw.line(cv.s, col, (cx, y + 35), (cx, y + 82), 3)
    pygame.draw.line(cv.s, col, (cx - 30, y + 52), (cx + 30, y + 52), 3)
    pygame.draw.line(cv.s, col, (cx, y + 82), (cx - 24, y + 122), 3)
    pygame.draw.line(cv.s, col, (cx, y + 82), (cx + 24, y + 122), 3)
    _text_lines(cv, n.title, x, y + 130, n.title_size, TEXT, True, n.w, "center")


def _class_node(cv, n):
    import pygame
    r = pygame.Rect(n.x, n.y, n.w, n.h)
    pygame.draw.rect(cv.s, n.fill, r, border_radius=6)
    pygame.draw.rect(cv.s, n.color, r, 2, border_radius=6)
    head_h = 42
    if n.extra.get("stereotype"):
        head_h = 52
    pygame.draw.rect(cv.s, _mix(n.fill, n.color, 0.18), pygame.Rect(n.x, n.y, n.w, head_h),
                     border_top_left_radius=6, border_top_right_radius=6)
    if n.extra.get("stereotype"):
        _center_text(cv, n.extra["stereotype"], n.x + n.w // 2, n.y + 15, 15, n.color, True)
        _center_text(cv, n.title, n.x + n.w // 2, n.y + 35, n.title_size, TEXT, True)
    else:
        _center_text(cv, n.title, n.x + n.w // 2, n.y + head_h // 2, n.title_size, TEXT, True)
    y = n.y + head_h
    lh = int(n.font_size * 1.35)
    # attributes
    if n.attrs:
        ah = len(n.attrs) * lh + 12
        pygame.draw.line(cv.s, n.color, (n.x, y), (n.x + n.w, y), 1)
        yy = y + 6
        for a in n.attrs:
            _text_lines(cv, a, n.x + 10, yy, n.font_size, DIM, False, n.w - 18)
            yy += lh
        y += ah
    if n.methods:
        pygame.draw.line(cv.s, n.color, (n.x, y), (n.x + n.w, y), 1)
        yy = y + 6
        for m in n.methods:
            _text_lines(cv, m, n.x + 10, yy, n.font_size, TEXT, False, n.w - 18)
            yy += lh


def _node(cv, n):
    import pygame
    if n.kind == "actor":
        _actor(cv, n)
        return
    if n.kind == "class":
        _class_node(cv, n)
        return
    if n.kind == "usecase":
        pygame.draw.ellipse(cv.s, n.fill, pygame.Rect(n.x, n.y, n.w, n.h))
        pygame.draw.ellipse(cv.s, n.color, pygame.Rect(n.x, n.y, n.w, n.h), 2)
        _text_lines(cv, n.title, n.x + 10, n.y + n.h // 2 - int(n.title_size * 0.6),
                    n.title_size, TEXT, True, n.w - 20, "center")
        return
    if n.kind == "decision":
        _diamond(cv, n.x + n.w // 2, n.y + n.h // 2, n.w, n.h, n.fill,
                 n.color)
        _text_lines(cv, n.title, n.x + 8, n.y + n.h // 2 - int(n.font_size * 0.55),
                    n.font_size, TEXT, True, n.w - 16, "center")
        return
    if n.kind == "start":
        pygame.draw.circle(cv.s, (15, 17, 26), (n.x + n.w // 2, n.y + n.h // 2), n.w // 2)
        pygame.draw.circle(cv.s, TEXT, (n.x + n.w // 2, n.y + n.h // 2), n.w // 2, 2)
        return
    if n.kind == "end":
        pygame.draw.circle(cv.s, (15, 17, 26), (n.x + n.w // 2, n.y + n.h // 2), n.w // 2)
        pygame.draw.circle(cv.s, TEXT, (n.x + n.w // 2, n.y + n.h // 2), n.w // 2, 2)
        pygame.draw.circle(cv.s, TEXT, (n.x + n.w // 2, n.y + n.h // 2), n.w // 2 - 6, 2)
        return
    if n.kind == "note":
        r = pygame.Rect(n.x, n.y, n.w, n.h)
        pygame.draw.rect(cv.s, (34, 38, 52), r, border_radius=3)
        pygame.draw.rect(cv.s, n.color, r, 2, border_radius=3)
        fold = 18
        pygame.draw.polygon(cv.s, BG, [(n.x + n.w - fold, n.y), (n.x + n.w, n.y + fold),
                                       (n.x + n.w - fold, n.y + fold)])
        pygame.draw.lines(cv.s, n.color, False, [(n.x + n.w - fold, n.y),
                                                 (n.x + n.w - fold, n.y + fold),
                                                 (n.x + n.w, n.y + fold)], 2)
        _text_lines(cv, n.title, n.x + 10, n.y + 8, n.font_size, TEXT, False, n.w - 22)
        return
    if n.kind == "package":
        r = pygame.Rect(n.x, n.y, n.w, n.h)
        pygame.draw.rect(cv.s, (18, 21, 32), r, border_radius=8)
        pygame.draw.rect(cv.s, n.color, r, 2, border_radius=8)
        tab_w = min(n.w, 380)
        tab = pygame.Rect(n.x, n.y, tab_w, 40)
        pygame.draw.rect(cv.s, n.color, tab, border_top_left_radius=8, border_top_right_radius=8)
        _text_lines(cv, n.title, n.x + 12, n.y + 8, 16, (10, 12, 20), True, tab.w - 20)
        return
    if n.kind == "state":
        pygame.draw.rect(cv.s, n.fill, pygame.Rect(n.x, n.y, n.w, n.h), border_radius=16)
        pygame.draw.rect(cv.s, n.color, pygame.Rect(n.x, n.y, n.w, n.h), 2, border_radius=16)
        _text_lines(cv, n.title, n.x + 10, n.y + n.h // 2 - int(n.title_size * 0.55),
                    n.title_size, TEXT, True, n.w - 20, "center")
        return
    if n.kind == "connector":
        pygame.draw.circle(cv.s, (13, 15, 24), (n.x + n.w // 2, n.y + n.h // 2), n.w // 2)
        pygame.draw.circle(cv.s, n.color, (n.x + n.w // 2, n.y + n.h // 2), n.w // 2, 2)
        _center_text(cv, n.title, n.x + n.w // 2, n.y + n.h // 2, n.title_size, TEXT, True)
        return
    if n.kind == "state_comp":
        r = pygame.Rect(n.x, n.y, n.w, n.h)
        pygame.draw.rect(cv.s, n.fill, r, border_radius=16)
        pygame.draw.rect(cv.s, n.color, r, 2, border_radius=16)
        pygame.draw.line(cv.s, n.color, (n.x + 14, n.y + 34), (n.x + n.w - 14, n.y + 34), 1)
        _text_lines(cv, n.title, n.x + 12, n.y + 8, 16, TEXT, True, n.w - 24, "center")
        return
    if n.kind == "lifeline":
        r = pygame.Rect(n.x, n.y, n.w, n.h)
        pygame.draw.rect(cv.s, n.fill, r, border_radius=6)
        pygame.draw.rect(cv.s, n.color, r, 2, border_radius=6)
        _text_lines(cv, n.title, n.x + 5, n.y + 8, n.font_size, TEXT, True, n.w - 10, "center")
        pygame.draw.line(cv.s, n.color, (n.x + n.w // 2, n.y + n.h),
                         (n.x + n.w // 2, n.y + n.h + n.extra.get("life", 500)), 2)
        return
    # process / box
    pygame.draw.rect(cv.s, n.fill, pygame.Rect(n.x, n.y, n.w, n.h), border_radius=10)
    pygame.draw.rect(cv.s, n.color, pygame.Rect(n.x, n.y, n.w, n.h),
                     2, border_radius=10)
    text_h = _text_lines(cv, n.title, n.x + 10, n.y + 8, n.title_size, TEXT, True,
                         n.w - 20, n.align)
    yy = n.y + 8 + text_h
    for ln in n.lines:
        yy += _text_lines(cv, ln, n.x + 10, yy + 2, n.font_size, DIM, False, n.w - 20,
                          n.align)


def _is_center(n, p):
    return (abs(p[0] - (n.x + n.w / 2)) <= 2 and
            abs(p[1] - (n.y + n.h / 2)) <= 2)


def _route(edge, nodes):
    a, b = nodes[edge.src], nodes[edge.dst]
    pts = list(edge.points)
    if edge.kind == "lifeline":
        return pts, a, b
    if not pts:
        ax, ay = a.x + a.w / 2, a.y + a.h / 2
        bx, by = b.x + b.w / 2, b.y + b.h / 2
        dx, dy = bx - ax, by - ay
        ta = _rect_t(a, ax, ay, dx, dy)
        tb = _rect_t(b, bx, by, -dx, -dy)
        if ta is None or tb is None:
            return [(ax, ay), (bx, by)], a, b
        return [(ax + dx * ta, ay + dy * ta), (bx - dx * tb, by - dy * tb)], a, b
    first, last = pts[0], pts[-1]
    # если маршрут начинается в центре узла — выводим его на границу
    if len(pts) >= 2 and _is_center(a, first):
        cx, cy = a.x + a.w / 2, a.y + a.h / 2
        dx, dy = pts[1][0] - cx, pts[1][1] - cy
        t = _rect_t(a, cx, cy, dx, dy)
        if t is not None:
            pts[0] = (cx + dx * t, cy + dy * t)
    # если маршрут заканчивается в центре узла — выводим его на границу
    if len(pts) >= 2 and _is_center(b, last):
        cx, cy = b.x + b.w / 2, b.y + b.h / 2
        p_prev = pts[-2]
        dx, dy = cx - p_prev[0], cy - p_prev[1]
        t = _rect_t(b, cx, cy, dx, dy)
        if t is not None:
            pts[-1] = (cx + dx * t, cy + dy * t)
    return pts, a, b


def _rect_t(n, x, y, dx, dy):
    """Параметр t, при котором луч из центра прямоугольника выходит на границу."""
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return None
    cx, cy = n.x + n.w / 2, n.y + n.h / 2
    tx = ((n.x if dx < 0 else n.x + n.w) - cx) / dx if abs(dx) > 1e-6 else 1e9
    ty = ((n.y if dy < 0 else n.y + n.h) - cy) / dy if abs(dy) > 1e-6 else 1e9
    return min(abs(tx), abs(ty))


def _draw_edge(cv, e, nodes, show_labels=False):
    import pygame
    if e.kind == "lifeline":
        a = nodes[e.src]
        cx = a.x + a.w // 2
        if e.src == e.dst:
            y1 = e.points[0][1] if e.points else a.y + a.h
            x1 = e.points[0][0] if e.points else cx
            pts = [(x1, y1), (x1 + 54, y1), (x1 + 54, y1 + 30), (x1, y1 + 30)]
            for i in range(3):
                pygame.draw.line(cv.s, e.color, pts[i], pts[i + 1], e.width)
            _arrow_head(cv, pts[2], pts[3], e.color, 15)
            return
        y1 = e.points[0][1] if e.points else a.y + a.h
        y2 = e.points[-1][1] if e.points else y1 + 100
        x1 = e.points[0][0] if e.points else cx
        x2 = e.points[-1][0] if e.points else cx
        if e.dashed:
            _dash_line(cv, (x1, y1), (x2, y2), e.color, e.width)
        else:
            pygame.draw.line(cv.s, e.color, (x1, y1), (x2, y2), e.width)
        if e.arrow:
            _arrow_head(cv, (x1, y1), (x2, y2), e.color, 16)
        return
    pts, a, b = _route(e, nodes)
    if len(pts) >= 2:
        for i in range(len(pts) - 1):
            if e.dashed:
                _dash_line(cv, pts[i], pts[i + 1], e.color, e.width)
            else:
                pygame.draw.line(cv.s, e.color, pts[i], pts[i + 1], e.width)
        if e.kind == "inherit":
            # пустой треугольник у родителя
            _arrow_head(cv, pts[-2], pts[-1], e.color, 22, filled=False, open_=True)
        elif e.arrow:
            _arrow_head(cv, pts[-2], pts[-1], e.color, 17)
        if e.kind == "composition":
            # ромб у источника
            _diamond_at(cv, pts[0], pts[1], e.color)
        if e.kind == "aggregation":
            _diamond_at(cv, pts[0], pts[1], e.color, filled=False)


def _tag(cv, s, cx, cy, size=18, color=DIM, bold=True):
    import pygame
    f = font(size, bold)
    img = f.render(str(s), True, color)
    r = img.get_rect(center=(int(cx), int(cy)))
    bg = r.inflate(14, 8)
    pygame.draw.rect(cv.s, (13, 15, 24), bg, border_radius=5)
    pygame.draw.rect(cv.s, (42, 48, 66), bg, 1, border_radius=5)
    cv.s.blit(img, r)


def _draw_edge_label(cv, e, nodes):
    if not e.label:
        return
    if e.kind == "lifeline":
        if e.src == e.dst:
            x1 = e.points[0][0] if e.points else nodes[e.src].x + nodes[e.src].w / 2
            y1 = e.points[0][1] if e.points else nodes[e.src].y + nodes[e.src].h
            _tag(cv, e.label, x1 + 110, y1 + 15, 17, e.color)
            return
        if len(e.points) >= 2:
            x1, y1 = e.points[0]
            x2, y2 = e.points[-1]
            _tag(cv, e.label, (x1 + x2) / 2, (y1 + y2) / 2 - 16, 17, e.color)
        return
    pts, a, b = _route(e, nodes)
    if len(pts) < 2:
        return
    idx = min(len(pts) - 2, max(0, int((len(pts) - 1) * e.label_pos)))
    p1, p2 = pts[idx], pts[idx + 1]
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    if abs(p2[0] - p1[0]) < abs(p2[1] - p1[1]):
        mx += 24
        my = (p1[1] + p2[1]) / 2
    else:
        my -= 16
    _tag(cv, e.label, mx, my, 17, e.color)


def _dash_line(cv, p1, p2, color, width=2, dash=10):
    import pygame
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    dist = max(1.0, math.hypot(dx, dy))
    ux, uy = dx / dist, dy / dist
    pos = 0.0
    while pos < dist:
        end = min(dist, pos + dash)
        pygame.draw.line(cv.s, color, (x1 + ux * pos, y1 + uy * pos),
                         (x1 + ux * end, y1 + uy * end), width)
        pos += dash * 2


def _diamond_at(cv, p1, p2, color, filled=True):
    import pygame
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    dist = max(1.0, math.hypot(dx, dy))
    ux, uy = dx / dist, dy / dist
    cx, cy = p1[0] + ux * 12, p1[1] + uy * 12
    px, py = -uy, ux
    pts = [(cx + ux * 12, cy + uy * 12), (cx + px * 7, cy + py * 7),
           (cx - ux * 12, cy - uy * 12), (cx - px * 7, cy - py * 7)]
    if filled:
        pygame.draw.polygon(cv.s, color, pts)
    else:
        pygame.draw.polygon(cv.s, BG, pts)
        pygame.draw.polygon(cv.s, color, pts, 2)


class Diagram:
    def __init__(self, title, subtitle="", w=1400, h=950, accent=BLUE):
        self.title = title
        self.subtitle = subtitle
        self.w, self.h = w, h
        self.accent = accent
        self.nodes = []
        self.edges = []
        self.texts = []
        self.tags = []

    def add(self, node):
        self.nodes.append(node)
        return node

    def edge(self, src, dst, label="", **kw):
        self.edges.append(Edge(src, dst, label=label, **kw))
        return self.edges[-1]

    def text(self, s, x, y, size=15, color=DIM, bold=False, width=None, align="left"):
        self.texts.append((s, x, y, size, color, bold, width, align))

    def tag(self, s, x, y, size=17, color=DIM):
        self.tags.append((s, x, y, size, color))

    def render(self, path):
        cv = Canvas(self.w, self.h)
        cv.s.fill(BG)
        # сетка
        import pygame
        for gx in range(0, self.w, 40):
            pygame.draw.line(cv.s, (18, 21, 31), (gx, 0), (gx, self.h), 1)
        for gy in range(0, self.h, 40):
            pygame.draw.line(cv.s, (18, 21, 31), (0, gy), (self.w, gy), 1)
        pygame.draw.rect(cv.s, self.accent, pygame.Rect(0, 0, self.w, 6))
        _text_lines(cv, self.title, 40, 30, 30, TEXT, True, self.w - 80)
        if self.subtitle:
            _text_lines(cv, self.subtitle, 40, 70, 16, DIM, False, self.w - 80)
        for s, x, y, size, color, bold, width, align in self.texts:
            _text_lines(cv, s, x, y, size, color, bold, width, align)
        by_id = {n.id: n for n in self.nodes}
        # пакеты и фоны сначала
        for n in self.nodes:
            if n.kind in ("package", "framebg", "state_comp", "lifeline"):
                _node(cv, n)
        for e in self.edges:
            _draw_edge(cv, e, by_id)
        for n in self.nodes:
            if n.kind not in ("package", "framebg", "state_comp", "lifeline"):
                _node(cv, n)
        # подписи рёбер поверх всего — с подложкой, чтобы не терялись
        for e in self.edges:
            _draw_edge_label(cv, e, by_id)
        for s, x, y, size, color in self.tags:
            _tag(cv, s, x, y, size, color)
        _text_lines(cv, "ТАРАН-ЭКСПРЕСС 3.2 · документация · %s" % self.title,
                    40, self.h - 30, 14, MUTED, False, self.w - 80)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        pygame.image.save(cv.s, path)
        return path

    def _style(self, n):
        c = "#%02x%02x%02x" % n.color
        f = "#%02x%02x%02x" % n.fill
        base = "html=1;whiteSpace=wrap;fontFamily=Segoe UI;fontSize=%d;fontColor=#e8eefc;" % n.font_size
        if n.kind == "actor":
            return ("shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;"
                    "fontSize=%d;fontColor=#e8eefc;" % n.title_size)
        if n.kind == "usecase":
            return ("ellipse;html=1;whiteSpace=wrap;fontFamily=Segoe UI;fontSize=%d;"
                    "fontColor=#e8eefc;fillColor=%s;strokeColor=%s;" % (n.title_size, f, c))
        if n.kind == "decision":
            return ("rhombus;html=1;whiteSpace=wrap;fontFamily=Segoe UI;fontSize=%d;"
                    "fontColor=#e8eefc;fillColor=%s;strokeColor=%s;" % (n.font_size, f, c))
        if n.kind == "start":
            return "ellipse;html=1;fillColor=#10131e;strokeColor=#e8eefc;"
        if n.kind == "end":
            return "ellipse;shape=doubleEllipse;html=1;fillColor=#10131e;strokeColor=#e8eefc;"
        if n.kind == "connector":
            return ("ellipse;html=1;whiteSpace=wrap;fontFamily=Segoe UI;fontSize=%d;"
                    "fontColor=#e8eefc;fillColor=#10131e;strokeColor=%s;" % (n.title_size, c))
        if n.kind == "state":
            return ("rounded=1;arcSize=24;html=1;whiteSpace=wrap;fontFamily=Segoe UI;"
                    "fontSize=%d;fontColor=#e8eefc;fillColor=%s;strokeColor=%s;" % (n.title_size, f, c))
        if n.kind == "state_comp":
            return ("swimlane;rounded=1;arcSize=8;html=1;startSize=34;fontFamily=Segoe UI;"
                    "fontSize=16;fontColor=#e8eefc;fillColor=%s;strokeColor=%s;"
                    "swimlaneFillColor=%s;" % (f, c, f))
        if n.kind == "class":
            return ("rounded=0;whiteSpace=wrap;html=1;verticalAlign=top;align=left;spacingLeft=6;"
                    "fontFamily=Segoe UI;fontSize=%d;fontColor=#e8eefc;fillColor=%s;"
                    "strokeColor=%s;" % (n.font_size, f, c))
        if n.kind == "note":
            return ("shape=note;whiteSpace=wrap;html=1;size=18;fontFamily=Segoe UI;"
                    "fontSize=%d;fontColor=#e8eefc;fillColor=#222736;strokeColor=%s;" % (n.font_size, c))
        if n.kind == "package":
            return ("swimlane;rounded=1;html=1;startSize=30;fontFamily=Segoe UI;fontSize=15;"
                    "fontColor=#0a0c14;fillColor=%s;strokeColor=%s;swimlaneFillColor=#12151f;"
                    % (c, c))
        if n.kind == "lifeline":
            return ("shape=umlLifeline;perimeter=lifelinePerimeter;html=1;whiteSpace=wrap;"
                    "fontFamily=Segoe UI;fontSize=%d;fontColor=#e8eefc;fillColor=%s;"
                    "strokeColor=%s;size=48;" % (n.font_size, f, c))
        return ("rounded=1;arcSize=16;html=1;whiteSpace=wrap;fontFamily=Segoe UI;"
                "fontSize=%d;fontColor=#e8eefc;fillColor=%s;strokeColor=%s;" % (n.title_size, f, c))

    def save_drawio(self, path):
        cells = []
        for n in self.nodes:
            label = n.title
            if n.kind == "class":
                parts = ["<b>%s</b>" % escape(n.title)]
                if n.extra.get("stereotype"):
                    parts.insert(0, "<i>%s</i>" % escape(n.extra["stereotype"]))
                if n.attrs:
                    parts.append("──────────")
                    parts += [escape(a) for a in n.attrs]
                if n.methods:
                    parts.append("──────────")
                    parts += [escape(m) for m in n.methods]
                label = "<br>".join(parts)
            elif n.lines:
                label = "<b>%s</b><br>%s" % (escape(n.title),
                                             "<br>".join(escape(x) for x in n.lines))
            else:
                label = escape(n.title)
            style = self._style(n)
            if n.dashed:
                style += "dashed=1;"
            cells.append(
                '<mxCell id="%s" value="%s" style="%s" vertex="1" parent="1">'
                '<mxGeometry x="%d" y="%d" width="%d" height="%d" as="geometry"/></mxCell>'
                % (escape(n.id), label.replace('"', "&quot;"), style,
                   n.x, n.y, n.w, n.h))
        for i, e in enumerate(self.edges):
            style = ("edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=block;"
                     "fontFamily=Segoe UI;fontSize=12;fontColor=#aab4cc;strokeColor=#6c7899;")
            if e.kind == "inherit":
                style += "endArrow=block;endFill=0;"
            if e.kind == "composition":
                style += "startArrow=diamond;startFill=1;"
            if e.kind == "aggregation":
                style += "startArrow=diamond;startFill=0;"
            if e.kind == "dependency":
                style += "dashed=1;"
            if e.dashed:
                style += "dashed=1;"
            pts = list(e.points)
            if e.kind == "lifeline":
                pts = e.points
            geom = ""
            if len(pts) > 2:
                geom = "<Array as=\"points\">" + "".join(
                    '<mxPoint x="%d" y="%d"/>' % (p[0], p[1]) for p in pts[1:-1]) + "</Array>"
            cells.append(
                '<mxCell id="edge_%d" value="%s" style="%s" edge="1" parent="1" '
                'source="%s" target="%s"><mxGeometry relative="1" as="geometry">%s'
                '</mxGeometry></mxCell>'
                % (i, escape(e.label).replace('"', "&quot;"), style,
                   escape(e.src), escape(e.dst), geom))
        xml = (
            '<mxfile host="app.diagrams.net" version="24.0.0">'
            '<diagram id="taran" name="%s"><mxGraphModel dx="1400" dy="900" grid="1" '
            'gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" '
            'pageScale="1" pageWidth="%d" pageHeight="%d" math="0" shadow="0"><root>'
            '<mxCell id="0"/><mxCell id="1" parent="0"/>%s</root></mxGraphModel></diagram></mxfile>'
            % (escape(self.title), self.w, self.h, "".join(cells)))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml)
        return path


def begin(title, subtitle="", w=1400, h=950, accent=BLUE):
    return Diagram(title, subtitle, w, h, accent)
