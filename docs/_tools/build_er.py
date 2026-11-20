# -*- coding: utf-8 -*-
"""ER-диаграмма и SQL/DBML-схема сохранения «ТАРАН-ЭКСПРЕСС».

Игра хранит прогресс в save.json, но модель на диаграмме — нормализованная
реляционная: 22 таблицы, справочники из taran/config.py и progression.py,
связи «один ко многим» и «один к одному».

Запуск:  py docs/_tools/build_er.py
Итог:    папка db_schema/ в корне проекта.
"""
import json
import os
import sys
from xml.sax.saxutils import escape as xml_escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import progression as P  # noqa: E402
from draw import (BG, BLUE, DIM, GOLD, GREEN, LINE, MUTED, PURPLE,  # noqa: E402
                  RED, SURFACE, SURFACE2, TEXT, Canvas, font)
from taran.config import BOSSES, ITEMS, SKINS, THEMES, UPGRADES  # noqa: E402

OUT = os.path.join(ROOT, "db_schema")

EDGE = (128, 172, 255)
HDR, ROW, PAD = 46, 24, 12

# --------------------------------------------------------------------------
# модель: таблица = имя, подпись, координаты, поля (имя, тип, ключ)
# --------------------------------------------------------------------------
def T(name, ru, x, y, w, accent, fields):
    return dict(name=name, ru=ru, x=x, y=y, w=w, accent=accent, fields=fields)


TABLES = [
    # ---------------- 1. справочники рейса ----------------
    T("themes", "Локации", 44, 232, 348, GOLD, [
        ("theme_id", "INTEGER", "PK"),
        ("name", "TEXT", ""),
        ("kills_required", "INTEGER", ""),
        ("kind", "TEXT", ""),
        ("light", "REAL", ""),
    ]),
    T("bosses", "Боссы станций", 44, 442, 348, GOLD, [
        ("boss_id", "INTEGER", "PK"),
        ("theme_id", "INTEGER", "FK"),
        ("name", "TEXT", ""),
        ("hp", "INTEGER", ""),
        ("speed", "REAL", ""),
        ("time_limit", "REAL", ""),
        ("flags", "TEXT", ""),
    ]),
    T("upgrades", "Улучшения магазина", 44, 700, 348, GOLD, [
        ("upgrade_key", "TEXT", "PK"),
        ("tab", "INTEGER", ""),
        ("req_level", "INTEGER", ""),
        ("name", "TEXT", ""),
        ("base_cost", "INTEGER", ""),
        ("growth", "REAL", ""),
        ("max_level", "INTEGER", ""),
    ]),
    T("items", "Расходники", 44, 960, 348, GOLD, [
        ("item_key", "TEXT", "PK"),
        ("name", "TEXT", ""),
        ("duration_sec", "INTEGER", ""),
        ("price", "INTEGER", ""),
        ("descr", "TEXT", ""),
    ]),
    T("skins", "Скины прохожих", 44, 1180, 348, GOLD, [
        ("skin_id", "INTEGER", "PK"),
        ("name", "TEXT", ""),
        ("palette", "TEXT", ""),
    ]),

    # ---------------- 2. сохранение игрока ----------------
    T("saves", "Сохранение игрока", 462, 232, 336, GREEN, [
        ("save_id", "INTEGER", "PK"),
        ("money", "INTEGER", ""),
        ("earned", "INTEGER", ""),
        ("kills", "INTEGER", ""),
        ("theme_id", "INTEGER", "FK"),
        ("won", "BOOLEAN", ""),
        ("muted", "BOOLEAN", ""),
        ("created_at", "TIMESTAMP", ""),
        ("updated_at", "TIMESTAMP", ""),
    ]),
    T("save_upgrades", "Уровни улучшений", 462, 700, 336, GREEN, [
        ("save_id", "INTEGER", "PKFK"),
        ("upgrade_key", "TEXT", "PKFK"),
        ("level", "INTEGER", ""),
    ]),
    T("save_items", "Заряды расходников", 462, 960, 336, GREEN, [
        ("save_id", "INTEGER", "PKFK"),
        ("item_key", "TEXT", "PKFK"),
        ("count", "INTEGER", ""),
    ]),
    T("save_skins", "Открытые скины", 462, 1180, 336, GREEN, [
        ("save_id", "INTEGER", "PKFK"),
        ("skin_id", "INTEGER", "PKFK"),
        ("unlocked_at", "TIMESTAMP", ""),
    ]),
    T("save_stats", "Статистика", 462, 1342, 336, GREEN, [
        ("save_id", "INTEGER", "PK"),
        ("pushes", "INTEGER", ""),
        ("bosses", "INTEGER", ""),
        ("coins", "INTEGER", ""),
        ("stations", "INTEGER", ""),
        ("contracts_done", "INTEGER", ""),
        ("max_combo", "INTEGER", ""),
        ("best_hard_sec", "REAL", ""),
    ]),
    T("save_notices", "Очередь уведомлений", 462, 1622, 336, GREEN, [
        ("notice_id", "INTEGER", "PK"),
        ("save_id", "INTEGER", "FK"),
        ("text", "TEXT", ""),
        ("created_at", "TIMESTAMP", ""),
    ]),

    # ---------------- 3. мета-прогрессия ----------------
    T("save_meta", "Мета-прогрессия", 896, 232, 332, PURPLE, [
        ("save_id", "INTEGER", "PK"),
        ("version", "INTEGER", ""),
        ("reborn", "INTEGER", ""),
        ("bp", "INTEGER", ""),
        ("lifetime_earned", "INTEGER", ""),
        ("best_station", "INTEGER", ""),
        ("epoch", "INTEGER", ""),
        ("mod_key", "TEXT", "FK"),
        ("run_bosses", "INTEGER", ""),
        ("runs", "INTEGER", ""),
        ("income_rate", "REAL", ""),
        ("last_seen", "TIMESTAMP", ""),
        ("offline_gain", "REAL", ""),
        ("offline_sec", "REAL", ""),
        ("play_time", "REAL", ""),
    ]),
    T("save_meta_tree", "Уровни депо", 896, 700, 332, PURPLE, [
        ("save_id", "INTEGER", "PKFK"),
        ("meta_key", "TEXT", "PKFK"),
        ("level", "INTEGER", ""),
    ]),
    T("save_relics", "Реликвии игрока", 896, 880, 332, PURPLE, [
        ("save_id", "INTEGER", "PKFK"),
        ("relic_key", "TEXT", "PKFK"),
        ("level", "INTEGER", ""),
    ]),
    T("save_relic_choices", "Текущий выбор", 896, 1060, 332, PURPLE, [
        ("save_id", "INTEGER", "PKFK"),
        ("relic_key", "TEXT", "PKFK"),
        ("offered_at", "TIMESTAMP", ""),
    ]),
    T("save_contracts", "Контракты", 896, 1240, 332, PURPLE, [
        ("contract_id", "INTEGER", "PK"),
        ("save_id", "INTEGER", "FK"),
        ("kind_key", "TEXT", "FK"),
        ("slot", "INTEGER", ""),
        ("target", "INTEGER", ""),
        ("progress", "INTEGER", ""),
        ("reward_bp", "INTEGER", ""),
        ("done", "BOOLEAN", ""),
    ]),
    T("save_achievements", "Достижения", 896, 1540, 332, PURPLE, [
        ("save_id", "INTEGER", "PKFK"),
        ("achievement_key", "TEXT", "PKFK"),
        ("unlocked_at", "TIMESTAMP", ""),
    ]),

    # ---------------- 4. справочники меты ----------------
    T("run_mods", "Модификаторы рейса", 1300, 300, 356, BLUE, [
        ("mod_key", "TEXT", "PK"),
        ("name", "TEXT", ""),
        ("descr", "TEXT", ""),
        ("income_mult", "REAL", ""),
        ("boss_mult", "REAL", ""),
        ("flow_mult", "REAL", ""),
    ]),
    T("meta_upgrades", "Дерево «Депо»", 1300, 680, 356, BLUE, [
        ("meta_key", "TEXT", "PK"),
        ("branch", "INTEGER", ""),
        ("name", "TEXT", ""),
        ("descr", "TEXT", ""),
        ("max_level", "INTEGER", ""),
        ("base_cost", "INTEGER", ""),
        ("growth", "REAL", ""),
        ("req_level", "INTEGER", ""),
    ]),
    T("relics", "Реликвии", 1300, 940, 356, BLUE, [
        ("relic_key", "TEXT", "PK"),
        ("name", "TEXT", ""),
        ("rarity", "INTEGER", ""),
        ("stat", "TEXT", ""),
        ("value", "REAL", ""),
        ("descr", "TEXT", ""),
        ("max_level", "INTEGER", ""),
    ]),
    T("contract_kinds", "Типы контрактов", 1300, 1240, 356, BLUE, [
        ("kind_key", "TEXT", "PK"),
        ("name", "TEXT", ""),
        ("stat", "TEXT", ""),
    ]),
    T("achievements", "Достижения (справочник)", 1300, 1540, 356, BLUE, [
        ("achievement_key", "TEXT", "PK"),
        ("name", "TEXT", ""),
        ("descr", "TEXT", ""),
    ]),
]

BY = {t["name"]: t for t in TABLES}

# родитель → ребёнок; route задаёт способ рисования связи
EDGES = [
    dict(src="themes", dst="saves", df="theme_id", card="N", route="right"),
    dict(src="themes", dst="bosses", df="theme_id", card="N", route="down"),
    dict(src="upgrades", dst="save_upgrades", df="upgrade_key", card="N", route="right"),
    dict(src="items", dst="save_items", df="item_key", card="N", route="right"),
    dict(src="skins", dst="save_skins", df="skin_id", card="N", route="right"),
    dict(src="saves", dst="save_upgrades", df="save_id", card="N", route="bus2"),
    dict(src="saves", dst="save_items", df="save_id", card="N", route="bus2"),
    dict(src="saves", dst="save_skins", df="save_id", card="N", route="bus2"),
    dict(src="saves", dst="save_stats", df="save_id", card="1", route="bus2"),
    dict(src="saves", dst="save_notices", df="save_id", card="N", route="bus2"),
    dict(src="saves", dst="save_meta", df="save_id", card="1", route="one"),
    dict(src="run_mods", dst="save_meta", df="mod_key", card="N", route="left"),
    dict(src="meta_upgrades", dst="save_meta_tree", df="meta_key", card="N", route="left"),
    dict(src="saves", dst="save_meta_tree", df="save_id", card="N", route="bus3"),
    dict(src="relics", dst="save_relics", df="relic_key", card="N", route="left"),
    dict(src="saves", dst="save_relics", df="save_id", card="N", route="bus3"),
    dict(src="relics", dst="save_relic_choices", df="relic_key", card="N", route="left"),
    dict(src="saves", dst="save_relic_choices", df="save_id", card="N", route="bus3"),
    dict(src="contract_kinds", dst="save_contracts", df="kind_key", card="N", route="left"),
    dict(src="saves", dst="save_contracts", df="save_id", card="N", route="bus3"),
    dict(src="achievements", dst="save_achievements", df="achievement_key", card="N", route="left"),
    dict(src="saves", dst="save_achievements", df="save_id", card="N", route="bus3"),
]

PANELS = [
    dict(x=28, y=190, w=380, h=1600, accent=GOLD, title="1 · СПРАВОЧНИКИ РЕЙСА",
         sub="taran/config.py"),
    dict(x=448, y=190, w=380, h=1600, accent=GREEN, title="2 · СОХРАНЕНИЕ ИГРОКА",
         sub="save.json"),
    dict(x=868, y=190, w=380, h=1600, accent=PURPLE, title="3 · МЕТА-ПРОГРЕССИЯ",
         sub="meta{} · progression.py"),
    dict(x=1288, y=190, w=380, h=1600, accent=BLUE, title="4 · СПРАВОЧНИКИ МЕТЫ",
         sub="progression.py"),
]

W, H = 1700, 1920


def h_of(t):
    return HDR + len(t["fields"]) * ROW + PAD


def row_center(t, field):
    for i, (name, _typ, _key) in enumerate(t["fields"]):
        if name == field:
            return t["y"] + HDR + i * ROW + ROW // 2
    raise KeyError(field)


def blend(c1, c2, k):
    return tuple(int(a + (b - a) * k) for a, b in zip(c1, c2))


# --------------------------------------------------------------------------
# рисование
# --------------------------------------------------------------------------
def draw_table(cv, t):
    x, y, w = t["x"], t["y"], t["w"]
    h = h_of(t)
    acc = t["accent"]
    cv.rect(x, y, w, h, fill=SURFACE, border=blend(acc, BG, 0.55), r=10, bw=2)

    cv.rect(x, y, w, HDR, fill=blend(acc, BG, 0.72), r=10)
    cv.rect(x, y + HDR - 12, w, 12, fill=blend(acc, BG, 0.72), r=0)
    cv.line((x, y + HDR), (x + w, y + HDR), blend(acc, BG, 0.35), 2)

    cv.text(t["name"], x + 12, y + 6, 16, TEXT, True)
    cv.text(t["ru"], x + 12, y + 27, 11, blend(acc, TEXT, 0.45))
    cv.text(f"{len(t['fields'])} пол.", x + w - 10, y + 28, 10, DIM, anchor="topright")

    for i, (name, typ, key) in enumerate(t["fields"]):
        ry = y + HDR + i * ROW
        if i:
            cv.rect(x + 1, ry, w - 2, ROW, fill=(23, 27, 39) if i % 2 else SURFACE, r=0)
        kc = {"PK": GOLD, "FK": BLUE, "PKFK": PURPLE}.get(key)
        if kc:
            cv.text("PK·FK" if key == "PKFK" else key, x + 9, ry + 7, 9, kc, True)
        cv.text(name, x + 44, ry + 5, 13, TEXT)
        cv.text(typ, x + w - 9, ry + 7, 10, MUTED, anchor="topright")


def many_marker(cv, tip, dx, dy):
    px, py = -dy, dx
    d, s = 12, 7
    bx, by = tip[0] - dx * d, tip[1] - dy * d
    cv.line(tip, (bx + px * s, by + py * s), EDGE, 2)
    cv.line(tip, (bx, by), EDGE, 2)
    cv.line(tip, (bx - px * s, by - py * s), EDGE, 2)


def one_marker(cv, pt, dx, dy):
    px, py = -dy, dx
    s = 7
    cv.line((pt[0] + px * s, pt[1] + py * s),
            (pt[0] - px * s, pt[1] - py * s), EDGE, 2)


def card_marker(cv, pt, dx, dy, card):
    if card == "1":
        one_marker(cv, pt, dx, dy)
    else:
        many_marker(cv, pt, dx, dy)


def label(cv, text, x, y, color=MUTED):
    cv.text(text, x, y, 10, color, True)


def draw_edges(cv):
    # горизонтальные связи «слева направо» (справочники рейса → сейв)
    for e in EDGES:
        if e["route"] != "right":
            continue
        src, dst = BY[e["src"]], BY[e["dst"]]
        y = row_center(dst, e["df"])
        x1, x2 = src["x"] + src["w"], dst["x"]
        cv.line((x1, y), (x2, y), EDGE, 2)
        one_marker(cv, (x1, y), 1, 0)
        card_marker(cv, (x2, y), 1, 0, e["card"])
        label(cv, "1", x1 + 10, y - 16)
        label(cv, "N", x2 - 14, y - 16)

    # горизонтальные связи «справа налево» (справочники меты → мета-таблицы)
    for e in EDGES:
        if e["route"] != "left":
            continue
        src, dst = BY[e["src"]], BY[e["dst"]]
        y = row_center(dst, e["df"])
        x1, x2 = src["x"], dst["x"] + dst["w"]
        cv.line((x1, y), (x2, y), EDGE, 2)
        one_marker(cv, (x1, y), -1, 0)
        card_marker(cv, (x2, y), -1, 0, e["card"])
        label(cv, "1", x1 - 20, y - 16)
        label(cv, "N", x2 + 6, y - 16)

    # вертикальная связь themes → bosses
    for e in EDGES:
        if e["route"] != "down":
            continue
        src, dst = BY[e["src"]], BY[e["dst"]]
        x = src["x"] + 160
        y1, y2 = src["y"] + h_of(src), dst["y"]
        cv.line((x, y1), (x, y2), EDGE, 2)
        one_marker(cv, (x, y1), 0, 1)
        card_marker(cv, (x, y2), 0, 1, e["card"])
        label(cv, "1", x + 8, y1 + 4)
        label(cv, "N", x + 8, y2 - 18)

    # 1:1 saves → save_meta
    e = next(e for e in EDGES if e["route"] == "one")
    src, dst = BY[e["src"]], BY[e["dst"]]
    y = src["y"] + 40
    x1, x2 = src["x"] + src["w"], dst["x"]
    cv.line((x1, y), (x2, y), EDGE, 2)
    one_marker(cv, (x1, y), 1, 0)
    one_marker(cv, (x2, y), 1, 0)
    label(cv, "1", x1 + 10, y - 16)
    label(cv, "1", x2 - 14, y - 16)

    # шины «сохранение → дочерние таблицы»
    draw_bus(cv, "bus2", "saves", side="right")
    draw_bus(cv, "bus3", "save_meta", side="left")


def draw_bus(cv, route, parent_name, side):
    parent = BY[parent_name]
    children = [e for e in EDGES if e["route"] == route]
    if side == "right":
        bx = parent["x"] + parent["w"] + 14
        y0 = parent["y"] + h_of(parent) - 18
        x_edge = parent["x"] + parent["w"]
    else:
        bx = parent["x"] - 18
        y0 = parent["y"] + 60
        x_edge = parent["x"]

    ys = [row_center(BY[e["dst"]], e["df"]) for e in children]
    cv.line((x_edge, y0), (bx, y0), EDGE, 2)
    cv.line((bx, y0), (bx, max(ys)), EDGE, 2)
    label(cv, "1", bx + 5, y0 - 16)

    for e, y in zip(children, ys):
        child = BY[e["dst"]]
        cx = child["x"] + child["w"] if side == "right" else child["x"]
        cv.line((bx, y), (cx, y), EDGE, 2)
        dx = -1 if side == "right" else 1
        card_marker(cv, (cx, y), dx, 0, e["card"])
        label(cv, "1" if e["card"] == "1" else "N", bx + 5, y - 16)


def draw_panel(cv, p):
    cv.rect(p["x"], p["y"], p["w"], p["h"], fill=(17, 20, 30),
            border=(38, 44, 60), r=16)
    cv.text(p["title"], p["x"] + 16, p["y"] + 10, 12, p["accent"], True)
    cv.text(p["sub"], p["x"] + 16, p["y"] + 27, 10, MUTED)
    cv.line((p["x"] + 16, p["y"] + 44), (p["x"] + p["w"] - 16, p["y"] + 44),
            blend(p["accent"], BG, 0.55), 2)


def draw_note(cv, x, y, w, text):
    cv.rect(x, y, w, 92, fill=(20, 24, 35), border=(38, 44, 60), r=10)
    cv.text(text, x + 12, y + 12, 11, DIM, wrap=w - 24)


def draw_legend(cv):
    y = 1806
    cv.text("PK", 44, y, 9, GOLD, True)
    cv.text("первичный ключ", 66, y - 1, 11, DIM)
    cv.text("FK", 190, y, 9, BLUE, True)
    cv.text("внешний ключ", 212, y - 1, 11, DIM)
    cv.text("PK·FK", 330, y, 9, PURPLE, True)
    cv.text("составной ключ", 368, y - 1, 11, DIM)

    x1 = 520
    cv.line((x1, y + 6), (x1 + 62, y + 6), EDGE, 2)
    one_marker(cv, (x1, y + 6), 1, 0)
    many_marker(cv, (x1 + 62, y + 6), 1, 0)
    cv.text("1 : N — один ко многим", x1 + 74, y - 1, 11, DIM)

    x2 = 780
    cv.line((x2, y + 6), (x2 + 62, y + 6), EDGE, 2)
    one_marker(cv, (x2, y + 6), 1, 0)
    one_marker(cv, (x2 + 62, y + 6), 1, 0)
    cv.text("1 : 1 — одна к одной", x2 + 74, y - 1, 11, DIM)

    cv.text("Модель построена по save.json, taran/config.py и progression.py · SQLite 3",
            1110, y - 1, 11, MUTED)


def build_png(path):
    cv = Canvas(W, H)
    cv.header("ER-диаграмма базы данных «ТАРАН-ЭКСПРЕСС»",
              "логическая модель сохранения прогресса · 22 таблицы · "
              "SQLite 3 · нотация «воронья лапка»", GOLD)

    for p in PANELS:
        draw_panel(cv, p)

    for t in TABLES:
        draw_table(cv, t)
    draw_edges(cv)

    draw_note(cv, 44, 1360, 348,
              f"Статические данные: {len(THEMES)} локаций, {len(BOSSES)} боссов, "
              f"{len(UPGRADES)} улучшений, {len(ITEMS)} расходников и "
              f"{len(SKINS)} скинов. Заполняются из taran/config.py "
              "при первом запуске и дальше не меняются.")
    draw_note(cv, 1300, 1690, 356,
              "Справочники меты: 6 модификаторов рейса, 27 узлов депо, "
              "12 реликвий, 6 типов контрактов и 24 достижения.")

    draw_legend(cv)
    cv.footer("Схема БД · ТАРАН-ЭКСПРЕСС 3.2 · сгенерировано docs/_tools/build_er.py")
    return cv.save(path)


# --------------------------------------------------------------------------
# SQL-схема (SQLite 3)
# --------------------------------------------------------------------------
def q(v):
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, str):
        return "'" + v.replace("'", "''") + "'"
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def insert(table, columns, rows):
    body = ",\n".join("  (" + ", ".join(q(v) for v in r) + ")" for r in rows)
    return f"INSERT INTO {table} ({', '.join(columns)}) VALUES\n{body};\n"


def skin_palette(sk):
    keep = ("color", "skin", "hair", "extra", "glow", "pants",
            "eyepatch", "long_hair")
    return json.dumps({k: sk[k] for k in keep if k in sk}, ensure_ascii=False)


def reference_seeds():
    out = []
    out.append(insert(
        "themes", ("theme_id", "name", "kills_required", "kind", "light"),
        [(i, th["name"], th["kills"], th["kind"], th["light"])
         for i, th in enumerate(THEMES)]))
    out.append(insert(
        "bosses", ("boss_id", "theme_id", "name", "hp", "speed",
                   "time_limit", "flags"),
        [(i, i, b["name"], b["hp"], b["speed"], b["time"],
          ",".join(b.get("flags", ()))) for i, b in enumerate(BOSSES)]))
    out.append(insert(
        "upgrades", ("upgrade_key", "tab", "req_level", "name", "base_cost",
                     "growth", "max_level"),
        [(u["key"], u["tab"], u["req"], u["name"], u["base"], u["growth"],
          u["max"]) for u in UPGRADES]))
    out.append(insert(
        "items", ("item_key", "name", "duration_sec", "price", "descr"),
        [(u["key"], u["name"], u["dur"], u["price"], u["desc"])
         for u in ITEMS]))
    out.append(insert(
        "skins", ("skin_id", "name", "palette"),
        [(i, s["name"], skin_palette(s)) for i, s in enumerate(SKINS)]))
    out.append(insert(
        "run_mods", ("mod_key", "name", "descr", "income_mult", "boss_mult",
                     "flow_mult"),
        [(m["key"], m["name"], m["desc"], m["income"], m["boss"], m["flow"])
         for m in P.RUN_MODS]))
    out.append(insert(
        "meta_upgrades", ("meta_key", "branch", "name", "descr", "max_level",
                          "base_cost", "growth", "req_level"),
        [(u["key"], u["b"], u["name"], u["desc"], u["maxl"], u["base"],
          u["growth"], u["req"]) for u in P.META_UPGRADES]))
    out.append(insert(
        "relics", ("relic_key", "name", "rarity", "stat", "value", "descr",
                   "max_level"),
        [(r["key"], r["name"], r["rarity"], r["stat"], r["val"], r["desc"],
          P.RELIC_MAX) for r in P.RELICS]))
    out.append(insert(
        "contract_kinds", ("kind_key", "name", "stat"),
        [(k, v[0], v[1]) for k, v in P.CONTRACT_INFO.items()]))
    out.append(insert(
        "achievements", ("achievement_key", "name", "descr"),
        [(a["key"], a["name"], a["desc"]) for a in P.ACHIEVEMENTS]))
    return "\n".join(out)


DDL = """-- ============================================================================
--  «ТАРАН-ЭКСПРЕСС» · схема базы данных (SQLite 3)
--
--  Игра хранит прогресс в save.json; эта схема — его нормализованная
--  реляционная модель плюс справочники контента из taran/config.py
--  и progression.py. 22 таблицы, версия схемы меты — 4.
--
--  Запуск:  sqlite3 taran.db < Схема_БД.sql
-- ============================================================================
PRAGMA foreign_keys = ON;

-- чистый пересоздаваемый набор (дочерние таблицы удаляются первыми)
DROP TABLE IF EXISTS save_notices;
DROP TABLE IF EXISTS save_achievements;
DROP TABLE IF EXISTS save_contracts;
DROP TABLE IF EXISTS save_relic_choices;
DROP TABLE IF EXISTS save_relics;
DROP TABLE IF EXISTS save_meta_tree;
DROP TABLE IF EXISTS save_meta;
DROP TABLE IF EXISTS save_stats;
DROP TABLE IF EXISTS save_skins;
DROP TABLE IF EXISTS save_items;
DROP TABLE IF EXISTS save_upgrades;
DROP TABLE IF EXISTS saves;
DROP TABLE IF EXISTS achievements;
DROP TABLE IF EXISTS contract_kinds;
DROP TABLE IF EXISTS relics;
DROP TABLE IF EXISTS meta_upgrades;
DROP TABLE IF EXISTS run_mods;
DROP TABLE IF EXISTS skins;
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS upgrades;
DROP TABLE IF EXISTS bosses;
DROP TABLE IF EXISTS themes;

-- ----------------------------------------------------------------------------
--  Справочники рейса
-- ----------------------------------------------------------------------------
CREATE TABLE themes (
    theme_id        INTEGER PRIMARY KEY,              -- индекс локации 0..19
    name            TEXT    NOT NULL,
    kills_required  INTEGER NOT NULL DEFAULT 0 CHECK (kills_required >= 0),
    kind            TEXT    NOT NULL,                 -- day / night / neon / ...
    light           REAL    NOT NULL DEFAULT 0 CHECK (light BETWEEN 0 AND 1)
);

CREATE TABLE bosses (
    boss_id     INTEGER PRIMARY KEY,
    theme_id    INTEGER NOT NULL REFERENCES themes(theme_id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,
    hp          INTEGER NOT NULL CHECK (hp > 0),
    speed       REAL    NOT NULL CHECK (speed > 0),
    time_limit  REAL    NOT NULL CHECK (time_limit > 0),   -- секунды на бой
    flags       TEXT    NOT NULL DEFAULT ''               -- поведения через запятую
);

CREATE TABLE upgrades (
    upgrade_key TEXT    PRIMARY KEY,                  -- power, income, flow, ...
    tab         INTEGER NOT NULL CHECK (tab BETWEEN 0 AND 2),
    req_level   INTEGER NOT NULL DEFAULT 0 CHECK (req_level >= 0),
    name        TEXT    NOT NULL,
    base_cost   INTEGER NOT NULL CHECK (base_cost > 0),
    growth      REAL    NOT NULL CHECK (growth >= 1),  -- множитель цены
    max_level   INTEGER NOT NULL CHECK (max_level > 0)
);

CREATE TABLE items (
    item_key      TEXT    PRIMARY KEY,
    name          TEXT    NOT NULL,
    duration_sec  INTEGER NOT NULL DEFAULT 0 CHECK (duration_sec >= 0),
    price         INTEGER NOT NULL CHECK (price > 0),
    descr         TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE skins (
    skin_id  INTEGER PRIMARY KEY,                     -- 0 — «Классика»
    name     TEXT    NOT NULL,
    palette  TEXT    NOT NULL DEFAULT '{}'            -- цвета в JSON
);

-- ----------------------------------------------------------------------------
--  Сохранение игрока
-- ----------------------------------------------------------------------------
CREATE TABLE saves (
    save_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    money       INTEGER NOT NULL DEFAULT 0 CHECK (money >= 0),    -- баланс
    earned      INTEGER NOT NULL DEFAULT 0 CHECK (earned >= 0),   -- доход за всё время
    kills       INTEGER NOT NULL DEFAULT 0 CHECK (kills >= 0),    -- поездки (толчки)
    theme_id    INTEGER NOT NULL REFERENCES themes(theme_id),     -- текущая станция
    won         INTEGER NOT NULL DEFAULT 0 CHECK (won IN (0, 1)),
    muted       INTEGER NOT NULL DEFAULT 0 CHECK (muted IN (0, 1)),
    created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    updated_at  INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE save_upgrades (
    save_id     INTEGER NOT NULL REFERENCES saves(save_id) ON DELETE CASCADE,
    upgrade_key TEXT    NOT NULL REFERENCES upgrades(upgrade_key),
    level       INTEGER NOT NULL DEFAULT 0 CHECK (level >= 0),
    PRIMARY KEY (save_id, upgrade_key)
);

CREATE TABLE save_items (
    save_id  INTEGER NOT NULL REFERENCES saves(save_id) ON DELETE CASCADE,
    item_key TEXT    NOT NULL REFERENCES items(item_key),
    count    INTEGER NOT NULL DEFAULT 0 CHECK (count >= 0),
    PRIMARY KEY (save_id, item_key)
);

CREATE TABLE save_skins (
    save_id     INTEGER NOT NULL REFERENCES saves(save_id) ON DELETE CASCADE,
    skin_id     INTEGER NOT NULL REFERENCES skins(skin_id),
    unlocked_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    PRIMARY KEY (save_id, skin_id)
);

CREATE TABLE save_stats (
    save_id        INTEGER PRIMARY KEY REFERENCES saves(save_id) ON DELETE CASCADE,
    pushes         INTEGER NOT NULL DEFAULT 0 CHECK (pushes >= 0),
    bosses         INTEGER NOT NULL DEFAULT 0 CHECK (bosses >= 0),
    coins          INTEGER NOT NULL DEFAULT 0 CHECK (coins >= 0),
    stations       INTEGER NOT NULL DEFAULT 0 CHECK (stations >= 0),
    contracts_done INTEGER NOT NULL DEFAULT 0 CHECK (contracts_done >= 0),
    max_combo      INTEGER NOT NULL DEFAULT 0 CHECK (max_combo >= 0),
    best_hard_sec  REAL    NOT NULL DEFAULT 0 CHECK (best_hard_sec >= 0)
);

CREATE TABLE save_notices (
    notice_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    save_id    INTEGER NOT NULL REFERENCES saves(save_id) ON DELETE CASCADE,
    text       TEXT    NOT NULL,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

-- ----------------------------------------------------------------------------
--  Мета-прогрессия
-- ----------------------------------------------------------------------------
CREATE TABLE save_meta (
    save_id         INTEGER PRIMARY KEY REFERENCES saves(save_id) ON DELETE CASCADE,
    version         INTEGER NOT NULL DEFAULT 4,        -- meta.v
    reborn          INTEGER NOT NULL DEFAULT 0 CHECK (reborn >= 0),
    bp              INTEGER NOT NULL DEFAULT 0 CHECK (bp >= 0),   -- чертежи
    lifetime_earned INTEGER NOT NULL DEFAULT 0 CHECK (lifetime_earned >= 0),
    best_station    INTEGER NOT NULL DEFAULT 0 CHECK (best_station BETWEEN 0 AND 20),
    epoch           INTEGER NOT NULL DEFAULT 1 CHECK (epoch >= 1),
    mod_key         TEXT    NOT NULL DEFAULT 'calm' REFERENCES run_mods(mod_key),
    run_bosses      INTEGER NOT NULL DEFAULT 0 CHECK (run_bosses >= 0),
    runs            INTEGER NOT NULL DEFAULT 0 CHECK (runs >= 0),
    income_rate     REAL    NOT NULL DEFAULT 0 CHECK (income_rate >= 0),
    last_seen       INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    offline_gain    REAL    NOT NULL DEFAULT 0 CHECK (offline_gain >= 0),
    offline_sec     REAL    NOT NULL DEFAULT 0 CHECK (offline_sec >= 0),
    play_time       REAL    NOT NULL DEFAULT 0 CHECK (play_time >= 0)
);

CREATE TABLE save_meta_tree (
    save_id  INTEGER NOT NULL REFERENCES saves(save_id) ON DELETE CASCADE,
    meta_key TEXT    NOT NULL REFERENCES meta_upgrades(meta_key),
    level    INTEGER NOT NULL DEFAULT 0 CHECK (level >= 0),
    PRIMARY KEY (save_id, meta_key)
);

CREATE TABLE save_relics (
    save_id   INTEGER NOT NULL REFERENCES saves(save_id) ON DELETE CASCADE,
    relic_key TEXT    NOT NULL REFERENCES relics(relic_key),
    level     INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1),
    PRIMARY KEY (save_id, relic_key)
);

CREATE TABLE save_relic_choices (
    save_id    INTEGER NOT NULL REFERENCES saves(save_id) ON DELETE CASCADE,
    relic_key  TEXT    NOT NULL REFERENCES relics(relic_key),
    offered_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    PRIMARY KEY (save_id, relic_key)
);

CREATE TABLE save_contracts (
    contract_id INTEGER PRIMARY KEY AUTOINCREMENT,
    save_id     INTEGER NOT NULL REFERENCES saves(save_id) ON DELETE CASCADE,
    kind_key    TEXT    NOT NULL REFERENCES contract_kinds(kind_key),
    slot        INTEGER NOT NULL CHECK (slot BETWEEN 0 AND 2),   -- 3 слота
    target      INTEGER NOT NULL CHECK (target > 0),
    progress    INTEGER NOT NULL DEFAULT 0 CHECK (progress >= 0),
    reward_bp   INTEGER NOT NULL DEFAULT 0 CHECK (reward_bp >= 0),
    done        INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1))
);

CREATE TABLE save_achievements (
    save_id         INTEGER NOT NULL REFERENCES saves(save_id) ON DELETE CASCADE,
    achievement_key TEXT    NOT NULL REFERENCES achievements(achievement_key),
    unlocked_at     INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    PRIMARY KEY (save_id, achievement_key)
);

-- ----------------------------------------------------------------------------
--  Справочники меты
-- ----------------------------------------------------------------------------
CREATE TABLE run_mods (
    mod_key     TEXT    PRIMARY KEY,
    name        TEXT    NOT NULL,
    descr       TEXT    NOT NULL DEFAULT '',
    income_mult REAL    NOT NULL DEFAULT 1 CHECK (income_mult > 0),
    boss_mult   REAL    NOT NULL DEFAULT 1 CHECK (boss_mult > 0),
    flow_mult   REAL    NOT NULL DEFAULT 1 CHECK (flow_mult > 0)
);

CREATE TABLE meta_upgrades (
    meta_key  TEXT    PRIMARY KEY,
    branch    INTEGER NOT NULL CHECK (branch BETWEEN 0 AND 2),   -- тяга/броня/логистика
    name      TEXT    NOT NULL,
    descr     TEXT    NOT NULL DEFAULT '',
    max_level INTEGER NOT NULL CHECK (max_level > 0),
    base_cost INTEGER NOT NULL CHECK (base_cost > 0),
    growth    REAL    NOT NULL CHECK (growth >= 1),
    req_level INTEGER NOT NULL DEFAULT 0 CHECK (req_level >= 0)
);

CREATE TABLE relics (
    relic_key TEXT    PRIMARY KEY,
    name      TEXT    NOT NULL,
    rarity    INTEGER NOT NULL CHECK (rarity BETWEEN 0 AND 2),
    stat      TEXT    NOT NULL,
    value     REAL    NOT NULL,
    descr     TEXT    NOT NULL DEFAULT '',
    max_level INTEGER NOT NULL DEFAULT 5 CHECK (max_level > 0)
);

CREATE TABLE contract_kinds (
    kind_key TEXT PRIMARY KEY,
    name     TEXT NOT NULL,
    stat     TEXT NOT NULL
);

CREATE TABLE achievements (
    achievement_key TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    descr           TEXT NOT NULL DEFAULT ''
);

-- ----------------------------------------------------------------------------
--  Индексы по внешним ключам (составные PK уже проиндексированы)
-- ----------------------------------------------------------------------------
CREATE INDEX idx_bosses_theme    ON bosses(theme_id);
CREATE INDEX idx_saves_theme     ON saves(theme_id);
CREATE INDEX idx_save_items_key  ON save_items(item_key);
CREATE INDEX idx_save_skins_key  ON save_skins(skin_id);
CREATE INDEX idx_notices_save    ON save_notices(save_id);
CREATE INDEX idx_meta_mod        ON save_meta(mod_key);
CREATE INDEX idx_tree_key        ON save_meta_tree(meta_key);
CREATE INDEX idx_relics_key      ON save_relics(relic_key);
CREATE INDEX idx_choices_key     ON save_relic_choices(relic_key);
CREATE INDEX idx_contracts_save  ON save_contracts(save_id);
CREATE INDEX idx_contracts_kind  ON save_contracts(kind_key);
CREATE INDEX idx_ach_key         ON save_achievements(achievement_key);

-- ============================================================================
--  Заполнение справочников (данные из taran/config.py и progression.py)
-- ============================================================================
"""


def build_sql(path):
    text = DDL + "\n" + reference_seeds() + """
-- Проверка: 22 таблицы, 20 локаций, 20 боссов, 16 улучшений, 6 расходников,
-- 12 скинов, 6 модификаторов, 27 узлов депо, 12 реликвий, 6 типов контрактов,
-- 24 достижения. Демо-сейв не добавляется: его создаёт игра при первом запуске.
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


# --------------------------------------------------------------------------
# DBML для dbdiagram.io
# --------------------------------------------------------------------------
DBML_TYPES = {"INTEGER": "integer", "TEXT": "text", "REAL": "real",
              "BOOLEAN": "boolean", "TIMESTAMP": "timestamp"}


def fk_edge(table, field):
    for e in EDGES:
        if e["dst"] == table and e["df"] == field:
            return e
    return None


def parent_pk(table):
    for name, _typ, key in BY[table]["fields"]:
        if key in ("PK", "PKFK"):
            return name
    return None


def build_dbml(path):
    out = [
        "// «ТАРАН-ЭКСПРЕСС» — логическая схема БД (SQLite)",
        "// Источник: save.json, taran/config.py, progression.py",
        "// Открыть: https://dbdiagram.io — File → Import → этот файл",
        "",
        "Project taran_express {",
        "  database_type: 'SQLite'",
        "  Note: 'Нормализованная модель сохранения прогресса игры. 22 таблицы.'",
        "}",
        "",
    ]
    for t in TABLES:
        out.append(f"// {t['ru']}")
        out.append(f"Table {t['name']} {{")
        pk_count = sum(1 for f in t["fields"] if f[2] in ("PK", "PKFK"))
        for name, typ, key in t["fields"]:
            attrs = []
            if key in ("PK", "PKFK") and pk_count == 1:
                attrs.append("pk")
            parent = fk_edge(t["name"], name)
            if parent:
                op = "-" if parent["card"] == "1" else ">"
                attrs.append(
                    f"ref: {op} {parent['src']}.{parent_pk(parent['src'])}")
            tail = " [" + ", ".join(attrs) + "]" if attrs else ""
            out.append(f"  {name} {DBML_TYPES.get(typ, typ.lower())}{tail}")
        if pk_count > 1:
            cols = ", ".join(f[0] for f in t["fields"] if f[2] in ("PK", "PKFK"))
            out += ["", "  indexes {", f"    ({cols}) [pk]", "  }"]
        out += ["}", ""]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    return path


# --------------------------------------------------------------------------
# draw.io (редактируемая версия той же диаграммы)
# --------------------------------------------------------------------------
BADGE_HTML = {
    "PK": "<span style='color:#ffd070;font-weight:bold'>PK</span>",
    "FK": "<span style='color:#68a0ff;font-weight:bold'>FK</span>",
    "PKFK": "<span style='color:#aa8cff;font-weight:bold'>PK·FK</span>",
    "": "",
}


def html_label(t):
    acc = "#%02x%02x%02x" % t["accent"]
    rows = []
    for name, typ, key in t["fields"]:
        rows.append(
            "<tr>"
            f"<td style='width:30px;font-size:8px'>{BADGE_HTML.get(key, '')}</td>"
            f"<td style='font-size:11px'>{xml_escape(name)}</td>"
            f"<td style='text-align:right;font-size:9px;color:#6e7894'>"
            f"{xml_escape(typ)}</td>"
            "</tr>")
    return (
        "<div style='font-family:Segoe UI,Arial;text-align:left'>"
        f"<div style='font-size:14px;font-weight:bold;color:{acc}'>"
        f"{xml_escape(t['name'])} "
        "<span style='font-size:10px;font-weight:normal;color:#96a2c0'>"
        f"{xml_escape(t['ru'])}</span></div>"
        "<table style='border-collapse:collapse;width:100%;color:#e8eefc'>"
        + "".join(rows) + "</table></div>")


def edge_style(card):
    end = "ERone" if card == "1" else "ERmany"
    return ("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;jettySize=auto;"
            "strokeColor=#80acff;strokeWidth=1.5;startArrow=ERone;"
            f"startFill=0;endArrow={end};endFill=0;")


def build_drawio(path):
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    for i, p in enumerate(PANELS, 1):
        acc = "#%02x%02x%02x" % p["accent"]
        style = (f"rounded=1;whiteSpace=wrap;html=1;fillColor=#12151f;"
                 f"strokeColor=#2c3346;verticalAlign=top;align=left;"
                 f"spacing=10;fontSize=11;fontStyle=1;fontColor={acc};")
        cells.append(
            f'<mxCell id="panel{i}" value="{xml_escape(p["title"])}" '
            f'style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{p["x"]}" y="{p["y"]}" width="{p["w"]}" '
            f'height="{p["h"]}" as="geometry"/></mxCell>')

    for t in TABLES:
        label = xml_escape(html_label(t), {'"': "&quot;"})
        style = ("rounded=1;whiteSpace=wrap;html=1;fillColor=#1b1f2d;"
                 "strokeColor=#3d4762;verticalAlign=top;align=left;"
                 "spacing=6;spacingTop=4;")
        cells.append(
            f'<mxCell id="{t["name"]}" value="{label}" style="{style}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{t["x"]}" y="{t["y"]}" width="{t["w"]}" '
            f'height="{h_of(t)}" as="geometry"/></mxCell>')

    for i, e in enumerate(EDGES, 1):
        dst = BY[e["dst"]]
        frac = round((row_center(dst, e["df"]) - dst["y"]) / h_of(dst), 3)
        route = e["route"]
        if route == "right":
            ex, ey, nx, ny = 1, 0.5, 0, frac
        elif route == "left":
            ex, ey, nx, ny = 0, 0.5, 1, frac
        elif route == "down":
            ex, ey, nx, ny = 0.5, 1, 0.5, 0
        elif route == "one":
            ex, ey, nx, ny = 1, 0.85, 0, 0.12
        elif route == "bus2":
            ex, ey, nx, ny = 1, 0.88, 1, frac
        else:  # bus3
            ex, ey, nx, ny = 0, 0.15, 0, frac
        style = (edge_style(e["card"]) +
                 f"exitX={ex};exitY={ey};entryX={nx};entryY={ny};")
        cells.append(
            f'<mxCell id="e{i}" style="{style}" edge="1" parent="1" '
            f'source="{e["src"]}" target="{e["dst"]}">'
            '<mxGeometry relative="1" as="geometry"/></mxCell>')

    xml = (
        '<mxfile host="app.diagrams.net" type="device">'
        '<diagram id="taran-db" name="ER-диаграмма">'
        '<mxGraphModel dx="1700" dy="1920" grid="0" gridSize="10" guides="1" '
        'tooltips="1" connect="1" arrows="1" fold="1" page="1" '
        'pageScale="1" pageWidth="1700" pageHeight="1920" math="0" shadow="0">'
        "<root>" + "".join(cells) + "</root></mxGraphModel></diagram></mxfile>")
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)
    return path


# --------------------------------------------------------------------------
# PDF и README
# --------------------------------------------------------------------------
def build_pdf(png, path):
    from PIL import Image
    Image.open(png).convert("RGB").save(path, "PDF", resolution=200.0)
    return path


def build_readme(path):
    counts = dict(
        themes=len(THEMES), bosses=len(BOSSES), upgrades=len(UPGRADES),
        items=len(ITEMS), skins=len(SKINS), meta=len(P.META_UPGRADES),
        relics=len(P.RELICS), mods=len(P.RUN_MODS),
        kinds=len(P.CONTRACT_INFO), ach=len(P.ACHIEVEMENTS))

    text = f"""# База данных «ТАРАН-ЭКСПРЕСС»

Комплект для отчёта и Google Диска: ER-диаграмма, готовая схема SQLite,
DBML для онлайн-редактора и редактируемый файл draw.io.

## Состав папки

| Файл | Что это | Чем открыть |
|---|---|---|
| `ER-диаграмма.png` | главная картинка диаграммы (1700 × 1920) | любой просмотрщик |
| `ER-диаграмма.pdf` | та же диаграмма для печати и Google Диска | PDF-просмотрщик |
| `Схема_БД.sql` | 22 таблицы SQLite + заполнение справочников | SQLite, DB Browser |
| `Схема_БД.dbml` | модель для dbdiagram.io | dbdiagram.io → Import |
| `ER-диаграмма.drawio` | редактируемая диаграмма | draw.io / diagrams.net |

## Важно: как игра хранит данные

Сейчас игра не использует СУБД: весь прогресс лежит в одном файле
`save.json` (на Android и в браузере — в `localStorage`). Диаграмма показывает
**нормализованную реляционную модель этого же прогресса**: то же самое, но
разложенное по таблицам со связями и ограничениями. Справочники контента
(локации, боссы, улучшения, реликвии и т. д.) взяты из `taran/config.py`
и `progression.py` и заполняются в БД автоматически.

Такой схемой можно пользоваться как проектной документацией, а можно
подключить её к игре вместо JSON — структура данных полностью совпадает.

## Группы таблиц (всего 22)

### 1. Справочники рейса — 5 таблиц
`themes` — {counts['themes']} локаций (порог поездок, тип, освещение) ·
`bosses` — {counts['bosses']} боссов (HP, скорость, время, поведения) ·
`upgrades` — {counts['upgrades']} улучшений магазина ·
`items` — {counts['items']} расходников ·
`skins` — {counts['skins']} скинов прохожих.

### 2. Сохранение игрока — 6 таблиц
`saves` — баланс, доход за всё время, поездки, текущая станция, флаги.
Дочерние таблицы: `save_upgrades` (уровни улучшений), `save_items` (заряды
зелий), `save_skins` (открытые скины), `save_stats` (статистика 1:1),
`save_notices` (очередь уведомлений).

### 3. Мета-прогрессия — 6 таблиц
`save_meta` — чертежи, перерождения, лучшая станция, модификатор, офлайн-доход
(1:1 к `saves`). Дочерние: `save_meta_tree` (уровни депо), `save_relics`
(собранные реликвии), `save_relic_choices` (текущий выбор наград),
`save_contracts` (3 активных контракта), `save_achievements` (24 вехи).

### 4. Справочники меты — 5 таблиц
`run_mods` — {counts['mods']} модификаторов рейса ·
`meta_upgrades` — {counts['meta']} узлов дерева «Депо» ·
`relics` — {counts['relics']} реликвий ·
`contract_kinds` — {counts['kinds']} типов контрактов ·
`achievements` — {counts['ach']} достижений.

## Нотация

* **PK** — первичный ключ, **FK** — внешний ключ, **PK·FK** — поле входит
  в составной первичный ключ и одновременно ссылается на справочник.
* Линия с засечкой `1` и «вороньей лапкой» `N` — связь «один ко многим».
* Линия с засечками `1` с обеих сторон — связь «один к одному».
* Пунктирных и «плавающих» связей нет: каждая линия проведена от конкретного
  поля родителя к конкретному полю ребёнка.

## Соответствие `save.json` → таблицы БД

| В `save.json` | В базе данных |
|---|---|
| `money`, `earned`, `kills`, `level`, `won`, `muted` | `saves` |
| `levels{{}}` (16 улучшений) | `save_upgrades` (строка на улучшение) |
| `items{{}}` (6 расходников) | `save_items` (строка на предмет) |
| `skins` (число открытых) | `save_skins` (строка на каждый открытый скин) |
| `meta.v`, `reborn`, `bp`, `lifetime`, `best`, `epoch`, `mod` | `save_meta` |
| `meta.tree{{}}` (27 узлов) | `save_meta_tree` |
| `meta.relics{{}}`, `meta.relic_choices[]` | `save_relics`, `save_relic_choices` |
| `meta.contracts[]` | `save_contracts` |
| `meta.ach{{}}` | `save_achievements` |
| `meta.stats{{}}` | `save_stats` |
| `meta.notices[]` | `save_notices` |
| `income_rate`, `last_seen`, `offline_gain`, `offline_dt`, `play_t` | `save_meta` |
| справочники из `config.py` / `progression.py` | `themes`, `bosses`, `upgrades`, `items`, `skins`, `run_mods`, `meta_upgrades`, `relics`, `contract_kinds`, `achievements` |

## Как пользоваться

### SQLite

```bash
sqlite3 taran.db < "Схема_БД.sql"
```

Или в **DB Browser for SQLite**: *File → Import → Database from SQL*.
Скрипт создаёт 22 таблицы, индексы и сразу заполняет справочники.
Файл можно запускать повторно — таблицы пересоздаются с нуля.

### dbdiagram.io

Открыть <https://dbdiagram.io>, нажать *Import* и выбрать `Схема_БД.dbml`.
Диаграмма отрисуется автоматически, её можно двигать и экспортировать в PNG/PDF.

### draw.io

Открыть <https://app.diagrams.net> (или Google Диск → «Открыть с помощью →
draw.io») и выбрать `ER-диаграмма.drawio`. Все таблицы и связи редактируются.

## Примечания

* `theme_id` — индекс локации `0…19`, он же `save.level`; `best_station`
  хранится как `1…20`.
* В JSON число `skins` — это количество открытых скинов. В БД то же самое
  выражается строками `save_skins`: открыты скины с `skin_id` от 0 до N−1.
* У реликвий максимум 5 уровней (`relics.max_level`), у контрактов ровно
  3 слота (`save_contracts.slot` = 0…2).
* SQLite не имеет отдельных типов `BOOLEAN` и `TIMESTAMP`: флаги хранятся
  как `INTEGER 0/1`, время — как Unix-время в секундах (см. `CHECK`).
* `save_notices` — очередь всплывающих сообщений, игра держит последние 12.

## Пересборка

```bash
py docs/_tools/build_er.py
```

Скрипт заново рисует PNG, собирает PDF, SQL, DBML, draw.io и этот README.
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    files = [
        build_png(os.path.join(OUT, "ER-диаграмма.png")),
        build_sql(os.path.join(OUT, "Схема_БД.sql")),
        build_dbml(os.path.join(OUT, "Схема_БД.dbml")),
        build_drawio(os.path.join(OUT, "ER-диаграмма.drawio")),
        build_readme(os.path.join(OUT, "README.md")),
    ]
    files.insert(1, build_pdf(files[0], os.path.join(OUT, "ER-диаграмма.pdf")))
    for p in files:
        print(p)




