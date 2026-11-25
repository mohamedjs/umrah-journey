import * as THREE from 'three';
import { glowM, adder, collideBoxes, sign, wanderers } from './kit.js';
import { makeCrowd, makeGlbPerson, seeded } from '../people.js';
import { cloneEnvScene, getCachedGLTF } from '../loaders.js';
import { voice } from '../voice.js';
import { Q } from '../quality.js';

// Chapter 4 — Makkah: the hotel lobby (key from the guide), the marble plaza, and the gate of
// al-Masjid al-Haram.
export const MAKKAH_SPOTS = {
  guide: new THREE.Vector3(-5, 0, 14.0),
  gate: new THREE.Vector3(0, 0, -37.6),
};
const BOUNDS = [-24, 24, -39.6, 18.4];
const BOXES = [];

export function buildMakkah(assets = {}) {
  const root = new THREE.Group();
  const add = adder(root);

  BOXES.length = 0;
  // Exact obstacle boxes matching makkah.glb (2 portico pillars, hotel desk, 12 plaza lamp posts)
  for (const x of [-11.5, 11.5]) BOXES.push([x - 0.5, x + 0.5, 9.6, 10.6]);
  BOXES.push([-7.4, -2.6, 15.4, 16.4]);
  for (let z = 4; z > -36; z -= 8) {
    for (const x of [-14, 14]) BOXES.push([x - 0.25, x + 0.25, z - 0.25, z + 0.25]);
  }

  const makkahGltf = assets.makkah || getCachedGLTF('models/env/makkah.glb');
  const guideGltf = assets.guide || getCachedGLTF('models/characters/guide.glb');
  const crowdGltf = assets.crowd || getCachedGLTF('models/characters/crowd.glb');
  if (!makkahGltf || !guideGltf) throw new Error('makkah.glb and guide.glb must be loaded before buildMakkah()');

  const env = cloneEnvScene(makkahGltf, { lod: Q.lod, shadows: Q.shadows });
  root.add(env);

  // Crisp Arabic hotel sign mounted inside the portico gilded frame (bronze backing at z=9.54..9.74,
  // gilded rails protrude to z=9.42 facing the plaza at -z in blender/env/makkah.py)
  const s1 = sign('فندق ضيوف الرحمن', { w: 8, h: 1.2, bg: '#7a5524' });
  s1.position.set(0, 6.6, 9.48);
  s1.rotation.y = Math.PI;
  root.add(s1);

  // Rigged hotel guide behind the reception desk facing -z
  const guide = makeGlbPerson(guideGltf, { shadows: Q.shadows });
  guide.group.position.set(-5, 0, 17.2);
  guide.group.rotation.y = Math.PI;
  root.add(guide.group);

  // Glowing rings at the hotel guide spot and the Haram gate
  const ring = add(
    new THREE.RingGeometry(0.8, 1.05, 40),
    glowM(0xffd68c, 0xffc04a, 1.5),
    MAKKAH_SPOTS.guide.x,
    0.05,
    MAKKAH_SPOTS.guide.z,
    root,
    false,
  );
  ring.rotation.x = -Math.PI / 2;

  const gateRing = add(
    new THREE.RingGeometry(1.1, 1.4, 40),
    glowM(0xffd68c, 0xffc04a, 1.5),
    MAKKAH_SPOTS.gate.x,
    0.05,
    MAKKAH_SPOTS.gate.z,
    root,
    false,
  );
  gateRing.rotation.x = -Math.PI / 2;

  // Pilgrims walking across the marble plaza toward the Haram gate
  const rnd = seeded(53);
  const crowd = makeCrowd(Q.makkahCrowd, rnd, {
    robeRatio: 0.38,
    streetRatio: 0.15,
    bareRatio: 0,
    shadows: Q.shadows,
    crowdGltf,
  });
  root.add(crowd.group);
  const walk = wanderers(crowd, rnd, [-22, 22, -36, 7], {
    avoid: BOXES,
    speed: [0.9, 1.4],
    to: r => ({ x: (r() - 0.5) * 6, z: -38.5 }),
  });

  function update(dt, t, p) {
    walk(dt, t, p);
    guide.animate(dt, 0, { talk: voice.speaking && voice.who === 'guide' });
  }

  function dispose() {
    guide.dispose();
    crowd.dispose();
    s1.material?.map?.dispose();
    s1.material?.dispose();
    s1.geometry?.dispose();
    ring.geometry?.dispose();
    ring.material?.dispose();
    gateRing.geometry?.dispose();
    gateRing.material?.dispose();
  }

  return { root, update, ring, gateRing, dispose };
}

export const makkahLayout = {
  id: 'makkah', outfit: 'ihram',
  spawn: { pos: new THREE.Vector3(2.5, 0, 9.2), heading: Math.PI + 0.5 },
  mentorStart: new THREE.Vector3(4.2, 0, 10.2),
  collide: p => collideBoxes(p, BOXES, BOUNDS),
  zoom: [5, 24],
  cam: { pitch: 0.36, dist: 9.2, clamp: { x: [-22.5, 22.5], y: 12, z: [-38.5, 17.2] } },
  background: 0x34466e, fog: [60, 160, 0x4a5a80],
  light: { sky: 0xb8c8f0, ground: 0xe8dcc2, hemi: 1.1, sun: 0xffd2a0, si: 1.9, pos: [-30, 40, 30], area: 50 },
  tags: [
    { text: 'مرشد الفندق', pos: new THREE.Vector3(-5, 2.6, 17.2) },
    { text: 'باب المسجد الحرام', pos: new THREE.Vector3(0, 10.5, -39.5), spot: 'gate' },
  ],
  map: { bounds: BOUNDS, boxes: BOXES },
};
