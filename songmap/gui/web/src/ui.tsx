// Shared controls: rotary knob, vertical fader, draggable splitter, persisted sizes.
import { useCallback, useEffect, useRef, useState } from "react";

const clamp = (x: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, x));

/** Vertical drag (or wheel) changes the value; Shift for fine steps; double-click resets.
 *  onChange fires while dragging, onCommit once on release. */
function useDragValue(value: number, min: number, max: number, step: number,
                      onChange: (v: number) => void, onCommit: (v: number) => void, pixels = 150) {
  const start = useRef<{ y: number; v: number } | null>(null);
  const live = useRef(value);
  live.current = value;
  const snap = (v: number) => clamp(Math.round(v / step) * step, min, max);
  const down = (e: React.PointerEvent) => {
    (e.target as Element).setPointerCapture(e.pointerId);
    start.current = { y: e.clientY, v: value };
    e.preventDefault();
  };
  const move = (e: React.PointerEvent) => {
    if (!start.current) return;
    const k = (max - min) / pixels * (e.shiftKey ? 0.1 : 1);
    onChange(snap(start.current.v + (start.current.y - e.clientY) * k));
  };
  const up = () => {
    if (!start.current) return;
    const changed = live.current !== start.current.v;
    start.current = null;
    if (changed) onCommit(live.current);
  };
  const wheel = (e: React.WheelEvent) => {
    const v = snap(value + (e.deltaY < 0 ? 1 : -1) * step * (e.shiftKey ? 1 : 5));
    onChange(v); onCommit(v);
  };
  return { onPointerDown: down, onPointerMove: move, onPointerUp: up, onPointerCancel: up, onWheel: wheel };
}

type Ctl = {
  value: number; min: number; max: number; step?: number; def?: number; label?: string;
  format?: (v: number) => string; onChange: (v: number) => void; onCommit: (v: number) => void; size?: number;
  title?: string; bipolar?: boolean;
};

export function Knob({ value, min, max, step = 0.01, def = 0, label, format, onChange, onCommit, size = 34, title, bipolar }: Ctl) {
  const h = useDragValue(value, min, max, step, onChange, onCommit);
  const f = (value - min) / (max - min);
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
    <div className="knob" title={title ?? label} onDoubleClick={() => { onChange(def); onCommit(def); }}>
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
  const h = useDragValue(value, min, max, step, onChange, onCommit, 220);
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
export function Splitter({ dir, value, set, min, max, invert }: {
  dir: "x" | "y"; value: number; set: (v: number) => void; min: number; max: number; invert?: boolean;
}) {
  const start = useRef<{ p: number; v: number } | null>(null);
  const [drag, setDrag] = useState(false);
  useEffect(() => { document.body.classList.toggle("dragging-" + dir, drag); }, [drag, dir]);
  return (
    <div className={`splitter splitter-${dir}` + (drag ? " on" : "")}
      onPointerDown={(e) => { (e.target as Element).setPointerCapture(e.pointerId); start.current = { p: dir === "x" ? e.clientX : e.clientY, v: value }; setDrag(true); }}
      onPointerMove={(e) => {
        if (!start.current) return;
        const d = (dir === "x" ? e.clientX : e.clientY) - start.current.p;
        set(clamp(start.current.v + (invert ? -d : d), min, max));
      }}
      onPointerUp={() => { start.current = null; setDrag(false); }} />
  );
}
