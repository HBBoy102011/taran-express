/* Service worker «ТАРАН-ЭКСПРЕСС».
 *
 * Стратегия:
 *   • при установке кэшируем оболочку (страницу, манифест, иконки);
 *   • всё остальное с того же origin (cdn-рантайм, mobile.apk, шрифты) —
 *     cache-first: первый запуск скачивает и запоминает, дальше игра
 *     работает без сети;
 *   • навигация — network-first, чтобы обновление сборки подхватывалось,
 *     а без сети отдаём сохранённую страницу.
 *
 * Версию подставляет mobile/make_pwa.py при сборке: смена версии = новый кэш
 * и удаление старого на активации.
 */
const VERSION = "__VERSION__";
const CACHE = "taran-express-" + VERSION;
const SHELL = [
  "",
  "index.html",
  "manifest.webmanifest",
  "logo.png",
  "favicon.png",
  "icons/icon-192.png",
  "icons/icon-512.png",
  "icons/maskable-512.png",
  "icons/apple-180.png",
];

const abs = (p) => new URL(p, self.registration.scope).href;

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    // fetch + put, а не cache.add: сервер отдаёт Cache-Control: no-store,
    // и add() на таких ответах отваливается молча
    await Promise.all(SHELL.map(async (p) => {
      try {
        const res = await fetch(abs(p), { cache: "reload" });
        if (res && (res.ok || res.type === "opaque")) await cache.put(abs(p), res);
      } catch (e) {
        // одна неудача не должна ломать установку целиком
      }
    }));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.map((n) => (n === CACHE ? null : caches.delete(n))));
    await self.clients.claim();
  })());
});

self.addEventListener("message", (event) => {
  const data = event.data;
  if (data === "SKIP_WAITING") {
    self.skipWaiting();
    return;
  }
  if (data && data.type === "WARM") {
    event.waitUntil(warm().then((info) => {
      self.clients.matchAll({ includeUncontrolled: true }).then((cs) => {
        cs.forEach((c) => c.postMessage({ type: "WARM_DONE", info }));
      });
    }).catch((err) => {
      self.clients.matchAll({ includeUncontrolled: true }).then((cs) => {
        cs.forEach((c) => c.postMessage({ type: "WARM_ERROR", info: String(err) }));
      });
    }));
  }
});

/* Прогрев кэша: main.js и часть рантайма грузятся до того, как SW начнёт
 * управлять страницей. Тянем их сами — последовательно, чтобы не мешать игре. */
async function warm() {
  const cache = await caches.open(CACHE);
  const res = await fetch(abs("warm.json"), { cache: "no-store" });
  if (!res.ok) return { error: "warm.json " + res.status };
  const list = await res.json();
  if (!Array.isArray(list)) return { error: "warm.json не список" };
  let added = 0, skipped = 0, failed = 0;
  for (const rel of list) {
    const url = abs(rel);
    if (await cache.match(url)) { skipped++; continue; }
    try {
      const r = await fetch(url, { cache: "reload" });
      if (r && (r.ok || r.type === "opaque")) { await cache.put(url, r); added++; }
      else failed++;
    } catch (e) {
      failed++;
    }
  }
  return { added, skipped, failed, total: list.length };
}

async function networkFirst(request, fallbackPath) {
  const cache = await caches.open(CACHE);
  try {
    const fresh = await fetch(request);
    if (fresh && fresh.ok) cache.put(request, fresh.clone()).catch(() => {});
    return fresh;
  } catch (e) {
    const cached = (await cache.match(request)) ||
      (fallbackPath ? await cache.match(abs(fallbackPath)) : null);
    if (cached) return cached;
    throw e;
  }
}

// небольшие файлы оболочки обновляем из сети, чтобы новая сборка подхватывалась сразу
const FRESH = /(?:index\.html|pwa\.js|manifest\.webmanifest|warm\.json)$/;

async function cacheFirst(request) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request);
  if (cached) return cached;
  const fresh = await fetch(request);
  if (fresh && (fresh.ok || fresh.type === "opaque")) {
    cache.put(request, fresh.clone()).catch(() => {});
  }
  return fresh;
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  let url;
  try {
    url = new URL(request.url);
  } catch (e) {
    return;
  }
  if (url.origin !== self.location.origin) return;
  if (url.pathname.endsWith("/sw.js")) return;

  if (request.mode === "navigate") {
    event.respondWith(networkFirst(request, "index.html"));
    return;
  }
  if (FRESH.test(url.pathname)) {
    event.respondWith(networkFirst(request));
    return;
  }
  event.respondWith(cacheFirst(request));
});
