# -*- coding: utf-8 -*-
"""Мета-прогрессия «ТАРАН-ЭКСПРЕСС 3.1».

Второй слой игры поверх рейса из 20 станций:
  * «Перерождение» — рейс начинается заново, но за него дают ЧЕРТЕЖИ;
  * «Депо» — три ветки постоянных улучшений (тяга, броня, логистика);
  * реликвии — выбор одной из трёх наград после перерождения;
  * контракты — небольшие цели, за них платят чертежами;
  * достижения — 24 вехи, каждая даёт бонус к доходу;
  * модификаторы рейса — каждый забег немного другой;
  * офлайн-доход — прогресс копится, пока игра закрыта.

Модуль не импортирует game.py напрямую (иначе циклический импорт):
game.py вызывает progression.bind(sys.modules[__name__]), а UI-функции
берут шрифты и помощники рисования из G.
"""
import math
import random
import time

import pygame

G = None


def bind(game_module):
    """Запоминает модуль игры (шрифты, палитры, помощники)."""
    global G
    G = game_module


def _k(n):
    return G.fmt(n) if G is not None else str(int(n))


# --------------------------------------------------------------------------
# дерево постоянных улучшений
# --------------------------------------------------------------------------
BRANCHES = (
    dict(key="drive", name="ТЯГА", sub="экономика", color=(96, 190, 255),
         dark=(24, 46, 78)),
    dict(key="armor", name="БРОНЯ", sub="бой", color=(255, 152, 92),
         dark=(72, 36, 24)),
    dict(key="logic", name="ЛОГИСТИКА", sub="автоматизация", color=(126, 236, 162),
         dark=(26, 58, 42)),
)

META_UPGRADES = [
    # ---- тяга: экономика ----
    dict(key="capital", b=0, name="Оборотный капитал", desc="Старт рейса",
         maxl=20, base=2, growth=1.42, req=0, v=lambda l: f"${_k(2500 * l)}"),
    dict(key="profit", b=0, name="Коммерческая жилка", desc="Весь доход",
         maxl=25, base=3, growth=1.38, req=0, v=lambda l: f"+{8 * l}%"),
    dict(key="fare", b=0, name="Гибкие тарифы", desc="Цены ниже",
         maxl=10, base=4, growth=1.55, req=0, v=lambda l: f"-{4 * l}%"),
    dict(key="offline", b=0, name="Ночная смена", desc="Офлайн-доход",
         maxl=10, base=5, growth=1.5, req=1, v=lambda l: f"{25 + 7 * l}%"),
    dict(key="market", b=0, name="Оптовые закупки", desc="Зелья дешевле",
         maxl=8, base=4, growth=1.5, req=1, v=lambda l: f"-{5 * l}%"),
    dict(key="luck", b=0, name="Счастливый билет", desc="Золотые пассажиры",
         maxl=10, base=5, growth=1.5, req=2, v=lambda l: f"+{2 * l}%"),
    dict(key="legacy", b=0, name="Наследие", desc="Бонус за ранг",
         maxl=1, base=25, growth=2, req=5,
         v=lambda l: "+10% за ранг" if l else "нет"),
    dict(key="tips", b=0, name="Щедрые чаевые", desc="Монеты",
         maxl=10, base=6, growth=1.5, req=2, v=lambda l: f"+{15 * l}%"),
    dict(key="premia", b=0, name="Премия за рейс", desc="Чертежи за станции",
         maxl=5, base=10, growth=1.7, req=4,
         v=lambda l: f"+{l} ЧТ / 5 станций"),
    # ---- броня: бой ----
    dict(key="fist", b=1, name="Стальной кулак", desc="Урон клика",
         maxl=15, base=2, growth=1.4, req=0, v=lambda l: f"+{l}"),
    dict(key="radius", b=1, name="Широкий замах", desc="Радиус клика",
         maxl=10, base=3, growth=1.45, req=0, v=lambda l: f"+{8 * l}px"),
    dict(key="bosstime", b=1, name="Терпение", desc="Время на босса",
         maxl=10, base=4, growth=1.5, req=0, v=lambda l: f"+{2 * l}с"),
    dict(key="life", b=1, name="Крепкие нервы", desc="Жизни в хардкоре",
         maxl=5, base=6, growth=1.7, req=1, v=lambda l: f"+{l}"),
    dict(key="crit", b=1, name="Точный удар", desc="Шанс крита",
         maxl=10, base=5, growth=1.5, req=1, v=lambda l: f"+{3 * l}%"),
    dict(key="loot", b=1, name="Трофейная команда", desc="Награда за босса",
         maxl=10, base=5, growth=1.55, req=2, v=lambda l: f"+{10 * l}%"),
    dict(key="execute", b=1, name="Добивание", desc="Урон по слабому боссу",
         maxl=5, base=8, growth=1.7, req=4, v=lambda l: f"+{20 * l}%"),
    dict(key="sharp", b=1, name="Точный расчёт", desc="Урон крита x3",
         maxl=8, base=6, growth=1.55, req=2, v=lambda l: f"+{25 * l}%"),
    dict(key="revive", b=1, name="Второе дыхание", desc="Спасение забега",
         maxl=1, base=30, growth=2, req=5,
         v=lambda l: "1 раз за рейс" if l else "нет"),
    # ---- логистика: автоматизация ----
    dict(key="autopush", b=2, name="Автотолчок", desc="Толкает сам",
         maxl=8, base=3, growth=1.45, req=0,
         v=lambda l: "нет" if l == 0 else f"раз в {max(1, 9 - l):.0f}с"),
    dict(key="autobuy", b=2, name="Автозакупка", desc="Покупает сам",
         maxl=5, base=4, growth=1.6, req=1,
         v=lambda l: "нет" if l == 0 else f"раз в {max(1.5, 8 - 1.2 * l):.1f}с"),
    dict(key="flow", b=2, name="Логистика толпы", desc="Приток людей",
         maxl=10, base=3, growth=1.45, req=0, v=lambda l: f"+{10 * l}%"),
    dict(key="trains", b=2, name="Диспетчер", desc="Поезда чаще",
         maxl=10, base=4, growth=1.45, req=1, v=lambda l: f"+{6 * l}%"),
    dict(key="start", b=2, name="Экспресс-маршрут", desc="Стартовая станция",
         maxl=5, base=8, growth=1.9, req=3, v=lambda l: f"+{l}"),
    dict(key="keep", b=2, name="Архив чертежей", desc="Сохранить прокачку",
         maxl=5, base=6, growth=1.75, req=2, v=lambda l: f"{10 * l}%"),
    dict(key="archive", b=2, name="Методичка", desc="Больше чертежей",
         maxl=10, base=4, growth=1.5, req=0, v=lambda l: f"+{10 * l}%"),
    dict(key="seat", b=2, name="Плотная посадка", desc="Мест на перроне",
         maxl=10, base=5, growth=1.5, req=2, v=lambda l: f"+{l} мест"),
    dict(key="peak", b=2, name="Разгон", desc="Час пик",
         maxl=6, base=7, growth=1.55, req=4,
         v=lambda l: f"+{8 * l}% дольше"),
]
META_BY_KEY = {u["key"]: u for u in META_UPGRADES}
META_BY_BRANCH = {b: [u for u in META_UPGRADES if u["b"] == b] for b in range(3)}

# --------------------------------------------------------------------------
# реликвии
# --------------------------------------------------------------------------
RELICS = [
    dict(key="compass", name="Медный компас", rarity=0, stat="income", val=0.06,
         desc="+6% доход"),
    dict(key="coupon", name="Старый талон", rarity=0, stat="price", val=0.04,
         desc="-4% цены"),
    dict(key="glove", name="Кожаная перчатка", rarity=0, stat="click", val=1,
         desc="+1 урон клика"),
    dict(key="lamp", name="Красный фонарь", rarity=0, stat="flow", val=0.06,
         desc="+6% поток"),
    dict(key="coin", name="Счастливая монета", rarity=1, stat="coin", val=0.15,
         desc="+15% монеты"),
    dict(key="watch", name="Часы машиниста", rarity=1, stat="bosstime", val=2,
         desc="+2с на босса"),
    dict(key="flask", name="Фляга обходчика", rarity=1, stat="life", val=1,
         desc="+1 жизнь"),
    dict(key="book", name="Блокнот ревизора", rarity=1, stat="bp", val=0.08,
         desc="+8% чертежей"),
    dict(key="gear", name="Шестерня экспресса", rarity=1, stat="trains", val=0.08,
         desc="+8% поезда"),
    dict(key="mask", name="Маска начальника", rarity=2, stat="boss", val=0.15,
         desc="+15% награда за босса"),
    dict(key="crown", name="Корона вокзала", rarity=2, stat="income", val=0.18,
         desc="+18% доход"),
    dict(key="core", name="Ядро времени", rarity=2, stat="offline", val=0.15,
         desc="+15% офлайн"),
]
RELIC_BY_KEY = {r["key"]: r for r in RELICS}
RELIC_MAX = 5
RARITY = (
    dict(name="обычная", color=(150, 210, 255), glow=(80, 160, 255)),
    dict(name="редкая", color=(190, 150, 255), glow=(150, 100, 255)),
    dict(name="легенда", color=(255, 210, 110), glow=(255, 170, 50)),
)

# --------------------------------------------------------------------------
# модификаторы рейса
# --------------------------------------------------------------------------
RUN_MODS = [
    dict(key="calm", name="Спокойный рейс", desc="Без модификаторов",
         income=1.0, boss=1.0, flow=1.0, color=(150, 190, 255)),
    dict(key="fog", name="Туман", desc="Доход +20%, боссы +20% HP",
         income=1.20, boss=1.20, flow=1.0, color=(170, 190, 210)),
    dict(key="holiday", name="Праздник", desc="Поток +25%, доход +10%",
         income=1.10, boss=1.0, flow=1.25, color=(255, 210, 120)),
    dict(key="strike", name="Забастовка", desc="Поток -20%, доход +35%",
         income=1.35, boss=1.0, flow=0.80, color=(255, 140, 110)),
    dict(key="race", name="Гонка", desc="Поезда +20%, боссы +15%",
         income=1.15, boss=1.15, flow=1.0, color=(120, 235, 200)),
    dict(key="night", name="Ночная смена", desc="Доход +25%, офлайн +15%",
         income=1.25, boss=1.0, flow=1.0, color=(140, 120, 255)),
]
MOD_BY_KEY = {m["key"]: m for m in RUN_MODS}

# --------------------------------------------------------------------------
# контракты
# --------------------------------------------------------------------------
CONTRACT_INFO = {
    "push": ("Столкнуть пассажиров", "push"),
    "boss": ("Победить боссов", "boss"),
    "earn": ("Заработать на билетах", "earn"),
    "coins": ("Поймать монеты", "coins"),
    "station": ("Пройти станций", "station"),
    "combo": ("Собрать серию", "combo"),
}
CONTRACT_KINDS = tuple(CONTRACT_INFO)

# --------------------------------------------------------------------------
# достижения
# --------------------------------------------------------------------------
ACHIEVEMENTS = [
    dict(key="first_push", name="Первый пассажир", desc="Столкнуть 1 пассажира"),
    dict(key="push_100", name="Работяга", desc="Столкнуть 100 пассажиров"),
    dict(key="push_1000", name="Машинист дня", desc="Столкнуть 1000 пассажиров"),
    dict(key="push_10000", name="Живая легенда", desc="Столкнуть 10 000 пассажиров"),
    dict(key="first_boss", name="Первый босс", desc="Победить 1 босса"),
    dict(key="boss_10", name="Гроза вокзалов", desc="Победить 10 боссов"),
    dict(key="boss_50", name="Кошмар депо", desc="Победить 50 боссов"),
    dict(key="boss_100", name="Император путей", desc="Победить 100 боссов"),
    dict(key="first_rebirth", name="Новый рейс", desc="Переродиться 1 раз"),
    dict(key="rebirth_5", name="Ветеран", desc="Переродиться 5 раз"),
    dict(key="rebirth_20", name="Бессмертный", desc="Переродиться 20 раз"),
    dict(key="station_5", name="Дальний маршрут", desc="Дойти до станции 5"),
    dict(key="station_10", name="Ночной экспресс", desc="Дойти до станции 10"),
    dict(key="station_20", name="Трон вокзала", desc="Пройти все 20 станций"),
    dict(key="earn_1m", name="Миллионер", desc="Заработать $1M за всё время"),
    dict(key="earn_1b", name="Магнат путей", desc="Заработать $1B за всё время"),
    dict(key="combo_25", name="Серия", desc="Собрать комбо x25"),
    dict(key="combo_100", name="Конвейер", desc="Собрать комбо x100"),
    dict(key="coins_50", name="Кладоискатель", desc="Поймать 50 монет"),
    dict(key="coins_500", name="Золотая касса", desc="Поймать 500 монет"),
    dict(key="relics_8", name="Коллекционер", desc="Собрать 8 реликвий"),
    dict(key="tree_30", name="Инженер", desc="Открыть 30 уровней депо"),
    dict(key="contracts_20", name="Подрядчик", desc="Выполнить 20 контрактов"),
    dict(key="hard_10m", name="Несокрушимый", desc="Продержаться 10 минут в хардкоре"),
]
ACH_BY_KEY = {a["key"]: a for a in ACHIEVEMENTS}


# --------------------------------------------------------------------------
# сохранение
# --------------------------------------------------------------------------
def new_meta():
    return dict(
        v=4, reborn=0, bp=0, lifetime=0, best=0, epoch=1,
        tree={u["key"]: 0 for u in META_UPGRADES},
        relics={}, relic_choices=[], mod="calm",
        contracts=[], ach={}, notices=[],
        stats=dict(pushes=0, bosses=0, coins=0, stations=0, contracts=0,
                   max_combo=0, best_hard=0),
        run_bosses=0, runs=0, income_rate=0.0, last_seen=time.time(),
        offline_gain=0, offline_dt=0.0, play_t=0.0,
    )


def ensure(s):
    """Дополняет сохранение новыми полями; старые сейвы продолжают работать."""
    m = s.get("meta")
    if isinstance(m, dict) and m.get("_ok") == 4:
        return m
    if not isinstance(m, dict):
        m = new_meta()
        s["meta"] = m
    base = new_meta()
    for k, v in base.items():
        if k not in m:
            m[k] = v
    for u in META_UPGRADES:
        if not isinstance(m.get("tree"), dict):
            m["tree"] = {}
        m["tree"][u["key"]] = max(0, min(u["maxl"], int(m["tree"].get(u["key"], 0))))
    if not isinstance(m.get("relics"), dict):
        m["relics"] = {}
    for k in list(m["relics"]):
        if k not in RELIC_BY_KEY:
            m["relics"].pop(k, None)
        else:
            m["relics"][k] = max(0, min(RELIC_MAX, int(m["relics"][k])))
    if not isinstance(m.get("ach"), dict):
        m["ach"] = {}
    if not isinstance(m.get("stats"), dict):
        m["stats"] = base["stats"]
    for k, v in base["stats"].items():
        m["stats"].setdefault(k, v)
    if not isinstance(m.get("contracts"), list):
        m["contracts"] = []
    if not isinstance(m.get("relic_choices"), list):
        m["relic_choices"] = []
    if not isinstance(m.get("notices"), list):
        m["notices"] = []
    if m.get("mod") not in MOD_BY_KEY:
        m["mod"] = "calm"
    m["reborn"] = max(0, int(m.get("reborn", 0)))
    m["bp"] = max(0, int(m.get("bp", 0)))
    m["lifetime"] = max(int(m.get("lifetime", 0)), int(s.get("earned", 0)))
    m["best"] = max(0, min(20, int(m.get("best", s.get("level", 0) + 1))))
    m["_ok"] = 4
    return m


def load_meta(s, d):
    if isinstance(d.get("meta"), dict):
        s["meta"] = dict(d["meta"])
        s["meta"].pop("_ok", None)      # заставляем ensure заново проверить все поля
    m = ensure(s)
    # старый сейв без меты: лучшая станция берётся из текущего прогресса
    if not m.get("best"):
        m["best"] = min(20, int(s.get("level", 0)) + 1)
    m["last_seen"] = time.time()          # офлайн считаем только от последнего закрытия
    return m


def touch(s):
    m = ensure(s)
    now = time.time()
    last = float(m.get("last_seen") or now)
    if 0 <= now - last < 600:
        m["play_t"] = float(m.get("play_t", 0)) + max(0.0, now - last)
    m["last_seen"] = now


def pop_notice(s):
    m = ensure(s)
    if m["notices"]:
        return m["notices"].pop(0)
    return None


def notice(s, text):
    m = ensure(s)
    m["notices"].append(text)
    m["notices"][:] = m["notices"][-12:]


# --------------------------------------------------------------------------
# дерево: стоимости и эффекты
# --------------------------------------------------------------------------
def tree_lvl(s, key):
    return int(ensure(s)["tree"].get(key, 0))


def branch_lvl(s, b):
    return sum(tree_lvl(s, u["key"]) for u in META_BY_BRANCH[b])


def tree_cost(u, lvl):
    return max(1, int(round(u["base"] * u["growth"] ** lvl)))


def can_buy_meta(s, key):
    m = ensure(s)
    u = META_BY_KEY.get(key)
    if not u:
        return False
    l = tree_lvl(s, key)
    return (l < u["maxl"] and m["reborn"] >= u["req"]
            and m["bp"] >= tree_cost(u, l))


def buy_meta(s, key):
    if not can_buy_meta(s, key):
        return False
    u = META_BY_KEY[key]
    m = ensure(s)
    m["bp"] -= tree_cost(u, lvl := tree_lvl(s, key))
    m["tree"][key] = lvl + 1
    check_achievements(s)
    return True


def relic_lvl(s, key):
    return int(ensure(s)["relics"].get(key, 0))


def relic_bonus(s, stat):
    total = 0.0
    for key, lvl in ensure(s)["relics"].items():
        r = RELIC_BY_KEY.get(key)
        if r and r["stat"] == stat:
            total += r["val"] * int(lvl)
    return total


def ach_count(s):
    return len(ensure(s)["ach"])


def mod(s):
    return MOD_BY_KEY.get(ensure(s)["mod"], RUN_MODS[0])


def legacy_mult(s):
    m = ensure(s)
    if tree_lvl(s, "legacy") <= 0:
        return 1.0
    return 1.0 + 0.10 * m["reborn"]


# ---- производные характеристики ----
def income_mult(s):
    m = ensure(s)
    base = 1.0 + 0.08 * tree_lvl(s, "profit") + relic_bonus(s, "income") \
        + 0.005 * len(m["ach"])
    return base * mod(s)["income"] * legacy_mult(s)


def price_mult(s):
    red = 0.04 * tree_lvl(s, "fare") + relic_bonus(s, "price")
    return max(0.25, 1.0 - red)


def item_price_mult(s):
    return price_mult(s) * max(0.3, 1.0 - 0.05 * tree_lvl(s, "market"))


def click_damage(s, boss=None):
    # базовая формула игры: 1 + 2*smash; здесь только добавки мета-слоя
    dmg = 1 + 2 * s["levels"].get("smash", 0) + tree_lvl(s, "fist") \
        + int(relic_bonus(s, "click"))
    if boss is not None and getattr(boss, "max_hp", 0) > 0:
        frac = getattr(boss, "hp", 0) / max(1.0, boss.max_hp)
        if frac <= 0.25:
            dmg = int(round(dmg * (1.0 + 0.20 * tree_lvl(s, "execute"))))
    return max(1, dmg)


def click_radius_bonus(s):
    return 8 * tree_lvl(s, "radius")


def boss_time_bonus(s):
    return 2 * tree_lvl(s, "bosstime") + relic_bonus(s, "bosstime")


def crit_chance(s):
    return min(0.75, 0.05 * s["levels"].get("crit", 0)
               + 0.03 * tree_lvl(s, "crit"))


def start_lives(s):
    return 5 + tree_lvl(s, "life") + int(relic_bonus(s, "life"))


def start_money(s):
    m = ensure(s)
    base = 1500 + 2500 * tree_lvl(s, "capital")
    if m["reborn"] <= 0:
        return 0
    return int(base * (1 + 0.10 * m["reborn"]))


def start_station(s):
    return min(5, tree_lvl(s, "start"))


def run_flow_mult(s):
    return mod(s)["flow"] * (1.0 + 0.10 * tree_lvl(s, "flow")
                             + relic_bonus(s, "flow"))


def train_mult(s):
    return 1.0 + 0.06 * tree_lvl(s, "trains") + relic_bonus(s, "trains")


def gold_chance_bonus(s):
    return 0.02 * tree_lvl(s, "luck")


def boss_hp_mult(s):
    """HP боссов растёт с каждым перерождением, иначе прокачанный рейс
    проходился бы без сопротивления; постоянные бонусы игрока компенсируют рост."""
    m = ensure(s)
    return mod(s)["boss"] * (1.0 + 0.40 * m["reborn"])


def boss_loot_mult(s):
    return 1.0 + 0.10 * tree_lvl(s, "loot") + relic_bonus(s, "boss")


def coin_mult(s):
    return 1.0 + relic_bonus(s, "coin") + 0.15 * tree_lvl(s, "tips")


def crit_mult(s):
    """Множитель критического удара (база игры — x3)."""
    return 3.0 * (1.0 + 0.25 * tree_lvl(s, "sharp"))


def revive_charges(s):
    """Сколько раз за рейс «Второе дыхание» спасает забег."""
    return tree_lvl(s, "revive")


def capacity_bonus(s):
    return tree_lvl(s, "seat")


def rush_scale(s):
    """Час пик длится дольше и приходит чаще."""
    return 1.0 + 0.08 * tree_lvl(s, "peak")


def offline_rate(s):
    m = ensure(s)
    base = 0.25 + 0.07 * tree_lvl(s, "offline") + relic_bonus(s, "offline")
    return min(1.0, base)


def offline_cap_h(s):
    return 8.0 + 2.0 * tree_lvl(s, "offline")


def bp_mult(s):
    return 1.0 + 0.10 * tree_lvl(s, "archive") + relic_bonus(s, "bp")


def keep_fraction(s):
    return min(0.5, 0.10 * tree_lvl(s, "keep"))


def auto_push_interval(s):
    l = tree_lvl(s, "autopush")
    return 0.0 if l <= 0 else max(1.0, 9.0 - l)


def auto_buy_interval(s):
    l = tree_lvl(s, "autobuy")
    return 0.0 if l <= 0 else max(1.5, 8.0 - 1.2 * l)


def set_income_rate(s, rate):
    m = ensure(s)
    old = float(m.get("income_rate", 0.0))
    m["income_rate"] = max(0.0, old * 0.65 + rate * 0.35)


def note_income(s, amount):
    """Разовые крупные поступления (боссы, монеты) тоже влияют на оценку."""
    m = ensure(s)
    m["income_rate"] = max(float(m.get("income_rate", 0.0)), amount / 8.0)


# --------------------------------------------------------------------------
# чертежи и перерождение
# --------------------------------------------------------------------------
def can_rebirth(s):
    return s.get("level", 0) >= 9 or bool(s.get("won"))


def bp_reward(s):
    m = ensure(s)
    earned = max(0, int(s.get("earned", 0)))
    stations = min(20, int(s.get("level", 0)) + 1)
    base = ((earned / 20000.0) ** 0.62) + stations * 2.2 + m["run_bosses"] * 2.0 \
        + m["epoch"] * 6.0 + (stations // 5) * tree_lvl(s, "premia")
    return max(1, int(base * bp_mult(s) * (1.0 + 0.03 * m["reborn"])))


def _new_contract(s, slot=0):
    m = ensure(s)
    rank = m["reborn"]
    kind = random.choice(CONTRACT_KINDS)
    scale = 1.0 + 0.35 * rank + 0.10 * m["epoch"]
    if kind == "push":
        target = int((90 + 30 * rank) * scale)
    elif kind == "boss":
        target = max(1, int(2 + rank * 0.7))
    elif kind == "earn":
        target = int(20000 * (1.75 ** rank) * scale)
    elif kind == "coins":
        target = int(6 + rank * 1.5)
    elif kind == "station":
        target = int(4 + rank * 0.4)
    else:
        target = int(20 + rank * 2)
    reward = int(2 + rank // 2 + (1 if kind == "earn" else 0))
    return dict(kind=kind, target=target, progress=0, done=False,
                reward=reward, slot=slot)


def new_contracts(s):
    m = ensure(s)
    used = set()
    out = []
    for i in range(3):
        for _ in range(20):
            c = _new_contract(s, i)
            if c["kind"] not in used:
                break
        used.add(c["kind"])
        out.append(c)
    m["contracts"] = out
    return out


def track(s, kind, n=1):
    """Продвигает контракты и вехи; возвращает список завершённых контрактов."""
    m = ensure(s)
    done = []
    for c in m.get("contracts", []):
        if c.get("kind") == kind and not c.get("done"):
            c["progress"] = min(int(c["target"]), int(c.get("progress", 0)) + int(n))
            if c["progress"] >= int(c["target"]):
                c["done"] = True
                done.append(c)
                notice(s, f"Контракт готов: +{c['reward']} ЧТ (Депо → Контракты)")
    return done


def claim_contract(s, idx):
    m = ensure(s)
    if not (0 <= idx < len(m.get("contracts", []))):
        return None
    c = m["contracts"][idx]
    if not c.get("done"):
        return None
    m["bp"] += int(c["reward"])
    m["stats"]["contracts"] = int(m["stats"].get("contracts", 0)) + 1
    m["contracts"][idx] = _new_contract(s, idx)
    check_achievements(s)
    return f"Контракт выполнен: +{c['reward']} ЧТ"


def roll_relics(s):
    m = ensure(s)
    pool = [r for r in RELICS if relic_lvl(s, r["key"]) < RELIC_MAX]
    if not pool:
        return []
    rank = m["reborn"]
    w = []
    for r in pool:
        weight = (0.70, 0.25, 0.05)[min(2, r["rarity"])]
        weight *= 1.0 + 0.06 * rank
        if r["rarity"] == 2:
            weight *= 1.0 + 0.12 * rank
        w.append(weight)
    picks = []
    while pool and len(picks) < 3:
        r = random.choices(pool, weights=w, k=1)[0]
        i = pool.index(r)
        pool.pop(i)
        w.pop(i)
        picks.append(r["key"])
    return picks


def take_relic(s, key):
    m = ensure(s)
    if key not in m.get("relic_choices", []):
        return None
    r = RELIC_BY_KEY.get(key)
    if not r:
        return None
    lvl = relic_lvl(s, key)
    if lvl >= RELIC_MAX:
        m["bp"] += 4
        msg = f"Реликвия уже максимальна: +4 ЧТ"
    else:
        m["relics"][key] = lvl + 1
        msg = f"Получена реликвия: {r['name']} (ур. {lvl + 1})"
    m["relic_choices"].remove(key)
    check_achievements(s)
    return msg


def has_pending_relic(s):
    return bool(ensure(s).get("relic_choices"))


def rebirth(s):
    """Полный сброс рейса с наградой и новым модификатором."""
    m = ensure(s)
    reward = bp_reward(s)
    m["bp"] += reward
    m["lifetime"] = int(m.get("lifetime", 0)) + int(s.get("earned", 0))
    m["best"] = max(int(m.get("best", 1)), min(20, int(s.get("level", 0)) + 1))
    m["reborn"] += 1
    m["runs"] += 1
    m["epoch"] += 1
    m["run_bosses"] = 0
    m["mod"] = random.choice([x["key"] for x in RUN_MODS[1:]]) if m["reborn"] else "calm"
    keep = keep_fraction(s)
    levels = {}
    for u in G.UPGRADES:
        levels[u["key"]] = int(s["levels"].get(u["key"], 0) * keep)
    s.update(money=start_money(s), earned=0, kills=0, won=False,
             level=start_station(s),
             levels=levels,
             items={u["key"]: 0 for u in G.ITEMS})
    if s["level"]:
        s["kills"] = G.THEMES[s["level"]]["kills"]
    m["relic_choices"] = roll_relics(s)
    m["contracts"] = new_contracts(s)
    m["stats"]["stations"] = int(m["stats"].get("stations", 0))
    check_achievements(s)
    notice(s, f"Перерождение #{m['reborn']}: +{reward} ЧТ")
    return dict(reward=reward, mod=mod(s)["name"], level=s["level"],
                relic_choices=m["relic_choices"])


# --------------------------------------------------------------------------
# достижения и события
# --------------------------------------------------------------------------
def check_achievements(s):
    m = ensure(s)
    m["lifetime"] = max(int(m.get("lifetime", 0)), int(s.get("earned", 0)))
    st = m["stats"]
    got = m["ach"]
    checks = {
        "first_push": st.get("pushes", 0) >= 1,
        "push_100": st.get("pushes", 0) >= 100,
        "push_1000": st.get("pushes", 0) >= 1000,
        "push_10000": st.get("pushes", 0) >= 10000,
        "first_boss": st.get("bosses", 0) >= 1,
        "boss_10": st.get("bosses", 0) >= 10,
        "boss_50": st.get("bosses", 0) >= 50,
        "boss_100": st.get("bosses", 0) >= 100,
        "first_rebirth": m["reborn"] >= 1,
        "rebirth_5": m["reborn"] >= 5,
        "rebirth_20": m["reborn"] >= 20,
        "station_5": m["best"] >= 5,
        "station_10": m["best"] >= 10,
        "station_20": m["best"] >= 20,
        "earn_1m": m.get("lifetime", 0) >= 1_000_000,
        "earn_1b": m.get("lifetime", 0) >= 1_000_000_000,
        "combo_25": st.get("max_combo", 0) >= 25,
        "combo_100": st.get("max_combo", 0) >= 100,
        "coins_50": st.get("coins", 0) >= 50,
        "coins_500": st.get("coins", 0) >= 500,
        "relics_8": len(m.get("relics", {})) >= 8,
        "tree_30": sum(m.get("tree", {}).values()) >= 30,
        "contracts_20": st.get("contracts", 0) >= 20,
        "hard_10m": st.get("best_hard", 0) >= 600,
    }
    new = []
    for key, ok in checks.items():
        if ok and key not in got:
            got[key] = True
            m["bp"] += 1
            a = ACH_BY_KEY[key]
            notice(s, f"Достижение: {a['name']}  (+1 ЧТ)")
            new.append(a["name"])
    return new


def on_push(s, n=1):
    m = ensure(s)
    m["stats"]["pushes"] = int(m["stats"].get("pushes", 0)) + n
    track(s, "push", n)
    check_achievements(s)


def on_boss(s, secret=False):
    m = ensure(s)
    m["run_bosses"] += 1
    m["stats"]["bosses"] = int(m["stats"].get("bosses", 0)) + (0 if secret else 1)
    track(s, "boss", 1)
    check_achievements(s)


def on_coin(s):
    m = ensure(s)
    m["stats"]["coins"] = int(m["stats"].get("coins", 0)) + 1
    track(s, "coins", 1)
    check_achievements(s)


def on_combo(s, combo):
    m = ensure(s)
    combo = int(combo)
    if combo > int(m["stats"].get("max_combo", 0)):
        m["stats"]["max_combo"] = combo
        check_achievements(s)
    # контракт «серия» меряет длину комбо, а не число рекордов
    for c in m.get("contracts", []):
        if c.get("kind") == "combo" and not c.get("done"):
            c["progress"] = max(int(c.get("progress", 0)), combo)
            if c["progress"] >= int(c["target"]):
                c["done"] = True
                notice(s, f"Контракт готов: +{c['reward']} ЧТ (Депо → Контракты)")


def on_station(s):
    m = ensure(s)
    m["stats"]["stations"] = int(m["stats"].get("stations", 0)) + 1
    m["best"] = max(int(m.get("best", 1)), min(20, int(s.get("level", 0)) + 1))
    track(s, "station", 1)
    check_achievements(s)


def on_hard_time(s, t):
    m = ensure(s)
    if t > float(m["stats"].get("best_hard", 0)):
        m["stats"]["best_hard"] = float(t)
        check_achievements(s)


# --------------------------------------------------------------------------
# офлайн
# --------------------------------------------------------------------------
def catch_up(s):
    """Начисляет офлайн-доход. Возвращает (gain, seconds)."""
    m = ensure(s)
    now = time.time()
    last = float(m.get("last_seen") or now)
    if last > now + 60:
        last = now
    delta = max(0.0, now - last)
    m["last_seen"] = now
    if delta < 90:
        return 0, delta
    rate = float(m.get("income_rate", 0.0))
    if rate <= 0:
        return 0, delta
    hours = min(delta / 3600.0, offline_cap_h(s))
    gain = int(rate * 3600.0 * hours * offline_rate(s))
    if gain > 0:
        s["money"] = int(s.get("money", 0)) + gain
        s["earned"] = int(s.get("earned", 0)) + gain
        m["lifetime"] = int(m.get("lifetime", 0)) + gain
    m["offline_gain"] = gain
    m["offline_dt"] = delta
    return gain, delta


# --------------------------------------------------------------------------
# автоматизация
# --------------------------------------------------------------------------
def autobuy_pick(s):
    best = None
    for i, u in enumerate(G.UPGRADES):
        if s.get("level", 0) < u["req"]:
            continue
        lvl = s["levels"].get(u["key"], 0)
        if lvl >= u["max"]:
            continue
        c = G.cost(u, lvl, G.up_infl(s))
        if c <= s.get("money", 0) and (best is None or c < best[0]):
            best = (c, i)
    return None if best is None else best[1]


def summary(s):
    """Короткая сводка бонусов для HUD/панели."""
    m = ensure(s)
    return dict(
        rank=m["reborn"], bp=m["bp"], income=income_mult(s),
        damage=click_damage(s), lives=start_lives(s),
        mod=mod(s), relics=len(m.get("relics", {})),
        ach=len(m.get("ach", {})), tree=sum(m.get("tree", {}).values()),
    )
