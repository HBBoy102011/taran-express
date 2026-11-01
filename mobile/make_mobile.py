# -*- coding: utf-8 -*-
"""Собирает мобильную версию игры из десктопного game.py.

Скрипт читает ../game.py и точечно патчит его под pygame-web (pygbag):
  * окно фиксированного размера 1280x720 вместо полноэкранного режима Windows;
  * шрифты берутся из папки fonts (в WebAssembly системных шрифтов нет);
  * сохранение — localStorage браузера, файл save.json остаётся запасным вариантом;
  * игровой цикл становится async, как требует pygbag;
  * вместо клавиш Esc/F11/F10 — экранная кнопка паузы;
  * кадры заставки ищутся в распакованном архиве.

Результат — mobile/game_app.py. Запуск:
    py mobile/make_mobile.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "game.py")
DST = os.path.join(HERE, "game_app.py")


def patch(text, old, new, label):
    """Заменяет ровно одно вхождение и падает, если исходник изменился."""
    n = text.count(old)
    if n != 1:
        sys.exit(f"ПАТЧ '{label}': ожидалось 1 вхождение, найдено {n}. "
                 f"game.py изменился — правь make_mobile.py.")
    return text.replace(old, new)


src = open(SRC, encoding="utf-8").read()

# ---------- 1. import asyncio ----------
src = patch(src, "import pygame\n", "import asyncio\n\nimport pygame\n", "import asyncio")

# ---------- 2. окно 1280x720 без полноэкранного режима ----------
src = patch(
    src,
    "set_scale(FORCE_K or scale_fullscreen())\n"
    "win = make_window(fullscreen)\n"
    "fullscreen = bool(win.get_flags() & pygame.FULLSCREEN)\n",
    '# мобильная версия: фиксированный размер полотна, pygbag сам растягивает его на экран\n'
    "set_scale(1.0)\n"
    "win = pygame.display.set_mode((WP, HP))\n"
    "fullscreen = False\n",
    "окно",
)

# ---------- 3. шрифты из комплекта (в WASM нет системных) ----------
src = patch(
    src,
    'FN = "arial,dejavusans,liberationsans"\n',
    'FN = "arial,dejavusans,liberationsans"\n'
    "# шрифты лежат рядом с игрой: в браузере SysFont не находит системных шрифтов,\n"
    "# а без кириллицы весь русский текст превратился бы в квадраты\n"
    '_HERE = os.path.dirname(os.path.abspath(__file__))\n'
    '_FONT_REG = os.path.join(_HERE, "fonts", "DejaVuSans.ttf")\n'
    '_FONT_BOLD = os.path.join(_HERE, "fonts", "DejaVuSans-Bold.ttf")\n'
    "\n"
    "\n"
    "def mfont(size, bold=False):\n"
    "    try:\n"
    '        return pygame.font.Font(_FONT_BOLD if bold else _FONT_REG, px(size))\n'
    "    except (OSError, pygame.error):\n"
    '        return pygame.font.SysFont(FN, px(size), bold=bold)\n',
    "шрифты-пути",
)

src = patch(
    src,
    "    f_big = pygame.font.SysFont(FN, px(46), bold=True)\n"
    "    f_money = pygame.font.SysFont(FN, px(34), bold=True)\n"
    "    f_mid = pygame.font.SysFont(FN, px(20), bold=True)\n"
    "    f_small = pygame.font.SysFont(FN, px(15))\n",
    "    f_big = mfont(46, True)\n"
    "    f_money = mfont(34, True)\n"
    "    f_mid = mfont(20, True)\n"
    "    f_small = mfont(15)\n",
    "шрифты HUD",
)

src = patch(
    src,
    '        fonts["big"] = pygame.font.SysFont(FN, px(86), bold=True)\n'
    '        fonts["mid"] = pygame.font.SysFont(FN, px(36), bold=True)\n'
    '        fonts["sml"] = pygame.font.SysFont(FN, px(16))\n',
    '        fonts["big"] = mfont(86, True)\n'
    '        fonts["mid"] = mfont(36, True)\n'
    '        fonts["sml"] = mfont(16)\n',
    "шрифты заставки",
)

# ---------- 4. сохранение в localStorage ----------
src = patch(
    src,
    "def load_save():\n",
    "def _ls():\n"
    '    """Хранилище браузера: в WebAssembly обычная запись в файл не сохраняется."""\n'
    "    try:\n"
    "        import platform\n"
    "        return platform.window.localStorage\n"
    "    except Exception:\n"
    "        return None\n"
    "\n"
    "\n"
    "def _save_text():\n"
    "    ls = _ls()\n"
    "    if ls is not None:\n"
    "        try:\n"
    '            raw = ls.getItem("train_game_v1")\n'
    "            if raw:\n"
    "                return str(raw)\n"
    "        except Exception:\n"
    "            pass\n"
    "    try:\n"
    '        with open(SAVE, "r", encoding="utf-8") as f:\n'
    "            return f.read()\n"
    "    except OSError:\n"
    "        return None\n"
    "\n"
    "\n"
    "def _put_text(txt):\n"
    "    ls = _ls()\n"
    "    if ls is not None:\n"
    "        try:\n"
    '            ls.setItem("train_game_v1", txt)\n'
    "            return\n"
    "        except Exception:\n"
    "            pass\n"
    "    with open(SAVE, \"w\", encoding=\"utf-8\") as f:\n"
    "        f.write(txt)\n"
    "\n"
    "\n"
    "def load_save():\n",
    "load_save: хранилище",
)

src = patch(
    src,
    '        with open(SAVE, "r", encoding="utf-8") as f:\n'
    "            d = json.load(f)\n",
    "        d = json.loads(_save_text())\n",
    "load_save: чтение",
)

src = patch(
    src,
    '        with open(SAVE, "w", encoding="utf-8") as f:\n'
    "            json.dump(s, f)\n",
    "        _put_text(json.dumps(s))\n",
    "write_save: запись",
)

# ---------- 5. кадры заставки в архиве pygbag ----------
src = patch(
    src,
    'INTRO_FRAMES_DIR = os.path.join(getattr(sys, "_MEIPASS", _BASE_DIR), "intro_frames")\n',
    "def _frames_dir():\n"
    '    """В exe кадры лежат рядом с распакованными файлами, в браузере — прямо в архиве."""\n'
    '    for c in ("intro_frames", os.path.join(_BASE_DIR, "intro_frames")):\n'
    "        try:\n"
    '            if any(n.endswith(".png") for n in os.listdir(c)):\n'
    "                return c\n"
    "        except OSError:\n"
    "            pass\n"
    '    return os.path.join(_BASE_DIR, "intro_frames")\n'
    "\n"
    "\n"
    "INTRO_FRAMES_DIR = _frames_dir()\n",
    "папка кадров",
)

# ---------- 6. async: заставка ----------
src = patch(src, "def run_intro():\n", "async def run_intro():\n", "run_intro: async")
src = patch(
    src,
    "    while running and t < end_t:\n        dt = min(clock.tick(60) / 1000, 0.05)\n",
    "    while running and t < end_t:\n"
    "        dt = min(clock.tick(60) / 1000, 0.05)\n"
    "        await asyncio.sleep(0)          # отдаём кадр браузеру, иначе вкладка зависнет\n",
    "run_intro: await",
)

src = patch(
    src,
    "        if running and t < run_dur:\n"
    '            txt_a(canvas, "пропустить — любая клавиша или клик", fonts["sml"],\n',
    "        if running and t < run_dur:\n"
    '            txt_a(canvas, "пропустить — тап по экрану", fonts["sml"],\n',
    "заставка: подсказка",
)

# ---------- 7. async: основной цикл ----------
src = patch(src, "def main():\n", "async def main():\n", "main: async")
src = patch(
    src,
    "    run_intro()                     # заставка: видео и титры «Режиссёр Айс»\n",
    "    await run_intro()               # заставка: видео и титры «Режиссёр Айс»\n",
    "main: заставка",
)
src = patch(
    src,
    "            g[\"paused\"] = False\n            run_intro()\n",
    "            g[\"paused\"] = False\n            await run_intro()\n",
    "reset: заставка",
)
src = patch(
    src,
    "    while True:\n        dt = min(clock.tick(60) / 1000, 0.05)\n",
    "    while True:\n"
    "        dt = min(clock.tick(60) / 1000, 0.05)\n"
    "        await asyncio.sleep(0)\n",
    "main: await в цикле",
)
src = patch(
    src,
    'if __name__ == "__main__":\n    main()',
    'if __name__ == "__main__":\n    asyncio.run(main())',
    "точка входа модуля",
)

# ---------- 8. кнопка паузы вместо клавиш ----------
src = patch(
    src,
    "def draw_heart(surf, x, y, r, filled):\n",
    "# экранная кнопка паузы: на телефоне нет Esc\n"
    "MBTN = (GW - 36, H - 34, 19)\n"
    "\n"
    "\n"
    "def mobile_btn_hit(mx, my):\n"
    "    return math.hypot(mx - MBTN[0], my - MBTN[1]) <= MBTN[2] + 10\n"
    "\n"
    "\n"
    "def draw_mobile_button(surf, paused):\n"
    "    x, y, r = MBTN\n"
    "    D.circle(surf, (12, 15, 28), (x, y), r + 2)\n"
    "    D.circle(surf, (170, 190, 240), (x, y), r + 2, 2)\n"
    "    if paused:\n"
    "        D.polygon(surf, (255, 255, 255), [(x - 5, y - 8), (x - 5, y + 8), (x + 8, y)])\n"
    "    else:\n"
    "        D.rect(surf, (255, 255, 255), (x - 7, y - 8, 5, 16), border_radius=2)\n"
    "        D.rect(surf, (255, 255, 255), (x + 2, y - 8, 5, 16), border_radius=2)\n"
    "\n"
    "\n"
    "def draw_heart(surf, x, y, r, filled):\n",
    "кнопка паузы: рисование",
)

src = patch(
    src,
    "        draw_panel(canvas, s, mouse, g[\"tab\"])\n",
    "        draw_mobile_button(canvas, g[\"paused\"])\n"
    "\n"
    "        draw_panel(canvas, s, mouse, g[\"tab\"])\n",
    "кнопка паузы: вывод",
)

src = patch(
    src,
    "            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:\n"
    "                mx, my = mp(e.pos)\n"
    "                if g[\"paused\"]:\n",
    "            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:\n"
    "                mx, my = mp(e.pos)\n"
    "                if mobile_btn_hit(mx, my):\n"
    "                    g[\"paused\"] = not g[\"paused\"]\n"
    "                    g[\"confirm_until\"] = 0\n"
    "                elif g[\"paused\"]:\n",
    "кнопка паузы: обработка тапа",
)

# ---------- 9. меню паузы: три пункта вместо четырёх ----------
src = patch(
    src,
    "    def pause_rects():\n"
    "        return [pygame.Rect(W // 2 - 170, 230 + i * 68, 340, 54) for i in range(4)]\n",
    "    def pause_rects():\n"
    "        return [pygame.Rect(W // 2 - 170, 230 + i * 68, 340, 54) for i in range(3)]\n",
    "пауза: 3 кнопки",
)

src = patch(
    src,
    "            if i == 0:\n"
    "                g[\"paused\"] = False\n"
    "            elif i == 1:\n"
    "                if set_fullscreen(not fullscreen):\n"
    "                    after_scale()\n"
    "            elif i == 2:\n"
    "                if pygame.time.get_ticks() < g[\"confirm_until\"]:   # второй клик — подтверждение\n"
    "                    reset_progress()\n"
    "                    g[\"paused\"] = False\n"
    "                else:\n"
    "                    g[\"confirm_until\"] = pygame.time.get_ticks() + 3500\n"
    "            else:\n",
    "            if i == 0:\n"
    "                g[\"paused\"] = False\n"
    "            elif i == 1:\n"
    "                if pygame.time.get_ticks() < g[\"confirm_until\"]:   # второй клик — подтверждение\n"
    "                    reset_progress()\n"
    "                    g[\"paused\"] = False\n"
    "                else:\n"
    "                    g[\"confirm_until\"] = pygame.time.get_ticks() + 3500\n"
    "            else:\n",
    "пауза: обработка",
)

src = patch(
    src,
    "            labels = [\n"
    '                "Продолжить  (Esc)",\n'
    "                f\"Полный экран: {'вкл' if fullscreen else 'выкл'}  (F11)\",\n"
    '                "Точно сбросить? Нажми ещё раз" if armed else "Сбросить прогресс",\n'
    '                "Выйти из игры",\n'
    "            ]\n",
    "            labels = [\n"
    '                "Продолжить",\n'
    '                "Точно сбросить? Нажми ещё раз" if armed else "Сбросить прогресс",\n'
    '                "Выйти из игры",\n'
    "            ]\n",
    "пауза: подписи",
)

src = patch(
    src,
    "                if i == 2:\n"
    "                    base = (150, 40, 44) if armed else (70, 44, 52)\n",
    "                if i == 1:\n"
    "                    base = (150, 40, 44) if armed else (70, 44, 52)\n",
    "пауза: цвет сброса",
)

src = patch(
    src,
    "                if hot and i == 2 and not armed:\n",
    "                if hot and i == 1 and not armed:\n",
    "пауза: подсветка сброса",
)

src = patch(
    src,
    '            text(canvas, f"Качество: x{K:g} (F10)   •   прогресс сохраняется автоматически",\n'
    "                 f_small, (170, 176, 205), (W // 2, 490), center=True, shadow=False)\n",
    '            text(canvas, "Прогресс сохраняется автоматически",\n'
    "                 f_small, (170, 176, 205), (W // 2, 490), center=True, shadow=False)\n",
    "пауза: подпись снизу",
)

# ---------- 10. подсказки под телефон ----------
src = patch(
    src,
    '        text(canvas, "Клик — столкнуть  |  лови монеты $  |  Esc — пауза  |  F11 — экран  |  F10 — качество",\n',
    '        text(canvas, "Тап — столкнуть  |  лови монеты $  |  кнопка справа — пауза",\n',
    "подсказка HUD",
)

src = patch(
    src,
    '    text(surf, "1–8 — купить/применить  •  Tab — вкладка", f_small, (130, 136, 165),\n',
    '    text(surf, "Тап по вкладке или строке магазина", f_small, (130, 136, 165),\n',
    "подсказка магазина",
)

src = patch(
    src,
    '        text(surf, "Клик по строке — применить", f_small, (130, 136, 165),\n',
    '        text(surf, "Тап по строке — применить", f_small, (130, 136, 165),\n',
    "подсказка зелий",
)

open(DST, "w", encoding="utf-8").write(src)
print(f"готово: {DST} ({len(src)} символов)")
