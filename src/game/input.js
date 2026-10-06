// Keyboard, mouse and touch input (same feel as the Quran game):
//  · WASD / arrows walk, Shift runs (raml / jogging), F toggles the autopilot (👣)
//  · drag anywhere orbits the camera, wheel / pinch / + − zoom
//  · touch: a fixed joystick bottom-left; only a touch that starts on it walks
export const input = { x: 0, y: 0, run: false, dragX: 0, dragY: 0, zoom: 0, stick: null, lastManual: -1 };
const keys = new Set();
const handlers = { key: () => {} };
export const onKey = f => { handlers.key = f; };

export const isTouch = () => matchMedia('(pointer: coarse)').matches || navigator.maxTouchPoints > 0;
const STICK_R = 50;

function updateKeys() {
  const k = c => keys.has(c);
  const x = (k('KeyD') || k('ArrowRight') ? 1 : 0) - (k('KeyA') || k('ArrowLeft') ? 1 : 0);
  const y = (k('KeyW') || k('ArrowUp') ? 1 : 0) - (k('KeyS') || k('ArrowDown') ? 1 : 0);
  if (!input.stick) { input.x = x; input.y = y; }
  input.run = k('ShiftLeft') || k('ShiftRight');
}

export function initInput(canvasEl) {
  addEventListener('keydown', e => {
    if (e.repeat) return;
    if (e.target?.tagName === 'INPUT') return;
    keys.add(e.code); updateKeys();
    if (e.code === 'Equal' || e.code === 'NumpadAdd') input.zoom -= 2;
    if (e.code === 'Minus' || e.code === 'NumpadSubtract') input.zoom += 2;
    handlers.key(e.code, e);
  });
  addEventListener('keyup', e => { keys.delete(e.code); updateKeys(); });
  addEventListener('blur', () => { keys.clear(); updateKeys(); });

  // joystick (touch devices)
  let stickEl = null, knob = null;
  if (isTouch()) {
    stickEl = document.createElement('div'); stickEl.id = 'stick';
    stickEl.innerHTML = '<i class="base"></i><i class="knob"></i>';
    document.body.append(stickEl); knob = stickEl.querySelector('.knob');
  }
  const onStick = (x, y) => { if (!stickEl || stickEl.hidden) return false; const r = stickEl.getBoundingClientRect(); return Math.hypot(x - (r.left + r.width / 2), y - (r.top + r.height / 2)) < r.width / 2 + 18; };
  const pointers = new Map(); let pinch = 0;
  canvasEl.addEventListener('pointerdown', e => {
    canvasEl.setPointerCapture?.(e.pointerId);
    if (e.pointerType === 'touch' && onStick(e.clientX, e.clientY)) {
      const r = stickEl.getBoundingClientRect();
      input.stick = { id: e.pointerId, cx: r.left + r.width / 2, cy: r.top + r.height / 2 };
      stickEl.classList.add('on'); moveStick(e); return;
    }
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.size === 2) { const [a, b] = [...pointers.values()]; pinch = Math.hypot(a.x - b.x, a.y - b.y); }
  });
  const moveStick = e => {
    let dx = e.clientX - input.stick.cx, dy = e.clientY - input.stick.cy; const d = Math.hypot(dx, dy);
    if (d > STICK_R) { dx *= STICK_R / d; dy *= STICK_R / d; }
    knob.style.transform = `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px))`;
    const m = Math.min(1, d / STICK_R); const dead = m < 0.12 ? 0 : m;
    input.x = d ? dx / STICK_R * (dead / m || 0) : 0; input.y = d ? -dy / STICK_R * (dead / m || 0) : 0;
    input.run = m > 0.92;
  };
  canvasEl.addEventListener('pointermove', e => {
    if (input.stick?.id === e.pointerId) return moveStick(e);
    const p = pointers.get(e.pointerId); if (!p) return;
    if (pointers.size === 2) {
      p.x = e.clientX; p.y = e.clientY;
      const [a, b] = [...pointers.values()], d = Math.hypot(a.x - b.x, a.y - b.y);
      input.zoom += (pinch - d) * 0.04; pinch = d; return;
    }
    input.dragX += e.clientX - p.x; input.dragY += e.clientY - p.y; p.x = e.clientX; p.y = e.clientY;
  });
  const up = e => {
    if (input.stick?.id === e.pointerId) { input.stick = null; input.x = input.y = 0; input.run = false; stickEl.classList.remove('on'); knob.style.transform = 'translate(-50%,-50%)'; updateKeys(); return; }
    pointers.delete(e.pointerId);
  };
  canvasEl.addEventListener('pointerup', up); canvasEl.addEventListener('pointercancel', up);
  canvasEl.addEventListener('wheel', e => { e.preventDefault(); input.zoom += Math.sign(e.deltaY) * Math.min(3, Math.abs(e.deltaY) / 40); }, { passive: false });
  canvasEl.addEventListener('contextmenu', e => e.preventDefault());
}
export const showStick = on => { const s = document.getElementById('stick'); if (s) s.hidden = !on; };
