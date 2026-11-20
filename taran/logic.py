# -*- coding: utf-8 -*-
"""Чистая игровая логика «ТАРАН-ЭКСПРЕСС».

Здесь только расчёты, которые не рисуют и не трогают состояние игры:
цены, инфляция, пороги станций и боссов, размеры кнопок магазина.
Функции зависят от данных `taran.config` и мета-прогрессии `progression`,
поэтому их можно тестировать без pygame-окна и без game.py.

game.py импортирует этот модуль целиком, поэтому старые имена
(`game.cost`, `game.boss_at`, ...) продолжают работать.
"""
import random

import pygame

import progression as P
from taran.config import (
    BOSS_DMG_K, BOSS_DMG_MAX, FINAL_BOSS_KILLS, GW, INFL_DIV, ITEMS, PILL_H,
    PILL_W, PW, ROW_H, ROW_Y0, SKINS, THEMES, UPGRADES,
)

__all__ = [
    "new_save", "stage_for", "boss_dmg_scale", "boss_at", "item_buy_rect",
    "tab_items", "inflation", "up_infl", "item_price", "cost",
    "pick_skin", "skull_chance", "pick_kind",
]


def new_save():
    """Новое сохранение: нулевой рейс и пустые уровни улучшений."""
    return dict(money=0, earned=0, kills=0, level=0, won=False, skins=1, muted=False,
                levels={u["key"]: 0 for u in UPGRADES},
                items={u["key"]: 0 for u in ITEMS}, meta=P.new_meta())


def stage_for(kills):
    """Индекс текущей локации по числу поездок."""
    idx = 0
    for i, th in enumerate(THEMES):
        if kills >= th["kills"]:
            idx = i
    return idx


def boss_dmg_scale(smash_lvl):
    """HP босса растёт прямо пропорционально урону за клик: урон / 41 * K (но не меньше x1)."""
    dmg = 1 + 2 * smash_lvl
    return max(1.0, dmg / BOSS_DMG_MAX * BOSS_DMG_K)


def boss_at(level):
    """Сколько поездок нужно, чтобы вызвать босса этого уровня."""
    return THEMES[level + 1]["kills"] if level < len(THEMES) - 1 else FINAL_BOSS_KILLS


def item_buy_rect(i):
    """Кнопка покупки внутри строки предмета.

    Правый край и размер совпадают с кнопками-ценами вкладки «Улучшения»
    (карточка кончается на 12 px от края панели), иначе кнопки двух вкладок
    «плясали» и цена попадала под курсор по-разному.
    """
    return pygame.Rect(GW + PW - 12 - PILL_W, ROW_Y0 + i * ROW_H + 34,
                       PILL_W, PILL_H)


def tab_items(t):
    """Индексы улучшений на вкладке t (0 — сила, 1 — наука)."""
    return [i for i, u in enumerate(UPGRADES) if u["tab"] == t]


def inflation(s):
    """Множитель цен магазина: чем богаче экономика, тем дороже товар."""
    return max(1.0, s.get("earned", s["money"]) / INFL_DIV)


def up_infl(s):
    """Улучшения и так растут с каждым уровнем, поэтому им хватает четвертого корня
    инфляции; бонус Депо «гибкие тарифы» применяется отдельно."""
    return inflation(s) ** 0.25 * P.price_mult(s)


def item_price(it, s):
    """Цена расходника с учётом инфляции и бонусов Депо."""
    return int(it["price"] * inflation(s) * P.item_price_mult(s))


def cost(u, lvl, infl=1.0):
    """Цена следующего уровня улучшения."""
    return int(u["base"] * u["growth"] ** lvl * infl)


def pick_skin(s):
    """Шанс украсить прохожего одним из уже открытых нарядов."""
    n = max(1, min(len(SKINS), s.get("skins", 1)))
    if n > 1 and random.random() < 0.3:
        return random.randrange(1, n)
    return 0


def skull_chance(level, base):
    """Череп летит в камеру всё реже — с каждым новым уровнем в 0.7 раза."""
    return max(0.004, base * 0.7 ** min(level, 9))


def pick_kind(kills):
    """Чем дальше игрок, тем разнообразнее (и злее) публика на платформе."""
    ramp = 1.0 + min(1.0, kills / 2500.0)
    pool = [("normal", 100)]
    for kind, w, need in (("fat", 16, 30), ("bomb", 9, 45), ("sprint", 14, 80),
                          ("fly", 12, 200), ("armor", 12, 400)):
        if kills >= need:
            pool.append((kind, w * ramp))
    total = sum(w for _, w in pool)
    r = random.uniform(0, total)
    for kind, w in pool:
        r -= w
        if r <= 0:
            return kind
    return "normal"
