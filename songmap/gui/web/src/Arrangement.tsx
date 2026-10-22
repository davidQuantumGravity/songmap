// The arrangement overview: sections, bar ruler, chords, one lane per part (a mini piano roll; drums by piece),
// events, loop and playhead. Click to seek, drag on the ruler to set a loop, click a section to jump to its code.
import { useEffect, useMemo, useRef, useState } from "react";
import type { Part, Summary } from "./api";

const SECT = 22, BARS = 16, CHORDS = 20, LANE = 40, LABEL = 150;
const TOP = SECT + BARS + CHORDS;

type Props = {
  summary: Summary;
  time: number;
  loop: [number, number] | null;
  mute: Set<string>;
  solo: Set<string>;
  colorOf: (part: string) => string;
  sectionColor: (name: string) => string;
  onSeek: (t: number) => void;
  onLoop: (l: [number, number] | null) => void;
  onSection: (index: number) => void;
  onMute: (part: string) => void;
  onSolo: (part: string) => void;
};

const css = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

function pitchRange(p: Part): [number, number] {
  let lo = Infinity, hi = -Infinity;
  for (const n of p.notes) if (n[2] !== null) { lo = Math.min(lo, n[2]); hi = Math.max(hi, n[2]); }
  if (!isFinite(lo)) return [0, 1];
  return hi - lo < 12 ? [(lo + hi) / 2 - 6, (lo + hi) / 2 + 6] : [lo - 1, hi + 1];
}

function roundRect(g: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  g.beginPath();
  if (w <= 0 || h <= 0) return;
  r = Math.max(0, Math.min(r, w / 2, h / 2));
  g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r);
  g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath();
}

export function Arrangement(props: Props) {
  const { summary, time, loop, mute, solo, colorOf, sectionColor, onSeek, onLoop, onSection, onMute, onSolo } = props;
  const wrap = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [width, setWidth] = useState(800);
  const [zoom, setZoom] = useState(1);
  const [hover, setHover] = useState<{ x: number; y: number; t: number } | null>(null);
  const drag = useRef<{ t0: number; moved: boolean } | null>(null);
  const height = TOP + summary.parts.length * LANE + 6;
  const total = Math.max(summary.seconds, 1);
  const pxs = ((width - LABEL - 12) / total) * zoom;
  const ranges = useMemo(() => summary.parts.map(pitchRange), [summary]);
  const pieces = useMemo(() => summary.parts.map((p) => [...new Set(p.notes.map((n) => n[4]))].sort()), [summary]);
  const heard = (p: string) => !mute.has(p) && (solo.size === 0 || solo.has(p));

  useEffect(() => {
    const el = wrap.current!;
    const ro = new ResizeObserver(() => setWidth(el.clientWidth));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {                                     // follow the playhead when zoomed in
    const el = wrap.current;
    if (!el || zoom <= 1) return;
    const x = LABEL + time * pxs;
    if (x < el.scrollLeft + LABEL || x > el.scrollLeft + el.clientWidth - 40) el.scrollLeft = x - LABEL - 40;
  }, [time, pxs, zoom]);

  useEffect(() => {
    const c = canvas.current!;
    const W = LABEL + total * pxs + 12;
    const dpr = window.devicePixelRatio || 1;
    c.width = W * dpr; c.height = height * dpr;
    c.style.width = `${W}px`; c.style.height = `${height}px`;
    const g = c.getContext("2d")!;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    const ink = css("--ink"), muted = css("--muted"), line = css("--line"), accent = css("--accent");
    g.fillStyle = css("--panel"); g.fillRect(0, 0, W, height);
    const X = (t: number) => LABEL + t * pxs;
    g.textBaseline = "middle";

    // section blocks: a tinted band through every lane, a solid tab on top
    summary.sections.forEach((s) => {
      const col = sectionColor(s.name), x = X(s.start), w = (s.end - s.start) * pxs;
      g.fillStyle = col; g.globalAlpha = 0.07; g.fillRect(x, SECT, w, height - SECT); g.globalAlpha = 1;
      roundRect(g, x + 1, 2, w - 2, SECT - 4, 4); g.fillStyle = col; g.fill();
      g.save(); g.beginPath(); g.rect(x + 1, 0, w - 6, SECT); g.clip();
      g.fillStyle = "#fff"; g.font = "600 11px system-ui, sans-serif";
      g.fillText(s.name, x + 7, SECT / 2);
      g.restore();
    });
    // bar ruler + grid
    g.font = "10px system-ui, sans-serif";
    const every = pxs * (summary.bar_times[1] ?? 1) < 18 ? 8 : pxs * (summary.bar_times[1] ?? 1) < 36 ? 4 : 1;
    summary.bar_times.forEach((t, i) => {
      const x = Math.round(X(t)) + 0.5;
      g.strokeStyle = line;
      g.globalAlpha = i % 4 === 0 ? 0.9 : 0.35;
      g.beginPath(); g.moveTo(x, SECT + (i % 4 === 0 ? 2 : 9)); g.lineTo(x, height); g.stroke();
      g.globalAlpha = 1;
      if (i % every === 0 && i < summary.bar_times.length - 1) { g.fillStyle = muted; g.fillText(String(i + 1), x + 3, SECT + BARS / 2 + 1); }
    });
    g.strokeStyle = line; g.beginPath(); g.moveTo(0, TOP - CHORDS + 0.5); g.lineTo(W, TOP - CHORDS + 0.5); g.stroke();
    // chords as pills
    g.font = "11px system-ui, sans-serif";
    for (const [a, b, sym] of summary.chords) {
      const x = X(a) + 1, w = (b - a) * pxs - 2;
      if (w < 3) continue;
      roundRect(g, x, TOP - CHORDS + 3, w, CHORDS - 6, 3);
      g.fillStyle = css("--band2"); g.fill();
      g.save(); g.clip(); g.fillStyle = ink; g.fillText(sym, x + 4, TOP - CHORDS / 2); g.restore();
    }
    // lanes
    summary.parts.forEach((p, i) => {
      const y0 = TOP + i * LANE, col = colorOf(p.name), on = heard(p.name);
      g.strokeStyle = line; g.globalAlpha = 0.6;
      g.beginPath(); g.moveTo(0, y0 + 0.5); g.lineTo(W, y0 + 0.5); g.stroke();
      g.fillStyle = col;
      const base = on ? 1 : 0.18;
      if (p.kit) {
        const ps = pieces[i], rowH = (LANE - 8) / Math.max(ps.length, 1);
        for (const n of p.notes) {
          const k = ps.indexOf(n[4]);
          g.globalAlpha = base * (0.35 + 0.65 * n[3]);
          g.fillRect(X(n[0]), y0 + 4 + k * rowH, Math.max(2, Math.min(n[1] * pxs, 5)), Math.max(2, rowH - 1));
        }
      } else {
        const [lo, hi] = ranges[i], h = Math.max(2, Math.min(5, (LANE - 10) / Math.max(hi - lo, 1) * 1.6));
        for (const n of p.notes) {
          if (n[2] === null) continue;
          const y = y0 + LANE - 5 - ((n[2] - lo) / Math.max(hi - lo, 1)) * (LANE - 10);
          g.globalAlpha = base * (0.45 + 0.55 * n[3]);
          roundRect(g, X(n[0]), y - h / 2, Math.max(2, n[1] * pxs - 1), h, 1.5); g.fill();
        }
      }
      g.globalAlpha = 1;
    });
    // events: a flag on the ruler and a dashed line
    g.font = "600 10px system-ui, sans-serif";
    for (const e of summary.events) {
      const x = Math.round(X(e.time)) + 0.5;
      g.strokeStyle = accent; g.fillStyle = accent; g.globalAlpha = 0.8;
      g.setLineDash([3, 3]); g.beginPath(); g.moveTo(x, SECT + 2); g.lineTo(x, height); g.stroke(); g.setLineDash([]);
      g.globalAlpha = 1;
      g.beginPath(); g.moveTo(x, SECT + 2); g.lineTo(x + 7, SECT + 6); g.lineTo(x, SECT + 10); g.fill();
    }
  }, [summary, pxs, height, total, ranges, pieces, mute, solo]);  // eslint-disable-line react-hooks/exhaustive-deps

  const tAt = (e: React.PointerEvent | React.MouseEvent) => {
    const r = canvas.current!.getBoundingClientRect();
    return { t: Math.min(Math.max(0, (e.clientX - r.left - LABEL) / pxs), summary.seconds), y: e.clientY - r.top, x: e.clientX - r.left };
  };
  const down = (e: React.PointerEvent) => {
    const { t, y } = tAt(e);
    if (y < SECT) {
      const s = summary.sections.find((s) => t >= s.start && t < s.end);
      if (s) { onSection(s.index); onSeek(s.start); }
      return;
    }
    (e.target as Element).setPointerCapture(e.pointerId);
    drag.current = { t0: t, moved: false };
  };
  const move = (e: React.PointerEvent) => {
    const h = tAt(e);
    setHover(h);
    if (drag.current && h.y < TOP && Math.abs(h.t - drag.current.t0) * pxs > 4) {
      drag.current.moved = true;
      const snap = (t: number) => summary.bar_times.reduce((a, b) => (Math.abs(b - t) < Math.abs(a - t) ? b : a), 0);
      const a = snap(Math.min(h.t, drag.current.t0)), b = snap(Math.max(h.t, drag.current.t0));
      if (b > a) onLoop([a, b]);
    }
  };
  const up = (e: React.PointerEvent) => {
    if (drag.current && !drag.current.moved) onSeek(tAt(e).t);
    drag.current = null;
  };
  const wheel = (e: React.WheelEvent) => {
    if (!e.ctrlKey) return;
    e.preventDefault();
    setZoom((z) => Math.min(64, Math.max(1, z * (e.deltaY < 0 ? 1.25 : 0.8))));
  };

  const info = hover && (() => {
    const bar = summary.bar_times.findIndex((b) => b > hover.t);
    const sec = summary.sections.find((s) => hover.t >= s.start && hover.t < s.end);
    const ch = summary.chords.find(([a, b]) => hover.t >= a && hover.t < b);
    const lane = Math.floor((hover.y - TOP) / LANE);
    const part = lane >= 0 ? summary.parts[lane]?.name : undefined;
    return `${Math.floor(hover.t / 60)}:${(hover.t % 60).toFixed(2).padStart(5, "0")} · bar ${bar < 0 ? summary.bars : bar}` +
      (sec ? ` · ${sec.name}` : "") + (ch ? ` · ${ch[2]}` : "") + (part ? ` · ${part}` : "");
  })();

  return (
    <div className="arr">
      <div className="arr-tools">
        <button className="ghost" onClick={() => setZoom(1)} disabled={zoom === 1}>fit</button>
        <span className="muted">zoom</span>
        <input type="range" min={0} max={6} step={0.01} value={Math.log2(zoom)} onChange={(e) => setZoom(2 ** +e.target.value)} />
        <span className="muted">{zoom.toFixed(1)}×</span>
        {loop && <button className="ghost" onClick={() => onLoop(null)}>clear loop</button>}
        <span className="spacer" />
        <span className="muted hover-info">{info ?? "drag on the ruler to loop · ctrl+wheel to zoom · click a section to jump to its code"}</span>
      </div>
      <div className="arr-scroll" ref={wrap} onWheel={wheel}>
        <div className="arr-inner" style={{ height }}>
          <div className="labels" style={{ height, width: LABEL, marginRight: -LABEL }}>
            <div style={{ height: SECT + BARS }} className="lab-head">{summary.sections.length} sections · {summary.bars} bars</div>
            <div style={{ height: CHORDS }} className="lab-head">chords</div>
            {summary.parts.map((p) => (
              <div key={p.name} className={"lab" + (heard(p.name) ? "" : " off")} style={{ height: LANE }}
                   title={`${p.name}: ${p.kit ? "drum kit" : p.instrument} · ${p.count} events`}>
                <i style={{ background: colorOf(p.name) }} />
                <div className="lab-text"><b>{p.name}</b><small>{p.kit ? "kit" : p.instrument}</small></div>
                <button className={"m" + (mute.has(p.name) ? " on" : "")} onClick={() => onMute(p.name)} title="mute">M</button>
                <button className={"s" + (solo.has(p.name) ? " on" : "")} onClick={() => onSolo(p.name)} title="solo">S</button>
              </div>
            ))}
          </div>
          <canvas ref={canvas} onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerLeave={() => setHover(null)} />
          {loop && <div className="loop" style={{ left: LABEL + loop[0] * pxs, width: (loop[1] - loop[0]) * pxs, height }} />}
          <div className="playhead" style={{ transform: `translateX(${LABEL + time * pxs}px)`, height }} />
        </div>
      </div>
    </div>
  );
}
