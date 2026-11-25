import * as THREE from 'three';
import { glowM, adder, collideBoxes } from './kit.js';
import { makeCrowd, makeGlbPerson, seeded } from '../people.js';
import { cloneEnvScene, getCachedGLTF } from '../loaders.js';
import { voice } from '../voice.js';
import { Q } from '../quality.js';

// Chapter 3 — inside the plane. The player walks the aisle (|x| < 0.9) to the lavatory at the
// back galley to make wudu and put on ihram, then waits for the captain's miqat announcement.
export const PLANE_SPOTS = { lav: new THREE.Vector3(0.7, 0, 11.2) };
const LAV = [1.3, 3.6, 10, 12.6];

export function buildPlane(assets = {}) {
  const root = new THREE.Group();
  const add = adder(root);

  const planeGltf = assets.plane || getCachedGLTF('models/env/plane.glb');
  const attendantGltf = assets.attendant || getCachedGLTF('models/characters/attendant.glb');
  const crowdGltf = assets.crowd || getCachedGLTF('models/characters/crowd.glb');
  if (!planeGltf || !attendantGltf) throw new Error('plane.glb and attendant.glb must be loaded before buildPlane()');

  const env = cloneEnvScene(planeGltf, { lod: Q.lod, shadows: Q.shadows });
  root.add(env);

  // Glowing lavatory floor marker
  const ring = add(
    new THREE.RingGeometry(0.55, 0.75, 40),
    glowM(0xffd68c, 0xffc04a, 1.5),
    PLANE_SPOTS.lav.x,
    0.08,
    PLANE_SPOTS.lav.z,
    root,
    false,
  );
  ring.rotation.x = -Math.PI / 2;

  // Rigged flight attendant near rear galley facing -z (down the cabin aisle)
  const attendant = makeGlbPerson(attendantGltf, { shadows: Q.shadows });
  attendant.group.position.set(-1.9, 0, 9.4);
  attendant.group.rotation.y = Math.PI;
  root.add(attendant.group);

  // Seated passengers (14 rows x 6 seats matching blender/env/plane.py, seats face -Z)
  // Seats have cushion top at y ~ 0.70, backrest front at dz ~ +0.19..+0.27.
  // crowd_seated_* has hips at y = 0.58 and faces +Z locally -> heading Math.PI faces -Z,
  // y = +0.10 sits thighs flush on cushion, z + 0.06 aligns back against reclined backrest.
  const rows = [];
  for (let i = 0; i < 14; i++) rows.push(-14 + i * 1.6);
  const xs = [-3, -2.2, -1.4, 1.4, 2.2, 3];
  const rnd = seeded(41);
  const seats = [];
  for (const z of rows) {
    for (const x of xs) {
      if (rnd() < 0.72 && !(Math.abs(z + 2.8) < 0.1 && x === 1.4)) seats.push([x, z]);
    }
  }

  const crowd = makeCrowd(seats.length, rnd, {
    robeRatio: 0.35,
    streetRatio: 0.5,
    bareRatio: 0,
    seated: true,
    shadows: Q.shadows,
    crowdGltf,
  });
  seats.forEach(([x, z], i) => crowd.place(i, x, z + 0.06, Math.PI, 0, 0.1, false));
  crowd.commit();
  root.add(crowd.group);

  function update(dt) {
    attendant.animate(dt, 0, { talk: voice.speaking && voice.who === 'attendant' });
  }

  function dispose() {
    attendant.dispose();
    crowd.dispose();
    ring.geometry?.dispose();
    ring.material?.dispose();
  }

  return { root, update, ring, dispose };
}

export const planeLayout = {
  id: 'plane', outfit: 'street',
  spawn: { pos: new THREE.Vector3(0, 0, -2.8), heading: 0 },
  collide(p) {
    const hit = collideBoxes(p, [LAV], null);
    p.z = Math.min(12.2, Math.max(-14.6, p.z));
    const lim = p.z < 8.7 ? 0.5 : 2.6;
    p.x = Math.min(lim, Math.max(-lim, p.x));
    return hit;
  },
  zoom: [3, 7],
  cam: { pitch: 0.3, dist: 5.2, clamp: { x: [-3.2, 3.2], y: 3.9, z: [-15.2, 12.4] } },
  mentor: { side: 0, back: 1.4 },
  mentorStart: new THREE.Vector3(0, 0, -4.4),
  background: 0x101826, fog: [30, 60, 0x101826],
  light: { sky: 0xdfe8ff, ground: 0x7a6a55, hemi: 1.15, sun: 0xffe1b5, si: 1.4, pos: [8, 14, 6], area: 16 },
  tags: [
    { text: 'الحمّام', pos: new THREE.Vector3(1.3, 3.0, 11.2), spot: 'lav' },
    { text: 'المضيفة', pos: new THREE.Vector3(-1.9, 2.5, 9.4) },
  ],
  map: { bounds: [-3.7, 3.7, -15.5, 12.7], boxes: [LAV] },
};
