import os, json, tempfile, threading, time, collections
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame, game, progression as P

game.run_intro = lambda: None          # screenshots: без заставки

tmp = os.path.join(tempfile.gettempdir(), "pc_shot_save.json")
s = game.new_save(); P.ensure(s)
s.update(money=3456789, earned=2200000, kills=1234, level=17, won=False)
m = P.ensure(s)
m["reborn"] = 3; m["bp"] = 47; m["best"] = 18
m["relics"] = {"compass": 2, "coin": 1, "watch": 1}
m["relic_choices"] = ["crown", "mask", "core"]
m["tree"]["capital"] = 3; m["tree"]["profit"] = 4; m["tree"]["fist"] = 2
m["contracts"] = [
    dict(kind="push", target=100, progress=64, done=False, reward=3, slot=0),
    dict(kind="boss", target=4, progress=4, done=True, reward=4, slot=1),
    dict(kind="earn", target=50000, progress=12000, done=False, reward=3, slot=2)]
m["income_rate"] = 450
json.dump(s, open(tmp, "w", encoding="utf-8"))
game.SAVE = tmp

# ---- атомарные скриншоты: сохраняем кадр в главном потоке после flip ----
_requests = collections.deque()
_orig_flip = pygame.display.flip

def _flip():
    _orig_flip()
    if _requests:
        name, done = _requests.popleft()
        pygame.image.save(game.canvas_buf, name)
        print("shot", name)
        done.set()

pygame.display.flip = _flip

def key(k):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0))

def shot(name):
    time.sleep(0.4)
    done = threading.Event()
    _requests.append((name, done))
    done.wait(5.0)

def feeder():
    time.sleep(1.5)
    shot("_s_hud.png")
    key(pygame.K_p); shot("_s_tree.png")
    key(pygame.K_2); shot("_s_relics.png")
    key(pygame.K_3); shot("_s_contracts.png")
    key(pygame.K_4); shot("_s_ach.png")
    key(pygame.K_p); shot("_s_main.png")
    key(pygame.K_TAB); key(pygame.K_TAB); shot("_s_potions.png")
    pygame.event.post(pygame.event.Event(pygame.QUIT))

threading.Thread(target=feeder, daemon=True).start()
try:
    game.main()
except SystemExit:
    pass
