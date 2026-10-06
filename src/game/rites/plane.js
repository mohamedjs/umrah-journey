import { PLANE, arNum } from '../content.js';
import { useStore, say, tip, setObjective, setChecklist, setAction, showOverlay, toast } from '../store.js';
import { world } from '../refs.js';
import { PLANE_SPOTS } from '../scenes/plane.js';
import { hotspots, bubble } from './kit.js';
import { stats } from './stats.js';

// Chapter 3 — the plane and the miqat. Before the miqat: wudu + ihram clothes (in the
// lavatory). At the miqat (the captain's announcement): the niyyah «لبيك اللهم عمرة» and the
// talbiyah. The 20 minutes are compressed (MIQAT_S seconds of play); if the player isn't ready
// the countdown waits at one minute while الحاج حسن hurries him — the game never lets him pass
// the miqat without ihram.
const MIQAT_S = 100, GAME_MIN = 20;
const mmss = s => { const m = Math.floor(s / 60), r = Math.floor(s % 60); return `${arNum(String(m).padStart(2, '0'))}:${arNum(String(r).padStart(2, '0'))}`; };

export function createPlane({ goTo }) {
  let phase = 'intro', wudu = false, dressed = false, left = GAME_MIN * 60, hurried = false;
  const list = () => setChecklist({ title: 'قبل الميقات', items: [
    { label: 'اتوضيت', state: wudu ? 'on' : '' },
    { label: 'لبست الإحرام', state: dressed ? 'on' : '' },
    { label: 'النية عند الميقات: لبيك اللهم عمرة', state: phase === 'ihram' || phase === 'landed' ? 'on' : '' },
  ] });
  const spots = hotspots([
    { id: 'wudu', pos: PLANE_SPOTS.lav, r: 1.5, on: () => phase === 'prep' && !wudu, action: { label: 'اتوضى', key: 'E', icon: 'ri-drop-line' } },
    { id: 'dress', pos: PLANE_SPOTS.lav, r: 1.5, on: () => phase === 'prep' && wudu && !dressed, action: { label: 'البس الإحرام', key: 'E', icon: 'ri-shirt-line' } },
  ]);
  function start() {
    stats.reset('plane'); list(); setObjective('استمع للإعلان');
    say(PLANE.intro, () => { phase = 'prep'; setObjective('جهّز نفسك قبل الميقات', 'الحمّام في آخر الطيارة'); });
  }
  async function act(id) {
    if (id === 'wudu') { wudu = true; setAction(null); list(); toast('اتوضيت ✓'); tip(PLANE.wudu); }
    else if (id === 'dress') {
      dressed = true; setAction(null); list();
      world.heroes.player.setOutfit('ihram'); world.heroes.mentor.setOutfit('ihram');
      stats.s.readyBefore = left > 0; tip(PLANE.dressed, 6000);
      if (phase === 'prep') phase = 'wait';
      setObjective('استنى إعلان الميقات', 'لسه منويتش');
    } else if (id === 'niyyah' && phase === 'niyyah') {
      setAction(null); world.gesture = 1.6; bubble(PLANE.niyyah.fusha, 3); phase = 'ihram'; list();
      await showOverlay({ title: PLANE.talbiyah.title, body: PLANE.talbiyah.body, button: 'لبّيك' });
      stats.s.talbiyah = (stats.s.talbiyah || 0) + 1;
      world.talbiyah = true; useStore.setState({ talbiyah: true });
      setObjective('إنت محرم دلوقتي', 'ردّد التلبية');
      say(PLANE.after, () => setTimeout(() => {
        phase = 'landed'; say(PLANE.landed, () => setAction({ id: 'go', label: 'انزل على مكة', key: 'E', icon: 'ri-arrow-left-line' }));
      }, 2500));
    } else if (id === 'go' && phase === 'landed') { setAction(null); goTo('makkah'); }
  }
  function update(dt) {
    spots.update();
    if (phase === 'prep' || phase === 'wait') {
      const ready = wudu && dressed;
      left = Math.max(ready ? 0 : 60, left - dt * (GAME_MIN * 60 / MIQAT_S));
      useStore.setState({ hint: `الميقات بعد ${mmss(left)}` });
      if (!ready && left < 5 * 60 && !hurried) { hurried = true; tip(PLANE.hurry); }
      if (ready && left <= 0) {
        phase = 'miqat'; useStore.setState({ hint: '' });
        say([PLANE.captain2, PLANE.niyyahNow], () => { phase = 'niyyah'; setObjective('انوِ العمرة'); setAction({ id: 'niyyah', label: 'انوِ وقل: لبيك اللهم عمرة', key: 'G', icon: 'ri-hand-heart-line' }); });
      }
    }
  }
  const autopilot = () => {
    if (phase === 'prep') return { x: PLANE_SPOTS.lav.x, z: PLANE_SPOTS.lav.z };
    if (phase === 'wait') return { x: 0, z: -2.8 };
    return null;
  };
  return { start, act, update, onHit() {}, autopilot, minimap: () => ({ target: phase === 'prep' ? PLANE_SPOTS.lav : null }), hideTag: () => false };
}
