// Installable offline app (same behaviour as «رحلة مع القرآن»):
//  · registers sw.js a few seconds after start (the precache never competes with the first load)
//  · Android / desktop Chrome: «ثبّت اللعبة» button on the title screen + a one-time popup
//  · iOS Safari (no install prompt): a hint «Share ⬆︎ → Add to Home Screen»
//  · a new version waits in the background; «تحديث جديد متاح» reloads into it when tapped
import { useStore } from '../game/store.js';

const supported = 'serviceWorker' in navigator && (location.protocol === 'https:' || ['localhost', '127.0.0.1'].includes(location.hostname));
const DISMISS_KEY = 'umrah-journey-install-dismissed';
let deferred = null;

export const isIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.maxTouchPoints > 1 && /Macintosh/.test(navigator.userAgent));
const isSafari = () => /safari/i.test(navigator.userAgent) && !/crios|fxios|edgios|opios|chrome|android/i.test(navigator.userAgent);
export const isStandalone = () => matchMedia('(display-mode: standalone), (display-mode: fullscreen)').matches || navigator.standalone === true;
const canInstall = () => !isStandalone() && (!!deferred || (isIOS() && isSafari()));
const dismissedRecently = () => { try { return Date.now() - +(localStorage.getItem(DISMISS_KEY) || 0) < 7 * 864e5; } catch { return false; } };
const refresh = () => useStore.setState({ pwa: { ...useStore.getState().pwa, canInstall: canInstall(), ios: !deferred && isIOS() } });

addEventListener('beforeinstallprompt', e => { e.preventDefault(); deferred = e; refresh(); });
addEventListener('appinstalled', () => { deferred = null; refresh(); });

export async function installApp() {
  if (!deferred) return false;
  const e = deferred; deferred = null;
  e.prompt(); const { outcome } = await e.userChoice.catch(() => ({}));
  refresh(); return outcome === 'accepted';
}
export function dismissInstall() {
  try { localStorage.setItem(DISMISS_KEY, String(Date.now())); } catch { /* private mode */ }
  useStore.setState({ pwa: { ...useStore.getState().pwa, popup: false } });
}
export function applyUpdate() {
  const reg = useStore.getState().pwa?.reg;
  reg?.waiting?.postMessage({ type: 'SKIP_WAITING' });
  setTimeout(() => location.reload(), 4000);
}

export function initPWA() {
  useStore.setState({ pwa: { canInstall: canInstall(), ios: isIOS(), popup: false, update: false, ready: false } });
  // the install popup: once offline play works and the browser offers it (or on iOS Safari)
  const offer = setInterval(() => {
    const st = useStore.getState();
    if (!canInstall() || dismissedRecently()) return clearInterval(offer);
    if (supported && !st.pwa?.ready) return;
    if (st.screen === 'play' && (st.dialog?.blocking || st.overlay)) return;   // wait for a calm moment
    clearInterval(offer); useStore.setState({ pwa: { ...st.pwa, popup: true } });
  }, 2500);
  if (!supported) return;
  const hadController = !!navigator.serviceWorker.controller;
  let asked = false;
  navigator.serviceWorker.addEventListener('controllerchange', () => { if (asked) location.reload(); });
  navigator.serviceWorker.addEventListener('message', e => {
    if (e.data?.type !== 'SW_ACTIVE') return;
    useStore.setState({ pwa: { ...useStore.getState().pwa, ready: true } });
    if (!hadController) useStore.setState({ toast: 'اللعبة جاهزة تتلعب من غير إنترنت ✓' }), setTimeout(() => useStore.setState({ toast: '' }), 4000);
  });
  const offerUpdate = reg => { if (reg.waiting) useStore.setState({ pwa: { ...useStore.getState().pwa, update: true, reg } }); };
  setTimeout(async () => {
    try {
      const reg = await navigator.serviceWorker.register(new URL('sw.js', document.baseURI).href, { updateViaCache: 'none' });
      if (navigator.serviceWorker.controller) useStore.setState({ pwa: { ...useStore.getState().pwa, ready: true } });
      if (reg.waiting && navigator.serviceWorker.controller) offerUpdate(reg);
      reg.addEventListener('updatefound', () => {
        const w = reg.installing;
        w?.addEventListener('statechange', () => { if (w.state === 'installed' && navigator.serviceWorker.controller) offerUpdate(reg); });
      });
      setInterval(() => reg.update().catch(() => {}), 30 * 60e3);
      document.addEventListener('visibilitychange', () => { if (!document.hidden) reg.update().catch(() => {}); });
      window.__applyUpdate = () => { asked = true; applyUpdate(); };
    } catch (e) { console.warn('service worker:', e); }
  }, 3000);
}
