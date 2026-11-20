# -*- coding: utf-8 -*-
"""Поезд «ТАРАН-ЭКСПРЕСС»: спрайт состава и объект Train.

Спрайт собирается один раз на цвет/ночь и кэшируется; каждый кадр поезд
только едет по экрану. Динамические помощники рисования приходят через
bind(game_module), как в progression.py и taran/world.py.
"""
import math

import pygame

from taran.config import GW, TRAIN_Y

G = None

# кэш собранных спрайтов; game.build_assets() очищает его при смене масштаба
TRAIN_CACHE = {}

_SYNC = (
    "D", "K", "fast", "lerp_c", "new_surf", "vband", "blit", "glow", "px",
    "HEAD_CONE",
)


def bind(game_module):
    """Запоминает модуль игры (масштаб и помощники рисования)."""
    global G
    G = game_module


def _sync():
    """Подтягивает актуальные значения из game.py перед рисованием."""
    if G is None:
        return
    m = globals()
    for name in _SYNC:
        m[name] = getattr(G, name)


def train_sprite(body, night, gold):
    """Корпус поезда рисуется один раз на каждый цвет; по экрану едет готовая картинка."""
    _sync()
    key = (K, body, night, gold)
    hit = TRAIN_CACHE.get(key)
    if hit is not None:
        return hit
    h = 110
    dark = lerp_c(body, (0, 0, 0), 0.42)
    deep = lerp_c(body, (0, 0, 0), 0.66)
    lite = lerp_c(body, (255, 255, 255), 0.32)
    stripe = lerp_c(body, (255, 255, 255), 0.55)
    wc = (255, 226, 140) if night else (170, 214, 245)
    wc2 = (255, 245, 200) if night else (228, 244, 255)
    s = new_surf(Train.LENGTH, h + 10)
    wheels_all = []
    parts = [(0, 230)] + [(238 + i * 198, 190) for i in range(3)]
    for idx, (ox, w) in enumerate(parts):
        r = pygame.Rect(ox, 0, w, h)
        rr = 12 if idx == 0 else 8
        # тележка и тень под кузовом
        D.rect(s, (14, 14, 20), (r.x + 8, r.y + h - 10, w - 16, 16), border_radius=5)
        D.rect(s, (38, 38, 46), (r.x + 14, r.y + h - 19, w - 28, 10), border_radius=3)
        D.line(s, (68, 68, 80), (r.x + 18, r.y + h - 18), (r.x + w - 18, r.y + h - 18), 1)
        # корпус: контур, тело, боковой градиент
        D.rect(s, deep, r, border_radius=rr)
        D.rect(s, body, (r.x + 1, r.y + 1, w - 2, h - 6), border_radius=rr - 1)
        vband(s, r.x + 3, r.x + w - 3, r.y + 8, r.y + h - 10, lite, lerp_c(body, (0, 0, 0), 0.10))
        # крыша с гофром и вентиляцией
        D.rect(s, dark, (r.x + 1, r.y + 1, w - 2, 9), border_radius=5)
        D.rect(s, lerp_c(dark, (255, 255, 255), 0.16), (r.x + 5, r.y + 1, w - 10, 2))
        for vx in range(r.x + 12, r.x + w - 10, 13):
            D.line(s, deep, (vx, r.y + 4), (vx, r.y + 8), 1)
        for vx in (r.x + int(w * 0.34), r.x + int(w * 0.70)):
            D.rect(s, (54, 54, 62), (vx - 9, r.y - 3, 18, 5), border_radius=2)
            D.rect(s, (96, 96, 108), (vx - 7, r.y - 3, 14, 2))
        # окна в тёмных нишах с переплётом и бликом
        if idx == 0:
            wins = ((r.x + 30, 22, 70, 38), (r.x + 118, 22, 50, 38))
        else:
            wins = [(r.x + 12 + k * 56, 24, 42, 34) for k in range(3)]
        for (wx, wy, ww, wh) in wins:
            D.rect(s, deep, (wx - 5, wy - 5, ww + 10, wh + 11), border_radius=7)
            D.rect(s, lerp_c(wc, (0, 0, 0), 0.32), (wx - 2, wy - 2, ww + 4, wh + 4), border_radius=5)
            D.rect(s, wc, (wx, wy, ww, wh), border_radius=4)
            D.line(s, lerp_c(wc, (0, 0, 0), 0.35), (wx + ww // 2, wy + 3), (wx + ww // 2, wy + wh - 3), 2)
            D.polygon(s, wc2, [(wx + 6, wy + wh - 4), (wx + 18, wy + 3), (wx + 27, wy + 3),
                               (wx + 14, wy + wh - 4)])
            D.line(s, lerp_c(wc2, (255, 255, 255), 0.5), (wx + 4, wy + wh - 6), (wx + ww - 6, wy + 4), 1)
            D.rect(s, dark, (wx - 4, wy + wh + 3, ww + 8, 3), border_radius=2)
        # тамбур с дверью
        if idx:
            dx = r.x + w - 26
            D.rect(s, deep, (dx - 3, r.y + 15, 22, 62), border_radius=4)
            D.rect(s, lerp_c(body, (0, 0, 0), 0.12), (dx, r.y + 17, 16, 58), border_radius=3)
            D.rect(s, wc, (dx + 3, r.y + 21, 10, 22), border_radius=2)
            D.line(s, deep, (dx + 8, r.y + 17), (dx + 8, r.y + 75), 1)
            D.rect(s, (64, 64, 76), (dx + 2, r.y + 50, 12, 3), border_radius=1)
            D.rect(s, (36, 36, 44), (dx - 4, r.y + h - 8, 24, 5), border_radius=2)
        # нижняя юбка, полоса и заклёпки
        D.rect(s, dark, (r.x + 1, r.y + h - 26, w - 2, 12), border_radius=4)
        D.rect(s, stripe, (r.x + 2, r.y + h - 40, w - 4, 7))
        D.rect(s, lerp_c(stripe, (0, 0, 0), 0.45), (r.x + 2, r.y + h - 33, w - 4, 2))
        for rx in range(r.x + 12, r.x + w - 8, 26):
            D.circle(s, lerp_c(body, (255, 255, 255), 0.20), (rx, r.y + h - 22), 2)
            D.circle(s, lerp_c(dark, (255, 255, 255), 0.20), (rx, r.y + 12), 1)
        # колёсная пара
        wheels = [r.x + 28, r.x + w - 30] + ([r.x + w // 2] if idx == 0 else [])
        for wx in wheels:
            cy = h - 4
            D.circle(s, (22, 22, 28), (wx, cy), 13)
            D.circle(s, (86, 86, 98), (wx, cy), 13, 2)
            D.circle(s, (140, 140, 152), (wx, cy), 6)
            D.circle(s, (46, 46, 54), (wx, cy), 3)
            for a in range(4):
                ang = a * math.pi / 2 + 0.4
                D.line(s, (110, 110, 122), (wx + math.cos(ang) * 4, cy + math.sin(ang) * 4),
                       (wx + math.cos(ang) * 11, cy + math.sin(ang) * 11), 1)
            wheels_all.append((wx, cy))
        # носовая часть локомотива
        if idx == 0:
            D.rect(s, (34, 34, 42), (r.x, 16, 9, h - 32), border_radius=4)
            D.rect(s, (78, 78, 90), (r.x + 1, 20, 3, h - 40))
            D.rect(s, (26, 26, 32), (r.x + 2, 52, 8, 20), border_radius=3)
    # межвагонные сцепки
    for ex in (222, 420, 618):
        D.rect(s, (42, 42, 50), (ex, 84, 18, 11), border_radius=3)
        D.line(s, (98, 98, 110), (ex + 2, 88), (ex + 16, 88), 1)
    D.circle(s, (255, 245, 170), (6, 66), 8)
    D.circle(s, (255, 255, 240), (5, 64), 4)
    if len(TRAIN_CACHE) > 8:
        TRAIN_CACHE.clear()
    hit = (fast(s), wheels_all)
    TRAIN_CACHE[key] = hit
    return hit


class Train:
    LENGTH = 824

    def __init__(self, gold=False):
        _sync()
        self.x = GW + 20
        self.speed = 1100
        self.gold = gold

    def rect(self):
        return pygame.Rect(self.x, TRAIN_Y, self.LENGTH, 110)

    def update(self, dt):
        self.x -= self.speed * dt

    def done(self):
        return self.x + self.LENGTH < 0

        _sync()
    def draw(self, surf, col, light):
        x = int(self.x)
        y = TRAIN_Y
        body = (235, 190, 40) if self.gold else col["train"]
        spr, wheels = train_sprite(body, light > 0.4, self.gold)
        # прожектор спереди
        if light > 0.3 or self.gold:
            HEAD_CONE.set_alpha(int(255 * max(light, 0.6 if self.gold else 0)))
            surf.blit(HEAD_CONE, (px(x + 6) - HEAD_CONE.get_width(), px(y + 68) - HEAD_CONE.get_height() // 2))
        # линии скорости позади
        for k in range(5):
            ly = y + 16 + k * 20
            ln = 60 + 26 * ((k * 7) % 4)
            D.line(surf, lerp_c(col["bed"], (255, 255, 255), 0.35),
                   (x + self.LENGTH + 6, ly), (x + self.LENGTH + 6 + ln, ly), 2)
        blit(surf, spr, (x, y))
        ang = self.x * 0.08
        for (wx, cy) in wheels:
            D.line(surf, (170, 170, 180), (x + wx, y + cy),
                   (x + wx + math.cos(ang) * 10, y + cy + math.sin(ang) * 10), 2)
        if light > 0.3 or self.gold:
            glow(surf, (x - 10, y + 66), 110, (255, 240, 170), int(130 * max(light, 0.6 if self.gold else 0)))
        if self.gold:
            for k in range(4):                # блестящие искорки на золотом поезде
                sx = x + 40 + ((pygame.time.get_ticks() // 7 + k * 211) % (self.LENGTH - 80))
                D.circle(surf, (255, 255, 220), (sx, y + 12 + (k * 23) % 60), 2)
