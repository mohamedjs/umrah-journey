import * as THREE from 'three';
import { Q } from '../quality.js';
import { canvasTex } from '../textures.js';

// Small helpers shared by the chapter scenes (home, airport, plane, Makkah).
export const M = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.75, ...o });
export const glowM = (c = 0xffd68c, e = 0xffb43a, k = 1.2) => M(c, { emissive: e, emissiveIntensity: k });

export function adder(root) {
  return (geo, mat, x = 0, y = 0, z = 0, p = root, cast = true) => {
    const o = new THREE.Mesh(geo, mat); o.position.set(x, y, z);
    o.castShadow = cast && Q.shadows; o.receiveShadow = Q.shadows; p.add(o); return o;
  };
}

// an axis-aligned box obstacle [x0, x1, z0, z1] drawn as a block (h tall) and returned for collisions
export function block(add, mat, [x0, x1, z0, z1], h, y0 = 0) {
  add(new THREE.BoxGeometry(x1 - x0, h, z1 - z0), mat, (x0 + x1) / 2, y0 + h / 2, (z0 + z1) / 2);
  return [x0, x1, z0, z1];
}

// a flat sign with Arabic text (canvas texture), facing +z unless rotated
export function sign(text, { w = 4, h = 1, bg = '#1d3b5a', fg = '#ffffff', size = 90 } = {}) {
  const tex = canvasTex(1024, Math.round(1024 * h / w), (x, W, H) => {
    x.fillStyle = bg; x.fillRect(0, 0, W, H);
    x.fillStyle = fg; x.font = `800 ${size}px Taj, Tajawal, sans-serif`; x.textAlign = 'center'; x.textBaseline = 'middle';
    x.direction = 'rtl'; x.fillText(text, W / 2, H / 2 + 6);
  });
  return new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: tex }));
}

// glowing ring + floating item marker for something to pick up / use
export function marker(add, x, y, z) {
  const ring = add(new THREE.TorusGeometry(0.55, 0.035, 8, 40), glowM(0xffd68c, 0xffc35a, 1.4), x, y, z, undefined, false);
  return ring;
}

// push a point out of a list of boxes and keep it inside bounds [x0, x1, z0, z1]
export function collideBoxes(p, boxes, bounds, rad = 0.38) {
  let hit = null;
  for (const b of boxes) {
    const x0 = b[0] - rad, x1 = b[1] + rad, z0 = b[2] - rad, z1 = b[3] + rad;
    if (p.x > x0 && p.x < x1 && p.z > z0 && p.z < z1) {
      const dx = Math.min(p.x - x0, x1 - p.x), dz = Math.min(p.z - z0, z1 - p.z);
      if (dx < dz) p.x = p.x - x0 < x1 - p.x ? x0 : x1; else p.z = p.z - z0 < z1 - p.z ? z0 : z1;
      hit = b.name || 'wall';
    }
  }
  if (bounds) {
    p.x = Math.min(bounds[1] - rad, Math.max(bounds[0] + rad, p.x));
    p.z = Math.min(bounds[3] - rad, Math.max(bounds[2] + rad, p.z));
  }
  return hit;
}

// people walking back and forth between random points (airport hall, Makkah plaza)
export function wanderers(crowd, rnd, area, { speed = [0.8, 1.3], avoid = [], to = null } = {}) {
  const [x0, x1, z0, z1] = area;
  const pick = () => ({ x: x0 + rnd() * (x1 - x0), z: z0 + rnd() * (z1 - z0) });
  const free = q => !avoid.some(b => q.x > b[0] - 0.6 && q.x < b[1] + 0.6 && q.z > b[2] - 0.6 && q.z < b[3] + 0.6);
  const ok = () => { let q; do q = pick(); while (!free(q)); return q; };
  const ag = crowd.info.map(() => { const a = ok(); return { ...a, t: to ? to(rnd) : ok(), v: speed[0] + rnd() * (speed[1] - speed[0]), h: 0 }; });
  return (dt, t, player) => {
    for (let i = 0; i < ag.length; i++) {
      const g = ag[i], dx = g.t.x - g.x, dz = g.t.z - g.z, d = Math.hypot(dx, dz);
      if (d < 0.5) { if (to) { const s = ok(); g.x = s.x; g.z = s.z; g.t = to(rnd); } else g.t = ok(); }
      else { g.x += dx / d * g.v * dt; g.z += dz / d * g.v * dt; g.h = Math.atan2(dx, dz); }
      let x = g.x, z = g.z;
      const px = x - player.x, pz = z - player.z, dd = px * px + pz * pz;
      if (dd < 2.6) { const k = (1.6 - Math.sqrt(dd)) / Math.max(0.2, Math.sqrt(dd)); x += px * k; z += pz * k; }
      crowd.place(i, x, z, g.h, t);
    }
    crowd.commit();
  };
}
