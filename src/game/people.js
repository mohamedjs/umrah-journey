import * as THREE from 'three';

// Soft "clay" people from the concept: faces have no features (no eyes, nose or mouth).
export const SKIN = [0xc68a5e, 0xa86b45, 0xdba57c, 0x8a5a3b, 0xe0b48e];
const mat = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.75, ...o });
const WHITE = 0xf7f5ef;
const STREET = [0x4a6fa5, 0x7a5b3a, 0x3d6b4f, 0x8a3d3d, 0x5a5f6b, 0xc9b48a, 0x2f4a6b, 0xe3dccb];

// ---------------------------------------------------------------- hero rig (player, mentor)
// Returns { group, setOutfit('street'|'ihram'), setIdtiba(bool), animate(dt, speed, {running, raise, pray}) }.
// 'street' = shirt + trousers (home, airport, plane before ihram); 'ihram' = izar + rida.
export function makePerson({ skin = 0xc68a5e, hair = 0x231a14, scale = 1, build = 1, shirt = 0x3f7cac, pants = 0x3a3f4a } = {}) {
  const g = new THREE.Group();
  const sk = mat(skin, { roughness: 0.6 }), white = mat(WHITE, { roughness: 0.92 }), dark = mat(0x3a2a1c);
  const shirtM = mat(shirt, { roughness: 0.8 }), pantsM = mat(pants, { roughness: 0.85 });
  const legMeshes = [];
  const add = (geo, m, x, y, z, p = g) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.castShadow = true; p.add(o); return o; };
  const body = new THREE.Group(); g.add(body);

  // legs: pivot at the hip, skin shins under the izar, dark sandals
  const legs = [-1, 1].map(s => {
    const pv = new THREE.Group(); pv.position.set(s * 0.13, 0.92, 0); body.add(pv);
    legMeshes.push(add(new THREE.CapsuleGeometry(0.1, 0.62, 4, 10), sk, 0, -0.44, 0, pv));
    add(new THREE.BoxGeometry(0.17, 0.06, 0.3), dark, 0, -0.88, 0.04, pv);
    return pv;
  });
  // izar (lower sheet) and rida (upper sheet)
  const izar = add(new THREE.CylinderGeometry(0.31 * build, 0.38 * build, 0.66, 20), white, 0, 0.78, 0, body);
  add(new THREE.CapsuleGeometry(0.29 * build, 0.42, 6, 16), sk, 0, 1.33, 0, body);
  const rida = add(new THREE.CapsuleGeometry(0.305 * build, 0.4, 6, 16), white, 0, 1.31, 0, body);
  rida.scale.set(1, 0.97, 1.02);
  // shoulders: the left is always covered; the right is bare in idtiba'
  // (a rig faces +z, so its right side is -x)
  const lShoulder = add(new THREE.SphereGeometry(0.17, 14, 10), white, 0.27 * build, 1.6, 0, body);
  const rCover = add(new THREE.SphereGeometry(0.17, 14, 10), white, -0.27 * build, 1.6, 0, body);
  const rBare = add(new THREE.SphereGeometry(0.165, 14, 10), sk, -0.27 * build, 1.6, 0, body);
  // arms: pivot at the shoulder — arms[0] is the right arm (-x), arms[1] the left
  const arms = [-1, 1].map(s => {
    const pv = new THREE.Group(); pv.position.set(s * 0.4 * build, 1.6, 0); body.add(pv);
    const upper = add(new THREE.CapsuleGeometry(0.085, 0.26, 4, 10), white, 0, -0.18, 0, pv);
    add(new THREE.CapsuleGeometry(0.075, 0.24, 4, 10), sk, 0, -0.48, 0, pv);
    add(new THREE.SphereGeometry(0.075, 10, 8), sk, 0, -0.65, 0, pv);
    pv.rotation.z = s * 0.1;
    return { pv, upper };
  });
  // head: a plain sphere (no features) + short hair
  add(new THREE.CylinderGeometry(0.09, 0.1, 0.12, 10), sk, 0, 1.73, 0, body);
  const head = add(new THREE.SphereGeometry(0.24, 24, 18), sk, 0, 1.95, 0, body);
  add(new THREE.SphereGeometry(0.25, 24, 18, 0, Math.PI * 2, 0, 1.15), mat(hair), 0, 1.97, -0.025, body);

  let idtiba = false, phase = 0, outfit = 'ihram';
  function setIdtiba(on) {
    idtiba = on && outfit === 'ihram'; rCover.visible = !idtiba; rBare.visible = idtiba;
    arms[0].upper.material = idtiba ? sk : (outfit === 'ihram' ? white : shirtM);
  }
  function setOutfit(o) {
    outfit = o; const ih = o === 'ihram';
    for (const m of legMeshes) m.material = ih ? sk : pantsM;
    izar.material = ih ? white : pantsM; izar.scale.set(ih ? 1 : 0.86, 1, ih ? 1 : 0.86);
    rida.material = lShoulder.material = rCover.material = arms[1].upper.material = ih ? white : shirtM;
    setIdtiba(false);
  }
  setIdtiba(false);

  function animate(dt, speed, { running = false, raise = 0, pray = 0, talk = false } = {}) {
    const k = Math.min(1, speed / 3);
    // raml / jogging: quicker, shorter steps
    phase += dt * (running ? 13 : 8.5) * (speed > 0.1 ? 1 : 0);
    const sw = Math.sin(phase) * (running ? 0.5 : 0.62) * k;
    legs[0].rotation.x = sw; legs[1].rotation.x = -sw;
    arms[1].pv.rotation.x = -sw * 0.8;
    arms[0].pv.rotation.x = raise > 0 ? -2.3 * Math.min(1, raise * 3) : sw * 0.8;
    arms[0].pv.rotation.z = raise > 0 ? -0.35 : -0.1;
    body.position.y = Math.abs(Math.sin(phase)) * 0.05 * k;
    // talking while standing: a small nod and a hand gesture
    if (talk && speed < 0.4 && raise <= 0) { const t = performance.now() / 1000; arms[1].pv.rotation.x = -0.7 + Math.sin(t * 5) * 0.25; body.rotation.y = Math.sin(t * 2.3) * 0.06; } else body.rotation.y = 0;
    body.rotation.x = pray > 0 ? Math.sin(Math.min(1, pray) * Math.PI) * 0.9 : (running ? 0.08 : 0.02) * k;
  }
  g.scale.setScalar(scale);
  return { group: g, head, setIdtiba, setOutfit, animate, get idtiba() { return idtiba; }, get outfit() { return outfit; } };
}

// ---------------------------------------------------------------- instanced crowd
// Instanced body + head (+ the bare right shoulder of men in idtiba', tawaf only).
// Men in white ihram, women in abayas with a hijab.
// `place(i, x, z, heading, bob)` is called by the scene every frame.
export function makeCrowd(n, rnd, { robeRatio = 0.33, bareRatio = 0.8, streetRatio = 0, shadows = false } = {}) {
  const bodyG = new THREE.CapsuleGeometry(0.3, 0.92, 3, 8);
  const headG = new THREE.SphereGeometry(0.24, 10, 8);
  const shoulderG = new THREE.SphereGeometry(0.15, 8, 6);
  const mb = new THREE.InstancedMesh(bodyG, mat(0xffffff, { roughness: 0.9 }), n);
  const mh = new THREE.InstancedMesh(headG, mat(0xffffff, { roughness: 0.7 }), n);
  const ms = new THREE.InstancedMesh(shoulderG, mat(0xffffff, { roughness: 0.6 }), n);   // men's bare right shoulder
  const c = new THREE.Color(), info = [];
  for (let i = 0; i < n; i++) {
    const woman = rnd() < robeRatio, s = 0.88 + rnd() * 0.22, skin = SKIN[(rnd() * SKIN.length) | 0];
    const street = !woman && rnd() < streetRatio;
    info.push({ woman, s, man: !woman, bare: !woman && !street && rnd() < bareRatio, phase: rnd() * 6.28 });
    mb.setColorAt(i, c.set(woman ? [0x2b2b33, 0x3d3a45, 0xf2efe6, 0x5a4f63][(rnd() * 4) | 0] : street ? STREET[(rnd() * STREET.length) | 0] : 0xf6f3ec));
    mh.setColorAt(i, c.set(woman ? [0x2b2b33, 0xeae6dd, 0x6b5b75][(rnd() * 3) | 0] : skin));
    ms.setColorAt(i, c.set(skin));
  }
  for (const m of [mb, mh, ms]) { m.castShadow = false; m.receiveShadow = shadows; m.frustumCulled = false; m.instanceMatrix.setUsage(THREE.DynamicDrawUsage); }
  const o = new THREE.Object3D(), group = new THREE.Group(); group.add(mb, mh, ms);
  const hide = new THREE.Matrix4().makeScale(0, 0, 0);
  return {
    group, info, n,
    // y: lift / drop (e.g. -0.55 for a seated passenger), bob: false for people standing still
    place(i, x, z, heading, t, y = 0, bobOn = true) {
      const f = info[i], s = f.s, bob = bobOn ? Math.abs(Math.sin(t * 7 + f.phase)) * 0.04 : 0;
      o.position.set(x, 0.92 * s + bob + y, z); o.rotation.set(0, heading, 0); o.scale.setScalar(s); o.updateMatrix(); mb.setMatrixAt(i, o.matrix);
      o.position.y = 1.86 * s + bob + y; o.updateMatrix(); mh.setMatrixAt(i, o.matrix);
      if (f.bare) { o.position.set(x - Math.cos(heading) * 0.24 * s, 1.5 * s + bob + y, z + Math.sin(heading) * 0.24 * s); o.updateMatrix(); ms.setMatrixAt(i, o.matrix); }
      else ms.setMatrixAt(i, hide);
    },
    commit() { mb.instanceMatrix.needsUpdate = mh.instanceMatrix.needsUpdate = ms.instanceMatrix.needsUpdate = true; },
  };
}

export function seeded(seed = 11) { return () => (seed = (seed * 16807) % 2147483647) / 2147483647; }

// a standing woman (flight attendant): long robe + hijab, no facial features
export function makeWoman({ robe = 0x7c2f3a, hijab = 0x7c2f3a, skin = 0xdba57c } = {}) {
  const g = new THREE.Group();
  const add = (geo, m, x, y, z) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.castShadow = true; g.add(o); return o; };
  add(new THREE.CylinderGeometry(0.32, 0.48, 1.25, 20), mat(robe), 0, 0.62, 0);
  add(new THREE.CapsuleGeometry(0.28, 0.45, 6, 16), mat(robe), 0, 1.38, 0);
  add(new THREE.SphereGeometry(0.27, 24, 18), mat(hijab), 0, 1.9, 0);
  add(new THREE.SphereGeometry(0.2, 20, 14), mat(skin, { roughness: 0.6 }), 0, 1.88, 0.1).scale.set(1, 1.1, 0.7);
  return g;
}
