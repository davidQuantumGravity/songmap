import React from 'react';
import { AbsoluteFill, Audio, interpolate, staticFile, useCurrentFrame } from 'remotion';
import { Background, Overlay, Flash, Slam, WordReveal, Typer, Counter, Tag, Chip, Center, Theme, clamp, ease, beatPulse } from './lib';

const T: Theme = { bg: '#07060f', ink: '#fff', a1: '#a77bff', a2: '#2bf5c8', dim: '#8a8fa6', grid: 'rgba(167,123,255,0.11)' };
const VI = T.a1, MT = T.a2, PK = '#ff5fa2', YL = '#ffd84a', RED = '#ff4d6a';

const NAMES = ['Anscombe', 'Aquinas', 'Archimedes', 'Arendt', 'Aristotle', 'Averroes', 'Avicenna', 'Bacon', 'Banach', 'Beauvoir', 'Bernoulli', 'Bohr', 'Boole', 'Carson', 'Carver', 'Chandrasekhar', 'Confucius', 'Copernicus', 'Dalton', 'Darwin', 'Dewey', 'Dirac', 'Einstein', 'Epicurus', 'Erdos', 'Euclid', 'Euler', 'Faraday', 'Fermat', 'Feynman', 'Galileo', 'Gauss', 'Gibbs', 'Godel', 'Halley', 'Harvey', 'Heisenberg', 'Helmholtz', 'Herschel', 'Hilbert', 'Hubble', 'Huygens', 'James', 'Kepler', 'Kierkegaard', 'Kuhn', 'Lagrange', 'Leibniz', 'Linnaeus', 'Maxwell', 'McClintock', 'Meitner', 'Mencius', 'Mendel', 'Mill', 'Nash', 'Newton', 'Nietzsche', 'Noether', 'Ohm', 'Parfit', 'Pascal', 'Pasteur', 'Pauli', 'Planck', 'Plato', 'Poincare', 'Popper', 'Ptolemy', 'Raman', 'Ramanujan', 'Rawls', 'Sagan', 'Sartre', 'Schrodinger', 'Singer', 'Tesla', 'Turing', 'Volta', 'Zeno'];

const hash = (i: number) => { const x = Math.sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };

const Fade: React.FC<{ at: number; out: number; children: React.ReactNode }> = ({ at, out, children }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const o = Math.min(interpolate(f, [at, at + 8], [0, 1], clamp), interpolate(f, [out - 8, out], [1, 0], clamp));
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};

// Terminal window
const Terminal: React.FC<{ at: number; out: number; lines: { t: number; text: string; color?: string }[] }> = ({ at, out, lines }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const o = Math.min(interpolate(f, [at, at + 10], [0, 1], clamp), interpolate(f, [out - 8, out], [1, 0], clamp));
  return (
    <div style={{ position: 'absolute', left: 260, top: 170, width: 1400, height: 700, opacity: o, borderRadius: 16, background: 'rgba(10,8,22,0.92)', border: `2px solid ${VI}66`, boxShadow: `0 0 60px ${VI}33`, overflow: 'hidden' }}>
      <div style={{ height: 48, background: 'rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', gap: 10, paddingLeft: 20 }}>
        {[RED, YL, MT].map((c) => <div key={c} style={{ width: 16, height: 16, borderRadius: 8, background: c }} />)}
        <div style={{ fontFamily: 'JetBrains Mono', color: '#8a8fa6', fontSize: 20, marginLeft: 20 }}>codex — autonomous goals</div>
      </div>
      <div style={{ padding: '26px 34px' }}>
        {lines.map((l, i) => (
          <Typer key={i} at={l.t} text={l.text} cps={60} caret={i === lines.length - 1} style={{ fontSize: 32, color: l.color || '#d8d4ff', lineHeight: '52px', height: 52 }} />
        ))}
      </div>
    </div>
  );
};

const GoalCard: React.FC<{ at: number; out: number; idx: string; title: string; sub: string; hours: number; color: string }> = ({ at, out, idx, title, sub, hours, color }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const t = f - at;
  const x = interpolate(t, [0, 14], [300, 0], { ...clamp, easing: ease });
  const o = Math.min(interpolate(t, [0, 8], [0, 1], clamp), interpolate(f, [out - 8, out], [1, 0], clamp));
  const prog = interpolate(t, [10, out - at - 10], [0, 1], clamp);
  return (
    <AbsoluteFill style={{ opacity: o, transform: `translateX(${x}px)` }}>
      <div style={{ position: 'absolute', left: 140, top: 250, fontFamily: 'JetBrains Mono', fontSize: 200, fontWeight: 700, color: `${color}33` }}>{idx}</div>
      <div style={{ position: 'absolute', left: 150, top: 470, width: 1100 }}>
        <div style={{ fontFamily: 'Space Grotesk', fontWeight: 700, fontSize: 92, color: '#fff', textShadow: `0 0 30px ${color}`, lineHeight: 1 }}>{title}</div>
        <div style={{ fontFamily: 'JetBrains Mono', fontSize: 36, color: '#c9c6e6', marginTop: 26 }}>{sub}</div>
        <div style={{ marginTop: 50, width: 1000, height: 14, borderRadius: 7, background: 'rgba(255,255,255,0.08)', overflow: 'hidden' }}>
          <div style={{ width: `${prog * 100}%`, height: '100%', background: `linear-gradient(90deg, ${color}, #fff)`, boxShadow: `0 0 20px ${color}` }} />
        </div>
      </div>
      <div style={{ position: 'absolute', right: 140, top: 420, textAlign: 'right' }}>
        <Counter at={at + 6} to={hours} dur={50} style={{ fontSize: 170, fontWeight: 700, color }} />
        <div style={{ fontFamily: 'JetBrains Mono', fontSize: 30, color: '#9a97b8' }}>GOAL-HOURS SO FAR</div>
      </div>
    </AbsoluteFill>
  );
};

const NameRain: React.FC<{ at: number; out: number }> = ({ at, out }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const t = f - at;
  const o = interpolate(f, [out - 10, out], [1, 0], clamp);
  return (
    <AbsoluteFill style={{ opacity: o, overflow: 'hidden' }}>
      {NAMES.map((n, i) => {
        const x = hash(i) * 1760 + 40;
        const speed = 3 + hash(i + 50) * 6;
        const start = hash(i + 99) * 70;
        const y = (t - start) * speed - 60;
        const cf = Math.min(1, Math.hypot((x - 900) / 650, (y - 480) / 300)); const vis = interpolate(t - start, [0, 6], [0, 1], clamp) * cf * cf;
        const big = hash(i + 7) > 0.85;
        return (
          <div key={n} style={{ position: 'absolute', left: x, top: y, fontFamily: 'JetBrains Mono', fontSize: big ? 40 : 24, color: big ? MT : `rgba(200,190,255,${0.35 + hash(i + 3) * 0.4})`, opacity: vis, whiteSpace: 'nowrap', textShadow: big ? `0 0 14px ${MT}` : undefined }}>{n}</div>
        );
      })}
    </AbsoluteFill>
  );
};

const Lanes: React.FC<{ at: number; out: number }> = ({ at, out }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const t = f - at;
  const o = Math.min(interpolate(t, [0, 8], [0, 1], clamp), interpolate(f, [out - 8, out], [1, 0], clamp));
  const cols = [VI, MT, PK, YL, VI, MT, PK];
  return (
    <div style={{ position: 'absolute', left: 120, top: 420, width: 1680, opacity: o }}>
      {cols.map((c, lane) => {
        const appear = interpolate(t, [lane * 5, lane * 5 + 10], [0, 1], clamp);
        return (
          <div key={lane} style={{ position: 'relative', height: 70, marginBottom: 14, opacity: appear }}>
            <div style={{ position: 'absolute', left: 0, top: 18, fontFamily: 'JetBrains Mono', fontSize: 26, color: '#8a8fa6' }}>T{lane + 1}</div>
            <div style={{ position: 'absolute', left: 70, right: 0, top: 30, height: 4, background: 'rgba(255,255,255,0.06)' }} />
            {[...Array(9)].map((_, k) => {
              const w = 80 + hash(lane * 13 + k) * 220;
              const pos = ((k * 260 + hash(lane + k * 3) * 200 - t * (6 + lane * 0.8)) % 2000 + 2000) % 2000 - 200;
              return <div key={k} style={{ position: 'absolute', left: 70 + pos, top: 12, width: w, height: 40, borderRadius: 8, background: `${c}55`, border: `2px solid ${c}`, boxShadow: `0 0 12px ${c}66` }} />;
            })}
          </div>
        );
      })}
    </div>
  );
};

const Receipt: React.FC<{ at: number; out: number; y: number; who: string; what: string; status: string; color: string }> = ({ at, out, y, who, what, status, color }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const t = f - at;
  const x = interpolate(t, [0, 12], [-120, 0], { ...clamp, easing: ease });
  const o = Math.min(interpolate(t, [0, 6], [0, 1], clamp), interpolate(f, [out - 8, out], [1, 0], clamp));
  const stamp = interpolate(t, [10, 16], [2.2, 1], { ...clamp, easing: ease });
  const so = interpolate(t, [10, 13], [0, 1], clamp);
  return (
    <div style={{ position: 'absolute', left: 140, top: y, width: 1640, height: 100, opacity: o, transform: `translateX(${x}px)`, display: 'flex', alignItems: 'center', borderRadius: 12, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', paddingLeft: 30 }}>
      <div style={{ fontFamily: 'JetBrains Mono', fontSize: 34, color: MT, width: 330 }}>{who}</div>
      <div style={{ fontFamily: 'JetBrains Mono', fontSize: 32, color: '#d8d4ff', flex: 1 }}>{what}</div>
      <div style={{ fontFamily: 'Space Grotesk', fontWeight: 700, fontSize: 38, color, border: `3px solid ${color}`, padding: '6px 18px', marginRight: 26, borderRadius: 8, transform: `scale(${stamp}) rotate(-4deg)`, opacity: so, boxShadow: `0 0 18px ${color}66` }}>{status}</div>
    </div>
  );
};

const PhdGrid: React.FC<{ at: number; out: number }> = ({ at, out }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const t = f - at;
  const o = Math.min(interpolate(t, [0, 8], [0, 1], clamp), interpolate(f, [out - 8, out], [1, 0], clamp));
  const hi: Record<number, string> = { 31: 'triboelectric audit', 33: 'flexoelectric harvesting', 49: 'fuel cell / electrolyzer', 50: 'Casimir energy limits', 85: 'eddy-current NDE', 86: 'cathodic protection', 87: 'amperometric biosensor', 103: 'ESD protection', 105: 'induced polarization' };
  return (
    <div style={{ position: 'absolute', left: 130, top: 300, width: 1100, display: 'flex', flexWrap: 'wrap', gap: 10, opacity: o }}>
      {[...Array(90)].map((_, i) => {
        const id = 31 + i;
        const lit = t > i * 1.1 + hash(i) * 8;
        const isHi = id in hi;
        const pulse = isHi ? beatPulse(f + i * 3, 30, 10) : 0;
        return (
          <div key={id} style={{ width: 100, height: 52, borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'JetBrains Mono', fontSize: 20, color: lit ? (isHi ? '#0b0918' : '#e7e3ff') : '#3a3656', background: lit ? (isHi ? MT : `rgba(167,123,255,${0.18 + 0.15 * pulse})`) : 'rgba(255,255,255,0.03)', border: `1px solid ${lit ? VI : '#2a2640'}`, boxShadow: isHi && lit ? `0 0 ${14 + 16 * pulse}px ${MT}` : undefined }}>
            P{String(id).padStart(3, '0')}
          </div>
        );
      })}
    </div>
  );
};

const Atoms: React.FC<{ at: number; out: number }> = ({ at, out }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const t = f - at;
  const o = Math.min(interpolate(t, [0, 10], [0, 1], clamp), interpolate(f, [out - 8, out], [1, 0], clamp));
  const ang = t * 0.02;
  const pts: { x: number; y: number; z: number; c: string }[] = [];
  for (let i = -2; i <= 2; i++) for (let j = -2; j <= 2; j++) for (let k = -2; k <= 2; k++) {
    pts.push({ x: i, y: j, z: k, c: (i + j + k) % 2 === 0 ? MT : VI });
    if (i < 2 && j < 2 && k < 2) pts.push({ x: i + 0.5, y: j + 0.5, z: k + 0.5, c: YL });
  }
  const proj = pts.map((p) => {
    const x1 = p.x * Math.cos(ang) - p.z * Math.sin(ang);
    const z1 = p.x * Math.sin(ang) + p.z * Math.cos(ang);
    const y1 = p.y * Math.cos(0.5) - z1 * Math.sin(0.5);
    const z2 = p.y * Math.sin(0.5) + z1 * Math.cos(0.5);
    const s = 600 / (8 + z2);
    return { sx: 1380 + x1 * s * 1.1, sy: 560 + y1 * s * 1.1, r: 4 + s * 0.12, z: z2, c: p.c };
  }).sort((a, b) => b.z - a.z);
  return (
    <svg width={1920} height={1080} style={{ position: 'absolute', opacity: o }}>
      {proj.map((p, i) => <circle key={i} cx={p.sx} cy={p.sy} r={p.r} fill={p.c} opacity={0.35 + 0.65 * (1 - (p.z + 3) / 6)} style={{ filter: `drop-shadow(0 0 6px ${p.c})` }} />)}
    </svg>
  );
};

const Triality: React.FC<{ at: number; out: number }> = ({ at, out }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const t = f - at;
  const o = Math.min(interpolate(t, [0, 10], [0, 1], clamp), interpolate(f, [out - 8, out], [1, 0], clamp));
  const rot = t * 0.9;
  const cx = 1400, cy = 560, R = 250;
  const nodes = [0, 1, 2].map((k) => ({ x: cx + R * Math.cos(((rot + k * 120 - 90) * Math.PI) / 180), y: cy + R * Math.sin(((rot + k * 120 - 90) * Math.PI) / 180) }));
  const cols = [VI, MT, PK];
  const p = beatPulse(f);
  return (
    <svg width={1920} height={1080} style={{ position: 'absolute', opacity: o }}>
      <circle cx={cx} cy={cy} r={R + 40} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={2} />
      {nodes.map((a, i) => { const b2 = nodes[(i + 1) % 3]; return <line key={i} x1={a.x} y1={a.y} x2={b2.x} y2={b2.y} stroke={cols[i]} strokeWidth={4} opacity={0.7} />; })}
      {nodes.map((a, i) => <circle key={'n' + i} cx={a.x} cy={a.y} r={46 + 8 * p} fill={`${cols[i]}33`} stroke={cols[i]} strokeWidth={4} style={{ filter: `drop-shadow(0 0 14px ${cols[i]})` }} />)}
      {nodes.map((a, i) => <text key={'t' + i} x={a.x} y={a.y + 12} textAnchor="middle" fill="#fff" fontFamily="Space Grotesk" fontWeight={700} fontSize={34}>{['I', 'II', 'III'][i]}</text>)}
      <text x={cx} y={cy + 16} textAnchor="middle" fill="#fff" fontFamily="Space Grotesk" fontWeight={700} fontSize={56}>128</text>
    </svg>
  );
};

export const VideoB: React.FC = () => {
  const f = useCurrentFrame();
  const endFade = interpolate(f, [3600, 3680], [0, 1], clamp);
  return (
    <AbsoluteFill style={{ background: T.bg }}>
      <Audio src={staticFile('track_B.wav')} />
      <Background theme={T} intensity={f > 240 ? 1 : 0.3} variant="dots" />

      {/* INTRO 0-240 */}
      <Terminal at={0} out={240} lines={[
        { t: 8, text: '$ codex goal list --active', color: '#8a8fa6' },
        { t: 40, text: '● geometric electrostatics   EGC-001 → EGC-091' },
        { t: 64, text: '● macroscopic media platform  MEMS · TE · plasmonic' },
        { t: 88, text: '● PhD research portfolio      P031 → P120' },
        { t: 112, text: '● force-measurement modeling  apparatus → signal' },
        { t: 136, text: '● E8(−24) triality           3 generations?' },
        { t: 175, text: '$ spawn subagents --until-done', color: MT },
      ]} />
      <Center><Slam at={240} out={360} size={260} glow={VI}>THE SWARM</Slam></Center>
      <AbsoluteFill style={{ top: 700 }}>
        <Center><WordReveal at={262} out={360} text="autonomous AI research agents · running for days" size={44} every={3} color="#c9c6e6" style={{ justifyContent: 'center' }} mono /></Center>
      </AbsoluteFill>

      {/* GOALS 360-960 */}
      <Tag at={360} out={1080} num="01" title="FIVE LONG-RUNNING GOALS" color={VI} />
      <GoalCard at={360} out={480} idx="01" title="Geometric Electrostatics" sub="91-task plan · multi-conductor capacitance → simulation" hours={229} color={VI} />
      <GoalCard at={480} out={600} idx="02" title="Macroscopic Media" sub="MEMS · thermoelectrics · plasmonics · micromorphic" hours={156} color={MT} />
      <GoalCard at={600} out={720} idx="03" title="PhD Portfolio ×90" sub="thesis-scale projects P031–P120, one at a time" hours={527} color={PK} />
      <GoalCard at={720} out={840} idx="04" title="Force-Measurement Models" sub="apparatus · instrument response · uncertainty" hours={171} color={YL} />
      <GoalCard at={840} out={960} idx="05" title="E8 Triality Theory" sub="three fermion generations from one 128?" hours={47} color={VI} />
      <Center>
        <Typer at={968} out={1078} text="> who is actually doing the work?" cps={26} style={{ fontSize: 56, color: MT }} />
      </Center>

      {/* AGENTS 1080-2040 */}
      <Tag at={1080} out={2040} num="02" title="THE AGENTS" color={MT} />
      <NameRain at={1080} out={1270} />
      <Center>
        <Counter at={1085} out={1270} to={135} dur={60} style={{ fontSize: 300, fontWeight: 700, color: '#fff', textShadow: `0 0 50px ${VI}` }} />
        <Slam at={1090} out={1270} size={52} mono color={MT} from={1.2}>SUBAGENTS SPAWNED · MON → SUN</Slam>
        <WordReveal at={1150} out={1270} text="each one named after a great thinker" size={40} every={3} color="#c9c6e6" style={{ marginTop: 30, justifyContent: 'center' }} />
      </Center>

      <AbsoluteFill style={{ padding: '200px 120px' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 30 }}>
          <Slam at={1270} out={1440} size={64} mono color="#9a97b8">PEAK:</Slam>
          <Slam at={1280} out={1440} size={150} glow={MT}>7 THREADS</Slam>
          <Slam at={1295} out={1440} size={64} mono color="#9a97b8">IN PARALLEL</Slam>
        </div>
      </AbsoluteFill>
      <Lanes at={1285} out={1440} />

      <AbsoluteFill style={{ padding: '170px 140px' }}>
        <Slam at={1440} out={1680} size={78} glow={VI}>EVERY CLAIM GETS A RECEIPT</Slam>
      </AbsoluteFill>
      <Receipt at={1465} out={1680} y={320} who="FERMAT" what="source review of a policy profile" status="ACCEPTED" color={MT} />
      <Receipt at={1490} out={1680} y={440} who="EULER" what="3 independent derivations, blind" status="AGREE" color={MT} />
      <Receipt at={1515} out={1680} y={560} who="GAUSS 2nd" what="math frozen before seeing results" status="FROZEN" color={VI} />
      <Receipt at={1540} out={1680} y={680} who="FEYNMAN" what="source comparison not complete" status="HOLD" color={YL} />
      <Receipt at={1565} out={1680} y={800} who="LINNAEUS" what="method check failed — result sealed" status="NEGATIVE" color={RED} />

      <AbsoluteFill style={{ padding: '190px 140px' }}>
        <Slam at={1680} out={2040} size={88} glow={MT}>RULES OF THE SWARM</Slam>
        <div style={{ marginTop: 60, display: 'flex', flexDirection: 'column', gap: 34 }}>
          <WordReveal at={1710} out={2040} text="01  Freeze the work order before running anything" size={46} every={2} accent={MT} accentWords={['01', 'Freeze']} />
          <WordReveal at={1755} out={2040} text="02  An independent reviewer for every claim" size={46} every={2} accent={MT} accentWords={['02', 'independent']} />
          <WordReveal at={1800} out={2040} text="03  Keep the failures, nulls and negatives" size={46} every={2} accent={MT} accentWords={['03', 'failures,']} />
          <WordReveal at={1845} out={2040} text="04  Passing tests ≠ validated physics" size={46} every={2} accent={PK} accentWords={['04', '≠']} />
        </div>
      </AbsoluteFill>

      {/* BREAK 2040-2160 */}
      <Center><Slam at={2050} out={2158} size={120} glow={VI} from={1.3}>SO WHAT CAME OUT?</Slam></Center>

      {/* RESULTS 2160-3120 */}
      <Tag at={2160} out={3120} num="03" title="OUTPUT" color={PK} />
      <AbsoluteFill style={{ padding: '170px 130px' }}>
        <Slam at={2160} out={2400} size={84} glow={PK}>90-PROJECT PhD PORTFOLIO</Slam>
      </AbsoluteFill>
      <PhdGrid at={2165} out={2400} />
      <AbsoluteFill style={{ left: 1300, top: 320, width: 520 }}>
        {[['P031', 'triboelectric audit'], ['P050', 'Casimir energy limits'], ['P085', 'eddy-current NDE'], ['P087', 'amperometric biosensor'], ['P103', 'ESD protection']].map(([id, n], i) => (
          <div key={id} style={{ marginBottom: 26 }}>
            <Slam at={2230 + i * 15} out={2400} size={34} mono color={MT} from={1.15}>{id}</Slam>
            <Slam at={2233 + i * 15} out={2400} size={40} color="#fff" from={1.15}>{n}</Slam>
          </div>
        ))}
      </AbsoluteFill>

      <Atoms at={2400} out={2580} />
      <AbsoluteFill style={{ padding: '260px 130px', width: 900 }}>
        <Slam at={2400} out={2580} size={92} glow={MT}>QUANTUM</Slam>
        <Slam at={2410} out={2580} size={92} glow={MT}>ESPRESSO</Slam>
        <Slam at={2420} out={2580} size={92} color={MT}>INSTALLED</Slam>
        <WordReveal at={2450} out={2580} text="first job: reproduce published semiconductor results — calibrate before you trust it" size={36} every={2} color="#c9c6e6" style={{ marginTop: 34 }} />
      </AbsoluteFill>

      <Triality at={2580} out={2760} />
      <AbsoluteFill style={{ padding: '240px 130px', width: 980 }}>
        <Slam at={2580} out={2760} size={80} glow={PK}>E8(−24) TRIALITY</Slam>
        <WordReveal at={2600} out={2760} text="Can one 128 give three complete Standard-Model generations — no extra copies?" size={44} every={2} color="#fff" style={{ marginTop: 30 }} accent={PK} accentWords={['three']} />
        <WordReveal at={2670} out={2760} text="adversarial critique → vetted → corrected" size={34} every={3} color={MT} style={{ marginTop: 34 }} mono />
      </AbsoluteFill>

      <AbsoluteFill style={{ padding: '200px 130px' }}>
        <Slam at={2760} out={2940} size={84} glow={MT}>MACROSCOPIC MEDIA PLATFORM</Slam>
        <WordReveal at={2780} out={2940} text="one typed contract for material, state and response — across three production lanes" size={40} every={2} color="#c9c6e6" style={{ marginTop: 26, maxWidth: 1500 }} />
      </AbsoluteFill>
      <Chip text="MEMS · electrode-driven" at={2810} out={2940} x={130} y={470} color={VI} size={40} />
      <Chip text="THERMOELECTRIC modules" at={2830} out={2940} x={130} y={570} color={MT} size={40} />
      <Chip text="PLASMONIC · polaritonic" at={2850} out={2940} x={130} y={670} color={PK} size={40} />
      <Chip text="+ micromorphic · nonlocal · quantum effective-mode extensions" at={2875} out={2940} x={130} y={790} color={YL} size={34} />

      <AbsoluteFill style={{ padding: '200px 130px' }}>
        <Slam at={2940} out={3120} size={52} mono color="#9a97b8">CUMULATIVE, ACROSS THE FIVE GOALS</Slam>
        <div style={{ display: 'flex', gap: 110, marginTop: 70 }}>
          <div>
            <Counter at={2955} out={3120} to={970} dur={50} suffix="M" style={{ fontSize: 190, fontWeight: 700, color: '#fff', textShadow: `0 0 40px ${VI}` }} />
            <Slam at={2960} out={3120} size={38} mono color={VI} from={1.1}>TOKENS PROCESSED</Slam>
          </div>
          <div>
            <Counter at={2975} out={3120} to={1130} dur={50} style={{ fontSize: 190, fontWeight: 700, color: '#fff', textShadow: `0 0 40px ${MT}` }} />
            <Slam at={2980} out={3120} size={38} mono color={MT} from={1.1}>GOAL-HOURS</Slam>
          </div>
          <div>
            <Counter at={2995} out={3120} to={135} dur={40} style={{ fontSize: 190, fontWeight: 700, color: '#fff', textShadow: `0 0 40px ${PK}` }} />
            <Slam at={3000} out={3120} size={38} mono color={PK} from={1.1}>AGENTS THIS WEEK</Slam>
          </div>
        </div>
      </AbsoluteFill>

      {/* BREAKDOWN 3120-3360 */}
      <Center style={{ padding: '0 200px' }}>
        <WordReveal at={3125} out={3360} text="I set the goals and the guardrails." size={64} every={4} color="#fff" style={{ justifyContent: 'center' }} accent={VI} accentWords={['goals', 'guardrails.']} />
        <div style={{ height: 30 }} />
        <WordReveal at={3185} out={3360} text="The swarm does the grinding." size={64} every={4} color="#fff" style={{ justifyContent: 'center' }} accent={MT} accentWords={['grinding.']} />
        <div style={{ height: 30 }} />
        <WordReveal at={3245} out={3360} text="Every claim still gets checked." size={64} every={4} color="#fff" style={{ justifyContent: 'center' }} accent={PK} accentWords={['checked.']} />
      </Center>

      {/* OUTRO 3360-3690 */}
      <Center>
        <Slam at={3360} out={3480} size={70} mono color={MT}>135 AGENTS · 5 GOALS · 7 THREADS</Slam>
        <Slam at={3480} out={3690} size={64} mono color={MT} from={1.2}>WEEK OF OCT 13 · 2026</Slam>
        <div style={{ height: 24 }} />
        <Slam at={3488} out={3690} size={210} glow={VI}>THE SWARM</Slam>
        <div style={{ height: 30 }} />
        <WordReveal at={3520} out={3690} text="David Chester" size={40} color="#9a97b8" every={3} style={{ justifyContent: 'center' }} />
      </Center>

      <Flash at={[240, 1080, 2160, 3360, 3480]} color="#e6dcff" />
      <Overlay />
      <AbsoluteFill style={{ background: '#000', opacity: endFade }} />
    </AbsoluteFill>
  );
};
