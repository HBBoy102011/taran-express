# -*- coding: utf-8 -*-
"""Графики для документов и презентации. Все цифры — из реального проекта."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

from draw import (BG, BLUE, DIM, GOLD, GREEN, LINE, MUTED, PURPLE, RED, SURFACE,  # noqa: E402
                  SURFACE2, TEXT, Canvas, bar_chart, donut, font, node, table)
import pygame  # noqa: E402

OUT = os.path.join(ROOT, "docs", "материалы")


def p(name):
    return os.path.join(OUT, name)


def _card(cv, x, y, w, h, title, lines, accent):
    node(cv, x, y, w, h, title, lines, accent, tsize=19, lsize=15)


def chart_versions():
    cv = Canvas(1600, 900)
    cv.header("История версий", "что появлялось в игре от 3.0 до текущей 3.2", GOLD)

    axis_y = 300
    pygame.draw.line(cv.s, LINE, (120, axis_y), (1480, axis_y), 3)
    marks = [(300, "3.0", GOLD), (790, "3.1", BLUE), (1290, "3.2", GREEN)]
    for x, ver, col in marks:
        pygame.draw.circle(cv.s, col, (x, axis_y), 13)
        cv.text(ver, x, axis_y - 62, 30, col, True, anchor="center")

    cards = [
        ("Перерождение и мета", [
            "дерево 21 узел в 3 ветках",
            "12 реликвий, выбор 1 из 3",
            "контракты и 24 достижения",
            "6 модификаторов рейса",
            "офлайн-доход, автотолчок"], GOLD),
        ("Больше контента и порядок", [
            "дерево выросло до 27 узлов",
            "миграция сейвов 3.0 без потерь",
            "«Депо» на весь экран",
            "сводки и прогресс во вкладках",
            "кэш кадра и спрайтов"], BLUE),
        ("Единый интерфейс", [
            "HUD разбит на три зоны",
            "магазин: вкладки и «пилюли»",
            "Shift + клик — купить 10",
            "клавиши 1–4 в «Депо»",
            "подсказки не обрезаются"], GREEN),
    ]
    x0, w = 90, 450
    for i, (title, lines, col) in enumerate(cards):
        x = x0 + i * 480
        _card(cv, x, 360, w, 210, title, lines, col)
        cv.line((x + w // 2, axis_y + 14), (x + w // 2, 356), col, 2, dashed=True)

    cv.text("3.2 — текущая версия: функционально завершена, идёт тестирование и полировка. "
            "Модули вынесены в пакет taran/, game.py сократился до 4 651 строки.",
            90, 640, 16, DIM, wrap=1420)

    # нижняя полоса фактов
    facts = [("20", "станций"), ("20", "боссов"), ("24", "достижения"),
             ("12", "реликвий"), ("27", "узлов дерева"), ("12", "скинов")]
    x = 90
    for num, lab in facts:
        cv.rect(x, 710, 220, 110, fill=(19, 22, 33), border=LINE, r=14)
        cv.text(num, x + 110, 748, 34, TEXT, True, anchor="center")
        cv.text(lab, x + 110, 792, 15, MUTED, anchor="center")
        x += 234

    cv.footer("График 1 · история версий")
    return cv.save(p("01_версии.png"))


def chart_perf():
    cv = Canvas(1600, 760)
    cv.header("Профиль кадра", "cProfile: 340 кадров за 7,97 с, 1 011 572 вызова", RED)

    rows = [("blit — копирование Surface", 3.349), ("draw_back — фон и погода", 2.212),
            ("smoothscale — масштаб кадра", 1.828), ("present — вывод кадра", 2.067),
            ("draw_atmosphere — HUD и эффекты", 0.772)]
    top = max(v for _, v in rows)
    y = 190
    for name, val in rows:
        cv.text(name, 64, y + 6, 17, DIM)
        bw = int(760 * val / top)
        cv.rect(64, y + 34, 760, 22, fill=SURFACE2, r=11)
        cv.rect(64, y + 34, max(8, bw), 22, fill=RED if val == top else GOLD, r=11)
        cv.text("%.2f с" % val, 840, y + 44, 15, TEXT, True, anchor="midleft")
        y += 82

    cv.text("Время накопительное: draw_back и present включают вложенные вызовы blit.", 
            64, 600, 14, MUTED)

    cv.rect(980, 180, 556, 300, fill=(19, 22, 33), border=LINE, r=16)
    cv.text("Замер игрового цикла", 1002, 196, 19, TEXT, True)
    stats = [("Кадров за 10 секунд", "512"), ("Средний FPS", "48,3"),
             ("Медиана кадра", "18,37 мс"), ("95-й процентиль", "26,93 мс"),
             ("Худший кадр (старт)", "168 мс")]
    yy = 238
    for k, v in stats:
        cv.text(k, 1002, yy, 15, DIM)
        cv.text(v, 1510, yy, 15, GREEN, True, anchor="topright")
        yy += 38
    cv.text("headless-режим SDL dummy, 10 секунд с кликами по платформе",
            1002, 436, 13, MUTED)

    cv.rect(980, 500, 556, 180, fill=(19, 22, 33), border=LINE, r=16)
    cv.text("Что уже оптимизировано", 1002, 516, 18, TEXT, True)
    for i, s in enumerate(["кадр масштабируется в переиспользуемый буфер",
                           "кэш сердечек и спрайтов вместо перерисовки",
                           "лимит одновременных эффектов"]):
        cv.rect(1006, 556 + i * 38 + 7, 7, 7, fill=GREEN, r=3)
        cv.text(s, 1024, 556 + i * 38, 15, DIM)

    cv.footer("График 2 · производительность")
    return cv.save(p("02_производительность.png"))


def chart_code():
    cv = Canvas(1600, 820)
    cv.header("Объём кода по модулям", "всего 7 395 строк: игра, мета-прогресс и интерфейс", BLUE)

    items = [("game.py", 4651), ("progression.py", 828), ("taran/ui/hud.py", 820),
             ("taran/ui/shop.py", 389), ("taran/config.py", 343),
             ("taran/audio.py", 183), ("taran/logic.py", 87),
             ("taran/saves.py", 50), ("taran/ui/theme.py", 27)]
    bar_chart(cv, 64, 190, 960, 500, items, maxv=4651, color=BLUE, fmt="{:,.0f}".replace(",", " "))

    cv.rect(1060, 190, 476, 300, fill=(19, 22, 33), border=LINE, r=16)
    cv.text("Тесты и инструменты", 1082, 206, 18, TEXT, True)
    tests = [("test_smoke.py", "19 проверок"), ("_meta_test.py", "12 утверждений"),
             ("docs/_tools/verify_content.py", "33 проверки"),
             ("docs/_tools/bench_fps.py", "FPS-замер")]
    yy = 246
    for k, v in tests:
        cv.text(k, 1082, yy, 14, DIM)
        cv.text(v, 1510, yy, 14, GREEN, True, anchor="topright")
        yy += 52

    cv.rect(1060, 520, 476, 170, fill=(19, 22, 33), border=LINE, r=16)
    cv.text("Как считалось", 1082, 536, 18, TEXT, True)
    cv.text("wc -l по файлам проекта без кэша и сборок. game.py — 4 651 строка: "
            "мир, сущности, боссы, отрисовка кадра.",
            1082, 572, 14, DIM, wrap=432)

    cv.footer("График 3 · объём кода")
    return cv.save(p("03_объём_кода.png"))


def chart_checks():
    cv = Canvas(1600, 720)
    cv.header("Автоматические проверки", "64 проверки в трёх наборах — все проходят", GREEN)

    suites = [("test_smoke.py", 19, "игровой цикл, толчки, поезда, предметы, магазин"),
              ("_meta_test.py", 12, "перерождение, дерево, реликвии, контракты"),
              ("verify_content.py", 33, "все темы, боссы, скины, сейвы, миграция")]
    y = 190
    for name, n, desc in suites:
        cv.text(name, 64, y, 20, TEXT, True)
        cv.rect(64, y + 36, 900, 34, fill=SURFACE2, r=17)
        cv.rect(64, y + 36, 900, 34, fill=GREEN, r=17)
        cv.text("%d / %d" % (n, n), 990, y + 34, 17, GREEN, True, anchor="midleft")
        cv.text(desc, 64, y + 76, 14, MUTED)
        y += 140

    cv.rect(1080, 190, 456, 260, fill=(19, 22, 33), border=LINE, r=16)
    cv.text("Итого", 1102, 206, 19, TEXT, True)
    cv.text("64", 1308, 290, 76, GREEN, True, anchor="center")
    cv.text("проверки пройдены", 1308, 340, 16, DIM, anchor="center")
    cv.text("0 провалов", 1308, 384, 16, GOLD, True, anchor="center")
    cv.text("прогон 09.11.2026", 1308, 416, 13, MUTED, anchor="center")

    cv.rect(1080, 480, 456, 160, fill=(19, 22, 33), border=LINE, r=16)
    cv.text("Чего автоматика не ловит", 1102, 496, 17, TEXT, True)
    cv.text("ощущение баланса, читаемость подсказок, удобство на телефоне — "
            "это задачи юзабилити-теста и ручного прогона.",
            1102, 530, 14, DIM, wrap=412)

    cv.footer("График 4 · проверки")
    return cv.save(p("04_проверки.png"))


def chart_content():
    cv = Canvas(1600, 820)
    cv.header("Сколько контента в игре", "цифры из taran/config.py и progression.py", PURPLE)

    items = [("Станции (темы)", 20), ("Боссы", 20), ("Узлы дерева", 27),
             ("Достижения", 24), ("Улучшения магазина", 16), ("Реликвии", 12),
             ("Скины", 12), ("Расходники", 6), ("Модификаторы рейса", 6)]
    bar_chart(cv, 64, 190, 1000, 520, items, maxv=27, color=PURPLE)

    cv.rect(1100, 190, 436, 240, fill=(19, 22, 33), border=LINE, r=16)
    cv.text("Редкости реликвий", 1122, 206, 18, TEXT, True)
    donut(cv, 1240, 330, 70, [("обычная", 70, GREEN), ("редкая", 25, GOLD), ("эпик", 5, RED)], 26,
          hole=SURFACE)
    yy = 280
    for lab, val, col in (("обычная", "70 %", GREEN), ("редкая", "25 %", GOLD), ("эпик", "5 %", RED)):
        cv.rect(1340, yy + 6, 9, 9, fill=col, r=4)
        cv.text(lab, 1358, yy, 15, DIM)
        cv.text(val, 1510, yy, 15, TEXT, True, anchor="topright")
        yy += 34

    cv.rect(1100, 460, 436, 250, fill=(19, 22, 33), border=LINE, r=16)
    cv.text("Балансовые константы", 1122, 476, 18, TEXT, True)
    rows = [("Жизни в хардкоре", "5"), ("Убийств до финального босса", "10 000"),
            ("Делитель инфляции", "10 000"), ("Максимум реликвии", "5 уровней"),
            ("Платформа", "1280 × 720")]
    yy = 516
    for k, v in rows:
        cv.text(k, 1122, yy, 14, DIM)
        cv.text(v, 1510, yy, 14, GOLD, True, anchor="topright")
        yy += 36

    cv.footer("График 5 · контент")
    return cv.save(p("05_контент.png"))


def chart_defects():
    cv = Canvas(1600, 700)
    cv.header("Дефекты по категориям", "12 записей в реестре: 11 закрыты, 1 открыт", GOLD)

    donut(cv, 380, 360, 170, [("Интерфейс", 7, BLUE), ("Производительность", 3, GOLD),
                              ("Данные", 1, GREEN), ("Релиз", 1, RED)], 58, hole=BG)
    cv.text("12", 380, 340, 56, TEXT, True, anchor="center")
    cv.text("дефектов", 380, 392, 16, MUTED, anchor="center")

    legend = [("Интерфейс и HUD", 7, BLUE), ("Производительность", 3, GOLD),
              ("Данные и сейвы", 1, GREEN), ("Перед публикацией", 1, RED)]
    y = 250
    for lab, n, col in legend:
        cv.rect(700, y + 8, 12, 12, fill=col, r=5)
        cv.text(lab, 724, y, 18, TEXT)
        cv.text(str(n), 1080, y, 18, col, True, anchor="topright")
        y += 58

    cv.rect(1160, 230, 376, 330, fill=(19, 22, 33), border=LINE, r=16)
    cv.text("Статусы", 1182, 246, 18, TEXT, True)
    st = [("Закрыт", "11", GREEN), ("Открыт", "1", RED), ("Отложен", "0", MUTED)]
    yy = 292
    for lab, n, col in st:
        cv.text(lab, 1182, yy, 16, DIM)
        cv.text(n, 1504, yy, 16, col, True, anchor="topright")
        yy += 44
    cv.text("Открытый дефект: targetSdk 33 при требовании\nGoogle Play 36 — блокирует публикацию в сторе,\n"
            "но не мешает установке APK вручную.",
            1182, 430, 14, MUTED, wrap=330)

    cv.text("Категории взяты из фактических правок README: наложения HUD, обрезанные подсказки, "
            "просвечивающая панель, тост поверх сцены, дерево вне панели, миграция сейвов, "
            "лишние поверхности и эффекты каждый кадр.",
            64, 600, 15, DIM, wrap=1440)

    cv.footer("График 6 · дефекты")
    return cv.save(p("06_дефекты.png"))


def main():
    made = [chart_versions(), chart_perf(), chart_code(), chart_checks(),
            chart_content(), chart_defects()]
    for m in made:
        print("ok", os.path.basename(m))


if __name__ == "__main__":
    main()
