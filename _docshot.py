# -*- coding: utf-8 -*-
"""Скриншоты для комплекта документации: заставка, игра, пауза, победа, поражение, Депо."""
import collections
import json
import os
import sys
import tempfile
import threading
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import game
import progression as P

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_docshots")
os.makedirs(OUT, exist_ok=True)

_requests = collections.deque()
_orig_flip = pygame.display.flip


def _flip():
    _orig_flip()
    if _requests:
        name, done = _requests.popleft()
        pygame.image.save(game.canvas_buf, os.path.join(OUT, name))
        print("shot", name, game.canvas_buf.get_size())
        done.set()


pygame.display.flip = _flip


def capture(name):
    time.sleep(0.35)
    done = threading.Event()
    _requests.append((name, done))
    done.wait(8.0)


def find_main():
    for _ in range(200):
        for fr in sys._current_frames().values():
            f = fr
            while f is not None:
                if f.f_code.co_name == "main":
                    if "g" in f.f_locals and "s" in f.f_locals:
                        return f.f_locals["g"], f.f_locals["s"]
                f = f.f_back
        time.sleep(0.1)
    return None, None


def intro():
    done = threading.Event()

    def skipper():
        time.sleep(1.5)
        capture("01_заставка.png")
        time.sleep(3.7)
        capture("01b_титры.png")
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
        done.set()

    threading.Thread(target=skipper, daemon=True).start()
    game.run_intro()
    done.wait(4.0)
    print("intro done")


def gameplay():
    tmp = os.path.join(tempfile.gettempdir(), "docshot_save.json")
    s = game.new_save()
    P.ensure(s)
    s.update(money=18400, earned=26500, kills=127, level=4, won=False)
    m = P.ensure(s)
    m["reborn"] = 1
    m["bp"] = 12
    m["best"] = 6
    m["relics"] = {"compass": 1, "coin": 1}
    m["tree"]["capital"] = 2
    m["tree"]["profit"] = 1
    m["tree"]["fist"] = 1
    m["income_rate"] = 48.0
    json.dump(s, open(tmp, "w", encoding="utf-8"))
    game.SAVE = tmp

    def feeder():
        g, s2 = find_main()
        if g is None:
            print("main frame not found")
            pygame.event.post(pygame.event.Event(pygame.QUIT))
            return
        time.sleep(2.2)
        capture("02_игровой_процесс.png")

        # магазин и Депо
        g["tab"] = 2
        capture("03_магазин_зелья.png")
        g["tab"] = 0
        g["depot"] = True
        g["depot_tab"] = 0
        capture("04_депо_дерево.png")
        g["depot_tab"] = 1
        capture("05_депо_реликвии.png")
        g["depot_tab"] = 2
        capture("06_депо_контракты.png")
        g["depot_tab"] = 3
        capture("07_депо_достижения.png")
        g["depot"] = False

        # пауза
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
        time.sleep(0.5)
        capture("08_пауза.png")
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
        time.sleep(0.4)

        # победа: финальная станция, в HUD горит «Депо — готово»
        s2["won"] = True
        s2["level"] = 19
        s2["kills"] = 10000
        g["stage"] = 19
        g["prev"] = 19
        g["trans"] = 1.0
        g["banner_t"] = 0.0
        g["toast"] = "ФИНАЛ РЕЙСА! 20 станций пройдено"
        g["toast_col"] = (255, 220, 120)
        g["toast_t"] = 8.0
        g["boss"] = None
        g["people"].clear()
        time.sleep(4.2)
        capture("09_победа.png")

        # поражение: последняя жизнь, новый забег и итог
        g["banner_t"] = 0.0
        s2["skins"] = len(game.SKINS)
        g["lives"] = 1
        g["hard_t"] = 61.0
        g["people"].clear()
        p = game.Person(False, "normal")
        p.x = -58
        p.state = "walk"
        p.entered = True
        p.dir = -1
        p.vx = -50
        g["people"].append(p)
        time.sleep(1.2)
        capture("10_поражение.png")

        pygame.event.post(pygame.event.Event(pygame.QUIT))

    threading.Thread(target=feeder, daemon=True).start()
    try:
        game.main()
    except SystemExit:
        pass


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("intro", "all"):
        intro()
    if mode in ("game", "all"):
        gameplay()
    print("DONE")
