# -*- coding: utf-8 -*-
"""Переводит собранную pygbag-страницу на локальный рантайм.

pygbag по умолчанию тянет CPython-WASM и SDL с сайта pygame-web.github.io —
без интернета игра бы не запустилась. Скрипт подменяет ссылки на папку cdn/
внутри сборки и проверяет, что все файлы на месте.

    py mobile/prepare_offline.py
"""
import os
import shutil
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

# --- оптимизации старта -------------------------------------------------
# 1) выключаем терминал vtx (data-os без "vtx"): иначе рантайм грузит xterm.js (~340 КБ),
#    рисует в него лог CPython и тратит на это время старта. Файлы xterm из сборки удаляем.
html = html.replace('data-os="vtx,snd,gui"', 'data-os="snd,gui"')

# 2) ссылка на browserfs.min.js в сборке битая — файла нет, каждый запуск ловил 404.
#    В офлайн-APK такие запросы возвращают ответ «нет файла» и замедляют загрузку.
html = html.replace('<script src="/cdn/0.9.3//browserfs.min.js"></script>', '')

# 3) pygbag распаковывает файлы игры из архива двумя разными путями:
#    mobile.apk (zip, быстрая распаковка) — только если хост выглядит как itch.zone.
#    Всегда выбираем этот путь: на телефоне он быстрее, чем gzip-архив mobile.tar.gz.
needle = "if platform.window.location.host.find('.itch.zone')>0:"
assert needle in html, 'условие itch.zone не найдено'
html = html.replace(needle, 'if True:  # оптимизация: всегда fast-path mobile.apk (zip)')

# 4) если терминал выключен, xterm в сборке больше не нужен — убираем, чтобы не попал в APK
for _f in ("vtx.js", os.path.join("vt", "xterm.js"), os.path.join("vt", "xterm.css"),
           os.path.join("vt", "xterm-addon-image.js")):
    _p = os.path.join(WEB, "cdn", _f)
    if os.path.exists(_p):
        os.remove(_p)

# --- запуск без «серого экрана» -----------------------------------------
# 1) pygbag по умолчанию ждёт «жест пользователя», чтобы разблокировать звук.
#    В WebView этот флаг иногда не срабатывает — игра навсегда остаётся серой.
#    Отключаем блокировку: игра стартует сразу, а SDL сам включит AudioContext
#    при первом касании (emscripten autoResumeAudioContext).
assert "ume_block : 1" in html, "не найден ume_block в index.html"
html = html.replace("ume_block : 1", "ume_block : 0", 1)

# 2) серый фон шаблона заменяем на фирменный тёмный — даже до загрузки
html = html.replace('platform.document.body.style.background = "#7f7f7f"',
                    'platform.document.body.style.background = "#070b18"')
html = html.replace("background-color:powderblue;", "background-color:#070b18;")

# 2б) pygbag по умолчанию рисует картинку в половину экрана (gui_divider=2):
#     на телефоне игра получалась маленьким окошком посреди чёрного поля.
#     Делитель 1 — канвас занимает весь экран, пропорции сохраняет сам рантайм.
html = html.replace("gui_divider : 2,", "gui_divider : 1,", 1)

# 3) заголовок страницы и логотип
html = html.replace("<title>mobile</title>", "<title>ТАРАН-ЭКСПРЕСС</title>")
logo_src = os.path.join(HERE, "logo.png")
if os.path.exists(logo_src):
    shutil.copy(logo_src, os.path.join(WEB, "logo.png"))
    shutil.copy(logo_src, os.path.join(WEB, "favicon.png"))

BOOT_CSS = """
<style id="boot-style">
  /* сцена занимает ровно экран: без полос прокрутки и без «уезжания» за края */
  html, body {
    margin: 0 !important; padding: 0 !important;
    width: 100% !important; height: 100% !important;
    max-width: 100vw; max-height: 100vh;
    overflow: hidden !important;
    background: #070b18 !important;
    overscroll-behavior: none;
    touch-action: none;
  }
  /* зелёная плашка pygbag «Loading, please wait ...» → тёмная */
  #infobox {
    background: rgba(10, 17, 36, .94) !important;
    color: #dbe6ff !important;
    border: 1px solid rgba(120, 170, 235, .35);
    border-radius: 12px;
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
  }
  #status { color: #8fa3c8 !important; }
  #transfer { background: transparent !important; }
  @keyframes boot-stripes { from { background-position: 0 0; } to { background-position: 40px 0; } }
  #boot-screen {
    position: fixed; inset: 0; z-index: 2147483647;
    display: flex; align-items: center; justify-content: center;
    background: radial-gradient(circle at 50% 30%, #142a52 0%, #0a1124 55%, #05070f 100%);
    color: #eef4ff; font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
    transition: opacity .55s ease;
    -webkit-tap-highlight-color: transparent;
  }
  #boot-screen.boot-hide { opacity: 0; pointer-events: none; }
  .boot-inner { width: min(86vw, 430px); text-align: center; }
  .boot-badge {
    width: 108px; height: 108px; margin: 0 auto 14px;
    border-radius: 26px; overflow: hidden;
    box-shadow: 0 0 0 2px rgba(255,205,90,.55), 0 14px 50px rgba(0,0,0,.65), 0 0 46px rgba(70,190,255,.25);
    animation: boot-pulse 2.4s ease-in-out infinite;
  }
  @keyframes boot-pulse { 0%,100% { transform: translateY(0) scale(1); } 50% { transform: translateY(-4px) scale(1.02); } }
  .boot-badge img { width: 100%; height: 100%; display: block; }
  .boot-inner h1 {
    margin: 0; font-size: clamp(23px, 5.2vw, 34px); letter-spacing: 2.5px;
    font-weight: 900; color: #fff; text-shadow: 0 0 22px rgba(90,200,255,.45);
  }
  .boot-tag { margin: 6px 0 22px; font-size: 13px; letter-spacing: 1.4px; color: #ffd76a; text-transform: uppercase; }
  .boot-track {
    position: relative; height: 14px; border-radius: 9px; overflow: hidden;
    background: rgba(255,255,255,.09); box-shadow: inset 0 1px 3px rgba(0,0,0,.6);
    border: 1px solid rgba(140,190,255,.22);
  }
  .boot-fill {
    height: 100%; width: 4%; border-radius: 9px;
    background: linear-gradient(90deg, #37a7ff 0%, #6fe3ff 45%, #ffd45e 100%);
    background-size: 40px 40px; box-shadow: 0 0 18px rgba(90,210,255,.55);
    transition: width .35s ease-out;
  }
  .boot-stripes { position: absolute; inset: 0; background-image: linear-gradient(45deg, rgba(255,255,255,.18) 25%, transparent 25%, transparent 50%, rgba(255,255,255,.18) 50%, rgba(255,255,255,.18) 75%, transparent 75%); background-size: 40px 40px; animation: boot-stripes .8s linear infinite; opacity: .45; pointer-events: none; }
  .boot-runner {
    position: absolute; top: 50%; left: 0; width: 30px; height: 30px; margin-top: -15px;
    margin-left: -15px; border-radius: 8px; box-shadow: 0 0 14px rgba(255,210,90,.65);
    transition: left .35s ease-out; pointer-events: none;
  }
  .boot-meta { display: flex; justify-content: space-between; align-items: baseline; margin-top: 12px; font-size: 13px; color: #b9c8e8; }
  .boot-meta b { font-size: 18px; color: #fff; font-variant-numeric: tabular-nums; }
  .boot-note { margin-top: 12px; font-size: 12px; line-height: 1.45; color: #8494b5; }
  .boot-note.boot-err { color: #ffb3a8; }
  .boot-note button {
    margin-top: 10px; padding: 9px 18px; border: 0; border-radius: 10px; cursor: pointer;
    background: linear-gradient(180deg,#ffd45e,#e8a92f); color: #1a1408; font-weight: 800; font-size: 14px;
  }
</style>
"""

BOOT_HTML = """
<div id="boot-screen">
  <div class="boot-inner">
    <div class="boot-badge"><img src="/logo.png" alt=""></div>
    <h1>ТАРАН-ЭКСПРЕСС</h1>
    <div class="boot-tag">Рельсы. Толпа. Хаос.</div>
    <div class="boot-track">
      <div class="boot-fill" id="boot-fill"></div>
      <div class="boot-stripes"></div>
      <img class="boot-runner" id="boot-runner" src="/logo.png" alt="">
    </div>
    <div class="boot-meta"><span id="boot-status">Загрузка игры…</span><b id="boot-pct">0%</b></div>
    <div class="boot-note" id="boot-note">Первый запуск может занять до минуты: распаковывается движок Python.</div>
  </div>
</div>
<script>
(function () {
  var FILES = {
    "/cdn/0.9.3/cpython312/main.wasm": 13447111,
    "/cdn/0.9.3/cpython312/main.data": 6668609,
    "/cdn/0.9.3/cpython312/main.js": 849985,
    "/cdn/0.9.3/pythons.js": 69205,
    "/cdn/cp312/pygame_ce-2.5.7-cp312-cp312-wasm32_bi_emscripten.whl": 1527290,
    "/mobile.apk": 1151636
  };
  var TOTAL = 0, k;
  for (k in FILES) TOTAL += FILES[k];

  var screen = document.getElementById("boot-screen");
  var fill = document.getElementById("boot-fill");
  var runner = document.getElementById("boot-runner");
  var pct = document.getElementById("boot-pct");
  var statusEl = document.getElementById("boot-status");
  var note = document.getElementById("boot-note");
  var t0 = performance.now();
  var shown = 0, started = false, lastGrow = 0, lastGrowAt = t0;

  function setShown(p) {
    p = Math.max(shown, Math.min(100, p));
    shown = p;
    if (fill) fill.style.width = p.toFixed(1) + "%";
    if (runner) runner.style.left = p.toFixed(1) + "%";
    if (pct) pct.textContent = Math.round(p) + "%";
  }

  function bytesLoaded() {
    var got = {}, total = 0;
    var entries = performance.getEntriesByType("resource") || [];
    for (var i = 0; i < entries.length; i++) {
      var name = String(entries[i].name || "").split("?")[0].split("#")[0];
      for (var key in FILES) {
        if (name.slice(-key.length) === key) {
          var sz = Math.max(entries[i].decodedBodySize || 0, entries[i].transferSize || 0);
          if (sz > (got[key] || 0)) got[key] = sz;
        }
      }
    }
    for (var key2 in got) total += Math.min(got[key2], FILES[key2]);
    return total;
  }

  function tick() {
    if (started) return;
    var target = bytesLoaded() / TOTAL;             // 0..1
    var idle = Math.min(4, (performance.now() - t0) / 9000);  // лёгкое движение, пока файл качается
    var base = 4 + target * 86 + idle;
    try { if (window.python && window.python.is_ready) base = Math.max(base, 93); } catch (e) {}
    base = Math.min(base, 97);
    setShown(shown + (base - shown) * 0.09);
    if (statusEl) {
      if (shown > 92) statusEl.textContent = "Запускаем движок…";
      else if (shown > 68) statusEl.textContent = "Готовим Python…";
      else if (shown > 30) statusEl.textContent = "Загружаем игровые файлы…";
      else if (shown > 7) statusEl.textContent = "Грузим движок…";
    }
    if (shown > lastGrow + 0.25) { lastGrow = shown; lastGrowAt = performance.now(); }
    if (performance.now() - lastGrowAt > 26000 && note && !note.dataset.slow) {
      note.dataset.slow = "1";
      note.textContent = "Загрузка идёт дольше обычного. На слабом телефоне это нормально — подождите ещё немного.";
    }
    requestAnimationFrame(tick);
  }

  window.__gameBootDone = function () {
    if (started) return;
    started = true;
    setShown(100);
    if (statusEl) statusEl.textContent = "Поехали!";
    try { if (window.AndroidApp && AndroidApp.gameReady) AndroidApp.gameReady(); } catch (e) {}
    setTimeout(function () {
      if (!screen) return;
      screen.className += " boot-hide";
      setTimeout(function () { if (screen && screen.parentNode) screen.parentNode.removeChild(screen); }, 650);
    }, 320);
  };

  window.__bootError = function (msg) {
    if (started) return;
    if (statusEl) statusEl.textContent = "Не удалось запустить";
    if (note) {
      note.className = "boot-note boot-err";
      note.innerHTML = "<b>Ошибка:</b> " + String(msg || "неизвестная") +
        "<br><button onclick=\\"location.reload()\\">Перезапустить</button>";
    }
  };

  // страховка: шаблон прячет infobox ровно тогда, когда игра начала рисовать
  function hookInfobox() {
    var inf = document.getElementById("infobox");
    if (inf && window.MutationObserver) {
      new MutationObserver(function () {
        if (!started && inf.style.display === "none") window.__gameBootDone();
      }).observe(inf, { attributes: true, attributeFilter: ["style"] });
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", hookInfobox);
  else hookInfobox();

  // если через 50 секунд прогресс встал — показываем кнопку перезапуска
  setInterval(function () {
    if (started) return;
    if (performance.now() - t0 > 50000 && shown < 97 && note && !note.dataset.stuck) {
      note.dataset.stuck = "1";
      note.innerHTML = "Похоже, загрузка застряла.<br><button onclick=\\"location.reload()\\">Перезапустить игру</button>";
    }
  }, 1500);

  window.addEventListener("error", function (ev) {
    if (!started && ev && ev.message && /wasm|memory|WebAssembly|fetch/i.test(ev.message)) {
      window.__bootError(ev.message);
    }
  }, true);

  setShown(4);
  requestAnimationFrame(tick);
})();
</script>
"""
assert "<body>" in html, "в index.html нет <body> — шаблон pygbag изменился"
assert "</head>" in html, "в index.html нет </head> — шаблон pygbag изменился"
html = html.replace("</head>", BOOT_CSS + "</head>", 1)
html = html.replace("<body>", "<body>" + BOOT_HTML, 1)

open(idx, "w", encoding="utf-8").write(html)

# считаем внешние ссылки только в самой странице — строка из патча выше и есть адрес CDN
left = html.count("pygame-web.github.io") - PATCH.count("pygame-web.github.io")
total = sum(os.path.getsize(os.path.join(WEB, f.replace("/", os.sep))) for f in NEEDED
            if os.path.exists(os.path.join(WEB, f.replace("/", os.sep))))
print(f"index.html обновлён: заменено ссылок {'да' if before != html else 'нет (уже локальные)'}")
print(f"внешних ссылок осталось: {left}")
print(f"размер сборки: {total / 1024 / 1024:.1f} МБ")
