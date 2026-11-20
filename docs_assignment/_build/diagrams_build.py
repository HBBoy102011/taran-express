# -*- coding: utf-8 -*-
"""Восемь схем комплекта: 5 UML + 2 блок-схемы + архитектура.

Схемы рисуются в двух форматах: PNG (для DOCX) и .drawio (редактируемый).
Все подписи — по реальному коду «ТАРАН-ЭКСПРЕСС» 3.2.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from diagramlib import (BLUE, GOLD, GREEN, LINE, MUTED, PURPLE, RED, SURFACE,
                        SURFACE2, Node, begin)

OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), "Документация_Pygame_Серик_3-26п",
                   "04_Проектирование и UML", "Диаграммы")

C1, C2, C3 = (38, 44, 62), (30, 35, 50), (24, 28, 40)


def save(d, name):
    png = d.render(os.path.join(OUT, name + ".png"))
    d.save_drawio(os.path.join(OUT, name + ".drawio"))
    print("ok", name, os.path.getsize(png) // 1024, "KB")
    return png


def box(d, nid, x, y, w, h, title, lines=(), color=GREEN, fill=(26, 34, 40),
        title_size=21, font_size=16, align="center"):
    return d.add(Node(nid, "box", x, y, w, h, title, lines, color=color, fill=fill,
                      title_size=title_size, font_size=font_size, align=align))


def dec(d, nid, x, y, w, h, title, color=GOLD, font_size=16):
    return d.add(Node(nid, "decision", x, y, w, h, title, color=color,
                      fill=(40, 36, 24), font_size=font_size))


def center(n):
    return (n.x + n.w // 2, n.y + n.h // 2)


# ---------------------------------------------------------------- 1. use case
def usecase():
    d = begin("UML: диаграмма вариантов использования",
              "Что игрок делает в «ТАРАН-ЭКСПРЕСС» 3.2 и какие функции ему доступны",
              1450, 980, BLUE)
    d.add(Node("sys", "package", 270, 115, 960, 780, "ТАРАН-ЭКСПРЕСС 3.2",
               color=BLUE, fill=(16, 19, 30)))
    d.add(Node("player", "actor", 55, 420, 150, 180, "Игрок", color=BLUE,
               title_size=22))
    d.add(Node("store", "actor", 1260, 690, 160, 180, "Локальное\nхранилище",
               color=GOLD, title_size=20))

    prim = [
        ("uc1", "Запустить игру", 185),
        ("uc2", "Толкать пассажиров", 272),
        ("uc3", "Покупать улучшения", 359),
        ("uc4", "Победить босса станции", 446),
        ("uc5", "Открыть «Депо»", 533),
        ("uc6", "Поставить паузу", 620),
        ("uc7", "Сохранить и выйти", 707),
    ]
    for uid, label, y in prim:
        d.add(Node(uid, "usecase", 320, y, 320, 62, label, color=BLUE,
                   fill=(28, 34, 52), title_size=20))

    sec = [
        ("uc8", "Пропустить заставку", 180),
        ("uc9", "Собрать серию", 265),
        ("uc10", "Использовать расходник", 350),
        ("uc11", "Перейти на станцию", 435),
        ("uc12", "Переродиться", 520),
        ("uc13", "Выбрать реликвию", 605),
        ("uc14", "Забрать контракт", 690),
        ("uc15", "Выйти из игры", 775),
    ]
    for uid, label, y in sec:
        d.add(Node(uid, "usecase", 780, y, 350, 58, label, color=PURPLE,
                   fill=(34, 30, 54), title_size=19))

    for uid, _, y in prim:
        d.edge("player", uid, color=(92, 108, 148), width=2, arrow=False)

    # «extend» и «include» между колонками
    d.edge("uc8", "uc1", "«extend»", color=GOLD, width=2, dashed=True,
           kind="dependency", points=[(955, 209), (710, 209), (710, 216), (480, 216)],
           label_pos=0.5)
    d.edge("uc9", "uc2", "«extend»", color=GOLD, width=2, dashed=True,
           kind="dependency", points=[(955, 294), (710, 294), (710, 303), (480, 303)],
           label_pos=0.5)
    d.edge("uc10", "uc3", "«extend»", color=GOLD, width=2, dashed=True,
           kind="dependency", points=[(955, 379), (710, 379), (710, 390), (480, 390)],
           label_pos=0.5)
    d.edge("uc4", "uc11", "«include»", color=GREEN, width=2, dashed=True,
           kind="dependency", points=[(480, 477), (710, 477), (710, 464), (955, 464)],
           label_pos=0.5)
    d.edge("uc5", "uc12", "вкладка", color=GREEN, width=2, dashed=True,
           kind="dependency", points=[(480, 564), (700, 564), (700, 549), (955, 549)],
           label_pos=0.5)
    d.edge("uc5", "uc14", "вкладка", color=GREEN, width=2, dashed=True,
           kind="dependency", points=[(560, 595), (730, 595), (730, 719), (955, 719)],
           label_pos=0.5)
    d.edge("uc12", "uc13", "«include»", color=GREEN, width=2, dashed=True,
           kind="dependency", points=[(1035, 549), (1180, 549), (1180, 634), (1035, 634)],
           label_pos=0.5)
    d.edge("uc7", "uc15", "«include»", color=GREEN, width=2, dashed=True,
           kind="dependency", points=[(480, 738), (700, 738), (700, 804), (955, 804)],
           label_pos=0.5)

    # сохранение и выход связаны с локальным хранилищем
    d.edge("uc7", "store", "save.json", color=GOLD, width=2, arrow=False,
           points=[(480, 738), (480, 860), (1210, 860), (1210, 780)],
           label_pos=0.5)

    d.text("Сплошная линия — ассоциация актора и варианта использования; пунктир — "
           "зависимость «include» (обязательно) или «extend» (при условии).",
           40, 925, 16, MUTED, width=1360)
    return save(d, "01_Диаграмма_вариантов_использования")


# --------------------------------------------------------------- 2. activity
def activity():
    d = begin("UML: диаграмма деятельности",
              "Алгоритм работы игры от запуска до завершения рейса",
              1600, 1050, GREEN)
    d.add(Node("start", "start", 215, 90, 36, 36, color=GREEN))
    box(d, "init", 95, 130, 240, 76, "Запуск приложения",
        ["pygame.init, окно, ассеты"], title_size=21)
    box(d, "intro", 95, 222, 240, 76, "Заставка run_intro()",
        ["видео + титры, пропуск"])
    box(d, "load", 95, 314, 240, 76, "Загрузка прогресса",
        ["load_save, ensure, catch_up"])
    box(d, "g", 95, 406, 240, 76, "Создание g{}",
        ["люди, поезд, босс, жизни"])
    box(d, "frame", 95, 498, 240, 76, "Начало кадра",
        ["dt = clock.tick(60)"])
    box(d, "events", 95, 590, 240, 76, "Обработка событий",
        ["клик, клавиши, окно"])
    dec(d, "pauseq", 95, 682, 240, 90, "Пауза или\nДепо?")
    box(d, "pause", 430, 690, 250, 76, "Оверлей паузы",
        ["Esc, F11, M, выход"], color=BLUE)
    box(d, "update", 430, 800, 250, 76, "Обновление мира",
        ["спавн, поезд, босс, люди"])
    box(d, "draw", 780, 800, 250, 68, "Отрисовка кадра",
        ["HUD, сцена, магазин"])
    dec(d, "exitq", 1110, 790, 230, 90, "Выход?")
    box(d, "end", 1380, 805, 180, 60, "Завершение",
        ["write_save, quit"], color=RED, title_size=20)

    d.edge("start", "init", color=GREEN)
    d.edge("init", "intro", color=GREEN)
    d.edge("intro", "load", color=GREEN)
    d.edge("load", "g", color=GREEN)
    d.edge("g", "frame", color=GREEN)
    d.edge("frame", "events", color=GREEN)
    d.edge("events", "pauseq", color=GREEN)
    d.edge("pauseq", "pause", "да", color=GOLD,
           points=[(215, 727), (430, 727)], label_pos=0.5)
    d.edge("pause", "draw", color=BLUE,
           points=[(680, 727), (730, 727), (730, 780), (905, 780), (905, 800)])
    d.edge("pauseq", "update", "нет", color=GREEN,
           points=[(215, 772), (215, 838), (380, 838), (380, 838), (430, 838)],
           label_pos=0.5)
    d.edge("update", "draw", color=GREEN,
           points=[(680, 838), (780, 838)])
    d.edge("draw", "exitq", color=GREEN,
           points=[(1030, 834), (1070, 834), (1070, 835), (1110, 835)], label_pos=0.5)
    d.edge("exitq", "end", "да", color=RED,
           points=[(1340, 835), (1380, 835)], label_pos=0.5)
    d.edge("exitq", "frame", "нет", color=GREEN,
           points=[(1225, 880), (1225, 940), (60, 940), (60, 536), (95, 536)],
           label_pos=0.15)
    d.text("Ромбами показаны условия, подписи на переходах — результаты проверок. "
           "Пауза и «Депо» останавливают игровое время (dt = 0), но цикл кадров продолжается. "
           "Автосохранение вызывается из update() каждые 12 секунд.",
           40, 950, 16, MUTED, width=1480)
    return save(d, "02_Диаграмма_деятельности")


# ------------------------------------------------------------- 3. sequence
def sequence():
    d = begin("UML: диаграмма последовательности",
              "Один клик по пассажиру: от события мыши до начисления очков и сохранения",
              1750, 960, PURPLE)
    lanes = [
        ("player", 300, 140, "Игрок"),
        ("main", 510, 140, "main()\nконтроллер"),
        ("person", 720, 140, "Person"),
        ("prog", 930, 150, "progression"),
        ("boss", 1150, 140, "Boss"),
        ("hud", 1360, 130, "HUD"),
        ("save", 1560, 140, "save.json"),
    ]
    for lid, x, w, label in lanes:
        d.add(Node(lid, "lifeline", x, 115, w, 64, label, color=PURPLE,
                   fill=(28, 26, 44), font_size=19, extra={"life": 650}))
    cx = {lid: x + w // 2 for lid, x, w, _ in lanes}

    def msg(src, dst, y, label, dashed=False, color=(150, 168, 210)):
        d.edge(src, dst, label, kind="lifeline", color=color, dashed=dashed,
               arrow=True, points=[(cx[src], y), (cx[dst], y)],
               label_pos=0.5)

    msg("player", "main", 230, "1. клик (x, y)")
    msg("main", "main", 285, "2. проверить оверлеи")
    msg("main", "person", 355, "3. rect().collidepoint()")
    msg("person", "main", 405, "4. push(direct) → True/False", dashed=True,
        color=(120, 200, 160))
    msg("main", "prog", 475, "5. on_push(s, falls)")
    msg("main", "main", 525, "6. earn(), combo++, TapFX")
    msg("main", "boss", 600, "7. если босс: hit(dmg)")
    msg("main", "main", 650, "8. крит → smash()")
    msg("main", "save", 720, "9. write_save(s) раз в 12 с")
    msg("main", "hud", 780, "10. draw_hud(s, g, mouse) в конце кадра")

    d.add(Node("alt", "note", 40, 840, 760, 70,
               "alt: клик попал по боссу — hit(dmg) → эффект; награда за пассажира "
               "начисляется позже, когда поезд наезжает на упавшего.",
               color=GOLD, font_size=16))
    d.text("Порядок сообщений соответствует main(): проверка попадания, push(), "
           "начисление награды, затем отрисовка HUD и автосохранение.",
           840, 865, 16, MUTED, width=850)
    return save(d, "03_Диаграмма_последовательности")


# ---------------------------------------------------------------- 4. states
def states():
    d = begin("UML: диаграмма состояний",
              "Состояния игры и переходы между ними",
              1500, 950, GOLD)
    d.add(Node("start", "start", 50, 170, 34, 34, color=GOLD))
    d.add(Node("intro", "state", 110, 140, 180, 64, "Заставка", color=GOLD,
               title_size=22))
    d.add(Node("game", "state_comp", 330, 90, 780, 700, "Игра", color=GOLD,
               fill=(26, 25, 22), title_size=22))
    d.add(Node("run", "state", 370, 150, 190, 64, "Рейс", color=GREEN, title_size=21))
    d.add(Node("fight", "state", 690, 150, 220, 64, "Бой с боссом", color=RED,
               title_size=21))
    d.add(Node("pause", "state", 370, 270, 190, 64, "Пауза", color=BLUE,
               title_size=21))
    d.add(Node("win", "state", 690, 270, 220, 64, "Победа", color=GOLD,
               title_size=21))
    d.add(Node("defeat", "state", 370, 390, 190, 64, "Поражение", color=RED,
               title_size=21))
    d.add(Node("depot", "state", 690, 390, 220, 64, "Депо", color=PURPLE,
               title_size=21))
    d.add(Node("newrun", "state", 370, 520, 190, 60, "Новый забег", color=GREEN,
               title_size=21))
    d.add(Node("rebirth", "state", 690, 520, 220, 60, "Перерождение", color=PURPLE,
               title_size=21))
    d.add(Node("exit", "state", 1200, 600, 180, 64, "Выход", color=RED,
               title_size=21))
    d.add(Node("end", "end", 1274, 720, 32, 32, color=RED))

    d.edge("start", "intro", color=GOLD)
    d.edge("intro", "run", color=GOLD,
           points=[(200, 172), (310, 172), (310, 182), (370, 182)])
    d.edge("run", "fight", color=RED,
           points=[(465, 170), (690, 170)])
    d.edge("fight", "run", color=RED,
           points=[(690, 195), (560, 195)])
    d.edge("run", "pause", color=BLUE,
           points=[(465, 182), (465, 270)])
    d.edge("pause", "run", color=BLUE,
           points=[(500, 270), (500, 182)])
    d.edge("run", "defeat", color=RED,
           points=[(370, 190), (340, 190), (340, 422), (370, 422)])
    d.edge("fight", "win", color=GOLD,
           points=[(800, 214), (800, 270)])
    d.edge("pause", "depot", color=PURPLE,
           points=[(560, 302), (620, 302), (620, 422), (690, 422)])
    d.edge("depot", "pause", color=PURPLE,
           points=[(690, 442), (650, 442), (650, 322), (560, 322)])
    d.edge("defeat", "newrun", color=RED,
           points=[(465, 454), (465, 520)])
    d.edge("depot", "rebirth", color=PURPLE,
           points=[(800, 454), (800, 520)])
    d.edge("rebirth", "newrun", color=GREEN,
           points=[(690, 550), (560, 550)])
    d.edge("newrun", "run", color=GREEN,
           points=[(370, 550), (355, 550), (355, 190), (370, 190)])
    d.edge("pause", "exit", color=RED,
           points=[(370, 302), (320, 302), (320, 700), (1160, 700), (1160, 632), (1200, 632)])
    d.edge("exit", "end", color=RED)

    d.tag("пропуск", 335, 232, 16, GOLD)
    d.tag("порог", 625, 158, 16, RED)
    d.tag("босс ушёл", 625, 232, 16, RED)
    d.tag("Esc", 480, 244, 15, BLUE)
    d.tag("Esc", 530, 258, 15, BLUE)
    d.tag("0 жизней", 345, 360, 16, RED)
    d.tag("20-я станция", 800, 242, 16, GOLD)
    d.tag("P", 620, 365, 15, PURPLE)
    d.tag("подтвердить", 465, 487, 16, RED)
    d.tag("кнопка", 800, 487, 16, PURPLE)
    d.tag("новый рейс", 340, 500, 16, GREEN)
    d.tag("Выйти из игры", 750, 688, 16, RED)

    d.text("Esc — пауза; P — «Депо»; 20-я станция — победа; 0 жизней — поражение. "
           "«Игра» — составное состояние: все переходы меняют флаги g{} и не пересоздают окно. "
           "Выход сохраняет прогресс и завершает процесс.",
           40, 835, 16, MUTED, width=1380)
    return save(d, "04_Диаграмма_состояний")


# ---------------------------------------------------------------- 5. classes
def classes():
    d = begin("UML: диаграмма классов",
              "Основные классы и модули версии 3.2, их данные, методы и связи",
              1700, 1080, BLUE)
    def K(nid, x, y, w, h, title, attrs, methods, color=BLUE, stereo=None,
          fill=(26, 31, 45)):
        d.add(Node(nid, "class", x, y, w, h, title, attrs=attrs, methods=methods,
                   color=color, fill=fill, font_size=18, title_size=22,
                   extra={"stereotype": stereo} if stereo else None))

    d.add(Node("game", "box", 40, 90, 1620, 52,
               "game.py · main() · игровой цикл, события, отрисовка кадра",
               color=GREEN, fill=(24, 36, 30), title_size=21))

    K("world", 40, 170, 300, 200, "World",
      ["t: float", "layers, weather, theme, scale"],
      ["update(dt, kind)", "draw_back()", "draw_front()"], GREEN)
    K("train", 370, 170, 270, 205, "Train",
      ["x, speed: float", "gold: bool", "t, done_t"],
      ["update(dt)", "rect() -> Rect", "draw()"], GOLD)
    K("sound", 670, 170, 270, 190, "SoundKit",
      ["muted, music_key", "sounds: dict"],
      ["play(name, vol)", "toggle()", "start_music()"], RED)
    K("prog", 970, 170, 360, 235, "progression.py",
      ["RELICS, RUN_MODS, CONTRACTS", "meta: dict в save"],
      ["rebirth(s), bp_reward(s)", "click_damage(s, boss)", "catch_up(s)", "track(s, kind, n)"],
      PURPLE, stereo="«module»")
    d.add(Node("save", "note", 1370, 170, 250, 180,
               "save.json / localStorage\nmoney, kills, level,\nlevels{16}, items{6},\nmeta{v:4}, stats{}",
               color=GOLD, font_size=17))

    K("person", 40, 440, 340, 255, "Person",
      ["gold, kind, hp, max_hp", "state, value, entered", "x, y, vx, vy, dir, timer"],
      ["push(direct=False) -> bool", "update(dt)", "rect() -> Rect", "draw(surf, warn=False)"],
      GREEN)
    K("boss", 430, 430, 390, 285, "Boss",
      ["level, name, hp, max_hp", "speed, time_left, flags", "state, shield, hidden",
       "body: Person"],
      ["hit(dmg) -> str", "update(dt)", "rect() -> Rect", "evil_pos(mx, my)"], RED)
    K("effect", 1160, 440, 280, 180, "Effect",
      ["x, y: float", "text, color, t"],
      ["update(dt)", "draw(surf)"], GOLD)

    K("secret", 430, 800, 220, 150, "SecretBoss",
      ["kind: str", "secret = True"], ["draw(surf)"], RED, fill=(34, 30, 32))
    K("flying", 680, 800, 220, 150, "FlyingBoss",
      ["hover_y: float"], ["draw(surf)"], RED, fill=(34, 30, 32))
    K("slime", 930, 800, 260, 175, "SlimeBoss",
      ["shells, fakes", "vuln: float"], ["blocked(x, y)", "draw(surf)"], RED,
      fill=(34, 30, 32))
    K("fake", 1230, 800, 240, 150, "SlimeFake",
      ["hp, x, y", "hit_t"], ["rect()", "draw(surf)"], RED, fill=(34, 30, 32))

    d.add(Node("more", "note", 40, 900, 340, 110,
               "Ещё эффекты: TapFX, Particle,\nCoin, Decal, SkullFly, Acid.\nУ всех update(dt) и draw().",
               color=GOLD, font_size=17))

    # связи
    d.edge("boss", "person", color=BLUE, kind="composition", arrow=False,
           points=[(625, 540), (380, 540)])
    d.edge("train", "person", color=GOLD, kind="dependency", dashed=True,
           points=[(505, 265), (345, 280), (345, 410), (200, 410), (200, 440)],
           label="colliderect()", label_pos=0.5)
    d.edge("boss", "effect", "hit()", color=GOLD, kind="dependency", dashed=True,
           points=[(820, 540), (1160, 540)], label_pos=0.5)
    d.edge("person", "effect", "создаёт", color=GOLD, kind="dependency", dashed=True,
           points=[(210, 695), (210, 760), (1290, 760), (1290, 620)], label_pos=0.5)
    d.edge("prog", "boss", "click_damage()", color=PURPLE, kind="dependency", dashed=True,
           points=[(1150, 405), (1150, 412), (625, 412), (625, 430)], label_pos=0.5)
    d.edge("secret", "boss", color=RED, kind="inherit",
           points=[(540, 800), (540, 715)])
    d.edge("flying", "boss", color=RED, kind="inherit",
           points=[(790, 800), (790, 715)])
    d.edge("slime", "boss", color=RED, kind="inherit",
           points=[(1060, 800), (1060, 715)])
    d.edge("slime", "fake", kind="composition", arrow=False, color=BLUE,
           points=[(1190, 887), (1230, 887)])

    d.text("Наследование: SecretBoss, FlyingBoss и SlimeBoss расширяют Boss. Boss содержит "
           "Person как тело, SlimeBoss — набор SlimeFake. Классы эффектов не хранят игровое "
           "состояние и живут в списках g{}.", 40, 1028, 16, MUTED, width=1620)
    return save(d, "05_Диаграмма_классов")


# ------------------------------------------------------------ 6. flow: loop
def flow_loop():
    d = begin("Блок-схема: основной игровой цикл",
              "Последовательность кадра в main(): события → логика → отрисовка → проверка выхода",
              1580, 1000, GREEN)
    d.add(Node("s", "start", 215, 95, 34, 34, color=GREEN))
    box(d, "init", 95, 140, 240, 62, "Инициализация", ["окно, шрифты, ассеты"])
    box(d, "intro", 95, 232, 240, 62, "Заставка", ["run_intro()"])
    box(d, "load", 95, 324, 240, 62, "Загрузка сейва", ["load_save, ensure, catch_up"])
    box(d, "g", 95, 416, 240, 70, "Создание g{}", ["списки, таймеры, жизни"])
    box(d, "frame", 95, 516, 240, 60, "Новый кадр", ["dt = clock.tick(60)"])
    box(d, "events", 95, 608, 240, 64, "События", ["pygame.event.get()"])
    dec(d, "pause", 95, 704, 240, 100, "Пауза / Депо?")
    box(d, "overlay", 420, 800, 250, 68, "Оверлей", ["dt = 0, меню"], color=BLUE)
    box(d, "update", 420, 700, 250, 90, "Обновление",
        ["спавн, поезд, босс,", "люди, эффекты"])
    box(d, "draw", 770, 700, 250, 68, "Отрисовка", ["сцена + HUD + магазин"])
    dec(d, "quit", 1090, 700, 230, 100, "Выход?")
    box(d, "end", 1390, 720, 170, 60, "Завершение", ["write_save, quit"],
        color=RED, title_size=20)

    d.edge("s", "init", color=GREEN)
    d.edge("init", "intro", color=GREEN)
    d.edge("intro", "load", color=GREEN)
    d.edge("load", "g", color=GREEN)
    d.edge("g", "frame", color=GREEN)
    d.edge("frame", "events", color=GREEN)
    d.edge("events", "pause", color=GREEN)
    d.edge("pause", "overlay", "да", color=GOLD,
           points=[(200, 754), (200, 835), (420, 835)], label_pos=0.5)
    d.edge("overlay", "draw", color=BLUE,
           points=[(670, 835), (730, 835), (730, 790), (895, 790), (895, 768)])
    d.edge("pause", "update", "нет", color=GREEN,
           points=[(335, 754), (380, 754), (380, 737), (420, 737)], label_pos=0.5)
    d.edge("update", "draw", color=GREEN)
    d.edge("draw", "quit", color=GREEN,
           points=[(1020, 734), (1050, 734), (1050, 750), (1090, 750)], label_pos=0.5)
    d.edge("quit", "end", "да", color=RED,
           points=[(1320, 750), (1390, 750)], label_pos=0.5)
    d.edge("quit", "frame", "нет", color=GREEN,
           points=[(1205, 800), (1205, 900), (60, 900), (60, 546), (95, 546)],
           label_pos=0.15)
    d.text("Цикл не создаёт и не уничтожает окно: пауза, «Депо» и смена станции — это "
           "изменение состояния g{} и словаря s. Автосохранение выполняется внутри "
           "update() каждые 12 секунд и отдельной стадией кадра не является.",
           40, 915, 16, MUTED, width=1500)
    return save(d, "06_Блок-схема_основного_цикла")


# ------------------------------------------------------- 7. flow: collision
def flow_collision():
    d = begin("Блок-схема: толчок, столкновение и начисление очков",
              "Клик по игровой зоне, падение пассажира и награда при наезде поезда",
              1650, 1100, GOLD)
    d.add(Node("s1", "start", 140, 95, 32, 32, color=GOLD))
    box(d, "click", 80, 140, 270, 62, "Клик по игровой зоне", ["mx, my; tap = TapFX"])
    dec(d, "coin", 80, 230, 270, 100, "Монета рядом?")
    box(d, "collect", 430, 245, 230, 62, "Собрать монету",
        ["reward, P.on_coin"], color=GREEN)
    d.add(Node("clo", "end", 730, 260, 34, 34, color=GREEN))
    box(d, "radius", 80, 370, 270, 62, "Радиус толчка", ["push_radius() + бонусы"])
    box(d, "loop", 80, 462, 270, 62, "Перебор людей", ["for p in g['people']"])
    dec(d, "hit", 80, 554, 270, 100, "Прямое попадание\nили в радиусе?")
    box(d, "push", 430, 570, 240, 62, "p.push(direct)", ["falls++, state='fall'"])
    dec(d, "fell", 80, 694, 270, 90, "fell > 0?")
    box(d, "onpush", 430, 700, 240, 62, "P.on_push(s, falls)", ["прогресс и квесты"])
    dec(d, "bossq", 430, 800, 260, 100, "Босс в бою\nи в радиусе?")
    box(d, "bosshit", 770, 815, 240, 62, "smash(bs, dmg)", ["hit(dmg), крит"], color=RED)
    box(d, "upd", 1080, 140, 200, 46, "update(): поезд", [], color=MUTED,
        font_size=15, title_size=18)
    dec(d, "train", 1040, 210, 280, 110, "Поезд наехал?")
    box(d, "reward", 1040, 350, 280, 90, "earn(reward), kills++",
        ["10 × 1.35^income × combo", "× gold × train × income_mult"], color=GREEN)
    dec(d, "combo", 1040, 470, 280, 110, "Круглая серия?")
    box(d, "bonus", 1390, 485, 210, 62, "Премия", ["P.on_combo + конфетти"], color=GREEN)
    d.add(Node("end2", "end", 1380, 620, 34, 34, color=GREEN))
    d.add(Node("end4", "end", 1400, 150, 28, 28, color=GREEN))
    d.add(Node("end3", "end", 820, 930, 34, 34, color=GREEN))

    d.edge("s1", "click", color=GOLD)
    d.edge("click", "coin", color=GOLD)
    d.edge("coin", "collect", color=GREEN,
           points=[(215, 280), (430, 276)])
    d.edge("collect", "clo", color=GREEN)
    d.edge("coin", "radius", color=GOLD,
           points=[(215, 280), (215, 370)])
    d.edge("radius", "loop", color=GOLD)
    d.edge("loop", "hit", color=GOLD)
    d.edge("hit", "push", color=GREEN,
           points=[(350, 604), (430, 601)])
    d.edge("push", "train", "падает", color=GOLD,
           points=[(670, 601), (980, 601), (980, 265), (1040, 265)], label_pos=0.32)
    d.edge("hit", "loop", color=MUTED,
           points=[(215, 604), (160, 604), (160, 524), (80, 524)])
    d.edge("loop", "fell", color=GREEN,
           points=[(215, 524), (215, 694)])
    d.edge("fell", "onpush", color=GREEN,
           points=[(350, 739), (430, 731)])
    d.edge("fell", "bossq", color=GREEN,
           points=[(350, 739), (400, 739), (400, 812), (430, 812)])
    d.edge("onpush", "bossq", color=GREEN)
    d.edge("bossq", "bosshit", color=RED,
           points=[(690, 850), (770, 846)])
    d.edge("bossq", "end3", color=GREEN,
           points=[(560, 900), (560, 950), (820, 950)])
    d.edge("bosshit", "end3", color=GREEN,
           points=[(890, 877), (890, 950), (854, 950)])

    d.edge("upd", "train", color=MUTED,
           points=[(1180, 186), (1180, 210)])
    d.edge("train", "reward", "да", color=GREEN,
           points=[(1180, 320), (1180, 350)], label_pos=0.5)
    d.edge("train", "end4", "нет", color=GREEN,
           points=[(1320, 265), (1414, 265), (1414, 178)], label_pos=0.5)
    d.edge("reward", "combo", color=GREEN)
    d.edge("combo", "bonus", "да", color=GREEN,
           points=[(1320, 525), (1390, 516)], label_pos=0.5)
    d.edge("combo", "end2", "нет", color=GREEN,
           points=[(1180, 580), (1180, 637), (1380, 637)], label_pos=0.25)
    d.edge("bonus", "end2", color=GREEN,
           points=[(1495, 547), (1495, 637), (1414, 637)])

    d.tag("да", 390, 252, 15, GREEN)
    d.tag("нет", 240, 350, 15, GOLD)
    d.tag("да", 390, 580, 15, GREEN)
    d.tag("нет", 250, 670, 15, MUTED)
    d.tag("да", 390, 718, 15, GREEN)
    d.tag("нет", 415, 778, 15, GREEN)
    d.tag("да", 730, 830, 15, RED)
    d.tag("нет", 700, 900, 15, GREEN)

    d.text("Награда начисляется не в момент клика, а в update(), когда поезд наезжает "
           "на упавшего: это создаёт тактическую паузу и связывает толчок с расписанием "
           "поездов.", 40, 990, 16, MUTED, width=1540)
    return save(d, "07_Блок-схема_начисления_очков")


# ------------------------------------------------------------ 8. architecture
def architecture():
    d = begin("Архитектура программы",
              "Слои, модули, направление зависимостей и внешние артефакты",
              1520, 1050, BLUE)
    d.add(Node("game", "box", 40, 90, 1440, 64,
               "Точка входа: game.py",
               ["main(), игровой цикл, события, кадр, сущности сцены"],
               color=GREEN, fill=(24, 36, 30), title_size=22, font_size=17))
    d.add(Node("ui", "package", 40, 195, 1440, 180,
               "Представление · taran/ui", color=BLUE, fill=(18, 22, 34)))
    for nid, x, w, title, lines, col in [
        ("hud", 70, 320, "taran/ui/hud.py", ["HUD рейса, сердца,", "полоса босса, «Депо»"], BLUE),
        ("shop", 420, 320, "taran/ui/shop.py", ["«Мастерская»: вкладки,", "карточки, цены"], BLUE),
        ("theme", 770, 320, "taran/ui/theme.py", ["палитра UI_*", "без pygame"], BLUE),
        ("progui", 1120, 330, "prog_ui.py", ["реэкспорт hud", "для старых импортов"], MUTED),
    ]:
        d.add(Node(nid, "box", x, 250, w, 100, title, lines, color=col,
                   fill=(28, 34, 50), title_size=20, font_size=16))

    d.add(Node("logic", "package", 40, 410, 940, 180,
               "Логика и вычисления", color=GOLD, fill=(20, 22, 28)))
    for nid, x, w, title, lines, col in [
        ("prog", 70, 280, "progression.py", ["дерево, реликвии,", "контракты, офлайн-доход"], PURPLE),
        ("logicpy", 370, 280, "taran/logic.py", ["цены, инфляция,", "пороги станций"], GOLD),
        ("saves", 670, 280, "taran/saves.py", ["load_save / write_save", "миграция и защита"], GOLD),
    ]:
        d.add(Node(nid, "box", x, 465, w, 100, title, lines, color=col,
                   fill=(30, 30, 30), title_size=20, font_size=16))
    d.add(Node("store", "box", 1020, 410, 460, 180, "Внешнее хранилище",
               ["save.json на десктопе", "localStorage в браузере и APK",
                "схема meta v4, миграция"], color=GOLD, fill=(38, 34, 24),
               title_size=21, font_size=17))

    d.add(Node("data", "package", 40, 625, 1440, 180,
               "Данные и ресурсы", color=GREEN, fill=(18, 28, 24)))
    for nid, x, w, title, lines, col in [
        ("config", 70, 320, "taran/config.py", ["20 тем, 20 боссов,", "16 улучшений, 6 предметов"], GREEN),
        ("world", 420, 320, "taran/world.py + train.py", ["фон, погода, станция,", "спрайт и класс Train"], GREEN),
        ("creatures", 770, 320, "taran/creatures.py + effects.py", ["спрайты боссов,", "частицы и эффекты"], GREEN),
        ("assets", 1120, 330, "sound/ + intro_frames/", ["18 звуков, музыка,", "45 кадров заставки"], MUTED),
    ]:
        d.add(Node(nid, "box", x, 680, w, 100, title, lines, color=col,
                   fill=(26, 36, 30), title_size=20, font_size=16))

    d.add(Node("platform", "box", 40, 850, 700, 80,
               "Платформа: pygame-ce 2.5.8 · SDL 2.32 · Python 3.12+",
               ["Surface, шрифты, звук, события, масштабирование кадра"],
               color=RED, fill=(34, 24, 24), title_size=20, font_size=16))
    d.add(Node("build", "box", 770, 850, 710, 80,
               "Сборка: mobile/make_mobile.py → pygbag → APK / PWA",
               ["desktop — прямой запуск, APK и PWA — WebAssembly, офлайн"],
               color=PURPLE, fill=(28, 24, 40), title_size=20, font_size=16))

    # направление зависимостей — одна вертикальная ось слева
    d.edge("game", "ui", color=LINE, width=3, dashed=True,
           points=[(260, 154), (260, 195)])
    d.edge("ui", "logic", color=LINE, width=3, dashed=True,
           points=[(260, 375), (260, 410)])
    d.edge("logic", "data", color=LINE, width=3, dashed=True,
           points=[(260, 590), (260, 625)])
    d.edge("data", "platform", color=LINE, width=3, dashed=True,
           points=[(260, 805), (260, 850)])
    d.edge("saves", "store", "JSON", color=GOLD, width=3, dashed=True,
           points=[(950, 515), (1020, 515)], label_pos=0.5)

    d.tag("вызовы", 315, 174, 15, MUTED)
    d.tag("импорт", 315, 392, 15, MUTED)
    d.tag("данные", 315, 607, 15, MUTED)
    d.tag("рендер", 315, 827, 15, MUTED)

    d.text("Стрелки обозначают импорт и вызовы. Модули taran/ui не импортируют game.py "
           "напрямую: связь идёт через bind(game_module) и _sync().", 40, 965, 16, MUTED,
           width=1440)
    return save(d, "08_Схема_архитектуры")


def build_all():
    os.makedirs(OUT, exist_ok=True)
    usecase()
    activity()
    sequence()
    states()
    classes()
    flow_loop()
    flow_collision()
    architecture()


if __name__ == "__main__":
    build_all()
