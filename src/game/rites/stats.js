// What the player did, for the end-of-chapter summary (kept positive: sunnahs are "bonus").
export const stats = {
  s: {},
  reset(ch) {
    if (ch === 'home') Object.assign(this.s, { packed: false, perfumeRight: false });
    if (ch === 'plane') Object.assign(this.s, { readyBefore: false, talbiyah: 0 });
    if (ch === 'tawaf') Object.assign(this.s, { circuits: 0, gestures: 0, raml: [], idtiba: false, started: false });
    if (ch === 'sai') Object.assign(this.s, { laps: 0, greenRun: [], hills: 0 });
  },
};
