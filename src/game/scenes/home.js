import * as THREE from 'three';
import { glowM, adder, collideBoxes, marker } from './kit.js';
import { cloneEnvScene, getCachedGLTF } from '../loaders.js';
import { Q } from '../quality.js';

// Chapter 1 — the bedroom at home (diorama: back + left wall, camera from the open
// front-right corner). Four things glow: passport & visa, ihram clothes, sandals, perfume.
export const HOME_SPOTS = {
  passport: new THREE.Vector3(5.6, 2.45, -5.4),
  ihram: new THREE.Vector3(-2.6, 1.55, -3.2),
  sandals: new THREE.Vector3(4.6, 0.35, 5.0),
  perfume: new THREE.Vector3(-7.0, 1.75, 2.3),
  door: new THREE.Vector3(6.9, 0, 6.3),
};
const BOUNDS = [-7.85, 7.9, -6.85, 6.9];
const BOXES = [];

export function buildHome(assets = {}) {
  const root = new THREE.Group();
  const add = adder(root);

  BOXES.length = 0;
  // Exact furniture collision boxes matching home.glb
  BOXES.push(
    [-6.4, -1.4, -6.9, -2.2],   // bed
    [4.4, 6.8, -6.9, -4.6],     // shelf / bookcase
    [-7.95, -6.5, 1.1, 3.5],    // dresser
  );

  const homeGltf = assets.home || getCachedGLTF('models/env/home.glb');
  if (!homeGltf) throw new Error('home.glb must be loaded before buildHome()');

  const env = cloneEnvScene(homeGltf, { lod: Q.lod, shadows: Q.shadows });
  root.add(env);

  // Locate the 4 top-level interactive item nodes inside home.glb
  const itemKeys = ['passport', 'ihram', 'sandals', 'perfume'];
  const items = { passport: [], ihram: [], sandals: [], perfume: [] };
  env.traverse(node => {
    const base = (node.name || '').replace(/\.\d+$/, '');
    for (const k of itemKeys) {
      if (base === `item_${k}`) items[k].push(node);
    }
  });

  // Floating golden marker rings above the four items + exit door floor ring
  const rings = {};
  const ringBaseY = {};
  const disposables = [];
  for (const k of itemKeys) {
    const p = HOME_SPOTS[k];
    const r = marker(add, p.x, p.y + 0.5, p.z);
    rings[k] = r;
    ringBaseY[k] = p.y + 0.5;
    disposables.push(r);
  }

  const doorRing = add(
    new THREE.RingGeometry(0.8, 1.05, 40),
    glowM(0xffd68c, 0xffc04a, 1.5),
    HOME_SPOTS.door.x,
    0.05,
    HOME_SPOTS.door.z,
    root,
    false,
  );
  doorRing.rotation.x = -Math.PI / 2;
  doorRing.visible = false;
  disposables.push(doorRing);

  const take = k => {
    for (const node of items[k] || []) node.visible = false;
    if (rings[k]) rings[k].visible = false;
  };

  function update(dt, t) {
    for (const k of itemKeys) {
      const r = rings[k];
      if (!r || !r.visible) continue;
      r.rotation.y += dt * 1.5;
      r.position.y = ringBaseY[k] + Math.sin(t * 2.5) * 0.08;
    }
  }

  function dispose() {
    for (const m of disposables) {
      m.geometry?.dispose();
      m.material?.dispose();
    }
  }

  return {
    root,
    update,
    take,
    showDoor: on => { doorRing.visible = on; },
    dispose,
  };
}

export const homeLayout = {
  id: 'home', outfit: 'street',
  spawn: { pos: new THREE.Vector3(1.2, 0, 2.2), heading: Math.PI },
  collide: p => collideBoxes(p, BOXES, BOUNDS),
  zoom: [6, 18],
  cam: { mode: 'fixed', yaw: 0.53, pitch: 0.68, dist: 12.5 },
  mentorStart: new THREE.Vector3(3, 0, 3.5),
  background: 0xf3e2c4, fog: [40, 90, 0xf3e2c4],
  light: { sky: 0xfff3dd, ground: 0xc9a77a, hemi: 1.2, sun: 0xffe2b0, si: 2.0, pos: [-12, 18, 10], area: 16 },
  tags: [
    { text: 'جواز السفر والتأشيرة', pos: HOME_SPOTS.passport.clone().setY(3.4), spot: 'passport' },
    { text: 'ملابس الإحرام', pos: HOME_SPOTS.ihram.clone().setY(2.6), spot: 'ihram' },
    { text: 'شبشب مريح', pos: HOME_SPOTS.sandals.clone().setY(1.4), spot: 'sandals' },
    { text: 'العطر', pos: HOME_SPOTS.perfume.clone().setY(2.8), spot: 'perfume' },
    { text: 'باب البيت', pos: HOME_SPOTS.door.clone().setY(3.8), spot: 'door' },
  ],
  map: { bounds: BOUNDS, boxes: BOXES },
};
