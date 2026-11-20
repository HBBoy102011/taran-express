# -*- coding: utf-8 -*-
"""Отрисовка панели «Мастерская» (магазин справа).

Модуль вынесен из game.py, но пока пользуется его помощниками рисования:
D, text, шрифтами и масштабом. Связь — через bind(game_module), как в
progression.py: game.py вызывает shop.bind(sys.modules[__name__]), а _sync()
перед каждым вызовом подтягивает актуальные значения (шрифты и K меняются
при смене разрешения). Когда появится общий taran/ui/kit.py, мост можно
будет убрать.
"""
import math

import pygame

import progression as P
from taran.ui.theme import *  # noqa: F401,F403

G = None

# имена, которые берутся из game.py на момент вызова, а не на момент импорта
_SYNC = (
    "GW", "PW", "H", "W", "HP", "WP", "GWP", "PWP", "K", "px",
    "ROW_Y0", "ROWS_PER_TAB", "ROW_H", "CARD_H", "TAB_Y", "TAB_GAP",
    "TAB_NAMES", "TAB_W", "ITEM_TAB", "ITEMS", "UPGRADES", "PILL_W", "PILL_H",
    "PANEL_BG", "f_mid", "f_small", "D", "text", "twidth", "ellipsize",
    "lerp_c", "fmt", "item_price", "cost", "tab_items", "up_infl", "inflation",
    "item_buy_rect", "_make_glow",
)


def bind(game_module):
    """Запоминает модуль игры, из которого берутся помощники рисования."""
    global G
    G = game_module


def _sync():
    if G is None:
        return
    g = globals()
    for name in _SYNC:
        try:
            g[name] = getattr(G, name)
        except AttributeError:
            pass


def card(surf, r, base=UI_SURFACE, border=UI_LINE, accent=None, radius=12):
    """Карточка: мягкая тень, ровная заливка, тонкая рамка и акцентная полоса."""
    _sync()
    D.rect(surf, (6, 7, 12), (r.x, r.y + 2, r.w, r.h), border_radius=radius)
    D.rect(surf, base, r, border_radius=radius)
    D.rect(surf, lerp_c(base, (255, 255, 255), 0.06),
           (r.x + 1, r.y + 1, r.w - 2, 2), border_radius=1)
    D.rect(surf, border, r, 1, border_radius=radius)
    if accent:
        D.rect(surf, accent, (r.x + 1, r.y + 10, 3, r.h - 20), border_radius=2)


def ui_pill(surf, right, y, label, can, hot=False, maxed=False):
    """Кнопка-цена справа в карточке: один размер, чтобы колонка не «плясала»."""
    _sync()
    r = pygame.Rect(int(right - PILL_W), int(y), PILL_W, PILL_H)
    if maxed:
        bg, edge, fg = (54, 46, 28), (196, 160, 78), (255, 226, 142)
    elif can:
        bg = (40, 108, 70) if hot else (32, 88, 58)
        edge, fg = (110, 210, 150), (240, 255, 246)
    else:
        bg, edge, fg = (30, 34, 48), (54, 62, 84), (140, 150, 178)
    D.rect(surf, bg, r, border_radius=8)
    D.rect(surf, edge, r, 1, border_radius=8)
    text(surf, label, f_small, fg, (r.centerx, r.y + 3), center=True, shadow=False)
    return r


def ui_badge(surf, x, y, w, h, label, bg, fg, edge=None, radius=10):
    _sync()
    D.rect(surf, bg, (x, y, w, h), border_radius=radius)
    if edge:
        D.rect(surf, edge, (x, y, w, h), 1, border_radius=radius)
    text(surf, label, f_mid, fg, (x + w // 2, y + h // 2 - 11), center=True, shadow=False)


def ui_bar(surf, r, frac, col, bg=(20, 23, 35)):
    """Плоский прогресс-бар: заливка, тёмная дорожка и тонкая рамка."""
    _sync()
    r = pygame.Rect(r)
    frac = max(0.0, min(1.0, frac))
    D.rect(surf, bg, r, border_radius=r.h // 2)
    if frac > 0:
        D.rect(surf, col, (r.x, r.y, max(3, int(r.w * frac)), r.h),
               border_radius=r.h // 2)
    D.rect(surf, (56, 64, 88), r, 1, border_radius=r.h // 2)


def ui_key(surf, x, y, label, size=22):
    """Клавиша-подсказка: маленький квадрат с буквой или цифрой."""
    _sync()
    r = pygame.Rect(x, y, size, size)
    D.rect(surf, (22, 25, 38), r, border_radius=7)
    D.rect(surf, (58, 66, 92), r, 1, border_radius=7)
    f = f_small
    text(surf, label, f, (172, 182, 210),
         (r.centerx, r.centery - f.get_height() / K / 2), center=True, shadow=False)


ITEM_COLS = {"p_flow": (62, 186, 116), "p_train": (78, 146, 235),
             "p_money": (235, 184, 56), "p_power": (232, 108, 78),
             "grenade": (176, 120, 220), "antidote": (108, 210, 146)}

_PANEL_FRAME = {"key": None, "surf": None}


_PULSE = {"key": None, "surf": None, "off": 0}


def _panel_pulse(surf, s, tab, now):
    """Дышащая подсветка строк, которые можно купить прямо сейчас.

    Раньше в ключ кэша панели входило время (int(now * 20)), и вся панель
    перерисовывалась 20 раз в секунду только ради пульсации рамки. Теперь
    панель кэшируется до реального изменения состояния, а пульс — это несколько
    блитов уже готового свечения, их дёшево делать каждый кадр.
    """
    _sync()
    a = int(45 + 65 * (0.5 + 0.5 * math.sin(now * 4))) // 10 * 10
    if a < 10:
        a = 10
    money = s["money"]
    rows = []
    if tab == ITEM_TAB:
        for k, it in enumerate(ITEMS):
            if money >= item_price(it, s):
                rows.append(k)
    else:
        upf = up_infl(s)
        for k, gi in enumerate(tab_items(tab)):
            u = UPGRADES[gi]
            lvl = s["levels"][u["key"]]
            if s["level"] >= u["req"] and lvl < u["max"] and money >= cost(u, lvl, upf):
                rows.append(k)
    if not rows:
        return
    # свечение у всех строк одно — строим раз на значение яркости и просто блитим
    st = _PULSE
    key = (K, a)
    if st["key"] != key:
        st["key"] = key
        st["off"] = int(16 * K)
        st["surf"] = _make_glow(int(16 * K), (120, 235, 150), a)
    img, off = st["surf"], st["off"]
    x = px(GW + 27) - off
    for k in rows:
        surf.blit(img, (x, px(ROW_Y0 + k * ROW_H + CARD_H // 2) - off))


TAB_COLORS = ((104, 160, 255), (166, 136, 255), (118, 226, 158))


def _tab_icon(surf, t, cx, cy, col):
    """Крошечные иконки вкладок: молния / колба / бутыль."""
    _sync()
    if t == 0:
        D.polygon(surf, col, [(cx + 2, cy - 7), (cx - 4, cy + 1), (cx - 1, cy + 1),
                              (cx - 3, cy + 7), (cx + 5, cy - 2), (cx + 1, cy - 2)])
    elif t == 1:
        D.rect(surf, col, (cx - 2, cy - 8, 4, 5), border_radius=1)
        D.polygon(surf, col, [(cx - 2, cy - 4), (cx + 2, cy - 4),
                              (cx + 6, cy + 6), (cx - 6, cy + 6)])
        D.rect(surf, (18, 21, 32), (cx - 4, cy + 2, 8, 3), border_radius=1)
    else:
        D.rect(surf, col, (cx - 2, cy - 8, 4, 4), border_radius=1)
        D.rect(surf, col, (cx - 3, cy - 5, 6, 5), border_radius=1)
        D.circle(surf, col, (cx, cy + 3), 5)
        D.rect(surf, (18, 21, 32), (cx - 3, cy + 1, 6, 2), border_radius=1)


def draw_panel(surf, s, mouse, tab):
    """Панель магазина перерисовывается только при изменении состояния.

    На телефоне это была одна из самых дорогих частей кадра, хотя меняются
    в ней только деньги, уровни, счётчики и подсветка строки под курсором.
    """
    _sync()
    now = pygame.time.get_ticks() / 1000.0
    dst = surf
    hover = -1
    if mouse[0] >= GW and ROW_Y0 <= mouse[1] < ROW_Y0 + ROWS_PER_TAB * ROW_H:
        idx = int((mouse[1] - ROW_Y0) // ROW_H)
        if mouse[1] < ROW_Y0 + idx * ROW_H + CARD_H:
            hover = idx
    hover_tab = -1
    if mouse[0] >= GW and TAB_Y - 4 <= mouse[1] < TAB_Y + 34:
        t = int((mouse[0] - (GW + 12)) // TAB_GAP)
        if 0 <= t < len(TAB_NAMES):
            hover_tab = t
    key = (surf.get_size(), tab, int(s["money"]), s["level"],
           bool(s.get("won", False)), tuple(s["levels"].values()),
           tuple(sorted(s["items"].items())), hover, hover_tab,
           int(P.ensure(s)["bp"]))
    cache = _PANEL_FRAME
    if cache["key"] == key and cache["surf"] is not None:
        dst.blit(cache["surf"], (GWP, 0), (GWP, 0, PWP, HP))
        _panel_pulse(dst, s, tab, now)
        return
    scratch = cache["surf"]
    if scratch is None or scratch.get_size() != surf.get_size():
        scratch = pygame.Surface(surf.get_size())
        try:
            scratch = scratch.convert()
        except pygame.error:
            pass
        cache["surf"] = scratch
    cache["key"] = key
    surf = scratch

    inf = inflation(s)
    upf = up_infl(s)
    surf.blit(PANEL_BG, (GWP, 0))
    accent = TAB_COLORS[tab % len(TAB_COLORS)]
    # мягкая цветная кромка отделяет магазин от игрового поля
    D.rect(surf, lerp_c((54, 62, 86), accent, 0.35), (GW, 0, 2, H))

    # ---- шапка: название, ранг и две «пилюли» ----
    text(surf, "МАСТЕРСКАЯ", f_mid, UI_TEXT, (GW + 18, 5), shadow=False)
    sub_head = f"ранг {P.ensure(s)['reborn']}"
    text(surf, ellipsize(f_small, sub_head, 112), f_small, UI_MUTED,
         (GW + 19, 30), shadow=False)
    bpl = f"ЧТ {P.ensure(s)['bp']}"
    bw2 = int(twidth(f_small, bpl)) + 20
    br2 = pygame.Rect(GW + PW - 12 - bw2, 26, bw2, 22)
    D.rect(surf, (52, 46, 28), br2, border_radius=7)
    D.rect(surf, (150, 122, 56), br2, 1, border_radius=7)
    text(surf, bpl, f_small, UI_GOLD, (br2.centerx, br2.y + 3),
         center=True, shadow=False)
    lab = f"ИНФЛЯЦИЯ ×{fmt(int(inf))}"
    iw = int(twidth(f_small, lab)) + 20
    ir = pygame.Rect(br2.x - 6 - iw, 26, iw, 22)
    D.rect(surf, (46, 40, 26), ir, border_radius=7)
    D.rect(surf, (120, 100, 52), ir, 1, border_radius=7)
    text(surf, lab, f_small, (226, 194, 120), (ir.centerx, ir.y + 3),
         center=True, shadow=False)
    D.rect(surf, lerp_c(UI_LINE_SOFT, accent, 0.30), (GW + 12, 54, PW - 24, 1))

    # ---- вкладки: сегментированный переключатель с иконками ----
    track = pygame.Rect(GW + 10, 58, PW - 20, 36)
    D.rect(surf, (18, 21, 32), track, border_radius=11)
    D.rect(surf, UI_LINE_SOFT, track, 1, border_radius=11)
    for t in range(len(TAB_NAMES)):
        r = pygame.Rect(GW + 12 + t * TAB_GAP, 61, TAB_W, 30)
        active = (t == tab)
        hot = (t == hover_tab and not active)
        col = TAB_COLORS[t % len(TAB_COLORS)]
        if active:
            bg = lerp_c((22, 26, 38), col, 0.34)
            edge = lerp_c(col, (255, 255, 255), 0.18)
        elif hot:
            bg, edge = (34, 39, 55), (64, 72, 98)
        else:
            bg, edge = (24, 28, 41), (40, 46, 64)
        D.rect(surf, bg, r, border_radius=8)
        D.rect(surf, edge, r, 1, border_radius=8)
        _tab_icon(surf, t, r.x + 15, r.centery,
                  col if active else lerp_c(col, (80, 88, 112), 0.55))
        text(surf, TAB_NAMES[t], f_small,
             UI_TEXT if active else (162, 172, 200),
             (r.centerx + 7, r.y + 7), center=True, shadow=False)
        if active:
            D.rect(surf, col, (r.x + 18, r.bottom - 3, r.w - 36, 2), border_radius=1)
        ready = False
        if t == ITEM_TAB:
            ready = any(s["money"] >= item_price(it, s) for it in ITEMS)
        else:
            for gi in tab_items(t):
                u = UPGRADES[gi]
                lvl = s["levels"][u["key"]]
                if s["level"] >= u["req"] and lvl < u["max"] and s["money"] >= cost(u, lvl, upf):
                    ready = True
                    break
        if ready and not active:      # жёлтая точка — есть что купить
            D.circle(surf, (255, 200, 60), (r.right - 9, r.y + 9), 4)

    # ---- карточки улучшений ----
    for k, gi in enumerate(tab_items(tab)):
        u = UPGRADES[gi]
        lvl = s["levels"][u["key"]]
        r = pygame.Rect(GW + 12, ROW_Y0 + k * ROW_H, PW - 24, CARD_H)
        locked = s["level"] < u["req"]
        if locked:
            card(surf, r, (23, 26, 38), UI_LINE_SOFT, radius=12)
            ui_badge(surf, r.x + 10, r.y + 9, 36, 36, "—", (25, 28, 40),
                     (104, 112, 140), (44, 50, 68), radius=10)
            text(surf, ellipsize(f_mid, u["name"], r.w - 106), f_mid, (118, 126, 150),
                 (r.x + 54, r.y + 5), shadow=False)
            text(surf, f"Откроется на уровне {u['req'] + 1}", f_small,
                 (140, 148, 176), (r.x + 54, r.y + 31), shadow=False)
            lx, ly = r.right - 34, r.y + 20
            D.rect(surf, (92, 100, 132), (lx, ly, 15, 12), border_radius=3)
            D.arc(surf, (92, 100, 132), (lx + 2, ly - 9, 11, 13), 0, math.pi, 2)
            continue
        maxed = lvl >= u["max"]
        c = cost(u, lvl, upf)
        can = (not maxed) and s["money"] >= c
        hot = (k == hover)
        if maxed:
            bg, edge, ac = (34, 31, 22), (150, 124, 58), UI_GOLD
        elif can:
            bg = (29, 38, 36) if not hot else (35, 46, 43)
            edge, ac = (46, 96, 68), UI_GREEN
        else:
            bg = (29, 33, 47) if not hot else (34, 39, 55)
            edge, ac = UI_LINE, None
        card(surf, r, bg, edge, ac, radius=12)
        bcol = (30, 76, 54) if can else ((56, 48, 28) if maxed else (24, 28, 41))
        bfg = (206, 255, 220) if can else ((255, 228, 144) if maxed else (196, 204, 230))
        ui_badge(surf, r.x + 10, r.y + 9, 36, 36, str(lvl), bcol, bfg,
                 lerp_c(edge, (0, 0, 0), 0.15), radius=10)
        lvs = f"{lvl}/{u['max']}"
        text(surf, lvs, f_small, (156, 168, 198),
             (r.right - 12 - twidth(f_small, lvs), r.y + 8), shadow=False)
        nmax = r.right - 12 - twidth(f_small, lvs) - 12 - (r.x + 54)
        fn = f_mid if twidth(f_mid, u["name"]) <= nmax - 10 else f_small
        text(surf, ellipsize(fn, u["name"], nmax), fn, UI_TEXT,
             (r.x + 54, r.y + (5 if fn is f_mid else 8)), shadow=False)
        pill = "МАКС" if maxed else f"${fmt(c)}"
        pr = ui_pill(surf, r.right - 12, r.y + 34, pill, can, hot, maxed)
        line = f"{u['label']}: {u['v'](lvl)}" + ("" if maxed else f" → {u['v'](lvl + 1)}")
        # описание не заходит под кнопку цены, даже если подпись длинная
        line = ellipsize(f_small, line, max(40, pr.x - 10 - (r.x + 54)))
        text(surf, line, f_small, (198, 208, 234), (r.x + 54, r.y + 31), shadow=False)
        # тонкая полоска уровня по низу карточки
        bw = r.w - 20
        D.rect(surf, (20, 23, 35), (r.x + 10, r.y + CARD_H - 5, bw, 3), border_radius=2)
        D.rect(surf, UI_GOLD if maxed else UI_GREEN,
               (r.x + 10, r.y + CARD_H - 5,
                max(2, int(bw * lvl / u["max"])), 3), border_radius=2)

    # ---- вкладка «Зелья»: строка — применить, кнопка справа — купить ----
    if tab == ITEM_TAB:
        for k, it in enumerate(ITEMS):
            r = pygame.Rect(GW + 12, ROW_Y0 + k * ROW_H, PW - 24, CARD_H)
            cnt = s["items"].get(it["key"], 0)
            p = item_price(it, s)
            can = s["money"] >= p
            hot = (k == hover)
            icol = ITEM_COLS.get(it["key"], (120, 140, 200))
            if cnt:
                bg = lerp_c((30, 35, 45), icol, 0.06)
                edge, ac = lerp_c(icol, UI_LINE, 0.45), icol
            else:
                bg, edge, ac = (29, 33, 47), UI_LINE, None
            if hot:
                bg = lerp_c(bg, (255, 255, 255), 0.05)
            card(surf, r, bg, edge, ac, radius=12)
            D.rect(surf, lerp_c(icol, (0, 0, 0), 0.55), (r.x + 10, r.y + 9, 36, 36),
                   border_radius=10)
            D.rect(surf, lerp_c(icol, (0, 0, 0), 0.28), (r.x + 11, r.y + 10, 34, 34),
                   border_radius=9)
            text(surf, it["name"][0], f_mid, (250, 252, 255),
                 (r.x + 28, r.y + 16), center=True, shadow=False)
            bs_ = f"×{cnt}"
            cw = int(twidth(f_small, bs_)) + 16
            cr = pygame.Rect(r.right - 12 - cw, r.y + 7, cw, 18)
            D.rect(surf, (52, 46, 28) if cnt else (26, 30, 43), cr, border_radius=7)
            D.rect(surf, (140, 116, 58) if cnt else (44, 50, 68), cr, 1, border_radius=7)
            text(surf, bs_, f_small, UI_GOLD if cnt else (140, 150, 178),
                 (cr.centerx, cr.y + 2), center=True, shadow=False)
            nmax = cr.x - 10 - (r.x + 54)
            fn = f_mid if twidth(f_mid, it["name"]) <= nmax - 10 else f_small
            text(surf, ellipsize(fn, it["name"], nmax), fn, UI_TEXT,
                 (r.x + 54, r.y + (5 if fn is f_mid else 8)), shadow=False)
            br = item_buy_rect(k)
            dmax = br.x - 10 - (r.x + 54)
            text(surf, ellipsize(f_small, it["desc"], dmax),
                 f_small, (198, 208, 234), (r.x + 54, r.y + 31), shadow=False)
            ui_pill(surf, r.right - 12, r.y + 34, f"${fmt(p)}", can, hot)

    # ---- нижняя подсказка ----
    D.rect(surf, UI_LINE_SOFT, (GW + 12, H - 62, PW - 24, 1))
    if tab == ITEM_TAB:
        tip1 = "ЛКМ — применить  ·  цена — купить"
    else:
        tip1 = "ЛКМ — купить  ·  Shift — ×10"
    text(surf, tip1, f_small, UI_MUTED, (GW + 16, H - 48), shadow=False)
    text(surf, "Tab — вкладка  ·  1–8 — выбор",
         f_small, UI_MUTED, (GW + 16, H - 26), shadow=False)
    dst.blit(cache["surf"], (GWP, 0), (GWP, 0, PWP, HP))
    _panel_pulse(dst, s, tab, now)
