# -*- coding: utf-8 -*-
"""Все схемы проекта в PNG: архитектура, цикл, рендер, классы, сейвы, сборка."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

from draw import (BG, BLUE, DIM, GOLD, GREEN, LINE, MUTED, PURPLE, RED, SURFACE,
                  SURFACE2, TEXT, Canvas, node, table)  # noqa: E402

OUT = os.path.join(ROOT, "docs", "04_Архитектура", "схемы")


def p(name):
    return os.path.join(OUT, name)


# ---------------------------------------------------------------- 1. модули
def scheme_modules():
    cv = Canvas()
    cv.header("Архитектура приложения", "слои, модули и направление зависимостей (версия 3.2)", BLUE)

    # рамка приложения
    cv.rect(48, 160, 1000, 560, fill=(19, 22, 33), border=LINE, r=18)

    def row(y, h, label, items):
        cv.text(label, 74, y - 24, 14, MUTED, True)
        n = len(items)
        gap = 12
        w = (952 - gap * (n - 1)) // n
        x = 74
        for title, sub, accent in items:
            node(cv, x, y, w, h, title, sub, accent, tsize=18, lsize=14)
            x += w + gap

    row(205, 84, "ВХОД И СЦЕНА", [
        ("game.py  ·  4 651 строка",
         ["главный цикл · события · World · Person · Boss · Train · кадр"], GREEN),
        ("prog_ui.py  ·  13 строк",
         ["тонкий реэкспорт taran.ui.hud для старых импортов"], MUTED),
    ])
    row(330, 92, "ПРЕДСТАВЛЕНИЕ (пакет taran/ui)", [
        ("taran/ui/theme.py", ["15 цветов интерфейса, без pygame"], BLUE),
        ("taran/ui/shop.py  ·  389", ["карточки магазина, вкладки, цены"], BLUE),
        ("taran/ui/hud.py  ·  820", ["HUD рейса, «Депо», атмосфера"], BLUE),
    ])
    row(455, 92, "ЛОГИКА И ДАННЫЕ", [
        ("taran/config.py  ·  343", ["20 тем · 20 боссов · 16 улучшений"], GOLD),
        ("taran/logic.py  ·  87", ["цены, инфляция, пороги станций"], GOLD),
        ("taran/saves.py  ·  50", ["чтение/запись save.json"], GOLD),
        ("progression.py  ·  828", ["дерево · реликвии · контракты"], PURPLE),
    ])
    row(580, 84, "ПЛАТФОРМА", [
        ("pygame-ce 2.5.8 / SDL 2.32", ["Surface · шрифты · звук · события"], RED),
        ("taran/audio.py  ·  183", ["18 эффектов, музыка станций и босса"], RED),
        ("sound/  ·  intro_frames/", ["ассеты рядом с игрой"], RED),
    ])

    # стрелки между слоями
    for x in (330, 720):
        cv.arrow((x, 289), (x, 326), LINE, 2, dashed=True)
        cv.arrow((x, 422), (x, 451), LINE, 2, dashed=True)
        cv.arrow((x, 547), (x, 576), LINE, 2, dashed=True)
    cv.text("импорт", 340, 303, 13, MUTED)
    cv.text("вызовы", 340, 433, 13, MUTED)
    cv.text("данные", 340, 557, 13, MUTED)

    # правая колонка
    cv.text("ВНЕ ПРИЛОЖЕНИЯ", 1080, 176, 15, MUTED, True)
    node(cv, 1080, 205, 472, 150, "Хранилище прогресса",
         ["save.json на десктопе", "localStorage в браузере и APK",
          "одна схема meta v4 для всех платформ"], GOLD, tsize=19)
    node(cv, 1080, 375, 472, 150, "Сборка",
         ["mobile/make_mobile.py → game_app.py",
          "pygbag → WebAssembly → APK / PWA",
          "desktop-версия запускается напрямую"], GREEN, tsize=19)
    node(cv, 1080, 545, 472, 150, "Проверки",
         ["test_smoke.py — 19 проверок",
          "_meta_test.py — 12 утверждений",
          "_prof.py — профиль кадра"], BLUE, tsize=19)

    cv.arrow((1048, 280), (1076, 280), GOLD, 2, dashed=True)
    cv.arrow((1048, 450), (1076, 450), GREEN, 2, dashed=True)
    cv.text("progression.bind(sys.modules[__name__]) убирает циклический импорт: "
            "progression и UI берут шрифты и помощники рисования из game через G.",
            48, 748, 15, DIM, wrap=1500)
    cv.footer("Схема 1 · модульная архитектура")
    return cv.save(p("01_модульная_архитектура.png"))


# ------------------------------------------------------------- 2. цикл игры
def scheme_loop():
    cv = Canvas()
    cv.header("Игровой цикл", "состояния приложения и переходы между ними", GREEN)

    node(cv, 64, 180, 300, 96, "1. Запуск", ["pygame.init · окно · шрифты"], MUTED, tsize=19)
    node(cv, 400, 180, 300, 96, "2. Заставка", ["run_intro: кадры + титры"], MUTED, tsize=19)
    node(cv, 736, 180, 340, 96, "3. Загрузка сейва",
         ["load_save → P.ensure → catch_up"], GOLD, tsize=19)
    node(cv, 1112, 180, 424, 96, "4. РЕЙС",
         ["клик · поезда · комбо · боссы · час пик"], GREEN, tsize=21)

    for x1, x2 in ((364, 396), (700, 732), (1076, 1108)):
        cv.arrow((x1, 228), (x2, 228), LINE, 3)

    node(cv, 1112, 340, 424, 110, "5. Босс станции",
         ["20 боссов · 12 поведений · таймер"], RED, tsize=20)
    node(cv, 620, 340, 460, 110, "6. Победа над боссом",
         ["+награда · следующая станция", "смена темы и декораций"], GOLD, tsize=20)
    node(cv, 64, 340, 500, 110, "7. «Депо» и перерождение",
         ["дерево 27 · реликвии 12 · контракты · достижения",
          "доступно с 9-й станции или после победы"], PURPLE, tsize=20)

    cv.arrow((1310, 276), (1310, 336), LINE, 3)
    cv.text("порог убийств", 1322, 302, 14, MUTED)
    cv.arrow((1108, 395), (1084, 395), GOLD, 3)
    cv.text("босс повержен", 1096, 310, 14, MUTED, anchor="center")
    cv.arrow((616, 395), (568, 395), GOLD, 3)
    cv.text("10-я станция / won", 592, 310, 14, MUTED, anchor="center")

    node(cv, 64, 520, 500, 110, "8. Новый рейс",
         ["модификатор рейса, стартовые бонусы дерева",
          "уровень сбрасывается, ЧТ и реликвии остаются"], GREEN, tsize=20)
    node(cv, 620, 520, 460, 110, "9. Хардкорный забег",
         ["5 жизней · ушёл пассажир — минус жизнь",
          "0 жизней → новый забег, открывается скин"], RED, tsize=19)
    node(cv, 1112, 520, 424, 110, "10. Пауза и настройки",
         ["Esc — пауза, M — звук, F11 — экран"], MUTED, tsize=19)

    cv.arrow((314, 452), (314, 516), PURPLE, 3)
    cv.text("перерождение", 326, 474, 14, MUTED)

    # петля «новый рейс возвращается в игру»
    cv.line((314, 630), (314, 682), PURPLE, 3)
    cv.line((314, 682), (1565, 682), PURPLE, 3)
    cv.line((1565, 682), (1565, 228), PURPLE, 3)
    cv.arrow((1565, 228), (1542, 228), PURPLE, 3)
    cv.text("после перерождения игра начинается заново с 0-й станции", 700, 648, 15, PURPLE)

    cv.text("9 и 10 — режимы внутри рейса, а не отдельные экраны. Прогресс пишется в save.json "
            "каждые 12 секунд и при выходе, а офлайн-доход начисляется в P.catch_up при следующем запуске.",
            64, 728, 15, DIM, wrap=1460)

    cv.footer("Схема 2 · состояния и переходы")
    return cv.save(p("02_игровой_цикл.png"))


# ------------------------------------------------------------ 3. рендеринг
def scheme_render():
    cv = Canvas()
    cv.header("Пайплайн отрисовки", "как логические 1280×720 превращаются в кадр на экране", BLUE)

    stages = [
        ("Логические координаты", ["W×H = 1280×720", "вся механика и баланс"], GOLD),
        ("canvas_buf", ["Surface при масштабе K", "K = 1.0 / 1.5 / 2.0", "в WASM ×0.75"], GREEN),
        ("present()", ["smoothscale в буфер", "буфер переиспользуется"], BLUE),
        ("Окно", ["letterbox по центру", "без искажений"], PURPLE),
        ("Экран", ["SDL2 blit", "цель — 60 кадров/с"], RED),
    ]
    x = 64
    w = 272
    for i, (title, lines, accent) in enumerate(stages):
        node(cv, x, 190, w, 130, title, lines, accent, tsize=18, lsize=15)
        if i < len(stages) - 1:
            cv.arrow((x + w + 4, 255), (x + w + 28, 255), LINE, 3)
        x += w + 32

    cv.text("Слой 1: кэш фона", 64, 360, 16, GOLD, True)
    cv.text("World.cache — до 48 готовых слоёв, ключ = цвета темы + масштаб K. "
            "Фон пересобирается только при смене локации.", 64, 386, 15, DIM, wrap=700)

    cv.text("Слой 2: кэш спрайтов", 790, 360, 16, GREEN, True)
    cv.text("spr_cache и кэш сердечек жизней: готовые Surface переиспользуются, "
            "а не рисуются заново каждый кадр.", 790, 386, 15, DIM, wrap=700)

    # профиль
    cv.rect(64, 460, 700, 300, fill=(19, 22, 33), border=LINE, r=16)
    cv.text("Профиль кадра (cProfile, 340 кадров, 7.97 с)", 86, 476, 18, TEXT, True)
    rows = [
        ("blit (копирование Surface)", "3.35 с", "42 %"),
        ("smoothscale (масштаб кадра)", "1.83 с", "23 %"),
        ("draw_back (фон и погода)", "2.21 с", "накопл."),
        ("draw_atmosphere (HUD)", "0.77 с", "накопл."),
    ]
    y = 520
    for name, t, share in rows:
        cv.text(name, 86, y, 16, DIM)
        cv.text(t, 500, y, 16, TEXT, True)
        cv.text(share, 640, y, 16, GOLD, True)
        y += 46
    cv.text("1 011 572 вызова функций за 340 кадров. Доля — от общих 7,97 с профиля;"
            " draw_back включает время blit.", 86, 706, 14, MUTED, wrap=660)

    # выводы
    cv.rect(800, 460, 736, 300, fill=(19, 22, 33), border=LINE, r=16)
    cv.text("Что сделано по итогам профиля", 822, 476, 18, TEXT, True)
    items = [
        "кадр масштабируется в переиспользуемый буфер;",
        "сердечки жизней кэшируются, а не рисуются заново;",
        "кэш спрайтов очищается реже, слои фона — по ключу;",
        "число одновременных эффектов ограничено;",
        "в WASM меньше снега, капель и звёзд, разрешение ×0.75;",
        "фон и передний план кэшируются отдельными Surface.",
    ]
    y = 516
    for it in items:
        cv.rect(826, y + 7, 7, 7, fill=GREEN, r=3)
        cv.text(it, 846, y, 15, DIM, wrap=660)
        y += 40

    cv.footer("Схема 3 · отрисовка и производительность")
    return cv.save(p("03_рендер_пайплайн.png"))


# --------------------------------------------------------------- 4. классы
def scheme_classes():
    cv = Canvas()
    cv.header("Классы и сущности сцены", "объекты, которые живут внутри игрового кадра g{}", PURPLE)

    node(cv, 64, 190, 380, 130, "World",
         ["фон и погода 6 типов", "слои с кэшем по теме", "станция и вывеска"], GREEN, tsize=22)
    node(cv, 64, 350, 380, 130, "Person",
         ["normal · fat · fly · sprint · armor · bomb",
          "6 типов, у каждого свой hp и награда"], GOLD, tsize=22)
    node(cv, 64, 530, 380, 100, "Train",
         ["проезд, удар по платформе", "золотой поезд ×5"], RED, tsize=22)

    node(cv, 500, 190, 420, 150, "Boss",
         ["hp · speed · time · flags",
          "12 поведений: erratic, shield, regen, ghost,",
          "acid, rage, blink, dodge, tough, frenzy,",
          "heal, timesteal"], RED, tsize=22, lsize=14)
    for i, (t, d) in enumerate((("FlyingBoss", "парит и бросает снаряды"),
                                ("SlimeBoss", "делится и прыгает"),
                                ("SecretBoss", "скрытый босс-сюрприз"))):
        node(cv, 500, 372 + i * 104, 420, 90, t, [d], RED, tsize=18, lsize=14)

    node(cv, 980, 190, 552, 180, "Эффекты и обратная связь",
         ["Effect — всплывающий текст при клике", "TapFX — кольцо и брызги от нажатия",
          "Particle — искры, конфетти, кровь", "Coin — монета, которую ловит игрок",
          "Decal — пятно на путях (до 60 штук)"], BLUE, tsize=20, lsize=15)
    node(cv, 980, 390, 552, 110, "Снаряды и добивания",
         ["SkullFly — череп летит в камеру", "Acid — плевок босса + кислотный оверлей"],
         GOLD, tsize=19, lsize=15)
    node(cv, 980, 520, 552, 100, "Интерфейс (taran/ui/hud.py)",
         ["draw_hud · draw_depot · draw_boss_bar", "4 вкладки «Депо», 3 вкладки магазина"],
         PURPLE, tsize=18, lsize=14)

    cv.arrow((254, 322), (254, 346), GREEN, 2, dashed=True)
    cv.text("место действия", 266, 324, 13, MUTED)
    cv.arrow((444, 530), (444, 484), GOLD, 2, dashed=True)
    cv.text("удар", 456, 498, 13, MUTED)
    cv.arrow((540, 342), (540, 368), RED, 2, dashed=True)
    cv.text("наследует", 552, 344, 13, MUTED)
    cv.arrow((920, 265), (976, 265), RED, 2, dashed=True)
    cv.text("урон", 928, 240, 13, MUTED)

    cv.text("Данные объекта хранятся в полях класса, а состояние кадра — в словаре g{}: "
            "people, effects, particles, rings, taps, coins, decals, skulls, acids.",
            64, 700, 15, DIM, wrap=1460)
    cv.text("Это упрощает сброс рейса: достаточно очистить списки, не пересоздавая окно и ассеты.",
            64, 734, 15, DIM, wrap=1460)

    cv.footer("Схема 4 · сущности сцены")
    return cv.save(p("04_классы_сущностей.png"))


# ---------------------------------------------------------------- 5. сейвы
def scheme_saves():
    cv = Canvas()
    cv.header("Хранение прогресса", "один формат save.json на всех платформах", GOLD)

    steps = [
        ("save.json / localStorage", ["файл рядом с игрой", "или ключ браузера"], GOLD),
        ("taran.saves.load_save", ["терпим к битым файлам", "и старым версиям"], BLUE),
        ("P.ensure + миграция", ["дозаполняет meta v4", "и недостающие ключи"], PURPLE),
        ("P.catch_up", ["офлайн-доход", "за время вне игры"], GREEN),
        ("Игровой цикл", ["меняет money, level,", "kills, items, meta"], TEXT),
        ("write_save", ["каждые 12 с", "и при выходе"], RED),
    ]
    y = 180
    for i, (title, lines, accent) in enumerate(steps):
        node(cv, 64, y, 620, 86, title, lines, accent, tsize=19, lsize=14)
        if i < len(steps) - 1:
            cv.arrow((374, y + 88), (374, y + 108), LINE, 3)
        y += 108

    cv.arrow((686, 560), (740, 560), RED, 3)
    cv.line((740, 560), (740, 300), RED, 3, dashed=True)
    cv.line((740, 300), (690, 300), RED, 3, dashed=True)
    cv.arrow((690, 300), (688, 300), RED, 3)
    cv.text("запись", 750, 430, 14, MUTED)

    # схема данных
    cv.text("Что лежит в save.json", 800, 176, 18, TEXT, True)
    rows = [
        ("Ключ", "Тип", "Назначение"),
        ("money / earned", "int", "баланс и доход за всё время"),
        ("kills / level / won", "int, bool", "рейс: станция, победа"),
        ("levels{16}", "dict", "уровни базовых улучшений"),
        ("items{6}", "dict", "заряды расходников"),
        ("meta{v:4}", "dict", "дерево, реликвии, контракты"),
        ("meta.tree{27}", "dict", "уровни узлов депо"),
        ("stats{}", "dict", "толчки, боссы, монеты, комбо"),
        ("income_rate / last_seen", "float", "офлайн-доход"),
    ]
    table(cv, 800, 210, [230, 130, 430], rows, row_h=46, size=15)

    cv.rect(800, 690, 760, 100, fill=(24, 28, 41), border=LINE, r=12)
    cv.text("Обратная совместимость: загрузка читает старый файл, дополняет его новыми "
            "ключами и пишет версию схемы (_ok, meta.v). Сейв 3.0 открывается в 3.2 без потерь.",
            818, 706, 15, DIM, wrap=724)

    cv.footer("Схема 5 · сохранение и миграция")
    return cv.save(p("05_сохранение_прогресса.png"))


# --------------------------------------------------------------- 6. сборка
def scheme_build():
    cv = Canvas()
    cv.header("Конвейер сборки", "один исходник — три платформы", GREEN)

    node(cv, 64, 180, 300, 160, "Исходники",
         ["game.py", "progression.py", "taran/", "sound/ + intro_frames/"],
         GOLD, tsize=20, lsize=15)
    node(cv, 404, 180, 340, 160, "make_mobile.py",
         ["точечные патчи game.py:", "окно 1280×720, шрифты из папки,",
          "localStorage, async-цикл"], BLUE, tsize=20, lsize=15)
    node(cv, 784, 180, 300, 160, "game_app.py",
         ["готовая веб-версия", "для pygbag"], BLUE, tsize=20, lsize=15)
    node(cv, 1124, 180, 412, 160, "pygbag → WebAssembly",
         ["CPython-WASM + pygame-ce", "архив игры + index.html",
          "build/web ≈ 45 МБ"], GREEN, tsize=20, lsize=15)

    cv.arrow((368, 260), (400, 260), LINE, 3)
    cv.arrow((748, 260), (780, 260), LINE, 3)
    cv.arrow((1088, 260), (1120, 260), LINE, 3)

    node(cv, 700, 400, 480, 190, "APK для Android",
         ["build_apk.py: aapt2 → d8 → apksigner", "pygame-архив внутрь assets",
          "TaranExpress_v3.2.apk ≈ 33 МБ", "minSdk 23 · targetSdk 33",
          "работает офлайн, внешних запросов нет"], RED, tsize=21, lsize=15)

    node(cv, 1200, 400, 336, 190, "PWA для сайта",
         ["make_pwa.py: manifest, иконки", "service worker кэширует игру",
          "установка из Chrome / Safari", "нужен HTTPS и MIME .wasm"],
         PURPLE, tsize=21, lsize=14)

    node(cv, 64, 400, 590, 190, "Десктопная версия",
         ["py game.py — окно pygame-ce", "Python 3.14.5 + pygame-ce 2.5.8",
          "save.json рядом с игрой", "полный экран, F11, мышь и клавиатура"],
         GREEN, tsize=21, lsize=15)

    cv.arrow((1150, 344), (1150, 396), RED, 3)
    cv.arrow((1400, 344), (1400, 396), GREEN, 3)
    cv.text("веб-сборка", 1164, 362, 14, MUTED)

    # шаги rebuild
    cv.rect(64, 630, 1472, 150, fill=(19, 22, 33), border=LINE, r=16)
    cv.text("py mobile/rebuild.py — шесть шагов одной командой", 86, 646, 18, TEXT, True)
    steps = ["setup.py", "make_mobile", "pygbag", "prepare_offline", "make_pwa", "build_apk"]
    x = 86
    for i, s in enumerate(steps):
        cv.rect(x, 690, 214, 52, fill=SURFACE2, border=LINE, r=10)
        cv.text(s, x + 107, 716, 16, TEXT, True, anchor="center")
        if i < len(steps) - 1:
            cv.arrow((x + 216, 716), (x + 240, 716), LINE, 2)
        x += 244

    cv.footer("Схема 6 · сборка под три платформы")
    return cv.save(p("06_конвейер_сборки.png"))


# ----------------------------------------------------------- 7. мета-прогресс
def scheme_meta():
    cv = Canvas()
    cv.header("Мета-прогресс: второй слой игры", "забег заканчивается — наследие остаётся", PURPLE)

    node(cv, 64, 190, 430, 150, "Откуда берутся ЧТ",
         ["bp_reward = (доход/20000)^0.62", "+ станции ×2.2 + боссы ×2.0",
          "+ эпоха ×6 + премия за 5 станций", "× bp_mult, +3 % за перерождение"],
         GOLD, tsize=19, lsize=14)

    node(cv, 570, 190, 400, 150, "Перерождение",
         ["доступно с 9-й станции", "или после победы",
          "сбрасывает рейс, сохраняет ЧТ"], PURPLE, tsize=20, lsize=14)

    node(cv, 1046, 190, 490, 150, "Модификатор нового рейса",
         ["6 вариантов: спокойный, туман, праздник,",
          "забастовка, гонка, ночная смена"], GREEN, tsize=19, lsize=14)

    cv.arrow((494, 265), (566, 265), GOLD, 3)
    cv.arrow((970, 265), (1042, 265), PURPLE, 3)

    cards = [
        ("Дерево бонусов · 27 узлов", ["Тяга — экономика: 9 узлов",
                                       "Броня — бой и урон: 9 узлов",
                                       "Логистика — автоматизация: 9"], BLUE),
        ("Реликвии · 12 штук",
         ["выбор 1 из 3 после перерождения",
          "до 5 уровней, редкость 70/25/5 %"], GREEN),
        ("Контракты · 3 слота",
         ["6 типов целей, награда в ЧТ",
          "масштабируются по рангу"], GOLD),
        ("Достижения · 24 вехи",
         ["толчки, боссы, станции, деньги,",
          "комбо, монеты, реликвии, депо"], RED),
        ("Офлайн-доход",
         ["от 25 % до 8 часов",
          "растёт с «Ночной сменой»"], PURPLE),
        ("Автоматизация",
         ["автотолчок и автозакупка",
          "открываются в логистике"], GREEN),
    ]
    x0, y0, w, h = 64, 396, 480, 132
    for i, (title, lines, accent) in enumerate(cards):
        col, row = i % 3, i // 3
        node(cv, x0 + col * 504, y0 + row * 156, w, h, title, lines, accent,
             tsize=19, lsize=14)

    cv.text("Постоянные бонусы складываются: доход, урон, жизни, цены, стартовые деньги, "
            "поезда и офлайн умножаются, а не заменяют друг друга.",
            64, 760, 15, DIM, wrap=1460)
    cv.footer("Схема 7 · мета-прогресс")
    return cv.save(p("07_мета_прогресс.png"))


# ---------------------------------------------------------- 8. тестирование
def scheme_testing():
    cv = Canvas()
    cv.header("Процесс тестирования", "от правки кода до проверки на телефоне", RED)

    levels = [
        ("1. Дымовой тест", ["19 проверок", "test_smoke.py"], GREEN),
        ("2. Мета-тест", ["12 утверждений", "_meta_test.py"], GREEN),
        ("3. Проверка контента", ["боссы, темы,", "предметы, реликвии"], BLUE),
        ("4. Профилирование", ["cProfile, FPS", "_prof.py, bench"], GOLD),
        ("5. Сборка и APK", ["установка", "прогон на телефоне"], PURPLE),
    ]
    x = 64
    for i, (title, lines, accent) in enumerate(levels):
        node(cv, x, 190, 280, 110, title, lines, accent, tsize=17, lsize=14)
        if i < len(levels) - 1:
            cv.arrow((x + 284, 245), (x + 302, 245), LINE, 2)
        x += 302

    node(cv, 64, 318, 1464, 84, "6. Юзабилити-тест — 5–8 игроков",
         ["протокол сессии, наблюдение, опрос после игры; результаты — в документе «Процесс разработки»"],
         RED, tsize=18, lsize=14)

    # цикл дефекта
    cv.text("Жизненный цикл дефекта", 64, 426, 20, TEXT, True)
    steps = [("Найден", "тест или игрок"), ("BR-номер", "шаги и окружение"),
             ("Причина", "код и данные"), ("Исправление", "минимальная правка"),
             ("Ретест", "тот же сценарий"), ("Регресс", "весь smoke-набор")]
    x = 64
    for i, (t, d) in enumerate(steps):
        cv.rect(x, 458, 236, 96, fill=SURFACE2, border=LINE, r=12)
        cv.text(t, x + 118, 488, 18, TEXT, True, anchor="center")
        cv.text(d, x + 118, 520, 13, DIM, anchor="center")
        if i < len(steps) - 1:
            cv.arrow((x + 240, 506), (x + 254, 506), LINE, 2)
        x += 254

    # метрики
    cv.rect(64, 594, 720, 220, fill=(19, 22, 33), border=LINE, r=16)
    cv.text("Метрики качества", 86, 610, 18, TEXT, True)
    mets = [
        ("Пройдено автоматических проверок", "31 / 31"),
        ("Медианное время кадра (headless)", "18.4 мс"),
        ("Средний FPS в замере", "48.3"),
        ("Утечки памяти в 10-минутном прогоне", "не выявлены"),
        ("Крэши в автоматических прогонах", "0"),
    ]
    yy = 648
    for k, v in mets:
        cv.text(k, 86, yy, 15, DIM)
        cv.text(v, 736, yy, 15, GREEN, True, anchor="topright")
        yy += 34

    cv.rect(820, 594, 708, 220, fill=(19, 22, 33), border=LINE, r=16)
    cv.text("Где ищем проблемы", 842, 610, 18, TEXT, True)
    risks = [
        "стыки HUD: наложения панелей и подсказок;",
        "сборка APK: подпись, размер, установка;",
        "производительность в WASM и на слабых телефонах;",
        "миграция старых сейвов и офлайн-доход;",
        "баланс: доход, цены, сложность боссов.",
    ]
    yy = 648
    for it in risks:
        cv.rect(848, yy + 7, 7, 7, fill=GOLD, r=3)
        cv.text(it, 866, yy, 15, DIM, wrap=640)
        yy += 32

    cv.footer("Схема 8 · тестирование")
    return cv.save(p("08_процесс_тестирования.png"))


def main():
    made = [scheme_modules(), scheme_loop(), scheme_render(), scheme_classes(),
            scheme_saves(), scheme_build(), scheme_meta(), scheme_testing()]
    for m in made:
        print("ok", os.path.basename(m))


if __name__ == "__main__":
    main()
