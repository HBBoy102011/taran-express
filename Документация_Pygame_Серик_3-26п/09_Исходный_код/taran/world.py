# -*- coding: utf-8 -*-
"""Мир «ТАРАН-ЭКСПРЕСС»: небо, город, платформа, пути, погода.

Класс World рисует статичные слои один раз и кэширует их, а каждый кадр
двигает только облака, дома, снег/дождь и искры. Модуль не импортирует
game.py: динамические помощники (масштаб, шрифты, D) приходят через
bind(game_module), как в progression.py и taran/ui/shop.py.
"""
import math
import random

import pygame

from taran.config import (
    GW, H, KEYS, KEYCOL, PLAT_BOT, PLAT_TOP, STAR_KINDS, STRIP_H, TRAIN_Y,
)

G = None

# имена, которые меняются при смене разрешения или собираются в build_assets()
_SYNC = (
    "K", "GWP", "HP", "WEB", "D", "px", "fast", "glow", "lerp_c", "text",
    "f_mid", "vband", "LAMP_CONE",
)


def bind(game_module):
    """Запоминает модуль игры (шрифты, масштаб, помощники рисования)."""
    global G
    G = game_module


def _sync():
    """Подтягивает актуальные значения из game.py перед отрисовкой."""
    if G is None:
        return
    m = globals()
    for name in _SYNC:
        m[name] = getattr(G, name)


class World:
    def __init__(self):
        _sync()
        rnd = random.Random(7)
        self.t = 0.0
        self.cache = {}
        self._back_key = None
        self._back_surf = None
        self._fg_key = None
        self._fg_surf = None
        self.clouds = [[rnd.uniform(0, GW), rnd.uniform(40, 220), rnd.uniform(0.7, 1.5), rnd.uniform(8, 22)]
                       for _ in range(7)]
        # в WASM каждый лишний draw-call стоит дорого — погоды и звёзд там меньше
        self.stars = [(rnd.uniform(0, GW), rnd.uniform(0, 300), rnd.uniform(0, 6))
                      for _ in range(56 if WEB else 90)]
        self.snow = [[random.uniform(0, GW), random.uniform(0, H), random.uniform(40, 90),
                      random.uniform(-15, 15), random.randint(2, 4)]
                     for _ in range(90 if WEB else 150)]
        self.rain = [[random.uniform(0, GW + 100), random.uniform(0, H), random.uniform(650, 900)]
                     for _ in range(120 if WEB else 220)]
        self.far = []
        x = 0
        while x < GW + 300:
            w = rnd.randint(50, 110)
            self.far.append((x, w, rnd.randint(60, 170)))
            x += w + rnd.randint(0, 18)
        self.far_span = x
        self.far2 = []
        x = 0
        while x < GW + 300:
            w = rnd.randint(40, 90)
            self.far2.append((x, w, rnd.randint(110, 230)))
            x += w + rnd.randint(0, 10)
        self.far2_span = x
        self.near = []
        x = 0
        while x < GW + 300:
            w = rnd.randint(70, 130)
            self.near.append((x, w, rnd.randint(100, 240), rnd.randint(0, 10 ** 6)))
            x += w + rnd.randint(4, 30)
        self.near_span = x
        self.gravel = [(rnd.randint(0, GW), rnd.randint(TRAIN_Y + 6, H - 4), rnd.randint(1, 3), rnd.random())
                       for _ in range(260)]
        self.flash = 0.0
        self.flash_t = random.uniform(4, 8)
        self.flash_surf = None
        self.flash_k = None

    # --- кэш статичных слоёв: пересобирается только когда меняются цвета локации ---
    def _ck(self, col, extra=()):
        return (K,) + tuple(col[k] for k in KEYS) + (round(col["light"], 3),) + tuple(extra)

    def _put(self, key, val):
        self.cache[key] = val
        while len(self.cache) > 48:
            self.cache.pop(next(iter(self.cache)))
        return val

    def update(self, dt, kind):
        _sync()
        self.t += dt
        for c in self.clouds:
            c[0] += c[3] * dt
            if c[0] > GW + 160:
                c[0] = -160
        if kind == "snow":
            for p in self.snow:
                p[1] += p[2] * dt
                p[0] += p[3] * dt
                if p[1] > H:
                    p[1] = -5
                    p[0] = random.uniform(0, GW)
        if kind == "lava":      # искры летят вверх
            for p in self.snow:
                p[1] -= p[2] * 1.4 * dt
                p[0] += p[3] * dt
                if p[1] < -5:
                    p[1] = H + 5
                    p[0] = random.uniform(0, GW)
        if kind == "rain":
            for d in self.rain:
                d[1] += d[2] * dt
                d[0] -= d[2] * 0.15 * dt
                if d[1] > H:
                    d[1] = -10
                    d[0] = random.uniform(0, GW + 100)
            self.flash_t -= dt
            if self.flash_t <= 0:
                self.flash = 1.0
                self.flash_t = random.uniform(4, 9)
        self.flash = max(0.0, self.flash - dt * 3)

    def flash_surface(self):
        _sync()
        if self.flash_surf is None or self.flash_k != K:
            s = pygame.Surface((GWP, HP))
            s.fill((255, 255, 255))
            self.flash_surf = fast(s, False)
            self.flash_k = K
        return self.flash_surf

    def sky(self, col, kind):
        _sync()
        key = self._ck(col, ("sky", kind))
        s = self.cache.get(key)
        if s is None:
            n = px(PLAT_TOP)
            s = pygame.Surface((GWP, n))
            for y in range(n):
                s.fill(lerp_c(col["top"], col["bot"], (y / n) ** 0.9), (0, y, GWP, 1))
            if kind != "finale":          # у финала светило пульсирует — оно рисуется каждый кадр
                self.draw_body(s, col, kind)
            s = self._put(key, fast(s, False))
        return s

    def haze(self, col):
        _sync()
        key = self._ck(col, ("haze",))
        s = self.cache.get(key)
        if s is None:
            n = px(150)
            s = pygame.Surface((GWP, n), pygame.SRCALPHA)
            c = col["bot"]
            for y in range(n):
                s.fill((c[0], c[1], c[2], int(170 * (y / n) ** 1.7)), (0, y, GWP, 1))
            s = self._put(key, fast(s))
        return s

    def cloud(self, sc, ccol):
        _sync()
        key = ("cloud", K, sc, ccol)
        hit = self.cache.get(key)
        if hit is None:
            ox, oy = 30 * sc, 46 * sc
            s = pygame.Surface((px(124 * sc), px(94 * sc)), pygame.SRCALPHA)
            shade = lerp_c(ccol, (0, 0, 0), 0.20)
            lite = lerp_c(ccol, (255, 255, 255), 0.50)
            blobs = ((0, 6, 25), (26, -4, 31), (56, 6, 25), (28, 14, 26), (82, 10, 19))

            def puff(dx, dy, r, color):
                D.circle(s, color, (ox + dx * sc, oy + dy * sc), r * sc)

            for dx, dy, r in blobs:            # воздушная кромка
                puff(dx, dy, r + 5, (*ccol, 45))
            for dx, dy, r in blobs:            # тень снизу
                puff(dx, dy + 5, r, (*shade, 190))
            for dx, dy, r in blobs:            # тело облака
                puff(dx, dy, r - 1, (*ccol, 240))
            for dx, dy, r in blobs:            # блики сверху
                puff(dx, dy - 5, r * 0.62, (*lite, 175))
            hit = self._put(key, (fast(s), ox, oy))
        return hit

    def draw_body(self, surf, col, kind):
        """Солнце, луна, планета и прочие светила."""
        _sync()
        if kind == "day":
            glow(surf, (720, 110), 200, (255, 238, 160), 60)
            glow(surf, (720, 110), 120, (255, 244, 196), 95)
            glow(surf, (720, 110), 72, (255, 250, 220), 140)
            D.circle(surf, (255, 236, 132), (720, 110), 38)
            D.circle(surf, (255, 246, 190), (718, 108), 30)
            D.circle(surf, (255, 252, 230), (712, 101), 15)
        elif kind == "sunset":
            for k in range(5):                       # дымка у горизонта
                D.rect(surf, lerp_c(col["bot"], (255, 208, 148), 0.28), (0, 332 + k * 13, GW, 5 - k))
            glow(surf, (620, 330), 300, (255, 170, 90), 95)
            glow(surf, (620, 330), 150, (255, 205, 130), 115)
            D.circle(surf, (255, 198, 112), (620, 330), 72)
            D.circle(surf, (255, 226, 158), (614, 322), 56)
            D.circle(surf, (255, 244, 200), (606, 310), 28)
        elif kind == "night":
            glow(surf, (730, 100), 150, (200, 210, 255), 55)
            D.circle(surf, (240, 243, 253), (730, 100), 30)
            D.circle(surf, (246, 248, 255), (722, 88), 16)          # освещённый бок
            D.circle(surf, (208, 214, 234), (722, 92), 5)           # кратеры
            D.circle(surf, (200, 206, 228), (740, 108), 7)
            D.circle(surf, (196, 202, 224), (734, 86), 4)
            D.circle(surf, (200, 206, 228), (714, 110), 3)
            D.circle(surf, (188, 194, 218), (744, 96), 3)
        elif kind == "neon":
            glow(surf, (700, 250), 300, (255, 60, 160), 90)
            D.circle(surf, (255, 92, 160), (700, 250), 88)
            D.circle(surf, (255, 152, 194), (694, 244), 68)
            D.circle(surf, (255, 206, 228), (686, 236), 36)
            for k in range(6):                       # полосы вечернего города
                D.rect(surf, col["near"], (612, 256 + k * 12, 176, 2 + k))
        elif kind == "desert":
            glow(surf, (720, 150), 260, (255, 200, 100), 100)
            glow(surf, (720, 150), 140, (255, 226, 150), 120)
            D.circle(surf, (255, 214, 104), (720, 150), 56)
            D.circle(surf, (255, 236, 160), (713, 143), 38)
            D.circle(surf, (255, 248, 208), (706, 136), 18)
        elif kind == "lava":
            D.polygon(surf, col["near"], [(430, PLAT_TOP), (590, 190), (670, 190), (830, PLAT_TOP)])
            D.polygon(surf, lerp_c(col["near"], (255, 120, 40), 0.16),
                      [(590, 190), (670, 190), (706, 300), (556, 300)])
            for sxx in (600, 626, 648):              # потоки лавы по склону
                D.polygon(surf, (255, 130, 40), [(sxx, 200), (sxx + 6, 200),
                                                 (sxx + (sxx - 630) * 0.35, 300), (sxx - 5 + (sxx - 630) * 0.35, 300)])
            glow(surf, (630, 190), 200, (255, 100, 30), 140)
            D.ellipse(surf, (255, 120, 34), (590, 181, 80, 18))
            D.ellipse(surf, (255, 196, 90), (604, 184, 52, 10))
            D.ellipse(surf, (255, 246, 200), (616, 186, 28, 5))
        elif kind == "space":
            glow(surf, (700, 170), 210, (160, 120, 255), 60)
            D.circle(surf, (128, 96, 206), (700, 170), 64)
            D.circle(surf, (158, 126, 232), (690, 158), 50)
            for k in range(4):                       # полосы атмосферы
                D.ellipse(surf, (176, 148, 240), (648, 150 + k * 14, 104, 6))
            D.ellipse(surf, (214, 196, 255), (602, 150, 196, 42), 3)
            D.circle(surf, (192, 192, 216), (260, 150), 17)
            D.circle(surf, (166, 166, 194), (254, 145), 5)
            D.circle(surf, (206, 206, 228), (265, 157), 4)
        elif kind == "finale":
            pulse = 0.5 + 0.5 * math.sin(self.t * 2)
            glow(surf, (700, 170), 260, (255, 60, 200), int(70 + 60 * pulse))
            glow(surf, (700, 170), 130, (255, 140, 230), int(60 + 40 * pulse))
            D.ellipse(surf, (255, 130, 220), (596, 158, 208, 26), 2)
            D.circle(surf, (8, 0, 14), (700, 170), 56)
            D.circle(surf, (255, 200, 240), (700, 170), 56, 3)
            D.circle(surf, (255, 120, 220), (700, 170), 64 + int(4 * pulse), 1)
            D.circle(surf, (255, 236, 250), (700, 170), 68 + int(3 * pulse), 1)

    # --- полосы с домами: рисуются один раз и просто едут по экрану ---
    def strip(self, which, col, kind):
        _sync()
        key = self._ck(col, ("strip", which, kind))
        hit = self.cache.get(key)
        if hit is not None:
            return hit
        light = col["light"]
        span = {"far2": self.far2_span, "far": self.far_span, "near": self.near_span}[which]
        s = pygame.Surface((px(span), px(STRIP_H)))
        s.fill(KEYCOL)
        if which == "far2":
            # самый дальний слой: бледные силуэты с разнообразными крышами
            pale = lerp_c(col["far"], col["bot"], 0.55)
            roof = lerp_c(pale, (0, 0, 0), 0.12)
            for (x, w, h) in self.far2:
                top = STRIP_H - h
                D.rect(s, pale, (x, top, w, h))
                D.rect(s, roof, (x, top, w, 3))
                D.rect(s, roof, (x + w - 4, top, 4, h))
                style = (int(x) // 40) % 3
                if style == 0:                    # надстройка
                    D.rect(s, pale, (x + w * 0.28, top - 12, w * 0.36, 12))
                    D.rect(s, roof, (x + w * 0.28, top - 12, w * 0.36, 2))
                elif style == 1:                  # антенна
                    D.line(s, roof, (x + w * 0.7, top), (x + w * 0.7, top - 26), 1)
                    D.line(s, roof, (x + w * 0.7 - 5, top - 20), (x + w * 0.7 + 5, top - 20), 1)
                    D.line(s, roof, (x + w * 0.7 - 3, top - 26), (x + w * 0.7 + 3, top - 26), 1)
                else:                             # трубa
                    D.rect(s, roof, (x + w * 0.6, top - 14, 7, 14))
        elif which == "far":
            far = col["far"]
            hi = lerp_c(far, (255, 255, 255), 0.20)
            dark = lerp_c(far, (0, 0, 0), 0.20)
            glass = lerp_c(far, col["bot"], 0.30)
            for (x, w, h) in self.far:
                top = STRIP_H - h
                D.rect(s, far, (x, top, w, h))
                D.rect(s, dark, (x, top, 3, h))            # тень слева
                D.rect(s, lerp_c(dark, (0, 0, 0), 0.25), (x + w - 4, top, 4, h))
                D.rect(s, hi, (x, top, w, 2))              # карниз
                style = (int(x) // 30) % 4
                if style == 0:                              # двускатная крыша
                    D.polygon(s, dark, [(x - 4, top), (x + w / 2, top - 18), (x + w + 4, top)])
                    D.line(s, hi, (x - 4, top), (x + w / 2, top - 18), 1)
                elif style == 1:                            # водонапорный бак
                    D.rect(s, dark, (x + w * 0.55, top - 16, 16, 12), border_radius=3)
                    D.line(s, dark, (x + w * 0.55 + 3, top - 4), (x + w * 0.55 + 3, top), 1)
                    D.line(s, dark, (x + w * 0.55 + 13, top - 4), (x + w * 0.55 + 13, top), 1)
                elif style == 2:
                    D.rect(s, lerp_c(far, (0, 0, 0), 0.10), (x + w * 0.3, top - 10, w * 0.34, 10))
                    D.line(s, dark, (x + w * 0.62, top - 10), (x + w * 0.62, top - 26), 1)
                # окна: редкие, тусклые
                for r in range(max(0, (h - 12) // 26)):
                    for c in range(max(0, (w - 10) // 20)):
                        if (r * 7 + c * 5 + int(x)) % 5 == 0:
                            wy = top + 9 + r * 26
                            D.rect(s, dark, (x + 5 + c * 20, wy, 8, 11))
                            D.rect(s, glass, (x + 6 + c * 20, wy + 1, 6, 9))
        else:
            # ближний слой: полноценные фасады с окнами, балконами и витринами
            body = col["near"]
            body_hi = lerp_c(body, (255, 255, 255), 0.14)
            body_lo = lerp_c(body, (0, 0, 0), 0.26)
            edge = lerp_c(body, (0, 0, 0), 0.42)
            for (x, w, h, seed) in self.near:
                top = STRIP_H - h
                brnd = random.Random(seed)
                # корпус с градиентом и подсветкой краёв
                vband(s, x, x + w, top, STRIP_H,
                      lerp_c(body, (255, 255, 255), 0.10), lerp_c(body, (0, 0, 0), 0.16))
                D.rect(s, body_hi, (x, top, 3, h))
                D.rect(s, body_lo, (x + w - 5, top, 5, h))
                # цоколь и карниз
                D.rect(s, edge, (x, STRIP_H - 6, w, 6))
                D.rect(s, body_hi, (x, top, w, 4))
                D.rect(s, edge, (x, top + 4, w, 1))
                # крыша: парапет, бак, антенна, вентиляция
                style = brnd.randint(0, 2)
                if style == 0:
                    D.rect(s, body_hi, (x + 6, top - 7, w - 12, 7))
                    D.rect(s, edge, (x + 6, top - 7, w - 12, 1))
                elif style == 1:
                    D.rect(s, lerp_c(body, (0, 0, 0), 0.12), (x + w * 0.55, top - 22, 18, 16), border_radius=4)
                    D.rect(s, body_hi, (x + w * 0.55 + 2, top - 20, 5, 12), border_radius=2)
                    D.line(s, edge, (x + w * 0.55 + 3, top - 6), (x + w * 0.55 + 3, top), 2)
                    D.line(s, edge, (x + w * 0.55 + 15, top - 6), (x + w * 0.55 + 15, top), 2)
                else:
                    D.rect(s, lerp_c(body, (0, 0, 0), 0.08), (x + 10, top - 12, 22, 12), border_radius=2)
                    D.line(s, edge, (x + w * 0.75, top), (x + w * 0.75, top - 30), 1)
                    D.line(s, edge, (x + w * 0.75 - 6, top - 24), (x + w * 0.75 + 6, top - 24), 1)
                if kind == "neon":
                    D.rect(s, (255, 60, 200), (x, top, w, h), 2)
                if kind == "finale":
                    D.rect(s, (200, 80, 220), (x, top, w, h), 1)

                # окна: решётка с рамами, подоконниками и редкими балконами
                cols = max(1, (w - 12) // 20)
                rows = max(1, (h - 62) // 26)
                glass_bg = lerp_c(body, (0, 0, 0), 0.40)
                sx = x + (w - cols * 20) // 2 + 4
                for r in range(rows):
                    for c in range(cols):
                        wx = sx + c * 20
                        wy = top + 12 + r * 26
                        if wy + 14 > STRIP_H - 46:
                            continue
                        hsh = (seed + r * 31 + c * 17) % 7
                        D.rect(s, edge, (wx - 1, wy - 1, 12, 15))       # ниша рамы
                        D.rect(s, glass_bg, (wx, wy, 10, 13))
                        lit = light > 0.4 and hsh < 3
                        if lit:
                            if kind == "neon":
                                wc = (0, 230, 230) if hsh == 0 else (255, 90, 200)
                            elif kind == "lava":
                                wc = (255, 120, 40)
                            elif kind == "space":
                                wc = (140, 220, 255)
                            elif kind == "finale":
                                wc = (255, 120, 220) if hsh == 0 else (255, 255, 255)
                            else:
                                wc = (255, 215, 120)
                            D.rect(s, wc, (wx, wy, 10, 13))
                            D.rect(s, lerp_c(wc, (255, 255, 255), 0.35), (wx, wy, 10, 4))
                            if hsh == 0:                                  # шторы
                                D.rect(s, lerp_c(wc, (0, 0, 0), 0.18), (wx + 7, wy + 2, 3, 11))
                        D.line(s, lerp_c(body, (0, 0, 0), 0.5), (wx + 5, wy), (wx + 5, wy + 13), 1)
                        D.line(s, body_hi, (wx - 2, wy + 14), (wx + 12, wy + 14), 2)   # подоконник
                        if hsh == 5:                                     # балкон
                            D.rect(s, body_lo, (wx - 3, wy + 16, 16, 3))
                            for k in range(4):
                                D.line(s, lerp_c(body_hi, (255, 255, 255), 0.2),
                                       (wx - 2 + k * 4, wy + 9), (wx - 2 + k * 4, wy + 16), 1)

                # первый этаж: витрины, дверь и козырёк
                fy = STRIP_H - 46
                D.rect(s, lerp_c(body, (0, 0, 0), 0.30), (x + 4, fy, w - 8, 40))
                for k in range(max(1, (w - 16) // 26)):
                    gx = x + 8 + k * 26
                    D.rect(s, lerp_c(body, (255, 255, 255), 0.05), (gx, fy + 4, 20, 30))
                    D.rect(s, lerp_c(body, (255, 255, 255), 0.16), (gx + 2, fy + 6, 16, 12))
                    D.line(s, edge, (gx + 10, fy + 6), (gx + 10, fy + 34), 1)
                if w > 90 and brnd.random() < 0.6:      # полосатый козырёк
                    acol = (210, 70, 70) if brnd.random() < 0.5 else (70, 130, 190)
                    for k in range((w - 10) // 10):
                        D.rect(s, acol if k % 2 else lerp_c(acol, (255, 255, 255), 0.6),
                               (x + 5 + k * 10, fy - 7, 9, 7))
                    D.line(s, edge, (x + 5, fy - 1), (x + w - 5, fy - 1), 1)
                # вывеска над витриной
                if w > 70:
                    sign_w = min(w - 16, 44)
                    sxx = x + (w - sign_w) // 2
                    D.rect(s, lerp_c(body, (0, 0, 0), 0.45), (sxx, fy - 20, sign_w, 11), border_radius=2)
                    scol = (255, 210, 120) if kind != "neon" else (0, 240, 230)
                    D.rect(s, scol, (sxx + 3, fy - 18, sign_w - 12, 7), border_radius=1)
                    D.rect(s, lerp_c(scol, (255, 255, 255), 0.4), (sxx + 3, fy - 18, sign_w - 12, 2), border_radius=1)
        s = fast(s, False)
        s.set_colorkey(KEYCOL)
        return self._put(key, (s, span))

    def blit_strip(self, surf, which, col, kind, speed):
        _sync()
        s, span = self.strip(which, col, kind)
        bx = -((self.t * speed) % span) - 150
        y = px(PLAT_TOP - STRIP_H)
        surf.blit(s, (px(bx), y))
        if bx + span < GW:
            surf.blit(s, (px(bx + span), y))

    # --- платформа, пути и всё, что лежит ниже горизонта: тоже один раз ---
    def ground(self, col):
        _sync()
        key = self._ck(col, ("ground",))
        s = self.cache.get(key)
        if s is not None:
            return s
        light = col["light"]
        s = pygame.Surface((GWP, HP))
        s.fill((0, 0, 0))
        # платформа: градиент, швы плитки, фаска
        rnd = random.Random(11)
        plate = col["plat"]
        top_c = lerp_c(plate, (255, 255, 255), 0.12)
        bot_c = lerp_c(plate, (0, 0, 0), 0.18)
        seam = lerp_c(plate, (0, 0, 0), 0.26)

        # --- плиты платформы: каждая со своей фасонной кромкой и потёртостями ---
        vband(s, 0, GW, PLAT_TOP, PLAT_BOT, top_c, bot_c)
        row_h = 34
        for row, yy in enumerate(range(PLAT_TOP, PLAT_BOT - 9, row_h)):
            off = (row % 2) * 40
            h = min(row_h, PLAT_BOT - 9 - yy)
            if h <= 0:
                continue
            for x in range(-80 + off, GW + 80, 80):
                tone = rnd.uniform(-0.055, 0.06)
                c = lerp_c(plate, (255, 255, 255) if tone > 0 else (0, 0, 0), abs(tone) + 0.03)
                D.rect(s, c, (x + 1, yy + 1, 78, h - 2), border_radius=2)
                D.line(s, lerp_c(c, (255, 255, 255), 0.30), (x + 3, yy + 2), (x + 76, yy + 2), 1)
                D.line(s, lerp_c(c, (255, 255, 255), 0.18), (x + 2, yy + 3), (x + 2, yy + h - 3), 1)
                D.line(s, seam, (x + 2, yy + h - 1), (x + 78, yy + h - 1), 1)
                D.line(s, seam, (x + 78, yy + 1), (x + 78, yy + h - 1), 1)
                if rnd.random() < 0.2:      # трещинка
                    cx0 = x + rnd.randint(10, 62)
                    cy0 = yy + rnd.randint(7, max(8, h - 8))
                    D.line(s, seam, (cx0, cy0), (cx0 + rnd.randint(-9, 9), cy0 + rnd.randint(3, 7)), 1)
                if rnd.random() < 0.14:     # тёмное пятно
                    D.ellipse(s, lerp_c(c, (0, 0, 0), 0.10),
                              (x + rnd.randint(6, 44), yy + rnd.randint(4, max(5, h - 10)), 20, 6))
        D.line(s, seam, (0, PLAT_TOP + 30), (GW, PLAT_TOP + 30), 1)
        # носок платформы: яркая кромка и тень под ней
        D.line(s, lerp_c(plate, (255, 255, 255), 0.45), (0, PLAT_TOP), (GW, PLAT_TOP), 3)
        D.line(s, lerp_c(plate, (0, 0, 0), 0.34), (0, PLAT_TOP + 3), (GW, PLAT_TOP + 3), 2)
        # решётки водоотвода у края
        for gx in range(120, GW, 240):
            D.rect(s, lerp_c(plate, (0, 0, 0), 0.34), (gx, PLAT_BOT - 23, 26, 13))
            for k in range(4):
                D.line(s, lerp_c(plate, (0, 0, 0), 0.62),
                       (gx + 3, PLAT_BOT - 20 + k * 3), (gx + 23, PLAT_BOT - 20 + k * 3), 1)

        # --- жёлтая полоса безопасности с косой штриховкой ---
        y0 = PLAT_BOT - 9
        D.rect(s, (232, 196, 28), (0, y0, GW, 9))
        for x in range(-20, GW + 20, 28):
            D.polygon(s, (58, 48, 8), [(x, PLAT_BOT), (x + 12, PLAT_BOT),
                                        (x + 18, y0), (x + 6, y0)])
        D.line(s, (255, 236, 120), (0, y0), (GW, y0), 1)
        D.line(s, (120, 96, 10), (0, PLAT_BOT - 1), (GW, PLAT_BOT - 1), 1)

        # --- стенка платформы: кирпичная кладка с расшивкой ---
        fw_top = lerp_c(col["front"], (255, 255, 255), 0.07)
        fw_bot = lerp_c(col["front"], (0, 0, 0), 0.32)
        vband(s, 0, GW, PLAT_BOT, TRAIN_Y, fw_top, fw_bot)
        mortar = lerp_c(col["front"], (0, 0, 0), 0.44)
        bw, bh = 24, 6
        for row, yy in enumerate(range(PLAT_BOT, TRAIN_Y, bh)):
            D.line(s, mortar, (0, yy), (GW, yy), 1)
            off = (row % 2) * (bw // 2)
            for x in range(-bw + off, GW, bw):
                if rnd.random() < 0.22:
                    D.rect(s, lerp_c(col["front"], (0, 0, 0), 0.16), (x + 1, yy + 1, bw - 2, bh - 2))
                D.line(s, mortar, (x, yy), (x, yy + bh), 1)

        # --- путевая зона: гравий, шпалы, рельсы ---
        bed_top = lerp_c(col["bed"], (0, 0, 0), 0.40)
        bed_bot = lerp_c(col["bed"], (0, 0, 0), 0.10)
        for py in range(px(TRAIN_Y), HP):
            t = min(1.0, (py / K - TRAIN_Y) / 60)
            s.fill(lerp_c(bed_top, bed_bot, t), (0, py, GWP, 1))
        # балласт: широкие полосы щебня, чтобы путь не выглядел пустым
        for _ in range(26):
            bx = rnd.randint(-20, GW)
            by = rnd.randint(TRAIN_Y + 8, H - 12)
            D.ellipse(s, lerp_c(col["bed"], (0, 0, 0), 0.22),
                      (bx, by, rnd.randint(60, 180), rnd.randint(8, 18)))
        # камешки: плотный ковёр из мелкого щебня
        for _ in range(1500):
            gx = rnd.randint(0, GW)
            gy = rnd.randint(TRAIN_Y + 2, H - 2)
            r = rnd.choice((1, 2, 2, 2, 3, 3))
            base = lerp_c(col["bed"], (255, 255, 255) if rnd.random() > 0.45 else (0, 0, 0),
                          rnd.uniform(0.05, 0.26))
            D.ellipse(s, lerp_c(base, (0, 0, 0), 0.30), (gx, gy + 1, r * 2, r))
            D.ellipse(s, base, (gx, gy, r * 2, r))
            D.ellipse(s, lerp_c(base, (255, 255, 255), 0.28), (gx + r // 2, gy, max(1, r), max(1, r // 2)))
        D.rect(s, lerp_c(col["bed"], (0, 0, 0), 0.30), (0, H - 80, GW, 80))
        # масляные пятна
        for _ in range(10):
            sx = rnd.randint(0, GW)
            D.ellipse(s, lerp_c(col["bed"], (0, 0, 0), 0.55),
                      (sx, rnd.choice((628, 634, 648)), rnd.randint(18, 44), 5))
        # шпалы: деревянные, с волокнами и болтами
        wood = lerp_c((132, 100, 66), (24, 20, 32), 0.55 * min(1.0, light))
        for x in range(-20, GW + 20, 52):
            D.rect(s, lerp_c(wood, (0, 0, 0), 0.55), (x + 3, 602, 31, 47), border_radius=3)
            D.rect(s, wood, (x, 598, 31, 46), border_radius=3)
            D.line(s, lerp_c(wood, (255, 255, 255), 0.22), (x + 2, 600), (x + 29, 600), 2)
            for k in range(3):
                D.line(s, lerp_c(wood, (0, 0, 0), 0.20), (x + 4, 607 + k * 12), (x + 27, 605 + k * 12), 1)
            for bx in (x + 7, x + 24):
                D.circle(s, lerp_c(wood, (0, 0, 0), 0.5), (bx, 612), 2)
                D.circle(s, lerp_c(wood, (255, 255, 255), 0.28), (bx, 611), 1)
        # рельсы: подкладка, шейка, блестящая головка
        for ry in (602, 636):
            D.rect(s, lerp_c(col["rail"], (0, 0, 0), 0.55), (0, ry - 2, GW, 10))
            D.rect(s, lerp_c(col["rail"], (0, 0, 0), 0.30), (0, ry, GW, 6))
            D.rect(s, col["rail"], (0, ry, GW, 4))
            D.line(s, lerp_c(col["rail"], (255, 255, 255), 0.62), (0, ry), (GW, ry), 1)
            D.line(s, lerp_c(col["rail"], (255, 255, 255), 0.30), (0, ry + 1), (GW, ry + 1), 1)
            for x in range(6, GW, 52):      # костыли
                D.rect(s, lerp_c(col["rail"], (0, 0, 0), 0.45), (x, ry + 4, 8, 4))
        return self._put(key, fast(s, False))

    def backdrop(self, col, kind):
        """Небо и земля одним слоем: собирается один раз на локацию.

        Раньше небо, дымка, платформа и пути перерисовывались каждый кадр
        десятками вызовов — на телефоне это и давало «подергивания».
        """
        _sync()
        key = self._ck(col, ("backdrop", kind))
        if self._back_key == key and self._back_surf is not None:
            return self._back_surf
        s = pygame.Surface((GWP, HP))
        s.fill((0, 0, 0))
        s.blit(self.sky(col, kind), (0, 0))
        gy = px(PLAT_TOP)
        s.blit(self.ground(col), (0, gy), (0, gy, GWP, HP - gy))
        self._back_key = key
        self._back_surf = fast(s, False)
        return self._back_surf

    def station(self, col, name):
        """Табличка станции и фонари — тоже статичный слой."""
        _sync()
        key = self._ck(col, ("station", name))
        if self._fg_key == key and self._fg_surf is not None:
            return self._fg_surf
        light = col["light"]
        tmp = pygame.Surface((GWP, HP), pygame.SRCALPHA)

        # --- табличка станции: металлический щит на фермах ---
        for p in (200, 410):
            D.rect(tmp, (36, 36, 46), (p - 4, 286, 8, PLAT_TOP - 286))
            D.rect(tmp, (96, 96, 116), (p - 4, 286, 2, PLAT_TOP - 286))
            D.rect(tmp, (22, 22, 30), (p - 8, PLAT_TOP - 10, 16, 10), border_radius=2)
        for hx, hx2 in ((205, 229), (405, 381)):
            D.line(tmp, (68, 68, 84), (hx, 241), (hx2, 251), 3)      # кронштейны
        if light > 0.4:
            glow(tmp, (305, 261), 170, (90, 150, 255), int(70 * light))
        D.rect(tmp, (8, 10, 18), (181, 235, 254, 54), border_radius=9)
        vband(tmp, 182, 432, 238, 286, (62, 110, 180), (16, 42, 88))
        D.rect(tmp, (255, 255, 255, 80), (183, 239, 242, 14), border_radius=5)
        D.rect(tmp, (10, 20, 44), (183, 281, 244, 3))
        D.rect(tmp, (235, 240, 250), (180, 236, 250, 50), 3, border_radius=8)
        for bx, by in ((189, 245), (421, 245), (189, 278), (421, 278)):
            D.circle(tmp, (146, 154, 174), (bx, by), 3)
            D.circle(tmp, (228, 234, 246), (bx - 1, by - 1), 1)
        for bx in (198, 412):
            D.circle(tmp, (255, 235, 150), (bx, 261), 2)
            D.circle(tmp, (255, 255, 220), (bx, 261), 1)
        text(tmp, f"Станция «{name}»", f_mid, (255, 255, 255), (305, 250),
             center=True, shadow=False)

        # --- фонари: чугунный столб с фонарём ---
        for lx in (110, 500, 850):
            if light > 0.25:
                cone = LAMP_CONE
                cone.set_alpha(int(255 * min(1.0, light)))
                tmp.blit(cone, (px(lx) - cone.get_width() // 2, px(282)))
            # база и столб
            D.rect(tmp, (30, 30, 40), (lx - 9, PLAT_TOP - 12, 18, 12), border_radius=3)
            D.rect(tmp, (56, 56, 70), (lx - 7, PLAT_TOP - 14, 14, 4), border_radius=2)
            D.rect(tmp, (40, 40, 52), (lx - 3, 270, 6, PLAT_TOP - 270))
            D.rect(tmp, (40, 40, 52), (lx - 5, 330, 10, PLAT_TOP - 330))
            D.rect(tmp, (84, 84, 102), (lx - 3, 272, 2, PLAT_TOP - 274))
            D.rect(tmp, (58, 58, 72), (lx - 8, 322, 16, 4), border_radius=2)     # кольцо
            # кронштейн и корпус фонаря
            D.rect(tmp, (40, 40, 52), (lx - 22, 262, 44, 7), border_radius=3)
            D.rect(tmp, (76, 76, 92), (lx - 22, 262, 44, 2), border_radius=2)
            D.polygon(tmp, (30, 30, 40), [(lx - 13, 266), (lx + 13, 266),
                                          (lx + 9, 284), (lx - 9, 284)])
            glass = lerp_c((122, 132, 152), (255, 232, 164), min(1.0, light))
            D.polygon(tmp, glass, [(lx - 11, 267), (lx + 11, 267),
                                   (lx + 7, 282), (lx - 7, 282)])
            D.line(tmp, (30, 30, 40), (lx, 267), (lx, 282), 1)
            D.rect(tmp, (24, 24, 32), (lx - 11, 283, 22, 3))
            D.circle(tmp, lerp_c((200, 200, 185), (255, 235, 160), light), (lx, 275), 4)
            if light > 0.25:
                glow(tmp, (lx, 278), 130, (255, 230, 150), int(110 * light))

        # обрезаем прозрачные поля: blit-ить 220 пикселей дешевле, чем 720
        top = px(236)
        crop = pygame.Surface((GWP, HP - top), pygame.SRCALPHA)
        crop.blit(tmp, (0, 0), (0, top, GWP, HP - top))
        self._fg_key = key
        self._fg_surf = fast(crop)
        return self._fg_surf

    def draw_back(self, surf, col, kind, name):
        _sync()
        surf.blit(self.backdrop(col, kind), (0, 0))

        if kind in STAR_KINDS:
            sz = max(1, int(K))
            for (x, y, ph) in self.stars:
                v = int(150 + 100 * math.sin(self.t * 2 + ph))
                v = max(0, min(255, v))
                surf.fill((v, v, v), (px(x), px(y), sz, sz))
                if v > 220:
                    glow(surf, (x, y), 6, (200, 210, 255), 90)
        if kind == "finale":
            self.draw_body(surf, col, kind)

        for (x, y, sc, _sp) in self.clouds:
            spr, ox, oy = self.cloud(sc, col["cloud"])
            surf.blit(spr, (px(x - ox), px(y - oy)))

        self.blit_strip(surf, "far2", col, kind, 3)
        self.blit_strip(surf, "far", col, kind, 6)
        self.blit_strip(surf, "near", col, kind, 14)

        # дымка у горизонта
        surf.blit(self.haze(col), (0, px(PLAT_TOP - 150)))

        # табличка и фонари поверх домов (готовая картинка, не пересобирается)
        surf.blit(self.station(col, name), (0, px(236)))

    def draw_front(self, surf, kind):
        _sync()
        if kind == "snow":
            for i, (x, y, _s, _d, r) in enumerate(self.snow):
                D.circle(surf, (255, 255, 255), (int(x), int(y)), r)
                if r > 3 and not (WEB and i % 2):
                    D.circle(surf, (225, 236, 250), (int(x) + 1, int(y) + 1), r - 1)
        elif kind == "lava":
            for i, (x, y, _s, _d, r) in enumerate(self.snow):
                if not WEB or i % 3 == 0:      # в браузере свечение — через одну искру
                    glow(surf, (x, y), r * 4, (255, 120, 40), 90)
                D.circle(surf, (255, 190, 80), (int(x), int(y)), max(1, r - 1))
        elif kind == "rain":
            for (x, y, _s) in self.rain:
                D.line(surf, (175, 195, 220), (int(x), int(y)), (int(x) - 4, int(y) + 14), 1)
                if PLAT_BOT - 22 < y < PLAT_BOT - 14:     # всплеск на платформе
                    D.ellipse(surf, (200, 215, 235), (int(x) - 4, int(y) + 6, 8, 3), 1)
            if self.flash > 0:
                fs = self.flash_surface()
                fs.set_alpha(int(150 * self.flash))
                surf.blit(fs, (0, 0))
