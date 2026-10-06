import { useStore, setAction } from '../store.js';
import { world } from '../refs.js';
import { PLANE } from '../content.js';
import { stats } from './stats.js';

// Proximity actions: the first enabled spot the player stands near shows its action button.
// spots: [{ id, pos: Vector3, r, on: () => bool, action: { label, key, icon } }]
export function hotspots(spots) {
  const ids = new Set(spots.map(s => s.id));
  return {
    update() {
      const P = world.player.pos, cur = useStore.getState().action;
      const near = spots.find(s => s.on() && Math.hypot(P.x - s.pos.x, P.z - s.pos.z) < (s.r || 1.8));
      if (near) { if (cur?.id !== near.id) setAction({ id: near.id, ...near.action }); }
      else if (cur && ids.has(cur.id)) setAction(null);
    },
    // the next spot to walk to (autopilot / minimap)
    next() { return spots.find(s => s.on()) || null; },
  };
}
export const faceTo = v => { const P = world.player.pos; world.player.heading = Math.atan2(v.x - P.x, v.z - P.z); };
export const bubble = (text, s = 2.6) => useStore.setState({ bubble: { text, until: world.time + s } });

// «لبّيك» (button / T): from the niyyah until tawaf begins
export function talbiyah() {
  useStore.setState({ bubble: { text: PLANE.talbiyahShort, until: world.time + 3 } });
  world.gesture = 1; stats.s.talbiyah = (stats.s.talbiyah || 0) + 1;
  world.rites?.onTalbiyah?.();
}
