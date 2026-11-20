# -*- coding: utf-8 -*-
"""Замер FPS без окна: считает кадры настоящего игрового цикла.

Запуск:  py docs/_tools/bench_fps.py [секунды]
Печатает средний FPS, медиану и 95-й процентиль времени кадра.
"""
import os
import statistics
import sys
import threading
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import pygame  # noqa: E402
import game  # noqa: E402

DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
stamps = []
real_present = game.present


def timed_present(*a, **kw):
    stamps.append(time.perf_counter())
    return real_present(*a, **kw)


game.present = timed_present


def feeder():
    time.sleep(0.8)
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(10, 10)))
    # немного «игры»: кликаем по платформе, пока идёт замер
    end = time.time() + DUR
    i = 0
    while time.time() < end:
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                             pos=(120 + (i * 47) % 700, 430)))
        i += 1
        time.sleep(0.08)
    pygame.event.post(pygame.event.Event(pygame.QUIT))


threading.Thread(target=feeder, daemon=True).start()
try:
    game.main()
except SystemExit:
    pass

if len(stamps) > 30:
    deltas = [(b - a) * 1000 for a, b in zip(stamps, stamps[1:])]
    deltas.sort()
    n = len(deltas)
    p95 = deltas[min(n - 1, int(n * 0.95))]
    print("frames=%d  avg_fps=%.1f  median_frame=%.2f ms  p95_frame=%.2f ms  max=%.2f ms"
          % (n, 1000.0 / statistics.mean(deltas), statistics.median(deltas), p95, max(deltas)))
else:
    print("not enough frames:", len(stamps))
