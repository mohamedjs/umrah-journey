import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
const SC = new URLSearchParams(location.search).get('s') || '1';
const R = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
R.setSize(1920, 1080); R.setPixelRatio(1); R.shadowMap.enabled = true; R.shadowMap.type = THREE.PCFSoftShadowMap;
R.toneMapping = THREE.ACESFilmicToneMapping; R.toneMappingExposure = 1.05; R.outputColorSpace = THREE.SRGBColorSpace;
document.body.prepend(R.domElement);
const scene = new THREE.Scene(); const cam = new THREE.PerspectiveCamera(40, 1920 / 1080, .1, 900);
const hud = document.getElementById('hud');
let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const M = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: .75, metalness: 0, ...o });
const add = (geo, mat, x = 0, y = 0, z = 0, p = scene) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.castShadow = m.receiveShadow = true; p.add(m); return m; };
const SKIN = [0xc68a5e, 0xa86b45, 0xdba57c, 0x8a5a3b, 0xe0b48e];

// ---------- faceless stylized person ----------
function person({ ihram = false, shirt = 0x4a6fa5, pants = 0x2f3440, skin = 0xc68a5e, scale = 1, hijab = null, robe = null } = {}) {
  const g = new THREE.Group(); const sk = M(skin, { roughness: .6 });
  const white = M(0xf7f5ef, { roughness: .9 });
  if (robe) { // women: long abaya + hijab
    add(new THREE.CylinderGeometry(.34, .5, 1.25, 20), M(robe), 0, .62, 0, g);
    add(new THREE.CapsuleGeometry(.3, .45, 6, 16), M(robe), 0, 1.38, 0, g);
    add(new THREE.SphereGeometry(.27, 24, 18), M(hijab), 0, 1.9, 0, g);
    const f = add(new THREE.SphereGeometry(.2, 20, 14), sk, 0, 1.88, .1, g); f.scale.set(1, 1.1, .7);
  } else {
    const lg = ihram ? white : M(pants);
    for (const s of [-1, 1]) add(new THREE.CapsuleGeometry(.11, .55, 4, 10), lg, s * .13, .42, 0, g);
    if (ihram) add(new THREE.CylinderGeometry(.33, .38, .72, 20), white, 0, .68, 0, g); // izar
    const tor = add(new THREE.CapsuleGeometry(.3, .42, 6, 16), ihram ? sk : M(shirt), 0, 1.33, 0, g);
    if (ihram) { const r = add(new THREE.CapsuleGeometry(.315, .44, 6, 16), white, 0, 1.33, 0, g); r.scale.set(1, 1, 1); r.rotation.z = .0;
      // rida over left shoulder, right shoulder bare (idtiba)
      const cut = add(new THREE.SphereGeometry(.2, 14, 10), sk, .26, 1.58, 0, g); }
    for (const s of [-1, 1]) { const a = add(new THREE.CapsuleGeometry(.085, .5, 4, 10), ihram && s < 0 ? white : (ihram ? sk : M(shirt)), s * .41, 1.25, 0, g); a.rotation.z = s * .12; }
    add(new THREE.SphereGeometry(.25, 24, 18), sk, 0, 1.92, 0, g);
    if (!ihram) { const h = add(new THREE.SphereGeometry(.262, 24, 18, 0, Math.PI * 2, 0, 1.25), M(0x231a14), 0, 1.94, -.02, g); }
  }
  g.scale.setScalar(scale); return g;
}
// instanced crowd of simple figures
function crowd(points, { robeRatio = .3 } = {}) {
  const n = points.length, body = new THREE.CapsuleGeometry(.3, .9, 4, 10), head = new THREE.SphereGeometry(.24, 12, 10);
  const mb = new THREE.InstancedMesh(body, M(0xffffff, { roughness: .9 }), n), mh = new THREE.InstancedMesh(head, M(0xffffff, { roughness: .7 }), n);
  const o = new THREE.Object3D(), c = new THREE.Color();
  points.forEach(([x, z, ry], i) => {
    const s = .9 + rnd() * .2; o.position.set(x, .9 * s, z); o.rotation.set(0, ry || 0, 0); o.scale.setScalar(s); o.updateMatrix(); mb.setMatrixAt(i, o.matrix);
    const w = rnd() < robeRatio; mb.setColorAt(i, c.set(w ? [0x2b2b33, 0x3d3a45, 0xf2efe6, 0x5a4f63][Math.floor(rnd() * 4)] : 0xf6f3ec));
    o.position.y = 1.85 * s; o.updateMatrix(); mh.setMatrixAt(i, o.matrix); mh.setColorAt(i, c.set(w ? [0x2b2b33, 0xeae6dd, 0x6b5b75][Math.floor(rnd() * 3)] : SKIN[Math.floor(rnd() * SKIN.length)]));
  });
  for (const m of [mb, mh]) { m.castShadow = m.receiveShadow = true; scene.add(m); } return mb;
}
function lights({ sky = 0xbfd8ff, ground = 0xd8c9a8, hemi = 1.1, sun = 0xfff1d6, si = 2.4, pos = [30, 50, 20], area = 60 } = {}) {
  scene.add(new THREE.HemisphereLight(sky, ground, hemi));
  const d = new THREE.DirectionalLight(sun, si); d.position.set(...pos); d.castShadow = true; d.shadow.mapSize.set(4096, 4096);
  Object.assign(d.shadow.camera, { left: -area, right: area, top: area, bottom: -area, near: 1, far: 300 }); d.shadow.bias = -.0004; d.shadow.normalBias = .03; scene.add(d); return d;
}
function tagAt(obj3, text, cls = '', dy = 2.4) { const v = new THREE.Vector3(); obj3.getWorldPosition(v); v.y += dy; v.project(cam); const e = document.createElement('div'); e.className = 'tag ' + cls; e.textContent = text; e.style.left = (v.x * .5 + .5) * 1920 + 'px'; e.style.top = (-v.y * .5 + .5) * 1080 + 'px'; hud.appendChild(e); }
function canvasTex(w, h, draw) { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t; }
const marble = (rep = 8, tint = '#f4f1ea') => { const t = canvasTex(512, 512, (x, w, h) => { x.fillStyle = tint; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(160,150,135,.35)'; x.lineWidth = 3; for (let i = 0; i <= 4; i++) { x.beginPath(); x.moveTo(i * 128, 0); x.lineTo(i * 128, h); x.stroke(); x.beginPath(); x.moveTo(0, i * 128); x.lineTo(w, i * 128); x.stroke(); } for (let i = 0; i < 40; i++) { x.strokeStyle = `rgba(150,140,125,${.05 + Math.random() * .08})`; x.lineWidth = 1 + Math.random() * 2; x.beginPath(); let px = Math.random() * w, py = Math.random() * h; x.moveTo(px, py); for (let k = 0; k < 6; k++) { px += (Math.random() - .5) * 90; py += (Math.random() - .5) * 90; x.lineTo(px, py); } x.stroke(); } }); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rep, rep); return t; };

// ======================= SCENE 1: home, packing =======================
if (SC === '1') {
  scene.background = new THREE.Color(0xf3e2c4); lights({ sky: 0xfff3dd, ground: 0xc9a77a, hemi: 1.2, sun: 0xffe2b0, si: 2.2, pos: [-12, 18, 10], area: 14 });
  const wood = M(0xb98a5a), wall = M(0xf0dcbc), wall2 = M(0xe6cda6);
  add(new THREE.BoxGeometry(16, .2, 14), M(0xc89a68), 0, -.1, 0);
  add(new THREE.BoxGeometry(16, 7, .2), wall, 0, 3.5, -5);
  add(new THREE.BoxGeometry(.2, 7, 14), wall2, -7, 3.5, 0);
  // window with morning light
  const win = add(new THREE.BoxGeometry(3.2, 2.6, .1), M(0xfff6e0, { emissive: 0xffe9b8, emissiveIntensity: 1.2 }), 2.5, 3.6, -4.88);
  for (const x of [-1.6, 0, 1.6]) add(new THREE.BoxGeometry(.12, 2.8, .2), wood, 2.5 + x, 3.6, -4.8); add(new THREE.BoxGeometry(3.4, .12, .2), wood, 2.5, 3.6, -4.8);
  // rug
  const rug = add(new THREE.CylinderGeometry(3.2, 3.2, .04, 48), M(0x9c3d2f), .5, .02, 1); rug.scale.z = .7;
  add(new THREE.CylinderGeometry(2.7, 2.7, .05, 48), M(0xd8a24a), .5, .03, 1).scale.z = .7;
  // bed
  add(new RoundedBoxGeometry(5, .8, 3.4, 4, .15), wood, -3.6, .4, -2.8); add(new RoundedBoxGeometry(4.8, .45, 3.2, 4, .2), M(0xf7f2e8), -3.6, 1, -2.8);
  add(new RoundedBoxGeometry(1.6, .35, .9, 4, .15), M(0xffffff), -5.2, 1.4, -2.8);
  add(new RoundedBoxGeometry(5, 2, .3, 4, .1), wood, -3.6, 1.6, -4.5);
  // open suitcase on bed
  const sc = new THREE.Group(); sc.position.set(-3.2, 1.25, -2.4); sc.rotation.y = .25; scene.add(sc);
  add(new RoundedBoxGeometry(2.2, .5, 1.5, 4, .1), M(0x2f6e8f), 0, .25, 0, sc);
  const lid = add(new RoundedBoxGeometry(2.2, .12, 1.5, 4, .05), M(0x2f6e8f), 0, .55, -.75, sc); lid.geometry.translate(0, 0, -.75); lid.position.set(0, .5, -.75); lid.rotation.x = -1.2;
  add(new RoundedBoxGeometry(1.9, .3, 1.25, 3, .08), M(0xffffff, { roughness: 1 }), -.25, .45, .05, sc); // folded ihram
  add(new RoundedBoxGeometry(.5, .25, .9, 3, .08), M(0xf7f7f0, { roughness: 1 }), .7, .43, 0, sc);
  // floating items to pack
  const items = [[0x7a2531, new THREE.BoxGeometry(.5, .7, .06), -1.2, 3.4, -.6, 'جواز السفر'], [0xf5f3ee, new RoundedBoxGeometry(.9, .45, .7, 3, .1), 2.9, 2.4, -1.6, 'ملابس الإحرام'], [0x6b4a2b, new THREE.BoxGeometry(.9, .18, .4), 3.6, 1.2, 1.6, 'شبشب مريح'], [0xc23d3d, new THREE.CylinderGeometry(.18, .18, .6, 16), -4.6, 3.2, .4, 'عطر (قبل الإحرام بس)']];
  const holders = [];
  for (const [c, geo, x, y, z, lb] of items) { const m = add(geo, M(c), x, y, z); m.rotation.set(rnd(), rnd() * 3, rnd() * .5); const ring = add(new THREE.TorusGeometry(.62, .03, 8, 48), M(0xffd68c, { emissive: 0xffc35a, emissiveIntensity: .8 }), x, y, z); ring.lookAt(cam.position); holders.push([m, lb, ring]); }
  const p = person({ shirt: 0x3f7cac, pants: 0x3a3f4a }); p.position.set(.6, 0, 1.2); p.rotation.y = -2.3; scene.add(p);
  // shelf + plant
  add(new RoundedBoxGeometry(2.4, 2.2, .8, 3, .08), wood, 5.6, 1.1, -4.4); add(new THREE.SphereGeometry(.5, 16, 12), M(0x4f8a4a), 5.2, 2.7, -4.4); add(new THREE.CylinderGeometry(.3, .25, .5, 16), M(0xc9693f), 5.2, 2.4, -4.4);
  cam.position.set(9.5, 8.6, 13); cam.lookAt(-1.2, 1.3, -1.6);
  R.render(scene, cam); for (const h of holders) h[2].lookAt(cam.position);
  tagAt(p, 'أنت', 'me', 2.5); for (const [m, lb] of holders) tagAt(m, lb, '', .75);
  hud.insertAdjacentHTML('beforeend', `<div class="chap">الفصل ١ · البيت</div><div class="obj"><small>المهمة</small><b>جهّز شنطة العمرة</b></div>
   <div class="list"><h4>الشنطة</h4><div><span class="ck on">✓</span>جواز السفر والتأشيرة</div><div><span class="ck on">✓</span>ملابس الإحرام</div><div><span class="ck"></span>شبشب مريح</div><div><span class="ck x">✕</span>عطر في الإحرام؟</div></div>
   <div class="dlg"><span class="who">الحاج حسن</span><p>متنساش ملابس الإحرام يا بني… والعطر حطه قبل ما تحرم، بعد النية مينفعش.</p><span class="nx">▸ التالي</span></div>`);
}
// ======================= SCENE 2: plane, miqat =======================
if (SC === '2') {
  scene.background = new THREE.Color(0x101826); lights({ sky: 0xdfe8ff, ground: 0x7a6a55, hemi: 1.15, sun: 0xffe1b5, si: 1.6, pos: [8, 14, 6], area: 12 });
  const cabin = new THREE.Group(); scene.add(cabin);
  const shell = add(new THREE.CylinderGeometry(4.2, 4.2, 40, 48, 1, true, Math.PI * .55, Math.PI * 1.9), M(0xeef0f2, { side: THREE.BackSide }), 0, 2.2, 0, cabin); shell.rotation.x = Math.PI / 2;
  add(new THREE.BoxGeometry(7.4, .1, 40), M(0x4a5468), 0, 0, 0, cabin);
  add(new THREE.BoxGeometry(1.1, .02, 40), M(0x7c2f3a), 0, .06, 0, cabin);
  // windows (sunset)
  for (let z = -16; z < 18; z += 2.2) for (const s of [-1, 1]) { const w = add(new RoundedBoxGeometry(.05, .75, .55, 3, .2), M(0xffb36b, { emissive: 0xff9a52, emissiveIntensity: 1.6 }), s * 3.85, 2.3, z, cabin); }
  // seats
  const seatM = M(0x26365a), headM = M(0xe9e4da);
  for (let z = -14; z < 8; z += 1.6) for (const x of [-3, -2.2, -1.4, 1.4, 2.2, 3]) {
    const g = new THREE.Group(); g.position.set(x, 0, z); cabin.add(g);
    add(new RoundedBoxGeometry(.72, .25, .7, 3, .08), seatM, 0, .65, 0, g); add(new RoundedBoxGeometry(.72, 1.2, .2, 3, .08), seatM, 0, 1.25, .35, g); add(new RoundedBoxGeometry(.6, .25, .12, 3, .05), headM, 0, 1.75, .3, g);
  }
  // overhead bins + lights
  for (const s of [-1, 1]) add(new RoundedBoxGeometry(1.8, .7, 40, 3, .15), M(0xf3f4f6), s * 2.75, 4, 0, cabin);
  add(new THREE.BoxGeometry(1.2, .04, 40), M(0xffffff, { emissive: 0xfff2d8, emissiveIntensity: .7 }), 0, 4.6, 0, cabin);
  // passengers in ihram seated + player standing in aisle
  const pts = [];
  for (let z = -14; z < 8; z += 1.6) for (const x of [-3, -2.2, -1.4, 1.4, 2.2, 3]) if (rnd() < .75) { const q = person({ ihram: rnd() < .8, skin: SKIN[Math.floor(rnd() * 5)], shirt: 0x8a6d4a, scale: .78 }); q.position.set(x, .25, z - .1); q.rotation.y = Math.PI; cabin.add(q); }
  const p = person({ ihram: true, skin: 0xc68a5e }); p.position.set(.15, 0, 9.4); p.rotation.y = Math.PI * 1.08; scene.add(p);
  add(new THREE.BoxGeometry(8, 6, .2), M(0xe9e2d4), 0, 2.5, -15.5, cabin); add(new THREE.BoxGeometry(2, 3.2, .1), M(0x7c2f3a), 0, 1.6, -15.35, cabin);
  const st = person({ robe: 0x7c2f3a, hijab: 0x7c2f3a, skin: 0xdba57c }); st.position.set(-.1, 0, 2.2); st.rotation.y = 0; scene.add(st);
  // glowing miqat banner
  cam.position.set(1.2, 4.6, 15.8); cam.lookAt(0, 1.2, 3);
  R.render(scene, cam); tagAt(p, 'أنت', 'me', 2.4); tagAt(st, 'المضيفة', '', 2.5);
  hud.insertAdjacentHTML('beforeend', `<div class="chap">الفصل ٢ · الطيارة</div><div class="obj"><small>المهمة</small><b>أحرِم قبل الميقات</b></div>
   <div class="list"><h4>قبل الميقات</h4><div><span class="ck on">✓</span>لبست الإحرام</div><div><span class="ck on">✓</span>اتوضيت</div><div><span class="ck"></span>النية: لبيك اللهم عمرة</div></div>
   <div class="hint">⏱ الطيارة هتحاذي الميقات بعد ٢٠ دقيقة</div>
   <div class="dlg"><span class="who">إعلان الكابتن</span><p>السادة الركاب المتوجهين للعمرة، سنحاذي الميقات بعد عشرين دقيقة… من يرد العمرة فليستعد للإحرام.</p><span class="nx">▸ انوِ العمرة</span></div>`);
}
// ======================= SCENE 3: tawaf =======================
if (SC === '3') {
  scene.background = new THREE.Color(0x1d2b48); scene.fog = new THREE.Fog(0x2a3655, 70, 170);
  lights({ sky: 0x9fb5e8, ground: 0xe8dcc2, hemi: 1.0, sun: 0xffd9a8, si: 2.2, pos: [-40, 60, 30], area: 50 });
  const fl = add(new THREE.CircleGeometry(64, 128), M(0xffffff, { map: marble(14), roughness: .35 }), 0, 0, 0); fl.rotation.x = -Math.PI / 2;
  // Kaaba
  const kiswa = canvasTex(1024, 1024, (x, w, h) => {
    x.fillStyle = '#0d0d0f'; x.fillRect(0, 0, w, h);
    for (let i = 0; i < 400; i++) { x.fillStyle = `rgba(255,255,255,${Math.random() * .03})`; x.fillRect(Math.random() * w, Math.random() * h, 40, 2); }
    const by = h * .2; x.fillStyle = '#b48a3c'; x.fillRect(0, by, w, h * .075);
    x.strokeStyle = '#e7c87a'; x.lineWidth = 3; x.strokeRect(-5, by + 6, w + 10, h * .075 - 12);
    for (let i = 0; i < 24; i++) { x.beginPath(); x.ellipse(i * w / 24 + w / 48, by + h * .0375, 14, 9, 0, 0, 7); x.strokeStyle = '#f6dc98'; x.lineWidth = 3; x.stroke(); }
  });
  const kb = new THREE.Group(); scene.add(kb); kb.rotation.y = .25;
  const km = add(new THREE.BoxGeometry(11, 13, 12), M(0xffffff, { map: kiswa, roughness: .85 }), 0, 6.5, 0, kb);
  add(new THREE.BoxGeometry(11.3, .5, 12.3), M(0xd9d4c8, { roughness: .4 }), 0, .25, 0, kb); // shadharwan base
  add(new THREE.BoxGeometry(1.8, 3.4, .12), M(0xd4a84d, { metalness: .8, roughness: .3 }), 2, 4.2, 6.03, kb); // door
  const bs = add(new THREE.SphereGeometry(.35, 16, 12), M(0xc0c4c8, { metalness: .9, roughness: .25 }), 5.5, 1.5, 6.05, kb); // Black Stone corner (silver frame)
  // Hijr Ismail low semicircle wall
  const hij = add(new THREE.TorusGeometry(7, .45, 8, 48, Math.PI), M(0xe8e3d6, { roughness: .4 }), 0, .6, -6, kb); hij.rotation.set(Math.PI / 2, 0, Math.PI); hij.scale.set(1, 1, 2.2);
  // Maqam Ibrahim
  const mq = new THREE.Group(); mq.position.set(3.4, 0, 12.5); kb.add(mq);
  add(new THREE.CylinderGeometry(.9, 1, .5, 8), M(0xe0dbd0), 0, .25, 0, mq);
  add(new THREE.CylinderGeometry(.7, .7, 1.6, 16, 1, true), M(0xd8b664, { metalness: .9, roughness: .25, transparent: true, opacity: .9 }), 0, 1.3, 0, mq);
  add(new THREE.SphereGeometry(.72, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2), M(0xd8b664, { metalness: .9, roughness: .25 }), 0, 2.1, 0, mq);
  // colonnade ring
  const arcM = M(0xf1ece2, { roughness: .5 });
  for (let i = 0; i < 80; i++) { const a = i / 80 * Math.PI * 2, r = 58; const c = add(new THREE.CylinderGeometry(.6, .6, 9, 12), arcM, Math.cos(a) * r, 4.5, Math.sin(a) * r); }
  const top = add(new THREE.TorusGeometry(58, 1.2, 8, 160), arcM, 0, 9.6, 0); top.rotation.x = Math.PI / 2;
  const top2 = add(new THREE.TorusGeometry(60, 2.4, 6, 160), M(0xe7e0d2), 0, 12.5, 0); top2.rotation.x = Math.PI / 2;
  for (let i = 0; i < 6; i++) { const a = i / 6 * Math.PI * 2 + .3; const mn = add(new THREE.CylinderGeometry(1.1, 1.5, 38, 12), M(0xf3eee4), Math.cos(a) * 66, 19, Math.sin(a) * 66); add(new THREE.ConeGeometry(1.2, 4, 12), M(0xd4b064, { metalness: .7, roughness: .3 }), Math.cos(a) * 66, 40, Math.sin(a) * 66); }
  for (let i = 0; i < 40; i++) { const a = i / 40 * Math.PI * 2; const l = new THREE.PointLight(0xffe2b0, 30, 22, 2); l.position.set(Math.cos(a) * 56, 8.5, Math.sin(a) * 56); scene.add(l); }
  // crowd circling counter-clockwise (Kaaba on the left)
  const pts = [];
  const PA = 1.15, PR = 15.5, px0 = Math.cos(PA) * PR, pz0 = Math.sin(PA) * PR;
  for (let i = 0; i < 2200; i++) { const r = 9.5 + Math.pow(rnd(), 1.4) * 40, a = rnd() * Math.PI * 2; const x = Math.cos(a) * r, z = Math.sin(a) * r; if (Math.hypot(x - px0, z - pz0) < 2.6) continue; const mx = Math.cos(.25) * 3.4 + Math.sin(.25) * 12.5, mz = -Math.sin(.25) * 3.4 + Math.cos(.25) * 12.5; if (Math.hypot(x - mx, z - mz) < 1.8) continue; pts.push([x, z, -a]); }
  crowd(pts, { robeRatio: .35 });
  const pa = PA, pr = PR; const p = person({ ihram: true }); p.position.set(Math.cos(pa) * pr, 0, Math.sin(pa) * pr); p.rotation.y = -pa + Math.PI; scene.add(p);
  const ring = add(new THREE.RingGeometry(.9, 1.15, 40), M(0xffd68c, { emissive: 0xffc04a, emissiveIntensity: 1.5, side: THREE.DoubleSide }), p.position.x, .05, p.position.z); ring.rotation.x = -Math.PI / 2;
  const guide = person({ ihram: true, skin: 0x9a6a48 }); guide.position.set(Math.cos(pa + .07) * (pr + 1.2), 0, Math.sin(pa + .07) * (pr + 1.2)); guide.rotation.y = p.rotation.y; scene.add(guide);
  // path arrows on floor
  for (let k = 1; k < 7; k++) { const a = pa - k * .09; const ar = add(new THREE.ConeGeometry(.35, .9, 3), M(0xffd68c, { emissive: 0xffb43a, emissiveIntensity: 1.2 }), Math.cos(a) * pr, .08, Math.sin(a) * pr); ar.rotation.set(Math.PI / 2, 0, 0); ar.rotation.z = a; ar.lookAt(Math.cos(a - .1) * pr, .08, Math.sin(a - .1) * pr); ar.rotateX(Math.PI / 2); }
  cam.position.set(Math.cos(1.3) * 44, 21, Math.sin(1.3) * 44); cam.lookAt(Math.cos(1.05) * 4, 0, Math.sin(1.05) * 4);
  R.render(scene, cam); tagAt(p, 'أنت', 'me', 2.4); tagAt(guide, 'الحاج حسن', '', 2.4); tagAt(bs, 'ركن الحجر الأسود · البداية', '', 1.2); tagAt(mq, 'مقام إبراهيم', '', 3);
  hud.insertAdjacentHTML('beforeend', `<div class="chap">الفصل ٤ · الطواف</div><div class="obj"><small>المهمة</small><b>طُف سبعة أشواط</b></div>
   <div class="cnt">${[1, 2, 3, 4, 5, 6, 7].map(n => `<i class="${n < 3 ? 'on' : n === 3 ? 'cur' : ''}">${'١٢٣٤٥٦٧'[n - 1]}</i>`).join('')}</div>
   <div class="mm"></div>
   <div class="dlg"><span class="who">الحاج حسن</span><p>خلّي الكعبة على شمالك دايماً… ولما توصل ركن الحجر الأسود، شاور بإيدك اليمين وقول: بسم الله والله أكبر.</p><span class="nx">▸ التالي</span></div>`);
  // minimap
  const mm = document.querySelector('.mm'); mm.innerHTML = `<svg viewBox="-50 -50 100 100" width="204" height="204"><circle r="44" fill="none" stroke="rgba(255,214,140,.4)" stroke-width="2"/><circle r="30" fill="none" stroke="rgba(255,255,255,.25)" stroke-width="10"/><rect x="-7" y="-7" width="14" height="14" fill="#111" stroke="#d4a84d" stroke-width="2" transform="rotate(14)"/><path d="M 0 -30 A 30 30 0 0 0 -30 0" fill="none" stroke="#ffd68c" stroke-width="4" stroke-dasharray="4 4"/><circle cx="${Math.cos(pa) * 30}" cy="${Math.sin(pa) * 30}" r="5" fill="#ffd68c"/></svg>`;
}
// ======================= SCENE 4: sa'i =======================
if (SC === '4') {
  scene.background = new THREE.Color(0xf4efe4); scene.fog = new THREE.Fog(0xf4efe4, 40, 120);
  lights({ sky: 0xfffaf0, ground: 0xd9cdb5, hemi: 1.4, sun: 0xfff2dc, si: 1.4, pos: [10, 30, 15], area: 40 });
  const L = 140, Wd = 20;
  const fl = add(new THREE.PlaneGeometry(Wd, L), M(0xffffff, { map: marble(6), roughness: .3 }), 0, 0, -L / 2 + 10); fl.rotation.x = -Math.PI / 2; fl.material.map.repeat.set(3, 20);
  add(new THREE.BoxGeometry(1.2, 1, L), M(0xd9d1c0), 0, .5, -L / 2 + 10); // central divider
  add(new THREE.BoxGeometry(Wd + 2, .6, L), M(0xf2ede3), 0, 12, -L / 2 + 10);
  const colM = M(0xf6f2ea, { roughness: .45 }), capM = M(0xd8b664, { metalness: .6, roughness: .35 });
  for (let z = 8; z > -L + 10; z -= 9) for (const x of [-Wd / 2 + .8, Wd / 2 - .8]) { add(new THREE.CylinderGeometry(.7, .7, 12, 16), colM, x, 6, z); add(new THREE.CylinderGeometry(.95, .7, .7, 16), capM, x, 11.6, z); }
  for (let z = 8; z > -L + 10; z -= 9) { const a = add(new THREE.TorusGeometry(Wd / 2 - .8, .35, 8, 32, Math.PI), M(0xefe8da), 0, 6.6, z); }
  // chandeliers
  for (let z = 5; z > -L + 10; z -= 12) for (const x of [-5, 5]) { add(new THREE.CylinderGeometry(.5, .3, .5, 12), M(0xd8b664, { metalness: .7, roughness: .3, emissive: 0xffd27a, emissiveIntensity: .8 }), x, 10.6, z); }
  // green lights zone
  const gz = -32; for (const dz of [0, -22]) { add(new THREE.BoxGeometry(Wd - 2, .25, 1.2), M(0x1fbf6a, { emissive: 0x18e070, emissiveIntensity: 2.4 }), 0, 11.6, gz + dz); for (const x of [-Wd / 2 + .8, Wd / 2 - .8]) add(new THREE.CylinderGeometry(.75, .75, 3, 16), M(0x1fbf6a, { emissive: 0x18e070, emissiveIntensity: 1.6 }), x, 9, gz + dz); }
  const gl = new THREE.PointLight(0x2bff8a, 120, 40, 2); gl.position.set(0, 9, gz - 11); scene.add(gl);
  // Marwa hill at the end (rock)
  const rock = add(new THREE.DodecahedronGeometry(6, 1), M(0x9a8a74, { roughness: 1 }), 0, 0, -L + 8); rock.scale.set(1.4, .7, 1);
  // crowd both directions
  const pts = []; for (let i = 0; i < 520; i++) { const left = rnd() < .5; const x = left ? -1.2 - rnd() * 7.8 : 1.2 + rnd() * 7.8; const z = 6 - rnd() * (L - 14); if (Math.hypot(x + 4.2, z + 14) < 2.4 || (z > -10 && z < 8 && Math.abs(x + 4) < 3)) continue; pts.push([x, z, left ? Math.PI : 0]); }
  crowd(pts, { robeRatio: .4 });
  const p = person({ ihram: true }); p.position.set(-4.2, 0, -14); p.rotation.y = Math.PI; scene.add(p);
  const ring = add(new THREE.RingGeometry(.9, 1.15, 40), M(0xffd68c, { emissive: 0xffc04a, emissiveIntensity: 1.5, side: THREE.DoubleSide }), -4.2, .05, -14); ring.rotation.x = -Math.PI / 2;
  cam.position.set(-2.8, 8.5, -2); cam.lookAt(-3.8, 0.2, -30);
  R.render(scene, cam); tagAt(p, 'أنت', 'me', 2.4); tagAt(rock, 'المروة', '', 4.5);
  const gm = new THREE.Object3D(); gm.position.set(0, 9.5, gz); scene.add(gm); tagAt(gm, 'العلم الأخضر · هرولة للرجال', '', 1.3);
  hud.insertAdjacentHTML('beforeend', `<div class="chap">الفصل ٥ · السعي</div><div class="obj"><small>المهمة</small><b>من الصفا إلى المروة</b></div>
   <div class="cnt">${[1, 2, 3, 4, 5, 6, 7].map(n => `<i class="${n < 5 ? 'on' : n === 5 ? 'cur' : ''}">${'١٢٣٤٥٦٧'[n - 1]}</i>`).join('')}</div>
   <div class="dlg"><span class="who">الحاج حسن</span><p>ده الشوط الخامس، من الصفا للمروة. بين النورين الأخضر امشي أسرع شوية… وادعي باللي في قلبك.</p><span class="nx">▸ التالي</span></div>`);
}
R.render(scene, cam);
await document.fonts.ready; window.ready = true;
