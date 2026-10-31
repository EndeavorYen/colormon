/* 顏色寶可夢探險的 Service Worker
   - 寶可夢和寶可夢球的圖片（PokeAPI，放在 GitHub）：第一次下載後存在手機裡，之後直接用，不再上網抓
     （PokeAPI 圖片本身只允許瀏覽器快取 5 分鐘，所以要自己存）
   - 網頁本身和資料檔：先上網拿最新版，沒網路時才用手機裡存的（所以改版會馬上看到，離線也能開） */
const IMG_CACHE = "colormon-img-v1";
const APP_CACHE = "colormon-app-v1";
const MODEL_CACHE = "colormon-model-v1";
const IMG_MAX = 1500;                         // 圖片最多存幾張（全部寶可夢＋球大約 1100 張）

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  if (url.hostname === "raw.githubusercontent.com" && url.pathname.startsWith("/PokeAPI/sprites/")) {
    e.respondWith(cacheFirst(url.href));
    return;
  }
  // 物品辨識的程式庫和模型（約 6MB，檔名有版本號、不會變）：存一次就一直用，不要每次重新下載
  if (url.origin === self.location.origin && /^\/(vendor|models)\//.test(url.pathname)) {
    e.respondWith(caches.open(MODEL_CACHE).then(async c => (await c.match(req)) || fetch(req).then(r => { if (r.ok) c.put(req, r.clone()); return r; })));
    return;
  }
  if (url.origin === self.location.origin) {
    e.respondWith(networkFirst(req));
  }
});

async function cacheFirst(href) {
  const cache = await caches.open(IMG_CACHE);
  const hit = await cache.match(href);
  if (hit) return hit;
  const res = await fetch(href, { mode: "cors" });       // PokeAPI 圖片允許跨網域，存下來的是完整圖片
  if (res.ok) {
    await cache.put(href, res.clone());
    trim(cache);
  }
  return res;
}

async function networkFirst(req) {
  try {
    const res = await fetch(req);
    if (res.ok) {
      const copy = res.clone();
      caches.open(APP_CACHE).then(c => c.put(req, copy));
    }
    return res;
  } catch (err) {
    const hit = await caches.match(req);
    if (hit) return hit;
    throw err;
  }
}

async function trim(cache) {
  const keys = await cache.keys();
  if (keys.length > IMG_MAX) {
    for (const k of keys.slice(0, keys.length - IMG_MAX)) await cache.delete(k);
  }
}
