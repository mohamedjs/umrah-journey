import * as THREE from 'three';

// Mutable per-frame state shared by the controller, rites, minimap and tags.
export const world = {
  player: { pos: new THREE.Vector3(), heading: 0, speed: 0, running: false, moving: false },
  mentor: { pos: new THREE.Vector3(), heading: 0 },
  cam: { yaw: 0, pitch: 0.42, dist: 9, lastDrag: -10 },
  layout: null,          // the active scene layout (mataf.js / masa.js)
  rites: null,           // the active rites engine (tawaf.js / sai.js)
  heroes: { player: null, mentor: null },   // person rigs (people.js)
  gesture: 0,            // seconds left of the right-hand raise animation
  pray: 0,
  time: 0,
  timeScale: Number(new URLSearchParams(location.search).get('speed')) || 1,   // ?speed=4 for testing
};
