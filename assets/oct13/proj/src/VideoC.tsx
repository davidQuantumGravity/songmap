import React from 'react';
import { AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame, Easing } from 'remotion';
import { Background, Overlay, Flash, Slam, WordReveal, Counter, Tag, Chip, Center, Theme, clamp, ease } from './lib';

const T: Theme = { bg: '#05080c', ink: '#fff', a1: '#4cc9ff', a2: '#ffb23d', dim: '#8a94a6', grid: 'rgba(76,201,255,0.08)' };
const CY = '#4cc9ff', AMB = '#ffb23d', GRN = '#3dffa2', RED = '#ff5a6e', VI = '#b48cff';
const B = (bars: number) => bars * 60;

const Fade: React.FC<{ at: number; out: number; children: React.ReactNode }> = ({ at, out, children }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const o = Math.min(interpolate(f, [at, at + 12], [0, 1], clamp), interpolate(f, [out - 12, out], [1, 0], clamp));
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};

type Focus = { t: number; x: number; y: number; s: number };
// Movie / image in a frame with a camera that eases between focus regions (source pixel coords, 1920x1080)
const Cam: React.FC<{ src: string; video?: boolean; at: number; out: number; x: number; y: number; w: number; h: number; focus: Focus[]; rate?: number; border?: string; label?: string }> = ({ src, video, at, out, x, y, w, h, focus, rate = 0.5, border = CY, label }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const t = f - at;
  let k = 0;
  while (k < focus.length - 1 && t >= focus[k + 1].t) k++;
  const a = focus[k], b2 = focus[Math.min(k + 1, focus.length - 1)];
  const p = k === focus.length - 1 ? 0 : interpolate(t, [b2.t - 24, b2.t], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const cx = a.x + (b2.x - a.x) * p, cy = a.y + (b2.y - a.y) * p, s = a.s + (b2.s - a.s) * p;
  const base = w / 1920;
  const sc = base * s;
  let tx = w / 2 - cx * sc, ty = h / 2 - cy * sc;
  tx = Math.min(0, Math.max(w - 1920 * sc, tx));
  ty = Math.min(0, Math.max(h - 1080 * sc, ty));
  const o = Math.min(interpolate(t, [0, 12], [0, 1], clamp), interpolate(f, [out - 12, out], [1, 0], clamp));
  return (
    <div style={{ position: 'absolute', left: x, top: y, width: w, height: h, opacity: o, borderRadius: 14, overflow: 'hidden', border: `2px solid ${border}88`, boxShadow: `0 20px 60px rgba(0,0,0,0.6), 0 0 30px ${border}44`, background: '#fff' }}>
      <div style={{ position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, transformOrigin: '0 0', transform: `translate(${tx}px, ${ty}px) scale(${sc})` }}>
        {video ? (
          <Sequence from={at} durationInFrames={out - at} layout="none">
            <OffthreadVideo src={staticFile(src)} muted playbackRate={rate} style={{ width: 1920, height: 1080 }} />
          </Sequence>
        ) : (
          <Img src={staticFile(src)} style={{ width: 1920, height: 1080, objectFit: 'contain' }} />
        )}
      </div>
      {label ? <div style={{ position: 'absolute', left: 14, top: 12, padding: '6px 14px', background: 'rgba(5,8,12,0.85)', color: '#fff', fontFamily: 'JetBrains Mono', fontSize: 22, borderRadius: 8 }}>{label}</div> : null}
    </div>
  );
};

// Explainer card in right column
const Card: React.FC<{ at: number; out: number; y: number; n: string; title: string; body: string; color?: string }> = ({ at, out, y, n, title, body, color = CY }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const t = f - at;
  const o = Math.min(interpolate(t, [0, 10], [0, 1], clamp), interpolate(f, [out - 10, out], [1, 0], clamp));
  const dx = interpolate(t, [0, 14], [60, 0], { ...clamp, easing: ease });
  return (
    <div style={{ position: 'absolute', left: 1380, top: y, width: 480, opacity: o, transform: `translateX(${dx}px)`, padding: '18px 22px', borderRadius: 12, background: 'rgba(255,255,255,0.05)', borderLeft: `6px solid ${color}` }}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'baseline' }}>
        <span style={{ fontFamily: 'JetBrains Mono', fontSize: 22, color }}>{n}</span>
        <span style={{ fontFamily: 'Space Grotesk', fontWeight: 700, fontSize: 32, color: '#fff' }}>{title}</span>
      </div>
      <div style={{ fontFamily: 'Space Grotesk', fontSize: 26, lineHeight: 1.3, color: '#c9d1dd', marginTop: 8 }}>{body}</div>
    </div>
  );
};

const Heading: React.FC<{ at: number; out: number; kicker: string; title: string; color?: string }> = ({ at, out, kicker, title, color = CY }) => (
  <AbsoluteFill style={{ padding: '110px 60px 0' }}>
    <Slam at={at} out={out} size={26} mono color={color} from={1.1}>{kicker}</Slam>
    <div style={{ height: 8 }} />
    <Slam at={at + 4} out={out} size={54} from={1.15}>{title}</Slam>
  </AbsoluteFill>
);

// Cross-section + top view of the device (not to scale)
const Geometry: React.FC<{ at: number; out: number }> = ({ at, out }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const t = f - at;
  const o = Math.min(interpolate(t, [0, 12], [0, 1], clamp), interpolate(f, [out - 12, out], [1, 0], clamp));
  const a = (d: number) => interpolate(t, [d, d + 14], [0, 1], { ...clamp, easing: ease });
  const pads = [...Array(9)].map((_, i) => 140 + i * 90);
  // coverage squares on top view
  const cov = Math.floor(interpolate(t, [150, 330], [0, 4], clamp));
  const covFrac = [0.25, 0.5, 0.75, 1][Math.min(3, cov)];
  const K = 380, side = K * Math.sqrt(covFrac);
  return (
    <svg width={1920} height={1080} style={{ position: 'absolute', opacity: o }}>
      {/* cross-section */}
      <text x={110} y={300} fill="#8a94a6" fontFamily="JetBrains Mono" fontSize={24}>CROSS-SECTION · thickness exaggerated</text>
      <g opacity={a(20)}>
        <rect x={100} y={500} width={880} height={110} fill="#9aa4b6" />
        <text x={1000} y={565} fill="#cfd6e2" fontFamily="Space Grotesk" fontSize={30}>Aluminum backing · 100 µm · grounded</text>
      </g>
      <g opacity={a(40)}>
        <rect x={60} y={430} width={960} height={70} fill="#ffb23d" opacity={0.75} />
        <text x={1040} y={475} fill="#ffd9a0" fontFamily="Space Grotesk" fontSize={30}>Kapton film · 25 µm · εr = 3.4</text>
      </g>
      <g opacity={a(60)}>
        {pads.map((px, i) => <rect key={i} x={px} y={414} width={46} height={16} fill="#e8eef6" stroke={CY} strokeWidth={2} />)}
        <text x={1040} y={410} fill={CY} fontFamily="Space Grotesk" fontSize={30}>Al pads · Ø 25 µm · 1 µm thick · 75 µm pitch</text>
      </g>
      <g opacity={a(80)}>
        {pads.map((px, i) => <rect key={i} x={px} y={432} width={46} height={14} fill={VI} opacity={0.8} />)}
        <text x={1040} y={350} fill={VI} fontFamily="Space Grotesk" fontSize={28}>trap layer: top 1 µm under each pad (≤ 0.1 pC/site)</text>
      </g>
      {/* top view */}
      <g opacity={a(120)} transform="translate(1180, 640)">
        <text x={0} y={-20} fill="#8a94a6" fontFamily="JetBrains Mono" fontSize={22}>TOP VIEW</text>
        <rect x={0} y={0} width={K} height={K} fill="#ffb23d33" stroke="#ffb23d" strokeWidth={2} />
        <rect x={K * 0.1} y={K * 0.1} width={K * 0.8} height={K * 0.8} fill="none" stroke="#cfd6e2" strokeWidth={3} strokeDasharray="10 6" />
        <rect x={(K - side) / 2} y={(K - side) / 2} width={side} height={side} fill={`${CY}44`} stroke={CY} strokeWidth={3} />
        <text x={K + 20} y={40} fill="#ffd9a0" fontFamily="Space Grotesk" fontSize={24}>Kapton 127 mm</text>
        <text x={K + 20} y={80} fill="#cfd6e2" fontFamily="Space Grotesk" fontSize={24}>backing 101.6 mm (dashed)</text>
        <text x={K + 20} y={130} fill={CY} fontFamily="Space Grotesk" fontWeight={700} fontSize={40}>{Math.round(covFrac * 100)}% footprint</text>
        <text x={K + 20} y={170} fill="#cfd6e2" fontFamily="JetBrains Mono" fontSize={24}>{['715,716', '1,435,204', '2,149,156', '2,869,636'][Math.min(3, cov)]} pads</text>
        {covFrac > 0.7 ? <text x={K + 20} y={215} fill={AMB} fontFamily="Space Grotesk" fontSize={24}>← pads now overhang the backing</text> : null}
      </g>
    </svg>
  );
};

// Charging protocol plot (schematic, log-ish time)
const Protocol: React.FC<{ at: number; out: number }> = ({ at, out }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const t = f - at;
  const o = Math.min(interpolate(t, [0, 12], [0, 1], clamp), interpolate(f, [out - 12, out], [1, 0], clamp));
  const draw = interpolate(t, [10, 150], [0, 1], { ...clamp, easing: Easing.inOut(Easing.quad) });
  const X0 = 140, X1 = 1240, Y0 = 300, Y1 = 760;
  // segments: 0-1 s ramp (x 0-0.15), hold to 11 s (0.15-0.45), float to 1011 s (0.45-1)
  const pts: [number, number][] = [];
  for (let i = 0; i <= 200; i++) {
    const u = i / 200;
    let v = 0;
    if (u < 0.15) v = (1 - Math.cos((Math.PI * u) / 0.15)) / 2; else v = 1;
    pts.push([X0 + u * (X1 - X0), Y0 + 40 + v * (Y1 - Y0 - 80)]);
  }
  const n = Math.max(2, Math.floor(draw * pts.length));
  const path = pts.slice(0, n).map((p, i) => `${i ? 'L' : 'M'}${p[0]},${p[1]}`).join(' ');
  const xd = X0 + 0.45 * (X1 - X0);
  return (
    <svg width={1920} height={1080} style={{ position: 'absolute', opacity: o }}>
      <line x1={X0} y1={Y0 + 40} x2={X1} y2={Y0 + 40} stroke="#ffffff33" />
      <text x={X0 - 20} y={Y0 + 48} textAnchor="end" fill="#8a94a6" fontFamily="JetBrains Mono" fontSize={22}>0 V</text>
      <text x={X0 - 20} y={Y1 - 32} textAnchor="end" fill="#8a94a6" fontFamily="JetBrains Mono" fontSize={22}>−V</text>
      <rect x={X0} y={Y0} width={0.15 * (X1 - X0)} height={Y1 - Y0} fill={`${CY}11`} />
      <rect x={X0 + 0.15 * (X1 - X0)} y={Y0} width={0.3 * (X1 - X0)} height={Y1 - Y0} fill={`${AMB}11`} />
      <rect x={xd} y={Y0} width={0.55 * (X1 - X0)} height={Y1 - Y0} fill={`${GRN}0d`} />
      <path d={path} fill="none" stroke="#fff" strokeWidth={6} style={{ filter: 'drop-shadow(0 0 8px #fff)' }} />
      <line x1={xd} y1={Y0} x2={xd} y2={Y1} stroke={RED} strokeWidth={3} strokeDasharray="8 6" opacity={interpolate(t, [70, 80], [0, 1], clamp)} />
      {[['RAMP · 1 s', X0 + 10, CY, 30], ['HOLD · 10 s', X0 + 0.16 * (X1 - X0), AMB, 60], ['DISCONNECT → FLOAT · 1000 s', xd + 14, GRN, 90]].map(([s, xx, c, d]) => (
        <text key={s as string} x={xx as number} y={Y1 + 50} fill={c as string} fontFamily="JetBrains Mono" fontSize={26} opacity={interpolate(t, [d as number, (d as number) + 10], [0, 1], clamp)}>{s as string}</text>
      ))}
      <text x={xd + 14} y={Y0 - 14} fill={RED} fontFamily="JetBrains Mono" fontSize={24} opacity={interpolate(t, [80, 90], [0, 1], clamp)}>t = 11 s: pads disconnected</text>
    </svg>
  );
};

const Matrix: React.FC<{ at: number; out: number }> = ({ at, out }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const t = f - at;
  const o = Math.min(interpolate(t, [0, 12], [0, 1], clamp), interpolate(f, [out - 12, out], [1, 0], clamp));
  const rows = [['COVERAGE', '25 · 50 · 75 · 100 %', 4, CY], ['DRIVE', '−100 V · −500 V', 2, AMB], ['CONTACT BARRIER', '1.0 · 1.7 · 1.7×5 · 2.5 eV', 4, VI], ['BACKING', 'grounded · floating', 2, GRN]];
  return (
    <div style={{ position: 'absolute', left: 60, top: 260, opacity: o }}>
      {rows.map(([k, v, n, c], i) => (
        <div key={k as string} style={{ display: 'flex', alignItems: 'center', gap: 30, marginBottom: 34, opacity: interpolate(t, [i * 14, i * 14 + 10], [0, 1], clamp) }}>
          <div style={{ width: 340, fontFamily: 'JetBrains Mono', fontSize: 28, color: c as string }}>{k as string}</div>
          <div style={{ width: 520, fontFamily: 'Space Grotesk', fontSize: 36, color: '#fff' }}>{v as string}</div>
          <div style={{ fontFamily: 'Space Grotesk', fontWeight: 700, fontSize: 56, color: c as string }}>×{n as number}</div>
        </div>
      ))}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 30, marginTop: 30, opacity: interpolate(t, [70, 80], [0, 1], clamp) }}>
        <div style={{ width: 340, fontFamily: 'JetBrains Mono', fontSize: 28, color: '#9aa4b6' }}>= SCENARIOS</div>
        <Counter at={at + 72} to={64} dur={30} style={{ fontSize: 120, fontWeight: 700, color: '#fff' }} />
        <div style={{ fontFamily: 'Space Grotesk', fontSize: 34, color: '#cfd6e2' }}>→ rendered as <b style={{ color: AMB }}>56 movies</b></div>
      </div>
      <div style={{ fontFamily: 'Space Grotesk', fontSize: 30, color: '#9aa4b6', marginTop: 20, opacity: interpolate(t, [110, 120], [0, 1], clamp) }}>per coverage: 6 field movies · 6 charge movies · 2 close-up cell movies</div>
    </div>
  );
};

// Highlight box over a still (How-to-read)
const HL: React.FC<{ at: number; out: number; x: number; y: number; w: number; h: number; n: string; text: string; color: string; tx: number; ty: number }> = ({ at, out, x, y, w, h, n, text, color, tx, ty }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const o = Math.min(interpolate(f - at, [0, 8], [0, 1], clamp), interpolate(f, [out - 8, out], [1, 0], clamp));
  return (
    <>
      <div style={{ position: 'absolute', left: x, top: y, width: w, height: h, border: `4px solid ${color}`, borderRadius: 8, opacity: o, boxShadow: `0 0 30px ${color}, inset 0 0 30px ${color}55` }} />
      <div style={{ position: 'absolute', left: tx, top: ty, width: 460, opacity: o, fontFamily: 'Space Grotesk', fontSize: 30, color: '#fff', padding: '14px 18px', background: 'rgba(5,8,12,0.9)', borderLeft: `6px solid ${color}`, borderRadius: 8 }}>
        <span style={{ fontFamily: 'JetBrains Mono', color, marginRight: 10 }}>{n}</span>{text}
      </div>
    </>
  );
};

const Bars: React.FC<{ at: number; out: number; items: { label: string; value: number; shown: string; color: string }[]; log?: boolean; max: number; title: string }> = ({ at, out, items, log, max, title }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const t = f - at;
  const o = Math.min(interpolate(t, [0, 12], [0, 1], clamp), interpolate(f, [out - 12, out], [1, 0], clamp));
  return (
    <div style={{ position: 'absolute', left: 80, top: 300, width: 1220, opacity: o }}>
      <div style={{ fontFamily: 'JetBrains Mono', fontSize: 24, color: '#8a94a6', marginBottom: 30 }}>{title}</div>
      {items.map((it, i) => {
        const g = interpolate(t, [10 + i * 18, 40 + i * 18], [0, 1], { ...clamp, easing: ease });
        const frac = log ? (Math.log10(it.value) - Math.log10(max) + 6) / 6 : it.value / max;
        return (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 30 }}>
            <div style={{ width: 300, fontFamily: 'Space Grotesk', fontSize: 30, color: '#fff' }}>{it.label}</div>
            <div style={{ width: Math.max(6, 760 * Math.max(0.01, frac) * g), height: 56, background: it.color, borderRadius: 6, boxShadow: `0 0 24px ${it.color}88` }} />
            <div style={{ fontFamily: 'Space Grotesk', fontWeight: 700, fontSize: 40, color: it.color, opacity: g, whiteSpace: 'nowrap' }}>{it.shown}</div>
          </div>
        );
      })}
    </div>
  );
};

const TugOfWar: React.FC<{ at: number; out: number }> = ({ at, out }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const t = f - at;
  const o = Math.min(interpolate(t, [0, 12], [0, 1], clamp), interpolate(f, [out - 12, out], [1, 0], clamp));
  const g = (d: number) => interpolate(t, [d, d + 25], [0, 1], { ...clamp, easing: ease });
  const wob = Math.sin(t * 0.25) * 4;
  const arrow = (x: number, y: number, len: number, up: boolean, col: string, label: string, val: string, d: number) => {
    const L = len * g(d);
    const y2 = up ? y - L : y + L;
    return (
      <g key={label}>
        <line x1={x} y1={y} x2={x} y2={y2} stroke={col} strokeWidth={22} strokeLinecap="round" style={{ filter: `drop-shadow(0 0 12px ${col})` }} />
        <polygon points={up ? `${x - 34},${y2 + 10} ${x + 34},${y2 + 10} ${x},${y2 - 40}` : `${x - 34},${y2 - 10} ${x + 34},${y2 - 10} ${x},${y2 + 40}`} fill={col} opacity={g(d)} />
        <text x={x + 50} y={(y + y2) / 2} fill="#fff" fontFamily="Space Grotesk" fontSize={30} opacity={g(d)}>{label}</text>
        <text x={x + 50} y={(y + y2) / 2 + 44} fill={col} fontFamily="Space Grotesk" fontWeight={700} fontSize={44} opacity={g(d)}>{val}</text>
      </g>
    );
  };
  return (
    <svg width={1920} height={1080} style={{ position: 'absolute', opacity: o }}>
      <g transform={`translate(0, ${wob})`}>
        <rect x={160} y={560} width={820} height={18} fill="#e8eef6" />
        <rect x={160} y={578} width={820} height={40} fill="#ffb23d" opacity={0.7} />
        <rect x={160} y={618} width={820} height={60} fill="#9aa4b6" />
        {arrow(300, 560, 230, false, VI, 'pads', '≈ −39 N', 10)}
        {arrow(560, 560, 230, true, AMB, 'Kapton', '≈ +37 N', 30)}
        {arrow(860, 560, 150, true, CY, 'backing', '≈ +8 N', 50)}
      </g>
    </svg>
  );
};

export const VideoC: React.FC = () => {
  const f = useCurrentFrame();
  const endFade = interpolate(f, [B(150) - 60, B(150) + 60], [0, 1], clamp);
  const MV = { x: 50, y: 230, w: 1300, h: 731 };
  return (
    <AbsoluteFill style={{ background: T.bg }}>
      <Audio src={staticFile('track_C.wav')} />
      <Background theme={T} intensity={0.5} />

      {/* ===== TITLE 0-6 ===== */}
      <Center>
        <Slam at={20} out={B(6)} size={30} mono color={CY} from={1.1}>DEEP DIVE · KAPTON ELECTRET LATTICE STUDY</Slam>
        <div style={{ height: 30 }} />
        <Slam at={50} out={B(6)} size={150} glow={CY}>INSIDE THE</Slam>
        <Slam at={70} out={B(6)} size={170} glow={AMB} color={AMB}>56 MOVIES</Slam>
        <div style={{ height: 40 }} />
        <WordReveal at={130} out={B(6)} text="What happens when you charge millions of tiny aluminum pads on plastic film — explained frame by frame" size={38} every={4} color="#cfd6e2" style={{ justifyContent: 'center', maxWidth: 1400 }} />
      </Center>

      {/* ===== GEOMETRY 6-14 ===== */}
      <Tag at={B(6)} out={B(28)} num="01" title="THE SETUP" color={CY} />
      <Heading at={B(6)} out={B(14)} kicker="WHAT WAS SIMULATED" title="A sheet of plastic, dotted with metal, over a metal plate" />
      <Geometry at={B(6) + 20} out={B(14)} />

      {/* ===== PROTOCOL + MATRIX 14-22 ===== */}
      <Heading at={B(14)} out={B(18)} kicker="THE CHARGING RECIPE" title="Push charge in, then let go and watch" />
      <Protocol at={B(14) + 10} out={B(18)} />
      <AbsoluteFill style={{ left: 1320, top: 330, width: 540 }}>
        <WordReveal at={B(14) + 100} out={B(18)} text="Like charging a battery, then unplugging it to see if the charge stays put." size={34} every={4} color="#cfd6e2" />
      </AbsoluteFill>
      <Heading at={B(18)} out={B(22)} kicker="THE EXPERIMENT GRID" title="Four knobs, every combination" />
      <Matrix at={B(18) + 10} out={B(22)} />

      {/* ===== HOW TO READ 22-28 ===== */}
      <Heading at={B(22)} out={B(28)} kicker="HOW TO READ A FIELD MOVIE" title="Four kinds of panels, two rows" />
      <Fade at={B(22)} out={B(28)}>
        <div style={{ position: 'absolute', left: 50, top: 230, width: 1300, height: 731, borderRadius: 14, overflow: 'hidden', border: `2px solid ${CY}88` }}>
          <Img src={staticFile('c_key_field.png')} style={{ width: 1300, height: 731 }} />
        </div>
      </Fade>
      {/* scale 1300/1920 = 0.677 */}
      <HL at={B(22) + 20} out={B(28)} x={50 + 70 * 0.677} y={230 + 30 * 0.677} w={380 * 0.677} h={480 * 0.677} n="1" text="Voltage map — the whole sheet in side view" color={CY} tx={1380} ty={250} />
      <HL at={B(22) + 80} out={B(28)} x={50 + 570 * 0.677} y={230 + 30 * 0.677} w={380 * 0.677} h={480 * 0.677} n="2" text="Field strength + arrows showing which way it points" color={AMB} tx={1380} ty={420} />
      <HL at={B(22) + 140} out={B(28)} x={50 + 1065 * 0.677} y={230 + 30 * 0.677} w={380 * 0.677} h={480 * 0.677} n="3" text="Under the plate, brightened so weak fields show" color={GRN} tx={1380} ty={590} />
      <HL at={B(22) + 200} out={B(28)} x={50 + 1525 * 0.677} y={230 + 20 * 0.677} w={390 * 0.677} h={500 * 0.677} n="4" text="Time plots: voltage, trapped charge, forces" color={VI} tx={1380} ty={760} />
      <AbsoluteFill style={{ left: 60, top: 990 }}>
        <WordReveal at={B(22) + 250} out={B(28)} text="Top row: backing grounded · Bottom row: backing floating" size={30} every={3} color="#9aa4b6" mono />
      </AbsoluteFill>

      {/* ===== M1 field 500V 28-36 ===== */}
      <Tag at={B(28)} out={B(106)} num="02" title="THE MOVIES" color={AMB} />
      <Heading at={B(28)} out={B(36)} kicker="MOVIE 1 · 100% COVERAGE · −500 V · LOW BARRIER" title="Charging up the whole sheet" color={AMB} />
      <Cam src="c_fld_C100_500V.mp4" video at={B(28)} out={B(36)} {...MV} focus={[{ t: 0, x: 960, y: 540, s: 1 }, { t: 110, x: 1720, y: 280, s: 2.3 }, { t: 260, x: 760, y: 280, s: 1.8 }, { t: 380, x: 1250, y: 280, s: 1.8 }]} />
      <Card at={B(28) + 30} out={B(36)} y={250} n="01" title="Volts in 1 second" body="All pads ramp smoothly to −500 V. Watch the top-right plot." />
      <Card at={B(28) + 140} out={B(36)} y={480} n="02" title="Traps fill in ~3 s" body="Electrons leak from the pads into the Kapton just beneath — then stop when the traps are full." color={VI} />
      <Card at={B(28) + 280} out={B(36)} y={710} n="03" title="Fields wrap around" body="The field curls around the plate edges and reaches the back side — weak, but there." color={GRN} />

      {/* ===== M2 local cell 36-44 ===== */}
      <Heading at={B(36)} out={B(44)} kicker="MOVIE 2 · ONE 75 µm CELL, CLOSE UP" title="Zooming into a single pad" color={AMB} />
      <Cam src="c_loc_C100_500V.mp4" video at={B(36)} out={B(44)} {...MV} focus={[{ t: 0, x: 960, y: 540, s: 1 }, { t: 100, x: 330, y: 290, s: 1.9 }, { t: 250, x: 1600, y: 290, s: 1.9 }]} />
      <Card at={B(36) + 30} out={B(44)} y={250} n="01" title="Layers to scale-ish" body="Pad on top, thin Kapton band, grey metal backing. Thickness is stretched so you can see it." />
      <Card at={B(36) + 130} out={B(44)} y={480} n="02" title="Over the plate: squeezed" body="Pads above the backing press on the film at ≈ 55,000 Pa — about half an atmosphere." color={AMB} />
      <Card at={B(36) + 270} out={B(44)} y={710} n="03" title="Past the edge: barely felt" body="Pads hanging beyond the plate feel ≈ 2 Pa. No metal below means almost no pull." color={RED} />

      {/* ===== M3 charge maps 44-52 ===== */}
      <Heading at={B(44)} out={B(52)} kicker="MOVIE 3 · WHERE THE CHARGE SITS" title="Five layers of charge, blue = negative, red = positive" color={AMB} />
      <Cam src="c_ch_C100_500V_b10.mp4" video at={B(44)} out={B(52)} {...MV} focus={[{ t: 0, x: 960, y: 540, s: 1 }, { t: 90, x: 380, y: 290, s: 2.0 }, { t: 220, x: 950, y: 290, s: 2.0 }, { t: 340, x: 1520, y: 290, s: 2.0 }]} />
      <Card at={B(44) + 30} out={B(52)} y={250} n="01" title="Pads + traps: negative" body="The electrons we pushed in — on the metal pads and in the traps just below." color={CY} />
      <Card at={B(44) + 160} out={B(52)} y={480} n="02" title="Kapton answers back" body="The plastic polarizes: its upper surface turns positive to oppose the field." color={AMB} />
      <Card at={B(44) + 290} out={B(52)} y={710} n="03" title="The plate mirrors it" body="The backing pulls in an equal-and-opposite positive charge — its 'mirror'." color={RED} />

      {/* ===== M4 -100 V 52-60 ===== */}
      <Heading at={B(52)} out={B(60)} kicker="MOVIE 4 · SAME SHEET AT −100 V" title="Five times less voltage — same trapped charge?" color={AMB} />
      <Cam src="c_fld_C100_100V.mp4" video at={B(52)} out={B(60)} {...MV} focus={[{ t: 0, x: 960, y: 540, s: 1 }, { t: 100, x: 1720, y: 280, s: 2.3 }, { t: 300, x: 760, y: 280, s: 1.6 }]} />
      <Card at={B(52) + 30} out={B(60)} y={250} n="01" title="Weaker fields" body="Everything scales down — 5× less voltage on the pads." />
      <Card at={B(52) + 140} out={B(60)} y={480} n="02" title="But traps still fill" body="With this (assumed) easy contact, traps hit their cap either way: ≈ 183 nC total." color={VI} />
      <Card at={B(52) + 270} out={B(60)} y={710} n="03" title="The difference is the metal" body="Pad charge ≈ −250 nC at −100 V vs ≈ −1,950 nC at −500 V." color={AMB} />

      {/* ===== M5/M6 side-by-side charge 60-66 ===== */}
      <Heading at={B(60)} out={B(66)} kicker="MOVIES 5 + 6 · CHARGE MAPS SIDE BY SIDE" title="−100 V (left) vs −500 V (right)" color={AMB} />
      <Cam src="c_ch_C100_100V_b10.mp4" video at={B(60)} out={B(66)} x={50} y={250} w={900} h={506} focus={[{ t: 0, x: 960, y: 290, s: 1.6 }]} border={CY} label="−100 V" />
      <Cam src="c_ch_C100_500V_b10.mp4" video at={B(60)} out={B(66)} x={970} y={250} w={900} h={506} focus={[{ t: 0, x: 960, y: 290, s: 1.6 }]} border={AMB} label="−500 V" />
      <AbsoluteFill style={{ left: 60, top: 800, width: 1800 }}>
        <WordReveal at={B(60) + 60} out={B(66)} text="Same pattern, same trapped dose — only the metal charge and mirror charge scale with voltage." size={38} every={4} color="#e6ebf2" accent={AMB} accentWords={['metal', 'mirror']} />
      </AbsoluteFill>

      {/* ===== M7-10 coverage grid 66-78 ===== */}
      <Heading at={B(66)} out={B(78)} kicker="MOVIES 7–10 · 25 → 100% COVERAGE AT −500 V" title="Filling more of the sheet with pads" color={AMB} />
      {([['c_fld_C25_500V.mp4', '25% · 715,716 pads', 50, 240], ['c_fld_C50_500V.mp4', '50% · 1,435,204', 710, 240], ['c_fld_C75_500V.mp4', '75% · 2,149,156', 50, 620], ['c_fld_C100_500V.mp4', '100% · 2,869,636', 710, 620]] as [string, string, number, number][]).map(([s, l, x, y], i) => (
        <Cam key={s} src={s} video at={B(66) + i * 15} out={B(78)} x={x} y={y} w={640} h={360} focus={[{ t: 0, x: 760, y: 280, s: 2.0 }]} rate={0.6} label={l} />
      ))}
      <Card at={B(66) + 120} out={B(78)} y={250} n="01" title="Bigger footprint" body="The charged area grows; the field pattern spreads toward the plate edges." />
      <Card at={B(66) + 330} out={B(78)} y={470} n="02" title="75% and up: overhang" body="Pads start landing beyond the 101.6 mm plate — 1.04 M of them at 100%." color={AMB} />
      <Card at={B(66) + 520} out={B(78)} y={690} n="03" title="Watch the payoff…" body="Does more coverage mean more charge? Next chart." color={GRN} />

      {/* coverage chart 78-84 */}
      <Heading at={B(78)} out={B(84)} kicker="RESULT · COVERAGE" title="More pads stops helping past 75%" color={GRN} />
      <Bars at={B(78) + 10} out={B(84)} title="TOTAL TRAPPED CHARGE AFTER CHARGING (nC) · −500 V · low barrier" max={190} items={[
        { label: '25%', value: 71.6, shown: '71.6 nC', color: CY },
        { label: '50%', value: 143.5, shown: '143.5 nC', color: CY },
        { label: '75%', value: 183.3, shown: '183.3 nC', color: AMB },
        { label: '100%', value: 183.3, shown: '183.3 nC', color: AMB },
      ]} />
      <Card at={B(78) + 120} out={B(84)} y={300} n="WHY" title="No plate, no pull" body="Overhanging pads have no grounded metal beneath them, so they barely charge. Per pad: 0.100 → 0.085 → 0.064 pC." color={GRN} />

      {/* ===== M11 high barrier charge 84-92 ===== */}
      <Heading at={B(84)} out={B(92)} kicker="MOVIE 11 · SAME SHEET, HARDER CONTACT (1.7 eV)" title="Raise the contact barrier…" color={VI} />
      <Cam src="c_ch_C100_500V_b17.mp4" video at={B(84)} out={B(92)} {...MV} focus={[{ t: 0, x: 960, y: 540, s: 1 }, { t: 100, x: 573, y: 290, s: 2.4 }, { t: 260, x: 720, y: 290, s: 3.2 }]} />
      <Card at={B(84) + 40} out={B(92)} y={250} n="01" title="What's a barrier?" body="An energy hurdle electrons must jump to leave the aluminum and enter the Kapton." color={VI} />
      <Card at={B(84) + 170} out={B(92)} y={480} n="02" title="Read the color bar!" body="The trap map looks just as blue — but its scale tops out near 10⁻⁷ µC/m², not 10¹. Roughly a hundred-million-fold less." color={VI} />
      <Card at={B(84) + 300} out={B(92)} y={740} n="03" title="Lesson" body="Always check the scale before comparing two heatmaps." color={AMB} />

      {/* ===== M12 high barrier + field factor 92-100 ===== */}
      <Heading at={B(92)} out={B(100)} kicker="MOVIE 12 · 1.7 eV WITH 5× FIELD BOOST AT THE EDGE" title="Even helped along, almost nothing gets in" color={VI} />
      <Cam src="c_fld_C100_500V_b17f5.mp4" video at={B(92)} out={B(100)} {...MV} focus={[{ t: 0, x: 960, y: 540, s: 1 }, { t: 90, x: 1720, y: 270, s: 2.6 }]} />
      <Card at={B(92) + 40} out={B(100)} y={250} n="01" title="Look at the charge plot" body="Trapped charge creeps to just ≈ 0.001 nC — after a full 1000 s." color={VI} />
      <Card at={B(92) + 170} out={B(100)} y={480} n="02" title="Voltage looks identical" body="The pads still sit at −500 V. The difference is all in what crosses the contact." />

      {/* barrier compare 100-106 */}
      <Heading at={B(100)} out={B(106)} kicker="RESULT · CONTACT BARRIER" title="The contact is the master knob" color={VI} />
      <Bars at={B(100) + 10} out={B(106)} log title="TRAPPED CHARGE · 100% · −500 V (log scale)" max={200} items={[
        { label: '1.0 eV barrier', value: 183, shown: '≈ 183 nC', color: GRN },
        { label: '1.7 eV × 5 boost', value: 0.001, shown: '≈ 0.001 nC', color: RED },
      ]} />
      <AbsoluteFill style={{ left: 80, top: 640, width: 1400 }}>
        <Slam at={B(100) + 70} out={B(106)} size={110} glow={VI} color="#fff">~180,000×</Slam>
        <WordReveal at={B(100) + 90} out={B(106)} text="difference from the contact alone. Measuring the real Al/Kapton barrier is the #1 unknown." size={38} every={4} color="#cfd6e2" accent={VI} accentWords={['#1']} />
      </AbsoluteFill>

      {/* ===== FINDINGS 106-138 ===== */}
      <Tag at={B(106)} out={B(146)} num="03" title="WHAT IT ALL MEANS" color={GRN} />
      <Heading at={B(106)} out={B(114)} kicker="FINDING · CHARGE BOOKKEEPING" title="Huge charges, nearly zero net" color={GRN} />
      <Cam src="c_charge_ledger_C100_02.png" at={B(106)} out={B(114)} x={50} y={230} w={1300} h={731} focus={[{ t: 0, x: 960, y: 540, s: 1 }, { t: 120, x: 960, y: 830, s: 1.4 }]} border={GRN} />
      <Card at={B(106) + 40} out={B(114)} y={250} n="−" title="Pads ≈ −1,950 nC" body="Negative charge on the metal dots." color={VI} />
      <Card at={B(106) + 110} out={B(114)} y={430} n="+" title="Plate ≈ +2,120 nC" body="The backing's mirror charge nearly cancels it." color={CY} />
      <Card at={B(106) + 180} out={B(114)} y={610} n="=" title="Net ≈ −1.9 nC" body="Less than 0.1% left over. The device as a whole is almost neutral." color={GRN} />

      <Heading at={B(114)} out={B(122)} kicker="FINDING · FORCES" title="A tug-of-war that cancels" color={GRN} />
      <TugOfWar at={B(114) + 10} out={B(122)} />
      <Card at={B(114) + 60} out={B(122)} y={260} n="01" title="Tens of newtons inside" body="Pads are pulled down, Kapton and plate pulled up — large internal stresses." color={AMB} />
      <Card at={B(114) + 180} out={B(122)} y={520} n="02" title="Not thrust" body="A charged object can't push itself. These pieces pull on each other; edge terms and surroundings are omitted. Forces stay unqualified." color={RED} />

      <Heading at={B(122)} out={B(128)} kicker="FINDING · GROUNDED vs FLOATING PLATE" title="Unplugging the plate changes nothing" color={GRN} />
      <AbsoluteFill style={{ padding: '300px 80px' }}>
        <div style={{ display: 'flex', gap: 100 }}>
          <div><Slam at={B(122) + 15} out={B(128)} size={34} mono color={CY} from={1.1}>GROUNDED</Slam><Slam at={B(122) + 20} out={B(128)} size={110} color="#fff">−1.9172 nC</Slam></div>
          <div><Slam at={B(122) + 35} out={B(128)} size={34} mono color={AMB} from={1.1}>FLOATING</Slam><Slam at={B(122) + 40} out={B(128)} size={110} color="#fff">−1.9172 nC</Slam></div>
        </div>
        <WordReveal at={B(122) + 80} out={B(128)} text="The plate already holds its mirror charge when it's cut loose — so it just keeps it." size={40} every={4} color="#cfd6e2" style={{ marginTop: 60, maxWidth: 1500 }} />
      </AbsoluteFill>

      <Heading at={B(128)} out={B(138)} kicker="HONEST LIMITS" title="What these movies do NOT prove yet" color={RED} />
      <AbsoluteFill style={{ padding: '280px 80px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 34 }}>
          <WordReveal at={B(128) + 20} out={B(138)} text="✗  The injection law is assumed — not calibrated to real Al/Kapton" size={42} every={3} accent={RED} accentWords={['✗', 'assumed']} />
          <WordReveal at={B(128) + 80} out={B(138)} text="✗  The 1000-s clock is illustrative, not a measured retention time" size={42} every={3} accent={RED} accentWords={['✗', 'illustrative,']} />
          <WordReveal at={B(128) + 140} out={B(138)} text="✗  23 of 179 accuracy checks failed (mesh changes of 9–31%) — kept, not hidden" size={42} every={3} accent={RED} accentWords={['✗', '23']} />
          <WordReveal at={B(128) + 200} out={B(138)} text="✗  Sharp pad edges and force totals remain unresolved" size={42} every={3} accent={RED} accentWords={['✗', 'unresolved']} />
          <WordReveal at={B(128) + 270} out={B(138)} text="✓  Bookkeeping is solid: all 64 scenarios replayed to 2 × 10⁻¹² agreement" size={42} every={3} accent={GRN} accentWords={['✓', 'solid:']} />
        </div>
      </AbsoluteFill>

      <Heading at={B(138)} out={B(146)} kicker="NEXT" title="Turn the biggest unknown into a measurement" color={GRN} />
      <AbsoluteFill style={{ padding: '300px 80px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 40 }}>
          <WordReveal at={B(138) + 20} out={B(146)} text="1 · Measure real Al/Kapton charge injection vs voltage and time" size={46} every={3} accent={GRN} accentWords={['1']} />
          <WordReveal at={B(138) + 90} out={B(146)} text="2 · Resolve the pad rim and edge fields properly" size={46} every={3} accent={GRN} accentWords={['2']} />
          <WordReveal at={B(138) + 160} out={B(146)} text="3 · Compare against surface-potential probes on a charged sample" size={46} every={3} accent={GRN} accentWords={['3']} />
        </div>
      </AbsoluteFill>

      {/* ===== OUTRO 146-150 ===== */}
      <Center>
        <Slam at={B(146)} out={B(150) + 90} size={34} mono color={CY} from={1.1}>64 SCENARIOS · 56 MOVIES · 2.87 M PADS</Slam>
        <div style={{ height: 24 }} />
        <Slam at={B(146) + 10} out={B(150) + 90} size={130} glow={AMB}>THE CONTACT</Slam>
        <Slam at={B(146) + 20} out={B(150) + 90} size={130} glow={AMB} color={AMB}>DECIDES.</Slam>
        <div style={{ height: 30 }} />
        <WordReveal at={B(146) + 50} out={B(150) + 90} text="David Chester · week of Oct 13, 2026 · private" size={32} every={3} color="#8a94a6" style={{ justifyContent: 'center' }} />
      </Center>

      <Flash at={[B(6), B(28), B(106), B(146)]} len={8} />
      <Overlay />
      <AbsoluteFill style={{ background: '#000', opacity: endFade }} />
    </AbsoluteFill>
  );
};
