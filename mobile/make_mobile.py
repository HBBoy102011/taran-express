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
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "game.py")
DST = os.path.join(HERE, "game_app.py")
SND_SRC = os.path.join(os.path.dirname(HERE), "sound")
SND_DST = os.path.join(HERE, "sound")


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
src = patch(
    src,
    "    _HEART, draw_boss_bar, draw_heart, draw_mute_button, mute_hit,\n",
    "    _HEART, draw_boss_bar, draw_heart, draw_mobile_button, draw_mute_button,\n"
    "    mobile_btn_hit, mute_hit,\n",
    "импорт мобильной кнопки",
)

# ---------- 2. окно 1280x720 без полноэкранного режима ----------
src = patch(
    src,
    "set_scale(FORCE_K or scale_fullscreen())\n"
    "win = make_window(fullscreen)\n"
    "fullscreen = bool(win.get_flags() & pygame.FULLSCREEN)\n",
    '# мобильная версия: 960×540 внутри, pygbag растягивает полотно на экран.\n'
    '# Меньше пикселей — стабильнее кадры на телефоне.\n'
    "set_scale(WEB_K)\n"
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
# Сами функции живут в taran/saves.py, поэтому патчим копию модуля ниже,
# после того как пакет taran/ скопирован в mobile/.

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
# Рисование кнопки живёт в taran/ui/hud.py; патчим копию модуля ниже.
# В game.py добавляем импорт draw_mobile_button/mobile_btn_hit.

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
    '        hint = "Клик — столкнуть  ·  монеты $  ·  P — Депо  ·  Esc — пауза  ·  F11 — экран"\n',
    '        hint = "Тап — столкнуть  ·  монеты $  ·  справа — Депо, пауза и звук"\n',
    "подсказка HUD",
)

open(DST, "w", encoding="utf-8").write(src)
# мета-прогрессия 3.0: модули должны лежать рядом с game_app.py, иначе
# pygbag не включит их в архив игры
for extra in ("progression.py", "prog_ui.py"):
    src_extra = os.path.join(ROOT, extra)
    if os.path.exists(src_extra):
        shutil.copy2(src_extra, os.path.join(HERE, extra))
        print(f"модуль скопирован: {extra}")
# пакет taran/ с конфигом и будущими модулями UI/мира
TARAN_SRC = os.path.join(ROOT, "taran")
TARAN_DST = os.path.join(HERE, "taran")
if os.path.isdir(TARAN_SRC):
    shutil.copytree(TARAN_SRC, TARAN_DST, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    print(f"пакет скопирован: {TARAN_DST}")
# сохранение в браузере: подменяем файловые операции в копии taran/saves.py
SAVES_DST = os.path.join(TARAN_DST, "saves.py")
if os.path.exists(SAVES_DST):
    saves_src = open(SAVES_DST, encoding="utf-8").read()
    saves_src = patch(
        saves_src,
        "def load_save(path):\n",
        "def _ls():\n"
        '    """Хранилище браузера: в WebAssembly обычная запись в файл не сохраняется."""\n'
        "    try:\n"
        "        import platform\n"
        "        return platform.window.localStorage\n"
        "    except Exception:\n"
        "        return None\n"
        "\n"
        "\n"
        "def _save_text(path):\n"
        "    ls = _ls()\n"
        "    if ls is not None:\n"
        "        try:\n"
        '            raw = ls.getItem("train_game_v1")\n'
        "            if raw:\n"
        "                return str(raw)\n"
        "        except Exception:\n"
        "            pass\n"
        "    try:\n"
        '        with open(path, "r", encoding="utf-8") as f:\n'
        "            return f.read()\n"
        "    except OSError:\n"
        "        return None\n"
        "\n"
        "\n"
        "def _put_text(txt, path):\n"
        "    ls = _ls()\n"
        "    if ls is not None:\n"
        "        try:\n"
        '            ls.setItem("train_game_v1", txt)\n'
        "            return\n"
        "        except Exception:\n"
        "            pass\n"
        '    with open(path, "w", encoding="utf-8") as f:\n'
        "        f.write(txt)\n"
        "\n"
        "\n"
        "def load_save(path):\n",
        "load_save: хранилище",
    )
    saves_src = patch(
        saves_src,
        '        with open(path, "r", encoding="utf-8") as f:\n'
        "            d = json.load(f)\n",
        "        d = json.loads(_save_text(path))\n",
        "load_save: чтение",
    )
    saves_src = patch(
        saves_src,
        '        with open(path, "w", encoding="utf-8") as f:\n'
        "            json.dump(s, f)\n",
        "        _put_text(json.dumps(s), path)\n",
        "write_save: запись",
    )
    open(SAVES_DST, "w", encoding="utf-8").write(saves_src)
    print("сохранение переведено на localStorage")

# экранная кнопка паузы: добавляем в копию taran/ui/hud.py
HUD_DST = os.path.join(TARAN_DST, "ui", "hud.py")
if os.path.exists(HUD_DST):
    hud_src = open(HUD_DST, encoding="utf-8").read()
    hud_src = patch(
        hud_src,
        "BUTTON_HIT_PAD = 10                 # запас вокруг кнопки для тапа (≈ 56 логических px)\n",
        "BUTTON_HIT_PAD = 10                 # запас вокруг кнопки для тапа (≈ 56 логических px)\n"
        "\n"
        "# экранная кнопка паузы: на телефоне нет Esc, ставим её рядом со звуком\n"
        "MBTN = (GW - 96, 69, 18)\n"
        "\n"
        "\n"
        "def mobile_btn_hit(mx, my):\n"
        "    return math.hypot(mx - MBTN[0], my - MBTN[1]) <= MBTN[2] + BUTTON_HIT_PAD\n"
        "\n"
        "\n"
        "def draw_mobile_button(surf, paused):\n"
        "    _bind()\n"
        "    x, y, r = MBTN\n"
        "    k = r / 15.0\n"
        "    G.D.circle(surf, (18, 21, 32), (x, y), r + 2)\n"
        "    G.D.circle(surf, (66, 76, 104), (x, y), r + 2, 2)\n"
        "    G.D.circle(surf, (27, 31, 45), (x, y), r)\n"
        "    if paused:\n"
        "        G.D.polygon(surf, (255, 255, 255), [(x - 5 * k, y - 8 * k),\n"
        "                                            (x - 5 * k, y + 8 * k),\n"
        "                                            (x + 8 * k, y)])\n"
        "    else:\n"
        "        G.D.rect(surf, (255, 255, 255), (x - 7 * k, y - 8 * k, 5 * k, 16 * k),\n"
        "                 border_radius=2)\n"
        "        G.D.rect(surf, (255, 255, 255), (x + 2 * k, y - 8 * k, 5 * k, 16 * k),\n"
        "                 border_radius=2)\n",
        "кнопка паузы: рисование",
    )
    open(HUD_DST, "w", encoding="utf-8").write(hud_src)
    print("кнопка паузы добавлена в HUD")

# подсказки магазина теперь живут в taran/ui/shop.py — патчим уже копию
SHOP_DST = os.path.join(TARAN_DST, "ui", "shop.py")
if os.path.exists(SHOP_DST):
    shop_src = open(SHOP_DST, encoding="utf-8").read()
    shop_src = patch(
        shop_src,
        '    if tab == ITEM_TAB:\n'
        '        tip1 = "ЛКМ — применить  ·  цена — купить"\n'
        '    else:\n'
        '        tip1 = "ЛКМ — купить  ·  Shift — ×10"\n',
        '    if tab == ITEM_TAB:\n'
        '        tip1 = "Тап — применить  ·  кнопка цены — купить"\n'
        '    else:\n'
        '        tip1 = "Тап — купить уровень"\n',
        "подсказка магазина",
    )
    shop_src = patch(
        shop_src,
        '    text(surf, "Tab — вкладка  ·  1–8 — выбор",\n',
        '    text(surf, "Тап по вкладке — переключить раздел",\n',
        "подсказка вкладок",
    )
    open(SHOP_DST, "w", encoding="utf-8").write(shop_src)
    print("подсказки магазина адаптированы под тап")
if os.path.isdir(SND_SRC):
    shutil.copytree(SND_SRC, SND_DST, dirs_exist_ok=True)
    print(f"звук скопирован: {SND_DST}")
print(f"готово: {DST} ({len(src)} символов)")
