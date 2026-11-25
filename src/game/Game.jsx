import { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { Q, dpr } from './quality.js';
import { useStore, resetUi, CINEMATIC } from './store.js';
import { world } from './refs.js';
import { buildMataf, matafLayout } from './mataf.js';
import { makeGlbPerson } from './people.js';
import { CORE_CHAR_GLBS, CHAPTER_GLBS, useGLTF, useGLTFMany } from './loaders.js';
import { Controller } from './Controller.jsx';
import { Hud } from './hud/Hud.jsx';
import { stats } from './rites/stats.js';
import { CHAPTERS, chapterById } from './chapters.js';

window.__game = { useStore, world };    // console / test hook

const TWILIGHT = new Set(['tawaf', 'makkah', 'plane']);
const TITLE_GLBS = [
  'models/characters/crowd.glb',
  'models/env/kaaba.glb',
  'models/env/maqam.glb',
  'models/env/haram_mataf.glb',
];

// Generate procedural RoomEnvironment IBL once per WebGLRenderer for crisp metallic/marble PBR response
const envCache = new WeakMap();
function getRoomEnvTexture(gl) {
  let tex = envCache.get(gl);
  if (tex) return tex;
  const pmrem = new THREE.PMREMGenerator(gl);
  const room = new RoomEnvironment();
  tex = pmrem.fromScene(room, 0.04).texture;
  room.dispose();
  pmrem.dispose();
  envCache.set(gl, tex);
  return tex;
}

function SceneEnv({ intensity = 0.7 }) {
  const { gl, scene } = useThree();
  useEffect(() => {
    world.gl = gl;
    scene.environment = getRoomEnvTexture(gl);
    scene.environmentIntensity = intensity;
  }, [gl, scene, intensity]);
  return null;
}

function SuspenseFlag({ onPending }) {
  useEffect(() => {
    world.sceneReady = false;
    onPending(true);
    return () => onPending(false);
  }, [onPending]);
  return null;
}

function Scene({ chapter }) {
  const ch = chapterById(chapter), layout = ch.layout;
  const { scene, gl } = useThree();

  // Load shared characters + chapter environment/NPC GLBs via Suspense before mounting frame 1
  const glbPaths = useMemo(
    () => [...CORE_CHAR_GLBS, ...(CHAPTER_GLBS[chapter] || [])],
    [chapter],
  );
  const gltfs = useGLTFMany(glbPaths);
  const playerGltf = gltfs[0];
  const mentorGltf = gltfs[1];

  const built = useMemo(() => ch.build(), [chapter]);
  const heroes = useMemo(() => {
    const outfit = layout.outfit || 'ihram';
    const player = makeGlbPerson(playerGltf, { outfit, shadows: Q.shadows });
    const mentor = makeGlbPerson(mentorGltf, { scale: 0.97, outfit, shadows: Q.shadows });
    return { player, mentor };
  }, [playerGltf, mentorGltf, layout.outfit]);

  const ring = useMemo(() => {
    const m = new THREE.Mesh(
      new THREE.RingGeometry(0.75, 0.95, 40),
      new THREE.MeshBasicMaterial({ color: 0xffd68c, transparent: true, opacity: 0.9, side: THREE.DoubleSide }),
    );
    m.rotation.x = -Math.PI / 2;
    return m;
  }, []);

  useEffect(() => () => {
    built.dispose?.();
    heroes.player.dispose?.();
    heroes.mentor.dispose?.();
    ring.geometry?.dispose();
    ring.material?.dispose();
  }, [built, heroes, ring]);

  useEffect(() => {
    document.getElementById('loading')?.remove();
    world.gl = gl;
    const prev = world.chapter;
    world.chapter = chapter;
    scene.background = new THREE.Color(layout.background);
    scene.fog = new THREE.Fog(layout.fog[2], layout.fog[0], layout.fog[1]);
    world.layout = layout;
    world.heroes = heroes;
    const P = world.player;
    P.pos.copy(layout.spawn.pos);
    P.heading = layout.spawn.heading;
    P.speed = 0;
    if (layout.mentorStart) world.mentor.pos.copy(layout.mentorStart);
    else world.mentor.pos.copy(P.pos).add(new THREE.Vector3(1.4, 0, -0.6));
    world.mentor.heading = P.heading;
    heroes.player.group.position.copy(P.pos);
    heroes.player.group.rotation.y = P.heading;
    heroes.mentor.group.position.copy(world.mentor.pos);
    heroes.mentor.group.rotation.y = world.mentor.heading;
    ring.position.set(P.pos.x, 0.04, P.pos.z);

    const cam = layout.cam || {};
    world.cam.yaw = cam.mode === 'fixed' ? cam.yaw : P.heading + Math.PI + (layout.yawBias || 0);
    world.cam.pitch = cam.pitch ?? 0.42;
    world.cam.dist = cam.dist ?? 9;
    world.cam.want = null;
    // arriving from Makkah: start far and high, then glide down to the player (first sight of the Kaaba)
    if (cam.introDist && prev === 'makkah') { world.cam.want = world.cam.dist; world.cam.dist = cam.introDist; }
    // costume for the chapter
    heroes.player.setOutfit(layout.outfit || 'ihram');
    heroes.mentor.setOutfit(layout.outfit || 'ihram');
    world.talbiyah = chapter === 'makkah';
    resetUi();
    useStore.setState({ talbiyah: world.talbiyah, chapterTitle: `الفصل ${'٠١٢٣٤٥٦٧٨٩'[ch.n]} · ${ch.title}` });
    const goTo = id => useStore.setState({ chapter: id });
    const end = () => useStore.setState({ screen: 'end', summary: { ...stats.s } });
    world.rites = ch.rites({ goTo, end, scene: built });
    world.sceneReady = true;

    // Eagerly preload the next chapter's GLBs in the background
    const idx = CHAPTERS.findIndex(c => c.id === chapter);
    const nextCh = idx >= 0 ? CHAPTERS[idx + 1] : null;
    if (nextCh) {
      for (const p of CHAPTER_GLBS[nextCh.id] || []) useGLTF.preload(p);
    }

    const t = setTimeout(() => world.rites.start(), 400);
    return () => {
      clearTimeout(t);
      world.sceneReady = false;
    };
  }, [chapter, built, heroes, ring, gl, scene, layout, ch]);

  useFrame((_, dt) => built.update(Math.min(dt, 0.05) * world.timeScale, world.time, world.player.pos));
  const L = layout.light, A = L.area || 55;
  return (
    <>
      <SceneEnv intensity={TWILIGHT.has(chapter) ? 0.5 : 0.7} />
      <hemisphereLight args={[L.sky, L.ground, L.hemi]} />
      <directionalLight
        position={L.pos}
        intensity={L.si}
        color={L.sun}
        castShadow={Q.shadows}
        shadow-mapSize={[2048, 2048]}
        shadow-bias={-0.0004}
        shadow-normalBias={0.03}
        shadow-camera-left={-A}
        shadow-camera-right={A}
        shadow-camera-top={A}
        shadow-camera-bottom={-A}
        shadow-camera-far={220}
      />
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
    id = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(id);
  }, [invalidate]);
  return null;
}

export function Game() {
  const screen = useStore(s => s.screen), chapter = useStore(s => s.chapter);
  const [sceneLoading, setSceneLoading] = useState(false);

  useEffect(() => {
    if (CINEMATIC) useStore.setState({ screen: 'play' });
  }, []);

  const playing = screen !== 'title';
  return (
    <>
      <Canvas
        id="game"
        dpr={dpr()}
        shadows={Q.shadows}
        frameloop={Q.fps <= 30 ? 'demand' : 'always'}
        gl={{
          antialias: Q.name !== 'lite',
          powerPreference: 'high-performance',
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: 1.05,
        }}
        camera={{ fov: 50, near: 0.1, far: 600, position: [20, 18, 20] }}
      >
        {Q.fps <= 30 && <FpsCap />}
        <Suspense fallback={<SuspenseFlag onPending={setSceneLoading} />}>
          {playing ? <Scene key={chapter} chapter={chapter} /> : <TitleBackdrop />}
        </Suspense>
      </Canvas>
      {sceneLoading && playing && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 90,
            display: 'grid',
            placeItems: 'center',
            pointerEvents: 'none',
          }}
        >
          <div
            style={{
              background: 'rgba(18, 24, 38, 0.82)',
              color: '#f5efe0',
              padding: '10px 22px',
              borderRadius: '999px',
              fontSize: '15px',
              fontWeight: 700,
              border: '1px solid rgba(255, 214, 140, 0.35)',
              backdropFilter: 'blur(6px)',
            }}
          >
            جاري تجهيز المشهد…
          </div>
        </div>
      )}
      <Hud />
    </>
  );
}

// slow orbit round the realistic Mataf & Kaaba behind the title screen
function TitleBackdrop() {
  useGLTFMany(TITLE_GLBS);
  const built = useMemo(() => buildMataf(), []);
  const { scene, camera, gl } = useThree();

  useEffect(() => () => {
    built.dispose?.();
    world.sceneReady = false;
  }, [built]);

  useEffect(() => {
    document.getElementById('loading')?.remove();
    world.gl = gl;
    world.sceneReady = true;
    scene.background = new THREE.Color(matafLayout.background);
    scene.fog = new THREE.Fog(0x2a3655, 70, 170);
    // Warm up Chapter 1 + core character GLBs while user views the title screen
    for (const p of [...CORE_CHAR_GLBS, ...CHAPTER_GLBS.home]) useGLTF.preload(p);
  }, [gl, scene]);

  const t = useRef(0);
  useFrame((_, dt) => {
    t.current += Math.min(dt, 0.05) * 0.05;
    built.update(Math.min(dt, 0.05), t.current * 20, { x: 999, z: 999 });
    camera.position.set(Math.cos(t.current) * 40, 22, Math.sin(t.current) * 40);
    camera.lookAt(0, 4, 0);
  });

  const L = matafLayout.light;
  return (
    <>
      <SceneEnv intensity={0.5} />
      <hemisphereLight args={[L.sky, L.ground, L.hemi]} />
      <directionalLight position={L.pos} intensity={L.si} color={L.sun} />
      <primitive object={built.root} />
    </>
  );
}
