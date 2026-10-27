// The piano roll: one part in one section. Generated parts (styles, motifs, figures) show their notes and
// can be baked into written notes; written notes are edited here and saved as `role="<notes>"` on the
// section's line. Rows are semitones, or sixth-steps in a 36-EDO song.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, type Summary } from "./api";
import { StepGrid } from "./StepGrid";
import { localBeat, sectionTime } from "./musicTiming";

type ClipJSON = {
  section: string; index: number; part: string; bars: number; beats_per_bar: number; start: number; end: number;
  tempo_spans: number[]; line: number | null; written: boolean; kit: boolean; shared: number;
  notes: { beat: number; dur: number; pitches: number[]; vel: number; art: string; slur: boolean; grace: boolean }[];
};
type N = { id: number; beat: number; dur: number; pitch: number; vel: number; art: string; slur: boolean; grace: boolean };

const NAMES = ["C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B"];
const SNAPS: [string, number][] = [["1/4", 1], ["1/8", 1 / 2], ["1/16", 1 / 4], ["1/8 triplet", 1 / 3], ["1/16 triplet", 1 / 6], ["1/32", 1 / 8]];
const KEY_W = 46, VEL_H = 70;
const isBlack = (k: number) => [1, 3, 6, 8, 10].includes(((k % 12) + 12) % 12);

export function PianoRoll({ path, text, summary, time, partHint, onApply, colorOf, onSeek }: {
  path: string; text: string; summary: Summary; time: number; partHint: string | null;
  onApply: (op: string, args: object) => Promise<void>; colorOf: (p: string) => string; onSeek: (t: number) => void;
}) {
  const pitched = summary.parts.filter((p) => !p.kit);
  const secAt = summary.sections.find((s) => time >= s.start && time < s.end) ?? summary.sections[0];
  const [secIdx, setSecIdx] = useState<number>(secAt?.index ?? 0);
  const [part, setPart] = useState<string>(partHint && pitched.some((p) => p.name === partHint) ? partHint : pitched[0]?.name ?? "");
  const [clip, setClip] = useState<ClipJSON | null>(null);
  const [notes, setNotes] = useState<N[]>([]);
  const [sel, setSel] = useState<Set<number>>(new Set());
  const [err, setErr] = useState<string | null>(null);
  const [snap, setSnap] = useState(1 / 4);
  const [pxb, setPxb] = useState(48);                   // pixels per beat
  const [rowH, setRowH] = useState(10);
  const [busy, setBusy] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);
  const drag = useRef<null | { mode: "move" | "resize" | "vel"; x0: number; y0: number; orig: N[]; changed: boolean; id: number }>(null);
  const nextId = useRef(1);
  const player = useRef<HTMLAudioElement>(new Audio());
  const edo36 = summary.tuning.includes("36");
  const step = edo36 ? 1 / 3 : 1;

  const isKit = !!summary.parts.find((p) => p.name === part)?.kit;
  // fetch the clip whenever the song, the section or the part changes
  useEffect(() => {
    if (!part || isKit) return;
    let live = true;
    api.clip(path, text, secIdx, part).then((c) => {
      if (!live) return;
      setClip(c); setErr(null);
      const ns: N[] = [];
      for (const n of c.notes) for (const p of n.pitches) ns.push({ id: nextId.current++, beat: n.beat, dur: n.dur, pitch: p, vel: n.vel, art: n.art, slur: n.slur, grace: n.grace });
      setNotes(ns); setSel(new Set());
    }).catch((e) => live && setErr(String(e)));
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [summary, secIdx, part]);

  const total = clip ? clip.bars * clip.beats_per_bar : 16;
  const [lo, hi] = useMemo(() => {
    const ps = notes.map((n) => n.pitch);
    const a = ps.length ? Math.min(...ps) : 60, b = ps.length ? Math.max(...ps) : 72;
    return [Math.max(12, Math.floor(Math.min(a - 7, (a + b) / 2 - 14))), Math.min(120, Math.ceil(Math.max(b + 7, (a + b) / 2 + 14)))];
  }, [clip]);                                                   // eslint-disable-line react-hooks/exhaustive-deps
  const rows = Math.round((hi - lo) / step);
  const W = total * pxb, H = rows * rowH;
  const yOf = (p: number) => (hi - p) / step * rowH;
  const pOf = (y: number) => Math.round(hi / step - y / rowH - 0.5) * step;
  const bOf = (x: number) => x / pxb;
  const snapB = (b: number) => Math.round(b / snap) * snap;

  // seconds <-> beats within the section (tempo may change)
  const secOfBeat = (b: number) => {
    if (!clip) return 0;
    return sectionTime(summary.sections[clip.index], b);
  };
  const beatOfSec = (s: number) => {
    if (!clip) return 0;
    return localBeat(summary.sections[clip.index], s);
  };
  const inSection = clip && time >= clip.start && time < clip.end;

  // scroll the notes into view when a clip loads
  useEffect(() => {
    const el = scroller.current;
    if (!el || !notes.length) return;
    const mid = notes.reduce((a, n) => a + n.pitch, 0) / notes.length;
    el.scrollTop = Math.max(0, yOf(mid) - el.clientHeight / 2);
  }, [clip]);                                                   // eslint-disable-line react-hooks/exhaustive-deps

  const audition = useCallback(async (ns: N[]) => {
    if (!ns.length) return;
    try {
      const t0 = Math.min(...ns.map((n) => n.beat));
      const url = await api.audition(path, text, part, ns.slice(0, 8).map((n) => ({ t: (n.beat - t0) * 0.5, pitch: n.pitch, vel: n.vel, gate: Math.min(1.2, Math.max(0.15, secOfBeat(n.beat + n.dur) - secOfBeat(n.beat))) })), null, {});
      const a = player.current; if (a.src) URL.revokeObjectURL(a.src); a.src = url; await a.play();
    } catch { /* auditions are best-effort */ }
  }, [path, text, part, clip]);                                 // eslint-disable-line react-hooks/exhaustive-deps

  const commit = async (ns: N[]) => {
    if (!clip) return;
    setBusy(true);
    try {
      await onApply("clip", { index: clip.index, part, notes: ns.map((n) => ({ beat: n.beat, dur: n.dur, pitches: [n.pitch], vel: n.vel, art: n.art, slur: n.slur, grace: n.grace })) });
    } catch (e) { setErr(String(e)); }
    setBusy(false);
  };
  const bake = async () => {
    if (!clip) return;
    setBusy(true);
    try { await onApply("bake", { index: clip.index, part }); } catch (e) { setErr(String(e)); }
    setBusy(false);
  };

  const editable = !!clip?.written;
  const local = (e: React.PointerEvent) => {
    const r = (e.currentTarget as SVGElement).closest("svg")!.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  };

  const downNote = (e: React.PointerEvent, n: N) => {
    e.stopPropagation();
    if (!editable) return;
    if (e.button === 2) { const ns = notes.filter((m) => m.id !== n.id); setNotes(ns); commit(ns); return; }
    const { x, y } = local(e);
    let s = sel;
    if (e.shiftKey) { s = new Set(sel); s.has(n.id) ? s.delete(n.id) : s.add(n.id); }
    else if (!sel.has(n.id)) s = new Set([n.id]);
    setSel(s);
    const nearEnd = x > (n.beat + n.dur) * pxb - 6;
    (e.currentTarget as Element).closest("svg")!.setPointerCapture(e.pointerId);
    drag.current = { mode: nearEnd ? "resize" : "move", x0: x, y0: y, orig: notes.map((m) => ({ ...m })), changed: false, id: n.id };
  };
  const downGrid = (e: React.PointerEvent) => {
    const { x, y } = local(e);
    if (y > H) return;
    if (!editable) { onSeek(clip ? secOfBeat(bOf(x)) : 0); return; }
    if (e.button !== 0) return;
    const last = notes.find((m) => sel.has(m.id));
    const n: N = { id: nextId.current++, beat: Math.max(0, Math.floor(bOf(x) / snap) * snap), dur: last?.dur ?? Math.max(snap, 0.5),
                   pitch: pOf(y), vel: last?.vel ?? 0.62, art: "normal", slur: false, grace: false };
    const ns = [...notes, n];
    setNotes(ns); setSel(new Set([n.id]));
    (e.currentTarget as Element).closest("svg")!.setPointerCapture(e.pointerId);
    drag.current = { mode: "resize", x0: x, y0: y, orig: ns.map((m) => ({ ...m })), changed: true, id: n.id };
    audition([n]);
  };
  const downVel = (e: React.PointerEvent, n: N) => {
    e.stopPropagation();
    if (!editable) return;
    const s = sel.has(n.id) ? sel : new Set([n.id]);
    setSel(s);
    (e.currentTarget as Element).closest("svg")!.setPointerCapture(e.pointerId);
    drag.current = { mode: "vel", x0: 0, y0: local(e).y, orig: notes.map((m) => ({ ...m })), changed: false, id: n.id };
    move(e);
  };
  const move = (e: React.PointerEvent) => {
    const d = drag.current;
    if (!d) return;
    const { x, y } = local(e);
    const ids = sel.has(d.id) ? sel : new Set([d.id]);
    let ns: N[];
    if (d.mode === "vel") {
      const v = Math.min(1, Math.max(0.02, 1 - (y - H - 4) / (VEL_H - 8)));
      ns = d.orig.map((m) => (ids.has(m.id) || m.id === d.id ? { ...m, vel: v } : m));
    } else if (d.mode === "move") {
      const db = snapB(bOf(x - d.x0)), dp = Math.round((d.y0 - y) / rowH) * step;
      ns = d.orig.map((m) => (ids.has(m.id) ? { ...m, beat: Math.max(0, Math.min(total - snap, m.beat + db)), pitch: m.pitch + dp } : m));
    } else {
      const db = bOf(x - d.x0);
      ns = d.orig.map((m) => (ids.has(m.id) || m.id === d.id ? { ...m, dur: Math.max(snap, snapB(m.dur + db) || snap) } : m));
    }
    d.changed = true;
    setNotes(ns);
  };
  const up = () => {
    const d = drag.current;
    drag.current = null;
    if (!d || !d.changed) return;
    commit(notes);
    if (d.mode === "move") {
      const moved = notes.filter((m) => sel.has(m.id) || m.id === d.id);
      const o = d.orig.find((m) => m.id === d.id), n = notes.find((m) => m.id === d.id);
      if (o && n && o.pitch !== n.pitch) audition(moved.slice(0, 4));
    }
  };

  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if (!editable || (e.target as HTMLElement).closest(".cm-editor, input, select, textarea") || !sel.size) return;
      let ns: N[] | null = null;
      if (e.key === "Delete" || e.key === "Backspace") ns = notes.filter((m) => !sel.has(m.id));
      else if (e.key === "ArrowUp" || e.key === "ArrowDown") {
        const dp = (e.key === "ArrowUp" ? 1 : -1) * (e.ctrlKey || e.metaKey ? 12 : e.shiftKey ? 1 : step);
        ns = notes.map((m) => (sel.has(m.id) ? { ...m, pitch: m.pitch + dp } : m));
      } else if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
        const db = (e.key === "ArrowRight" ? 1 : -1) * snap;
        ns = notes.map((m) => (sel.has(m.id) ? { ...m, beat: Math.max(0, m.beat + db) } : m));
      } else if (e.key === "a" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); setSel(new Set(notes.map((m) => m.id))); return; }
      if (ns) { e.preventDefault(); e.stopPropagation(); setNotes(ns); commit(ns); if (e.key.startsWith("Arrow") && e.key !== "ArrowLeft" && e.key !== "ArrowRight") audition(ns.filter((m) => sel.has(m.id)).slice(0, 4)); }
    };
    window.addEventListener("keydown", k, true);
    return () => window.removeEventListener("keydown", k, true);
  });

  const label = (p: number) => {
    const k = Math.round(p), off = Math.round((p - k) * 3);
    return (off > 0 ? "^" : off < 0 ? "v" : "") + NAMES[((k % 12) + 12) % 12] + (Math.floor(k / 12) - 1);
  };
  const col = colorOf(part);
  const bpb = clip?.beats_per_bar ?? 4;

  return (
    <div className="roll">
      <div className="roll-tools">
        <label className="field-inline">section
          <select value={secIdx} onChange={(e) => setSecIdx(+e.target.value)}>
            {summary.sections.map((s) => <option key={s.index} value={s.index}>{s.name} · bar {s.bar + 1}</option>)}
          </select></label>
        <label className="field-inline">part
          <select value={part} onChange={(e) => setPart(e.target.value)}>
            {summary.parts.map((p) => <option key={p.name} value={p.name}>{p.name} ({p.kit ? "kit: step grid" : p.instrument})</option>)}
          </select></label>
        {!isKit && <>
        <label className="field-inline">snap
          <select value={snap} onChange={(e) => setSnap(+e.target.value)}>
            {SNAPS.map(([n, v]) => <option key={n} value={v}>{n}</option>)}
          </select></label>
        <label className="field-inline">zoom <input type="range" min={16} max={160} value={pxb} onChange={(e) => setPxb(+e.target.value)} /></label>
        <label className="field-inline">rows <input type="range" min={5} max={20} value={rowH} onChange={(e) => setRowH(+e.target.value)} /></label>
        </>}
        <span className="spacer" />
        {clip && !isKit && (editable
          ? <span className="pill ok-pill" title={`written on line ${clip.line}`}>written notes{clip.shared > 1 ? ` · line shared by ${clip.shared} sections` : ""}</span>
          : <><span className="pill">generated</span><button className="primary" disabled={busy} onClick={bake} title="Write what this part plays here as notes you can edit">Bake to notes</button></>)}
        {busy && <span className="muted small">saving…</span>}
      </div>
      {err && <p className="warn-text small pad">{err}</p>}
      {isKit ? <StepGrid path={path} text={text} summary={summary} index={secIdx} part={part} time={time} onApply={onApply} color={col} /> :
       !part ? <p className="pad muted">This song has no parts.</p> : (
        <div className="roll-scroll" ref={scroller}>
          <div className="roll-inner" style={{ width: W + KEY_W, height: H + VEL_H }}>
            <div className="roll-keys" style={{ height: H }}>
              {Array.from({ length: rows }, (_, i) => {
                const p = hi - (i + 1) * step;
                const k = Math.round(p), micro = Math.abs(p - k) > 1e-6;
                return <div key={i} className={"rk" + (isBlack(k) && !micro ? " black" : "") + (micro ? " micro" : "")} style={{ height: rowH }}
                            onPointerDown={() => audition([{ id: 0, beat: 0, dur: 1, pitch: p, vel: 0.7, art: "normal", slur: false, grace: false }])}>
                  {!micro && k % 12 === 0 && rowH >= 7 ? label(p) : ""}</div>;
              })}
            </div>
            <svg width={W} height={H + VEL_H} className={"roll-svg" + (editable ? " editable" : "")} style={{ left: KEY_W }}
                 onPointerDown={downGrid} onPointerMove={move} onPointerUp={up} onContextMenu={(e) => e.preventDefault()}>
              {Array.from({ length: rows }, (_, i) => {
                const p = hi - (i + 1) * step, k = Math.round(p), micro = Math.abs(p - k) > 1e-6;
                return <rect key={i} x={0} y={i * rowH} width={W} height={rowH} className={micro ? "row-micro" : isBlack(k) ? "row-black" : "row-white"} />;
              })}
              {Array.from({ length: Math.round(total / snap) + 1 }, (_, i) => {
                const b = i * snap, isBar = Math.abs(b / bpb - Math.round(b / bpb)) < 1e-6, isBeat = Math.abs(b - Math.round(b)) < 1e-6;
                return <line key={i} x1={b * pxb} x2={b * pxb} y1={0} y2={H} className={isBar ? "gl-bar" : isBeat ? "gl-beat" : "gl-sub"} />;
              })}
              {Array.from({ length: Math.round(total / bpb) }, (_, i) => <text key={i} x={i * bpb * pxb + 4} y={11} className="bar-num">{i + 1}</text>)}
              {notes.map((n) => {
                const x = n.beat * pxb, w = Math.max(3, n.dur * pxb - 1), y = yOf(n.pitch) - rowH;
                return (
                  <g key={n.id} onPointerDown={(e) => downNote(e, n)} className={"note" + (sel.has(n.id) ? " sel" : "") + (n.grace ? " grace" : "") + (editable ? "" : " ghost")}>
                    <rect x={x} y={y + 1} width={w} height={Math.max(3, rowH - 2)} rx={2} style={{ fill: col, fillOpacity: 0.35 + 0.65 * n.vel }} />
                    {w > 34 && rowH >= 9 && <text x={x + 3} y={y + rowH - 2.5} className="note-label">{label(n.pitch)}</text>}
                    {editable && <rect x={x + w - 5} y={y + 1} width={5} height={Math.max(3, rowH - 2)} className="note-handle" />}
                  </g>
                );
              })}
              <rect x={0} y={H} width={W} height={VEL_H} className="vel-bg" />
              {notes.map((n) => (
                <line key={n.id} x1={n.beat * pxb + 2} x2={n.beat * pxb + 2} y1={H + VEL_H - 4} y2={H + VEL_H - 4 - n.vel * (VEL_H - 8)}
                      className={"vel-bar" + (sel.has(n.id) ? " sel" : "")} style={{ stroke: col }} onPointerDown={(e) => downVel(e, n)} />
              ))}
              {inSection && <line x1={beatOfSec(time) * pxb} x2={beatOfSec(time) * pxb} y1={0} y2={H + VEL_H} className="roll-playhead" />}
            </svg>
          </div>
        </div>
      )}
      {!isKit && <div className="roll-foot muted small">
        {editable ? "click to add · drag to move · drag the right edge to resize · right-click or Delete to remove · ↑↓ transpose (shift: semitone, ctrl: octave) · ←→ nudge · velocity: drag the bars"
                  : "Generated by the part's style or figures. Bake to notes to edit them here; the code keeps the result."}
      </div>}
    </div>
  );
}
