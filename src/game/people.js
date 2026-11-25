import * as THREE from 'three';
import { createCharacterRig } from './characterRig.js';
import { getCachedGLTF, setupMaterialTextures } from './loaders.js';
import { Q } from './quality.js';

export const SKIN = [0xc68a5e, 0xa86b45, 0xdba57c, 0x8a5a3b, 0xe0b48e];
const IHRAM = [0xfaf8f2, 0xf4f1ea, 0xf7f4ec, 0xfbf9f4];
const STREET = [0x4a6fa5, 0x7a5b3a, 0x3d6b4f, 0x8a3d3d, 0x5a5f6b, 0xc9b48a, 0x2f4a6b, 0xd4cbb8];
const ABAYA = [0x26262e, 0x222c3c, 0x3b2a3e, 0x5d5044, 0x343a31, 0x2d3038];
const HIJAB = [0x26262e, 0xf0ece2, 0x5d4c63, 0x7c6a57, 0x3a4a5e, 0x545d4c];

export function seeded(seed = 11) {
  return () => (seed = (seed * 16807) % 2147483647) / 2147483647;
}

export function makeGlbPerson(gltf, opts = {}) {
  return createCharacterRig(gltf, opts);
}

// Archetype definitions matching exact mesh names in `public/models/characters/crowd.glb`
const ARCHETYPE_PARTS = {
  ihram_idtiba: [
    { role: 'cloth', mesh: 'crowd_ihram_idtiba_cloth' },
    { role: 'skin', mesh: 'crowd_ihram_idtiba_skin' },
  ],
  ihram_covered: [
    { role: 'cloth', mesh: 'crowd_ihram_covered_cloth' },
    { role: 'skin', mesh: 'crowd_ihram_covered_skin' },
  ],
  man_street: [
    { role: 'cloth', mesh: 'crowd_man_street_cloth' },
    { role: 'skin', mesh: 'crowd_man_street_skin' },
  ],
  woman_abaya: [
    { role: 'cloth', mesh: 'crowd_woman_abaya_cloth' },
    { role: 'hijab', mesh: 'crowd_woman_abaya_hijab' },
    { role: 'skin', mesh: 'crowd_woman_abaya_skin' },
  ],
  seated_man: [
    { role: 'cloth', mesh: 'crowd_seated_man_cloth' },
    { role: 'skin', mesh: 'crowd_seated_man_skin' },
  ],
  seated_woman: [
    { role: 'cloth', mesh: 'crowd_seated_woman_cloth' },
    { role: 'hijab', mesh: 'crowd_seated_woman_hijab' },
    { role: 'skin', mesh: 'crowd_seated_woman_skin' },
  ],
};

function indexCrowdMeshes(gltf) {
  const byName = new Map();
  gltf.scene.traverse(node => {
    if (!node.isMesh) return;
    const base = (node.name || '').replace(/\.\d+$/, '');
    if (base && !byName.has(base)) byName.set(base, node);
  });
  return byName;
}

function pickFrom(arr, rnd) {
  return arr[(rnd() * arr.length) | 0];
}

// Realistic GLB-backed instanced crowd (<= 9-11 draw calls total regardless of crowd size).
// Supports standing pilgrims/travellers and seated airline passengers (`opts.seated = true`).
export function makeCrowd(
  n,
  rnd,
  { robeRatio = 0.33, bareRatio = 0.8, streetRatio = 0, seated = false, shadows = false, crowdGltf = null } = {},
) {
  const gltf = crowdGltf || getCachedGLTF('models/characters/crowd.glb');
  if (!gltf) {
    throw new Error('crowd.glb must be loaded before calling makeCrowd()');
  }

  const meshIndex = indexCrowdMeshes(gltf);
  const buckets = new Map();
  const info = new Array(n);

  for (let i = 0; i < n; i++) {
    const woman = rnd() < robeRatio;
    const s = seated ? (0.95 + rnd() * 0.08) : (0.88 + rnd() * 0.22);
    const skin = pickFrom(SKIN, rnd);
    const street = !woman && rnd() < streetRatio;
    const bare = !seated && !woman && !street && rnd() < bareRatio;

    let arch;
    let clothColor;
    let hijabColor = null;

    if (seated) {
      if (woman) {
        arch = 'seated_woman';
        clothColor = pickFrom(ABAYA, rnd);
        hijabColor = pickFrom(HIJAB, rnd);
      } else {
        arch = 'seated_man';
        clothColor = street ? pickFrom(STREET, rnd) : pickFrom(IHRAM, rnd);
      }
    } else if (woman) {
      arch = 'woman_abaya';
      clothColor = pickFrom(ABAYA, rnd);
      hijabColor = pickFrom(HIJAB, rnd);
    } else if (street) {
      arch = 'man_street';
      clothColor = pickFrom(STREET, rnd);
    } else if (bare) {
      arch = 'ihram_idtiba';
      clothColor = pickFrom(IHRAM, rnd);
    } else {
      arch = 'ihram_covered';
      clothColor = pickFrom(IHRAM, rnd);
    }

    let list = buckets.get(arch);
    if (!list) {
      list = [];
      buckets.set(arch, list);
    }
    const slot = list.length;
    const rec = {
      woman,
      man: !woman,
      s,
      bare,
      phase: rnd() * 6.2831853,
      arch,
      slot,
      colors: { cloth: clothColor, hijab: hijabColor, skin },
    };
    list.push(rec);
    info[i] = rec;
  }

  const group = new THREE.Group();
  const archMeshes = new Map();
  const allMeshes = [];
  const clonedMaterials = [];
  const c = new THREE.Color();
  const aniso = Q.name === 'lite' ? 2 : 4;

  for (const [arch, list] of buckets.entries()) {
    const defs = ARCHETYPE_PARTS[arch];
    const parts = [];
    for (const def of defs) {
      const src = meshIndex.get(def.mesh);
      if (!src) continue;
      const mat = Array.isArray(src.material) ? src.material[0].clone() : src.material.clone();
      // Reset base color to pure white so per-instance color multiplies accurately without darkening
      mat.color.setHex(0xffffff);
      mat.vertexColors = false;
      setupMaterialTextures(mat, aniso);
      clonedMaterials.push(mat);

      const im = new THREE.InstancedMesh(src.geometry, mat, list.length);
      im.castShadow = false;
      im.receiveShadow = Boolean(shadows);
      im.frustumCulled = false;
      im.instanceMatrix.setUsage(seated ? THREE.StaticDrawUsage : THREE.DynamicDrawUsage);

      for (let slot = 0; slot < list.length; slot++) {
        const hex = list[slot].colors[def.role] ?? 0xffffff;
        im.setColorAt(slot, c.setHex(hex));
      }
      if (im.instanceColor) im.instanceColor.needsUpdate = true;

      group.add(im);
      parts.push(im);
      allMeshes.push(im);
    }
    archMeshes.set(arch, parts);
  }

  const dummy = new THREE.Object3D();

  function place(i, x, z, heading, t, y = 0, bobOn = true) {
    const f = info[i];
    if (!f) return;
    const parts = archMeshes.get(f.arch);
    if (!parts || !parts.length) return;

    const s = f.s;
    if (bobOn && !seated) {
      const cyc = t * 7.5 + f.phase;
      const bob = Math.abs(Math.sin(cyc)) * 0.035;
      const sway = Math.sin(cyc) * 0.022;
      dummy.position.set(x, y + bob, z);
      dummy.rotation.set(0.025, heading, sway);
    } else {
      dummy.position.set(x, y, z);
      dummy.rotation.set(0, heading, 0);
    }
    dummy.scale.setScalar(s);
    dummy.updateMatrix();
    for (let k = 0; k < parts.length; k++) {
      parts[k].setMatrixAt(f.slot, dummy.matrix);
    }
  }

  function commit() {
    for (let k = 0; k < allMeshes.length; k++) {
      allMeshes[k].instanceMatrix.needsUpdate = true;
    }
  }

  function dispose() {
    for (const m of allMeshes) m.dispose();
    for (const mat of clonedMaterials) mat.dispose();
  }

  return { group, info, n, place, commit, dispose };
}
