import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { M, glowM, adder, collideBoxes } from './kit.js';
import { makeCrowd, makeWoman, seeded } from '../people.js';
import { Q } from '../quality.js';

// Chapter 3 — inside the plane. The player walks the aisle (|x| < 0.9) to the lavatory at the
// back galley to make wudu and put on ihram, then waits for the captain's miqat announcement.
export const PLANE_SPOTS = { lav: new THREE.Vector3(0.7, 0, 11.2) };
const LAV = [1.3, 3.6, 10, 12.6];

export function buildPlane() {
  const root = new THREE.Group(), add = adder(root);
  const shell = add(new THREE.CylinderGeometry(4.2, 4.2, 30, 40, 1, true, Math.PI * 0.55, Math.PI * 1.9), M(0xeef0f2, { side: THREE.BackSide }), 0, 2.2, -1.5, root, false);
  shell.rotation.x = Math.PI / 2;
  add(new THREE.BoxGeometry(7.4, 0.1, 30), M(0x4a5468), 0, 0, -1.5, root, false);
  add(new THREE.BoxGeometry(1.1, 0.02, 21), M(0x7c2f3a), 0, 0.06, -4, root, false);
  add(new THREE.BoxGeometry(7.4, 6, 0.2), M(0xe9e2d4), 0, 2.5, 12.8, root, false);            // rear wall
  add(new THREE.BoxGeometry(7.4, 6, 0.2), M(0xe9e2d4), 0, 2.5, -15.6, root, false);           // front bulkhead
  add(new THREE.BoxGeometry(2, 3.2, 0.1), M(0x7c2f3a), 0, 1.6, -15.45, root, false);
  // windows (sunset)
  const win = new THREE.InstancedMesh(new RoundedBoxGeometry(0.05, 0.75, 0.55, 3, 0.2), M(0xffb36b, { emissive: 0xff9a52, emissiveIntensity: 1.6 }), 34);
  const o = new THREE.Object3D(); let k = 0;
  for (let z = -15; z < 9 && k < 34; z += 1.6) for (const s of [-1, 1]) { o.position.set(s * 3.85, 2.3, z); o.updateMatrix(); win.setMatrixAt(k++, o.matrix); }
  win.count = k; root.add(win);
  // seats (instanced: cushion, back, headrest)
  const rows = []; for (let z = -14; z < 8; z += 1.6) rows.push(z);
  const xs = [-3, -2.2, -1.4, 1.4, 2.2, 3], n = rows.length * xs.length;
  const parts = [[new RoundedBoxGeometry(0.72, 0.25, 0.7, 3, 0.08), M(0x26365a), 0, 0.65, 0], [new RoundedBoxGeometry(0.72, 1.2, 0.2, 3, 0.08), M(0x26365a), 0, 1.25, 0.35], [new RoundedBoxGeometry(0.6, 0.25, 0.12, 3, 0.05), M(0xe9e4da), 0, 1.75, 0.3]];
  for (const [geo, mat, dx, dy, dz] of parts) {
    const im = new THREE.InstancedMesh(geo, mat, n); let i = 0;
    for (const z of rows) for (const x of xs) { o.position.set(x + dx, dy, z + dz); o.updateMatrix(); im.setMatrixAt(i++, o.matrix); }
    root.add(im);
  }
  // overhead bins + ceiling light strip
  for (const s of [-1, 1]) add(new RoundedBoxGeometry(1.8, 0.7, 24, 3, 0.15), M(0xf3f4f6), s * 2.75, 4, -3.5, root, false);
  add(new THREE.BoxGeometry(1.2, 0.04, 24), M(0xffffff, { emissive: 0xfff2d8, emissiveIntensity: 0.7 }), 0, 4.6, -3.5, root, false);
  // lavatory at the back galley
  add(new THREE.BoxGeometry(LAV[1] - LAV[0], 3.4, LAV[3] - LAV[2]), M(0xdcdfe3), (LAV[0] + LAV[1]) / 2, 1.7, (LAV[2] + LAV[3]) / 2);
  add(new THREE.BoxGeometry(0.06, 2.2, 0.9), glowM(0xffe2a6, 0xffc35a, 0.6), LAV[0] - 0.03, 1.2, 11.2, root, false);
  add(new THREE.BoxGeometry(1.6, 1.1, 2.2), M(0xcfd3d8), -2.6, 0.55, 11, root, false);        // galley trolley
  const ring = add(new THREE.RingGeometry(0.55, 0.75, 40), glowM(0xffd68c, 0xffc04a, 1.5), PLANE_SPOTS.lav.x, 0.08, PLANE_SPOTS.lav.z, root, false); ring.rotation.x = -Math.PI / 2;
  const attendant = makeWoman({ robe: 0x7c2f3a, hijab: 0x7c2f3a }); attendant.position.set(-1.9, 0, 9.4); attendant.rotation.y = Math.PI; root.add(attendant);
  // seated passengers (static: placed once)
  const rnd = seeded(41), seats = [];
  for (const z of rows) for (const x of xs) if (rnd() < 0.72 && !(Math.abs(z + 2.8) < 0.1 && x === 1.4)) seats.push([x, z]);
  const crowd = makeCrowd(seats.length, rnd, { robeRatio: 0.35, streetRatio: 0.5, bareRatio: 0, shadows: Q.shadows });
  seats.forEach(([x, z], i) => crowd.place(i, x, z - 0.05, Math.PI, 0, -0.42, false)); crowd.commit();
  root.add(crowd.group);
  return { root, update() {}, ring };
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
