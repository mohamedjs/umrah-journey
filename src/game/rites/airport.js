import { AIRPORT } from '../content.js';
import { say, setObjective, setChecklist, setAction, showOverlay } from '../store.js';
import { AIRPORT_SPOTS } from '../scenes/airport.js';
import { hotspots, faceTo } from './kit.js';

// Chapter 2 — check-in at the airline counter, then gate 12 and boarding (travel du'a).
export function createAirport({ goTo }) {
  let phase = 'intro';
  const list = () => setChecklist({ title: 'في المطار', items: [
    { label: 'سلّمت الشنطة وخدت كارت الصعود', state: phase === 'intro' || phase === 'counter' ? '' : 'on' },
    { label: 'البوابة ١٢', state: phase === 'board' ? 'on' : '' },
  ] });
  const spots = hotspots([
    { id: 'counter', pos: AIRPORT_SPOTS.counter, r: 2.2, on: () => phase === 'counter', action: { label: 'سلّم الجواز والشنطة', key: 'E', icon: 'ri-suitcase-line' } },
    { id: 'gate', pos: AIRPORT_SPOTS.gate, r: 2.2, on: () => phase === 'gate', action: { label: 'اركب الطيارة', key: 'E', icon: 'ri-flight-takeoff-line' } },
  ]);
  function start() {
    list(); setObjective('استمع للحاج حسن');
    say(AIRPORT.intro, () => { phase = 'counter'; setObjective('روح كاونتر الطيران', 'سلّم الشنطة وخد كارت الصعود'); });
  }
  async function act(id) {
    if (id === 'counter' && phase === 'counter') {
      phase = 'busy'; setAction(null); faceTo(AIRPORT_SPOTS.counter.clone().setZ(-10));
      say([...AIRPORT.counter, AIRPORT.toGate], () => { phase = 'gate'; list(); setObjective('روح البوابة ١٢', 'في آخر الصالة على اليمين'); });
    } else if (id === 'gate' && phase === 'gate') {
      phase = 'board'; setAction(null); list();
      say(AIRPORT.gate, async () => {
        await showOverlay({ title: AIRPORT.travel.title, body: AIRPORT.travel.body, button: 'يلا نركب' });
        goTo('plane');
      });
    }
  }
  const target = () => spots.next()?.pos || null;
  return { start, act, update: () => spots.update(), onHit() {}, autopilot: () => { const t = target(); return t && { x: t.x, z: t.z }; }, minimap: () => ({ target: target() }), hideTag: () => false };
}
