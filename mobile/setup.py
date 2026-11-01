# -*- coding: utf-8 -*-
"""Готовит проект к сборке APK: проверяет всё нужное и докачивает недостающее.

    py mobile/setup.py           # только проверить: что на месте, чего не хватает
    py mobile/setup.py --fetch   # докачать недостающее (интернет нужен только тут)

После одного запуска с --fetch проект собирается полностью офлайн: всё лежит
внутри папки проекта.

Что проверяется:
  * .apkbuild            — venv с pygbag (сборщик веб-версии)
  * packages/*.whl        — установщик pygbag на случай, если venv сломается
  * packages/fonts/       — шрифты DejaVu (в вебе системных шрифтов нет)
  * android_sdk/*.zip     — JDK 17, Android build-tools, платформа (для APK)
  * mobile/cdn_cache/     — рантайм CPython-WASM + колесо pygame + индекс пакетов
"""
import os
import shutil
import subprocess
import sys
import urllib.request

# консоль на русской Windows — cp1251, а мы печатаем кириллицу и стрелки ⇒ принудительно utf-8
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
VENV = os.path.join(ROOT, ".apkbuild")
PYGBAG_WHL = "pygbag-0.9.3-py3-none-any.whl"
PACKAGES = os.path.join(ROOT, "packages")
FONTS_SRC = os.path.join(HERE, "fonts")
FONTS_CACHE = os.path.join(PACKAGES, "fonts")
SDK = os.path.join(ROOT, "android_sdk")
CDN_CACHE = os.path.join(HERE, "cdn_cache")
WEB = os.path.join(HERE, "build", "web")
CDN_DIR = os.path.join(WEB, "cdn")

CDN_BASE = "https://pygame-web.github.io/cdn/"

# ---------- что качается из сети (только при --fetch и только если локально нет) ----------
SDK_FILES = {
    "bt.zip": "https://dl.google.com/android/repository/build-tools_r34-windows.zip",
    "platform.zip": "https://dl.google.com/android/repository/platform-34-ext7_r03.zip",
    "jdk.zip": ("https://api.adoptium.net/v3/binary/latest/17/ga/windows/x64/"
                "jdk/hotspot/normal/eclipse"),
}

# файлы рантайма pygbag: они один раз скачиваются и дальше живут в mobile/cdn_cache
CDN_FILES = [
    "0.9.3/pythons.js",
    "0.9.3/cpython312/main.js",
    "0.9.3/cpython312/main.data",
    "0.9.3/cpython312/main.wasm",
    "0.9.3/cpythonrc.py",
    "0.9.3/empty.html",
    "0.9.3/empty.ogg",
    "vtx.js",
    "vt/xterm.css",
    "vt/xterm.js",
    "vt/xterm-addon-image.js",
    "index-0.9.3-cp312.json",
    "cp312/pygame_ce-2.5.7-cp312-cp312-wasm32_bi_emscripten.whl",
]

problems = []
notes = []


def ok(msg):
    print("  ok    " + msg)


def bad(msg, fix):
    problems.append(msg)
    print("  НАДО   " + msg)
    print("         -> " + fix)


def fetch(url, dst, label):
    """Скачивание с возобновлением: неполный файл докачивается, а не начинается заново."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    part = dst + ".part"
    done = os.path.getsize(part) if os.path.exists(part) else 0
    total = 0
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            total = int(r.headers.get("Content-Length") or 0)
            mode = "ab" if done else "wb"
            if done:
                r.close()
                req = urllib.request.Request(url, headers={
                    "User-Agent": "curl/8", "Range": f"bytes={done}-"})
                r = urllib.request.urlopen(req, timeout=60)
                if r.status != 206:
                    mode, done = "wb", 0
                    r.close()
                    r = urllib.request.urlopen(
                        urllib.request.Request(url, headers={"User-Agent": "curl/8"}),
                        timeout=60)
            print(f"  качаю {label} ({(total or 0) / 1024 / 1024:.1f} МБ)")
            with open(part, mode) as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
        if total and os.path.getsize(part) < total:
            raise IOError(f"недокачано {os.path.getsize(part)} из {total}")
        os.replace(part, dst)
        return True
    except Exception as e:                                     # noqa: BLE001
        print(f"  НЕ ВЫШЛО {label}: {e}")
        return False


def venv_python():
    p = os.path.join(VENV, "Scripts", "python.exe")
    return p if os.path.exists(p) else None


def check_venv(fetch_missing):
    py = venv_python()
    if not py:
        if not fetch_missing:
            bad("нет окружения .apkbuild с pygbag", "py mobile/setup.py --fetch")
            return
        print("  создаю окружение .apkbuild...")
        subprocess.run([sys.executable, "-m", "venv", VENV], check=True)
        py = venv_python()
    r = subprocess.run([py, "-c", "import pygbag"], capture_output=True)
    if r.returncode == 0:
        ok(".apkbuild с pygbag")
        return
    wheel = os.path.join(PACKAGES, PYGBAG_WHL)
    if not os.path.exists(wheel):
        if not fetch_missing:
            bad(f"pygbag не установлен, а {PYGBAG_WHL} не скачан",
                "py mobile/setup.py --fetch")
            return
        # pygbag ставится только через pip — качаем колесо им же
        r2 = subprocess.run([sys.executable, "-m", "pip", "download", "pygbag==0.9.3",
                             "-d", PACKAGES], capture_output=True, text=True)
        if not os.path.exists(wheel):
            bad("не удалось скачать pygbag", r2.stderr[-300:])
            return
    print("  ставлю pygbag из packages/ (офлайн)...")
    r3 = subprocess.run([py, "-m", "pip", "install", "--no-index",
                         "--find-links", PACKAGES, "pygbag==0.9.3"],
                        capture_output=True, text=True)
    if r3.returncode != 0:
        bad("не удалось поставить pygbag", r3.stderr[-300:])
        return
    ok(".apkbuild с pygbag (установлен из packages/)")


def check_wheel(fetch_missing):
    p = os.path.join(PACKAGES, PYGBAG_WHL)
    if os.path.exists(p):
        ok(f"packages/{PYGBAG_WHL}")
        return
    if not fetch_missing:
        bad(f"нет packages/{PYGBAG_WHL}", "py mobile/setup.py --fetch")
        return
    r = subprocess.run([sys.executable, "-m", "pip", "download", "pygbag==0.9.3",
                        "-d", PACKAGES], capture_output=True, text=True)
    ok(f"packages/{PYGBAG_WHL}") if os.path.exists(p) else bad(
        "pip download pygbag не прошёл", r.stderr[-300:])


def check_fonts(fetch_missing):
    files = ["DejaVuSans.ttf", "DejaVuSans-Bold.ttf"]
    if not all(os.path.exists(os.path.join(FONTS_SRC, f)) for f in files):
        if os.path.isdir(FONTS_CACHE) and all(
                os.path.exists(os.path.join(FONTS_CACHE, f)) for f in files):
            for f in files:
                shutil.copy(os.path.join(FONTS_CACHE, f), os.path.join(FONTS_SRC, f))
            ok("fonts/ восстановлены из packages/fonts")
        elif fetch_missing:
            bad("шрифты DejaVu не найдены", "скачай их в mobile/fonts вручную — "
                                             "git-ссылки DejaVu отдают 404")
        else:
            bad("нет fonts/ и packages/fonts", "py mobile/setup.py --fetch")
    else:
        ok("fonts/ (DejaVu, кириллица)")
    os.makedirs(FONTS_CACHE, exist_ok=True)
    for f in files:
        src = os.path.join(FONTS_SRC, f)
        dst = os.path.join(FONTS_CACHE, f)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy(src, dst)


def check_sdk(fetch_missing):
    for name, url in SDK_FILES.items():
        p = os.path.join(SDK, name)
        if os.path.exists(p) and os.path.getsize(p) > 1 << 20:
            ok(f"android_sdk/{name} ({os.path.getsize(p) / 1024 / 1024:.0f} МБ)")
        elif fetch_missing:
            fetch(url, p, name)
        else:
            bad(f"нет android_sdk/{name}", "py mobile/setup.py --fetch")
    if not os.path.isdir(SDK):
        os.makedirs(SDK, exist_ok=True)
    if fetch_missing:
        for name in SDK_FILES:
            p = os.path.join(SDK, name)
            if os.path.exists(p) and not os.path.isdir(os.path.join(SDK, name[:-4])):
                try:
                    print(f"  распаковываю {name}...")
                    shutil.unpack_archive(p, os.path.join(SDK, name[:-4]), "zip")
                except Exception as e:                          # noqa: BLE001
                    print(f"  НЕ ВЫШЛО распаковать {name}: {e}")


def check_cdn(fetch_missing):
    """Рантайм живёт в cdn_cache; в build/web/cdn он подкладывается при сборке."""
    have_cache = all(os.path.exists(os.path.join(CDN_CACHE, f.replace("/", os.sep)))
                     for f in CDN_FILES)
    if not have_cache:
        if not fetch_missing:
            bad("нет mobile/cdn_cache (файлы рантайма)", "py mobile/setup.py --fetch")
            return
        for f in CDN_FILES:
            dst = os.path.join(CDN_CACHE, f.replace("/", os.sep))
            if os.path.exists(dst):
                continue
            fetch(CDN_BASE + f, dst, f)
    ok("cdn_cache (%.0f МБ)" % (
        sum(os.path.getsize(os.path.join(CDN_CACHE, f.replace("/", os.sep)))
            for f in CDN_FILES
            if os.path.exists(os.path.join(CDN_CACHE, f.replace("/", os.sep))))
        / 1024 / 1024))
    # и рядом со сборкой — если её удалят, подложим заново
    for f in CDN_FILES:
        src = os.path.join(CDN_CACHE, f.replace("/", os.sep))
        dst = os.path.join(CDN_DIR, f.replace("/", os.sep))
        if os.path.exists(src) and not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy(src, dst)
    notes.append("cdn_cache → build/web/cdn подложится автоматически")


def main():
    fetch_missing = "--fetch" in sys.argv
    print("ПРОВЕРКА КОМПЛЕКТА СБОРКИ" + (" (с докачкой)" if fetch_missing else ""))
    check_venv(fetch_missing)
    check_wheel(fetch_missing)
    check_fonts(fetch_missing)
    check_sdk(fetch_missing)
    check_cdn(fetch_missing)
    print()
    for n in notes:
        print("  * " + n)
    if problems:
        print(f"\nНЕ ХВАТАЕТ: {len(problems)} — запусти  py mobile/setup.py --fetch")
        sys.exit(1)
    print("ВСЁ НА МЕСТЕ — сборка идёт офлайн:\n"
          "    py mobile/rebuild.py")


if __name__ == "__main__":
    main()
