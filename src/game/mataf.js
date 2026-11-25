import * as THREE from 'three';
import { makeCrowd, seeded } from './people.js';
import { cloneEnvScene, getCachedGLTF } from './loaders.js';
import { Q } from './quality.js';

// ------------------------------------------------------------------------------------------
// The Mataf. World axes: +x = east, -z = north. Angles are compass-free "math" angles seen
// from above: θ = atan2(-z, x), so θ grows counter-clockwise (east → north → west → south),
// which is the direction of tawaf (the Kaaba on the walker's left).
// The Kaaba's corners point (roughly) to the four directions: the Black Stone corner east (θ=0),
// the Iraqi corner north, the Shami corner west, the Yamani corner south (θ=-90°).
// The door is on the north-east face near the Black Stone; Hijr Ismail is the low semicircle
// off the north-west face; Maqam Ibrahim stands in front of the door side.
// ------------------------------------------------------------------------------------------
export const H = 5.8;                     // half side
export const R = H * Math.SQRT2;          // centre → corner
export const KAABA_H = 13;
export const HIJR = { a: 5.0, b: 8.0, t: 0.9 };
export const MAQAM = { th: 0.62, r: 17.5 };
export const MATAF_R = 45;
export const ang = (x, z) => Math.atan2(-z, x);
export const polar = (th, r, y = 0) => new THREE.Vector3(Math.cos(th) * r, y, -Math.sin(th) * r);
const C = Math.SQRT1_2;
const toLocal = (x, z) => [x * C - z * C, x * C + z * C];
const toWorld = (lx, lz) => [lx * C + lz * C, -lx * C + lz * C];
export const maqamPos = polar(MAQAM.th, MAQAM.r);
export const prayPos = polar(MAQAM.th, MAQAM.r + 3.2);
export const blackStone = new THREE.Vector3(R + 0.05, 1.5, 0);
export const yamaniPos = polar(-Math.PI / 2, R + 0.05, 1.2);

export function buildMataf(assets = {}) {
  const root = new THREE.Group();

  const kaabaGltf = assets.kaaba || getCachedGLTF('models/env/kaaba.glb');
  const maqamGltf = assets.maqam || getCachedGLTF('models/env/maqam.glb');
  const haramGltf = assets.haram || getCachedGLTF('models/env/haram_mataf.glb');
  const crowdGltf = assets.crowd || getCachedGLTF('models/characters/crowd.glb');
  if (!kaabaGltf || !maqamGltf || !haramGltf) {
    throw new Error('kaaba.glb, maqam.glb, and haram_mataf.glb must be loaded before buildMataf()');
  }

  // Realistic Kaaba + Hijr Ismail (already rotated to exact world orientation in kaaba.glb)
  const kaaba = cloneEnvScene(kaabaGltf, { lod: Q.lod, shadows: Q.shadows });
  root.add(kaaba);

  // Realistic Maqam Ibrahim positioned at maqamPos
  const maqam = cloneEnvScene(maqamGltf, { lod: Q.lod, shadows: Q.shadows });
  maqam.position.copy(maqamPos);
  root.add(maqam);

  // Realistic Al-Masjid al-Haram Mataf courtyard, colonnade, green lamp & minarets
  const haram = cloneEnvScene(haramGltf, { lod: Q.lod, shadows: Q.shadows });
  root.add(haram);

  // Gameplay start line along θ = 0 (y = 0.03) from the Black Stone corner outward
  const lineGeo = new THREE.PlaneGeometry(MATAF_R - R - 0.5, 0.32);
  const lineMat = new THREE.MeshStandardMaterial({
    color: 0xffd68c,
    emissive: 0xffb43a,
    emissiveIntensity: 1.1,
    roughness: 0.4,
    transparent: true,
    opacity: 0.85,
  });
  const line = new THREE.Mesh(lineGeo, lineMat);
  line.position.set((MATAF_R + R + 0.5) / 2, 0.03, 0);
  line.rotation.x = -Math.PI / 2;
  root.add(line);

  // Realistic instanced crowd circling counter-clockwise around the Kaaba & Hijr Ismail
  const rnd = seeded(11);
  const crowd = makeCrowd(Q.tawafCrowd, rnd, {
    robeRatio: 0.35,
    bareRatio: 0.85,
    shadows: Q.shadows,
    crowdGltf,
  });
  const agents = crowd.info.map(() => {
    const r = 10 + Math.pow(rnd(), 1.3) * 32;
    return { r, th: rnd() * Math.PI * 2, w: (0.8 + rnd() * 0.6) / r };
  });
  root.add(crowd.group);

  const hijrTh = Math.PI * 0.75;
  function update(dt, t, player) {
    for (let i = 0; i < agents.length; i++) {
      const g = agents[i];
      g.th += g.w * dt;
      let r = g.r;
      const d = Math.abs(Math.atan2(Math.sin(g.th - hijrTh), Math.cos(g.th - hijrTh)));   // keep clear of Hijr Ismail
      if (d < 0.95 && r < 16.2) r += (16.2 - r) * Math.sqrt(1 - d / 0.95);
      let x = Math.cos(g.th) * r, z = -Math.sin(g.th) * r;
      const dx = x - player.x, dz = z - player.z, dd = dx * dx + dz * dz;                 // make room round the player
      if (dd < 2.6) {
        const k = (1.6 - Math.sqrt(dd)) / Math.max(0.2, Math.sqrt(dd));
        x += dx * k;
        z += dz * k;
      }
      crowd.place(i, x, z, g.th + Math.PI, t);
    }
    crowd.commit();
  }

  function dispose() {
    crowd.dispose();
    lineGeo.dispose();
    lineMat.dispose();
  }

  return { root, update, dispose };
}

// push a point out of the Kaaba, Hijr Ismail, the Maqam and keep it in the Mataf.
// returns the name of what it touched ('hijr' | 'kaaba' | 'maqam' | null).
export function collideMataf(p, rad = 0.38) {
  let hit = null;
  let [lx, lz] = toLocal(p.x, p.z);
  // Hijr Ismail (counted as part of the Kaaba: tawaf goes round it)
  const v = -(lz + H), A = HIJR.a + HIJR.t + rad, B = HIJR.b + HIJR.t + rad;
  if (v > -0.2) {
    const e = (lx / A) ** 2 + (Math.max(v, 0) / B) ** 2;
    if (e < 1) {
      const k = 1 / Math.sqrt(Math.max(e, 1e-4));
      lx *= k;
      const nv = Math.max(v, 0.01) * k;
      lz = -nv - H;
      hit = 'hijr';
    }
  }
  // the Kaaba itself
  const h = H + 0.25 + rad;
  if (Math.abs(lx) < h && Math.abs(lz) < h) {
    const px = h - Math.abs(lx), pz = h - Math.abs(lz);
    if (px < pz) lx = Math.sign(lx) * h; else lz = Math.sign(lz) * h;
    hit = hit || 'kaaba';
  }
  [p.x, p.z] = toWorld(lx, lz);
  // Maqam Ibrahim
  const mx = p.x - maqamPos.x, mz = p.z - maqamPos.z, md = Math.hypot(mx, mz), mr = 1.05 + rad;
  if (md < mr) { p.x = maqamPos.x + mx / (md || 1) * mr; p.z = maqamPos.z + mz / (md || 1) * mr; hit = hit || 'maqam'; }
  const r = Math.hypot(p.x, p.z);
  if (r > MATAF_R) { p.x *= MATAF_R / r; p.z *= MATAF_R / r; }
  return hit;
}

export const matafLayout = {
  id: 'tawaf',
  spawn: { pos: polar(-0.42, 15), heading: Math.PI - 0.42 },   // facing the tawaf direction
  collide: collideMataf,
  zoom: [4, 30],
  cam: { pitch: 0.6, dist: 13, introDist: 42 },
  outfit: 'ihram',
  yawBias: 0.5, lookBias: 3.5,       // camera behind-right (outside the circle), looking toward the Kaaba
  background: 0x1d2b48, fog: [70, 170, 0x2a3655],
  light: { sky: 0x9fb5e8, ground: 0xe8dcc2, hemi: 1.05, sun: 0xffd9a8, si: 2.1, pos: [-40, 60, 30] },
  tags: [
    { text: 'ركن الحجر الأسود', pos: blackStone.clone().setY(2.6) },
    { text: 'الركن اليماني', pos: yamaniPos.clone().setY(2.4) },
    { text: 'مقام إبراهيم', pos: maqamPos.clone().setY(3.6) },
    { text: 'حِجر إسماعيل', pos: polar(Math.PI * 0.75, H + HIJR.b * 0.6, 2.2) },
  ],
  mini: 30,     // metres from the centre shown on the minimap
};
