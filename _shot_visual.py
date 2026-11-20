import os, json, tempfile, threading, time, collections
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame, game, progression as P

game.run_intro = lambda: None

tmp = os.path.join(tempfile.gettempdir(), "pc_shot_visual.json")
s = game.new_save(); P.ensure(s)
s.update(money=840, earned=9500, kills=42, level=3, won=False)
m = P.ensure(s)
m["reborn"] = 0; m["bp"] = 2; m["best"] = 4
m["income_rate"] = 12
json.dump(s, open(tmp, "w", encoding="utf-8"))
game.SAVE = tmp

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
    shot("_s_main2.png")
    key(pygame.K_TAB); shot("_s_potions2.png")
    pygame.event.post(pygame.event.Event(pygame.QUIT))

threading.Thread(target=feeder, daemon=True).start()
try:
    game.main()
except SystemExit:
    pass
