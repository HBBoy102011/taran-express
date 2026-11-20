# -*- coding: utf-8 -*-
"""Сохранение и загрузка прогресса «ТАРАН-ЭКСПРЕСС».

Функции принимают путь явно, поэтому модуль не зависит от того, где лежит
игра (рядом с exe, в APK или во временной папке тестов). Загрузка терпима
к старым сейвам и к битым файлам: при любой ошибке возвращается новый сейв.
"""
import json

import progression as P
from taran.config import ITEMS, SKINS, THEMES, UPGRADES
from taran.logic import new_save

__all__ = ["new_save", "load_save", "write_save"]


def load_save(path):
    """Читает сейв; недостающие поля заполняет значениями по умолчанию."""
    s = new_save()
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        s["money"] = int(d.get("money", 0))
        # старые сейвы без «earned» берут баланс за стартовую экономику —
        # иначе инфляция обнулилась бы у игрока с 280 миллиардами
        s["earned"] = max(int(d.get("earned", 0)), s["money"])
        s["kills"] = int(d.get("kills", 0))
        s["level"] = max(0, min(len(THEMES) - 1, int(d.get("level", 0))))
        s["won"] = bool(d.get("won", False))
        s["skins"] = max(1, min(len(SKINS), int(d.get("skins", 1))))
        s["muted"] = bool(d.get("muted", False))
        for u in UPGRADES:
            s["levels"][u["key"]] = max(0, min(u["max"], int(d.get("levels", {}).get(u["key"], 0))))
        for u in ITEMS:
            s["items"][u["key"]] = max(0, int(d.get("items", {}).get(u["key"], 0)))
        P.load_meta(s, d)
    except (OSError, ValueError, TypeError):
        pass
    P.ensure(s)
    return s


def write_save(s, path):
    """Записывает сейв; ошибка диска не должна ронять игру."""
    P.touch(s)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(s, f)
    except OSError:
        pass
