import { useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { world } from './refs.js';
import { input, initInput, onKey } from './input.js';
import { useStore, isBlocking, next, closeOverlay, CINEMATIC } from './store.js';
import { talbiyah } from './rites/kit.js';
import { voice } from './voice.js';

const WALK = 3.4, RUN = 5.6;
const lerpAngle = (a, b, k) => a + Math.atan2(Math.sin(b - a), Math.cos(b - a)) * k;
const v = new THREE.Vector3(), tgt = new THREE.Vector3();
let inited = false, actT = 0;

export function runAction(id) { world.rites?.act(id); }

// Player movement (keys / joystick / autopilot), the mentor walking beside him, the follow
// camera, and the per-frame rites update.
export function Controller({ ring }) {
  const { camera, gl } = useThree();
  useEffect(() => {
    world.camera = camera;
    if (inited) return; inited = true;
    initInput(gl.domElement);
    onKey(code => {
      const st = useStore.getState();
      if (st.screen !== 'play') return;
      if (st.overlay) { if (['Enter', 'Space', 'KeyE', 'KeyG'].includes(code)) closeOverlay(); return; }
      if (code === 'Enter' || code === 'Space') return next();
      if (code === 'KeyF') return useStore.setState({ auto: !st.auto });
      if (code === 'KeyT' && st.talbiyah) return talbiyah();
      if (code === 'Escape') return useStore.setState({ qaOpen: false });
      const a = st.action;
      if (a && code === 'Key' + a.key) runAction(a.id);
    });
  }, []);

  // ?speed=N runs N fixed sub-steps per frame (fast-forward for testing)
  useFrame((_, rawDt) => { for (let i = 0; i < world.timeScale; i++) step(Math.min(rawDt, 0.05)); });
  function step(dt) {
    world.time += dt;
    const P = world.player, C = world.cam, L = world.layout, st = useStore.getState();
    if (!L) return;

    // camera input
    if (input.dragX || input.dragY) { C.yaw -= input.dragX * 0.006; C.pitch = THREE.MathUtils.clamp(C.pitch + input.dragY * 0.004, 0.1, 1.3); C.lastDrag = world.time; input.dragX = input.dragY = 0; }
    if (input.zoom) { C.dist = THREE.MathUtils.clamp(C.dist + input.zoom, L.zoom[0], L.zoom[1]); input.zoom = 0; C.want = null; }
    if (C.want) { C.dist += (C.want - C.dist) * Math.min(1, dt * 0.7); if (Math.abs(C.dist - C.want) < 0.05) C.want = null; }

    // movement
    const blocked = isBlocking();
    let mx = 0, mz = 0, run = input.run || st.runHold, auto = false;
    if (!blocked) {
      if (input.x || input.y) {
        const fx = -Math.sin(C.yaw), fz = -Math.cos(C.yaw);
        mx = fx * input.y + Math.cos(C.yaw) * input.x; mz = fz * input.y - Math.sin(C.yaw) * input.x;
        if (st.auto) useStore.setState({ auto: false });
      } else if (st.auto && world.rites) {
        const t = world.rites.autopilot();
        if (t) { const dx = t.x - P.pos.x, dz = t.z - P.pos.z, d = Math.hypot(dx, dz); if (d > 0.5) { mx = dx / d; mz = dz / d; run = run || !!t.run; auto = true; } }
      }
    }
    const len = Math.hypot(mx, mz);
    if (len > 1) { mx /= len; mz /= len; }
    const want = Math.min(1, len) * (run ? RUN : WALK);
    P.speed += (want - P.speed) * Math.min(1, dt * 8);
    if (len > 0.05) P.heading = lerpAngle(P.heading, Math.atan2(mx, mz), Math.min(1, dt * 10));
    const dirx = Math.sin(P.heading), dirz = Math.cos(P.heading);
    P.pos.x += dirx * P.speed * dt; P.pos.z += dirz * P.speed * dt;
    const hit = L.collide(P.pos);
    if (hit) world.rites?.onHit(hit);
    P.moving = P.speed > 0.4; P.running = run && P.moving;

    // hero rig
    world.gesture = Math.max(0, world.gesture - dt); world.pray = Math.max(0, world.pray - dt);
    const H = world.heroes.player;
    H.group.position.copy(P.pos); H.group.rotation.y = P.heading;
    H.animate(dt, P.speed, { talk: voice.speaking && voice.who === 'player', running: P.running, raise: world.gesture, pray: world.pray > 0 ? (world.pray % 2) / 2 : 0 });
    ring.position.set(P.pos.x, 0.04, P.pos.z);

    // the mentor walks beside the player, on his right and a little behind
    const Mn = world.mentor, MH = world.heroes.mentor;
    const mo = L.mentor || { side: 1.3, back: 0.7 };
    tgt.set(P.pos.x - Math.cos(P.heading) * mo.side - dirx * mo.back, 0, P.pos.z + Math.sin(P.heading) * mo.side - dirz * mo.back);
    if (Mn.pos.distanceTo(P.pos) > 15) Mn.pos.copy(tgt);      // fell far behind (teleport / chapter switch)
    v.subVectors(tgt, Mn.pos); v.y = 0;
    const md = v.length(), ms = md > 0.25 ? Math.min(md * 2.2, RUN + 0.5) : 0;
    if (md > 0.01) { Mn.pos.addScaledVector(v, Math.min(1, (ms * dt) / md)); }
    L.collide(Mn.pos);
    Mn.heading = ms > 0.4 ? lerpAngle(Mn.heading, Math.atan2(v.x, v.z), Math.min(1, dt * 6)) : lerpAngle(Mn.heading, P.heading, Math.min(1, dt * 3));
    MH.group.position.copy(Mn.pos); MH.group.rotation.y = Mn.heading;
    MH.animate(dt, ms, { talk: voice.speaking && voice.who === 'hassan', running: ms > WALK + 0.3, raise: world.gesture > 0 ? world.gesture : 0, pray: world.pray > 0 ? (world.pray % 2) / 2 : 0 });

    // follow camera: eases back behind the player while walking (unless dragged lately)
    if (L.cam?.mode !== 'fixed' && P.moving && world.time - C.lastDrag > 2) C.yaw = lerpAngle(C.yaw, P.heading + Math.PI + (L.yawBias || 0), Math.min(1, dt * (auto ? 1.4 : 0.9)));
    const cp = Math.cos(C.pitch), sp = Math.sin(C.pitch);
    camera.position.set(P.pos.x + Math.sin(C.yaw) * cp * C.dist, 1.6 + sp * C.dist, P.pos.z + Math.cos(C.yaw) * cp * C.dist);
    const cl = L.cam?.clamp;
    if (cl) { if (cl.y) camera.position.y = Math.min(camera.position.y, cl.y); if (cl.x) camera.position.x = THREE.MathUtils.clamp(camera.position.x, ...cl.x); if (cl.z) camera.position.z = THREE.MathUtils.clamp(camera.position.z, ...cl.z); }
    // tawaf: look a little toward the Kaaba so it stays in the picture
    const lb = L.lookBias || 0, pr = Math.hypot(P.pos.x, P.pos.z) || 1;
    camera.lookAt(P.pos.x - (P.pos.x / pr) * lb, 1.4, P.pos.z - (P.pos.z / pr) * lb);

    if (st.screen === 'play' && world.rites && !st.overlay) world.rites.update(dt);
    // cinematic mode presses the action button by itself
    if (CINEMATIC && st.action && !blocked) { if ((actT += dt) > 0.5) { actT = 0; runAction(st.action.id); } } else actT = 0;
  }
  return null;
}
