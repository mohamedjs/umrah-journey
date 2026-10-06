import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import 'remixicon/fonts/remixicon.css';
import { useStore, next, closeOverlay, say, CINEMATIC } from '../store.js';
import { world } from '../refs.js';
import { QA, arNum } from '../content.js';
import { runAction } from '../Controller.jsx';
import { Q, toggleQuality } from '../quality.js';
import { voice } from '../voice.js';
import { isTouch, showStick } from '../input.js';
import { H, R, HIJR, maqamPos, prayPos } from '../mataf.js';
import { GREEN, SAFA_Z, MARWA_Z } from '../masa.js';
import { CHAPTERS } from '../chapters.js';
import { talbiyah } from '../rites/kit.js';

// All icons are Remix Icon (https://remixicon.com) — <Ic n="footprint" /> → <i class="ri-footprint-line">
const Ic = ({ n, fill }) => <i className={`ri ri-${n}-${fill ? 'fill' : 'line'}`} aria-hidden="true" />;
const NUMS = [1, 2, 3, 4, 5, 6, 7];


export function Hud() {
  const s = useStore();
  const touch = isTouch();
  useEffect(() => { showStick(s.screen === 'play' && !s.dialog?.blocking && !s.overlay && !CINEMATIC); }, [s.screen, s.dialog, s.overlay]);

  if (s.screen === 'title') return <Title />;
  if (s.screen === 'end') return <End summary={s.summary} />;
  const blocking = s.dialog?.blocking;
  return (
    <div id="hud" className={(touch ? 'touch ' : '') + (CINEMATIC ? 'cine' : '')}>
      <div className="chap">{s.chapterTitle}</div>
      {s.objective && <div className="obj"><small>المهمة</small><b>{s.objective}</b>{s.objectiveSub && <em>{s.objectiveSub}</em>}</div>}
      {s.counter && (
        <div className="cnt" aria-label={`الشوط ${s.counter.current || s.counter.done} من ٧`}>
          {NUMS.map(n => <i key={n} className={n <= s.counter.done ? 'on' : n === s.counter.current ? 'cur' : ''}>{arNum(n)}</i>)}
        </div>
      )}
      {s.checklist && (
        <div className="list"><h4>{s.checklist.title}</h4>
          {s.checklist.items.map(it => <div key={it.label}><span className={'ck ' + it.state}>{it.state === 'on' ? <Ic n="check" /> : it.state === 'x' ? <Ic n="close" /> : null}</span>{it.label}</div>)}
        </div>
      )}
      {s.hint && <div className="hint"><Ic n="timer" />{s.hint}</div>}
      {s.card && <div className="card"><small>{s.card.title}</small><p className="fusha">{s.card.fusha}</p></div>}
      <Tags />
      <Minimap />
      {s.toast && <div className="toast">{s.toast}</div>}
      {s.dialog && (
        <div className={'dlg' + (blocking ? '' : ' tip')} onClick={next}>
          <span className="who">{s.dialog.who}</span>
          <p>{s.dialog.text}</p>
          {blocking && <span className="nx">التالي <Ic n="arrow-left-s" /></span>}
        </div>
      )}
      {s.action && !blocking && !s.overlay && (
        <button className="act" onClick={() => runAction(s.action.id)}>
          <i className={'ri ' + (s.action.icon || 'ri-hand-heart-line')} aria-hidden="true" />{s.action.label}{!touch && <kbd>{s.action.key}</kbd>}
        </button>
      )}
      {!CINEMATIC && (
        <div className="dock">
          {s.talbiyah && <button className="wide" title="لبّيك (T)" onClick={talbiyah}><Ic n="speak" /><span>لبّيك</span></button>}
          <button className={s.auto ? 'on' : ''} title="امشِ تلقائيًا (F)" onClick={() => useStore.setState({ auto: !s.auto })}><Ic n="footprint" /></button>
          {touch && <button className={s.runHold ? 'on' : ''} title="هرولة / رمل" onClick={() => useStore.setState({ runHold: !s.runHold })}><Ic n="run" /></button>}
          <button title="اسأل الحاج حسن" onClick={() => useStore.setState({ qaOpen: !s.qaOpen })}><Ic n="question-answer" /></button>
          <button title="الصوت" onClick={() => { voice.muted = !voice.muted; if (voice.muted) voice.stop(); useStore.setState({}); }}><Ic n={voice.muted ? 'volume-mute' : 'volume-up'} /></button>
        </div>
      )}
      {s.qaOpen && <QaPanel chapter={s.chapter} />}
      {!touch && !CINEMATIC && <div className="keys">WASD تمشي · Shift رمل/هرولة · اسحب للكاميرا · F مشي تلقائي · Enter التالي{s.talbiyah ? ' · T لبّيك' : ''}</div>}
      {s.overlay && <Overlay o={s.overlay} />}
    </div>
  );
}

function Title() {
  const start = ch => useStore.setState({ screen: 'play', chapter: ch });
  return (
    <div id="title">
      <div className="panel">
        <small>نموذج تجريبي</small>
        <h1>رحلة العمرة</h1>
        <p>امشِ مع الحاج حسن خطوة بخطوة، من البيت لحد آخر شوط في السعي.</p>
        <div className="chapters">
          <button className="big" onClick={() => start('home')}><Ic n="play" fill /><b>ابدأ الرحلة</b></button>
        </div>
        <div className="grid">
          {CHAPTERS.map(c => (
            <button key={c.id} onClick={() => start(c.id)}>
              <i className={'ri ' + c.icon} aria-hidden="true" />
              <b>الفصل {arNum(c.n)} · {c.title}</b><span>{c.sub}</span>
            </button>
          ))}
        </div>
        <div className="row">
          <button className="ghost" onClick={toggleQuality}><Ic n="settings-3" /> الجودة: {Q.label}</button>
        </div>
        <em>المحتوى الشرعي في انتظار مراجعة الشيخ قبل النشر.</em>
      </div>
    </div>
  );
}

function End({ summary: m = {} }) {
  const raml = m.raml?.length ? Math.round(m.raml.reduce((a, b) => a + b, 0) / m.raml.length * 100) : null;
  const green = m.greenRun?.length ? Math.round(m.greenRun.reduce((a, b) => a + b, 0) / m.greenRun.length * 100) : null;
  const Li = ({ children }) => <li><Ic n="check" />{children}</li>;
  return (
    <div id="title">
      <div className="panel">
        <small>تقبّل الله</small>
        <h1>{m.circuits && m.laps ? 'خلصت الطواف والسعي' : m.laps ? 'خلصت السعي' : 'خلصت الطواف'}</h1>
        <ul className="sum">
          {m.packed ? <Li>جهّزت شنطة العمرة{m.perfumeRight ? '، والعطر صح من أول مرة' : ''}</Li> : null}
          {m.readyBefore ? <Li>لبست الإحرام قبل الميقات</Li> : null}
          {m.talbiyah ? <Li>التلبية: {arNum(m.talbiyah)} مرة</Li> : null}
          {m.entered ? <Li>دخلت المسجد الحرام بالدعاء</Li> : null}
          {m.circuits ? <Li>الطواف: {arNum(m.circuits)} أشواط</Li> : null}
          {m.idtiba ? <Li>الاضطباع</Li> : null}
          {m.gestures ? <Li>الإشارة للحجر الأسود والتكبير: {arNum(m.gestures)} مرة</Li> : null}
          {raml !== null ? <Li>الرمل في أول ٣ أشواط: {arNum(raml)}٪</Li> : null}
          {m.laps ? <Li>السعي: {arNum(m.laps)} أشواط، من الصفا للمروة</Li> : null}
          {green !== null ? <Li>الهرولة بين العلمين الأخضرين: {arNum(green)}٪</Li> : null}
          {m.hills ? <Li>الذكر على الصفا والمروة: {arNum(m.hills)} مرة</Li> : null}
        </ul>
        <p>الفصل الجاي: الحلق أو التقصير، وبيه تخلص العمرة.</p>
        <div className="chapters"><button onClick={() => location.reload()}><Ic n="restart" /><b>العب تاني</b></button></div>
      </div>
    </div>
  );
}

function Overlay({ o }) {
  return (
    <div className="ovl">
      <div className="panel">
        <small>{o.title}</small>
        {o.verse && <p className="verse">﴿{o.verse}﴾<span>[{o.ref}]</span></p>}
        {o.hadith && <p className="hadith">«{o.hadith}»</p>}
        {o.body && <p className={/[ًٌٍَُِّْ]/.test(o.body) && !o.verse ? 'fusha' : 'body'}>{o.body}</p>}
        {o.options
          ? <div className="opts">{o.options.map((t, i) => <button key={i} onClick={() => closeOverlay(i)}>{t}</button>)}</div>
          : <button onClick={() => closeOverlay()}>{o.button || 'تمام'} <Ic n="arrow-left-s" /></button>}
      </div>
    </div>
  );
}

function QaPanel({ chapter }) {
  const ask = item => { useStore.setState({ qaOpen: false }); say([{ id: item.a.id + '-q', who: 'player', text: item.q }, item.a]); };
  return (
    <div className="qa">
      <h4><Ic n="question-answer" /> اسأل الحاج حسن</h4>
      {(QA[chapter] || []).map(item => <button key={item.a.id} onClick={() => ask(item)}>{item.q}</button>)}
    </div>
  );
}

// ---------------------------------------------------------------- floating name tags
function Tags() {
  const ref = useRef();
  useEffect(() => {
    let id; const v = new THREE.Vector3();
    const tags = () => [
      { text: 'أنت', me: true, pos: v.clone().copy(world.player.pos).setY(2.55) },
      { text: 'الحاج حسن', pos: v.clone().copy(world.mentor.pos).setY(2.5) },
      ...(world.layout?.tags || []).filter(t => !world.rites?.hideTag?.(t.spot)),
    ];
    const loop = () => {
      const el = ref.current, cam = world.camera;
      if (el && cam) {
        const list = tags(), st = useStore.getState();
        if (st.bubble && st.bubble.until > world.time) list.push({ text: st.bubble.text, bubble: true, pos: v.clone().copy(world.player.pos).setY(3.25) });
        while (el.children.length < list.length) el.append(document.createElement('div'));
        [...el.children].forEach((d, i) => {
          const t = list[i];
          if (!t) { d.style.display = 'none'; return; }
          v.copy(t.pos).project(cam);
          const dist = cam.position.distanceTo(t.pos);
          const show = v.z < 1 && Math.abs(v.x) < 1.1 && Math.abs(v.y) < 1.1 && (t.me || t.bubble || dist < 55);
          d.style.display = show ? '' : 'none'; if (!show) return;
          d.className = 'tag' + (t.me ? ' me' : '') + (t.bubble ? ' bubble' : '');
          if (d.textContent !== t.text) d.textContent = t.text;
          d.style.transform = `translate(${(v.x * 0.5 + 0.5) * innerWidth}px, ${(-v.y * 0.5 + 0.5) * innerHeight}px) translate(-50%, -100%)`;
        });
      }
      id = requestAnimationFrame(loop);
    };
    id = requestAnimationFrame(loop); return () => cancelAnimationFrame(id);
  }, []);
  return <div className="tags" ref={ref} />;
}

// ---------------------------------------------------------------- minimap (north up)
function Minimap() {
  const ref = useRef();
  useEffect(() => {
    const cv = ref.current, x = cv.getContext('2d'), S = cv.width, c = S / 2;
    const draw = () => {
      const L = world.layout, P = world.player.pos, m = world.rites?.minimap?.() || {};
      x.clearRect(0, 0, S, S);
      if (L?.id === 'tawaf') {
        const k = (c - 8) / L.mini, X = px => c + px * k, Z = pz => c + pz * k;
        x.strokeStyle = 'rgba(255,255,255,.18)'; x.lineWidth = 12 * k * 2; x.beginPath(); x.arc(c, c, 17 * k, 0, 7); x.stroke();
        // start line
        x.strokeStyle = '#ffd68c'; x.lineWidth = 2; x.beginPath(); x.moveTo(X(R), c); x.lineTo(X(L.mini), c); x.stroke();
        // progress arc (counter-clockwise on the map = anticlockwise canvas)
        if (m.progress > 0) { const fr = m.progress - m.done; x.strokeStyle = '#ffd68c'; x.lineWidth = 4; x.setLineDash([5, 4]); x.beginPath(); x.arc(c, c, 21 * k, 0, -fr * Math.PI * 2, true); x.stroke(); x.setLineDash([]); }
        // Kaaba (diamond), Hijr, Maqam
        x.save(); x.translate(c, c); x.rotate(-Math.PI / 4); x.fillStyle = '#111'; x.strokeStyle = '#d4a84d'; x.lineWidth = 2; x.fillRect(-H * k, -H * k, 2 * H * k, 2 * H * k); x.strokeRect(-H * k, -H * k, 2 * H * k, 2 * H * k);
        x.strokeStyle = '#e8e3d6'; x.lineWidth = 2.5; x.beginPath(); x.ellipse(0, -H * k, (HIJR.a + 0.4) * k, (HIJR.b + 0.4) * k, 0, Math.PI, 0); x.stroke(); x.restore();
        x.fillStyle = '#d8b664'; x.beginPath(); x.arc(X(maqamPos.x), Z(maqamPos.z), 3, 0, 7); x.fill();
        if (m.phase === 'to-maqam') { x.strokeStyle = '#7dffb0'; x.lineWidth = 2; x.beginPath(); x.arc(X(prayPos.x), Z(prayPos.z), 5, 0, 7); x.stroke(); }
        const px = THREE.MathUtils.clamp(X(P.x), 6, S - 6), pz = THREE.MathUtils.clamp(Z(P.z), 6, S - 6);
        dot(px, pz, world.player.heading);
      } else if (L?.id === 'sai') {
        const top = 18, bot = S - 18, zs = z => top + (SAFA_Z - z) / (SAFA_Z - MARWA_Z) * (bot - top);
        x.strokeStyle = 'rgba(255,255,255,.35)'; x.lineWidth = 26; x.beginPath(); x.moveTo(c, top); x.lineTo(c, bot); x.stroke();
        x.strokeStyle = '#1fbf6a'; x.beginPath(); x.moveTo(c, zs(GREEN[0])); x.lineTo(c, zs(GREEN[1])); x.stroke();
        x.fillStyle = '#fff'; x.font = '700 12px Taj, sans-serif'; x.textAlign = 'center';
        x.fillText('الصفا', c, top - 4); x.fillText('المروة', c, bot + 13);
        dot(c + P.x * 1.2, zs(P.z), world.player.heading);
      } else if (L?.map) {
        const [x0, x1, z0, z1] = L.map.bounds, k = (S - 30) / Math.max(x1 - x0, z1 - z0);
        const X = px => c + (px - (x0 + x1) / 2) * k, Z = pz => c + (pz - (z0 + z1) / 2) * k;
        x.fillStyle = 'rgba(255,255,255,.12)'; x.fillRect(X(x0), Z(z0), (x1 - x0) * k, (z1 - z0) * k);
        x.fillStyle = 'rgba(255,255,255,.35)'; for (const b of L.map.boxes) x.fillRect(X(b[0]), Z(b[2]), Math.max(2, (b[1] - b[0]) * k), Math.max(2, (b[3] - b[2]) * k));
        if (m.target) { x.strokeStyle = '#7dffb0'; x.lineWidth = 2.5; x.beginPath(); x.arc(X(m.target.x), Z(m.target.z), 6 + Math.sin(Date.now() / 200) * 1.5, 0, 7); x.stroke(); }
        dot(THREE.MathUtils.clamp(X(P.x), 6, S - 6), THREE.MathUtils.clamp(Z(P.z), 6, S - 6), world.player.heading);
      }
    };
    const dot = (px, pz, h) => {
      x.save(); x.translate(px, pz); x.rotate(Math.PI - h);
      x.fillStyle = '#ffd68c'; x.beginPath(); x.moveTo(0, -7); x.lineTo(5, 5); x.lineTo(-5, 5); x.closePath(); x.fill(); x.restore();
    };
    const id = setInterval(draw, 120); return () => clearInterval(id);
  }, []);
  return <canvas className="mm" ref={ref} width="180" height="180" />;
}
