# -*- coding: utf-8 -*-
"""Рисование HUD, «Депо» и атмосферных эффектов.

Модуль получает ссылку на game через progression.G, поэтому не импортирует
game.py и не создаёт циклических зависимостей. Палитра общая — из
taran.ui.theme, чтобы HUD, магазин и Депо выглядели одной системой.
"""
import math

import pygame

import progression as P
from taran.config import GW
from taran.ui.theme import (
    UI_BLUE, UI_DIM, UI_GOLD, UI_GREEN, UI_LINE, UI_MUTED, UI_RED, UI_SURFACE,
    UI_TEXT, UI_VIOLET,
)

G = None

# --------------------------------------------------------------------------
# общие мелочи
# --------------------------------------------------------------------------
C_GOOD = UI_GREEN
C_GOLD = UI_GOLD
C_BLUE = UI_BLUE
C_VIOLET = UI_VIOLET
C_BAD = UI_RED
C_TEXT = UI_TEXT
C_DIM = UI_DIM
C_MUTED = UI_MUTED
C_SURFACE = UI_SURFACE
C_LINE = UI_LINE

# кнопка «Депо»: во второй строке правого блока HUD, рядом со звуком
DEPOT_BTN = pygame.Rect(694, 56, 160, 28)
# три внутренние зоны HUD: касса / рейс / прогресс
HUD_LEFT = pygame.Rect(14, 12, 290, 80)
HUD_CENTER = pygame.Rect(310, 12, 366, 80)
HUD_RIGHT = pygame.Rect(682, 12, 258, 80)
# Депо почти на весь экран: HUD, подсказки и магазин не просвечивают по краям.
PANEL_RECT = pygame.Rect(6, 6, 1268, 708)
RAIL_RECT = pygame.Rect(24, 116, 258, 548)
CONTENT_RECT = pygame.Rect(300, 116, 948, 548)
CLOSE_RECT = pygame.Rect(1096, 42, 150, 34)
REBIRTH_RECT = pygame.Rect(40, 266, 226, 92)
FOOT_RECT = pygame.Rect(24, 672, 1224, 36)
NAV_Y = 372
NAV_H = 46


def _bind():
    global G
    G = P.G


def _diamond(surf, x, y, r, col, edge=None):
    pts = [(x, y - r), (x + r, y), (x, y + r), (x - r, y)]
    G.D.polygon(surf, edge or tuple(max(0, c - 60) for c in col), pts)
    G.D.polygon(surf, col, [(x, y - r + 2), (x + r - 2, y), (x, y + r - 2), (x - r + 2, y)])
    G.D.line(surf, (255, 255, 255), (x, y - r + 4), (x + 3, y - 3), 1)


def _button(surf, r, label, hot=False, on=True, col=C_BLUE, small=None):
    """Кнопка: тонированная заливка в цвет акцента, без тяжёлых обводок."""
    if not on:
        bg, edge, fg = (30, 34, 48), (54, 62, 84), (140, 150, 176)
    else:
        bg = G.lerp_c((22, 26, 38), col, 0.34 if hot else 0.26)
        edge = G.lerp_c(col, (255, 255, 255), 0.16)
        fg = (255, 255, 255)
    G.D.rect(surf, bg, r, border_radius=9)
    G.D.rect(surf, edge, r, 1, border_radius=9)
    f = small or G.f_mid
    G.text(surf, label, f, fg, (r.centerx, r.y + (r.h - f.get_height() / G.K) // 2),
           center=True, shadow=False)


def _bar(surf, r, frac, col, bg=(20, 23, 35)):
    G.ui_bar(surf, r, frac, col, bg)


def _chip(surf, x, y, w, h, label, value, col, dim=False):
    G.D.rect(surf, (22, 25, 37), (x, y, w, h), border_radius=9)
    G.D.rect(surf, C_LINE if not dim else (38, 44, 60), (x, y, w, h), 1, border_radius=9)
    G.text(surf, label, G.f_small, C_MUTED,
           (x + 10, y + 4), shadow=False)
    G.text(surf, value, G.f_mid, col if not dim else (140, 148, 176),
           (x + 10, y + 18), shadow=False)


def _toast(g, text, col=(255, 235, 120)):
    if g is None:
        return
    g["toast"] = text
    g["toast_col"] = col
    g["toast_t"] = 2.8


_HEART = {}


def draw_heart(surf, x, y, r, filled):
    """Сердечко-жизнь в хардкоре: пустое — уже потрачено.

    Рисуется один раз на размер и состояние, затем просто блитится: в хардкоре
    сердечки нужны каждый кадр, а три фигуры на каждое — лишняя работа.
    Картинка строится с запасом и уменьшается smoothscale — края гладкие.
    """
    _bind()
    rp = max(2, int(round(r * G.K)))
    key = (rp, bool(filled))
    img = _HEART.get(key)
    if img is None:
        ss = 3
        size = rp * 3
        sp = size * ss
        s = pygame.Surface((sp, sp), pygame.SRCALPHA)
        cx, cy, rr = rp * 1.5 * ss, rp * 1.4 * ss, rp * ss
        col = (245, 74, 86) if filled else (60, 46, 56)
        pygame.draw.circle(s, col, (int(cx - rr * 0.5), int(cy - rr * 0.3)), int(rr * 0.62))
        pygame.draw.circle(s, col, (int(cx + rr * 0.5), int(cy - rr * 0.3)), int(rr * 0.62))
        pygame.draw.polygon(s, col, [(int(cx - rr * 1.05), int(cy)),
                                     (int(cx + rr * 1.05), int(cy)),
                                     (int(cx), int(cy + rr * 1.3))])
        if filled:
            pygame.draw.circle(s, (255, 176, 180),
                               (int(cx - rr * 0.55), int(cy - rr * 0.55)),
                               max(1, int(rr * 0.2)))
        img = G.fast(pygame.transform.smoothscale(s, (size, size)))
        _HEART[key] = img
    surf.blit(img, (G.px(x) - int(rp * 1.5), G.px(y) - int(rp * 1.4)))


# кнопка звука: в правом верхнем углу HUD, рядом с экранной паузой на телефоне.
# Радиус 18 и отступ 40 от края — палец должен попадать в неё без прицела,
# а на телефонах с закруглёнными углами кнопка не уезжает под скругление.
MUTE_BTN = (GW - 40, 69, 18)
BUTTON_HIT_PAD = 10                 # запас вокруг кнопки для тапа (≈ 56 логических px)


def mute_hit(mx, my):
    return math.hypot(mx - MUTE_BTN[0], my - MUTE_BTN[1]) <= MUTE_BTN[2] + BUTTON_HIT_PAD


def draw_mute_button(surf, muted, hot=False):
    _bind()
    x, y, r = MUTE_BTN
    k = r / 15.0
    G.D.circle(surf, (18, 21, 32), (x, y), r + 2)
    G.D.circle(surf, (128, 170, 240) if hot else (66, 76, 104), (x, y), r + 2, 2)
    G.D.circle(surf, (34, 40, 58) if hot else (27, 31, 45), (x, y), r)
    col = (255, 120, 110) if muted else (226, 236, 252)
    # корпус динамика и звуковые волны (размеры масштабируются вместе с кнопкой)
    G.D.polygon(surf, col, [(x - 7 * k, y - 3 * k), (x - 3 * k, y - 3 * k), (x + 2 * k, y - 8 * k),
                            (x + 2 * k, y + 8 * k), (x - 3 * k, y + 3 * k), (x - 7 * k, y + 3 * k)])
    if muted:
        G.D.line(surf, (255, 90, 85), (x + 3 * k, y - 7 * k), (x + 10 * k, y + 7 * k), 3)
        G.D.line(surf, (255, 90, 85), (x + 10 * k, y - 7 * k), (x + 3 * k, y + 7 * k), 3)
    else:
        G.D.arc(surf, col, (x, y - 5 * k, 14 * k, 10 * k), -1.0, 1.0, 2)
        G.D.arc(surf, col, (x + 2 * k, y - 9 * k, 19 * k, 18 * k), -1.0, 1.0, 2)


def draw_boss_bar(surf, b, top=96):
    """Полоса здоровья босса — под верхним HUD, чтобы не спорить с деньгами."""
    _bind()
    w, x0 = 420, G.GW // 2 - 210
    tags = list(getattr(b, "tags", None)
                or [n for k, n in G.ABILITY_TAGS if k in getattr(b, "flags", ())])
    rows = [tags[i:i + 3] for i in range(0, len(tags), 3)]
    G.plate(surf, (x0 - 14, top, w + 28, 70 + 16 * max(0, len(rows) - 1)), 178, 14,
            border=(255, 120, 100, 100))
    if getattr(b, "secret", False):
        G.text(surf, f"СЕКРЕТ: {b.name}", G.f_mid, (255, 215, 70), (G.GW // 2, top + 5), center=True)
    else:
        G.text(surf, f"БОСС: {b.name}", G.f_mid, (255, 130, 110), (G.GW // 2, top + 5), center=True)
    G.D.rect(surf, (18, 18, 28), (x0, top + 30, w, 15), border_radius=8)
    if b.hp > 0:
        fw = max(2, int(w * b.hp / b.max_hp))
        G.D.rect(surf, (200, 40, 50), (x0, top + 30, fw, 15), border_radius=8)
        G.D.rect(surf, (245, 90, 90), (x0, top + 30, fw, 7), border_radius=6)
        G.D.rect(surf, (255, 170, 160), (x0 + 3, top + 32, max(1, fw - 6), 2), border_radius=1)
    for q in (1, 2, 3):
        G.D.line(surf, (18, 18, 28), (x0 + w * q // 4, top + 30),
                 (x0 + w * q // 4, top + 44), 2)
    G.D.rect(surf, (255, 255, 255), (x0, top + 30, w, 15), 2, border_radius=8)
    if b.state == "fight":
        info = f"{int(b.hp)}/{int(b.max_hp)}  •  осталось {int(b.time_left)} с"
    else:
        info = "Босс сброшен на пути — жди поезд!"
    G.text(surf, info, G.f_small, (255, 255, 255), (G.GW // 2, top + 49), center=True)
    for i, row in enumerate(rows):
        G.text(surf, " • ".join(row), G.f_small, (150, 235, 110), (G.GW // 2, top + 65 + 16 * i),
               center=True, shadow=False)


# --------------------------------------------------------------------------
# HUD
# --------------------------------------------------------------------------
def depot_hit(mx, my):
    # небольшой запас вокруг кнопки: на телефоне палец не всегда попадает точно
    return DEPOT_BTN.inflate(10, 6).collidepoint(mx, my)


def draw_hud(canvas, s, g, mouse, name, hard):
    """Верхняя панель: касса слева, рейс в центре, прогресс справа.

    Корпус один, но внутри три мягкие зоны с собственным акцентом. Так глаз
    сразу находит нужный блок, а подписи и цифры стоят ровной сеткой.
    """
    _bind()
    m = P.ensure(s)
    md = P.mod(s)
    now = pygame.time.get_ticks() / 1000.0

    # ---- корпус и внутренние зоны ----
    G.plate(canvas, (8, 6, 944, 92), 224, 18, border=(62, 72, 100, 150))
    G.D.rect(canvas, md["color"], (8, 7, 944, 2), border_radius=1)
    for zr, accent in ((HUD_LEFT, (255, 202, 46)),
                       (HUD_CENTER, md["color"]),
                       (HUD_RIGHT, (166, 136, 255))):
        G.plate(canvas, zr, 120, 12, border=(58, 66, 92, 90))
        G.D.rect(canvas, accent, (zr.x + 12, zr.y, zr.w - 24, 2), border_radius=1)

    # ---- касса ----
    G.glow(canvas, (42, 40), 28, (255, 205, 70), 70)
    G.D.circle(canvas, (255, 202, 46), (42, 40), 18)
    G.D.circle(canvas, (186, 136, 18), (42, 40), 18, 2)
    G.text(canvas, "$", G.f_small, (120, 82, 8), (42, 33), center=True, shadow=False)
    money = G.fmt(s["money"])
    fm = G.f_money
    if G.twidth(fm, money) > 198:
        fm = G.f_mid
    G.text(canvas, money, fm, (255, 255, 255), (70, 16), shadow=False)
    rate = g.get("rate_show", 0.0) if g else 0.0
    rides = f"Поездок: {G.fmt(s['kills'])}"
    G.text(canvas, rides, G.f_small, C_DIM, (70, 64), shadow=False)
    wr = G.twidth(G.f_small, rides)
    if rate >= 1:
        G.text(canvas, f"  ·  +${G.fmt(int(rate))}/с", G.f_small, C_GOOD,
               (70 + wr, 64), shadow=False)
    else:
        G.text(canvas, "  ·  пассажиры платят", G.f_small, (128, 146, 172),
               (70 + wr, 64), shadow=False)

    # ---- рейс и прогресс ----
    x0 = 322
    G.text(canvas, f"РЕЙС {m['reborn'] + 1}  ·  {md['name'].upper()}", G.f_small,
           md["color"], (x0, 17), shadow=False)
    fname = G.f_mid
    if G.twidth(fname, name) > 344:
        fname = G.f_small
    G.text(canvas, name, fname, (255, 255, 255), (x0, 33), shadow=False)

    if hard:
        lives_max = P.start_lives(s)
        pill = pygame.Rect(x0, 64, 78, 19)
        G.D.rect(canvas, (54, 28, 34), pill, border_radius=7)
        G.D.rect(canvas, (128, 52, 58), pill, 1, border_radius=7)
        G.text(canvas, "ХАРДКОР", G.f_small, C_BAD,
               (pill.centerx, pill.y + 2), center=True, shadow=False)
        for i in range(lives_max):
            draw_heart(canvas, x0 + 94 + i * 21, 74, 8, i < g["lives"])
        tt = G.fmt_time(g["hard_t"])
        tw = max(44, int(G.twidth(G.f_small, tt)) + 22)
        tr = pygame.Rect(HUD_CENTER.right - 12 - tw, 64, tw, 19)
        G.D.rect(canvas, (22, 25, 37), tr, border_radius=7)
        G.D.rect(canvas, C_LINE, tr, 1, border_radius=7)
        G.text(canvas, tt, G.f_small, (255, 255, 255),
               (tr.centerx, tr.y + 2), center=True, shadow=False)
    else:
        lo = G.THEMES[s["level"]]["kills"]
        hi = G.boss_at(s["level"])
        frac = max(0.0, min(1.0, (s["kills"] - lo) / max(1, hi - lo)))
        seg_n, seg_h = 20, 8
        seg_w = (344 - (seg_n - 1) * 2) / seg_n
        track = pygame.Rect(x0 - 2, 58, 348, 12)
        G.D.rect(canvas, (15, 18, 28), track, border_radius=6)
        G.D.rect(canvas, (44, 50, 68), track, 1, border_radius=6)
        for i in range(seg_n):
            sx = x0 + i * (seg_w + 2)
            passed = i < s["level"]
            cur = i == s["level"]
            c = (100, 172, 255) if passed else ((255, 208, 112) if cur else (36, 42, 58))
            G.D.rect(canvas, (28, 33, 47), (sx, 60, int(seg_w), seg_h), border_radius=2)
            if passed or (cur and frac > 0):
                fw = int(seg_w) if passed else max(2, int(seg_w * frac))
                G.D.rect(canvas, c, (sx, 60, fw, seg_h), border_radius=2)
        left = hi - s["kills"]
        G.text(canvas, f"{G.fmt(s['kills'])} / {G.fmt(hi)} поездок", G.f_small,
               C_DIM, (x0, 72), shadow=False)
        msg = "БОСС НА ПЛАТФОРМЕ" if g["boss"] else (
            "БОСС ИДЁТ!" if left <= 0 else f"до босса {G.fmt(left)}")
        col = C_BAD if g["boss"] else C_GOLD
        G.text(canvas, msg, G.f_small, col,
               (HUD_CENTER.right - 12 - G.twidth(G.f_small, msg), 72), shadow=False)

    # ---- мета-прогресс: три равные колонки, подписи и числа по центру ----
    ach = f"{P.ach_count(s)}/{len(P.ACHIEVEMENTS)}"
    stats = (("ЧЕРТЕЖИ", str(m["bp"]), C_GOLD),
             ("РАНГ", str(m["reborn"]), (255, 255, 255)),
             ("ДОСТИЖ.", ach, (200, 212, 240)))
    col_w = (HUD_RIGHT.w - 24) / 3
    for i, (label, value, col) in enumerate(stats):
        cx = HUD_RIGHT.x + 12 + int(col_w * (i + 0.5))
        G.text(canvas, label, G.f_small, C_MUTED, (cx, 15), center=True, shadow=False)
        G.text(canvas, value, G.f_mid, col, (cx, 28), center=True, shadow=False)

    ready = P.can_rebirth(s) and not P.has_pending_relic(s)
    hot = depot_hit(*mouse) if mouse else False
    if ready:
        pulse = 90 + int(70 * (0.5 + 0.5 * math.sin(now * 4.5)))
        G.glow(canvas, (DEPOT_BTN.centerx, DEPOT_BTN.centery), 54, C_GOLD, pulse)
        label, col = "ДЕПО · ГОТОВО", C_GOLD
    elif P.has_pending_relic(s):
        label, col = "ДЕПО · НАГРАДА", C_GOLD
    else:
        label, col = "ДЕПО  P", C_BLUE
    _button(canvas, DEPOT_BTN, label, hot, True, col, small=G.f_small)


# --------------------------------------------------------------------------
# атмосфера: лучи, сияние, пыль, искры
# --------------------------------------------------------------------------
_ATM = {}


def _atm_surface(kind, key):
    k = (G.K, key)
    surf = _ATM.get(k)
    if surf is not None:
        return surf
    w, h = G.GW, 420
    surf = G.new_surf(w, h)
    if key == "rays":
        for i in range(5):
            x = 80 + i * 190
            pts = [(x, 0), (x + 34, 0), (x + 260, h), (x + 150, h)]
            G.D.polygon(surf, (255, 240, 190, 22 - i * 2), pts)
        for i in range(3):
            x = 40 + i * 300
            G.D.polygon(surf, (255, 255, 255, 10), [(x, 0), (x + 12, 0),
                                                   (x + 120, h), (x + 80, h)])
    elif key == "aurora":
        cols = ((70, 255, 190, 40), (90, 170, 255, 34), (190, 120, 255, 30))
        for i, c in enumerate(cols):
            G.D.ellipse(surf, c, (20 + i * 40, 40 + i * 34, w - 80, 92))
            G.D.ellipse(surf, (c[0], c[1], c[2], c[3] // 2),
                        (90 + i * 60, 70 + i * 30, w - 260, 70))
    elif key == "nebula":
        for i, c in enumerate(((120, 80, 220, 22), (40, 120, 220, 18),
                               (220, 70, 160, 14))):
            G.D.ellipse(surf, c, (40 + i * 90, 30 + i * 50, w - 120, 150))
    _ATM[k] = G.fast(surf)
    _ATM[k].set_alpha(255)
    return _ATM[k]


def draw_atmosphere(surf, col, kind, t, rush=False):
    _bind()
    img = None
    if kind in ("day", "sunset", "desert"):
        img = _atm_surface(kind, "rays")
    elif kind in ("night", "snow", "finale"):
        img = _atm_surface(kind, "aurora")
    elif kind == "space":
        img = _atm_surface(kind, "nebula")
    if img is not None:
        try:
            img.set_alpha(120 if kind in ("day", "desert") else 150)
        except Exception:
            pass
        ox = int(18 * math.sin(t * 0.15))
        surf.blit(img, (G.px(ox), G.px(24)))
        try:
            img.set_alpha(255)
        except Exception:
            pass

    # пыль/искры: позиции считаются синусами, без random в кадре
    n = 12 if G.WEB else 20
    for i in range(n):
        px_ = (i * 173 + t * (12 + (i % 5) * 6)) % G.GW
        py_ = 60 + (i * 97 + 18 * math.sin(t * 0.7 + i)) % 330
        a = 40 + (i % 4) * 18
        c = (255, 240, 190) if kind in ("day", "sunset", "desert") else (170, 220, 255)
        G.glow(surf, (px_, py_), 5, c, a)

    if rush:
        for i in range(8):
            y = 80 + i * 55
            x = int((t * 640 + i * 137) % (G.GW + 200)) - 160
            G.D.line(surf, (255, 210, 140), (x, y), (x + 70, y), 1)


# --------------------------------------------------------------------------
# Депо: геометрия
# --------------------------------------------------------------------------
def _nav_rects():
    return [pygame.Rect(40, NAV_Y + i * (NAV_H + 8), 226, NAV_H) for i in range(4)]


def _tree_rects():
    out = []
    for b in range(3):
        x = CONTENT_RECT.x + b * 320
        for i, u in enumerate(P.META_BY_BRANCH[b]):
            out.append((u["key"], pygame.Rect(x, 206 + i * 49, 308, 45)))
    return out


def _relic_choice_rects(s):
    out = []
    for i, key in enumerate(P.ensure(s).get("relic_choices", [])[:3]):
        out.append((key, pygame.Rect(CONTENT_RECT.x + i * 319, 190, 309, 158)))
    return out


def _relic_owned_rects(s):
    out = []
    keys = list(P.ensure(s).get("relics", {}).keys())
    # при незабранной награде сверху стоят три больших карточки — сетка ниже
    start = 350 if P.has_pending_relic(s) else 282
    for i, key in enumerate(keys[:12]):
        r = pygame.Rect(CONTENT_RECT.x + (i % 4) * 239,
                        start + (i // 4) * 104, 231, 96)
        out.append((key, r))
    return out


def _contract_rects():
    return [pygame.Rect(CONTENT_RECT.x, 170 + i * 128, CONTENT_RECT.w, 116)
            for i in range(3)]


def _ach_rects():
    return [pygame.Rect(CONTENT_RECT.x + (i // 12) * 480,
                        170 + (i % 12) * 40, 468, 36)
            for i in range(len(P.ACHIEVEMENTS))]


_KIND_COL = {"push": (110, 190, 255), "boss": (255, 120, 108),
             "earn": (255, 214, 110), "coins": (126, 236, 162),
             "station": (190, 150, 255), "combo": (255, 170, 100)}


def _footer(canvas, s, g, tab):
    """Нижняя строка Депо: сводка по вкладке и общий прогресс.

    Раньше низ панели пустовал, а полезные цифры были разбросаны по экрану.
    """
    m = P.ensure(s)
    G.plate(canvas, FOOT_RECT, 150, 10, border=(58, 66, 92, 120))
    G.D.rect(canvas, (48, 54, 76), (FOOT_RECT.x, FOOT_RECT.y + 6, 1, FOOT_RECT.h - 12))
    tree_total = sum(m.get("tree", {}).values())
    tree_max = sum(u["maxl"] for u in P.META_UPGRADES)
    relic_lv = sum(P.relic_lvl(s, k) for k in m.get("relics", {}))
    relic_max = len(P.RELICS) * P.RELIC_MAX
    done_c = sum(1 for c in m["contracts"] if c.get("done"))
    ready_bp = sum(int(c.get("reward", 0)) for c in m["contracts"] if c.get("done"))
    ach_n, ach_max = P.ach_count(s), len(P.ACHIEVEMENTS)
    if tab == 0:
        col = C_BLUE
        line = (f"УРОВНЕЙ ДЕПО: {tree_total}/{tree_max}   ·   ЧЕРТЕЖЕЙ: {m['bp']}"
                f"   ·   РАНГ: {m['reborn']}")
        frac, right = tree_total / max(1, tree_max), f"{tree_total}/{tree_max}"
    elif tab == 1:
        col = C_GOLD
        if P.has_pending_relic(s):
            line = "НЕЗАБРАННАЯ НАГРАДА: выберите реликвию в списке выше"
        else:
            line = (f"СОБРАНО: {len(m['relics'])}/{len(P.RELICS)}   ·   "
                    f"СУММА УРОВНЕЙ: {relic_lv}/{relic_max}")
        frac, right = relic_lv / max(1, relic_max), f"{len(m['relics'])}/{len(P.RELICS)}"
    elif tab == 2:
        col = C_GOOD
        line = (f"ГОТОВО К СДАЧЕ: {done_c}/3   ·   НАГРАДА: {ready_bp} ЧТ"
                f"   ·   после награды выдаётся новый контракт")
        frac, right = done_c / 3.0, f"{done_c}/3"
    else:
        col = C_GOLD
        line = (f"ОТКРЫТО: {ach_n}/{ach_max}   ·   БОНУС К ДОХОДУ: "
                f"+{ach_n * 0.5:.1f}%   ·   каждое достижение даёт +1 ЧТ")
        frac, right = ach_n / max(1, ach_max), f"{ach_n}/{ach_max}"
    br = pygame.Rect(FOOT_RECT.right - 238, FOOT_RECT.y + 11, 210, 14)
    G.text(canvas, G.ellipsize(G.f_small, line, br.x - FOOT_RECT.x - 32),
           G.f_small, (206, 216, 240), (FOOT_RECT.x + 14, FOOT_RECT.y + 9),
           shadow=False)
    _bar(canvas, br, frac, col, bg=(18, 21, 34))
    G.text(canvas, right, G.f_small, col, (br.right + 10, FOOT_RECT.y + 8),
           shadow=False)


# --------------------------------------------------------------------------
# Депо: отрисовка
# --------------------------------------------------------------------------
def draw_depot(canvas, s, g, mouse):
    _bind()
    m = P.ensure(s)
    now = pygame.time.get_ticks() / 1000.0
    if getattr(G, "PAUSE_DIM", None):
        canvas.blit(G.PAUSE_DIM, (0, 0))
    G.plate(canvas, PANEL_RECT, 252, 20, border=(64, 74, 102, 160))
    G.D.rect(canvas, (74, 118, 198), (18, 30, 1244, 2), border_radius=1)

    # ---- шапка ----
    G.text(canvas, "ДЕПО МАШИНИСТА", G.f_big, (255, 255, 255), (36, 38), shadow=False)
    G.text(canvas, "ПОСТОЯННОЕ НАСЛЕДИЕ · РЕЙС ЗА РЕЙСОМ", G.f_small,
           (140, 176, 232), (38, 84), shadow=False)
    G.D.rect(canvas, (48, 54, 76), (872, 36, 1, 60))
    _diamond(canvas, 896, 56, 12, C_GOLD)
    G.text(canvas, "ЧЕРТЕЖИ", G.f_small, C_MUTED, (916, 38), shadow=False)
    G.text(canvas, str(m["bp"]), G.f_money, C_GOLD, (914, 52), shadow=False)
    hot = CLOSE_RECT.collidepoint(*mouse) if mouse else False
    G.D.rect(canvas, (38, 44, 62) if hot else (28, 32, 46), CLOSE_RECT, border_radius=9)
    G.D.rect(canvas, (76, 92, 128) if hot else C_LINE, CLOSE_RECT, 1, border_radius=9)
    G.text(canvas, "ЗАКРЫТЬ  P", G.f_small, C_TEXT,
           (CLOSE_RECT.centerx, CLOSE_RECT.y + 9), center=True, shadow=False)

    # ---- левая колонка ----
    G.plate(canvas, RAIL_RECT, 150, 14, border=(76, 88, 124, 120))
    G.text(canvas, "РАНГ МАШИНИСТА", G.f_small, C_MUTED, (40, 128), shadow=False)
    G.text(canvas, str(m["reborn"]), G.f_big, C_GOLD, (40, 144), shadow=False)
    G.text(canvas, f"рейсов: {m['runs']}   ·   лучшая: {m['best']}/20",
           G.f_small, (196, 208, 236), (40, 198), shadow=False)
    tree_total = sum(m.get("tree", {}).values())
    G.text(canvas, f"уровней депо: {tree_total}   ·   реликвий: {len(m['relics'])}",
           G.f_small, C_DIM, (40, 218), shadow=False)

    # перерождение
    rr = REBIRTH_RECT
    can = P.can_rebirth(s)
    pending = P.has_pending_relic(s)
    if can and not pending:
        pulse = 90 + int(70 * (0.5 + 0.5 * math.sin(now * 4.0)))
        G.glow(canvas, (rr.centerx, rr.centery), 74, C_GOLD, pulse)
    G.card(canvas, rr, (54, 46, 30) if can else (38, 42, 58),
           (250, 208, 110) if can else (70, 78, 104),
           C_GOLD if can else None)
    G.text(canvas, "ПЕРЕРОЖДЕНИЕ", G.f_small, C_GOLD if can else C_DIM,
           (rr.x + 12, rr.y + 8), shadow=False)
    if pending:
        G.text(canvas, "сначала реликвия", G.f_mid, C_GOLD,
               (rr.x + 12, rr.y + 25), shadow=False)
    else:
        rew = P.bp_reward(s) if can else 0
        G.text(canvas, f"+{rew} ЧТ" if can else "нужна станция 10", G.f_mid,
               (255, 255, 255) if can else (150, 156, 180),
               (rr.x + 12, rr.y + 25), shadow=False)
    btn = pygame.Rect(rr.x + 10, rr.y + 56, rr.w - 20, 26)
    armed = pygame.time.get_ticks() < g.get("depot_confirm", 0)
    label = "ТОЧНО НАЧАТЬ?" if armed else ("НАЧАТЬ РЕЙС" if can else "ЗАКРЫТО")
    if pending:
        label = "ВЫБРАТЬ РЕЛИКВИЮ"
    _button(canvas, btn, label, btn.collidepoint(*mouse) if mouse else False,
            can or pending, C_GOLD, small=G.f_small)

    # навигация
    names = ("НАСЛЕДИЕ", "РЕЛИКВИИ", "КОНТРАКТЫ", "ДОСТИЖЕНИЯ")
    subs = ("дерево бонусов", f"{len(m['relics'])}/12 собрано",
            f"{sum(1 for c in m['contracts'] if c.get('done'))} готово",
            f"{P.ach_count(s)}/24 открыто")
    for i, r in enumerate(_nav_rects()):
        active = g.get("depot_tab", 0) == i
        hot = r.collidepoint(*mouse) if mouse else False
        if active:
            G.D.rect(canvas, (34, 48, 74), r, border_radius=11)
            G.D.rect(canvas, (104, 160, 255), (r.x, r.y + 9, 3, r.h - 18), border_radius=2)
            edge = (86, 128, 200)
        else:
            G.D.rect(canvas, (26, 30, 43) if not hot else (34, 39, 56), r, border_radius=11)
            edge = (44, 50, 70)
        G.D.rect(canvas, edge, r, 1, border_radius=11)
        G.ui_key(canvas, r.x + 9, r.y + 12, str(i + 1))
        G.text(canvas, names[i], G.f_small, C_TEXT if active else (178, 188, 214),
               (r.x + 40, r.y + 7), shadow=False)
        G.text(canvas, G.ellipsize(G.f_small, subs[i], r.w - 48),
               G.f_small, (160, 176, 208) if active else (122, 132, 158),
               (r.x + 40, r.y + 25), shadow=False)

    G.text(canvas, "P — Депо   ·   1–4 разделы",
           G.f_small, C_MUTED, (40, 630), shadow=False)
    G.text(canvas, "Офлайн-доход: %d%% · до %d ч" % (int(P.offline_rate(s) * 100),
                                                     P.offline_cap_h(s)),
           G.f_small, (140, 160, 196), (40, 648), shadow=False)

    # ---- контент ----
    tab = g.get("depot_tab", 0)
    if tab == 0:
        _draw_tree(canvas, s, g, mouse, now)
    elif tab == 1:
        _draw_relics(canvas, s, g, mouse)
    elif tab == 2:
        _draw_contracts(canvas, s, g, mouse)
    else:
        _draw_ach(canvas, s, g, mouse)
    _footer(canvas, s, g, tab)


def _draw_tree(canvas, s, g, mouse, now):
    m = P.ensure(s)
    heads = ("НАСЛЕДИЕ: ДЕРЕВО БОНУСОВ", "Вкладывай чертежи в три ветки")
    G.text(canvas, heads[0], G.f_mid, C_TEXT, (CONTENT_RECT.x, 122), shadow=False)
    G.text(canvas, heads[1], G.f_small, C_DIM, (CONTENT_RECT.x, 146), shadow=False)
    for b, br in enumerate(P.BRANCHES):
        x = CONTENT_RECT.x + b * 320
        hdr = pygame.Rect(x, 170, 308, 36)
        G.D.rect(canvas, br["dark"], hdr, border_radius=10)
        G.D.rect(canvas, (44, 50, 68), hdr, 1, border_radius=10)
        G.D.rect(canvas, br["color"], (hdr.x + 1, hdr.y + 9, 3, hdr.h - 18), border_radius=2)
        G.text(canvas, br["name"], G.f_mid, (255, 255, 255), (x + 12, hdr.y + 4), shadow=False)
        sub = f"{br['sub']} · ур. {P.branch_lvl(s, b)}"
        G.text(canvas, G.ellipsize(G.f_small, sub, 160), G.f_small, br["color"],
               (x + 138, hdr.y + 9), shadow=False)
    for key, r in _tree_rects():
        u = P.META_BY_KEY[key]
        lvl = P.tree_lvl(s, key)
        maxed = lvl >= u["maxl"]
        locked = m["reborn"] < u["req"]
        hot = r.collidepoint(*mouse) if mouse else False
        can = P.can_buy_meta(s, key)
        if locked:
            bg, edge, accent = (23, 26, 38), (40, 46, 64), None
        elif maxed:
            bg, edge, accent = (34, 31, 22), (150, 124, 58), C_GOLD
        elif can:
            bg, edge, accent = (28, 38, 36) if not hot else (34, 46, 43), (44, 106, 74), C_GOOD
        else:
            bg, edge, accent = (29, 33, 47) if not hot else (34, 39, 55), C_LINE, None
        G.card(canvas, r, bg, edge, accent, radius=10)
        bc = (32, 76, 54) if can else ((54, 46, 28) if maxed else (26, 30, 43))
        G.ui_badge(canvas, r.x + 8, r.y + 9, 28, 28, str(lvl), bc,
                   C_GOOD if can else ((C_GOLD if maxed else (190, 198, 224))),
                   edge, radius=8)
        nm = G.ellipsize(G.f_small, u["name"], 168)
        G.text(canvas, nm, G.f_small, (255, 255, 255) if not locked else (116, 124, 148),
               (r.x + 42, r.y + 3), shadow=False)
        cost = "МАКС" if maxed else f"ЧТ {P.tree_cost(u, lvl)}"
        cr = pygame.Rect(r.right - 62, r.y + 4, 54, 18)
        if maxed:
            G.D.rect(canvas, (54, 46, 28), cr, border_radius=7)
            col, ced = C_GOLD, (150, 124, 58)
        elif can:
            G.D.rect(canvas, (32, 88, 58), cr, border_radius=7)
            col, ced = (214, 255, 226), (110, 210, 150)
        else:
            G.D.rect(canvas, (30, 34, 48), cr, border_radius=7)
            col, ced = (140, 150, 178), (54, 62, 84)
        G.D.rect(canvas, ced, cr, 1, border_radius=7)
        G.text(canvas, cost, G.f_small, col, (cr.centerx, cr.y + 2),
               center=True, shadow=False)
        if locked:
            G.text(canvas, f"нужен ранг {u['req']}", G.f_small, (140, 148, 176),
                   (r.x + 42, r.y + 21), shadow=False)
        else:
            cur = u["v"](lvl)
            nxt = "" if maxed else f" → {u['v'](lvl + 1)}"
            line = f"{u['desc']}: {cur}{nxt}"
            G.text(canvas, G.ellipsize(G.f_small, line, r.w - 52), G.f_small,
                   (198, 208, 234), (r.x + 42, r.y + 21), shadow=False)


def _draw_relics(canvas, s, g, mouse):
    m = P.ensure(s)
    G.text(canvas, "РЕЛИКВИИ", G.f_mid, (255, 255, 255), (CONTENT_RECT.x, 122), shadow=False)
    G.text(canvas, "Выпадают после перерождения. Каждый уровень усиливает эффект.",
           G.f_small, C_DIM, (CONTENT_RECT.x, 146), shadow=False)
    cnt = f"{len(m['relics'])}/{len(P.RELICS)}"
    G.text(canvas, cnt, G.f_small, C_GOLD,
           (CONTENT_RECT.right - G.twidth(G.f_small, cnt), 146), shadow=False)
    choices = m.get("relic_choices", [])
    if choices:
        G.text(canvas, "ВЫБЕРИТЕ НАГРАДУ ЗА РЕЙС", G.f_small, C_GOLD,
               (CONTENT_RECT.x, 168), shadow=False)
        for key, r in _relic_choice_rects(s):
            rel = P.RELIC_BY_KEY[key]
            rar = P.RARITY[rel["rarity"]]
            hot = r.collidepoint(*mouse) if mouse else False
            G.card(canvas, r, (40, 42, 60) if not hot else (52, 54, 76),
                   rar["color"], rar["glow"])
            _diamond(canvas, r.x + 26, r.y + 30, 16, rar["color"])
            G.text(canvas, rel["name"], G.f_mid, (255, 255, 255), (r.x + 50, r.y + 10),
                   shadow=False)
            G.text(canvas, rar["name"].upper(), G.f_small, rar["color"],
                   (r.x + 50, r.y + 34), shadow=False)
            G.text(canvas, rel["desc"], G.f_small, (210, 220, 244),
                   (r.x + 14, r.y + 58), shadow=False)
            lvl = P.relic_lvl(s, key)
            G.text(canvas, f"у вас: ур. {lvl}/{P.RELIC_MAX}", G.f_small, (166, 178, 208),
                   (r.x + 14, r.y + 82), shadow=False)
            br = pygame.Rect(r.x + 14, r.y + 112, r.w - 28, 30)
            G.glow(canvas, (br.centerx, br.centery), 44, rar["glow"], 90 if hot else 55)
            _button(canvas, br, "ВЗЯТЬ", hot, True, rar["color"], small=G.f_mid)
    else:
        # вместо одинокой строки — карточка с готовностью к следующей награде
        cr = pygame.Rect(CONTENT_RECT.x, 190, CONTENT_RECT.w, 76)
        G.card(canvas, cr, (36, 40, 58), (72, 80, 108))
        G.text(canvas, "ВСЕ ДОСТУПНЫЕ РЕЛИКВИИ ВЫБРАНЫ", G.f_mid, C_GOLD,
               (cr.x + 18, cr.y + 10), shadow=False)
        G.text(canvas, "Следующая награда — после перерождения: пройдите 10 станций рейса.",
               G.f_small, (196, 206, 232), (cr.x + 18, cr.y + 38), shadow=False)
        prep = min(1.0, (s["level"] + 1) / 10.0)
        _bar(canvas, (cr.right - 250, cr.y + 52, 230, 12), prep,
             C_GOLD if prep >= 1 else C_BLUE)
        G.text(canvas, f"рейс: {min(10, s['level'] + 1)}/10", G.f_small,
               (176, 188, 216), (cr.right - 250, cr.y + 32), shadow=False)

    for key, r in _relic_owned_rects(s):
        rel = P.RELIC_BY_KEY[key]
        lvl = P.relic_lvl(s, key)
        rar = P.RARITY[rel["rarity"]]
        maxed = lvl >= P.RELIC_MAX
        G.card(canvas, r, (34, 38, 54), rar["color"], rar["glow"] if maxed else None)
        _diamond(canvas, r.x + 20, r.y + 20, 11, rar["color"])
        G.text(canvas, rel["name"], G.f_small, (255, 255, 255), (r.x + 38, r.y + 6),
               shadow=False)
        lv = "МАКС" if maxed else f"ур. {lvl}/{P.RELIC_MAX}"
        G.text(canvas, lv, G.f_small, rar["color"],
               (r.x + 12, r.y + 34), shadow=False)
        G.text(canvas, G.ellipsize(G.f_small, rel["desc"], r.w - 24), G.f_small,
               (196, 206, 232), (r.x + 12, r.y + 54), shadow=False)
        for i in range(P.RELIC_MAX):
            col = rar["color"] if i < lvl else (52, 58, 80)
            G.D.circle(canvas, col, (r.x + 20 + i * 14, r.y + 82), 4)


def _draw_contracts(canvas, s, g, mouse):
    m = P.ensure(s)
    G.text(canvas, "КОНТРАКТЫ", G.f_mid, (255, 255, 255), (CONTENT_RECT.x, 122), shadow=False)
    G.text(canvas, "Выполняйте цели рейса и забирайте чертежи. После награды выдаётся новый.",
           G.f_small, C_DIM, (CONTENT_RECT.x, 146), shadow=False)
    if not m.get("contracts"):
        G.plate(canvas, (CONTENT_RECT.x, 190, 700, 110), 120, 12,
                border=(70, 80, 110, 100))
        G.text(canvas, "КОНТРАКТЫ ОТКРОЮТСЯ ПОСЛЕ ПЕРВОГО ПЕРЕРОЖДЕНИЯ",
               G.f_mid, C_GOLD, (CONTENT_RECT.x + 24, 220), shadow=False)
        G.text(canvas, "Завершите 10 станций и нажмите «Перерождение».",
               G.f_small, (180, 192, 222), (CONTENT_RECT.x + 24, 252), shadow=False)
        return
    done_n = sum(1 for c in m["contracts"] if c.get("done"))
    G.text(canvas, f"готово к сдаче: {done_n}/3", G.f_small,
           C_GOLD if done_n else C_DIM,
           (CONTENT_RECT.right - G.twidth(G.f_small, f"готово к сдаче: {done_n}/3"), 146),
           shadow=False)
    for i, (c, r) in enumerate(zip(m["contracts"], _contract_rects())):
        info = P.CONTRACT_INFO.get(c["kind"], ("Контракт", c["kind"]))
        done = c.get("done")
        prog = int(c.get("progress", 0))
        target = max(1, int(c.get("target", 1)))
        kcol = _KIND_COL.get(c["kind"], C_BLUE)
        val = f"${G.fmt(prog)} / ${G.fmt(target)}" if c["kind"] == "earn" \
            else f"{prog} / {target}"
        G.card(canvas, r, (36, 33, 24) if done else (29, 33, 47),
               C_GOLD if done else C_LINE, C_GOLD if done else kcol)
        # левая колонка: название, прогресс и награда
        G.text(canvas, info[0], G.f_mid, (255, 255, 255), (r.x + 18, r.y + 12),
               shadow=False)
        G.text(canvas, val, G.f_small, (198, 210, 238), (r.x + 18, r.y + 40),
               shadow=False)
        G.text(canvas, f"награда: {c['reward']} ЧТ", G.f_small, C_GOLD,
               (r.x + 18, r.y + 60), shadow=False)
        # разделитель между описанием и прогрессом
        G.D.rect(canvas, (58, 64, 86), (r.x + 232, r.y + 14, 1, r.h - 28))
        pw = max(120, r.w - 430)
        _bar(canvas, (r.x + 250, r.y + 24, pw, 14), prog / target,
             C_GOLD if done else kcol)
        pct = f"{min(100, int(100 * prog / target))}%"
        G.text(canvas, pct, G.f_small, (208, 218, 242),
               (r.x + 250 + pw - G.twidth(G.f_small, pct), r.y + 42), shadow=False)
        G.text(canvas, "ГОТОВО — заберите награду" if done else "выполняется",
               G.f_small, C_GOLD if done else C_DIM, (r.x + 250, r.y + 44), shadow=False)
        br = pygame.Rect(r.right - 146, r.y + 42, 128, 32)
        hot = br.collidepoint(*mouse) if mouse else False
        if done:
            _button(canvas, br, "ЗАБРАТЬ", hot, True, C_GOLD, small=G.f_small)
        else:
            _button(canvas, br, "В РАБОТЕ", False, False, C_BLUE, small=G.f_small)

    # итоговая карточка: заполняет низ вкладки и показывает общую награду
    done_all = [c for c in m["contracts"] if c.get("done")]
    ready_bp = sum(int(c.get("reward", 0)) for c in done_all)
    sr = pygame.Rect(CONTENT_RECT.x, 556, CONTENT_RECT.w, 96)
    G.card(canvas, sr, (28, 32, 46), C_LINE)
    G.text(canvas, "ИТОГО ГОТОВО", G.f_small, C_DIM, (sr.x + 20, sr.y + 10),
           shadow=False)
    G.text(canvas, f"{done_n}/3", G.f_money, C_GOLD if done_n else (180, 190, 216),
           (sr.x + 20, sr.y + 30), shadow=False)
    G.text(canvas, f"К СДАЧЕ: {ready_bp} ЧТ", G.f_mid, C_GOLD,
           (sr.x + 220, sr.y + 18), shadow=False)
    G.text(canvas, "Сдайте готовый контракт — вместо него появится новый.",
           G.f_small, (186, 198, 226), (sr.x + 220, sr.y + 50), shadow=False)
    for i, c in enumerate(m["contracts"]):
        done = c.get("done")
        cr = pygame.Rect(sr.right - 258 + i * 82, sr.y + 34, 72, 30)
        G.D.rect(canvas, (58, 50, 30) if done else (30, 34, 50), cr, border_radius=8)
        G.D.rect(canvas, C_GOLD if done else (64, 72, 100), cr, 1, border_radius=8)
        if done:
            G.D.line(canvas, C_GOLD, (cr.centerx - 8, cr.centery),
                     (cr.centerx - 2, cr.centery + 6), 2)
            G.D.line(canvas, C_GOLD, (cr.centerx - 2, cr.centery + 6),
                     (cr.centerx + 9, cr.centery - 7), 2)
        else:
            G.text(canvas, str(i + 1), G.f_small, (150, 160, 190),
                   (cr.centerx, cr.y + 6), center=True, shadow=False)


def _draw_ach(canvas, s, g, mouse):
    m = P.ensure(s)
    got = m.get("ach", {})
    G.text(canvas, "ДОСТИЖЕНИЯ", G.f_mid, (255, 255, 255), (CONTENT_RECT.x, 122), shadow=False)
    total = len(P.ACHIEVEMENTS)
    G.text(canvas, f"Открыто {len(got)}/{total} · каждое даёт +0.5% доходу и +1 ЧТ",
           G.f_small, C_DIM, (CONTENT_RECT.x, 146), shadow=False)
    ab = pygame.Rect(CONTENT_RECT.x + 580, 142, CONTENT_RECT.w - 580 - 46, 10)
    _bar(canvas, ab, len(got) / max(1, total), C_GOLD)
    pct = f"{int(100 * len(got) / max(1, total))}%"
    G.text(canvas, pct, G.f_small, (255, 224, 130),
           (ab.right + 10, 138), shadow=False)
    for a, r in zip(P.ACHIEVEMENTS, _ach_rects()):
        ok = bool(got.get(a["key"]))
        hot = r.collidepoint(*mouse) if mouse else False
        G.D.rect(canvas, (44, 50, 66) if ok else ((34, 38, 52) if not hot else (40, 44, 60)),
                 r, border_radius=7)
        G.D.rect(canvas, C_GOLD if ok else (58, 64, 88), r, 1, border_radius=7)
        G.D.circle(canvas, C_GOLD if ok else (58, 62, 84),
                   (r.x + 16, r.centery), 7)
        if ok:
            G.D.line(canvas, (40, 34, 16), (r.x + 12, r.centery),
                     (r.x + 15, r.centery + 4), 2)
            G.D.line(canvas, (40, 34, 16), (r.x + 15, r.centery + 4),
                     (r.x + 21, r.centery - 5), 2)
        G.text(canvas, G.ellipsize(G.f_small, a["name"], r.w - 120),
               G.f_small, (255, 255, 255) if ok else (166, 174, 200),
               (r.x + 30, r.y + 3), shadow=False)
        G.text(canvas, G.ellipsize(G.f_small, a["desc"] if not ok else "получено",
                                   r.w - 120),
               G.f_small, (190, 200, 226) if ok else (126, 134, 158),
               (r.x + 30, r.y + 18), shadow=False)
        cr = pygame.Rect(r.right - 66, r.centery - 9, 56, 18)
        G.D.rect(canvas, (70, 58, 30) if ok else (40, 44, 62), cr, border_radius=6)
        G.D.rect(canvas, C_GOLD if ok else (66, 72, 96), cr, 1, border_radius=6)
        G.text(canvas, "+1 ЧТ", G.f_small, C_GOLD if ok else (150, 160, 190),
               (cr.centerx, cr.y + 1), center=True, shadow=False)


# --------------------------------------------------------------------------
# Депо: клики
# --------------------------------------------------------------------------
def depot_click(s, g, mx, my):
    _bind()
    m = P.ensure(s)
    if CLOSE_RECT.collidepoint(mx, my):
        g["depot"] = False
        G.SND.play("click", 0.7)
        return True
    for i, r in enumerate(_nav_rects()):
        if r.collidepoint(mx, my):
            g["depot_tab"] = i
            G.SND.play("click", 0.65)
            return True
    tab = g.get("depot_tab", 0)
    if tab == 0:
        for key, r in _tree_rects():
            if not r.collidepoint(mx, my):
                continue
            if P.can_buy_meta(s, key):
                u = P.META_BY_KEY[key]
                cost = P.tree_cost(u, P.tree_lvl(s, key))
                P.buy_meta(s, key)
                G.SND.play("buy", 0.8)
                _toast(g, f"{u['name']}: уровень {P.tree_lvl(s, key)}  (-{cost} ЧТ)",
                       C_GOOD)
            else:
                u = P.META_BY_KEY[key]
                if m["reborn"] < u["req"]:
                    _toast(g, f"Нужен ранг {u['req']}", C_BAD)
                elif P.tree_lvl(s, key) >= u["maxl"]:
                    _toast(g, "Уже максимум", C_GOLD)
                else:
                    _toast(g, f"Нужно {P.tree_cost(u, P.tree_lvl(s, key))} ЧТ", C_BAD)
            return True
        if REBIRTH_RECT.collidepoint(mx, my):
            if P.has_pending_relic(s):
                g["depot_tab"] = 1
                _toast(g, "Выберите реликвию за прошлый рейс", C_GOLD)
            elif not P.can_rebirth(s):
                _toast(g, "Перерождение доступно со станции 10", C_BAD)
            else:
                now = pygame.time.get_ticks()
                if now < g.get("depot_confirm", 0):
                    res = P.rebirth(s)
                    g["depot_confirm"] = 0
                    g["depot_tab"] = 1
                    G.SND.play("levelup", 0.95)
                    _toast(g, f"НОВЫЙ РЕЙС! +{res['reward']} ЧТ · {res['mod']}", C_GOLD)
                else:
                    g["depot_confirm"] = now + 3000
                    _toast(g, "Нажмите ещё раз, чтобы начать рейс заново", C_GOLD)
            return True
    elif tab == 1:
        for key, r in _relic_choice_rects(s):
            br = pygame.Rect(r.x + 14, r.y + 112, r.w - 28, 30)
            if br.collidepoint(mx, my):
                msg = P.take_relic(s, key)
                if msg:
                    G.SND.play("power", 0.9)
                    _toast(g, msg, C_GOLD)
                return True
    elif tab == 2:
        for i, (c, r) in enumerate(zip(m.get("contracts", []), _contract_rects())):
            br = pygame.Rect(r.right - 146, r.y + 42, 128, 32)
            if br.collidepoint(mx, my) and c.get("done"):
                msg = P.claim_contract(s, i)
                if msg:
                    G.SND.play("coin", 0.9)
                    _toast(g, msg, C_GOLD)
                return True
    return True
