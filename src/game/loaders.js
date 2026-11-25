import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { Q } from './quality.js';

// Base-path-safe URL resolver (works on dev server, relative ./, and GitHub Pages subpaths)
export const assetUrl = rel => {
  const clean = rel.replace(/^\.?\//, '');
  const base = (import.meta.env.BASE_URL || './');
  if (base === './' || base === '') return new URL(clean, document.baseURI).href;
  return new URL(clean, new URL(base.endsWith('/') ? base : base + '/', location.origin)).href;
};

// Shared singleton GLTFLoader with local Draco WASM decoder + MeshoptDecoder
let sharedLoader = null;
function getLoader() {
  if (sharedLoader) return sharedLoader;
  const draco = new DRACOLoader();
  draco.setDecoderPath(assetUrl('draco/'));
  draco.preload();
  const loader = new GLTFLoader();
  loader.setDRACOLoader(draco);
  loader.setMeshoptDecoder(MeshoptDecoder);
  sharedLoader = loader;
  return sharedLoader;
}

const cache = new Map();
const normalizeKey = relPath => relPath.replace(/^\.?\//, '');

function ensureEntry(relPath) {
  const key = normalizeKey(relPath);
  let entry = cache.get(key);
  if (entry) return entry;
  entry = { status: 'pending', value: null, error: null, promise: null };
  entry.promise = new Promise((resolve, reject) => {
    getLoader().load(
      assetUrl(key),
      gltf => {
        entry.status = 'resolved';
        entry.value = gltf;
        resolve(gltf);
      },
      undefined,
      err => {
        entry.status = 'rejected';
        entry.error = err;
        reject(err);
      },
    );
  });
  cache.set(key, entry);
  return entry;
}

export function loadGLTF(relPath) {
  return ensureEntry(relPath).promise;
}

export function getCachedGLTF(relPath) {
  const entry = cache.get(normalizeKey(relPath));
  return entry && entry.status === 'resolved' ? entry.value : null;
}

export function useGLTF(relPath) {
  const entry = ensureEntry(relPath);
  if (entry.status === 'resolved') return entry.value;
  if (entry.status === 'rejected') throw entry.error;
  throw entry.promise;
}

export function useGLTFMany(relPaths) {
  const entries = relPaths.map(ensureEntry);
  const pending = [];
  for (const e of entries) {
    if (e.status === 'rejected') throw e.error;
    if (e.status === 'pending') pending.push(e.promise);
  }
  if (pending.length) throw Promise.all(pending);
  return entries.map(e => e.value);
}

useGLTF.preload = relPath => {
  loadGLTF(relPath).catch(() => {});
};

// Material classification for clean shadows & PBR texture filtering
function matIsEmissiveOrGlass(m) {
  if (!m) return false;
  if (m.transparent || (m.opacity !== undefined && m.opacity < 0.99)) return true;
  const em = m.emissive;
  const ei = m.emissiveIntensity ?? 1;
  if (em && ei > 0.25 && (em.r + em.g + em.b) > 0.05) return true;
  return false;
}

function isEmissiveOrGlassMaterial(material) {
  if (!material) return false;
  if (Array.isArray(material)) return material.length > 0 && material.every(matIsEmissiveOrGlass);
  return matIsEmissiveOrGlass(material);
}

const TEX_SLOTS = ['map', 'normalMap', 'roughnessMap', 'metalnessMap', 'emissiveMap', 'aoMap'];

export function setupMaterialTextures(material, anisotropy = Q.name === 'lite' ? 2 : 4) {
  if (!material) return;
  const list = Array.isArray(material) ? material : [material];
  for (const m of list) {
    if (!m) continue;
    for (const slot of TEX_SLOTS) {
      const tex = m[slot];
      if (tex && tex.isTexture && tex.anisotropy < anisotropy) {
        tex.anisotropy = anisotropy;
      }
    }
  }
}

export function applyLOD(root, lodName = Q.lod, shadows = Q.shadows) {
  const aniso = Q.name === 'lite' ? 2 : 4;
  root.traverse(node => {
    const name = node.name || '';
    if (name.endsWith('_LOD0')) {
      node.visible = lodName === 'LOD0';
    } else if (name.endsWith('_LOD1')) {
      node.visible = lodName === 'LOD1';
    }
    if (node.isMesh) {
      const skipShadow = isEmissiveOrGlassMaterial(node.material);
      node.castShadow = Boolean(shadows && !skipShadow);
      node.receiveShadow = Boolean(shadows && !skipShadow);
      setupMaterialTextures(node.material, aniso);
    }
  });
  return root;
}

export function cloneEnvScene(gltf, { lod = Q.lod, shadows = Q.shadows } = {}) {
  const cloned = gltf.scene.clone(true);
  applyLOD(cloned, lod, shadows);
  return cloned;
}

export const CORE_CHAR_GLBS = [
  'models/characters/player.glb',
  'models/characters/mentor.glb',
  'models/characters/crowd.glb',
];

export const CHAPTER_GLBS = {
  home: ['models/env/home.glb'],
  airport: ['models/env/airport.glb', 'models/characters/agent.glb'],
  plane: ['models/env/plane.glb', 'models/characters/attendant.glb'],
  makkah: ['models/env/makkah.glb', 'models/characters/guide.glb'],
  tawaf: ['models/env/kaaba.glb', 'models/env/maqam.glb', 'models/env/haram_mataf.glb'],
  sai: ['models/env/masa.glb'],
};
