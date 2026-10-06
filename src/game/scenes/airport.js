import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { M, glowM, adder, block, collideBoxes, sign, wanderers } from './kit.js';
import { makeCrowd, makePerson, seeded } from '../people.js';
import { marble } from '../textures.js';
import { Q } from '../quality.js';

// Chapter 2 — the departures hall: the airline counter, then gate 12 at the far end.
export const AIRPORT_SPOTS = {
  counter: new THREE.Vector3(0, 0, -6.4),
  gate: new THREE.Vector3(25, 0, -9.6),
};
const BOUNDS = [-28, 30, -11.6, 12];
const BOXES = [];

export function buildAirport() {
  const root = new THREE.Group(), add = adder(root);
  BOXES.length = 0;
  const fl = add(new THREE.PlaneGeometry(64, 30), M(0xffffff, { map: marble(10, '#e9edf0'), roughness: 0.3 }), 1, 0, 0, root, false);
  fl.rotation.x = -Math.PI / 2; fl.material.map.repeat.set(10, 5);
  // glass wall with the sky and a parked plane behind it
  add(new THREE.BoxGeometry(64, 9, 0.2), M(0xbfe0f5, { emissive: 0x9fd0f0, emissiveIntensity: 0.55 }), 1, 4.5, -12.2, root, false);
  for (let x = -30; x <= 32; x += 4) add(new THREE.BoxGeometry(0.2, 9, 0.3), M(0x5a6470), x, 4.5, -12, root, false);
  const jet = new THREE.Group(); jet.position.set(22, 2.6, -18); root.add(jet);
  add(new THREE.CapsuleGeometry(1.6, 18, 6, 16), M(0xf4f6f8), 0, 0, 0, jet).rotation.z = Math.PI / 2;
  add(new THREE.BoxGeometry(5, 0.3, 16), M(0xe3e7ea), 0, -0.5, 0, jet);
  add(new THREE.BoxGeometry(0.3, 4, 3), M(0x1d6f6a), -9, 2.4, 0, jet);
  for (const s of [-1, 1]) add(new THREE.BoxGeometry(0.2, 9, 30), M(0xe9edf0), s > 0 ? 30.1 : -28.1, 4.5, 0, root, false);
  add(new THREE.BoxGeometry(64, 0.4, 30), M(0xf2f4f5), 1, 9.2, 0, root, false);
  // the check-in counter, the belt and the agent
  BOXES.push(block(add, M(0x2f4a6b), [-12, 12, -9.2, -7.8], 1.1));
  add(new THREE.BoxGeometry(24, 0.08, 1.4), M(0xdfe6ea), 0, 1.14, -8.5);
  add(new THREE.BoxGeometry(24, 0.4, 1.2), M(0x2a2d33), 0, 0.5, -10.8, root, false);
  const s1 = sign('تسجيل الوصول · الرحلات', { w: 10, h: 1.4 }); s1.position.set(0, 5, -11.9); root.add(s1);
  const s2 = sign('البوابة ١٢', { w: 5, h: 1.2, bg: '#c08a3e' }); s2.position.set(25, 5, -11.9); root.add(s2);
  const s3 = sign('البوابات', { w: 5, h: 1, bg: '#1d3b5a' }); s3.position.set(14, 6, -0.5); root.add(s3);
  const agent = makePerson({ skin: 0xdba57c, shirt: 0x1d3b5a, pants: 0x1d2433 }); agent.setOutfit('street');
  agent.group.position.set(0, 0, -10); root.add(agent.group);
  // pillars
  for (const x of [-18, -6, 6, 18]) BOXES.push(block(add, M(0xdfe3e6), [x - 0.6, x + 0.6, 3.4, 4.6], 9));
  // gate: seats + the glowing gate door
  for (const z of [-5, -2, 1]) BOXES.push(block(add, M(0x3d4b5c), [19.5, 28.5, z - 0.35, z + 0.35], 0.5));
  add(new THREE.BoxGeometry(3, 3.4, 0.3), glowM(0xffe2a6, 0xffc35a, 0.8), 25, 1.7, -11.7, root, false);
  const ring = add(new THREE.RingGeometry(0.8, 1.05, 40), glowM(0xffd68c, 0xffc04a, 1.5), 25, 0.05, -9.6, root, false); ring.rotation.x = -Math.PI / 2;
  // a few suitcases by the counter
  for (let i = 0; i < 5; i++) add(new RoundedBoxGeometry(0.6, 0.8, 0.35, 3, 0.06), M([0x8a3d3d, 0x2f6e8f, 0x3d6b4f][i % 3]), -10 + i * 4.6, 0.4, -7.2);
  // travellers
  const rnd = seeded(31), crowd = makeCrowd(Q.name === 'lite' ? 70 : 160, rnd, { robeRatio: 0.35, streetRatio: 0.75, bareRatio: 0, shadows: Q.shadows });
  root.add(crowd.group);
  const walk = wanderers(crowd, rnd, [-26, 28, -6.5, 11], { avoid: BOXES });
  return { root, update: (dt, t, p) => walk(dt, t, p), ring };
}

export const airportLayout = {
  id: 'airport', outfit: 'street',
  spawn: { pos: new THREE.Vector3(-20, 0, 9), heading: 2.4 },
  collide: p => collideBoxes(p, BOXES, BOUNDS),
  zoom: [5, 20],
  cam: { pitch: 0.5, dist: 10, clamp: { x: [-27.4, 29.4], y: 8.4, z: [-11.2, 16] } },
  background: 0xdbe8f0, fog: [50, 120, 0xdbe8f0],
  light: { sky: 0xffffff, ground: 0xd9dde0, hemi: 1.3, sun: 0xfff6e8, si: 1.6, pos: [10, 30, 20], area: 40 },
  tags: [
    { text: 'كاونتر الطيران', pos: new THREE.Vector3(0, 3, -8.5), spot: 'counter' },
    { text: 'البوابة ١٢', pos: AIRPORT_SPOTS.gate.clone().setY(3.6), spot: 'gate' },
  ],
  map: { bounds: BOUNDS, boxes: BOXES },
};
