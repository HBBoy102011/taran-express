# -*- coding: utf-8 -*-
"""Спрайты боссов-зверей «ТАРАН-ЭКСПРЕСС».

Каждая функция рисует фигуру по кадрам анимации в переданный слой; кэш
`SPR` принадлежит game.py, поэтому при смене масштаба он очищается оттуда.
Динамические помощники рисования приходят через bind(game_module).
"""
import math

import pygame

G = None

_SYNC = (
    "D", "px", "K", "SPR", "fast", "new_surf", "outlined", "spr_trim",
    "SKULL_IMGS",
)


def bind(game_module):
    """Запоминает модуль игры (масштаб, кэш спрайтов и помощники рисования)."""
    global G
    G = game_module


def _sync():
    if G is None:
        return
    m = globals()
    for name in _SYNC:
        m[name] = getattr(G, name)


def _c_pigeon(fig, p, q):
    grey, dk, lt = (150, 160, 178), (108, 118, 138), (196, 204, 218)
    _sync()
    D.polygon(fig, dk, [(52, 128), (14, 148), (18, 168), (60, 158)])
    for sg in (1, -1):
        lx = 110 + sg * 10 + p * sg * 8
        D.line(fig, (240, 150, 50), (110 + sg * 10, 188), (lx, 211), 6)
        D.line(fig, (240, 150, 50), (lx, 211), (lx + 16, 213), 5)
    D.ellipse(fig, grey, (46, 110, 128, 84))
    D.ellipse(fig, lt, (70, 138, 84, 48))
    D.ellipse(fig, dk, (54, 118, 82, 50))
    D.ellipse(fig, (70, 170, 120), (138, 104, 36, 30))
    D.circle(fig, grey, (176, 96), 26)
    D.circle(fig, lt, (168, 90), 8)
    D.polygon(fig, (250, 170, 40), [(196, 92), (228, 102), (196, 112)])
    D.circle(fig, (255, 255, 255), (184, 90), 7)
    D.circle(fig, (210, 30, 30), (186, 91), 4)
    D.line(fig, (20, 20, 30), (174, 80), (194, 88), 3)


def _c_cat(fig, p, q):
    orange, dk, lt = (226, 142, 58), (176, 98, 36), (250, 214, 160)
    D.lines(fig, orange, False, [(54, 140), (26, 120 + p * 10), (20, 86 + p * 12), (36, 60 + p * 10)], 12)
    for lx, off in ((70, p), (92, -p), (148, -p), (170, p)):
        D.rect(fig, dk, (lx - 8 + off * 6, 160, 16, 50), border_radius=6)
        D.ellipse(fig, orange, (lx - 12 + off * 6, 200, 26, 14))
    D.ellipse(fig, orange, (50, 104, 140, 84))
    D.ellipse(fig, lt, (78, 150, 86, 34))
    for sx in (76, 104, 132):
        D.line(fig, dk, (sx, 108), (sx - 6, 132), 5)
    D.circle(fig, orange, (188, 104), 34)
    D.polygon(fig, orange, [(164, 84), (166, 50), (188, 74)])
    D.polygon(fig, orange, [(196, 72), (214, 48), (220, 92)])
    D.polygon(fig, (240, 150, 150), [(168, 78), (169, 60), (182, 74)])
    D.rect(fig, (210, 30, 40), (158, 82, 60, 9))
    D.polygon(fig, (210, 30, 40), [(158, 86), (140, 100 + p * 4), (144, 84)])
    D.ellipse(fig, (255, 235, 60), (190, 96, 16, 12))
    D.ellipse(fig, (255, 235, 60), (166, 98, 14, 11))
    D.line(fig, (10, 10, 10), (198, 94), (198, 108), 3)
    D.circle(fig, (240, 120, 130), (218, 112), 5)
    D.line(fig, (255, 255, 255), (214, 118), (240, 110), 2)
    D.line(fig, (255, 255, 255), (214, 122), (240, 126), 2)


def _c_bat(fig, p, q):
    fl = p * 14
    for sg in (-1, 1):
        c0 = 120
        pts = [(c0 + sg * 14, 96), (c0 + sg * 70, 40 - fl), (c0 + sg * 112, 70 - fl),
               (c0 + sg * 96, 98), (c0 + sg * 78, 92), (c0 + sg * 64, 122),
               (c0 + sg * 44, 106), (c0 + sg * 26, 140)]
        D.polygon(fig, (74, 42, 104), pts)
        D.polygon(fig, (40, 20, 70), pts, 3)
    D.ellipse(fig, (52, 34, 70), (94, 80, 52, 92))
    D.ellipse(fig, (84, 62, 104), (104, 104, 32, 50))
    D.polygon(fig, (150, 20, 40), [(100, 96), (140, 96), (152, 116), (88, 116)])
    D.circle(fig, (62, 42, 84), (120, 72), 26)
    D.polygon(fig, (62, 42, 84), [(100, 60), (96, 26), (116, 50)])
    D.polygon(fig, (62, 42, 84), [(140, 60), (144, 26), (124, 50)])
    for ex in (110, 130):
        D.circle(fig, (255, 40, 40), (ex, 70), 6)
        D.circle(fig, (255, 220, 200), (ex, 69), 2)
    D.polygon(fig, (255, 255, 255), [(113, 86), (118, 86), (115, 99)])
    D.polygon(fig, (255, 255, 255), [(122, 86), (127, 86), (125, 99)])
    D.line(fig, (52, 34, 70), (112, 168), (106, 190), 6)
    D.line(fig, (52, 34, 70), (128, 168), (134, 190), 6)


def _c_yeti(fig, p, q):
    fur, sh, belly = (236, 242, 250), (188, 204, 226), (214, 226, 242)
    D.rect(fig, sh, (84, 170, 32, 40), border_radius=10)
    D.rect(fig, sh, (124, 170, 32, 40), border_radius=10)
    D.ellipse(fig, fur, (76, 198, 44, 18))
    D.ellipse(fig, fur, (120, 198, 44, 18))
    D.line(fig, fur, (86, 100), (52, 150 + p * 12), 24)
    D.line(fig, fur, (154, 100), (192, 150 - p * 12), 24)
    D.circle(fig, sh, (52, 152 + p * 12), 14)
    D.circle(fig, sh, (192, 152 - p * 12), 14)
    D.ellipse(fig, fur, (70, 80, 100, 110))
    D.ellipse(fig, belly, (92, 112, 56, 62))
    D.circle(fig, fur, (120, 68), 34)
    D.ellipse(fig, (128, 160, 214), (98, 56, 44, 40))
    for ex in (110, 130):
        D.circle(fig, (255, 255, 255), (ex, 66), 6)
        D.circle(fig, (20, 40, 90), (ex, 67), 3)
    D.line(fig, (30, 50, 100), (102, 57), (116, 64), 3)
    D.line(fig, (30, 50, 100), (138, 57), (124, 64), 3)
    D.rect(fig, (40, 30, 60), (108, 80, 24, 10), border_radius=3)
    D.polygon(fig, (255, 255, 255), [(110, 80), (115, 80), (112, 88)])
    D.polygon(fig, (255, 255, 255), [(125, 80), (130, 80), (128, 88)])
    D.polygon(fig, (150, 210, 255), [(96, 42), (101, 14), (110, 38)])
    D.polygon(fig, (150, 210, 255), [(144, 42), (139, 14), (130, 38)])


def _c_frog(fig, p, q):
    g1, g2, lt = (84, 164, 72), (54, 120, 50), (196, 230, 140)
    D.ellipse(fig, g2, (40, 140, 60, 66))
    D.rect(fig, g2, (30, 196, 70, 14), border_radius=6)
    D.rect(fig, g2, (150 + p * 4, 170, 18, 40), border_radius=6)
    D.ellipse(fig, g1, (40, 96, 150, 100))
    D.ellipse(fig, lt, (80, 150, 90, 44))
    for wx, wy in ((70, 120), (104, 108), (140, 118), (88, 138)):
        D.circle(fig, g2, (wx, wy), 5)
    D.ellipse(fig, g1, (120, 76, 100, 62))
    for ex in (150, 192):
        D.circle(fig, g1, (ex, 64), 22)
        D.circle(fig, (255, 230, 80), (ex, 64), 14)
        D.ellipse(fig, (10, 10, 10), (ex - 3, 52, 6, 24))
    D.line(fig, (30, 70, 30), (130, 112), (216, 118), 4)
    D.line(fig, (230, 80, 110), (216, 118), (232, 130 + p * 6), 6)
    D.circle(fig, (240, 240, 120), (118, 118), 3)


def _c_robot(fig, p, q):
    steel, dk, neon, mag = (150, 160, 180), (70, 76, 96), (0, 230, 230), (255, 70, 200)
    D.rect(fig, dk, (92, 160, 26, 50))
    D.rect(fig, dk, (124, 160, 26, 50))
    D.rect(fig, steel, (86, 200, 40, 14), border_radius=4)
    D.rect(fig, steel, (120, 200, 40, 14), border_radius=4)
    D.line(fig, dk, (76, 96), (48, 130 + p * 10), 16)
    D.line(fig, dk, (168, 96), (198, 130 - p * 10), 16)
    D.polygon(fig, steel, [(38, 128 + p * 10), (60, 128 + p * 10), (49, 154 + p * 10)])
    D.polygon(fig, steel, [(188, 128 - p * 10), (210, 128 - p * 10), (199, 154 - p * 10)])
    D.rect(fig, steel, (76, 80, 92, 88), border_radius=12)
    D.rect(fig, dk, (88, 96, 68, 50), border_radius=8)
    D.circle(fig, neon, (122, 120), 14)
    D.circle(fig, (220, 255, 255), (122, 120), 6)
    for i in range(3):
        D.rect(fig, mag, (94 + i * 16, 152, 10, 5))
    D.rect(fig, neon, (76, 80, 92, 88), 2, border_radius=12)
    D.rect(fig, steel, (92, 38, 60, 44), border_radius=10)
    D.rect(fig, neon, (98, 52, 48, 12), border_radius=4)
    D.rect(fig, (255, 60, 60), (118 + p * 14, 54, 8, 8))
    D.line(fig, dk, (122, 38), (122, 14), 4)
    D.circle(fig, mag, (122, 12), 6)


def _c_scorpion(fig, p, q):
    tan, dk, lt = (206, 150, 70), (146, 98, 40), (236, 190, 110)
    for i in range(4):
        bx = 70 + i * 24
        sw = p * 6 if i % 2 else -p * 6
        D.lines(fig, dk, False, [(bx, 170), (bx - 10 + sw, 196), (bx - 14, 212)], 6)
    pts = [(54, 150), (30, 132), (24, 100), (40, 70), (70, 52), (98, 56 + p * 4)]
    D.lines(fig, tan, False, pts, 16)
    for i, pt in enumerate(pts):
        D.circle(fig, lt if i % 2 else tan, pt, 9)
    D.polygon(fig, (220, 40, 40), [(96, 42 + p * 4), (130, 64 + p * 4), (98, 72 + p * 4)])
    D.ellipse(fig, tan, (52, 138, 120, 56))
    for sx in (74, 98, 122):
        D.line(fig, dk, (sx, 142), (sx, 190), 3)
    D.ellipse(fig, tan, (150, 146, 44, 42))
    D.circle(fig, (255, 50, 50), (184, 152), 5)
    D.line(fig, dk, (176, 160), (206, 140 + p * 8), 10)
    D.polygon(fig, tan, [(200, 126 + p * 8), (238, 138 + p * 8), (212, 154 + p * 8)])
    D.polygon(fig, dk, [(200, 126 + p * 8), (238, 138 + p * 8), (212, 154 + p * 8)], 2)


def _c_dino(fig, p, q):
    red, dk, lt = (176, 52, 32), (120, 30, 22), (236, 150, 70)
    D.polygon(fig, red, [(70, 120), (8, 168 + p * 4), (14, 186), (86, 168)])
    D.rect(fig, dk, (96 + p * 6, 150, 30, 52), border_radius=8)
    D.ellipse(fig, dk, (90 + p * 6, 196, 52, 18))
    D.rect(fig, dk, (132 - p * 6, 150, 30, 52), border_radius=8)
    D.ellipse(fig, dk, (126 - p * 6, 196, 52, 18))
    D.ellipse(fig, red, (60, 86, 120, 90))
    D.ellipse(fig, lt, (84, 132, 84, 42))
    for i in range(5):
        sx = 76 + i * 18
        D.polygon(fig, (255, 150, 40), [(sx, 94 - i * 2), (sx + 9, 94 - i * 2), (sx + 4, 74 - i * 2)])
    D.polygon(fig, red, [(150, 96), (168, 44), (200, 46), (206, 100)])
    D.polygon(fig, red, [(162, 46), (236, 44), (238, 76), (210, 80), (160, 92)])
    D.polygon(fig, dk, [(170, 84 + p * 3), (236, 80 + p * 3), (228, 100 + p * 3), (176, 102 + p * 3)])
    for tx in range(184, 232, 10):
        D.polygon(fig, (255, 255, 255), [(tx, 78 + p * 2), (tx + 6, 78 + p * 2), (tx + 3, 88 + p * 2)])
    D.circle(fig, (255, 220, 60), (190, 58), 7)
    D.circle(fig, (10, 0, 0), (192, 58), 3)
    D.line(fig, (40, 10, 10), (180, 48), (202, 56), 4)
    D.line(fig, dk, (150, 112), (172, 130), 8)
    D.lines(fig, (255, 170, 50), False, [(100, 100), (112, 116), (104, 130)], 3)
    D.polygon(fig, (255, 140, 40), [(238, 56), (252, 50 + p * 3), (240, 66)])


def _c_octopus(fig, p, q):
    pur, lt = (130, 70, 190), (190, 130, 240)
    ph = math.atan2(p, q)
    for i in range(6):
        bx = 72 + i * 19
        pts = []
        for j in range(6):
            pts.append((bx + math.sin(j * 0.9 + i * 0.7 + ph) * 10 + (i - 2.5) * j * 3, 120 + j * 18))
        D.lines(fig, pur, False, pts, 12)
        D.circle(fig, lt, pts[-1], 7)
    D.circle(fig, pur, (120, 86), 54)
    D.ellipse(fig, lt, (78, 46, 44, 24))
    for ex in (102, 138):
        D.circle(fig, (255, 240, 100), (ex, 92), 14)
        D.ellipse(fig, (10, 0, 20), (ex - 3, 82, 6, 20))
    D.line(fig, (50, 20, 90), (88, 76), (112, 84), 4)
    D.line(fig, (50, 20, 90), (152, 76), (128, 84), 4)
    for sx, sy in ((84, 108), (156, 106), (120, 52), (100, 58)):
        D.circle(fig, (120, 255, 220), (sx, sy), 4)
    D.ellipse(fig, (40, 10, 60), (104, 114, 32, 16))
    D.polygon(fig, (255, 255, 255), [(108, 114), (113, 114), (110, 122)])
    D.polygon(fig, (255, 255, 255), [(127, 114), (132, 114), (130, 122)])
    D.line(fig, pur, (120, 34), (120, 14), 5)
    D.circle(fig, (120, 255, 200), (120, 12), 7)


def _c_skull(fig, p, q):
    robe, robe2 = (60, 30, 110), (110, 60, 180)
    ph = math.atan2(p, q)
    bottom = []
    for i in range(9):
        bottom.append((190 - i * 17.5, 208 + math.sin(i * 1.3 + ph) * 8))
    D.polygon(fig, robe, [(72, 100), (168, 100)] + bottom)
    D.polygon(fig, robe2, [(96, 120), (144, 120), (156, 200), (84, 200)])
    D.ellipse(fig, robe, (36, 108 + p * 6, 34, 64))
    D.ellipse(fig, robe, (170, 108 - p * 6, 34, 64))
    D.circle(fig, (236, 228, 208), (52, 176 + p * 6), 10)
    D.circle(fig, (236, 228, 208), (188, 176 - p * 6), 10)
    img = pygame.transform.smoothscale(SKULL_IMGS[0], (px(116), px(116)))
    fig.blit(img, (px(62), px(26)))


def _c_dragon(fig, p, q):
    body, dk, lt, fire = (60, 150, 200), (30, 90, 140), (170, 225, 245), (255, 150, 40)
    fl = p * 34
    # дальнее крыло
    D.polygon(fig, dk, [(105, 100), (62, 30 - fl), (24, 50 - fl), (48, 80 - fl * 0.4), (32, 100), (72, 112)])
    # хвост
    D.lines(fig, body, False, [(64, 140), (36, 160), (20, 152 + p * 8), (10, 168)], 14)
    D.polygon(fig, fire, [(4, 158 + p * 8), (24, 168 + p * 8), (8, 186 + p * 8)])
    # лапы
    D.line(fig, dk, (100, 170), (96, 198), 8)
    D.line(fig, dk, (140, 170), (146, 196), 8)
    # тело и брюхо
    D.ellipse(fig, body, (56, 100, 130, 80))
    D.ellipse(fig, lt, (80, 132, 90, 40))
    for i in range(5):
        sx = 76 + i * 20
        D.polygon(fig, fire, [(sx, 104 - i), (sx + 10, 104 - i), (sx + 5, 86 - i)])
    # шея и голова
    D.polygon(fig, body, [(150, 104), (170, 62), (198, 66), (186, 116)])
    D.polygon(fig, body, [(168, 60), (232, 62), (236, 84), (200, 92), (170, 86)])
    D.polygon(fig, dk, [(176, 84), (234, 84), (224, 98), (184, 96)])
    for tx in range(190, 228, 10):
        D.polygon(fig, (255, 255, 255), [(tx, 84), (tx + 6, 84), (tx + 3, 92)])
    D.polygon(fig, dk, [(172, 60), (160, 34), (192, 54)])
    D.circle(fig, (255, 220, 60), (198, 70), 7)
    D.circle(fig, (10, 0, 0), (200, 70), 3)
    D.line(fig, (20, 40, 60), (188, 60), (208, 68), 4)
    D.circle(fig, dk, (228, 70), 2)
    # ближнее крыло
    wing = [(118, 98), (84, 22 - fl), (38, 38 - fl), (64, 72 - fl * 0.4), (48, 96), (92, 108)]
    D.polygon(fig, lt, wing)
    D.polygon(fig, dk, wing, 3)


_CREATURES = {"pigeon": _c_pigeon, "cat": _c_cat, "bat": _c_bat, "yeti": _c_yeti, "frog": _c_frog,
              "robot": _c_robot, "scorpion": _c_scorpion, "dino": _c_dino, "octopus": _c_octopus,
              "skull": _c_skull, "dragon": _c_dragon}


def creature_surf(kind, fr, d):
    """Кадр секретного босса (240x240); рисуется лицом вправо, влево — зеркалом."""
    _sync()
    key = ("crt", K, kind, fr, d)
    fig = SPR.get(key)
    if fig is None:
        fig = new_surf(240, 240)
        p = math.sin(fr * math.pi / 2)
        q = math.cos(fr * math.pi / 2)
        _CREATURES[kind](fig, p, q)
        fig = fast(outlined(fig))
        if d < 0:
            fig = pygame.transform.flip(fig, True, False)
        SPR[key] = fig
        spr_trim()
    return fig
