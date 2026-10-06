import * as THREE from 'three';
import { marble } from './textures.js';
import { makeCrowd, seeded } from './people.js';
import { Q } from './quality.js';

// ------------------------------------------------------------------------------------------
// The Mas'a (gallery between as-Safa and al-Marwa). As-Safa is at the +z end, al-Marwa at
// z = -LEN. The real distance is about 395 m; the prototype shortens it to LEN metres so seven
// laps stay playable. The green-lit stretch (where men jog) is GREEN = [from, to] (z, negative).
// The Kaaba lies to the west (-x) of the gallery.
// ------------------------------------------------------------------------------------------
export const LEN = 120;
export const HALF_W = 10;
export const GREEN = [-38, -55];
export const SAFA_Z = 1.5, MARWA_Z = -LEN - 1.5;
export const KAABA_HEADING = -Math.PI / 2;      // facing -x
const M = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.75, ...o });

export function buildMasa() {
  const root = new THREE.Group();
  const add = (geo, m, x = 0, y = 0, z = 0, p = root, cast = true) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.castShadow = cast && Q.shadows; o.receiveShadow = Q.shadows; p.add(o); return o; };
  const zMid = -LEN / 2, full = LEN + 34;
  const fl = add(new THREE.PlaneGeometry(2 * HALF_W, full), M(0xffffff, { map: marble(6), roughness: 0.3 }), 0, 0, zMid, root, false);
  fl.rotation.x = -Math.PI / 2; fl.material.map.repeat.set(3, full / 7);
  // central divider (open near both hills)
  add(new THREE.BoxGeometry(1.2, 1, LEN - 6), M(0xd9d1c0), 0, 0.5, zMid);
  // walls, ceiling
  for (const s of [-1, 1]) add(new THREE.BoxGeometry(0.5, 12, full), M(0xefe9dd), s * (HALF_W + 0.25), 6, zMid, root, false);
  add(new THREE.BoxGeometry(2 * HALF_W + 1, 0.6, full), M(0xf2ede3), 0, 12.3, zMid, root, false);
  // columns + arches
  const colM = M(0xf6f2ea, { roughness: 0.45 }), capM = M(0xd8b664, { metalness: 0.6, roughness: 0.35 });
  const zs = []; for (let z = 8; z > -LEN - 8; z -= 9) zs.push(z);
  const colI = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.7, 0.7, 12, 12), colM, zs.length * 2);
  const capI = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.95, 0.7, 0.7, 12), capM, zs.length * 2);
  const arcI = new THREE.InstancedMesh(new THREE.TorusGeometry(HALF_W - 0.8, 0.35, 6, 24, Math.PI), M(0xefe8da), zs.length);
  const o = new THREE.Object3D(); let k = 0;
  zs.forEach((z, i) => {
    for (const x of [-HALF_W + 0.8, HALF_W - 0.8]) { o.position.set(x, 6, z); o.updateMatrix(); colI.setMatrixAt(k, o.matrix); o.position.y = 11.6; o.updateMatrix(); capI.setMatrixAt(k++, o.matrix); }
    o.position.set(0, 6.6, z); o.updateMatrix(); arcI.setMatrixAt(i, o.matrix);
  });
  root.add(colI, capI, arcI);
  // chandeliers (emissive)
  const chI = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.5, 0.3, 0.5, 10), M(0xd8b664, { metalness: 0.7, roughness: 0.3, emissive: 0xffd27a, emissiveIntensity: 0.9 }), Math.ceil(LEN / 12 + 3) * 2);
  k = 0; for (let z = 6; z > -LEN - 8; z -= 12) for (const x of [-5, 5]) { o.position.set(x, 10.8, z); o.updateMatrix(); chI.setMatrixAt(k++, o.matrix); }
  chI.count = k; root.add(chI);
  // the green lights: bars across the ceiling at both ends + a strip along the stretch
  const gM = M(0x1fbf6a, { emissive: 0x18e070, emissiveIntensity: 2.4 });
  for (const z of GREEN) {
    add(new THREE.BoxGeometry(2 * HALF_W - 2, 0.3, 1.2), gM, 0, 11.7, z, root, false);
    for (const x of [-HALF_W + 0.8, HALF_W - 0.8]) add(new THREE.CylinderGeometry(0.76, 0.76, 3, 12), gM, x, 8.6, z, root, false);
  }
  for (const x of [-5, 5]) add(new THREE.BoxGeometry(0.5, 0.15, GREEN[0] - GREEN[1]), gM, x, 11.9, (GREEN[0] + GREEN[1]) / 2, root, false);
  const gFloor = add(new THREE.PlaneGeometry(2 * HALF_W, GREEN[0] - GREEN[1]), M(0x1fbf6a, { emissive: 0x18e070, emissiveIntensity: 0.25, transparent: true, opacity: 0.12 }), 0, 0.02, (GREEN[0] + GREEN[1]) / 2, root, false);
  gFloor.rotation.x = -Math.PI / 2;
  // the hills: rock under a low marble ring, with a gentle slope up to it
  const rockM = M(0x9a8a74, { roughness: 1 });
  const hill = (z, dir) => {
    const g = new THREE.Group(); g.position.set(0, 0, z); root.add(g);
    for (let i = 0; i < 7; i++) { const r = add(new THREE.DodecahedronGeometry(1.8 + (i % 3) * 0.7, 0), rockM, -6 + i * 2 + Math.sin(i) * 0.6, 0.6, dir * (2 + (i % 2) * 1.6), g); r.rotation.set(i, i * 0.7, 0); r.scale.y = 0.6; }
    const rail = add(new THREE.TorusGeometry(8, 0.08, 6, 48, Math.PI), M(0xd8b664, { metalness: 0.7, roughness: 0.3 }), 0, 1.1, 0, g, false);
    rail.rotation.x = -Math.PI / 2; if (dir < 0) rail.rotation.z = Math.PI;
    const ramp = add(new THREE.PlaneGeometry(2 * HALF_W, 7), M(0xe9e2d4, { roughness: 0.4 }), 0, 0.04, -dir * 2.5, g, false); ramp.rotation.x = -Math.PI / 2;
    return g;
  };
  hill(SAFA_Z + 9, 1); hill(MARWA_Z - 9, -1);
  // a wall arrow pointing to the Kaaba (west) at each hill
  for (const z of [SAFA_Z + 3, MARWA_Z - 3]) add(new THREE.ConeGeometry(0.5, 1.2, 3), M(0xffd68c, { emissive: 0xffb43a, emissiveIntensity: 1 }), -HALF_W + 0.4, 4, z, root, false).rotation.z = Math.PI / 2;

  // ---- crowd in both directions (left lane → al-Marwa, right lane → as-Safa)
  const rnd = seeded(23), crowd = makeCrowd(Q.saiCrowd, rnd, { robeRatio: 0.4, bareRatio: 0, shadows: Q.shadows });   // no idtiba' in sa'i
  const agents = crowd.info.map(f => { const left = rnd() < 0.5; return { x: (1.4 + rnd() * 7.6), dir: left ? -1 : 1, z: 6 - rnd() * (LEN + 10), v: 1 + rnd() * 0.5, man: f.man }; });
  root.add(crowd.group);
  function update(dt, t, player) {
    for (let i = 0; i < agents.length; i++) {
      const g = agents[i];
      const inGreen = g.z < GREEN[0] && g.z > GREEN[1];
      g.z += g.dir * g.v * (inGreen && g.man ? 1.7 : 1) * dt;
      if (g.z < MARWA_Z - 4) g.dir = 1; else if (g.z > SAFA_Z + 4) g.dir = -1;
      let x = g.dir < 0 ? -g.x : g.x, z = g.z;
      const dx = x - player.x, dz = z - player.z, dd = dx * dx + dz * dz;
      if (dd < 2.6) { const kk = (1.6 - Math.sqrt(dd)) / Math.max(0.2, Math.sqrt(dd)); x += dx * kk; z += dz * kk; }
      crowd.place(i, x, z, g.dir < 0 ? Math.PI : 0, t);
    }
    crowd.commit();
  }
  return { root, update };
}

export function collideMasa(p, rad = 0.38) {
  let hit = null;
  const lim = HALF_W - 1.5 - rad;
  if (p.x < -lim) p.x = -lim; else if (p.x > lim) p.x = lim;
  if (p.z > SAFA_Z + 7) p.z = SAFA_Z + 7; else if (p.z < MARWA_Z - 7) p.z = MARWA_Z - 7;
  const dz0 = -3, dz1 = -LEN + 3;
  if (p.z < dz0 && p.z > dz1 && Math.abs(p.x) < 0.6 + rad) { p.x = Math.sign(p.x || 1) * (0.6 + rad); hit = 'divider'; }
  return hit;
}

export const masaLayout = {
  id: 'sai',
  spawn: { pos: new THREE.Vector3(-3.5, 0, -9), heading: 0 },
  collide: collideMasa,
  zoom: [4, 11],
  cam: { pitch: 0.42, dist: 8, clamp: { x: [-8.8, 8.8], y: 10.6 } },
  outfit: 'ihram',
  background: 0xf4efe4, fog: [40, 130, 0xf4efe4],
  light: { sky: 0xfffaf0, ground: 0xd9cdb5, hemi: 1.35, sun: 0xfff2dc, si: 1.3, pos: [10, 30, 15] },
  tags: [
    { text: 'الصفا', pos: new THREE.Vector3(0, 4.5, SAFA_Z + 9) },
    { text: 'المروة', pos: new THREE.Vector3(0, 4.5, MARWA_Z - 9) },
    { text: 'العلم الأخضر', pos: new THREE.Vector3(0, 10, GREEN[0]) },
    { text: 'العلم الأخضر', pos: new THREE.Vector3(0, 10, GREEN[1]) },
  ],
};
