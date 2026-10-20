import React from 'react';
import {
  AbsoluteFill, Img, interpolate, spring, useCurrentFrame, useVideoConfig, staticFile, Easing,
} from 'remotion';

export const FPS = 30;
export const BEAT = 15; // frames per beat at 120 BPM
export const BAR = 60;
export const b = (bars: number) => Math.round(bars * BAR);

export type Theme = { bg: string; ink: string; a1: string; a2: string; dim: string; grid: string };

export const clamp = { extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const };

export const ease = Easing.bezier(0.16, 1, 0.3, 1);

// Pulsing value on each beat (1 on beat, decays)
export const beatPulse = (frame: number, every = BEAT, decay = 6) => {
  const k = frame % every;
  return Math.exp(-k / decay);
};

export const Background: React.FC<{ theme: Theme; intensity?: number; variant?: 'grid' | 'dots' }> = ({ theme, intensity = 1, variant = 'grid' }) => {
  const f = useCurrentFrame();
  const p = beatPulse(f) * intensity;
  const off = (f * 0.6) % 80;
  return (
    <AbsoluteFill style={{ background: theme.bg, overflow: 'hidden' }}>
      <AbsoluteFill
        style={{
          backgroundImage:
            variant === 'grid'
              ? `linear-gradient(${theme.grid} 1px, transparent 1px), linear-gradient(90deg, ${theme.grid} 1px, transparent 1px)`
              : `radial-gradient(${theme.grid} 1.6px, transparent 1.6px)`,
          backgroundSize: '80px 80px',
          backgroundPosition: `${off}px ${off * 0.5}px`,
          opacity: 0.55 + 0.25 * p,
          transform: 'perspective(900px) rotateX(18deg) scale(1.4) translateY(-60px)',
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 40%, ${theme.a1}22 0%, transparent 55%), radial-gradient(ellipse at 80% 90%, ${theme.a2}1c 0%, transparent 50%)`,
        }}
      />
      <AbsoluteFill style={{ background: 'radial-gradient(ellipse at center, transparent 45%, rgba(0,0,0,0.75) 100%)' }} />
    </AbsoluteFill>
  );
};

// Scanlines + grain overlay
export const Overlay: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      <AbsoluteFill
        style={{
          backgroundImage: 'repeating-linear-gradient(0deg, rgba(255,255,255,0.025) 0px, rgba(255,255,255,0.025) 1px, transparent 2px, transparent 4px)',
          transform: `translateY(${(f % 4)}px)`,
        }}
      />
    </AbsoluteFill>
  );
};

// White flash on impacts
export const Flash: React.FC<{ at: number[]; color?: string; len?: number }> = ({ at, color = '#fff', len = 10 }) => {
  const f = useCurrentFrame();
  let o = 0;
  for (const a of at) if (f >= a && f < a + len) o = Math.max(o, interpolate(f, [a, a + len], [0.85, 0]));
  return <AbsoluteFill style={{ background: color, opacity: o, pointerEvents: 'none', mixBlendMode: 'screen' }} />;
};

// Text that slams in (scale down from large with blur) and optionally glitches out
export const Slam: React.FC<{
  children: React.ReactNode; at: number; out?: number; size?: number; color?: string; style?: React.CSSProperties;
  glow?: string; weight?: number; mono?: boolean; from?: number;
}> = ({ children, at, out = 99999, size = 120, color = '#fff', style, glow, weight = 700, mono, from = 1.8 }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const t = f - at;
  const s = interpolate(t, [0, 7], [from, 1], { ...clamp, easing: ease });
  const blur = interpolate(t, [0, 6], [14, 0], clamp);
  const o = Math.min(interpolate(t, [0, 4], [0, 1], clamp), interpolate(f, [out - 6, out], [1, 0], clamp));
  const shake = t < 8 ? Math.sin(t * 9) * (8 - t) * 0.9 : 0;
  return (
    <div
      style={{
        fontFamily: mono ? 'JetBrains Mono' : 'Space Grotesk',
        fontSize: size, fontWeight: weight, color, lineHeight: 1.0, letterSpacing: mono ? 0 : '-0.02em',
        transform: `scale(${s}) translate(${shake}px, ${-shake * 0.5}px)`, filter: `blur(${blur}px)`, opacity: o,
        textShadow: glow ? `0 0 24px ${glow}, 0 0 60px ${glow}88` : undefined, ...style,
      }}
    >
      {children}
    </div>
  );
};

// Words revealing one by one on beats
export const WordReveal: React.FC<{ text: string; at: number; out?: number; every?: number; size?: number; color?: string; accent?: string; accentWords?: string[]; style?: React.CSSProperties; mono?: boolean }> = ({ text, at, out = 99999, every = 4, size = 64, color = '#fff', accent, accentWords = [], style, mono }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const words = text.split(' ');
  const fo = interpolate(f, [out - 6, out], [1, 0], clamp);
  return (
    <div style={{ fontFamily: mono ? 'JetBrains Mono' : 'Space Grotesk', fontSize: size, fontWeight: 600, color, opacity: fo, display: 'flex', flexWrap: 'wrap', gap: `0 ${size * 0.28}px`, ...style }}>
      {words.map((w, i) => {
        const t = f - at - i * every;
        const o = interpolate(t, [0, 5], [0, 1], clamp);
        const y = interpolate(t, [0, 8], [30, 0], { ...clamp, easing: ease });
        const isA = accentWords.includes(w.replace(/[.,:!?]/g, ''));
        return (
          <span key={i} style={{ opacity: o, transform: `translateY(${y}px)`, display: 'inline-block', color: isA && accent ? accent : undefined }}>
            {w}
          </span>
        );
      })}
    </div>
  );
};

// Typewriter mono line
export const Typer: React.FC<{ text: string; at: number; cps?: number; style?: React.CSSProperties; caret?: boolean; out?: number }> = ({ text, at, cps = 40, style, caret = true, out = 99999 }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const n = Math.floor(((f - at) / FPS) * cps);
  const shown = text.slice(0, n);
  const blink = Math.floor(f / 8) % 2 === 0;
  return (
    <div style={{ fontFamily: 'JetBrains Mono', whiteSpace: 'pre', ...style }}>
      {shown}
      {caret && n < text.length + 20 ? <span style={{ opacity: blink ? 1 : 0 }}>▌</span> : null}
    </div>
  );
};

// Animated number counter
export const Counter: React.FC<{ from?: number; to: number; at: number; dur?: number; decimals?: number; prefix?: string; suffix?: string; style?: React.CSSProperties; out?: number }> = ({ from = 0, to, at, dur = 40, decimals = 0, prefix = '', suffix = '', style, out = 99999 }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const v = interpolate(f, [at, at + dur], [from, to], { ...clamp, easing: Easing.out(Easing.cubic) });
  const o = Math.min(interpolate(f, [at, at + 5], [0, 1], clamp), interpolate(f, [out - 6, out], [1, 0], clamp));
  const s = v.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  return <div style={{ fontFamily: 'Space Grotesk', fontVariantNumeric: 'tabular-nums', opacity: o, ...style }}>{prefix}{s}{suffix}</div>;
};

// Framed image with Ken Burns, slide-in and glow
export const Shot: React.FC<{
  src: string; at: number; out: number; x: number; y: number; w: number; h: number; fit?: 'cover' | 'contain';
  zoom?: [number, number]; pan?: [number, number, number, number]; border?: string; label?: string; labelColor?: string;
  from?: 'left' | 'right' | 'up' | 'down' | 'zoom'; rot?: number; bg?: string; objPos?: string;
}> = ({ src, at, out, x, y, w, h, fit = 'cover', zoom = [1.05, 1.15], pan = [0, 0, 0, 0], border = '#ffffff33', label, labelColor = '#fff', from = 'zoom', rot = 0, bg = '#000', objPos = 'center' }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (f < at || f >= out) return null;
  const t = f - at;
  const sp = spring({ frame: t, fps, config: { damping: 18, stiffness: 140 } });
  const exit = interpolate(f, [out - 8, out], [1, 0], clamp);
  const prog = (f - at) / Math.max(1, out - at);
  const z = zoom[0] + (zoom[1] - zoom[0]) * prog;
  const px = pan[0] + (pan[2] - pan[0]) * prog;
  const py = pan[1] + (pan[3] - pan[1]) * prog;
  let tx = 0, ty = 0, sc = 1;
  if (from === 'left') tx = (1 - sp) * -w * 1.2;
  if (from === 'right') tx = (1 - sp) * w * 1.2;
  if (from === 'up') ty = (1 - sp) * -h * 1.2;
  if (from === 'down') ty = (1 - sp) * h * 1.2;
  if (from === 'zoom') sc = 0.7 + 0.3 * sp;
  return (
    <div style={{ position: 'absolute', left: x, top: y, width: w, height: h, opacity: Math.min(sp * 1.4, 1) * exit, transform: `translate(${tx}px, ${ty}px) scale(${sc}) rotate(${rot}deg)` }}>
      <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', borderRadius: 14, border: `2px solid ${border}`, boxShadow: `0 30px 80px rgba(0,0,0,0.6), 0 0 40px ${border}`, background: bg }}>
        <Img src={staticFile(src)} style={{ width: '100%', height: '100%', objectFit: fit, objectPosition: objPos, transform: `scale(${z}) translate(${px}%, ${py}%)` }} />
      </div>
      {label ? (
        <div style={{ position: 'absolute', left: 18, bottom: -54, fontFamily: 'JetBrains Mono', fontSize: 26, color: labelColor, letterSpacing: '0.04em' }}>{label}</div>
      ) : null}
    </div>
  );
};

// Section tag at top-left: e.g. "01 / THE BENCH"
export const Tag: React.FC<{ at: number; out: number; num: string; title: string; color: string }> = ({ at, out, num, title, color }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const w = interpolate(f - at, [0, 14], [0, 1], { ...clamp, easing: ease });
  const o = interpolate(f, [out - 8, out], [1, 0], clamp);
  return (
    <div style={{ position: 'absolute', left: 70, top: 56, display: 'flex', alignItems: 'center', gap: 18, opacity: o, fontFamily: 'JetBrains Mono', fontSize: 26, letterSpacing: '0.18em', color: '#fff' }}>
      <span style={{ color }}>{num}</span>
      <span style={{ width: 80 * w, height: 2, background: color, display: 'inline-block' }} />
      <span style={{ opacity: w }}>{title}</span>
    </div>
  );
};

export const Chip: React.FC<{ text: string; at: number; out: number; x: number; y: number; color: string; size?: number }> = ({ text, at, out, x, y, color, size = 30 }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const t = f - at;
  const o = Math.min(interpolate(t, [0, 5], [0, 1], clamp), interpolate(f, [out - 6, out], [1, 0], clamp));
  const dx = interpolate(t, [0, 10], [-40, 0], { ...clamp, easing: ease });
  return (
    <div style={{ position: 'absolute', left: x, top: y, opacity: o, transform: `translateX(${dx}px)`, padding: '10px 20px', border: `2px solid ${color}`, borderRadius: 999, background: `${color}22`, color: '#fff', fontFamily: 'JetBrains Mono', fontSize: size, whiteSpace: 'nowrap', boxShadow: `0 0 24px ${color}55` }}>
      {text}
    </div>
  );
};

export const Center: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center', flexDirection: 'column', textAlign: 'center', ...style }}>{children}</AbsoluteFill>
);

// Glitch text effect (RGB split) — used for error messages
export const Glitch: React.FC<{ text: string; at: number; out: number; size?: number; color?: string; style?: React.CSSProperties }> = ({ text, at, out, size = 60, color = '#ff3b5c', style }) => {
  const f = useCurrentFrame();
  if (f < at || f >= out) return null;
  const j = (f * 7919) % 13;
  const on = j < 4;
  const dx = on ? (j - 2) * 6 : 0;
  const o = interpolate(f, [out - 5, out], [1, 0], clamp);
  const base: React.CSSProperties = { position: 'absolute', inset: 0, fontFamily: 'JetBrains Mono', fontSize: size, fontWeight: 700, whiteSpace: 'nowrap' };
  return (
    <div style={{ position: 'relative', height: size * 1.2, opacity: o, ...style }}>
      <div style={{ ...base, color: '#00e5ff', transform: `translateX(${-dx}px)`, opacity: 0.7 }}>{text}</div>
      <div style={{ ...base, color: '#ff00aa', transform: `translateX(${dx}px)`, opacity: 0.7 }}>{text}</div>
      <div style={{ ...base, color }}>{text}</div>
    </div>
  );
};
