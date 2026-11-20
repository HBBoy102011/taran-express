"""Дымовой тест: прогоняет новый контент без интерактива.

Запуск:  py test_smoke.py
"""
import json
import os
import tempfile
import threading
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import game  # noqa: E402


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("ok -", msg)


# ----------------------------- базовые объекты -----------------------------
for kind in ("normal", "fat", "fly", "sprint", "armor"):
    p = game.Person(False, kind)
    check(p.hp == game.KIND_HP[kind], f"{kind}: hp={p.hp}")
    p.update(0.1)
    p.sprite()

    if kind == "armor":
        check(p.push() is False, "armor: площадной удар не сбивает")
    hits = 0
    while p.state == "walk" and hits < 5:
        hits += 1
        p.push(direct=True)
    check(hits == game.KIND_HP[kind], f"{kind}: падает с {hits}-го прямого удара")
    p.update(0.5)

check(sorted(game.pick_kind(5000) for _ in range(200)) != ["normal"] * 200,
      "смешивается несколько типов людей")

# ----------------------------- кровь и череп -------------------------------
d = game.Decal(300, game.TRACK_Y, big=True)
d.update(0.1)
d.draw(game.world_surf)

sk = game.SkullFly(400, 300)
for _ in range(20):
    sk.update(0.06)
    sk.draw(game.canvas_buf)
check(sk.t > 0, "череп летит в камеру")

# ----------------------------- кислота босса -------------------------------
b = game.Boss(2)                       # «Тень» умеет плевать кислотой
check("acid" in b.flags, "у босса есть флаг acid")
b.acid_t = 0.01
b.update(0.05)
check(b.spit is True, "босс запускает плевок")
b.spit = False

a = game.Acid(b.x, b.y - 150)
while not a.done:
    a.update(0.05)
    a.draw(game.canvas_buf)
check(a.done, "снаряд кислоты долетел")

overlay = game.make_acid_overlay()
overlay.set_alpha(200)
game.canvas_buf.blit(overlay, (0, 0))
check(overlay.get_size() == (game.W, game.H), "затемнение кислотой на весь экран")

# ----------------------------- магазин предметов ---------------------------
tmp = os.path.join(tempfile.gettempdir(), "pc_smoke_save.json")
with open(tmp, "w", encoding="utf-8") as f:
    lv = {u["key"]: 3 for u in game.UPGRADES}
    lv.update(power=6, income=10, flow=10, trains=8, smash=20, cap=4, gold=4)
    json.dump(dict(money=100000, kills=1200, level=5, won=False,
                   levels=lv, items={u["key"]: 0 for u in game.ITEMS}), f)
game.SAVE = tmp
s = game.load_save()
check(s["money"] == 100000, "загрузка сохранения")

g = dict(people=[game.Person(False, "normal")], particles=[], effects=[], rings=[],
         fx={k: 0.0 for k in game.FX_LABELS}, acid=0.0, splats=None,
         toast="", toast_t=0.0, toast_col=(255, 255, 255), shake=0.0,
         helper_t=0.0, boss=None, next_train=5.0, warn=0.0, tab=game.ITEM_TAB)

m0 = s["money"]
p0 = game.item_price(game.ITEMS[0], s)        # цена с учётом инфляции
game.buy_item(s, 0, g)
check(s["items"]["p_flow"] == 1 and s["money"] == m0 - p0,
      "покупка зелья списывает деньги (с инфляцией)")
game.use_item(s, 0, g)
check(s["items"]["p_flow"] == 0 and g["fx"]["p_flow"] == 30, "зелье потока активно на 30с")

game.buy_item(s, 5, g)                 # противоядие
g["acid"] = 5.0
g["splats"] = game.make_acid_overlay()
game.use_item(s, 5, g)
check(g["acid"] == 0.0 and g["splats"] is None, "противоядие смывает кислоту")

game.buy_item(s, 4, g)                 # граната
walkers = [p for p in g["people"] if p.state == "walk"]
game.use_item(s, 4, g)
check(all(p.state != "walk" for p in walkers), "граната сбивает всех на платформе")

# панель магазина рисуется на всех трёх вкладках
for t in range(len(game.TAB_NAMES)):
    game.draw_panel(game.canvas_buf, s, (100, 100), t)
check(True, "панель магазина рисуется (3 вкладки)")

# ----------------------------- полный игровой цикл -------------------------
game.win = game.make_window(False)
game.fullscreen = False


def feeder():
    time.sleep(1.0)
    ww, wh = game.win.get_size()
    sc = min(ww / game.W, wh / game.H)
    ox, oy = (ww - int(game.W * sc)) // 2, (wh - int(game.H * sc)) // 2

    def pos(x, y):
        return (int(x * sc + ox), int(y * sc + oy))

    def key(k):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0))

    def click(x, y):
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos(x, y)))

    key(game.pygame.K_TAB)
    key(game.pygame.K_TAB)              # вкладка «Зелья»
    click(game.GW + 100, game.ROW_Y0 + 38)          # строка без заряда — покупает
    key(game.pygame.K_1)                # применить купленное
    click(game.GW + game.PW - 70, game.ROW_Y0 + game.ROW_H + 47)   # кнопка «купить»
    key(game.pygame.K_TAB)              # назад к базовым
    key(game.pygame.K_2)
    # массово сбиваем людей на пути и бьём босса
    t_end = time.time() + 9.0
    i = 0
    while time.time() < t_end:
        click(120 + (i * 53) % 760, 430)
        if i % 4 == 0:
            click(810, 350)             # босс стоит у правого края
        i += 1
        time.sleep(0.06)
    time.sleep(5.0)                     # ждём поезд, добивание и кислотный босса
    pygame.event.post(pygame.event.Event(pygame.QUIT))


# заставку пропускаем сразу: её события не должны съесть события теста
pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0)))

threading.Thread(target=feeder, daemon=True).start()
try:
    game.main()
except SystemExit:
    pass

with open(tmp, encoding="utf-8") as f:
    saved = json.load(f)
print("   итог: money=%s kills=%s level=%s items=%s" %
      (saved["money"], saved["kills"], saved["level"], saved.get("items")))
check(saved["kills"] > 1200, "поезда в реальном цикле сбили людей")
check("items" in saved, "предметы сохраняются в save.json")
check(saved["money"] != 100000, "деньги двигались (покупки и доход)")
print("\nALL SMOKE CHECKS PASSED")
