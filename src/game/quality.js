// Two quality levels. Lite is the default: DPR <= 1, LOD1 meshes, no shadow map,
// 30 fps cap, and lighter instanced crowds. "Normal" upgrades to LOD0 meshes,
// sun shadow map, higher DPR, 60 fps, and fuller instanced crowds.
// ?q=lite|normal or the settings button (saved in localStorage) selects it.
const KEY = 'umrah-journey-quality';
const read = () => { try { return localStorage.getItem(KEY); } catch { return null; } };

export const PRESETS = {
  lite: {
    name: 'lite',
    lod: 'LOD1',
    dpr: 1,
    shadows: false,
    fps: 30,
    tawafCrowd: 56,
    saiCrowd: 36,
    airportCrowd: 40,
    makkahCrowd: 64,
    label: 'خفيف',
  },
  normal: {
    name: 'normal',
    lod: 'LOD0',
    dpr: 1.5,
    shadows: true,
    fps: 60,
    tawafCrowd: 140,
    saiCrowd: 84,
    airportCrowd: 95,
    makkahCrowd: 150,
    label: 'عادي',
  },
};

const pick = new URLSearchParams(location.search).get('q') || read() || 'lite';
export const Q = PRESETS[pick] || PRESETS.lite;
export const dpr = () => Math.min(Q.dpr, window.devicePixelRatio || 1);

export function toggleQuality() {
  const nextQ = Q.name === 'lite' ? 'normal' : 'lite';
  try { localStorage.setItem(KEY, nextQ); } catch { /* private mode */ }
  const u = new URL(location.href);
  u.searchParams.delete('q');
  location.href = u.toString();
}
