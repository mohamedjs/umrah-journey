import { SAI, arNum } from '../content.js';
import { useStore, say, tip, setAction, setCard, setObjective, setCounter, showOverlay, toast } from '../store.js';
import { world } from '../refs.js';
import { LEN, GREEN, SAFA_Z, MARWA_Z, KAABA_HEADING } from '../masa.js';
import { stats } from './stats.js';

// Sa'i rules (chapter 7): start on as-Safa, seven laps, as-Safa → al-Marwa is one lap and the
// way back another, so it ends on al-Marwa. Men jog between the green lights (sunnah).
export function createSai({ end }) {
  let phase = 'intro', lap = 0, from = 'safa', furthest = 0, cool = {}, once = {};
  let green = { in: false, t: 0, run: 0 }, hillDone = false;
  const cd = (k, s) => { const t = world.time; if ((cool[k] ?? -99) > t) return false; cool[k] = t + s; return true; };
  const first = k => (once[k] ? false : (once[k] = true));
  const counter = () => setCounter({ total: 7, done: lap, current: phase === 'sai' ? lap + 1 : 0 });
  const goal = () => (from === 'safa' ? 'المروة' : 'الصفا');

  function start() {
    phase = 'intro'; stats.reset('sai'); counter();
    setObjective('استمع للحاج حسن');
    say(SAI.intro, () => { phase = 'to-safa'; setObjective('اطلع على الصفا', 'السعي بيبدأ من الصفا'); });
  }

  function act(id) {
    if (id !== 'hill') return;
    setAction(null); world.player.heading = KAABA_HEADING; world.gesture = 2.2; stats.s.hills++; hillDone = true;
    if (phase === 'to-safa') {
      phase = 'safa';
      say(SAI.onSafa, () => showOverlay({ ...SAI.safaCard, button: 'يلا على المروة' }).then(() => {
        phase = 'sai'; lap = 0; from = 'safa'; furthest = 0; counter();
        setObjective(`إلى ${goal()}`, `الشوط ${arNum(1)} من ٧`);
        say(SAI.go);
      }));
    } else {
      showOverlay({ ...SAI.hillCard, button: 'كمّل' });
    }
  }

  function update(dt) {
    const P = world.player.pos, z = P.z, running = world.player.running && world.player.moving;
    const onSafa = z > SAFA_Z, onMarwa = z < MARWA_Z;
    const a = useStore.getState().action;

    if (phase === 'to-safa') {
      if (z < -16 && cd('ws', 12)) tip(SAI.wrongStart);
      if (onSafa && !a) setAction({ id: 'hill', label: 'استقبل الكعبة واذكر الله', key: 'G', icon: 'ri-hand-heart-line' });
      else if (!onSafa && a?.id === 'hill') setAction(null);
      return;
    }
    if (phase !== 'sai') return;

    // progress along this lap, in metres
    const d = from === 'safa' ? SAFA_Z - z : z - MARWA_Z;
    furthest = Math.max(furthest, d);
    if (d < furthest - 12 && furthest > 15 && cd('ny', 12)) tip(SAI.notYet);

    // optional dhikr on the hill you are standing on (not after the last lap)
    const onStartHill = from === 'safa' ? onSafa : onMarwa;
    if (onStartHill && lap > 0 && !hillDone && !a) setAction({ id: 'hill', label: 'استقبل الكعبة واذكر الله', key: 'G', icon: 'ri-hand-heart-line' });
    else if (!onStartHill && a?.id === 'hill') setAction(null);

    // the green lights
    const inG = z < GREEN[0] && z > GREEN[1];
    if (inG && !green.in) {
      green = { in: true, t: 0, run: 0 };
      if (first('green')) tip(SAI.green); else if (cd('ga', 30)) tip(SAI.greenAgain, 2500);
    }
    if (inG) { green.t += dt; if (running) green.run += dt; setCard(SAI.greenDua); }
    if (!inG && green.in) {
      green.in = false; setCard(null);
      const ratio = green.t ? green.run / green.t : 0; stats.s.greenRun.push(ratio);
      if (ratio < 0.3 && first('gm')) tip(SAI.greenMiss);
    }

    // arrived at the other hill → one lap
    if ((from === 'safa' && onMarwa) || (from === 'marwa' && onSafa)) {
      lap++; from = from === 'safa' ? 'marwa' : 'safa'; furthest = 0; hillDone = false; stats.s.laps = lap;
      counter();
      if (lap === 7) return finish();
      toast(`الشوط ${arNum(lap)} ✓`);
      tip(SAI.lap[lap], 5000);
      setObjective(`إلى ${goal()}`, `الشوط ${arNum(lap + 1)} من ٧`);
    }
  }

  function finish() {
    phase = 'done'; setAction(null); setCard(null); counter();
    setObjective('خلصت السعي', 'تقبّل الله');
    say(SAI.done, end);
  }

  function autopilot() {
    if (phase === 'to-safa') return { x: -3.5, z: SAFA_Z + 3 };
    if (phase !== 'sai') return null;
    const { x, z } = world.player.pos, lane = from === 'safa' ? -4 : 4;
    // past the divider's end: first step across into this direction's lane
    if (Math.abs(x - lane) > 1.5 && (z > -3 || z < -LEN + 3)) return { x: lane, z };
    return { x: lane, z: from === 'safa' ? MARWA_Z - 3 : SAFA_Z + 3, run: z < GREEN[0] + 1 && z > GREEN[1] - 1 };
  }
  function minimap() { return { phase, lap, from, len: LEN }; }
  return { start, act, update, autopilot, onHit() {}, minimap };
}
