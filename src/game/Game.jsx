import { useEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { Q, dpr } from './quality.js';
import { useStore, resetUi, CINEMATIC } from './store.js';
import { world } from './refs.js';
import { buildMataf, matafLayout } from './mataf.js';
import { makePerson } from './people.js';
import { Controller } from './Controller.jsx';
import { Hud } from './hud/Hud.jsx';
import { stats } from './rites/stats.js';
import { chapterById } from './chapters.js';

window.__game = { useStore, world };    // console / test hook

function Scene({ chapter }) {
  const ch = chapterById(chapter), layout = ch.layout;
  const { scene } = useThree();
  const built = useMemo(() => ch.build(), [chapter]);
  const heroes = useMemo(() => {
    const player = makePerson({ skin: 0xc68a5e, hair: 0x231a14, shirt: 0x3f7cac, pants: 0x3a3f4a });
    const mentor = makePerson({ skin: 0x9a6a48, hair: 0xb9b4ac, build: 1.08, scale: 0.97, shirt: 0xc9b48a, pants: 0x6b5b45 });
    return { player, mentor };
  }, []);
  const ring = useMemo(() => {
    const m = new THREE.Mesh(new THREE.RingGeometry(0.75, 0.95, 40), new THREE.MeshBasicMaterial({ color: 0xffd68c, transparent: true, opacity: 0.9, side: THREE.DoubleSide }));
    m.rotation.x = -Math.PI / 2; return m;
  }, []);

  useEffect(() => {
    const prev = world.chapter; world.chapter = chapter;
    scene.background = new THREE.Color(layout.background);
    scene.fog = new THREE.Fog(layout.fog[2], layout.fog[0], layout.fog[1]);
    world.layout = layout;
    world.heroes = heroes;
    const P = world.player; P.pos.copy(layout.spawn.pos); P.heading = layout.spawn.heading; P.speed = 0;
    if (layout.mentorStart) world.mentor.pos.copy(layout.mentorStart); else world.mentor.pos.copy(P.pos).add(new THREE.Vector3(1.4, 0, -0.6));
    world.mentor.heading = P.heading;
    const cam = layout.cam || {};
    world.cam.yaw = cam.mode === 'fixed' ? cam.yaw : P.heading + Math.PI + (layout.yawBias || 0);
    world.cam.pitch = cam.pitch ?? 0.42; world.cam.dist = cam.dist ?? 9; world.cam.want = null;
    // arriving from Makkah: start far and high, then glide down to the player (first sight of the Kaaba)
    if (cam.introDist && prev === 'makkah') { world.cam.want = world.cam.dist; world.cam.dist = cam.introDist; }
    // costume for the chapter
    heroes.player.setOutfit(layout.outfit || 'ihram'); heroes.mentor.setOutfit(layout.outfit || 'ihram');
    world.talbiyah = chapter === 'makkah';
    resetUi();
    useStore.setState({ talbiyah: world.talbiyah, chapterTitle: `الفصل ${'٠١٢٣٤٥٦٧٨٩'[ch.n]} · ${ch.title}` });
    const goTo = id => useStore.setState({ chapter: id });
    const end = () => useStore.setState({ screen: 'end', summary: { ...stats.s } });
    world.rites = ch.rites({ goTo, end, scene: built });
    const t = setTimeout(() => world.rites.start(), 400);
    return () => clearTimeout(t);
  }, [chapter]);

  useFrame((_, dt) => built.update(Math.min(dt, 0.05) * world.timeScale, world.time, world.player.pos));
  const L = layout.light, A = L.area || 55;
  return (
    <>
      <hemisphereLight args={[L.sky, L.ground, L.hemi]} />
      <directionalLight position={L.pos} intensity={L.si} color={L.sun} castShadow={Q.shadows}
        shadow-mapSize={[2048, 2048]} shadow-bias={-0.0004} shadow-normalBias={0.03}
        shadow-camera-left={-A} shadow-camera-right={A} shadow-camera-top={A} shadow-camera-bottom={-A} shadow-camera-far={220} />
      <primitive object={built.root} />
      <primitive object={heroes.player.group} />
      <primitive object={heroes.mentor.group} />
      <primitive object={ring} />
      <Controller ring={ring} />
    </>
  );
}

// Lite: cap at ~30 fps (render every other display frame)
function FpsCap() {
  const { invalidate } = useThree();
  useEffect(() => {
    let id, odd = false;
    const loop = () => { odd = !odd; if (odd || Q.fps > 30) invalidate(); id = requestAnimationFrame(loop); };
    id = requestAnimationFrame(loop); return () => cancelAnimationFrame(id);
  }, [invalidate]);
  return null;
}

export function Game() {
  const screen = useStore(s => s.screen), chapter = useStore(s => s.chapter);
  useEffect(() => { document.getElementById('loading')?.remove(); if (CINEMATIC) useStore.setState({ screen: 'play' }); }, []);
  const playing = screen !== 'title';
  return (
    <>
      <Canvas id="game" dpr={dpr()} shadows={Q.shadows} frameloop={Q.fps <= 30 ? 'demand' : 'always'}
        gl={{ antialias: Q.name !== 'lite', powerPreference: 'high-performance' }}
        camera={{ fov: 50, near: 0.1, far: 600, position: [20, 18, 20] }}>
        {Q.fps <= 30 && <FpsCap />}
        {playing ? <Scene key={chapter} chapter={chapter} /> : <TitleBackdrop />}
      </Canvas>
      <Hud />
    </>
  );
}

// slow orbit round the Mataf behind the title screen
function TitleBackdrop() {
  const built = useMemo(() => buildMataf(), []);
  const { scene, camera } = useThree();
  useEffect(() => { scene.background = new THREE.Color(matafLayout.background); scene.fog = new THREE.Fog(0x2a3655, 70, 170); }, []);
  const t = useRef(0);
  useFrame((_, dt) => {
    t.current += dt * 0.05; built.update(dt, t.current * 20, { x: 999, z: 999 });
    camera.position.set(Math.cos(t.current) * 40, 22, Math.sin(t.current) * 40); camera.lookAt(0, 4, 0);
  });
  const L = matafLayout.light;
  return (<><hemisphereLight args={[L.sky, L.ground, L.hemi]} /><directionalLight position={L.pos} intensity={L.si} color={L.sun} /><primitive object={built.root} /></>);
}
