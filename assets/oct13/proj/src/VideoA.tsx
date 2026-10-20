import React from 'react';
import { AbsoluteFill, Audio, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame, Img } from 'remotion';
import { Background, Overlay, Flash, Slam, WordReveal, Typer, Counter, Shot, Tag, Chip, Center, Glitch, Theme, clamp, ease, beatPulse } from './lib';

const T: Theme = { bg: '#06080d', ink: '#fff', a1: '#ffb23d', a2: '#29d3ff', dim: '#8a94a6', grid: 'rgba(41,211,255,0.10)' };
const AMB = T.a1, CY = T.a2, GRN = '#3dffa2', RED = '#ff3b5c';

// ---------- custom pieces ----------
const Scope: React.FC<{ pulses: number[]; opacity?: number }> = ({ pulses, opacity = 1 }) => {
  const f = useCurrentFrame();
  const pts: string[] = [];
  for (let x = 0; x <= 1920; x += 4) {
    const tt = f - ((1920 - x) / 1920) * 45;
    let v = 0;
    for (const p of pulses) if (tt >= p) v += Math.exp(-(tt - p) / 2.2) * (tt - p < 0.15 ? (tt - p) / 0.15 : 1);
    const noise = Math.sin(x * 0.9 + f * 3.1) * 2 + Math.sin(x * 0.23 + f) * 1.5;
    pts.push(`${x},${760 - v * 420 + noise}`);
  }
  return (
    <svg width={1920} height={1080} style={{ position: 'absolute', opacity }}>
      {[...Array(11)].map((_, i) => <line key={'v' + i} x1={i * 192} x2={i * 192} y1={0} y2={1080} stroke="rgba(61,255,162,0.10)" />)}
      {[...Array(9)].map((_, i) => <line key={'h' + i} y1={i * 135} y2={i * 135} x1={0} x2={1920} stroke="rgba(61,255,162,0.10)" />)}
      <polyline points={pts.join(' ')} fill="none" stroke={GRN} strokeWidth={4} style={{ filter: `drop-shadow(0 0 8px ${GRN})` }} />
    </svg>
  );
};

const DotField: React.FC<{ at: number; out: number; from: number; to: number; color: string }> = ({ at, out, from, to, color }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const p = interpolate(f, [at, out], [0, 1], { ...clamp, easing: ease });
  const size = from * Math.pow(to / from, p);
  const o = Math.min(interpolate(f, [at, at + 10], [0, 0.85], clamp), interpolate(f, [out - 10, out], [0.85, 0], clamp));
  return (
    <AbsoluteFill style={{ opacity: o, backgroundImage: `radial-gradient(circle, ${color} ${Math.max(0.6, size * 0.22)}px, transparent ${Math.max(0.9, size * 0.26)}px)`, backgroundSize: `${size}px ${size}px`, backgroundPosition: 'center', maskImage: 'radial-gradient(ellipse at center, black 30%, transparent 75%)' }} />
  );
};

const Gauge: React.FC<{ at: number; out: number; value: number; max: number; target: number }> = ({ at, out, value, max, target }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const v = interpolate(f, [at + 10, at + 80], [0, value], { ...clamp, easing: ease });
  const jitter = f > at + 80 ? Math.sin(f * 1.7) * 2 : 0;
  const ang = (x: number) => Math.PI * (1 - x / max);
  const R = 300, cx = 400, cy = 360;
  const pt = (x: number, r = R) => [cx + r * Math.cos(ang(x)), cy - r * Math.sin(ang(x))];
  const [nx, ny] = pt(v + jitter, R - 30);
  const [tx1, ty1] = pt(target, R - 50); const [tx2, ty2] = pt(target, R + 30);
  const arc = (a: number, b2: number, col: string, w: number) => {
    const [x1, y1] = pt(a); const [x2, y2] = pt(b2);
    return <path d={`M ${x1} ${y1} A ${R} ${R} 0 0 1 ${x2} ${y2}`} stroke={col} strokeWidth={w} fill="none" strokeLinecap="round" />;
  };
  const o = Math.min(interpolate(f, [at, at + 8], [0, 1], clamp), interpolate(f, [out - 8, out], [1, 0], clamp));
  const hit = v >= target;
  return (
    <svg width={800} height={460} style={{ position: 'absolute', left: 120, top: 330, opacity: o }}>
      {arc(0, max, 'rgba(255,255,255,0.12)', 34)}
      {arc(0, Math.max(0.01, v), hit ? AMB : CY, 34)}
      <line x1={tx1} y1={ty1} x2={tx2} y2={ty2} stroke={RED} strokeWidth={6} />
      <text x={tx2 + 10} y={ty2 - 6} fill={RED} fontFamily="JetBrains Mono" fontSize={26}>300</text>
      <line x1={cx} y1={cy} x2={nx} y2={ny} stroke="#fff" strokeWidth={8} strokeLinecap="round" style={{ filter: 'drop-shadow(0 0 10px #fff)' }} />
      <circle cx={cx} cy={cy} r={16} fill="#fff" />
      <text x={cx} y={cy + 80} textAnchor="middle" fill={hit ? AMB : '#fff'} fontFamily="Space Grotesk" fontWeight={700} fontSize={84}>{v.toFixed(1)}</text>
      <text x={cx} y={cy + 120} textAnchor="middle" fill="#9aa4b6" fontFamily="JetBrains Mono" fontSize={28}>MV/m · oxide RMS field</text>
    </svg>
  );
};

const Chain: React.FC<{ at: number; out: number; y: number; label: string; color: string; items: string[]; strike?: boolean }> = ({ at, out, y, label, color, items, strike }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const t = f - at;
  const o = interpolate(f, [out - 8, out], [1, 0], clamp);
  const sw = strike ? interpolate(t, [40, 55], [0, 1], clamp) : 0;
  return (
    <div style={{ position: 'absolute', left: 120, top: y, opacity: o, display: 'flex', alignItems: 'center', gap: 22 }}>
      <div style={{ width: 170, fontFamily: 'JetBrains Mono', fontSize: 30, color, letterSpacing: '0.15em' }}>{label}</div>
      {items.map((it, i) => {
        const a = interpolate(t - i * 8, [0, 8], [0, 1], clamp);
        return (
          <React.Fragment key={i}>
            {i > 0 ? <div style={{ opacity: a, color, fontSize: 44 }}>→</div> : null}
            <div style={{ opacity: a, transform: `translateY(${(1 - a) * 20}px)`, padding: '18px 28px', border: `3px solid ${color}`, borderRadius: 12, fontFamily: 'Space Grotesk', fontWeight: 700, fontSize: 40, color: '#fff', background: `${color}1f`, boxShadow: strike ? undefined : `0 0 24px ${color}66` }}>{it}</div>
          </React.Fragment>
        );
      })}
      {strike ? <div style={{ position: 'absolute', left: 190, right: 0, top: '50%', height: 5, background: RED, transform: `scaleX(${sw})`, transformOrigin: 'left', boxShadow: `0 0 12px ${RED}` }} /> : null}
    </div>
  );
};

const CutLabel: React.FC<{ text: string; color: string }> = ({ text, color }) => (
  <div style={{ position: 'absolute', left: 90, bottom: 90, fontFamily: 'Space Grotesk', fontWeight: 700, fontSize: 86, color: '#fff', textShadow: `0 0 30px ${color}`, background: 'rgba(0,0,0,0.55)', padding: '8px 26px', borderLeft: `10px solid ${color}` }}>{text}</div>
);

const Fade: React.FC<{ at: number; out: number; children: React.ReactNode }> = ({ at, out, children }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const o = Math.min(interpolate(f, [at, at + 8], [0, 1], clamp), interpolate(f, [out - 8, out], [1, 0], clamp));
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};

const Column: React.FC<{ at: number; x: number; color: string; title: string; lines: string[] }> = ({ at, x, color, title, lines }) => {
  const f = useCurrentFrame();
  const t = f - at;
  const o = interpolate(t, [0, 8], [0, 1], clamp);
  const y = interpolate(t, [0, 12], [60, 0], { ...clamp, easing: ease });
  return (
    <div style={{ position: 'absolute', left: x, top: 360, width: 560, opacity: o, transform: `translateY(${y}px)` }}>
      <div style={{ height: 6, width: 120, background: color, boxShadow: `0 0 20px ${color}` }} />
      <div style={{ fontFamily: 'Space Grotesk', fontWeight: 700, fontSize: 72, color: '#fff', marginTop: 22 }}>{title}</div>
      {lines.map((l, i) => (
        <div key={i} style={{ fontFamily: 'JetBrains Mono', fontSize: 32, color: '#c9d1dd', marginTop: 20, opacity: interpolate(t - 10 - i * 6, [0, 6], [0, 1], clamp) }}>{l}</div>
      ))}
    </div>
  );
};

// ---------- main composition ----------
export const VideoA: React.FC = () => {
  const f = useCurrentFrame();
  const zaps = [120, 135, 150, 165, 180, 195, 240, 255, 270, 285, 300, 315, 330, 345, 360, 375, 390, 405];
  const endFade = interpolate(f, [4440, 4520], [0, 1], clamp);
  const cuts: [string, string][] = [
    ['dash_two_sensor_plots_preview.png', 'TWO-PLOT VIEW'],
    ['dash_baseline_zero_preview.png', 'BASELINE ZERO · C₀'],
    ['dash_plot_navigation_preview.png', 'PAN · ZOOM · FIT'],
    ['dash_notes_timeline_preview.png', 'TIMESTAMPED NOTES'],
    ['dash_com5_connection_diagnostics_preview.png', 'LIVE COM5 DIAGNOSTICS'],
    ['dash_sensor_off_warning_preview.png', 'SENSOR-OFF DETECTION'],
  ];
  return (
    <AbsoluteFill style={{ background: T.bg }}>
      <Audio src={staticFile('track_A.wav')} />
      <Background theme={T} intensity={f > 240 ? 1 : 0.3} />

      {/* ================= COLD OPEN 0-240 ================= */}
      <Fade at={0} out={420}><Scope pulses={zaps} opacity={f < 240 ? 0.9 : 0.35} /></Fade>
      <Center>
        <Typer text="WEEK OF OCT 13, 2026" at={12} cps={28} out={118} style={{ fontSize: 34, color: GRN, letterSpacing: '0.25em' }} />
        <Slam at={60} out={118} size={150} glow={CY}>ONE WEEK.</Slam>
        <WordReveal text="THE BENCH. THE FIELDS. THE THRUSTER." at={122} out={236} every={14} size={78} accent={AMB} accentWords={['BENCH', 'FIELDS', 'THRUSTER']} style={{ justifyContent: 'center', maxWidth: 1500 }} />
      </Center>

      {/* ================= ACT 1: THE BENCH 240-2040 ================= */}
      <Tag at={240} out={2040} num="01" title="THE BENCH" color={AMB} />
      {/* pulser specs 240-420 */}
      <AbsoluteFill style={{ padding: '200px 120px' }}>
        <Slam at={240} out={420} size={260} glow={AMB} style={{ color: '#fff' }}>20 kV</Slam>
        <div style={{ display: 'flex', gap: 50, marginTop: 30 }}>
          <Slam at={262} out={420} size={74} color={CY} mono>&lt;10 ns RISE</Slam>
          <Slam at={285} out={420} size={74} color={CY} mono>UP TO 1 kHz</Slam>
        </div>
        <WordReveal at={315} out={420} text="New HV pulser — wired up and scoped with Jarod" size={46} color="#cfd6e2" every={4} style={{ marginTop: 40 }} accent={AMB} accentWords={['Jarod']} />
      </AbsoluteFill>

      {/* signal chain 420-600 */}
      <AbsoluteFill style={{ padding: '170px 120px' }}>
        <Slam at={420} out={600} size={80} glow={AMB}>NEW SIGNAL CHAIN</Slam>
      </AbsoluteFill>
      <Chain at={440} out={600} y={380} label="BEFORE" color="#8a94a6" items={['ZVS driver', 'AC transformer', 'CW multiplier', 'thruster']} strike />
      <Chain at={490} out={600} y={620} label="NOW" color={AMB} items={['20 kV pulser', 'CW multiplier', 'thruster']} />
      <AbsoluteFill style={{ top: 860, left: 120 }}>
        <WordReveal at={530} out={600} text="Edges of roughly 5–10 ns on the oscilloscope" size={38} every={4} color={CY} mono />
      </AbsoluteFill>

      {/* what we tested 600-780 */}
      <AbsoluteFill style={{ padding: '170px 120px' }}>
        <Slam at={600} out={780} size={80} glow={CY}>WHAT WE TESTED</Slam>
        <div style={{ display: 'flex', gap: 80, marginTop: 70 }}>
          <div>
            <Slam at={620} out={780} size={130} color="#fff" glow={AMB}>5 kV</Slam>
            <Slam at={625} out={780} size={30} mono color="#9aa4b6" from={1.1}>NOMINAL AMPLITUDE</Slam>
          </div>
          <div>
            <Slam at={640} out={780} size={130} color="#fff" glow={AMB}>200 Hz</Slam>
            <Slam at={645} out={780} size={30} mono color="#9aa4b6" from={1.1}>REP RATE</Slam>
          </div>
          <div>
            <Slam at={660} out={780} size={130} color="#fff" glow={AMB}>AIR</Slam>
            <Slam at={665} out={780} size={30} mono color="#9aa4b6" from={1.1}>DIAGNOSTIC RUNS</Slam>
          </div>
        </div>
      </AbsoluteFill>
      <Chip text="box OFF" at={690} out={780} x={120} y={760} color="#8a94a6" size={36} />
      <Chip text="box ON · no HV" at={705} out={780} x={380} y={760} color={CY} size={36} />
      <Chip text="5 kV ON / OFF" at={720} out={780} x={790} y={760} color={AMB} size={36} />
      <AbsoluteFill style={{ top: 870, left: 120 }}>
        <WordReveal at={730} out={780} text="one change at a time" size={34} every={4} color="#9aa4b6" mono />
      </AbsoluteFill>

      {/* problem 780-960 */}
      <Shot src="wiring.png" at={790} out={960} x={1060} y={220} w={760} h={500} fit="cover" zoom={[1.0, 1.15]} from="right" border={RED + '66'} />
      <AbsoluteFill style={{ padding: '190px 120px' }}>
        <Slam at={780} out={960} size={100} color={RED} glow={RED}>THE PROBLEM:</Slam>
        <Slam at={795} out={960} size={84} color="#fff">pulser vs. DAQ</Slam>
        <div style={{ height: 40 }} />
        <Glitch text="ADS1115 not found at 0x48" at={815} out={960} size={46} />
      </AbsoluteFill>
      <Chip text="I²C dropouts" at={850} out={960} x={120} y={640} color={RED} />
      <Chip text="serial gaps" at={865} out={960} x={400} y={640} color={RED} />
      <Chip text="clock jumps" at={880} out={960} x={640} y={640} color={RED} />
      <Chip text="drift" at={895} out={960} x={120} y={720} color={RED} />

      {/* before / after 960-1140 */}
      <AbsoluteFill style={{ padding: '150px 120px 0' }}>
        <Slam at={960} out={1140} size={84} glow={AMB}>DAQ: TORN DOWN &amp; REBUILT</Slam>
      </AbsoluteFill>
      <Shot src="before.jpg" at={970} out={1140} x={160} y={300} w={720} h={600} from="left" border={RED + '99'} label="BEFORE · breadboard + bench supply" labelColor="#ffb3c0" zoom={[1.0, 1.12]} />
      <Shot src="after.jpg" at={1020} out={1140} x={1040} y={300} w={720} h={600} from="right" border={GRN + '99'} label="AFTER · soldered board · batteries + buck" labelColor="#b6ffd9" zoom={[1.0, 1.12]} objPos="center 60%" />

      {/* fixes 1140-1320 */}
      <AbsoluteFill style={{ padding: '170px 120px' }}>
        <Slam at={1140} out={1320} size={92} glow={GRN} color={GRN}>THE FIXES</Slam>
        <div style={{ marginTop: 50, display: 'flex', flexDirection: 'column', gap: 26 }}>
          <WordReveal at={1160} out={1320} text="01  Breadboard → soldered perfboard" size={46} every={3} accent={GRN} accentWords={['01']} />
          <WordReveal at={1180} out={1320} text="02  Bench supply → 2× 9 V batteries + buck converter" size={46} every={3} accent={GRN} accentWords={['02']} />
          <WordReveal at={1200} out={1320} text="03  Sensor 1.7 m from the pulser, cables taped down" size={46} every={3} accent={GRN} accentWords={['03']} />
          <WordReveal at={1220} out={1320} text="04  Long USB extension removed" size={46} every={3} accent={GRN} accentWords={['04']} />
          <WordReveal at={1240} out={1320} text="05  Logger auto-recovers ADC dropouts" size={46} every={3} accent={GRN} accentWords={['05']} />
        </div>
      </AbsoluteFill>

      {/* dashboard hero 1320-1500 */}
      <Shot src="dash_live_displacement_preview.png" at={1320} out={1500} x={820} y={150} w={1000} h={800} fit="cover" objPos="top" zoom={[1.0, 1.1]} pan={[0, 0, 0, -6]} from="right" border={CY + '88'} rot={-2} />
      <AbsoluteFill style={{ padding: '220px 100px', width: 760 }}>
        <Slam at={1320} out={1500} size={92} glow={CY}>REAL-TIME</Slam>
        <Slam at={1332} out={1500} size={92} glow={CY}>DAQ VIEWER</Slam>
        <div style={{ height: 40 }} />
        <WordReveal at={1355} out={1500} text="instant feedback while we sweep settings" size={38} color="#9aa4b6" every={4} />
      </AbsoluteFill>
      <Chip text="RAW ADC COUNTS" at={1385} out={1500} x={100} y={640} color={CY} />
      <Chip text="DISPLACEMENT · µm" at={1400} out={1500} x={100} y={710} color={CY} />
      <Chip text="FORCE · µN" at={1415} out={1500} x={100} y={780} color={AMB} />
      <Chip text="50 ms REFRESH" at={1430} out={1500} x={100} y={850} color={GRN} />

      {/* feature cuts 1500-1680, 30 frames each */}
      {cuts.map(([src, label], i) => (
        <Sequence key={i} from={1500 + i * 30} durationInFrames={30} layout="none">
          <AbsoluteFill>
            <Img src={staticFile(src)} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top', transform: `scale(${1.05 + 0.02 * i})`, filter: 'brightness(0.8)' }} />
            <CutLabel text={label} color={i % 2 ? AMB : CY} />
          </AbsoluteFill>
        </Sequence>
      ))}

      {/* result 1680-1800 */}
      <Shot src="dash_deployed.png" at={1680} out={1800} x={1000} y={240} w={820} h={570} fit="cover" objPos="top" zoom={[1.0, 1.08]} from="right" border={GRN + '88'} />
      <AbsoluteFill style={{ padding: '230px 100px' }}>
        <Slam at={1680} out={1800} size={150} color={GRN} glow={GRN}>CLEAN.</Slam>
        <Typer at={1692} out={1800} text={'R083 · 1,616 samples\n@ 100 Hz · 0 gaps'} cps={40} style={{ fontSize: 40, color: '#d6ffe9', marginTop: 30 }} />
      </AbsoluteFill>
      <AbsoluteFill style={{ left: 100, top: 800 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 20 }}>
          <Counter at={1710} out={1800} from={37} to={167} dur={45} style={{ fontSize: 110, fontWeight: 700, color: GRN }} />
          <Slam at={1710} out={1800} size={40} mono color="#cfd6e2" from={1.2}>SOFTWARE TESTS PASSING</Slam>
        </div>
      </AbsoluteFill>

      {/* notebook 1800-1920 */}
      <AbsoluteFill style={{ padding: '230px 120px' }}>
        <Slam at={1800} out={1920} size={96} glow={AMB}>AUTO LAB NOTEBOOK</Slam>
        <div style={{ display: 'flex', gap: 90, marginTop: 70 }}>
          <div>
            <Slam at={1812} out={1920} size={88} color={CY} mono>R073→R085</Slam>
            <Slam at={1815} out={1920} size={32} color="#9aa4b6" mono from={1.1}>DAQ RUNS LOGGED</Slam>
          </div>
          <div>
            <Counter at={1825} out={1920} to={980946} dur={50} style={{ fontSize: 88, fontWeight: 700, color: '#fff' }} />
            <Slam at={1825} out={1920} size={32} color="#9aa4b6" mono from={1.1}>DATA ROWS REVIEWED</Slam>
          </div>
          <div>
            <Counter at={1840} out={1920} to={42} dur={30} style={{ fontSize: 88, fontWeight: 700, color: AMB }} />
            <Slam at={1840} out={1920} size={32} color="#9aa4b6" mono from={1.1}>BENCH NOTES</Slam>
          </div>
        </div>
      </AbsoluteFill>

      {/* Jeremiah 1920-2040 */}
      <Center>
        <Slam at={1920} out={2040} size={44} mono color="#9aa4b6" from={1.2}>SHOUT-OUT</Slam>
        <div style={{ height: 20 }} />
        <Slam at={1928} out={2040} size={130} glow={AMB}>THANK YOU,</Slam>
        <Slam at={1940} out={2040} size={150} glow={AMB} color={AMB}>JEREMIAH</Slam>
        <div style={{ height: 30 }} />
        <WordReveal at={1960} out={2040} text="for the quad-eutectic solder — really nice to work with" size={40} every={4} color="#cfd6e2" style={{ justifyContent: 'center' }} />
      </Center>

      <Sequence from={840} layout="none">
      {/* ================= BREAK 1200-1320 ================= */}
      <Center>
        <Typer at={1205} out={1318} text="> meanwhile, in simulation..." cps={22} style={{ fontSize: 56, color: CY }} />
      </Center>

      {/* ================= ACT 2: THE FIELDS 1320-2280 ================= */}
      <Tag at={1320} out={2280} num="02" title="THE FIELDS" color={CY} />
      <Center><Slam at={1320} out={1382} size={220} glow={CY}>THE FIELDS</Slam></Center>
      <Shot src="k_potential.png" at={1382} out={1500} x={100} y={260} w={1720} h={600} fit="contain" bg="#fff" zoom={[1.0, 1.05]} border={CY + '88'} />
      <AbsoluteFill style={{ padding: '150px 120px' }}>
        <WordReveal at={1388} out={1500} text="−500 V pad · 25 µm Kapton · grounded plate" size={50} every={5} accent={AMB} accentWords={['−500']} />
      </AbsoluteFill>
      <Chip text="SectorSim · electrostatics" at={1400} out={1500} x={120} y={930} color={CY} />

      <Shot src="k_wrap.png" at={1500} out={1680} x={560} y={190} w={1280} h={760} fit="contain" bg="#fff" zoom={[1.0, 1.12]} pan={[0, 0, 4, 0]} border={CY + '88'} from="right" />
      <AbsoluteFill style={{ padding: '260px 100px', width: 520 }}>
        <Slam at={1505} out={1680} size={78} glow={CY}>FIELDS</Slam>
        <Slam at={1520} out={1680} size={78} glow={CY}>WRAP</Slam>
        <Slam at={1535} out={1680} size={78} glow={AMB} color={AMB}>AROUND</Slam>
        <WordReveal at={1560} out={1680} text="from the charge sites to the backside of the ground plate" size={34} color="#cfd6e2" every={4} style={{ marginTop: 30 }} />
      </AbsoluteFill>

      <DotField at={1680} out={1860} from={180} to={6} color={CY} />
      <Center>
        <Counter at={1700} out={1860} from={1} to={2869636} dur={110} style={{ fontSize: 190, fontWeight: 700, color: '#fff', textShadow: `0 0 40px ${CY}` }} />
        <Slam at={1700} out={1860} size={56} mono color={CY} from={1.2}>CHARGE SITES SIMULATED</Slam>
        <WordReveal at={1760} out={1860} text="4 → 9 → full lattice at 25 · 50 · 75 · 100% coverage" size={36} every={5} color="#cfd6e2" style={{ marginTop: 40, justifyContent: 'center' }} mono />
      </Center>

      <Fade at={1860} out={2040}>
        <div style={{ position: 'absolute', left: 80, top: 190, width: 1180, height: 664, borderRadius: 14, overflow: 'hidden', border: `2px solid ${CY}88`, boxShadow: `0 0 40px ${CY}55`, background: '#fff' }}>
          <Sequence from={1860} durationInFrames={180} layout="none">
            <OffthreadVideo src={staticFile('m_lattice.mp4')} style={{ width: '100%', height: '100%', objectFit: 'cover' }} muted playbackRate={1.3} />
          </Sequence>
        </div>
        <AbsoluteFill style={{ left: 1310, top: 210, width: 560 }}>
          <Slam at={1870} out={2040} size={44} mono color="#9aa4b6" from={1.1}>CHARGE → DISCONNECT → HOLD</Slam>
          <Counter at={1890} out={2040} to={56} dur={30} style={{ fontSize: 120, fontWeight: 700, color: '#fff', marginTop: 40 }} suffix=" movies" />
          <Counter at={1915} out={2040} to={17.1} decimals={1} dur={30} style={{ fontSize: 96, fontWeight: 700, color: CY, marginTop: 10 }} suffix="M cells" />
          <Counter at={1940} out={2040} to={64} dur={30} style={{ fontSize: 96, fontWeight: 700, color: AMB, marginTop: 10 }} suffix=" cases" />
        </AbsoluteFill>
      </Fade>

      <Fade at={2040} out={2280}>
        <Img src={staticFile('k_loads.png')} style={{ position: 'absolute', right: 80, top: 160, height: 860, opacity: 0.25, filter: 'grayscale(0.4)' }} />
      </Fade>
      <AbsoluteFill style={{ padding: '200px 120px' }}>
        <Typer at={2040} out={2280} text="then the adversarial audit:" cps={30} style={{ fontSize: 44, color: '#9aa4b6' }} caret={false} />
        <Slam at={2075} out={2280} size={140} glow={GRN} color="#fff" style={{ marginTop: 40 }}>NET FORCE</Slam>
        <Slam at={2090} out={2280} size={170} glow={GRN} color={GRN} mono>(0, 0, 0)</Slam>
        <WordReveal at={2140} out={2280} text="The apparent push was a mesh artifact. Caught, fixed, documented." size={44} every={5} color="#e6ebf2" style={{ marginTop: 50, maxWidth: 1300 }} accent={GRN} accentWords={['Caught', 'fixed', 'documented']} />
        <div style={{ height: 30 }} />
        <Slam at={2200} out={2280} size={36} mono color={CY} from={1.1}>max field error 1.96 × 10⁻⁶</Slam>
      </AbsoluteFill>

      {/* ================= BREAK 2280-2400 ================= */}
      <Center>
        <Slam at={2285} out={2340} size={110} color="#9aa4b6">NOW,</Slam>
        <Slam at={2318} out={2398} size={130} glow={AMB} from={1.3}>THE BIG ONE.</Slam>
      </Center>

      {/* ================= ACT 3: THE THRUSTER 2400-3360 ================= */}
      <Tag at={2400} out={3360} num="03" title="DIGITAL THRUSTER · PRIVATE" color={AMB} />
      <Center>
        <Slam at={2400} out={2478} size={200} glow={AMB} color="#fff">DIGITAL</Slam>
        <Slam at={2410} out={2478} size={200} glow={AMB} color={AMB}>THRUSTER</Slam>
      </Center>
      <Shot src="t_exec1.png" at={2478} out={2580} x={560} y={200} w={1200} h={675} zoom={[1.0, 1.06]} border={AMB + '99'} from="right" />
      <AbsoluteFill style={{ padding: '260px 100px', width: 480 }}>
        <Slam at={2482} out={2580} size={64} color="#fff">BUILD.</Slam>
        <Slam at={2497} out={2580} size={64} color={AMB}>CHARGE.</Slam>
        <Slam at={2512} out={2580} size={64} color={CY}>TEST.</Slam>
        <WordReveal at={2530} out={2580} text="Electret wafer, factory-built, charged by me last" size={30} every={4} color="#9aa4b6" style={{ marginTop: 30 }} />
      </AbsoluteFill>

      <AbsoluteFill style={{ padding: '170px 120px' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 24 }}>
          <Counter at={2580} out={2760} to={131} dur={40} style={{ fontSize: 120, fontWeight: 700, color: '#fff' }} />
          <Slam at={2580} out={2760} size={44} mono color="#9aa4b6" from={1.1}>SIMULATION CASES · TARGET ≥ 300 MV/m</Slam>
        </div>
      </AbsoluteFill>
      <Gauge at={2595} out={2760} value={368.8} max={450} target={300} />
      <Shot src="t_candA.png" at={2640} out={2760} x={1000} y={360} w={820} h={420} fit="contain" bg="#fff" border={AMB + '99'} from="right" label="20 µm island · 250 nm oxide · 150 nm nitride" labelColor="#ffd9a0" />

      <DotField at={2760} out={2940} from={140} to={5} color={AMB} />
      <AbsoluteFill style={{ padding: '210px 120px' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 20 }}>
          <Counter at={2770} out={2940} to={15.9} decimals={1} dur={60} style={{ fontSize: 220, fontWeight: 700, color: '#fff', textShadow: `0 0 40px ${AMB}` }} />
          <Slam at={2770} out={2940} size={90} color={AMB} glow={AMB}>MILLION</Slam>
        </div>
        <Slam at={2785} out={2940} size={52} mono color="#fff" from={1.1}>ELECTRET SITES PER WAFER</Slam>
      </AbsoluteFill>
      <Chip text="10 µm sites" at={2830} out={2940} x={120} y={700} color={AMB} />
      <Chip text="20 µm pitch" at={2845} out={2940} x={420} y={700} color={AMB} />
      <Chip text="90 mm active area" at={2860} out={2940} x={720} y={700} color={AMB} />
      <Chip text="348 MV/m modeled" at={2875} out={2940} x={120} y={790} color={CY} />
      <Shot src="t_wafer.png" at={2850} out={2940} x={1260} y={430} w={580} h={436} fit="contain" bg="#fff" border={AMB + '99'} from="right" />

      <Shot src="t_charging.png" at={2940} out={3120} x={120} y={540} w={1680} h={400} fit="contain" bg="#fff" border={CY + '88'} from="down" zoom={[1.0, 1.04]} />
      <AbsoluteFill style={{ padding: '170px 120px' }}>
        <Slam at={2940} out={3120} size={88} glow={CY}>CORONA CHARGING DOCK</Slam>
        <WordReveal at={2965} out={3120} text="room temperature · no vacuum oven · one final step" size={40} every={5} color="#cfd6e2" style={{ marginTop: 26 }} />
      </AbsoluteFill>
      <Chip text="~80% charge left at 3 months · planning budget" at={3010} out={3120} x={120} y={420} color={AMB} size={32} />

      <AbsoluteFill style={{ padding: '190px 120px' }}>
        <Slam at={3120} out={3360} size={200} glow={AMB} color="#fff">9.4–15.3 N*</Slam>
        <Slam at={3135} out={3360} size={46} mono color="#9aa4b6" from={1.1}>PER WAFER · HANDOFF SCALING RULE</Slam>
        <div style={{ height: 40 }} />
        <Slam at={3170} out={3360} size={130} color={CY} glow={CY}>T/W 105–171*</Slam>
        <WordReveal at={3215} out={3360} text="*Heuristic from a prior anomalous result — not yet supported by mainstream physics. First gate: a charged test coupon." size={30} every={4} color="#8a94a6" style={{ marginTop: 50, maxWidth: 1500 }} mono />
      </AbsoluteFill>
      <Chip text="NEXT ▶ CHARGED COUPON TEST" at={3285} out={3360} x={1190} y={180} color={GRN} size={34} />

      {/* ================= OUTRO 3360-3690 ================= */}
      <Fade at={3360} out={3480}>
        <Column at={3362} x={110} color={AMB} title="THE BENCH" lines={['20 kV pulser online', 'DAQ rebuilt + live viewer', '167 tests passing']} />
        <Column at={3374} x={700} color={CY} title="THE FIELDS" lines={['2.87M-site lattices', '56 field movies', 'net force audited to zero']} />
        <Column at={3386} x={1290} color={GRN} title="THE THRUSTER" lines={['≥300 MV/m design found', '15.9M-site wafer plan', 'charging dock workflow']} />
      </Fade>
      <Center>
        <Slam at={3480} out={3690} size={64} mono color={CY} from={1.2}>WEEK OF OCT 13 · 2026</Slam>
        <div style={{ height: 30 }} />
        <Slam at={3490} out={3690} size={150} glow={AMB}>ONWARD.</Slam>
        <div style={{ height: 40 }} />
        <WordReveal at={3520} out={3690} text="David Chester · with Jarod" size={40} color="#9aa4b6" every={5} style={{ justifyContent: 'center' }} />
      </Center>

      </Sequence>
      <Flash at={[240, 780, 960, 2160, 3240, 4200, 4320]} />
      <Flash at={[1680]} color={GRN} len={8} />
      <Overlay />
      <AbsoluteFill style={{ background: '#000', opacity: endFade }} />
    </AbsoluteFill>
  );
};
