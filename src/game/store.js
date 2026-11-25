import { create } from 'zustand';
import { WHO } from './content.js';
import { voice } from './voice.js';

// UI state only (React HUD reads it). Per-frame state (positions, angles) lives in `world`
// (refs.js) so moving never re-renders React.
const params = new URLSearchParams(location.search);
export const CINEMATIC = params.has('cine');

export const useStore = create(() => ({
  screen: 'title',          // title | play | end
  chapter: 'home',          // see chapters.js
  objective: '',
  objectiveSub: '',
  counter: null,            // { total: 7, done: 2, current: 3 } or null
  dialog: null,             // { who, text, blocking }
  card: null,               // { title, fusha, note }  — du'a / dhikr panel (non-blocking)
  overlay: null,            // { title, verse, ref, hadith, body, button } — modal
  action: null,             // { id, label, key }
  auto: CINEMATIC,          // autopilot (👣 / F)
  runHold: false,           // touch 🏃 toggle
  qaOpen: false,
  summary: null,
  toast: '',
  checklist: null,         // { title, items: [{ label, state: 'on' | 'x' | '' }] }
  hint: '',                // green pill (e.g. the miqat countdown)
  talbiyah: false,         // «لبّيك» button (after the niyyah, until tawaf starts)
  bubble: null,
}));
const set = useStore.setState, get = useStore.getState;

// ---------- dialogue queue ----------------------------------------------------------------
let queue = [], onDone = null, autoTimer = 0, tipTimer = 0;
export function say(lines, then) {
  queue = (Array.isArray(lines) ? lines : [lines]).filter(Boolean).slice();
  onDone = then || null;
  showNext();
}
// Dialogue moves on by itself: when the recording ends (+ a short pause), or after a reading
// time when the line has no recording. A click / Enter skips ahead at any time.
const readMs = t => 1500 + t.length * 60;
function showNext() {
  clearTimeout(autoTimer);
  const l = queue.shift();
  if (!l) { set({ dialog: null }); voice.stop(); const f = onDone; onDone = null; f?.(); return; }
  set({ dialog: { who: WHO[l.who] || l.who, text: l.text, blocking: true } });
  const shown = get().dialog;
  voice.play(l.text, l.who, voiced => {
    if (get().dialog !== shown) return;
    clearTimeout(autoTimer);
    autoTimer = setTimeout(next, voiced ? 700 : readMs(l.text));
  });
}
export function next() { if (get().dialog?.blocking) showNext(); }
export const isBlocking = () => !!get().dialog?.blocking || !!get().overlay || get().screen !== 'play';

// non-blocking line from the mentor (walk on while he talks); never interrupts a blocking dialog
export function tip(l, ms = 0) {
  if (!l || get().dialog?.blocking) return;
  clearTimeout(tipTimer);
  set({ dialog: { who: WHO[l.who] || l.who, text: l.text, blocking: false } });
  const shown = get().dialog;
  const hide = () => { if (get().dialog === shown) set({ dialog: null }); };
  // stays up while the recording plays, then a moment longer
  voice.play(l.text, l.who, voiced => { clearTimeout(tipTimer); tipTimer = setTimeout(hide, voiced ? 1200 : (ms || 2600 + l.text.length * 55)); });
}
export function toast(text, ms = 2200) {
  set({ toast: text }); clearTimeout(toast.t); toast.t = setTimeout(() => set({ toast: '' }), ms);
}
export const setAction = action => set({ action });
export const setCard = card => { if (get().card?.fusha !== card?.fusha) set({ card }); };
export const setObjective = (objective, objectiveSub = '') => set({ objective, objectiveSub });
export const setCounter = counter => set({ counter });
export function showOverlay(o) {
  if (CINEMATIC) setTimeout(() => closeOverlay(o.right ?? 0), 3500 + (o.body?.length || 0) * 40);
  return new Promise(res => set({ overlay: { ...o, resolve: res } }));
}
export function closeOverlay(v) { const o = get().overlay; set({ overlay: null }); o?.resolve?.(v); }
// a question with options → resolves to the chosen index
export function ask(o) { return showOverlay({ ...o }); }
export const setChecklist = checklist => set({ checklist });
export function resetUi() { queue = []; onDone = null; set({ dialog: null, card: null, overlay: null, action: null, counter: null, checklist: null, hint: '', bubble: null, objective: '', objectiveSub: '', qaOpen: false }); }
