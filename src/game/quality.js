// Two levels for the prototype. Lite is the default (as in the Quran game): DPR ≤ 1, no shadow
// map, 30 fps cap, a thinner crowd and colonnade. "Normal" adds a sun shadow map, a fuller crowd
// and a higher resolution. ?q=lite|normal or the ⚙ button (saved in localStorage) picks it.
const KEY = 'umrah-journey-quality';
const read = () => { try { return localStorage.getItem(KEY); } catch { return null; } };

export const PRESETS = {
  lite:   { name: 'lite',   dpr: 1,   shadows: false, fps: 30, tawafCrowd: 4, saiCrowd: 4, columns: 48, label: 'خفيف' },
  normal: { name: 'normal', dpr: 1.5, shadows: true,  fps: 60, tawafCrowd: 4, saiCrowd: 4, columns: 84, label: 'عادي' },
};
const pick = new URLSearchParams(location.search).get('q') || read() || 'lite';
export const Q = PRESETS[pick] || PRESETS.lite;
export const dpr = () => Math.min(Q.dpr, window.devicePixelRatio || 1);
export function toggleQuality() {
  const nextQ = Q.name === 'lite' ? 'normal' : 'lite';
  try { localStorage.setItem(KEY, nextQ); } catch { /* private mode */ }
  const u = new URL(location.href); u.searchParams.delete('q'); location.href = u.toString();
}
