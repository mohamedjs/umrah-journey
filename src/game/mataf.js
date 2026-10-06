import * as THREE from 'three';
import { marble, kiswa } from './textures.js';
import { makeCrowd, seeded } from './people.js';
import { Q } from './quality.js';

// ------------------------------------------------------------------------------------------
// The Mataf. World axes: +x = east, -z = north. Angles are compass-free "math" angles seen
// from above: θ = atan2(-z, x), so θ grows counter-clockwise (east → north → west → south),
// which is the direction of tawaf (the Kaaba on the walker's left).
// The Kaaba's corners point (roughly) to the four directions: the Black Stone corner east (θ=0),
// the Iraqi corner north, the Shami corner west, the Yamani corner south (θ=-90°).
// The door is on the north-east face near the Black Stone; Hijr Ismail is the low semicircle
// off the north-west face; Maqam Ibrahim stands in front of the door side.
// Sizes are simplified (a square 11.6 m footprint, 13 m high) — this is a prototype.
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

const M = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.75, ...o });

export function buildMataf() {
  const root = new THREE.Group();
  const add = (geo, m, x = 0, y = 0, z = 0, p = root, cast = true) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.castShadow = cast && Q.shadows; o.receiveShadow = Q.shadows; p.add(o); return o; };

  // floor: white marble mataf + the outer floor
  const fl = add(new THREE.CircleGeometry(MATAF_R + 8, 96), M(0xffffff, { map: marble(13), roughness: 0.35 }), 0, 0, 0, root, false); fl.rotation.x = -Math.PI / 2;

  // the Kaaba
  const kb = new THREE.Group(); kb.rotation.y = Math.PI / 4; root.add(kb);
  const kis = kiswa();
  const topM = M(0x111114, { roughness: 0.9 });
  add(new THREE.BoxGeometry(2 * H, KAABA_H, 2 * H), [M(0xffffff, { map: kis, roughness: 0.85 }), M(0xffffff, { map: kis, roughness: 0.85 }), topM, topM, M(0xffffff, { map: kis, roughness: 0.85 }), M(0xffffff, { map: kis, roughness: 0.85 })], 0, KAABA_H / 2 + 0.4, 0, kb);
  add(new THREE.BoxGeometry(2 * H + 0.5, 0.4, 2 * H + 0.5), M(0xd9d4c8, { roughness: 0.4 }), 0, 0.2, 0, kb);     // shadharwan base
  // the door: north-east face (local +x), near the Black Stone corner (local +z)
  const gold = M(0xd4a84d, { metalness: 0.8, roughness: 0.3 });
  add(new THREE.BoxGeometry(0.14, 3.4, 1.8), gold, H + 0.03, 2.3 + 1.7, H - 2.6, kb);
  add(new THREE.BoxGeometry(0.1, 3.9, 2.3), M(0x6b4f22, { metalness: 0.5, roughness: 0.5 }), H + 0.01, 2.3 + 1.7, H - 2.6, kb);
  // Black Stone in its silver frame at the east corner
  const bsG = new THREE.Group(); bsG.position.set(H, 1.5, H); bsG.rotation.y = Math.PI / 4; kb.add(bsG);
  add(new THREE.SphereGeometry(0.26, 16, 12), M(0x1a1416, { roughness: 0.4 }), 0.02, 0, 0, bsG);
  const frame = add(new THREE.TorusGeometry(0.34, 0.09, 10, 28), M(0xc0c4c8, { metalness: 0.9, roughness: 0.25 }), 0.05, 0, 0, bsG); frame.rotation.y = Math.PI / 2;
  // Hijr Ismail: low semicircular wall off the north-west face (local -z)
  const sh = new THREE.Shape(), { a, b, t } = HIJR, N = 40;
  for (let i = 0; i <= N; i++) { const q = Math.PI * i / N; sh[i ? 'lineTo' : 'moveTo'](Math.cos(q) * (a + t), Math.sin(q) * (b + t)); }
  for (let i = N; i >= 0; i--) { const q = Math.PI * i / N; sh.lineTo(Math.cos(q) * a, Math.sin(q) * b); }
  const hij = add(new THREE.ExtrudeGeometry(sh, { depth: 1.3, bevelEnabled: true, bevelSize: 0.08, bevelThickness: 0.08, bevelSegments: 2, curveSegments: 4 }), M(0xe8e3d6, { roughness: 0.45 }), 0, 0, -H, kb);
  hij.rotation.x = -Math.PI / 2;
  const hf = add(new THREE.CircleGeometry(1, 40, 0, Math.PI), M(0xf2efe8, { roughness: 0.4 }), 0, 0.02, -H, kb, false);
  hf.rotation.x = -Math.PI / 2; hf.scale.set(a, b, 1);
  // Maqam Ibrahim
  const mq = new THREE.Group(); mq.position.copy(maqamPos); root.add(mq);
  add(new THREE.CylinderGeometry(0.9, 1, 0.5, 8), M(0xe0dbd0), 0, 0.25, 0, mq);
  add(new THREE.CylinderGeometry(0.7, 0.7, 1.6, 16, 1, true), M(0xd8b664, { metalness: 0.9, roughness: 0.25, transparent: true, opacity: 0.85, side: THREE.DoubleSide }), 0, 1.3, 0, mq);
  add(new THREE.SphereGeometry(0.72, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2), M(0xd8b664, { metalness: 0.9, roughness: 0.25 }), 0, 2.1, 0, mq);
  add(new THREE.ConeGeometry(0.12, 0.5, 8), gold, 0, 3, 0, mq);

  // start line (a game aid, not a real marking) from the Black Stone corner outwards, and the
  // green lamp on the colonnade opposite the Black Stone
  const line = add(new THREE.PlaneGeometry(MATAF_R - R - 0.5, 0.32), M(0xffd68c, { emissive: 0xffb43a, emissiveIntensity: 1.1, transparent: true, opacity: 0.85 }), (MATAF_R + R + 0.5) / 2, 0.03, 0, root, false);
  line.rotation.x = -Math.PI / 2;
  add(new THREE.BoxGeometry(0.3, 0.9, 1.6), M(0x1fbf6a, { emissive: 0x18e070, emissiveIntensity: 2.2 }), MATAF_R + 2.6, 5, 0, root, false);

  // colonnade ring, arches, upper storey, minarets (instanced columns)
  const cols = Q.columns, colR = MATAF_R + 3;
  const colM = M(0xf1ece2, { roughness: 0.5 });
  const col = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.6, 0.6, 9, 10), colM, cols);
  const o = new THREE.Object3D();
  for (let i = 0; i < cols; i++) { const q = i / cols * Math.PI * 2; o.position.set(Math.cos(q) * colR, 4.5, Math.sin(q) * colR); o.updateMatrix(); col.setMatrixAt(i, o.matrix); }
  col.castShadow = Q.shadows; root.add(col);
  const ring = add(new THREE.TorusGeometry(colR, 1.2, 8, 128), colM, 0, 9.6, 0, root, false); ring.rotation.x = Math.PI / 2;
  const ring2 = add(new THREE.TorusGeometry(colR + 2, 2.4, 6, 128), M(0xe7e0d2), 0, 12.5, 0, root, false); ring2.rotation.x = Math.PI / 2;
  add(new THREE.CylinderGeometry(colR + 12, colR + 12, 16, 64, 1, true), M(0xe9e2d4, { side: THREE.BackSide }), 0, 8, 0, root, false);
  for (let i = 0; i < 6; i++) {
    const q = i / 6 * Math.PI * 2 + 0.3, x = Math.cos(q) * (colR + 16), z = Math.sin(q) * (colR + 16);
    add(new THREE.CylinderGeometry(1.1, 1.5, 38, 10), M(0xf3eee4), x, 19, z, root, false);
    add(new THREE.ConeGeometry(1.2, 4, 10), gold, x, 40, z, root, false);
  }
  // warm lamps on the colonnade (emissive only: no real lights, cheap on phones)
  const lamp = new THREE.InstancedMesh(new THREE.SphereGeometry(0.35, 8, 6), M(0xffe2b0, { emissive: 0xffd08a, emissiveIntensity: 2 }), 40);
  for (let i = 0; i < 40; i++) { const q = i / 40 * Math.PI * 2; o.position.set(Math.cos(q) * (colR - 1), 8.3, Math.sin(q) * (colR - 1)); o.updateMatrix(); lamp.setMatrixAt(i, o.matrix); }
  root.add(lamp);

  // ---- crowd circling counter-clockwise
  const rnd = seeded(11), crowd = makeCrowd(Q.tawafCrowd, rnd, { robeRatio: 0.35, shadows: Q.shadows });
  const agents = crowd.info.map(() => { const r = 10 + Math.pow(rnd(), 1.3) * 32; return { r, th: rnd() * Math.PI * 2, w: (0.8 + rnd() * 0.6) / r }; });
  root.add(crowd.group);
  const hijrTh = Math.PI * 0.75;
  function update(dt, t, player) {
    for (let i = 0; i < agents.length; i++) {
      const g = agents[i]; g.th += g.w * dt;
      let r = g.r;
      const d = Math.abs(Math.atan2(Math.sin(g.th - hijrTh), Math.cos(g.th - hijrTh)));   // keep clear of Hijr Ismail
      if (d < 0.95 && r < 16.2) r += (16.2 - r) * Math.sqrt(1 - d / 0.95);
      let x = Math.cos(g.th) * r, z = -Math.sin(g.th) * r;
      const dx = x - player.x, dz = z - player.z, dd = dx * dx + dz * dz;           // make room round the player
      if (dd < 2.6) { const k = (1.6 - Math.sqrt(dd)) / Math.max(0.2, Math.sqrt(dd)); x += dx * k; z += dz * k; }
      crowd.place(i, x, z, g.th + Math.PI, t);
    }
    crowd.commit();
  }
  return { root, update };
}

// push a point out of the Kaaba, Hijr Ismail, the Maqam and keep it in the Mataf.
// returns the name of what it touched ('hijr' | 'kaaba' | 'maqam' | null).
export function collideMataf(p, rad = 0.38) {
  let hit = null;
  let [lx, lz] = toLocal(p.x, p.z);
  // Hijr Ismail (counted as part of the Kaaba: tawaf goes round it)
  const v = -(lz + H), A = HIJR.a + HIJR.t + rad, B = HIJR.b + HIJR.t + rad;
  if (v > -0.2) { const e = (lx / A) ** 2 + (Math.max(v, 0) / B) ** 2; if (e < 1) { const k = 1 / Math.sqrt(Math.max(e, 1e-4)); lx *= k; const nv = Math.max(v, 0.01) * k; lz = -nv - H; hit = 'hijr'; } }
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
