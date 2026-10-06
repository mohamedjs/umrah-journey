// Recorded voice lines, same contract as the Quran game:
// public/audio/manifest.json = { "<exact line text>": "audio/<file>.mp3" }.
// No manifest / no file → the line is just shown as text.
let manifest = null, current = null;
const load = () => (manifest ??= fetch('./audio/manifest.json').then(r => (r.ok ? r.json() : {})).catch(() => ({})));

export const voice = {
  muted: false,
  async play(text) {
    this.stop();
    if (this.muted) return;
    const src = (await load())[text];
    if (!src) return;
    const a = new Audio(src); current = a;
    a.play().catch(() => {});
  },
  stop() { if (current) { current.pause(); current = null; } },
};
