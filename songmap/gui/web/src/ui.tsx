// Shared controls: rotary knob, vertical fader, draggable splitter, persisted sizes.
import { useCallback, useEffect, useRef, useState } from "react";

const clamp = (x: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, x));

/** Maps a control's value to its travel 0..1 and back: linear, or logarithmic (Hz, seconds). */
function scale(min: number, max: number, curve: "lin" | "log" = "lin") {
  if (curve === "log" && min > 0) {
    const a = Math.log(min), b = Math.log(max);
    return { toN: (v: number) => (Math.log(clamp(v, min, max)) - a) / (b - a), fromN: (n: number) => Math.exp(a + clamp(n, 0, 1) * (b - a)) };
  }
  return { toN: (v: number) => (v - min) / (max - min), fromN: (n: number) => min + clamp(n, 0, 1) * (max - min) };
}

/** Round to the step, or (step 0) to 3 significant digits. */
function quantize(v: number, step: number, min: number, max: number) {
  if (step > 0) return clamp(Math.round(v / step) * step, min, max);
  if (v === 0) return 0;
  const k = Math.pow(10, 2 - Math.floor(Math.log10(Math.abs(v))));
  return clamp(Math.round(v * k) / k, min, max);
}

/** Vertical drag (or wheel) moves the control along its travel; Shift for fine moves; double-click resets.
 *  onChange fires while dragging, onCommit once on release. */
function useDragValue(value: number, min: number, max: number, step: number, curve: "lin" | "log",
                      onChange: (v: number) => void, onCommit: (v: number) => void, pixels = 150) {
  const start = useRef<{ y: number; n: number; v: number } | null>(null);
  const live = useRef(value);
  live.current = value;
  const sc = scale(min, max, curve);
  const down = (e: React.PointerEvent) => {
    (e.currentTarget as Element).setPointerCapture(e.pointerId);
    start.current = { y: e.clientY, n: sc.toN(value), v: value };
    e.preventDefault();
  };
  const move = (e: React.PointerEvent) => {
    if (!start.current) return;
    const dn = (start.current.y - e.clientY) / pixels * (e.shiftKey ? 0.1 : 1);
    onChange(quantize(sc.fromN(start.current.n + dn), step, min, max));
  };
  const up = () => {
    if (!start.current) return;
    const changed = live.current !== start.current.v;
    start.current = null;
    if (changed) onCommit(live.current);
  };
  const wheel = (e: React.WheelEvent) => {
    const v = quantize(sc.fromN(sc.toN(value) + (e.deltaY < 0 ? 1 : -1) * (e.shiftKey ? 0.005 : 0.03)), step, min, max);
    onChange(v); onCommit(v);
  };
  return { onPointerDown: down, onPointerMove: move, onPointerUp: up, onPointerCancel: up, onWheel: wheel };
}

type Ctl = {
  value: number; min: number; max: number; step?: number; def?: number; label?: string; curve?: "lin" | "log";
  format?: (v: number) => string; onChange: (v: number) => void; onCommit: (v: number) => void; size?: number;
  title?: string; bipolar?: boolean; modified?: boolean;
};

export function Knob({ value, min, max, step = 0.01, def = 0, label, curve = "lin", format, onChange, onCommit, size = 34, title, bipolar, modified }: Ctl) {
  const h = useDragValue(value, min, max, step, curve, onChange, onCommit);
  const f = scale(min, max, curve).toN(value);
  const a0 = -135, a1 = 135, a = a0 + f * (a1 - a0);
  const r = size / 2 - 3, c = size / 2;
  const pt = (deg: number) => [c + r * Math.sin((deg * Math.PI) / 180), c - r * Math.cos((deg * Math.PI) / 180)];
  const arc = (from: number, to: number) => {
    const [x0, y0] = pt(from), [x1, y1] = pt(to);
    return `M ${x0} ${y0} A ${r} ${r} 0 ${Math.abs(to - from) > 180 ? 1 : 0} ${to > from ? 1 : 0} ${x1} ${y1}`;
  };
  const zero = bipolar ? 0 : a0;
  const [px, py] = pt(a);
  return (
    <div className={"knob" + (modified ? " modified" : "")} title={title ?? label} onDoubleClick={() => { onChange(def); onCommit(def); }}>
      <svg width={size} height={size} {...h}>
        <path d={arc(a0, a1)} className="knob-track" />
        {Math.abs(a - zero) > 0.5 && <path d={a > zero ? arc(zero, a) : arc(a, zero)} className="knob-value" />}
        <line x1={c} y1={c} x2={px} y2={py} className="knob-needle" />
      </svg>
      {label && <span className="knob-label">{label}</span>}
      <span className="knob-num">{format ? format(value) : value.toFixed(2)}</span>
    </div>
  );
}

export function Fader({ value, min, max, step = 0.5, def = 0, format, onChange, onCommit, title }: Ctl) {
  const h = useDragValue(value, min, max, step, "lin", onChange, onCommit, 220);
  const f = (value - min) / (max - min);
  const zero = (0 - min) / (max - min);
  return (
    <div className="fader" title={title} onDoubleClick={() => { onChange(def); onCommit(def); }} {...h}>
      <div className="fader-track"><i className="fader-zero" style={{ bottom: `${zero * 100}%` }} />
        <i className="fader-fill" style={{ height: `${f * 100}%` }} /></div>
      <div className="fader-cap" style={{ bottom: `calc(${f * 100}% - 7px)` }} />
      <span className="fader-num">{format ? format(value) : value.toFixed(1)}</span>
    </div>
  );
}

/** A size remembered across sessions (try/catch: storage may be unavailable). */
export function useStored(key: string, initial: number): [number, (v: number) => void] {
  const [v, setV] = useState(() => {
    try { const s = localStorage.getItem(key); return s ? +s : initial; } catch { return initial; }
  });
  const set = useCallback((x: number) => {
    setV(x);
    try { localStorage.setItem(key, String(x)); } catch { /* not persisted */ }
  }, [key]);
  return [v, set];
}

/** A drag handle between panes. `dir` = "x" resizes widths, "y" heights; delta sign set by `invert`. */
export function Splitter({ dir, value, set, min, max, invert, area }: {
  dir: "x" | "y"; value: number; set: (v: number) => void; min: number; max: number; invert?: boolean; area?: string;
}) {
  const start = useRef<{ p: number; v: number } | null>(null);
  const [drag, setDrag] = useState(false);
  useEffect(() => { document.body.classList.toggle("dragging-" + dir, drag); }, [drag, dir]);
  return (
    <div className={`splitter splitter-${dir}` + (drag ? " on" : "")} style={{ gridArea: area }}
      onPointerDown={(e) => { (e.target as Element).setPointerCapture(e.pointerId); start.current = { p: dir === "x" ? e.clientX : e.clientY, v: value }; setDrag(true); }}
      onPointerMove={(e) => {
        if (!start.current) return;
        const d = (dir === "x" ? e.clientX : e.clientY) - start.current.p;
        set(clamp(start.current.v + (invert ? -d : d), min, max));
      }}
      onPointerUp={() => { start.current = null; setDrag(false); }} />
  );
}
