import * as THREE from 'three';
import { glowM, adder, collideBoxes, sign, wanderers } from './kit.js';
import { makeCrowd, makeGlbPerson, seeded } from '../people.js';
import { cloneEnvScene, getCachedGLTF } from '../loaders.js';
import { voice } from '../voice.js';
import { Q } from '../quality.js';

// Chapter 2 — the departures hall: the airline counter, then gate 12 at the far end.
export const AIRPORT_SPOTS = {
  counter: new THREE.Vector3(0, 0, -6.4),
  gate: new THREE.Vector3(25, 0, -9.6),
};
const BOUNDS = [-28, 30, -11.6, 12];
const BOXES = [];

export function buildAirport(assets = {}) {
  const root = new THREE.Group();
  const add = adder(root);

  BOXES.length = 0;
  // Exact obstacle boxes matching airport.glb (counter, 4 pillars, 3 chair rows)
  BOXES.push([-12, 12, -9.2, -7.8]);
  for (const x of [-18, -6, 6, 18]) BOXES.push([x - 0.6, x + 0.6, 3.4, 4.6]);
  for (const z of [-5, -2, 1]) BOXES.push([19.5, 28.5, z - 0.35, z + 0.35]);

  const airportGltf = assets.airport || getCachedGLTF('models/env/airport.glb');
  const agentGltf = assets.agent || getCachedGLTF('models/characters/agent.glb');
  const crowdGltf = assets.crowd || getCachedGLTF('models/characters/crowd.glb');
  if (!airportGltf || !agentGltf) throw new Error('airport.glb and agent.glb must be loaded before buildAirport()');

  const env = cloneEnvScene(airportGltf, { lod: Q.lod, shadows: Q.shadows });
  root.add(env);

  // Crisp Arabic canvas signs mounted flush in front of Blender signboard housings
  // (housings front faces are at z = -11.925 and z = -0.525 in blender/env/airport.py)
  const s1 = sign('تسجيل الوصول · الرحلات', { w: 10, h: 1.4 });
  s1.position.set(0, 5, -11.9);
  root.add(s1);

  const s2 = sign('البوابة ١٢', { w: 5, h: 1.2, bg: '#c08a3e' });
  s2.position.set(25, 5, -11.9);
  root.add(s2);

  const s3 = sign('البوابات', { w: 5, h: 1, bg: '#1d3b5a' });
  s3.position.set(14, 6, -0.5);
  root.add(s3);

  // Rigged check-in agent behind the counter facing +z
  const agent = makeGlbPerson(agentGltf, { shadows: Q.shadows });
  agent.group.position.set(0, 0, -10);
  root.add(agent.group);

  // Glowing floor marker at Gate 12
  const ring = add(
    new THREE.RingGeometry(0.8, 1.05, 40),
    glowM(0xffd68c, 0xffc04a, 1.5),
    25,
    0.05,
    -9.6,
    root,
    false,
  );
  ring.rotation.x = -Math.PI / 2;

  // Instanced GLB travellers wandering the departures hall
  const rnd = seeded(31);
  const crowd = makeCrowd(Q.airportCrowd, rnd, {
    robeRatio: 0.35,
    streetRatio: 0.75,
    bareRatio: 0,
    shadows: Q.shadows,
    crowdGltf,
  });
  root.add(crowd.group);
  const walk = wanderers(crowd, rnd, [-26, 28, -6.5, 11], { avoid: BOXES });

  function update(dt, t, p) {
    walk(dt, t, p);
    agent.animate(dt, 0, { talk: voice.speaking && voice.who === 'agent' });
  }

  function dispose() {
    agent.dispose();
    crowd.dispose();
    for (const s of [s1, s2, s3]) {
      s.material?.map?.dispose();
      s.material?.dispose();
      s.geometry?.dispose();
    }
    ring.geometry?.dispose();
    ring.material?.dispose();
  }

  return { root, update, ring, dispose };
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
