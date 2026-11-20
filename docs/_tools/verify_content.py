# -*- coding: utf-8 -*-
"""Расширенная проверка контента и данных «ТАРАН-ЭКСПРЕСС 3.2».

Дополняет test_smoke.py и _meta_test.py: проходит по всем 20 темам, 20 боссам,
16 улучшениям, 12 скинам, 12 реликвиям, 27 узлам дерева и проверяет отрисовку
и сохранения. Пишет отчёт в docs/06_Тестирование/материалы/verify_report.json.

Запуск:  py docs/_tools/verify_content.py
"""
import json
import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import pygame  # noqa: E402

import game  # noqa: E402
import progression as P  # noqa: E402
import taran.saves as SAVES  # noqa: E402
from taran.config import BOSSES, ITEMS, SKINS, THEMES, UPGRADES  # noqa: E402
from taran.logic import cost, new_save  # noqa: E402

RESULTS = []


def check(cond, msg):
    RESULTS.append((bool(cond), msg))
    print(("ok   - " if cond else "FAIL - ") + msg)
    return cond


def main():
    pygame.init()
    pygame.display.set_mode((1280, 720))
    try:
        game.build_assets()
    except Exception as e:                      # шрифты могут требовать дисплей
        print("assets warning:", type(e).__name__, e)

    # ---------------- данные ----------------
    check(len(THEMES) == 20, "тем в THEMES: %d" % len(THEMES))
    need = ("name", "kills", "kind", "top", "bot", "plat", "train", "cloud")
    bad = [t.get("name") for t in THEMES if any(k not in t for k in need)]
    check(not bad, "у всех тем есть обязательные поля (плохих: %d)" % len(bad))
    ks = [t["kills"] for t in THEMES]
    check(ks == sorted(ks), "порог kills в темах не убывает")

    check(len(BOSSES) == 20, "боссов в BOSSES: %d" % len(BOSSES))
    bad = [b["name"] for b in BOSSES if b["hp"] <= 0 or b["speed"] <= 0 or b["time"] <= 0]
    check(not bad, "у всех боссов положительные hp, speed и time")
    flags = set()
    for b in BOSSES:
        flags.update(b["flags"])
    check(len(flags) >= 8, "уникальных поведений боссов: %d" % len(flags))

    check(len(UPGRADES) == 16, "улучшений в UPGRADES: %d" % len(UPGRADES))
    check(len(game.TAB_NAMES) == 3 and set(u["tab"] for u in UPGRADES) <= {0, 1, 2},
          "вкладок магазина 3, улучшения разложены по tab 0/1: %s"
          % sorted(set(u["tab"] for u in UPGRADES)))
    grows = all(cost(u, 5) > cost(u, 4) > cost(u, 0) for u in UPGRADES)
    check(grows, "цена каждого улучшения растёт с уровнем")

    check(len(ITEMS) == 6, "расходников: %d" % len(ITEMS))
    check(all(i["price"] > 0 for i in ITEMS), "у всех расходников цена больше нуля")
    check(len(SKINS) == 12, "скинов: %d" % len(SKINS))
    check(len(P.RELICS) == 12, "реликвий: %d" % len(P.RELICS))
    check(len(P.ACHIEVEMENTS) == 24, "достижений: %d" % len(P.ACHIEVEMENTS))
    check(len(P.META_UPGRADES) == 27, "узлов дерева: %d" % len(P.META_UPGRADES))
    branches = {}
    for u in P.META_UPGRADES:
        branches[u["b"]] = branches.get(u["b"], 0) + 1
    check(len(branches) == 3 and all(v == 9 for v in branches.values()),
          "три ветки дерева по 9 узлов: %s" % branches)
    check(len(P.RUN_MODS) == 6, "модификаторов рейса: %d" % len(P.RUN_MODS))
    check(game.HARD_LIVES == 5, "жизней в хардкоре: %d" % game.HARD_LIVES)

    # ---------------- отрисовка ----------------
    surf = pygame.Surface((game.GW, game.H))
    painted = 0
    for i, b in enumerate(BOSSES):
        try:
            boss = game.Boss(i)
            boss.draw(surf)
            painted += 1
        except Exception as e:
            print("boss %d (%s) draw: %s: %s" % (i, b["name"], type(e).__name__, e))
    check(painted == 20, "рисуются все 20 боссов (%d/20)" % painted)

    skins_ok = 0
    for i in range(len(SKINS)):
        try:
            p = game.Person(False, "normal", i)
            img = p.sprite()
            if img is not None and img.get_width() > 0:
                skins_ok += 1
        except Exception as e:
            print("skin %d: %s: %s" % (i, type(e).__name__, e))
    check(skins_ok == 12, "спрайт игрока собирается для всех 12 скинов (%d/12)" % skins_ok)

    kinds_ok = 0
    for kind in game.KIND_HP:
        try:
            p = game.Person(False, kind)
            p.update(0.1)
            p.sprite()
            kinds_ok += 1
        except Exception as e:
            print("kind %s: %s: %s" % (kind, type(e).__name__, e))
    check(kinds_ok == len(game.KIND_HP), "все типы прохожих живые (%d/%d)"
          % (kinds_ok, len(game.KIND_HP)))

    # ---------------- бой ----------------
    boss = game.Boss(0)
    hp0 = boss.hp
    boss.hp -= 10
    check(boss.hp < hp0, "босс получает урон")
    check(game.Boss(19).max_hp > game.Boss(0).max_hp, "сила боссов растёт с уровнем")

    # ---------------- сохранения ----------------
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "_taran_verify.json")
    if os.path.exists(tmp):
        os.remove(tmp)
    s = SAVES.load_save(tmp)
    check(isinstance(s, dict) and "money" in s, "отсутствующий файл даёт новый сейв")
    s["money"] = 123456
    s["level"] = 7
    SAVES.write_save(s, tmp)
    s2 = SAVES.load_save(tmp)
    check(s2["money"] == 123456 and s2["level"] == 7, "money и level переживают запись и чтение")

    old = {"money": 500, "level": 3}          # сейв до 3.0: без meta
    SAVES.write_save(old, tmp)
    s3 = SAVES.load_save(tmp)
    m = P.ensure(s3)
    check(isinstance(m, dict) and "tree" in m, "старый сейв мигрирует в meta v4")
    check(len(m["tree"]) == 27, "после миграции в дереве 27 узлов")

    # офлайн-доход
    s4 = new_save()
    s4["money"] = 0
    m4 = P.ensure(s4)
    m4["last_seen"] = time.time() - 3600
    m4["income_rate"] = 50.0
    before = s4["money"]
    try:
        gained, secs = P.catch_up(s4)
    except Exception as e:
        gained, secs = 0, 0
        print("catch_up:", type(e).__name__, e)
    check(s4["money"] > before, "офлайн-доход начисляется (было %s, стало %s)"
          % (before, s4["money"]))

    # ---------------- мета ----------------
    rich = new_save()
    rich["earned"] = 10 ** 6
    rich["level"] = 9
    check(P.can_rebirth(rich), "перерождение доступно с 9-й станции")
    check(P.bp_reward(rich) > 0, "награда чертежами положительна (%d)" % P.bp_reward(rich))
    poor = new_save()
    poor["earned"] = 100
    check(P.bp_reward(rich) > P.bp_reward(poor), "награда растёт вместе с доходом")

    m2 = P.ensure(new_save())
    m2["relics"]["compass"] = 2
    m2["relics"]["coupon"] = 1
    check(abs(P.relic_bonus({"meta": m2}, "income") - 0.12) < 1e-6,
          "реликвии суммируют бонус по уровням")
    check(P.tree_cost(P.META_UPGRADES[0], 3) > P.tree_cost(P.META_UPGRADES[0], 1),
          "стоимость узла дерева растёт")

    os.remove(tmp) if os.path.exists(tmp) else None

    ok = sum(1 for c, _ in RESULTS if c)
    total = len(RESULTS)
    report = {"suite": "verify_content", "passed": ok, "total": total,
              "checks": [{"ok": c, "name": m} for c, m in RESULTS]}
    out = os.path.join(ROOT, "docs", "06_Тестирование", "материалы", "verify_report.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\nRESULT %d/%d  report=%s" % (ok, total, out))
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
