# -*- coding: utf-8 -*-
"""Переводит собранную pygbag-страницу на локальный рантайм.

pygbag по умолчанию тянет CPython-WASM и SDL с сайта pygame-web.github.io —
без интернета игра бы не запустилась. Скрипт подменяет ссылки на папку cdn/
внутри сборки и проверяет, что все файлы на месте.

    py mobile/prepare_offline.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "build", "web")

NEEDED = [
    "index.html",
    "mobile.apk",
    "cdn/index-0.9.3-cp312.json",
    "cdn/cp312/pygame_ce-2.5.7-cp312-cp312-wasm32_bi_emscripten.whl",
    "cdn/0.9.3/pythons.js",
    "cdn/0.9.3/empty.html",
    "cdn/0.9.3/empty.ogg",
    "cdn/0.9.3/cpython312/main.js",
    "cdn/0.9.3/cpython312/main.data",
    "cdn/0.9.3/cpython312/main.wasm",
    "cdn/vtx.js",
    "cdn/vt/xterm.css",
    "cdn/vt/xterm.js",
    "cdn/vt/xterm-addon-image.js",
]

missing = [f for f in NEEDED if not os.path.exists(os.path.join(WEB, f.replace("/", os.sep)))]
if missing:
    sys.exit("нет файлов рантайма: " + ", ".join(missing) + "\nскачай их в mobile/build/web (см. dl_runtime.log)")

idx = os.path.join(WEB, "index.html")
html = open(idx, encoding="utf-8").read()
before = html
# ссылки обязаны быть абсолютными ("/cdn/..."): внутри рантайма есть импорты вида
# config.cdn + "../vt/xterm.js", и относительный путь с ".." браузер считает
# именем модуля и отказывается его загружать
html = html.replace("https://pygame-web.github.io/cdn/", "/cdn/")
html = html.replace('src="cdn/', 'src="/cdn/')
html = html.replace('"cdn/', '"/cdn/')
html = html.replace('href="cdn/', 'href="/cdn/')
# рантайм пытается поставить service worker с CDN — локально файла нет, убираем строку
html = html.replace(
    'navigator.serviceWorker.register("/cdn/0.9.3/pygbag0.9.3.js")',
    "void 0 // service worker только у хостинга pygbag",
)

# рантайм в момент работы сам ходит на сайт pygbag за индексом пакетов и колесом pygame.
# На телефоне интернета может не быть, поэтому перехватываем эти обращения на уровне
# страницы и подменяем локальной папкой cdn/ (см. той же заменой выше ссылок).
PATCH = '''<script>
(function () {
  var CDN = "https://pygame-web.github.io/cdn/";
  function fix(u) {
    return typeof u === "string" && u.indexOf(CDN) === 0 ? "/cdn/" + u.slice(CDN.length) : u;
  }
  var of = window.fetch;
  window.fetch = function (input, init) {
    try {
      if (typeof input === "string") input = fix(input);
      else if (input && typeof input.url === "string" && input.url.indexOf(CDN) === 0)
        input = new Request(fix(input.url), input);
    } catch (e) {}
    return of.call(this, input, init);
  };
  var ox = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (m, u) {
    var a = Array.prototype.slice.call(arguments);
    a[1] = fix(u);
    return ox.apply(this, a);
  };
})();
</script>'''
if "pygbag_cdn_patch" not in html:
    html = html.replace("<head>", "<head><!-- pygbag_cdn_patch -->" + PATCH, 1)

# локальный индекс пакетов тоже ссылается на внешний CDN — делаем путь относительным
idx_json = os.path.join(WEB, "cdn", "index-0.9.3-cp312.json")
if os.path.exists(idx_json):
    s = open(idx_json, encoding="utf-8").read()
    s2 = s.replace('"https://pygame-web.github.io/cdn/"', '"/cdn/"')
    if s2 != s:
        open(idx_json, "w", encoding="utf-8").write(s2)

open(idx, "w", encoding="utf-8").write(html)

# считаем внешние ссылки только в самой странице — строка из патча выше и есть адрес CDN
left = html.count("pygame-web.github.io") - PATCH.count("pygame-web.github.io")
total = sum(os.path.getsize(os.path.join(WEB, f.replace("/", os.sep))) for f in NEEDED
            if os.path.exists(os.path.join(WEB, f.replace("/", os.sep))))
print(f"index.html обновлён: заменено ссылок {'да' if before != html else 'нет (уже локальные)'}")
print(f"внешних ссылок осталось: {left}")
print(f"размер сборки: {total / 1024 / 1024:.1f} МБ")
