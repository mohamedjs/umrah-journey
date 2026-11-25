/* رحلة العمرة — service worker (same design as «رحلة مع القرآن», no Workbox).
 * Built by tools/vite-pwa.js, which prepends
 *   self.__PRECACHE = [{ url, rev, size, core }]   (paths relative to this file)
 *   self.__VERSION  = '<hash of that list>'
 * · precache: the app shell, JS/CSS chunks, fonts, icons and every recorded voice line, so the
 *   whole game plays offline after the first visit. Files already cached with the same revision
 *   are kept across versions (an update only downloads what changed). Core files must all
 *   arrive; a voice line that fails is fetched again at runtime.
 * · updates: a new version installs in the background and WAITS; the page shows «تحديث جديد
 *   متاح» and sends SKIP_WAITING when the player taps it, then reloads.
 */
const PRECACHE = self.__PRECACHE || [];
const VERSION = self.__VERSION || 'dev';
const SHELL = 'uj-shell', FONTS = 'uj-fonts';
const scope = new URL(self.registration.scope);
const abs = u => new URL(u, scope).href;
const keyFor = e => abs(e.url) + (e.url.includes('?') ? '&' : '?') + '__rev=' + e.rev;
const byUrl = new Map(PRECACHE.map(e => [abs(e.url), e]));

async function precache() {
  const cache = await caches.open(SHELL), have = new Set((await cache.keys()).map(r => r.url));
  const todo = PRECACHE.filter(e => !have.has(keyFor(e)));
  let i = 0; const failed = [];
  const worker = async () => {
    while (i < todo.length) {
      const e = todo[i++];
      try {
        const r = await fetch(abs(e.url), { cache: 'no-cache', credentials: 'same-origin' });
        if (!r.ok) throw new Error(r.status);
        await cache.put(keyFor(e), r);
      } catch { failed.push(e); }
    }
  };
  await Promise.all(Array.from({ length: 6 }, worker));
  const core = failed.filter(e => e.core);
  if (core.length) throw new Error('precache failed: ' + core.map(e => e.url).join(', '));
}

self.addEventListener('install', e => { e.waitUntil(precache()); });
self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    const cache = await caches.open(SHELL), keep = new Set(PRECACHE.map(keyFor));
    for (const r of await cache.keys()) if (!keep.has(r.url)) await cache.delete(r);
    await self.clients.claim();
    for (const c of await self.clients.matchAll({ type: 'window' })) c.postMessage({ type: 'SW_ACTIVE', version: VERSION });
  })());
});
self.addEventListener('message', e => { if (e.data?.type === 'SKIP_WAITING') self.skipWaiting(); });

// media elements ask for byte ranges; Safari insists on 206
async function ranged(req, res) {
  const range = req.headers.get('range');
  if (!range || !res || res.status !== 200) return res;
  const m = /bytes=(\d*)-(\d*)/.exec(range); if (!m) return res;
  const buf = await res.arrayBuffer(), size = buf.byteLength;
  let start = m[1] === '' ? size - +m[2] : +m[1], end = m[1] === '' || m[2] === '' ? size - 1 : +m[2];
  start = Math.max(0, start); end = Math.min(size - 1, end);
  if (start > end) return new Response(null, { status: 416, headers: { 'Content-Range': `bytes */${size}` } });
  const h = new Headers(res.headers);
  h.set('Content-Range', `bytes ${start}-${end}/${size}`); h.set('Content-Length', String(end - start + 1));
  return new Response(buf.slice(start, end + 1), { status: 206, statusText: 'Partial Content', headers: h });
}
async function fromShell(req, entry) {
  const cache = await caches.open(SHELL);
  let res = await cache.match(keyFor(entry));
  if (!res) {
    try { res = await fetch(abs(entry.url), { credentials: 'same-origin' }); if (res.ok) cache.put(keyFor(entry), res.clone()); }
    catch { return Response.error(); }
  }
  if (req.method === 'HEAD') return new Response(null, { status: res.status, headers: res.headers });
  return ranged(req, res);
}
async function staleWhileRevalidate(req, name) {
  const cache = await caches.open(name), hit = await cache.match(req);
  const net = fetch(req).then(r => { if (r.ok || r.type === 'opaque') cache.put(req, r.clone()); return r; }).catch(() => null);
  if (hit) return hit;
  return (await net) || Response.error();
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' && req.method !== 'HEAD') return;
  const url = new URL(req.url);
  if (url.origin === scope.origin) {
    const clean = url.origin + url.pathname;
    if (req.mode === 'navigate' && clean.startsWith(scope.href)) {
      const shell = byUrl.get(abs('index.html'));
      if (shell) { e.respondWith(fromShell(req, shell)); return; }
    }
    const entry = byUrl.get(clean);
    if (entry) e.respondWith(fromShell(req, entry));
    return;
  }
  if (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com') e.respondWith(staleWhileRevalidate(req, FONTS));
});
