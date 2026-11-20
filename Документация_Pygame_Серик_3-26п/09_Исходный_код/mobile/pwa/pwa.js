/* PWA-обвязка «ТАРАН-ЭКСПРЕСС»: установка с сайта, офлайн, обновления.
 * Не вмешивается в canvas и тач-управление игры: весь UI — одна плашка.
 */
(function () {
  "use strict";

  var standalone = window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true;
  var isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  var inShell = !!window.AndroidApp || /TaranExpress/.test(navigator.userAgent);

  function el(tag, css, html) {
    var n = document.createElement(tag);
    if (css) n.setAttribute("style", css);
    if (html) n.innerHTML = html;
    return n;
  }

  // ---- офлайн-кэш: просим браузер не вычищать наши файлы ----
  try {
    if (navigator.storage && navigator.storage.persist) navigator.storage.persist();
  } catch (e) {}

  // ---- service worker ----
  var reg = null;
  function bootSW() {
    if (reg) return;
    navigator.serviceWorker.register("sw.js", { scope: "./" }).then(function (r) {
        reg = r;
        if (r.waiting) askUpdate(r);
        r.addEventListener("updatefound", function () {
          var sw = r.installing;
          if (!sw) return;
          sw.addEventListener("statechange", function () {
            if (sw.state === "installed" && navigator.serviceWorker.controller) askUpdate(r);
          });
        });
      }).then(function () {
        window.__swState = "registered";
      }).catch(function (err) {
        window.__swState = "error";
        window.__swError = String(err);
      });
  }

  // регистрируемся сразу: обработчик load мог уже отгреметь (скрипт грузится позже)
  if ("serviceWorker" in navigator && location.protocol !== "file:") {
    if (document.readyState === "complete") bootSW();
    else window.addEventListener("load", bootSW);
  }

  // ---- прогрев кэша: main.js и часть рантайма грузятся раньше, чем SW начинает
  // управлять страницей, поэтому просим SW догрузить их сам уже после старта.
  function warmCache(reg) {
    if (!navigator.onLine || !reg) return;
    var sw = reg.active || reg.waiting || reg.installing;
    if (!sw) return;
    try { sw.postMessage({ type: "WARM" }); } catch (e) {}
  }

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.ready.then(function (reg) {
      setTimeout(function () { warmCache(reg); }, 10000);
    }).catch(function () {});
  }

  function askUpdate(r) {
    if (document.getElementById("pwa-update")) return;
    var box = el("div",
      "position:fixed;left:50%;transform:translateX(-50%);bottom:16px;z-index:2147483646;" +
      "display:flex;gap:10px;align-items:center;padding:10px 12px;border-radius:12px;" +
      "background:rgba(10,17,36,.96);border:1px solid rgba(120,170,235,.35);" +
      "box-shadow:0 10px 30px rgba(0,0,0,.55);font:13px/1.3 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;color:#dbe6ff",
      "<span>Новая версия готова</span>");
    box.id = "pwa-update";
    var btn = el("button",
      "border:0;border-radius:9px;padding:8px 14px;cursor:pointer;font-weight:800;" +
      "background:linear-gradient(180deg,#ffd45e,#e8a92f);color:#1a1408;font-size:13px",
      "Обновить");
    btn.onclick = function () {
      if (r && r.waiting) r.waiting.postMessage("SKIP_WAITING");
      setTimeout(function () { location.reload(); }, 250);
    };
    box.appendChild(btn);
    document.body.appendChild(box);
  }

  if (standalone || inShell) return;

  // ---- установка на Android/десктоп ----
  var deferred = null;
  var pill = null;

  function showInstall() {
    if (pill) return;
    pill = el("div",
      "position:fixed;right:14px;bottom:14px;z-index:2147483645;display:flex;align-items:center;" +
      "gap:8px;padding:8px 10px 8px 12px;border-radius:999px;background:rgba(10,17,36,.94);" +
      "border:1px solid rgba(120,170,235,.4);box-shadow:0 10px 26px rgba(0,0,0,.5);" +
      "font:13px/1 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;color:#eaf1ff;cursor:pointer");
    pill.innerHTML = "<span style='font-weight:700'>Установить игру</span>";
    pill.onclick = function () {
      if (isIOS) return;
      if (!deferred) return;
      deferred.prompt();
      deferred.userChoice.then(function (res) {
        if (res && res.outcome === "accepted") hide();
        deferred = null;
      });
    };
    document.body.appendChild(pill);
  }

  function hide() {
    if (pill && pill.parentNode) pill.parentNode.removeChild(pill);
    pill = null;
  }

  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferred = e;
    setTimeout(showInstall, 6000);
  });

  window.addEventListener("appinstalled", hide);

  // ---- подсказка для iPhone: там промпта нет вообще ----
  if (isIOS) {
    setTimeout(function () {
      if (document.getElementById("pwa-ios")) return;
      var box = el("div",
        "position:fixed;left:12px;right:12px;bottom:12px;z-index:2147483645;padding:12px 14px;" +
        "border-radius:14px;background:rgba(10,17,36,.96);border:1px solid rgba(120,170,235,.4);" +
        "box-shadow:0 10px 30px rgba(0,0,0,.55);color:#eaf1ff;" +
        "font:13px/1.45 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif",
        "<b>Играть с домашнего экрана:</b> «Поделиться» → «На экран Домой». " +
        "Тогда игра запустится без адресной строки и будет работать офлайн.");
      box.id = "pwa-ios";
      var close = el("button",
        "position:absolute;top:6px;right:8px;border:0;background:transparent;color:#9fb0d4;" +
        "font-size:18px;line-height:1;cursor:pointer;padding:4px", "×");
      close.onclick = function () { box.parentNode.removeChild(box); };
      box.appendChild(close);
      document.body.appendChild(box);
      setTimeout(function () { if (box.parentNode) box.parentNode.removeChild(box); }, 14000);
    }, 12000);
  }
})();
