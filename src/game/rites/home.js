import { HOME } from '../content.js';
import { say, tip, setObjective, setChecklist, setAction, showOverlay, ask } from '../store.js';
import { world } from '../refs.js';
import { HOME_SPOTS } from '../scenes/home.js';
import { hotspots, faceTo } from './kit.js';
import { stats } from './stats.js';

// Chapter 1 — pack the Umrah bag. Perfume is the "trap": it is worn on the body before ihram,
// never packed to be used while in ihram. A wrong pick only brings a gentle correction.
export function createHome({ goTo, scene }) {
  const got = { passport: false, ihram: false, sandals: false, perfume: false };
  let phase = 'intro', perfumeTries = 0;
  const KEYS = ['passport', 'ihram', 'sandals', 'perfume'];
  const list = () => setChecklist({
    title: 'شنطة العمرة',
    items: KEYS.map(k => ({ label: k === 'perfume' ? 'العطر (قبل الإحرام بس)' : HOME.items[k].label, state: got[k] ? 'on' : (k === 'perfume' && perfumeTries ? 'x' : '') })),
  });
  const spots = hotspots([
    ...KEYS.map(k => ({ id: k, pos: HOME_SPOTS[k], r: 2.1, on: () => phase === 'collect' && !got[k], action: { label: `خد ${HOME.items[k].label}`, key: 'E', icon: k === 'passport' ? 'ri-passport-line' : k === 'ihram' ? 'ri-shirt-line' : k === 'sandals' ? 'ri-footprint-line' : 'ri-drop-line' } })),
    { id: 'door', pos: HOME_SPOTS.door, r: 1.8, on: () => phase === 'door', action: { label: 'اخرج من البيت', key: 'E', icon: 'ri-door-open-line' } },
  ]);

  function start() {
    stats.reset('home'); list();
    setObjective('استمع للحاج حسن');
    say(HOME.intro, () => { phase = 'collect'; setObjective('جهّز شنطة العمرة', 'قرّب من الحاجات المنوّرة'); });
  }
  async function act(id) {
    if (KEYS.includes(id) && phase === 'collect') {
      setAction(null); faceTo(HOME_SPOTS[id]); world.gesture = 0.8;
      if (id === 'perfume') {
        const pick = await ask(HOME.perfumeAsk);
        if (pick !== HOME.perfumeAsk.right) { perfumeTries++; list(); say(HOME.perfumeWrong); return; }
        stats.s.perfumeRight = perfumeTries === 0;
        say(HOME.perfumeRight);
      } else say(HOME.items[id].line);
      got[id] = true; scene.take(id); list();
      if (KEYS.every(k => got[k])) {
        stats.s.packed = true;
        say(HOME.done, () => { phase = 'door'; scene.showDoor(true); setObjective('اخرج من البيت', 'الباب في الركن'); });
      }
    } else if (id === 'door' && phase === 'door') {
      phase = 'leave'; setAction(null);
      await showOverlay({ title: HOME.leave.title, body: HOME.leave.fusha, button: 'على المطار' });
      goTo('airport');
    }
  }
  function update() { spots.update(); }
  const target = () => spots.next()?.pos || null;
  return { start, act, update, onHit() {}, autopilot: () => { const t = target(); return t && { x: t.x, z: t.z }; }, minimap: () => ({ target: target() }), hideTag: k => k && (k === 'door' ? phase !== 'door' : got[k]) };
}
