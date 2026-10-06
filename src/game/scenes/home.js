import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { M, glowM, adder, block, collideBoxes, marker } from './kit.js';

// Chapter 1 — the bedroom at home (diorama like the concept: back + left wall, camera from the
// open front-right corner). Four things glow: passport & visa, ihram clothes, sandals, perfume.
export const HOME_SPOTS = {
  passport: new THREE.Vector3(5.6, 2.45, -5.4),
  ihram: new THREE.Vector3(-2.6, 1.55, -3.2),
  sandals: new THREE.Vector3(4.6, 0.35, 5.0),
  perfume: new THREE.Vector3(-7.0, 1.75, 2.3),
  door: new THREE.Vector3(6.9, 0, 6.3),
};
const BOUNDS = [-7.85, 7.9, -6.85, 6.9];
const BOXES = [];

export function buildHome() {
  const root = new THREE.Group(), add = adder(root);
  const wood = M(0xb98a5a), wall = M(0xf0dcbc), wall2 = M(0xe6cda6);
  BOXES.length = 0;
  add(new THREE.BoxGeometry(16, 0.2, 14), M(0xc89a68), 0, -0.1, 0, root, false);
  add(new THREE.BoxGeometry(16, 7, 0.2), wall, 0, 3.5, -7.05, root, false);
  add(new THREE.BoxGeometry(0.2, 7, 14), wall2, -8.05, 3.5, 0, root, false);
  // window with morning light
  add(new THREE.BoxGeometry(3.2, 2.6, 0.1), M(0xfff6e0, { emissive: 0xffe9b8, emissiveIntensity: 1.2 }), 1.5, 3.8, -6.92, root, false);
  for (const x of [-1.6, 0, 1.6]) add(new THREE.BoxGeometry(0.12, 2.8, 0.2), wood, 1.5 + x, 3.8, -6.85);
  add(new THREE.BoxGeometry(3.4, 0.12, 0.2), wood, 1.5, 3.8, -6.85);
  // rug
  add(new THREE.CylinderGeometry(3.2, 3.2, 0.04, 48), M(0x9c3d2f), 0.5, 0.02, 1, root, false).scale.z = 0.7;
  add(new THREE.CylinderGeometry(2.7, 2.7, 0.05, 48), M(0xd8a24a), 0.5, 0.03, 1, root, false).scale.z = 0.7;
  // bed with the open suitcase
  BOXES.push(block(add, wood, [-6.4, -1.4, -6.9, -2.2], 0.8));
  add(new RoundedBoxGeometry(4.8, 0.45, 4.4, 4, 0.2), M(0xf7f2e8), -3.9, 1, -4.55);
  add(new RoundedBoxGeometry(1.6, 0.35, 0.9, 4, 0.15), M(0xffffff), -5.5, 1.4, -5.6);
  add(new RoundedBoxGeometry(5, 2, 0.3, 4, 0.1), wood, -3.9, 1.6, -6.75);
  const sc = new THREE.Group(); sc.position.set(-4.2, 1.25, -4); sc.rotation.y = 0.25; root.add(sc);
  add(new RoundedBoxGeometry(2.2, 0.5, 1.5, 4, 0.1), M(0x2f6e8f), 0, 0.25, 0, sc);
  const lid = add(new RoundedBoxGeometry(2.2, 0.12, 1.5, 4, 0.05), M(0x2f6e8f), 0, 0.5, -0.75, sc); lid.geometry.translate(0, 0, -0.75); lid.rotation.x = -1.2;
  // shelf (passport + visa on top), dresser (perfume), plant
  BOXES.push(block(add, wood, [4.4, 6.8, -6.9, -4.6], 2.2));
  add(new THREE.SphereGeometry(0.5, 16, 12), M(0x4f8a4a), 4.9, 2.9, -6.3); add(new THREE.CylinderGeometry(0.3, 0.25, 0.5, 16), M(0xc9693f), 4.9, 2.45, -6.3);
  BOXES.push(block(add, wood, [-7.95, -6.5, 1.1, 3.5], 1.3));
  add(new THREE.BoxGeometry(0.1, 1.6, 1.2), M(0xcfe3ea, { metalness: 0.6, roughness: 0.1 }), -7.9, 2.3, 2.3);   // mirror
  // the front door (a free-standing frame at the open corner)
  const door = new THREE.Group(); door.position.set(7.3, 0, 6.3); door.rotation.y = -Math.PI / 2; root.add(door);
  add(new THREE.BoxGeometry(2.2, 0.25, 0.3), wood, 0, 3.2, 0, door); for (const x of [-1, 1]) add(new THREE.BoxGeometry(0.25, 3.3, 0.3), wood, x, 1.65, 0, door);
  add(new THREE.BoxGeometry(1.8, 3.0, 0.08), M(0x8a5a32), 0.55, 1.5, 0.5, door).rotation.y = -1.1;

  // the four items (+ glowing rings)
  const items = {
    passport: [add(new THREE.BoxGeometry(0.5, 0.06, 0.7), M(0x7a2531), HOME_SPOTS.passport.x, 2.25, HOME_SPOTS.passport.z)],
    ihram: [add(new RoundedBoxGeometry(0.9, 0.3, 0.7, 3, 0.1), M(0xffffff, { roughness: 1 }), HOME_SPOTS.ihram.x, 1.38, HOME_SPOTS.ihram.z), add(new RoundedBoxGeometry(0.8, 0.22, 0.6, 3, 0.08), M(0xf7f7f0, { roughness: 1 }), HOME_SPOTS.ihram.x, 1.62, HOME_SPOTS.ihram.z)],
    sandals: [-0.18, 0.18].map(dx => add(new THREE.BoxGeometry(0.22, 0.06, 0.55), M(0x6b4a2b), HOME_SPOTS.sandals.x + dx, 0.05, HOME_SPOTS.sandals.z)),
    perfume: [add(new THREE.CylinderGeometry(0.14, 0.14, 0.42, 16), M(0xc23d3d, { metalness: 0.3, roughness: 0.3 }), HOME_SPOTS.perfume.x, 1.52, HOME_SPOTS.perfume.z)],
  };
  const rings = {};
  for (const k of Object.keys(items)) { const p = HOME_SPOTS[k]; rings[k] = marker(add, p.x, p.y + 0.5, p.z); }
  const doorRing = add(new THREE.RingGeometry(0.8, 1.05, 40), glowM(0xffd68c, 0xffc04a, 1.5), HOME_SPOTS.door.x, 0.05, HOME_SPOTS.door.z, root, false);
  doorRing.rotation.x = -Math.PI / 2; doorRing.visible = false;

  const take = k => { for (const m of items[k]) m.visible = false; rings[k].visible = false; };
  function update(dt, t) {
    for (const r of Object.values(rings)) { r.rotation.y += dt * 1.5; r.position.y += Math.sin(t * 2.5) * 0.002; }
  }
  return { root, update, take, showDoor: on => { doorRing.visible = on; } };
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
