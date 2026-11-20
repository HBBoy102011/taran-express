# -*- coding: utf-8 -*-
"""Единая палитра интерфейса «ТАРАН-ЭКСПРЕСС».

Один набор цветов на весь интерфейс: глубокий фон, спокойные поверхности,
1–2 акцента. Так HUD, магазин и Депо выглядят как одна система, а не как
три разных экрана. Модуль чистый: без pygame и без обращений к game.py.
"""

UI_BG = (13, 15, 24)
UI_SURFACE = (27, 31, 45)
UI_SURFACE_2 = (35, 40, 57)
UI_LINE = (52, 60, 82)
UI_LINE_SOFT = (40, 46, 64)
UI_TEXT = (232, 238, 252)
UI_DIM = (150, 162, 192)
UI_MUTED = (110, 120, 148)
UI_BLUE = (104, 160, 255)
UI_VIOLET = (166, 136, 255)
UI_GOLD = (255, 208, 112)
UI_GREEN = (118, 226, 158)
UI_RED = (255, 116, 104)

__all__ = [
    "UI_BG", "UI_SURFACE", "UI_SURFACE_2", "UI_LINE", "UI_LINE_SOFT",
    "UI_TEXT", "UI_DIM", "UI_MUTED", "UI_BLUE", "UI_VIOLET", "UI_GOLD",
    "UI_GREEN", "UI_RED",
]
