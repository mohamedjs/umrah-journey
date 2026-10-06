import * as THREE from 'three';
import { M, glowM, adder, block, collideBoxes, sign, wanderers } from './kit.js';
import { makeCrowd, makePerson, seeded } from '../people.js';
import { marble } from '../textures.js';
import { Q } from '../quality.js';

// Chapter 4 — Makkah: the hotel lobby (key from the guide), the marble plaza, and the gate of
// al-Masjid al-Haram. Simplified, generic architecture (not a model of a specific gate).
export const MAKKAH_SPOTS = {
  guide: new THREE.Vector3(-5, 0, 14.0),
  gate: new THREE.Vector3(0, 0, -37.6),
};
const BOUNDS = [-24, 24, -39.6, 18.4];
const BOXES = [];

export function buildMakkah() {
  const root = new THREE.Group(), add = adder(root);
  BOXES.length = 0;
  const fl = add(new THREE.PlaneGeometry(90, 80), M(0xffffff, { map: marble(14), roughness: 0.35 }), 0, 0, -12, root, false);
  fl.rotation.x = -Math.PI / 2;
  // the hotel: lobby portico, counter, guide
  const hotelM = M(0xe9dcc6), glass = M(0x9fb8c8, { emissive: 0xffe2b0, emissiveIntensity: 0.35 });
  add(new THREE.BoxGeometry(40, 30, 6), hotelM, 0, 15, 21.5, root, false);
  for (let y = 7; y < 30; y += 3.2) for (let x = -18; x <= 18; x += 3) add(new THREE.BoxGeometry(2, 2, 0.1), glass, x, y, 18.45, root, false);
  add(new THREE.BoxGeometry(24, 0.6, 9), M(0xd8c8ac), 0, 5.6, 14, root, false);       // portico roof
  for (const x of [-11.5, 11.5]) BOXES.push(block(add, M(0xd8c8ac), [x - 0.5, x + 0.5, 9.6, 10.6], 5.3));
  const s1 = sign('فندق ضيوف الرحمن', { w: 8, h: 1.2, bg: '#7a5524' }); s1.position.set(0, 6.6, 9.45); root.add(s1);
  BOXES.push(block(add, M(0x8a5a32), [-7.4, -2.6, 15.4, 16.4], 1.1));
  const guide = makePerson({ skin: 0xa86b45, shirt: 0x2f4a6b, pants: 0x2a2d33 }); guide.setOutfit('street');
  guide.group.position.set(-5, 0, 17.2); guide.group.rotation.y = Math.PI; root.add(guide.group);
  const ring = add(new THREE.RingGeometry(0.8, 1.05, 40), glowM(0xffd68c, 0xffc04a, 1.5), MAKKAH_SPOTS.guide.x, 0.05, MAKKAH_SPOTS.guide.z, root, false); ring.rotation.x = -Math.PI / 2;
  // the Haram facade with arches, the gate and two minarets
  const stone = M(0xf1ece2, { roughness: 0.5 }), gold = M(0xd4b064, { metalness: 0.7, roughness: 0.3 });
  add(new THREE.BoxGeometry(100, 16, 4), stone, 0, 8, -42.5, root, false);
  const arch = new THREE.InstancedMesh(new THREE.BoxGeometry(3.2, 7, 0.4), M(0x7a6a55, { emissive: 0xffd9a0, emissiveIntensity: 0.25 }), 26);
  const o = new THREE.Object3D(); let k = 0;
  for (let x = -48; x <= 48; x += 4) { if (Math.abs(x) < 7) continue; o.position.set(x, 3.6, -40.4); o.updateMatrix(); arch.setMatrixAt(k++, o.matrix); }
  arch.count = k; root.add(arch);
  add(new THREE.BoxGeometry(10, 14, 1.2), M(0xe6dccb), 0, 7, -40.2, root, false);
  add(new THREE.BoxGeometry(5, 9, 0.4), glowM(0xfff1d0, 0xffd9a0, 0.9), 0, 4.5, -39.5, root, false);
  for (const x of [-9, 9]) {
    add(new THREE.CylinderGeometry(1.4, 1.8, 60, 12), stone, x, 30, -42, root, false);
    add(new THREE.CylinderGeometry(2.1, 2.1, 1.2, 12), gold, x, 44, -42, root, false);
    add(new THREE.ConeGeometry(1.2, 5, 12), gold, x, 62.5, -42, root, false);
  }
  // a tall tower in the distance (generic silhouette)
  add(new THREE.BoxGeometry(14, 120, 14), M(0xcfc6b6), 42, 60, -95, root, false);
  add(new THREE.CylinderGeometry(5, 5, 0.6, 32), glowM(0xffffff, 0xbfe8c8, 0.8), 42, 100, -87.7, root, false).rotation.x = Math.PI / 2;
  // lamp posts along the plaza
  for (let z = 4; z > -36; z -= 8) for (const x of [-14, 14]) {
    BOXES.push(block(add, M(0x8a8f96), [x - 0.25, x + 0.25, z - 0.25, z + 0.25], 6));
    add(new THREE.SphereGeometry(0.5, 12, 8), glowM(0xfff1d0, 0xffe2b0, 1.6), x, 6.4, z, root, false);
  }
  const gateRing = add(new THREE.RingGeometry(1.1, 1.4, 40), glowM(0xffd68c, 0xffc04a, 1.5), MAKKAH_SPOTS.gate.x, 0.05, MAKKAH_SPOTS.gate.z, root, false); gateRing.rotation.x = -Math.PI / 2;
  // pilgrims walking to the gate
  const rnd = seeded(53), crowd = makeCrowd(Q.name === 'lite' ? 180 : 420, rnd, { robeRatio: 0.38, streetRatio: 0.15, bareRatio: 0, shadows: Q.shadows });
  root.add(crowd.group);
  const walk = wanderers(crowd, rnd, [-22, 22, -36, 7], { avoid: BOXES, speed: [0.9, 1.4], to: r => ({ x: (r() - 0.5) * 6, z: -38.5 }) });
  return { root, update: (dt, t, p) => walk(dt, t, p), ring, gateRing };
}

export const makkahLayout = {
  id: 'makkah', outfit: 'ihram',
  spawn: { pos: new THREE.Vector3(2.5, 0, 12.5), heading: Math.PI + 0.6 },
  collide: p => collideBoxes(p, BOXES, BOUNDS),
  zoom: [5, 24],
  cam: { pitch: 0.42, dist: 11 },
  background: 0x34466e, fog: [60, 160, 0x4a5a80],
  light: { sky: 0xb8c8f0, ground: 0xe8dcc2, hemi: 1.1, sun: 0xffd2a0, si: 1.9, pos: [-30, 40, 30], area: 50 },
  tags: [
    { text: 'مرشد الفندق', pos: new THREE.Vector3(-5, 2.6, 17.2) },
    { text: 'باب المسجد الحرام', pos: new THREE.Vector3(0, 10.5, -39.5), spot: 'gate' },
  ],
  map: { bounds: BOUNDS, boxes: BOXES },
};
