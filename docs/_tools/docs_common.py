# -*- coding: utf-8 -*-
"""Общие данные и пути для сборки документов."""
import os
import shutil
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DOCS = os.path.join(ROOT, "docs")
sys.path.insert(0, ROOT)

import progression as P  # noqa: E402
from taran.config import (BOSSES, ITEMS, KIND_HP, KIND_VALUE, SKINS,  # noqa: E402
                          TAB_NAMES, THEMES, UPGRADES)

DATE = "9 ноября 2026"
VERSION = "3.2"

D01 = os.path.join(DOCS, "01_Общие_сведения")
D02 = os.path.join(DOCS, "02_Требования")
D03 = os.path.join(DOCS, "03_Спецификации")
D04 = os.path.join(DOCS, "04_Архитектура")
D05 = os.path.join(DOCS, "05_Процесс_разработки")
D06 = os.path.join(DOCS, "06_Тестирование")
D07 = os.path.join(DOCS, "07_Презентация")
MAT = os.path.join(DOCS, "материалы")
SHOTS = os.path.join(MAT, "скриншоты")
SCHEMES = os.path.join(D04, "схемы")

RARITY = {0: "обычная", 1: "редкая", 2: "эпик"}
FLAG_RU = {
    "erratic": "рывки", "shield": "щит", "regen": "регенерация", "ghost": "призрак",
    "acid": "кислота", "rage": "ярость", "blink": "телепорт", "dodge": "уклонение",
    "tough": "толстая шкура", "frenzy": "ускорение", "heal": "лечение",
    "timesteal": "крадёт время",
}
KIND_RU = {
    "normal": "обычный", "fat": "толстяк", "fly": "муха", "sprint": "бегун",
    "armor": "броня", "bomb": "бомба",
}


def prep():
    for d in (MAT, SHOTS, SCHEMES):
        os.makedirs(d, exist_ok=True)
    # скриншоты игры кладём в материалы документации
    for src, dst in (("_s_main.png", "01_рейс.png"), ("_s_tree.png", "02_депо.png"),
                     ("_s_hud.png", "03_hud.png"), ("_s_potions.png", "04_магазин_зелья.png"),
                     ("_s_contracts.png", "05_контракты.png"), ("_s_ach.png", "06_достижения.png"),
                     ("_s_relics.png", "07_реликвии.png"), ("_s_main2.png", "08_рейс_2.png"),
                     ("_s_potions2.png", "09_магазин_2.png")):
        s = os.path.join(ROOT, src)
        if os.path.exists(s):
            shutil.copyfile(s, os.path.join(SHOTS, dst))


def shot(name):
    return os.path.join(SHOTS, name)


def scheme(name):
    return os.path.join(SCHEMES, name)


def chart(name):
    return os.path.join(MAT, name)


def boss_rows():
    rows = []
    for i, b in enumerate(BOSSES, 1):
        flags = ", ".join(FLAG_RU.get(f, f) for f in b["flags"]) or "—"
        rows.append([i, b["name"], b["hp"], b["speed"], b["time"], flags])
    return rows


def theme_rows():
    return [[i, t["name"], t["kills"], t["kind"]] for i, t in enumerate(THEMES, 1)]


def upgrade_rows():
    rows = []
    for u in UPGRADES:
        rows.append([TAB_NAMES[u["tab"]], u["name"], u["base"], u["growth"], u["max"]])
    return rows


def item_rows():
    return [[i["name"], i["price"], i["dur"] or "—", i["desc"]] for i in ITEMS]


def relic_rows():
    return [[r["name"], RARITY.get(r["rarity"], r["rarity"]), r["desc"]] for r in P.RELICS]


def tree_rows():
    names = {0: "Тяга", 1: "Броня", 2: "Логистика"}
    return [[names.get(u["b"], u["b"]), u["name"], u["desc"], u["maxl"], u["base"]]
            for u in P.META_UPGRADES]


def ach_rows():
    return [[i, a["name"]] for i, a in enumerate(P.ACHIEVEMENTS, 1)]
