import os, json, tempfile, threading, time, cProfile, pstats, io
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame, game, progression as P

game.run_intro = lambda: None
tmp = os.path.join(tempfile.gettempdir(), "pc_prof_save.json")
s = game.new_save(); P.ensure(s)
s.update(money=3456789, earned=2200000, kills=1234, level=17, won=False)
m = P.ensure(s)
m["reborn"] = 3; m["bp"] = 47; m["best"] = 18
m["relics"] = {"compass": 2, "coin": 1, "watch": 1}
m["tree"]["capital"] = 3; m["tree"]["profit"] = 4; m["tree"]["fist"] = 2
m["contracts"] = [
    dict(kind="push", target=100, progress=64, done=False, reward=3, slot=0),
    dict(kind="boss", target=4, progress=4, done=True, reward=4, slot=1),
    dict(kind="earn", target=50000, progress=12000, done=False, reward=3, slot=2)]
m["income_rate"] = 450
json.dump(s, open(tmp, "w", encoding="utf-8"))
game.SAVE = tmp

def feeder():
    time.sleep(2.0)
    # let a boss and crowd build up
    time.sleep(6.0)
    pygame.event.post(pygame.event.Event(pygame.QUIT))

threading.Thread(target=feeder, daemon=True).start()

pr = cProfile.Profile()
pr.enable()
try:
    game.main()
except SystemExit:
    pass
pr.disable()
buf = io.StringIO()
pstats.Stats(pr, stream=buf).sort_stats("cumulative").print_stats(45)
print(buf.getvalue())
