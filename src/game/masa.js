import * as THREE from 'three';
import { makeCrowd, seeded } from './people.js';
import { cloneEnvScene, getCachedGLTF } from './loaders.js';
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

export function buildMasa(assets = {}) {
  const root = new THREE.Group();

  const masaGltf = assets.masa || getCachedGLTF('models/env/masa.glb');
  const crowdGltf = assets.crowd || getCachedGLTF('models/characters/crowd.glb');
  if (!masaGltf) throw new Error('masa.glb must be loaded before buildMasa()');

  const env = cloneEnvScene(masaGltf, { lod: Q.lod, shadows: Q.shadows });
  root.add(env);

  // Realistic two-lane crowd (covered ihram men + women in abayas/hijabs, no idtiba' in sa'i)
  const rnd = seeded(23);
  const crowd = makeCrowd(Q.saiCrowd, rnd, {
    robeRatio: 0.4,
    bareRatio: 0,
    shadows: Q.shadows,
    crowdGltf,
  });
  const agents = crowd.info.map(f => {
    const left = rnd() < 0.5;
    return {
      x: 1.4 + rnd() * 7.6,
      dir: left ? -1 : 1,
      z: 6 - rnd() * (LEN + 10),
      v: 1 + rnd() * 0.5,
      man: f.man,
    };
  });
  root.add(crowd.group);

  function update(dt, t, player) {
    for (let i = 0; i < agents.length; i++) {
      const g = agents[i];
      const inGreen = g.z < GREEN[0] && g.z > GREEN[1];
      g.z += g.dir * g.v * (inGreen && g.man ? 1.7 : 1) * dt;
      if (g.z < MARWA_Z - 4) g.dir = 1; else if (g.z > SAFA_Z + 4) g.dir = -1;
      let x = g.dir < 0 ? -g.x : g.x, z = g.z;
      const dx = x - player.x, dz = z - player.z, dd = dx * dx + dz * dz;
      if (dd < 2.6) {
        const kk = (1.6 - Math.sqrt(dd)) / Math.max(0.2, Math.sqrt(dd));
        x += dx * kk;
        z += dz * kk;
      }
      crowd.place(i, x, z, g.dir < 0 ? Math.PI : 0, t);
    }
    crowd.commit();
  }

  function dispose() {
    crowd.dispose();
  }

  return { root, update, dispose };
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
