import { TAWAF, arNum } from '../content.js';
import { useStore, say, tip, setAction, setCard, setObjective, setCounter, showOverlay, toast } from '../store.js';
import { world } from '../refs.js';
import { ang, prayPos, blackStone, maqamPos } from '../mataf.js';
import { stats } from './stats.js';

// Tawaf rules (chapter 5) + two rak'ahs behind Maqam Ibrahim and Zamzam (chapter 6).
// Progress is the unwrapped angle walked round the Kaaba since the start line (θ = 0, the
// Black Stone corner). Counter-clockwise adds, clockwise takes away, so walking backwards
// never counts; 7 × 2π = done. Mistakes only bring a gentle word from الحاج حسن.
const TAU = Math.PI * 2;
const wrap = a => Math.atan2(Math.sin(a), Math.cos(a));
const norm = a => ((a % TAU) + TAU) % TAU;

export function createTawaf({ goTo }) {
  let phase = 'intro', prevTh = 0, p = 0, maxP = 0, done = 0, gestured = false, back = 0;
  let circ = { run: 0, move: 0 }, cool = {}, once = {};
  const cd = (k, s) => { const t = world.time; if ((cool[k] ?? -99) > t) return false; cool[k] = t + s; return true; };
  const first = k => (once[k] ? false : (once[k] = true));
  const counter = () => setCounter({ total: 7, done, current: phase === 'tawaf' ? done + 1 : 0 });

  function start() {
    phase = 'intro'; stats.reset('tawaf'); world.talbiyah = false; useStore.setState({ talbiyah: false });   // talbiyah stops as tawaf begins prevTh = ang(world.player.pos.x, world.player.pos.z);
    setObjective('استمع للحاج حسن');
    setCounter({ total: 7, done: 0, current: 0 });
    say(TAWAF.intro, () => {
      phase = 'idtiba';
      setObjective('اضطبع', 'خلّي كتفك اليمين يبان');
      setAction({ id: 'idtiba', label: 'اضطبع (كتفك اليمين يبان)', key: 'R', icon: 'ri-shirt-line' });
    });
  }

  function faceTo(v) { const P = world.player.pos; world.player.heading = Math.atan2(v.x - P.x, v.z - P.z); }

  function act(id) {
    if (id === 'idtiba' && phase === 'idtiba') {
      world.heroes.player.setIdtiba(true); world.heroes.mentor.setIdtiba(true); stats.s.idtiba = true;
      setAction(null); phase = 'to-start';
      say(TAWAF.idtibaDone, () => setObjective('روح لخط البداية', 'عند ركن الحجر الأسود — الخط المنوّر'));
    } else if (id === 'gesture') {
      faceTo(blackStone); world.gesture = 1.4; gestured = true; stats.s.gestures++;
      bubble(phase === 'to-start' ? TAWAF.firstTakbir.fusha : TAWAF.takbir.fusha);
      setAction(null);
    } else if (id === 'cover' && phase === 'cover') {
      world.heroes.player.setIdtiba(false); world.heroes.mentor.setIdtiba(false);
      setAction(null); phase = 'to-maqam';
      say(TAWAF.toMaqam, () => setObjective('صلِّ ركعتين خلف مقام إبراهيم', 'روح للدايرة المنوّرة ورا المقام'));
    } else if (id === 'pray' && phase === 'to-maqam') {
      phase = 'pray'; setAction(null); faceTo(maqamPos); world.pray = 4;
      showOverlay({ ...TAWAF.pray, button: 'تقبّل الله' }).then(() => {
        say(TAWAF.zamzam, () => {
          phase = 'zamzam'; setObjective('على المسعى', 'السعي بين الصفا والمروة');
          setAction({ id: 'to-sai', label: 'على المسعى', key: 'E', icon: 'ri-arrow-left-line' });
        });
      });
    } else if (id === 'to-sai' && phase === 'zamzam') { setAction(null); goTo('sai'); }
  }

  const bubble = text => useStore.setState({ bubble: { text, until: world.time + 2.6 } });

  function update(dt) {
    const P = world.player.pos, th = ang(P.x, P.z), r = Math.hypot(P.x, P.z);
    const old = prevTh, dth = wrap(th - old); prevTh = th;
    const running = world.player.running && world.player.moving;

    if (phase === 'to-start') {
      if (dth < 0 && world.player.moving) back -= dth; else if (dth > 0) back = Math.max(0, back - dth);
      if (back > 0.6 && cd('wws', 12)) { tip(TAWAF.wrongWayStart); back = 0; }
      const win = th > -0.2 && th < 0.02 && r < 42;
      if (win && !gestured) { if (first('atStart')) tip(TAWAF.atStart, 7000); setAction({ id: 'gesture', label: 'شاور بيمينك وكبّر', key: 'G', icon: 'ri-hand-heart-line' }); }
      else if (useStore.getState().action?.id === 'gesture' && !win) setAction(null);
      if (old < 0 && old > -0.5 && th >= 0 && th < 0.5 && r < 44) {        // crossed the start line
        phase = 'tawaf'; p = th; maxP = p; done = 0; circ = { run: 0, move: 0 };
        if (!gestured) tip(TAWAF.noGesture); gestured = false; setAction(null);
        stats.s.started = true;
        setObjective('طُف سبعة أشواط', 'الكعبة على شمالك');
        counter();
        say(TAWAF.go);
      }
      return;
    }

    if (phase === 'tawaf') {
      p += dth; maxP = Math.max(maxP, p);
      if (p < maxP - 0.35 && cd('ww', 10)) tip(TAWAF.wrongWay);
      if (world.player.moving) { circ.move += dt; if (running) circ.run += dt; }
      const tn = norm(p), frac = (p - done * TAU) / TAU;
      // Rukn al-Yamani, then the du'a between it and the Black Stone
      if (tn > 1.5 * Math.PI - 0.12 && tn < 1.5 * Math.PI + 0.06 && r < 14 && first('yamani')) tip(TAWAF.yamani, 7000);
      setCard(tn > 1.5 * Math.PI && tn < TAU - 0.02 ? TAWAF.rabbana : null);
      if (done === 1 && frac > 0.1 && first('freeDua')) tip(TAWAF.freeDua);
      // raml advice
      if (done >= 3 && frac > 0.4 && circ.move > 4 && circ.run / circ.move > 0.6 && first('ranLate')) tip(TAWAF.ranLate);
      // approaching the start line: offer the gesture for the next circuit
      const win = tn > TAU - 0.2 && done < 6 && r < 42;
      if (win && !gestured) setAction({ id: 'gesture', label: 'شاور بيمينك وكبّر', key: 'G', icon: 'ri-hand-heart-line' });
      else if (!win && useStore.getState().action?.id === 'gesture') setAction(null);
      if (p >= (done + 1) * TAU) {                    // a circuit is complete
        done++;
        if (done <= 3) stats.s.raml.push(circ.move ? circ.run / circ.move : 0);
        const ramlLow = done <= 2 && circ.move && circ.run / circ.move < 0.35;
        circ = { run: 0, move: 0 }; gestured = false; setAction(null);
        counter();
        if (done === 7) return finish();
        toast(`الشوط ${arNum(done)} ✓`);
        tip(ramlLow && first('ramlMiss') ? TAWAF.ramlMiss : TAWAF.circuit[done]);
      }
      return;
    }

    if (phase === 'to-maqam') {
      const near = P.distanceTo(prayPos) < 2.4;
      const a = useStore.getState().action;
      if (near && !a) setAction({ id: 'pray', label: 'صلِّ ركعتين', key: 'E', icon: 'ri-user-heart-line' });
      else if (!near && a?.id === 'pray') setAction(null);
    }
  }

  function finish() {
    phase = 'cover'; setCard(null);
    stats.s.circuits = 7;
    setObjective('غطّي كتفك اليمين');
    say(TAWAF.done, () => setAction({ id: 'cover', label: 'غطّي كتفك', key: 'R', icon: 'ri-shirt-line' }));
  }

  // where the autopilot (👣) walks next
  function autopilot() {
    const P = world.player.pos, th = ang(P.x, P.z), r = Math.hypot(P.x, P.z);
    if (phase === 'to-start' || phase === 'tawaf') {
      const rr = r + (16.8 - r) * 0.5, a = th + 0.2;
      return { x: Math.cos(a) * rr, z: -Math.sin(a) * rr, run: phase === 'tawaf' && done < 3 };
    }
    if (phase === 'to-maqam') {
      // go round the Maqam on the outside
      const pt = ang(prayPos.x, prayPos.z);
      if (Math.abs(wrap(th - pt)) > 0.12 && r < 20.5) { const a = th + Math.sign(wrap(pt - th)) * 0.2, rr = Math.min(21, r + 1.5); return { x: Math.cos(a) * rr, z: -Math.sin(a) * rr }; }
      return { x: prayPos.x, z: prayPos.z };
    }
    return null;
  }

  function onHit(what) { if (what === 'hijr' && cd('hijr', 15)) tip(TAWAF.hijr); }
  function minimap() { return { phase, progress: phase === 'tawaf' ? p / TAU : 0, done }; }
  return { start, act, update, autopilot, onHit, minimap };
}
