import { MAKKAH } from '../content.js';
import { say, tip, setObjective, setChecklist, setAction, showOverlay } from '../store.js';
import { world } from '../refs.js';
import { MAKKAH_SPOTS } from '../scenes/makkah.js';
import { hotspots, faceTo } from './kit.js';
import { stats } from './stats.js';

// Chapter 4 — arrive at the hotel, take the key from the guide, walk to al-Masjid al-Haram
// (talbiyah on the way), enter with the right foot and the du'a, then the first sight of the Kaaba.
export function createMakkah({ goTo }) {
  let phase = 'intro', toldGate = false;
  const list = () => setChecklist({ title: 'في مكة', items: [
    { label: 'استلمت مفتاح الأوضة', state: phase === 'intro' || phase === 'guide' ? '' : 'on' },
    { label: 'التلبية في الطريق', state: (stats.s.talbiyahMakkah || 0) > 0 ? 'on' : '' },
    { label: 'دخلت المسجد برجلك اليمين', state: phase === 'in' ? 'on' : '' },
  ] });
  const spots = hotspots([
    { id: 'guide', pos: MAKKAH_SPOTS.guide, r: 2, on: () => phase === 'guide', action: { label: 'استلم مفتاح الأوضة', key: 'E', icon: 'ri-key-2-line' } },
    { id: 'gate', pos: MAKKAH_SPOTS.gate, r: 2.6, on: () => phase === 'walk', action: { label: 'ادخل برجلك اليمين', key: 'E', icon: 'ri-door-open-line' } },
  ]);
  function start() {
    world.heroes.player.setOutfit('ihram'); world.heroes.mentor.setOutfit('ihram');
    list(); setObjective('استمع للحاج حسن');
    say(MAKKAH.intro, () => { phase = 'guide'; setObjective('استلم مفتاح الأوضة', 'من مرشد الفندق'); });
  }
  async function act(id) {
    if (id === 'guide' && phase === 'guide') {
      phase = 'busy'; setAction(null); faceTo({ x: -5, z: 17.2 });
      say([...MAKKAH.guide, MAKKAH.toHaram], () => { phase = 'walk'; list(); setObjective('على المسجد الحرام', 'الباب في آخر الساحة'); });
    } else if (id === 'gate' && phase === 'walk') {
      phase = 'in'; setAction(null); list(); stats.s.entered = true;
      await showOverlay({ title: MAKKAH.enter.title, body: MAKKAH.enter.body, button: 'ادخل' });
      goTo('tawaf');
    }
  }
  function update() {
    spots.update();
    const P = world.player.pos;
    if (phase === 'walk' && !toldGate && P.z < -30) { toldGate = true; tip(MAKKAH.gate); }
  }
  function onTalbiyah() { stats.s.talbiyahMakkah = (stats.s.talbiyahMakkah || 0) + 1; list(); }
  const target = () => spots.next()?.pos || null;
  return { start, act, update, onTalbiyah, onHit() {}, autopilot: () => { const t = target(); return t && { x: t.x, z: t.z }; }, minimap: () => ({ target: target() }), hideTag: () => false };
}
