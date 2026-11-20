# -*- coding: utf-8 -*-
"""Ресурсы «ТАРАН-ЭКСПРЕСС», зависящие от масштаба рендера.

Виньетка, конусы света, тени, череп, кислота на стекле и фон магазина
пересобираются в game.build_assets() при старте и смене качества.
Динамические помощники рисования приходят через bind(game_module).
"""
import math
import random

import pygame

from taran.config import H, PW, W

G = None

_SYNC = (
    "D", "px", "K", "GWP", "PWP", "HP", "fast", "new_surf", "vband", "lerp_c",
    "outlined",
)


def bind(game_module):
    """Запоминает модуль игры (масштаб и помощники рисования)."""
    global G
    G = game_module


def _sync():
    """Подтягивает актуальные значения из game.py перед сборкой ресурса."""
    if G is None:
        return
    m = globals()
    for name in _SYNC:
        m[name] = getattr(G, name)


def make_vignette():
    """Карта затемнения по краям; накладывается через BLEND_RGB_MULT (быстрее alpha-blit)."""
    _sync()
    sw, sh = 64, 40
    s = pygame.Surface((sw, sh))
    for y in range(sh):
        for x in range(sw):
            dx = (x / (sw - 1) - 0.5) * 2
            dy = (y / (sh - 1) - 0.5) * 2
            d = math.sqrt(dx * dx * 0.8 + dy * dy)
            a = max(0.0, min(1.0, (d - 0.62) / 0.75)) ** 1.6 * 150 / 255.0
            v = int(255 * (1 - a))
            s.set_at((x, y), (v, v, min(255, v + 4)))
    return fast(pygame.transform.smoothscale(s, (GWP, HP)), False)


def make_cone(w, h, vertical, peak):
    """Конус света: вертикальный (фонарь) или горизонтальный (прожектор поезда)."""
    _sync()
    pw, ph = px(w), px(h)
    s = pygame.Surface((pw, ph), pygame.SRCALPHA)
    if vertical:
        for y in range(ph):
            k = y / ph
            half = int((10 + (w / 2 - 10) * k) * K)
            a = int(peak * (1 - k) ** 1.5)
            # три вложенных полосы: у конуса мягкие края, а не резкий треугольник
            pygame.draw.line(s, (255, 236, 160, a // 3), (pw // 2 - half, y), (pw // 2 + half, y))
            mid = int(half * 0.7)
            pygame.draw.line(s, (255, 240, 172, (a * 2) // 3), (pw // 2 - mid, y), (pw // 2 + mid, y))
            inner = int(half * 0.38)
            pygame.draw.line(s, (255, 246, 200, a), (pw // 2 - inner, y), (pw // 2 + inner, y))
    else:
        for x in range(pw):
            k = (pw - 1 - x) / pw
            half = int((6 + (h / 2 - 6) * k) * K)
            a = int(peak * (1 - k) ** 1.35)
            # три вложенные полосы: у луча мягкие края
            pygame.draw.line(s, (255, 236, 176, a // 3), (x, ph // 2 - half), (x, ph // 2 + half))
            mid = int(half * 0.7)
            pygame.draw.line(s, (255, 242, 188, (a * 2) // 3), (x, ph // 2 - mid), (x, ph // 2 + mid))
            inner = int(half * 0.36)
            pygame.draw.line(s, (255, 250, 216, a), (x, ph // 2 - inner), (x, ph // 2 + inner))
    return fast(s)


def make_shadow(big):
    if big:
        s = new_surf(90, 22)
        D.ellipse(s, (0, 0, 0, 50), (0, 0, 90, 22))
        D.ellipse(s, (0, 0, 0, 70), (12, 4, 66, 14))
    else:
        s = new_surf(46, 14)
        D.ellipse(s, (0, 0, 0, 40), (0, 0, 46, 14))
        D.ellipse(s, (0, 0, 0, 60), (6, 2, 34, 10))
    return fast(s)


def make_skull(jaw=0):
    """Череп с запасом по разрешению (576 px): он летит в камеру и растягивается на весь экран.
    Объёмная кость с градиентом, трещины, злые пылающие глаза, клыки и челюсть, которая щёлкает."""
    _sync()
    S = 6
    s = pygame.Surface((96 * S, 96 * S), pygame.SRCALPHA)
    dr = pygame.draw

    def R(x, y, w, h):
        return (int(x * S), int(y * S), int(w * S), int(h * S))

    def P(*pts):
        return [(int(x * S), int(y * S)) for x, y in pts]

    bone = (238, 230, 210)
    mid = (208, 198, 172)
    shade = (152, 140, 118)
    deep = (92, 82, 70)
    hi = (255, 252, 240)
    black = (8, 6, 10)
    jy = 9 * jaw                       # на сколько опущена челюсть

    # --- нижняя челюсть (рисуется первой, она позади черепа) ---
    dr.rect(s, shade, R(24, 70 + jy, 48, 19), border_radius=9 * S)
    dr.rect(s, bone, R(25, 70 + jy, 46, 16), border_radius=8 * S)
    dr.rect(s, mid, R(25, 79 + jy, 46, 7), border_radius=6 * S)
    dr.line(s, deep, (48 * S, 79 * S + jy * S), (48 * S, 87 * S + jy * S), S)    # шов подбородка
    # тёмный рот
    dr.rect(s, black, R(26, 62, 44, 12 + jy), border_radius=4 * S)
    # нижние зубы
    for i in range(8):
        tx = 28.5 + i * 5.2
        dr.rect(s, hi, R(tx, 69 + jy, 4, 7), border_radius=S)
        dr.rect(s, shade, R(tx, 69 + jy, 4, 7), max(1, S // 3), border_radius=S)

    # --- череп: объём из слоёв, свет сверху-слева ---
    dr.ellipse(s, deep, R(9, 2, 78, 68))
    dr.ellipse(s, shade, R(11, 3, 74, 65))
    layers = 9
    for i in range(layers):
        k = i / (layers - 1)
        c = lerp_c(mid, hi, k)
        dr.ellipse(s, c, R(12 + i * 1.3, 4 + i * 1.0, 72 - i * 3.4, 60 - i * 3.2))
    # скулы и верхняя челюсть
    dr.rect(s, shade, R(21, 47, 54, 24), border_radius=10 * S)
    dr.rect(s, bone, R(22, 47, 52, 22), border_radius=9 * S)
    for cx_ in (12, 66):
        dr.ellipse(s, shade, R(cx_, 38, 19, 20))
        dr.ellipse(s, bone, R(cx_ + 1, 38, 17, 18))
        dr.ellipse(s, hi, R(cx_ + 3, 40, 7, 6))

    # --- шов на лбу и трещины ---
    dr.lines(s, deep, False, P((49, 6), (46, 12), (51, 18), (47, 25)), int(S * 1.2))
    dr.lines(s, deep, False, P((64, 7), (60, 14), (66, 21), (61, 30), (63, 36)), int(S * 1.6))
    dr.lines(s, deep, False, P((60, 14), (54, 17)), S)
    dr.lines(s, deep, False, P((24, 13), (29, 20), (26, 26)), S)

    # --- глазницы: злые, скошенные внутрь ---
    left = [(16, 31), (31, 26), (46, 37), (43, 52), (28, 55), (17, 46)]
    right = [(96 - x, y) for x, y in left]
    for pts in (left, right):
        dr.polygon(s, deep, P(*pts))
        inner = [((x - 48) * 0.88 + 48 if x < 48 else (x - 48) * 0.88 + 48, y) for x, y in pts]
        dr.polygon(s, black, P(*inner))
    # пылающие зрачки
    for ex in (31, 65):
        dr.circle(s, (90, 6, 6), (ex * S, 42 * S), 9 * S)
        dr.circle(s, (200, 24, 14), (ex * S, 42 * S), 6.5 * S)
        dr.circle(s, (255, 110, 30), (ex * S, 42 * S), 4.2 * S)
        dr.circle(s, (255, 225, 120), (ex * S, 41 * S), 2 * S)
    # тяжёлые брови над глазницами
    dr.line(s, deep, (14 * S, 29 * S), (46 * S, 37 * S), int(S * 2.2))
    dr.line(s, deep, (82 * S, 29 * S), (50 * S, 37 * S), int(S * 2.2))

    # --- нос: перевёрнутое сердечко ---
    dr.polygon(s, black, P((48, 51), (42, 61), (45, 66), (48, 62), (51, 66), (54, 61)))

    # --- верхние зубы и клыки ---
    for i in range(8):
        tx = 28.5 + i * 5.2
        dr.rect(s, hi, R(tx, 61, 4, 9), border_radius=S)
        dr.rect(s, shade, R(tx, 61, 4, 9), max(1, S // 3), border_radius=S)
    for fx in (30.5, 65.5):            # клыки
        dr.polygon(s, hi, P((fx - 2.5, 62), (fx + 2.5, 62), (fx, 74 + jy * 0.5)))
        dr.polygon(s, shade, P((fx - 2.5, 62), (fx + 2.5, 62), (fx, 74 + jy * 0.5)), max(1, S // 3))

    # тёмная кромка, чтобы череп «держал» объём
    dr.ellipse(s, deep, R(9, 2, 78, 68), S)
    return fast(outlined(s, (6, 4, 8), o=S))


def make_acid_overlay():
    """Кислота на «стекле» камеры: капли и потёки поверх всего экрана."""
    _sync()
    s = new_surf(W, H)
    for _ in range(random.randint(7, 10)):
        r = random.randint(80, 210)
        x, y = random.randint(-30, W - 30), random.randint(-30, H - 30)
        D.circle(s, (66, 185, 38, 150), (x, y), r)
        D.circle(s, (120, 225, 66, 110), (x - r // 4, y - r // 4), max(6, r * 2 // 3))
        D.circle(s, (185, 250, 120, 70), (x - r // 3, y - r // 3), max(4, r // 3))
        for _ in range(6):
            D.circle(s, (90, 210, 50, random.randint(70, 145)),
                     (x + random.randint(-r, r), y + random.randint(-r, r)),
                     random.randint(3, 13))
        # потёк вниз
        fx = x + random.randint(-r // 2, r // 2)
        fh = random.randint(40, 150)
        D.rect(s, (86, 205, 46, 130), (fx, y, random.randint(6, 14), fh), border_radius=6)
    return fast(s)


def build_panel_bg():
    """Фон магазина: глубокий градиент, мягкое свечение сверху и шапка."""
    _sync()
    base = pygame.Surface((PWP, HP))
    vband(base, 0, PW, 0, H, (30, 34, 50), (12, 14, 22))
    # подсветка шапки: плавно гаснет вниз, без резкой полосы
    n = max(1, px(88))
    for y in range(n):
        t = 1.0 - y / n
        base.fill(lerp_c((30, 34, 50), (54, 78, 132), 0.30 * t), (0, y, PWP, 1))
    D.rect(base, (48, 54, 78), (0, px(56), PWP, max(1, px(1))))
    D.rect(base, (10, 12, 20), (0, px(57), PWP, max(1, px(1))))
    # тонкая кромка со стороны игрового поля
    D.rect(base, (54, 62, 86), (0, 0, max(1, px(1)), HP))
    return fast(base, False)
