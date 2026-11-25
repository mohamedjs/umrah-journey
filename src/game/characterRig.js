import * as THREE from 'three';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';
import { Q } from './quality.js';
import { setupMaterialTextures } from './loaders.js';

const stripSuffix = name => (name || '').replace(/\.\d+$/, '');
const stripClipPrefix = name => (name || '').replace(/^.*\|/, '').replace(/\.\d+$/, '').toLowerCase();

// Builds a rigged character instance from a loaded character GLTF
// (`player`, `mentor`, `attendant`, `guide`, `agent`) using SkeletonUtils.clone
// + THREE.AnimationMixer.
export function createCharacterRig(gltf, { scale = 1, outfit = 'ihram', shadows = Q.shadows } = {}) {
  const group = new THREE.Group();
  const cloned = SkeletonUtils.clone(gltf.scene);
  group.add(cloned);
  if (scale !== 1) group.scale.setScalar(scale);

  const aniso = Q.name === 'lite' ? 2 : 4;
  const nodesByName = new Map();
  const registerNode = (key, node) => {
    if (!key) return;
    let list = nodesByName.get(key);
    if (!list) {
      list = [];
      nodesByName.set(key, list);
    }
    list.push(node);
  };

  cloned.traverse(node => {
    const base = stripSuffix(node.name);
    if (base) registerNode(base, node);
    if (node.isMesh || node.isSkinnedMesh) {
      node.castShadow = Boolean(shadows);
      node.receiveShadow = Boolean(shadows);
      if (node.isSkinnedMesh) node.frustumCulled = false;
      setupMaterialTextures(node.material, aniso);
    }
  });

  const setNodeVis = (key, visible) => {
    const list = nodesByName.get(key);
    if (!list) return;
    for (const n of list) n.visible = visible;
  };

  const hasHeroOutfits =
    nodesByName.has('outfit_street') ||
    nodesByName.has('outfit_ihram_izar') ||
    nodesByName.has('outfit_ihram_rida_covered') ||
    nodesByName.has('outfit_ihram_rida_idtiba');

  const head = cloned.getObjectByName('head') || cloned;

  const mixer = new THREE.AnimationMixer(cloned);
  const actions = {};
  for (const clip of gltf.animations || []) {
    const key = stripClipPrefix(clip.name);
    if (!key || actions[key]) continue;
    const action = mixer.clipAction(clip);
    if (key === 'gesture') {
      action.setLoop(THREE.LoopOnce, 1);
      action.clampWhenFinished = true;
    } else {
      action.setLoop(THREE.LoopRepeat, Infinity);
    }
    actions[key] = action;
  }

  let activeName = null;
  if (actions.idle) {
    actions.idle.reset().setEffectiveWeight(1).play();
    activeName = 'idle';
  } else {
    const firstKey = Object.keys(actions)[0];
    if (firstKey) {
      actions[firstKey].reset().setEffectiveWeight(1).play();
      activeName = firstKey;
    }
  }

  let curOutfit = outfit;
  let curIdtiba = false;
  let prevRaise = 0;

  function applyOutfitVisibility() {
    if (!hasHeroOutfits) return;
    setNodeVis('body_skin', true);
    setNodeVis('hair', true);
    const isIhram = curOutfit === 'ihram';
    setNodeVis('outfit_street', !isIhram);
    setNodeVis('outfit_ihram_izar', isIhram);
    setNodeVis('outfit_ihram_rida_covered', isIhram && !curIdtiba);
    setNodeVis('outfit_ihram_rida_idtiba', isIhram && curIdtiba);
  }

  function setIdtiba(on) {
    curIdtiba = Boolean(on && curOutfit === 'ihram');
    applyOutfitVisibility();
  }

  function setOutfit(nextOutfit) {
    curOutfit = nextOutfit || 'ihram';
    if (curOutfit !== 'ihram') curIdtiba = false;
    applyOutfitVisibility();
  }

  if (hasHeroOutfits) applyOutfitVisibility();

  function switchTo(target, fadeDuration = 0.2, forceReset = false) {
    const nextAction = actions[target];
    if (!nextAction) return;
    if (activeName === target) {
      if (forceReset) nextAction.reset().play();
      return;
    }
    const prevAction = activeName ? actions[activeName] : null;
    nextAction.enabled = true;
    nextAction.reset();
    nextAction.setEffectiveTimeScale(1);
    nextAction.setEffectiveWeight(1);
    nextAction.play();
    if (prevAction && prevAction !== nextAction) {
      prevAction.crossFadeTo(nextAction, fadeDuration, false);
    }
    activeName = target;
  }

  function animate(dt, speed = 0, { running = false, raise = 0, pray = 0, talk = false } = {}) {
    let target = 'idle';
    let fade = 0.2;
    let forceReset = false;

    if (pray > 0 && actions.pray) {
      target = 'pray';
      fade = 0.24;
    } else if (raise > 0 && actions.gesture) {
      target = 'gesture';
      fade = 0.14;
      if (prevRaise <= 0) forceReset = true;
    } else if (speed > 0.35) {
      if ((running || speed > 4.2) && actions.run) {
        target = 'run';
        fade = 0.18;
      } else if (actions.walk) {
        target = 'walk';
        fade = 0.18;
      }
    } else if (talk && actions.talk) {
      target = 'talk';
      fade = 0.22;
    } else if (actions.idle) {
      target = 'idle';
      fade = 0.22;
    }

    prevRaise = raise;
    if (actions[target]) {
      switchTo(target, fade, forceReset);
      if (target === 'walk') {
        actions.walk.timeScale = Math.max(0.65, speed / 1.45);
      } else if (target === 'run') {
        actions.run.timeScale = Math.max(0.8, speed / 2.6);
      } else {
        actions[target].timeScale = 1;
      }
    }

    mixer.update(Math.min(dt, 0.1));
  }

  function dispose() {
    mixer.stopAllAction();
    mixer.uncacheRoot(cloned);
  }

  return {
    group,
    head,
    setOutfit,
    setIdtiba,
    animate,
    dispose,
    get idtiba() { return curIdtiba; },
    get outfit() { return curOutfit; },
    get clip() { return activeName; },
  };
}
