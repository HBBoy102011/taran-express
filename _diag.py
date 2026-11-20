import os, json, tempfile, threading, time
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame, game, progression as P
game.run_intro = lambda: None
tmp = os.path.join(tempfile.gettempdir(), "pc_diag_save.json")
s = game.new_save(); P.ensure(s); s.update(money=1000, kills=10, level=2)
json.dump(s, open(tmp, "w", encoding="utf-8")); game.SAVE = tmp
def feeder():
    time.sleep(2.0)
    print("K", game.K, "WP,HP", game.WP, game.HP, "canvas", game.canvas_buf.get_size(),
          "win", game.win.get_size(), "SCALED_OK", game.SCALED_OK,
          "flags", game.win.get_flags(), "desktop", game.desktop_size(), flush=True)
    pygame.event.post(pygame.event.Event(pygame.QUIT))
threading.Thread(target=feeder, daemon=True).start()
try:
    game.main()
except SystemExit:
    pass
