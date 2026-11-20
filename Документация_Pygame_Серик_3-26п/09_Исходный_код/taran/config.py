# -*- coding: utf-8 -*-
"""Статические данные и константы «ТАРАН-ЭКСПРЕСС».

Модуль намеренно не импортирует pygame и не обращается к game.py:
здесь только чистые данные (темы, боссы, улучшения, предметы, скины).
game.py импортирует их через `from taran.config import *`, поэтому
старые обращения вида `game.KIND_HP` продолжают работать.
"""

__all__ = [
    "W",
    "H",
    "GW",
    "PW",
    "PLAT_TOP",
    "PLAT_BOT",
    "TRAIN_Y",
    "TRACK_Y",
    "THEMES",
    "KEYS",
    "STAR_KINDS",
    "BOSSES",
    "FINAL_BOSS_KILLS",
    "BOSS_HP_MULT",
    "BOSS_TIME_MULT",
    "BOSS_DMG_MAX",
    "BOSS_DMG_K",
    "UPGRADES",
    "TAB_NAMES",
    "TAB_Y",
    "TAB_W",
    "TAB_GAP",
    "ROWS_PER_TAB",
    "ROW_Y0",
    "ROW_H",
    "CARD_H",
    "PILL_W",
    "PILL_H",
    "ITEM_TAB",
    "HARD_LIVES",
    "ITEMS",
    "FX_LABELS",
    "INFL_DIV",
    "STRIP_H",
    "KEYCOL",
    "KIND_HP",
    "KIND_VALUE",
    "WALK_QUOTES",
    "FALL_QUOTES",
    "BOMB_QUOTES",
    "SKINS",
    "RUSH_DUR",
    "COMBO_MILESTONES",
]


# ---------- Геометрия и компоновка ----------
# Игра считает всё в логических координатах 1280x720, а рисует в K раз подробнее
# (на экране 1920x1080 K = 1.5, на 2560x1440 и выше K = 2). Так картинка чёткая,
# а механика, координаты и баланс не зависят от разрешения.
W, H = 1280, 720
GW, PW = 960, 320            # игровая зона и панель магазина
PLAT_TOP, PLAT_BOT = 400, 470
TRAIN_Y = 488                # верх корпуса поезда
TRACK_Y = 596                # высота ног на путях


# ---------- Локации (20 уровней, меняются по числу поездок) ----------
# Первые десять — знакомый маршрут, дальше начинается «ночной экспресс»:
# вторая половина игры длиннее по порогам и злее по боссам.
THEMES = [
    dict(name="Утро", kills=0, kind="day", light=0.0,
         top=(110, 185, 245), bot=(220, 240, 252), far=(160, 192, 215), near=(120, 150, 175),
         plat=(158, 158, 168), front=(112, 112, 128), bed=(92, 82, 74), rail=(195, 195, 205),
         train=(205, 50, 50), cloud=(255, 255, 255)),
    dict(name="Закат", kills=25, kind="sunset", light=0.3,
         top=(70, 60, 135), bot=(255, 155, 95), far=(130, 85, 115), near=(80, 52, 88),
         plat=(145, 128, 138), front=(100, 84, 100), bed=(82, 66, 66), rail=(210, 180, 170),
         train=(225, 95, 50), cloud=(255, 190, 170)),
    dict(name="Ночь", kills=70, kind="night", light=1.0,
         top=(8, 12, 38), bot=(42, 52, 105), far=(30, 38, 74), near=(18, 22, 50),
         plat=(72, 78, 98), front=(50, 54, 74), bed=(40, 38, 50), rail=(135, 140, 165),
         train=(60, 110, 205), cloud=(48, 58, 100)),
    dict(name="Зима", kills=150, kind="snow", light=0.2,
         top=(150, 182, 218), bot=(236, 243, 251), far=(192, 207, 224), near=(160, 178, 202),
         plat=(228, 234, 242), front=(172, 182, 198), bed=(192, 197, 208), rail=(150, 156, 172),
         train=(70, 150, 172), cloud=(246, 249, 253)),
    dict(name="Ливень", kills=270, kind="rain", light=0.6,
         top=(46, 54, 68), bot=(104, 114, 126), far=(76, 86, 100), near=(54, 62, 76),
         plat=(96, 100, 108), front=(70, 73, 82), bed=(56, 53, 52), rail=(150, 156, 168),
         train=(172, 62, 62), cloud=(62, 68, 80)),
    dict(name="Неон-сити", kills=430, kind="neon", light=1.0,
         top=(24, 4, 62), bot=(215, 42, 152), far=(72, 20, 112), near=(40, 10, 76),
         plat=(56, 46, 88), front=(36, 28, 62), bed=(30, 22, 50), rail=(0, 232, 232),
         train=(0, 205, 232), cloud=(120, 52, 160)),
    dict(name="Пустыня", kills=640, kind="desert", light=0.0,
         top=(240, 170, 80), bot=(255, 232, 175), far=(222, 172, 112), near=(190, 140, 90),
         plat=(214, 186, 140), front=(170, 140, 100), bed=(150, 120, 85), rail=(210, 200, 185),
         train=(40, 150, 120), cloud=(255, 240, 215)),
    dict(name="Вулкан", kills=900, kind="lava", light=0.8,
         top=(40, 10, 10), bot=(200, 60, 20), far=(90, 30, 25), near=(55, 18, 18),
         plat=(80, 62, 62), front=(56, 42, 44), bed=(44, 32, 32), rail=(255, 140, 60),
         train=(230, 110, 30), cloud=(90, 35, 30)),
    dict(name="Космос", kills=1210, kind="space", light=1.0,
         top=(3, 3, 18), bot=(40, 20, 90), far=(35, 30, 80), near=(22, 18, 60),
         plat=(90, 96, 130), front=(60, 64, 96), bed=(34, 32, 60), rail=(150, 200, 255),
         train=(180, 185, 215), cloud=(50, 40, 110)),
    dict(name="Последняя станция", kills=1580, kind="finale", light=1.0,
         top=(15, 0, 20), bot=(120, 30, 90), far=(50, 15, 60), near=(28, 8, 38),
         plat=(60, 50, 70), front=(40, 30, 52), bed=(28, 20, 36), rail=(255, 255, 255),
         train=(20, 20, 26), cloud=(90, 40, 100)),
    # ---- вторая половина: ночной экспресс ----
    dict(name="Северное сияние", kills=2010, kind="night", light=1.0,
         top=(4, 16, 38), bot=(22, 74, 92), far=(18, 54, 72), near=(10, 30, 48),
         plat=(62, 84, 104), front=(42, 58, 76), bed=(34, 42, 58), rail=(130, 220, 220),
         train=(40, 190, 170), cloud=(28, 90, 100)),
    dict(name="Штормовой порт", kills=2500, kind="rain", light=0.7,
         top=(26, 34, 48), bot=(76, 92, 110), far=(58, 68, 84), near=(40, 48, 62),
         plat=(88, 94, 104), front=(62, 68, 80), bed=(52, 50, 52), rail=(150, 158, 172),
         train=(220, 120, 50), cloud=(54, 62, 76)),
    dict(name="Золотые дюны", kills=3050, kind="desert", light=0.0,
         top=(238, 160, 60), bot=(255, 224, 150), far=(216, 164, 96), near=(184, 132, 78),
         plat=(212, 180, 128), front=(168, 134, 88), bed=(146, 114, 76), rail=(214, 200, 178),
         train=(150, 70, 160), cloud=(255, 236, 200)),
    dict(name="Ледяной дворец", kills=3660, kind="snow", light=0.3,
         top=(120, 170, 220), bot=(232, 246, 255), far=(176, 206, 232), near=(144, 178, 208),
         plat=(226, 238, 248), front=(168, 190, 214), bed=(186, 200, 220), rail=(214, 240, 255),
         train=(80, 190, 230), cloud=(250, 253, 255)),
    dict(name="Мегаполис 2099", kills=4340, kind="neon", light=1.0,
         top=(14, 0, 40), bot=(60, 0, 110), far=(100, 20, 150), near=(50, 8, 86),
         plat=(52, 40, 80), front=(32, 22, 56), bed=(26, 18, 44), rail=(255, 60, 200),
         train=(255, 40, 170), cloud=(90, 20, 140)),
    dict(name="Преисподняя", kills=5090, kind="lava", light=0.9,
         top=(30, 0, 0), bot=(230, 80, 20), far=(110, 30, 20), near=(64, 14, 12),
         plat=(76, 48, 44), front=(52, 32, 32), bed=(40, 24, 24), rail=(255, 120, 40),
         train=(255, 80, 20), cloud=(120, 30, 20)),
    dict(name="Орбита", kills=5910, kind="space", light=1.0,
         top=(0, 0, 10), bot=(20, 30, 80), far=(30, 40, 100), near=(16, 20, 60),
         plat=(80, 100, 140), front=(52, 64, 96), bed=(30, 30, 56), rail=(130, 210, 255),
         train=(220, 230, 255), cloud=(40, 60, 120)),
    dict(name="Затмение", kills=6800, kind="night", light=1.0,
         top=(10, 0, 14), bot=(90, 20, 50), far=(56, 10, 34), near=(28, 4, 20),
         plat=(66, 48, 58), front=(44, 30, 40), bed=(32, 20, 28), rail=(255, 120, 90),
         train=(160, 30, 50), cloud=(70, 14, 36)),
    dict(name="Временной разлом", kills=7760, kind="finale", light=1.0,
         top=(8, 0, 26), bot=(90, 20, 130), far=(50, 20, 90), near=(26, 8, 50),
         plat=(70, 56, 96), front=(46, 34, 68), bed=(30, 22, 48), rail=(120, 255, 210),
         train=(60, 220, 180), cloud=(90, 40, 130)),
    dict(name="Трон вокзала", kills=8800, kind="finale", light=1.0,
         top=(10, 6, 8), bot=(120, 84, 30), far=(70, 52, 26), near=(40, 28, 16),
         plat=(92, 76, 58), front=(60, 48, 36), bed=(40, 32, 24), rail=(255, 220, 140),
         train=(240, 200, 90), cloud=(120, 90, 40)),
]
KEYS = ("top", "bot", "far", "near", "plat", "front", "bed", "rail", "train", "cloud")
STAR_KINDS = ("night", "neon", "space", "finale")


# ---------- Боссы: по одному на каждый уровень ----------
BOSSES = [
    dict(name="Начальник станции", hp=40, speed=70, time=45, flags=(),
         color=(200, 40, 40), skin=(245, 210, 170), hair=(40, 30, 25), hat=(30, 30, 40)),
    dict(name="Бегун-спринтер", hp=70, speed=170, time=45, flags=("erratic",),
         color=(60, 200, 90), skin=(225, 180, 135), hair=(30, 30, 30), hat=(255, 80, 80)),
    dict(name="Тень", hp=100, speed=90, time=50, flags=("ghost", "acid"),
         color=(40, 40, 60), skin=(70, 70, 95), hair=(15, 15, 25), hat=None),
    dict(name="Снеговик-гигант", hp=140, speed=60, time=50, flags=("regen",),
         color=(240, 245, 250), skin=(250, 250, 255), hair=(220, 225, 235), hat=(40, 40, 60)),
    dict(name="Громила с зонтом", hp=180, speed=80, time=55, flags=("shield", "acid"),
         color=(30, 50, 110), skin=(190, 140, 100), hair=(30, 30, 30), hat=None),
    dict(name="Киборг-директор", hp=260, speed=110, time=60, flags=("erratic", "shield", "regen"),
         color=(80, 80, 100), skin=(170, 180, 190), hair=(60, 60, 70), hat=None),
    dict(name="Песчаный страж", hp=340, speed=130, time=60, flags=("erratic", "regen", "acid"),
         color=(170, 120, 50), skin=(200, 150, 100), hair=(90, 60, 30), hat=(220, 190, 110)),
    dict(name="Лавовый голем", hp=460, speed=75, time=65, flags=("shield", "regen", "rage"),
         color=(150, 40, 20), skin=(220, 90, 30), hair=(255, 160, 40), hat=None),
    dict(name="Пришелец-капитан", hp=620, speed=150, time=70, flags=("ghost", "erratic", "blink"),
         color=(90, 60, 160), skin=(120, 220, 150), hair=(60, 200, 120), hat=(200, 200, 230)),
    # финальный босс первой половины: тёмная кожа, длинные волосы, белая одежда, чёрные джинсы
    dict(name="Хозяйка вокзала", hp=900, speed=140, time=90,
         flags=("erratic", "shield", "regen", "ghost", "rage", "acid"),
         color=(245, 245, 248), skin=(112, 72, 48), hair=(18, 14, 14), hat=None,
         pants=(18, 18, 24), long_hair=True),
    # ---- ночной экспресс: вторая половина маршрута ----
    dict(name="Смотритель полярного пути", hp=1000, speed=120, time=85,
         flags=("regen", "shield", "dodge"),
         color=(30, 110, 120), skin=(220, 200, 180), hair=(240, 240, 245), hat=(20, 60, 70)),
    dict(name="Капитан шторма", hp=1100, speed=165, time=85,
         flags=("erratic", "rage", "acid"),
         color=(25, 60, 120), skin=(200, 150, 110), hair=(30, 30, 40), hat=(240, 200, 60)),
    dict(name="Хранитель дюн", hp=1200, speed=115, time=90,
         flags=("shield", "regen", "tough"),
         color=(180, 130, 50), skin=(205, 160, 110), hair=(70, 45, 25), hat=(245, 215, 130)),
    dict(name="Ледяная королева", hp=1320, speed=135, time=90,
         flags=("ghost", "blink", "acid", "dodge"),
         color=(180, 225, 255), skin=(230, 240, 250), hair=(200, 235, 255), hat=(250, 250, 255),
         pants=(200, 225, 245), long_hair=True),
    dict(name="Синт-директор", hp=1450, speed=175, time=95,
         flags=("erratic", "shield", "regen", "frenzy"),
         color=(40, 40, 60), skin=(120, 220, 200), hair=(255, 60, 180), hat=None),
    dict(name="Владыка пепла", hp=1580, speed=105, time=95,
         flags=("rage", "regen", "acid", "tough", "heal"),
         color=(90, 25, 20), skin=(200, 80, 40), hair=(255, 140, 50), hat=(40, 20, 20)),
    dict(name="Командор орбиты", hp=1720, speed=185, time=100,
         flags=("erratic", "blink", "shield", "dodge", "frenzy"),
         color=(30, 40, 90), skin=(150, 190, 220), hair=(220, 230, 255), hat=(200, 220, 255)),
    dict(name="Тень затмения", hp=1870, speed=155, time=100,
         flags=("ghost", "blink", "regen", "acid", "timesteal"),
         color=(30, 10, 30), skin=(80, 50, 80), hair=(20, 5, 20), hat=None),
    dict(name="Хранитель времени", hp=2030, speed=165, time=105,
         flags=("erratic", "shield", "regen", "heal", "frenzy", "timesteal"),
         color=(70, 40, 120), skin=(180, 170, 230), hair=(230, 220, 255), hat=(120, 90, 200)),
    dict(name="Император вокзала", hp=2250, speed=175, time=115,
         flags=("erratic", "shield", "regen", "ghost", "rage", "acid",
                "heal", "dodge", "tough", "frenzy"),
         color=(240, 200, 80), skin=(190, 140, 95), hair=(20, 16, 14), hat=(30, 24, 20),
         pants=(30, 26, 24)),
]
FINAL_BOSS_KILLS = 10000
BOSS_HP_MULT = 2.2      # во сколько раз больше HP у всех боссов
BOSS_TIME_MULT = 0.9    # чуть меньше времени на босса
BOSS_DMG_MAX = 41       # урон за клик при максимальной прокачке (1 + 2*20)
BOSS_DMG_K = 7.0        # во сколько раз боссы жирнее при максимальном уроне


# ---------- Улучшения, вкладки магазина и расходники ----------
UPGRADES = [
    dict(key="power", tab=0, req=0, name="Сила толчка", label="Радиус", base=50, growth=1.9, max=10,
         v=lambda l: f"{l * 35}px"),
    dict(key="income", tab=0, req=0, name="Цена билета", label="Доход", base=30, growth=1.6, max=40,
         v=lambda l: f"${round(10 * 1.35 ** l)}"),
    dict(key="flow", tab=0, req=0, name="Поток людей", label="Приток", base=40, growth=1.55, max=15,
         v=lambda l: f"x{1 + 0.25 * l:g}"),
    dict(key="trains", tab=0, req=0, name="Частота поездов", label="Раз в", base=60, growth=1.6, max=12,
         v=lambda l: f"{6 * 0.92 ** l:.1f}с"),
    dict(key="helper", tab=0, req=0, name="Помощник", label="Толкает", base=100, growth=1.7, max=8,
         v=lambda l: "нет" if l == 0 else f"{max(0.6, 6.0 - 0.7 * (l - 1)):.1f}с"),
    dict(key="combo", tab=0, req=0, name="Комбо", label="Множ.", base=80, growth=1.65, max=12,
         v=lambda l: f"x{1.5 + 0.5 * l:g}"),
    dict(key="gold", tab=0, req=0, name="Золотые пассажиры", label="Шанс x5", base=120, growth=1.7, max=8,
         v=lambda l: f"{(0.04 + 0.03 * l) * 100:.0f}%"),
    dict(key="smash", tab=0, req=0, name="Удар по боссам", label="Урон за клик", base=60, growth=1.75, max=20,
         v=lambda l: str(1 + 2 * l)),
    # --- продвинутые: открываются по мере прохождения уровней ---
    dict(key="crit", tab=1, req=1, name="Критический клик", label="Крит", base=150, growth=1.7, max=10,
         v=lambda l: f"{5 * l}%"),
    dict(key="idle", tab=1, req=2, name="Пассивный доход", label="Доход", base=200, growth=1.65, max=15,
         v=lambda l: f"${3 * l}/с"),
    dict(key="gtrain", tab=1, req=3, name="Золотой поезд", label="Шанс x3", base=300, growth=1.75, max=10,
         v=lambda l: f"{4 * l}%"),
    dict(key="timebonus", tab=1, req=4, name="Время на боссов", label="Бонус", base=250, growth=1.7, max=8,
         v=lambda l: f"+{5 * l}с"),
    dict(key="bot", tab=1, req=5, name="Помощник-боец", label="Урон боссу/с", base=400, growth=1.7, max=12,
         v=lambda l: str(2 * l)),
    dict(key="mult", tab=1, req=6, name="Экспресс-билет", label="Весь доход", base=600, growth=1.75, max=20,
         v=lambda l: f"x{1 + 0.15 * l:.2f}"),
    dict(key="cap", tab=1, req=7, name="Вместимость", label="Мест", base=500, growth=1.8, max=6,
         v=lambda l: str(14 + 2 * l)),
    dict(key="combot", tab=1, req=8, name="Долгое комбо", label="Время комбо", base=700, growth=1.8, max=8,
         v=lambda l: f"{6 + l}с"),
]
TAB_NAMES = ("Сила", "Наука", "Зелья")
TAB_Y = 60
TAB_W, TAB_GAP = 94, 98        # три сегмента в одну «дорожку» на всю ширину панели
ROWS_PER_TAB = 8
ROW_Y0, ROW_H = 99, 70      # 8 строк + подсказки снизу помещаются в 720 без наложений
CARD_H = 65
PILL_W, PILL_H = 74, 24     # кнопка-цена: один размер во всех карточках
ITEM_TAB = 2
HARD_LIVES = 5           # хардкор: столько жизней после 10-го уровня

# ---------- расходники (вкладка «Зелья») ----------
# dur > 0 — временный эффект, dur == 0 — мгновенное действие
ITEMS = [
    dict(key="p_flow", name="Зелье потока", dur=30, price=260,
         desc="x2 приток людей, 30с"),
    dict(key="p_train", name="Сжатое расписание", dur=45, price=340,
         desc="поезда x2 чаще, 45с"),
    dict(key="p_money", name="Двойная касса", dur=30, price=520,
         desc="x2 весь доход, 30с"),
    dict(key="p_power", name="Супер-толчок", dur=30, price=420,
         desc="радиус клика x2, 30с"),
    dict(key="grenade", name="Граната", dur=0, price=300,
         desc="сбивает всех сразу"),
    dict(key="antidote", name="Противоядие", dur=0, price=150,
         desc="смывает кислоту"),
]
FX_LABELS = {"p_flow": "Поток x2", "p_train": "Поезда x2",
             "p_money": "Касса x2", "p_power": "Радиус x2"}


# ---------- Инфляция ----------
# Цены привязаны к накопленному доходу s["earned"], а не к балансу: баланс тратится,
# а инфляция назад не уходит. Израсходовано $10 000 экономики — платим базовую цену,
# дальше множитель растёт линейно с доходом, поэтому граната за 280 млрд не стоит 300.
INFL_DIV = 10_000


# ---------- Мир: фон и погода ----------
STRIP_H = 244                  # высота полосы с домами (логические пиксели)
KEYCOL = (255, 0, 255)


# ---------- Объекты, реплики и скины прохожих ----------
# обычный, жирный (несколько ударов), летающий (парит), спринтер (быстрый),
# бронированный (падает только от прямого клика), бомба (взрывается и сбивает соседей)
KIND_HP = {"normal": 1, "fat": 3, "fly": 2, "sprint": 1, "armor": 2, "bomb": 1}
KIND_VALUE = {"normal": 1, "fat": 3, "fly": 3, "sprint": 2, "armor": 2.5, "bomb": 2}

# реплики людей на платформе — для веселья
WALK_QUOTES = ("Я опаздываю!", "Где мой кофе?", "Какой хороший день", "Это моя остановка?",
               "Ммм, пончики", "Я забыл утюг!", "Не толкаться!", "Поезд не видели?",
               "Опять задерживают...", "Мама, я в телевизоре!")
FALL_QUOTES = ("А-А-А!", "Мама!", "Мой телефон!", "Только не это!", "Ой-ой-ой!", "Я не хочу!",
               "Передайте жене...")
BOMB_QUOTES = ("Тик-так...", "Я не бомба!", "Не трогай меня!", "Я просто пассажир")

# ---------- скины прохожих: награда за забеги в хардкоре ----------
# 0 («Классика») открыт всегда, остальные выдаются по одному за каждый
# проигранный забег — на платформе бегают люди в этих нарядах.
SKINS = [
    dict(name="Классика"),
    dict(name="Дед Мороз", color=(200, 44, 44), skin=(245, 210, 170), hair=(240, 240, 245), extra="hat"),
    dict(name="Киборг", color=(118, 130, 152), skin=(175, 185, 195), hair=(60, 66, 78), extra="visor"),
    dict(name="Призрак", color=(206, 228, 255), skin=(225, 235, 250), hair=(200, 215, 240),
         glow=(150, 200, 255)),
    dict(name="Неон", color=(40, 255, 200), skin=(198, 255, 240), hair=(20, 40, 36), glow=(0, 255, 200)),
    dict(name="Пират", color=(72, 52, 42), hair=(30, 24, 20), extra="tricorn", eyepatch=True),
    dict(name="Астронавт", color=(234, 240, 248), skin=(200, 210, 225), hair=(180, 190, 205),
         extra="helmet", glow=(180, 210, 255)),
    dict(name="Дьявол", color=(168, 32, 32), skin=(198, 62, 52), hair=(30, 12, 12),
         extra="horns", glow=(255, 70, 40)),
    dict(name="Золотой", color=(252, 202, 44), skin=(252, 224, 132), hair=(150, 110, 30),
         extra="crown", glow=(255, 210, 60)),
    dict(name="Кот", color=(92, 92, 122), hair=(40, 40, 56), extra="ears"),
    dict(name="Король", color=(122, 44, 162), hair=(24, 18, 30), extra="crown", glow=(200, 120, 255)),
    dict(name="Ледяной", color=(122, 192, 242), skin=(214, 238, 255), hair=(230, 246, 255),
         glow=(140, 210, 255)),
]


# ---------- Быстрые режимы ----------
RUSH_DUR = 15.0          # «Час пик»: толпа и доход удваиваются
COMBO_MILESTONES = (10, 25, 50, 100, 200)
