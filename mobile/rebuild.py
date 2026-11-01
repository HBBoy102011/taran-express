# -*- coding: utf-8 -*-
"""Полная пересборка мобильной версии игры одной командой:

    py mobile/rebuild.py

Шаги:
  1. проверка комплекта (mobile/setup.py);
  2. патч десктопного game.py под веб (mobile/make_mobile.py);
  3. сборка pygbag: архив игры + index.html -> mobile/build/web;
  4. перевод страницы на локальный рантайм (mobile/prepare_offline.py);
  5. сборка и подпись APK (mobile/build_apk.py).

Ничего не качает, если один раз прогнал py mobile/setup.py --fetch.
"""
import os
import shutil
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
VENV_PY = os.path.join(ROOT, ".apkbuild", "Scripts", "python.exe")
OUT_APK = os.path.join(HERE, "build", "train_game_v4.0.apk")
CDN_CACHE = os.path.join(HERE, "cdn_cache")


def step(title, cmd):
    print("\n=== " + title + " ===", flush=True)
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    r = subprocess.run(cmd, cwd=ROOT, env=env)
    if r.returncode != 0:
        sys.exit(f"\nСТОП: шаг не прошёл — {title}")


def main():
    if not os.path.exists(VENV_PY):
        sys.exit("нет .apkbuild — сначала  py mobile/setup.py --fetch")

    step("1/5 комплект", [sys.executable, os.path.join(HERE, "setup.py")])
    step("2/5 патч игры под веб", [sys.executable, os.path.join(HERE, "make_mobile.py")])
    step("3/5 pygbag build", [VENV_PY, "-m", "pygbag", "--build", os.path.join("mobile")])
    step("4/5 локальный рантайм", [sys.executable, os.path.join(HERE, "prepare_offline.py")])

    # обновляем кэш рантайма: если pygbag что-то своё положил рядом — сохраним
    web_cdn = os.path.join(HERE, "build", "web", "cdn")
    if os.path.isdir(web_cdn):
        for dp, dn, fns in os.walk(web_cdn):
            for fn in fns:
                src = os.path.join(dp, fn)
                dst = os.path.join(CDN_CACHE, os.path.relpath(src, web_cdn))
                if not os.path.exists(dst):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy(src, dst)

    step("5/5 APK", [sys.executable, os.path.join(HERE, "build_apk.py")])

    if os.path.exists(OUT_APK):
        print(f"\nГОТОВО: {OUT_APK}  ({os.path.getsize(OUT_APK) / 1024 / 1024:.1f} МБ)")


if __name__ == "__main__":
    main()
