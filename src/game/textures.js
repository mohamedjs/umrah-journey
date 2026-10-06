import * as THREE from 'three';

export function canvasTex(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t;
}

// white marble tiles with faint grey veins
export function marble(rep = 8, tint = '#f4f1ea') {
  let s = 7; const r = () => (s = (s * 16807) % 2147483647) / 2147483647;
  const t = canvasTex(512, 512, (x, w, h) => {
    x.fillStyle = tint; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(160,150,135,.32)'; x.lineWidth = 3;
    for (let i = 0; i <= 4; i++) { x.beginPath(); x.moveTo(i * 128, 0); x.lineTo(i * 128, h); x.stroke(); x.beginPath(); x.moveTo(0, i * 128); x.lineTo(w, i * 128); x.stroke(); }
    for (let i = 0; i < 40; i++) {
      x.strokeStyle = `rgba(150,140,125,${0.05 + r() * 0.08})`; x.lineWidth = 1 + r() * 2; x.beginPath();
      let px = r() * w, py = r() * h; x.moveTo(px, py);
      for (let k = 0; k < 6; k++) { px += (r() - 0.5) * 90; py += (r() - 0.5) * 90; x.lineTo(px, py); }
      x.stroke();
    }
  });
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rep, rep); return t;
}

// black kiswa with the gold band (hizam) about a third from the top
export function kiswa() {
  return canvasTex(1024, 1024, (x, w, h) => {
    x.fillStyle = '#0d0d0f'; x.fillRect(0, 0, w, h);
    for (let i = 0; i < 500; i++) { x.fillStyle = `rgba(255,255,255,${Math.random() * 0.03})`; x.fillRect(Math.random() * w, Math.random() * h, 40, 2); }
    const by = h * 0.24; x.fillStyle = '#b48a3c'; x.fillRect(0, by, w, h * 0.075);
    x.strokeStyle = '#e7c87a'; x.lineWidth = 3; x.strokeRect(-5, by + 6, w + 10, h * 0.075 - 12);
    for (let i = 0; i < 24; i++) { x.beginPath(); x.ellipse(i * w / 24 + w / 48, by + h * 0.0375, 14, 9, 0, 0, 7); x.strokeStyle = '#f6dc98'; x.lineWidth = 3; x.stroke(); }
  });
}
