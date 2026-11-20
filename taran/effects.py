# -*- coding: utf-8 -*-
"""Короткоживущие эффекты «ТАРАН-ЭКСПРЕСС».

Частицы, всплывающий текст, отклик на тап, монеты, пятна крови, летящий
череп и кислота босса. Каждый объект знает, как обновиться и нарисоваться,
но не знает про игровое состояние — им управляет game.py.

Динамические помощники рисования приходят через bind(game_module), как в
progression.py, taran/world.py и taran/ui/shop.py.
"""
import math
import random

import pygame

from taran.config import GW, H, PLAT_TOP, W

G = None

_SYNC = (
    "D", "px", "f_mid", "glow", "lerp", "lerp_c", "fast", "new_surf", "text",
    "_text_img", "_ol", "blit_c", "SKULL_IMGS", "RED_FLASH",
)


def bind(game_module):
    """Запоминает модуль игры (шрифты, масштаб, помощники рисования)."""
    global G
    G = game_module


def _sync():
    """Подтягивает актуальные значения из game.py перед созданием/отрисовкой."""
    if G is None:
        return
    m = globals()
    for name in _SYNC:
        m[name] = getattr(G, name)


class Effect:
    def __init__(self, x, y, txt, color=(255, 255, 255)):
        _sync()
        self.x, self.y, self.t, self.txt, self.color = x, y, 0.9, txt, color
        # копия текста делается один раз: каждый кадр ей просто меняем альфу
        self.img = _text_img(txt, f_mid, color, True).copy()
        self.o = _ol()
        self.bw = self.img.get_width() - 2 * self.o

    def update(self, dt):
        self.t -= dt

    def draw(self, surf):
        _sync()
        age = 0.9 - self.t
        self.img.set_alpha(255 if self.t > 0.3 else max(0, int(255 * self.t / 0.3)))
        surf.blit(self.img, (px(self.x) - self.bw // 2 - self.o,
                             px(self.y - 110 - age * 50) - self.o))


class TapFX:
    """Отклик на тап: волна, вспышка и искры (как в хороших кликерах).

    Живёт треть секунды. Картинка маленькая и рисуется в собственный
    alpha-слой, поэтому не зависит от цвета фона под курсором.
    """

    W = 132                     # логический размер слоя

    def __init__(self, x, y, color=(255, 244, 200), power=1.0):
        _sync()
        self.x, self.y = float(x), float(y)
        self.color = color
        self.power = float(power)
        self.t = self.max = 0.32
        self.img = fast(new_surf(self.W, self.W))
        self.c = self.W // 2
        self.rays = [(random.uniform(0, math.tau), random.uniform(0.75, 1.2))
                     for _ in range(6)]

    def update(self, dt):
        self.t -= dt

    def draw(self, surf):
        _sync()
        k = 1.0 - max(0.0, self.t) / self.max          # 0 → 1
        fade = max(0.0, self.t / self.max)             # 1 → 0
        c = self.c
        img = self.img
        img.fill((0, 0, 0, 0))
        col = self.color
        r1 = 9 + (38 * self.power) * k
        D.circle(img, (col[0], col[1], col[2], int(200 * fade)), (c, c), r1, 2)
        if k < 0.7:
            a2 = int(120 * (1.0 - k / 0.7))
            D.circle(img, (col[0], col[1], col[2], a2), (c, c), r1 * 0.6, 2)
        for ang, ln in self.rays:
            r0 = 7 + 22 * k
            r1b = r0 + (9 + 20 * ln) * fade
            a = int(210 * fade * fade)
            D.line(img, (col[0], col[1], col[2], a),
                   (c + math.cos(ang) * r0, c + math.sin(ang) * r0),
                   (c + math.cos(ang) * r1b, c + math.sin(ang) * r1b), 2)
        # мягкая вспышка и ядро
        glow(surf, (self.x, self.y), 30 + 24 * self.power * k, col, int(105 * fade))
        D.circle(surf, lerp_c(col, (255, 255, 255), 0.6),
                 (int(self.x), int(self.y)), max(1, 5.5 * fade * self.power))
        surf.blit(img, (px(self.x - self.W // 2), px(self.y - self.W // 2)))


class Particle:
    def __init__(self, x, y, color):
        _sync()
        a = random.uniform(0, math.tau)
        sp = random.uniform(80, 260)
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(a) * sp, math.sin(a) * sp - 150
        self.life = self.max = random.uniform(0.5, 1.0)
        self.color = color
        self.hi = lerp_c(color, (255, 255, 255), 0.5)   # блик считаем один раз
        self.size = random.randint(3, 6)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 600 * dt
        self.life -= dt

    def draw(self, surf):
        _sync()
        r = max(1, int(self.size * self.life / self.max))
        D.circle(surf, self.color, (int(self.x), int(self.y)), r)
        if r > 2:
            D.circle(surf, self.hi, (int(self.x) - 1, int(self.y) - 1), max(1, r // 2))


class Coin:
    """Золотая монета падает с неба и подпрыгивает на платформе — кликни, пока не исчезла."""

    def __init__(self):
        _sync()
        self.x = random.uniform(90, GW - 90)
        self.y = -20.0
        self.vy = 0.0
        self.t = 8.0
        self.floor = random.uniform(PLAT_TOP + 20, PLAT_TOP + 55)
        self.spin = random.uniform(0, 6)

    def update(self, dt):
        self.t -= dt
        self.spin += dt * 6
        self.vy += 900 * dt
        self.y += self.vy * dt
        if self.y >= self.floor:
            self.y = self.floor
            self.vy = -self.vy * 0.55 if abs(self.vy) > 140 else 0.0

    def draw(self, surf):
        _sync()
        if self.t < 2.0 and int(self.t * 8) % 2 == 0:
            return                              # мигает перед исчезновением
        x, y = int(self.x), int(self.y)
        wob = abs(math.cos(self.spin))          # монета вращается
        rw = max(3, int(17 * (0.35 + 0.65 * wob)))
        glow(surf, (x, y), 52, (255, 215, 60), 110)
        D.ellipse(surf, (200, 150, 20), (x - rw - 1, y - 18, rw * 2 + 2, 36))
        D.ellipse(surf, (255, 205, 40), (x - rw, y - 17, rw * 2, 34))
        D.ellipse(surf, (255, 240, 150), (x - rw + 3, y - 13, max(2, rw - 2), 12))
        if wob > 0.6:
            text(surf, "$", f_mid, (160, 105, 10), (x, y - 11), center=True, shadow=False)


class Decal:
    """Пятно крови на путях: остаётся на несколько секунд и медленно тает."""

    def __init__(self, x, y, big=False):
        _sync()
        self.max = self.t = random.uniform(6.0, 10.0)
        w = random.randint(36, 62) if big else random.randint(22, 42)
        h = max(8, int(w * 0.45))
        s = new_surf(w, h)
        for _ in range(random.randint(4, 7)):
            rw = random.randint(max(6, w // 3), max(7, w * 2 // 3))
            rh = random.randint(max(4, h // 3), max(5, h * 2 // 3))
            D.ellipse(s, (135 + random.randint(0, 45), 12, 16, random.randint(130, 205)),
                      (random.randint(0, max(0, w - rw)), random.randint(0, max(0, h - rh)), rw, rh))
        for _ in range(4):                      # брызги вокруг пятна
            D.circle(s, (120, 10, 14, random.randint(80, 150)),
                     (random.randint(1, w - 2), random.randint(1, h - 2)),
                     random.randint(2, 5))
        self.surf = fast(s)
        self.x, self.y = x - w // 2, y - h // 2

    def update(self, dt):
        self.t -= dt

    def draw(self, surf):
        _sync()
        k = max(0.0, self.t / self.max)
        self.surf.set_alpha(255 if k > 0.35 else int(255 * k / 0.35))
        surf.blit(self.surf, (px(self.x), px(self.y)))


class SkullFly:
    """Череп летит в камеру: от маленькой точки до всего экрана, щёлкает челюстью."""

    def __init__(self, x, y):
        _sync()
        self.x, self.y = float(x), float(y)
        self.t = 0.0
        self.dur = 1.1
        self.rot = 0.0
        self.spin = random.uniform(-220, 220)

    def update(self, dt):
        self.t += dt
        # вращение гасится, чтобы к концу череп смотрел «в лицо»
        self.rot += self.spin * dt * max(0.0, 1.0 - self.t / self.dur)

    def draw(self, surf):
        _sync()
        k = min(1.0, self.t / self.dur)
        size = max(8, int(96 * (0.4 + 4.6 * k * k)))
        base = SKULL_IMGS[int(self.t * 16) % 2]
        spx = max(8, px(size))
        img = pygame.transform.smoothscale(base, (spx, spx))
        if k > 0.8:
            img.set_alpha(max(0, int(255 * (1 - (k - 0.8) / 0.2))))
        if abs(self.rot) > 1:
            img = pygame.transform.rotate(img, self.rot)
        cx = lerp(self.x, W * 0.5, k)
        cy = lerp(self.y, H * 0.48, k)
        # дрожь, нарастающая к концу
        if k > 0.3:
            amp = int(2 + 8 * k)
            cx += random.randint(-amp, amp)
            cy += random.randint(-amp, amp)
        if 0.45 < k < 1.0:                     # красная вспышка по всему экрану
            fa = int(110 * math.sin((k - 0.45) / 0.55 * math.pi))
            if fa > 0:
                RED_FLASH.set_alpha(fa)
                surf.blit(RED_FLASH, (0, 0))
        pulse = 0.5 + 0.5 * math.sin(self.t * 30)
        glow(surf, (cx, cy), min(size * 0.95, 280), (255, 30, 30), int(60 + 40 * pulse) // 20 * 20)
        blit_c(surf, img, cx, cy)


class Acid:
    """Плевок босса летит по дуге в камеру и заливает экран зелёным."""

    def __init__(self, x, y):
        _sync()
        self.x0, self.y0 = float(x), float(y)
        self.tx = random.uniform(W * 0.28, W * 0.78)
        self.ty = random.uniform(H * 0.35, H * 0.72)
        self.t = 0.0
        self.dur = random.uniform(1.0, 1.35)
        self.done = False

    def update(self, dt):
        self.t = min(self.dur, self.t + dt)
        if self.t >= self.dur:
            self.done = True

    def _pt(self, k):
        return (lerp(self.x0, self.tx, k),
                lerp(self.y0, self.ty, k) - math.sin(k * math.pi) * 150)

    def draw(self, surf):
        _sync()
        k = self.t / self.dur
        x, y = self._pt(k)
        r = 10 + 18 * k
        glow(surf, (x, y), r * 2.6, (120, 255, 60), 80)
        for i in range(4):                     # шлейф из капель
            tx, ty = self._pt(max(0.0, k - 0.06 * (i + 1)))
            D.circle(surf, (150 - i * 22, 240 - i * 34, 44),
                               (int(tx), int(ty)), max(2, int(r * (1 - 0.2 * i))))
        D.circle(surf, (210, 255, 130), (int(x), int(y)), max(3, int(r * 0.55)))
