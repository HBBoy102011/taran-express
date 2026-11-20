# -*- coding: utf-8 -*-
"""Добавляет к собранной веб-версии PWA-слой: манифест, иконки, service worker.

Запускать после `py mobile/rebuild.py` (или pygbag + prepare_offline.py):

    py mobile/make_pwa.py

Скрипт идемпотентен: повторный запуск обновляет блоки разметки, а не дублирует их.
"""
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "build", "web")
SRC = os.path.join(HERE, "pwa")
ICONS = os.path.join(WEB, "icons")
LOGO = os.path.join(HERE, "logo.png")
MANIFEST = os.path.join(HERE, "..", "apk", "AndroidManifest.xml")

HEAD_MARK = "<!-- pwa-head -->"
BODY_MARK = "<!-- pwa-body -->"


def fail(msg):
    sys.exit("ошибка: " + msg)


def read_version():
    try:
        with open(MANIFEST, encoding="utf-8") as f:
            xml = f.read()
        m = re.search(r'android:versionName="([^"]+)"', xml)
        code = re.search(r'android:versionCode="(\d+)"', xml)
        if m:
            return m.group(1), (code.group(1) if code else "0")
    except OSError:
        pass
    return "0.0", "0"


def make_icons():
    """192/512/maskable/apple из logo.png (256×256)."""
    from PIL import Image

    if not os.path.exists(LOGO):
        fail("нет mobile/logo.png — не из чего делать иконки")
    os.makedirs(ICONS, exist_ok=True)
    src = Image.open(LOGO).convert("RGBA")
    out = []

    def rounded(size, path, radius_ratio=0.22):
        """Иконка с фирменным фоном и скруглением по краям."""
        base = Image.new("RGBA", (size, size), (7, 11, 24, 255))
        art = src.resize((size, size), Image.LANCZOS)
        base.alpha_composite(art)
        mask = Image.new("L", (size, size), 0)
        from PIL import ImageDraw
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, size - 1, size - 1), radius=int(size * radius_ratio), fill=255)
        base.putalpha(mask)
        base.save(path, "PNG", optimize=True)
        out.append(path)

    rounded(192, os.path.join(ICONS, "icon-192.png"))
    rounded(512, os.path.join(ICONS, "icon-512.png"))
    # apple не любит прозрачность — на тёмном фоне
    apple = Image.new("RGBA", (180, 180), (7, 11, 24, 255))
    apple.alpha_composite(src.resize((180, 180), Image.LANCZOS))
    apple.convert("RGB").save(os.path.join(ICONS, "apple-180.png"), "PNG", optimize=True)
    out.append(os.path.join(ICONS, "apple-180.png"))
    # maskable: логотип в «безопасной зоне» 78% от площади
    m = Image.new("RGBA", (512, 512), (7, 11, 24, 255))
    inner = src.resize((400, 400), Image.LANCZOS)
    m.alpha_composite(inner, ((512 - 400) // 2, (512 - 400) // 2))
    m.convert("RGB").save(os.path.join(ICONS, "maskable-512.png"), "PNG", optimize=True)
    out.append(os.path.join(ICONS, "maskable-512.png"))
    return out


def copy_assets():
    copied = []
    for name in ("manifest.webmanifest", "sw.js", "pwa.js"):
        src = os.path.join(SRC, name)
        if not os.path.exists(src):
            fail("нет файла " + src)
        shutil.copy(src, os.path.join(WEB, name))
        copied.append(name)
    return copied


def write_sw(version):
    path = os.path.join(WEB, "sw.js")
    with open(path, encoding="utf-8") as f:
        js = f.read()
    if "__VERSION__" in js:
        js = js.replace("__VERSION__", version)
        with open(path, "w", encoding="utf-8") as f:
            f.write(js)
    elif version not in js:
        print("внимание: в sw.js нет метки версии — кэш не будет обновляться")


HEAD = HEAD_MARK + """
<link rel="manifest" href="manifest.webmanifest">
<meta name="theme-color" content="#070b18">
<meta name="application-name" content="ТАРАН-ЭКСПРЕСС">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="ТАРАН">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="apple-touch-icon" href="icons/apple-180.png">
<link rel="icon" type="image/png" sizes="192x192" href="icons/icon-192.png">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<!-- /pwa-head -->"""

BODY = BODY_MARK + """
<script src="pwa.js" defer></script>
<!-- /pwa-body -->"""


def patch_index():
    path = os.path.join(WEB, "index.html")
    if not os.path.exists(path):
        fail("нет build/web/index.html — сначала соберите веб-версию")
    with open(path, encoding="utf-8") as f:
        html = f.read()
    # одна ссылка на CDN — это строка-патч внутри prepare_offline, а не реальный запрос
    if html.count("pygame-web.github.io") > 1 or "pygbag_cdn_patch" not in html:
        print("внимание: index.html ещё ходит на внешний CDN — сначала prepare_offline.py")

    html = re.sub(re.escape(HEAD_MARK) + r".*?<!-- /pwa-head -->", "", html, flags=re.S)
    html = re.sub(re.escape(BODY_MARK) + r".*?<!-- /pwa-body -->", "", html, flags=re.S)
    # свой viewport: старый убираем, чтобы не было двух тегов
    html = re.sub(r'<meta\s+name="viewport"[^>]*>\s*', "", html, flags=re.I)

    if "</head>" in html:
        html = html.replace("</head>", HEAD + "</head>", 1)
    else:
        fail("в index.html нет </head> — шаблон pygbag изменился")
    if "</body>" in html:
        html = html.replace("</body>", BODY + "</body>", 1)
    else:
        html = html.replace("</html>", BODY + "</html>", 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def write_warm_list():
    """Список файлов рантайма для «прогрева» кэша после первого запуска.
    Имена версионные, поэтому берём их из самой сборки, а не из констант."""
    urls = []
    cdn = os.path.join(WEB, "cdn")
    for root, _dirs, names in os.walk(cdn):
        for n in names:
            if n.endswith((".js", ".wasm", ".data", ".json", ".whl", ".ogg", ".py", ".html")):
                full = os.path.join(root, n)
                rel = os.path.relpath(full, WEB).replace(os.sep, "/")
                if "vtx" in rel or "xterm" in rel:
                    continue
                urls.append(rel)
    if os.path.exists(os.path.join(WEB, "mobile.apk")):
        urls.append("mobile.apk")
    urls.sort()
    with open(os.path.join(WEB, "warm.json"), "w", encoding="utf-8") as f:
        json.dump(urls, f, ensure_ascii=False, indent=0)
    return urls


def main():
    if not os.path.isdir(WEB):
        fail("нет каталога build/web")
    version, code = read_version()
    icons = make_icons()
    files = copy_assets()
    write_sw(version)
    warm = write_warm_list()
    patch_index()

    total = 0
    for root, _dirs, names in os.walk(WEB):
        for n in names:
            total += os.path.getsize(os.path.join(root, n))
    print("версия:", version, "(versionCode " + code + ", кэш taran-express-" + version + ")")
    print("иконки:", ", ".join(os.path.basename(p) for p in icons))
    print("файлы:", ", ".join(files), "+ warm.json (", len(warm), "шт.)")
    print(f"готово: build/web ({total / 1024 / 1024:.1f} МБ)")
    print("локальный запуск: py mobile/serve_web.py 8099")


if __name__ == "__main__":
    main()
