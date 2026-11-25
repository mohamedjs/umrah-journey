// Recorded voice lines, same contract as the Quran game:
// public/audio/manifest.json = { "<exact line text>": "audio/<file>.mp3" }.
// play(text, who, onEnd) → onEnd(true) when the recording finishes, onEnd(false) right away when
// the line has no recording (or sound is off / blocked), so dialogue can move on by itself.
// If the browser blocks playback (no user gesture yet), the line plays on the next tap / key.
let manifest = null, current = null, pending = null, seq = 0;
const load = () => (manifest ??= fetch('./audio/manifest.json', { cache: 'no-store' })
  .then(r => (r.ok ? r.json() : (console.warn('[voice] audio/manifest.json not found — lines are text only'), {})))
  .catch(() => ({})));

export const voice = {
  muted: false, speaking: false, who: null,
  async play(text, who, onEnd) {
    this.stop();
    const tok = ++seq, done = ok => { if (tok === seq) onEnd?.(ok); };
    if (this.muted) return done(false);
    const src = (await load())[text];
    if (tok !== seq) return;                       // a newer line started meanwhile
    if (!src) { console.info('[voice] no recording:', text.slice(0, 50)); return done(false); }
    const a = new Audio(src); current = a; this.who = who;
    a.onplaying = () => { if (current === a) this.speaking = true; };
    a.onpause = () => { if (current === a) this.speaking = false; };
    a.onended = () => { if (current === a) { this.speaking = false; done(true); } };
    a.onerror = () => { console.warn('[voice] could not load', src); done(false); };
    a.play().catch(e => { if (e.name === 'NotAllowedError') pending = a; else console.warn('[voice]', e.name, src); done(false); });
  },
  stop() { seq++; if (current) { current.pause(); current = null; } pending = null; this.speaking = false; },
};
const retry = () => { if (pending && pending === current) { const a = pending; pending = null; a.play().catch(() => {}); } };
addEventListener('pointerdown', retry, true);
addEventListener('keydown', retry, true);
