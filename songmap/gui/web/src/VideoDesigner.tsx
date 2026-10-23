// The video designer: what the song's video shows, where and how (visual/view.py). A live frame at the playhead
// with every layer's box on top: drag a box to move it, drag its corner to resize, click it to edit it. The
// panel sets the frame (size, theme, colours, which parts, colour by part), the layers (show, order, add,
// remove) and the selected layer's options. Save writes <song>.view.yaml, which exports and `songmap video` use.
import { useEffect, useRef, useState } from "react";
import { api, type Layer, type Summary, type View } from "./api";

const LAYER_DOC: Record<string, string> = {
  header: "title, section and bar, and the chord as a chip",
  letters: "the names of the notes sounding now",
  staff: "a grand staff, page by page, with the played part veiled",
  roll: "a scrolling piano roll around the playhead",
  progress: "a bar filling up over the song",
  sections: "the song's sections as a strip, the current one lit",
  text: "a caption, optionally only between two times",
};
const NEW_BOX: Record<string, Layer["box"]> = {
  header: [0.02, 0.03, 0.96, 0.09], letters: [0.02, 0.13, 0.96, 0.11], staff: [0.02, 0.26, 0.96, 0.46],
  roll: [0.02, 0.74, 0.96, 0.2], progress: [0.02, 0.975, 0.96, 0.017], sections: [0.02, 0.9, 0.96, 0.05], text: [0.1, 0.42, 0.8, 0.16],
};
const COLOR_KEYS: [string, string][] = [["bg", "background"], ["panel", "panels"], ["ink", "text"], ["muted", "secondary"], ["gold", "accent / playhead"]];
const r3 = (x: number) => Math.round(x * 1000) / 1000;

export function VideoDesigner({ path, text, time, summary, view, setView, ok, onSeek }: {
  path: string; text: string; time: number; summary: Summary | null; view: View; setView: (v: View) => void; ok: boolean;
  onSeek: (t: number) => void;
}) {
  const [img, setImg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [sel, setSel] = useState<number | null>(null);
  const [saved, setSaved] = useState<{ file: string; at: number } | null>(null);
  const [sizes, setSizes] = useState<Record<string, [number, number]>>({});
  const [defaults, setDefaults] = useState<View | null>(null);
  const stage = useRef<HTMLDivElement>(null);
  const drag = useRef<null | { i: number; mode: "move" | "size"; x: number; y: number; box: Layer["box"] }>(null);
  const [live, setLive] = useState<View>(view);
  useEffect(() => setLive(view), [view]);
  useEffect(() => {
    api.getView(path).then((r) => { setSizes(r.sizes); setDefaults(r.default); if (r.saved) setSaved({ file: r.file, at: 0 }); }).catch(() => undefined);
  }, [path]);

  // the preview: one frame at the playhead (debounced; the server caches the renderer)
  const t = Math.round(time * 10) / 10;
  useEffect(() => {
    if (!ok) return;
    const id = window.setTimeout(async () => {
      try {
        const url = await api.frameUrl(path, text, t, live);
        setImg((old) => { if (old) URL.revokeObjectURL(old); return url; });
        setErr(null);
      } catch (e) { setErr(String(e)); }
    }, 200);
    return () => window.clearTimeout(id);
  }, [path, text, t, live, ok]);

  const [W, H] = live.size;
  const commit = (v: View) => { setLive(v); setView(v); };
  const setLayer = (i: number, patch: Partial<Layer>) =>
    commit({ ...live, layers: live.layers.map((l, j) => (j === i ? { ...l, ...patch } as Layer : l)) });
  const move = (i: number, d: number) => {
    const j = i + d;
    if (j < 0 || j >= live.layers.length) return;
    const ls = [...live.layers]; [ls[i], ls[j]] = [ls[j], ls[i]];
    commit({ ...live, layers: ls }); setSel(j);
  };
  const add = (type: string) => {
    const layer: Layer = { type, box: NEW_BOX[type], ...(type === "text" ? { text: summary?.title ?? "Title", size: 0.06, from: r3(time), to: r3(time + 4) } : {}) };
    commit({ ...live, layers: [...live.layers, layer] }); setSel(live.layers.length);
  };

  const down = (e: React.PointerEvent, i: number, mode: "move" | "size") => {
    e.stopPropagation(); e.preventDefault();
    (e.currentTarget as Element).setPointerCapture?.(e.pointerId);
    setSel(i);
    drag.current = { i, mode, x: e.clientX, y: e.clientY, box: [...live.layers[i].box] as Layer["box"] };
  };
  const pmove = (e: React.PointerEvent) => {
    const d = drag.current;
    if (!d || !stage.current) return;
    const r = stage.current.getBoundingClientRect();
    const dx = (e.clientX - d.x) / r.width, dy = (e.clientY - d.y) / r.height;
    const [x, y, w, h] = d.box;
    const box: Layer["box"] = d.mode === "move"
      ? [r3(Math.min(1 - w, Math.max(0, x + dx))), r3(Math.min(1 - h, Math.max(0, y + dy))), w, h]
      : [x, y, r3(Math.max(0.02, Math.min(1 - x, w + dx))), r3(Math.max(0.01, Math.min(1 - y, h + dy)))];
    setLive({ ...live, layers: live.layers.map((l, j) => (j === d.i ? { ...l, box } : l)) });
  };
  const pup = () => { if (drag.current) { drag.current = null; setView(live); } };

  const save = async () => {
    try { const r = await api.saveView(path, live); setSaved({ file: r.file, at: Date.now() }); setErr(null); }
    catch (e) { setErr(String(e)); }
  };
  const pitched = summary?.parts.filter((p) => !p.kit).map((p) => p.name) ?? [];
  const shown = live.parts ?? pitched;
  const L = sel !== null ? live.layers[sel] : null;
  const num = (k: string, v: unknown, d: number) => (typeof v === "number" ? v : d);

  return (
    <div className="vd">
      <div className="vd-stage-wrap">
        <div className="vd-stage" ref={stage} style={{ aspectRatio: `${W} / ${H}` }} onPointerMove={pmove} onPointerUp={pup} onPointerDown={() => setSel(null)}>
          {img ? <img src={img} alt="frame" draggable={false} /> : <span className="muted">{ok ? "rendering a frame…" : "fix the errors to preview"}</span>}
          {live.layers.map((l, i) => l.show === false ? null : (
            <div key={i} className={"vd-box" + (sel === i ? " sel" : "")} title={`${l.type}: ${LAYER_DOC[l.type]}`}
                 style={{ left: `${l.box[0] * 100}%`, top: `${l.box[1] * 100}%`, width: `${l.box[2] * 100}%`, height: `${l.box[3] * 100}%` }}
                 onPointerDown={(e) => down(e, i, "move")}>
              <span className="vd-tag">{l.type}</span>
              <i className="vd-handle" onPointerDown={(e) => down(e, i, "size")} />
            </div>
          ))}
        </div>
        <div className="vd-under">
          <span className="muted small">{W}×{H} · frame at {time.toFixed(1)} s (move the playhead to preview another moment) · drag boxes to move, corners to resize</span>
          {err && <span className="warn-text small">{err}</span>}
        </div>
      </div>
      <aside className="vd-panel">
        <h4>Frame</h4>
        <div className="vd-grid">
          <label>size<select value={Object.entries(sizes).find(([, s]) => s[0] === W && s[1] === H)?.[0] ?? "custom"}
                             onChange={(e) => sizes[e.target.value] && commit({ ...live, size: sizes[e.target.value] })}>
            {Object.entries(sizes).map(([n, s]) => <option key={n} value={n}>{n} ({s[0]}×{s[1]})</option>)}
            <option value="custom">custom</option></select></label>
          <label>width<input type="number" value={W} step={2} onChange={(e) => commit({ ...live, size: [+e.target.value, H] })} /></label>
          <label>height<input type="number" value={H} step={2} onChange={(e) => commit({ ...live, size: [W, +e.target.value] })} /></label>
          <label>theme<select value={live.theme} onChange={(e) => commit({ ...live, theme: e.target.value as View["theme"] })}>
            <option value="light">light</option><option value="dark">dark</option></select></label>
          <label>page<input type="number" step={0.5} min={2} max={30} value={live.page_seconds} onChange={(e) => commit({ ...live, page_seconds: +e.target.value })} /></label>
          <label>notes coloured by<select value={live.color_by} onChange={(e) => commit({ ...live, color_by: e.target.value as View["color_by"] })}>
            <option value="spelling">36-EDO layer</option><option value="part">part</option></select></label>
        </div>
        <div className="vd-colors">
          {COLOR_KEYS.map(([k, label]) => (
            <label key={k} title={label}><input type="color" value={live.colors?.[k] ?? "#888888"} onChange={(e) => commit({ ...live, colors: { ...live.colors, [k]: e.target.value } })} />
              <span>{label}</span></label>
          ))}
          {Object.keys(live.colors ?? {}).length > 0 && <button className="ghost small" onClick={() => commit({ ...live, colors: {} })}>theme colours</button>}
        </div>
        <h4>Parts on screen</h4>
        <div className="chips">
          {pitched.map((p) => (
            <span key={p} className="vd-part">
              <button className={"chip" + (shown.includes(p) ? " on" : "")}
                      onClick={() => { const next = shown.includes(p) ? shown.filter((x) => x !== p) : [...shown, p]; commit({ ...live, parts: next.length === pitched.length ? null : next }); }}>{p}</button>
              {live.color_by === "part" && <input type="color" value={live.part_colors?.[p] ?? "#c48a12"}
                onChange={(e) => commit({ ...live, part_colors: { ...live.part_colors, [p]: e.target.value } })} />}
            </span>
          ))}
        </div>
        <h4>Layers <span className="muted small">(drawn top to bottom)</span></h4>
        <ul className="vd-layers">
          {live.layers.map((l, i) => (
            <li key={i} className={sel === i ? "on" : ""} onClick={() => setSel(i)}>
              <input type="checkbox" checked={l.show !== false} onChange={(e) => setLayer(i, { show: e.target.checked })} onClick={(e) => e.stopPropagation()} title="show" />
              <span className="vd-lname">{l.type}{l.type === "text" ? `: ${String(l.text ?? "").slice(0, 18)}` : ""}</span>
              <button className="ghost small" onClick={(e) => { e.stopPropagation(); move(i, -1); }}>↑</button>
              <button className="ghost small" onClick={(e) => { e.stopPropagation(); move(i, 1); }}>↓</button>
              <button className="ghost small" onClick={(e) => { e.stopPropagation(); commit({ ...live, layers: live.layers.filter((_, j) => j !== i) }); setSel(null); }}>✕</button>
            </li>
          ))}
        </ul>
        <div className="vd-add">
          {Object.keys(LAYER_DOC).map((t) => <button key={t} className="small" title={LAYER_DOC[t]} onClick={() => add(t)}>+ {t}</button>)}
        </div>
        {L && sel !== null && (
          <>
            <h4>{L.type} <span className="muted small">— {LAYER_DOC[L.type]}</span></h4>
            <div className="vd-grid">
              {(["x", "y", "w", "h"] as const).map((k, j) => (
                <label key={k}>{k} %<input type="number" step={0.5} value={r3(L.box[j] * 100)}
                  onChange={(e) => { const b = [...L.box] as Layer["box"]; b[j] = r3(+e.target.value / 100); setLayer(sel, { box: b }); }} /></label>
              ))}
              <label className="cb"><input type="checkbox" checked={L.panel ?? !["progress", "text"].includes(L.type)} onChange={(e) => setLayer(sel, { panel: e.target.checked })} /> panel</label>
            </div>
            {L.type === "header" && (
              <div className="vd-grid">
                {(["title", "info", "chord"] as const).map((k) => (
                  <label key={k} className="cb"><input type="checkbox" checked={L[k] !== false} onChange={(e) => setLayer(sel, { [k]: e.target.checked })} /> {k}</label>
                ))}
                <label className="wide">title text<input value={String(L.text ?? "")} placeholder={summary?.title} onChange={(e) => setLayer(sel, { text: e.target.value || undefined })} /></label>
              </div>
            )}
            {L.type === "staff" && (
              <div className="vd-grid">
                {(["veil", "chords"] as const).map((k) => (
                  <label key={k} className="cb"><input type="checkbox" checked={L[k] !== false} onChange={(e) => setLayer(sel, { [k]: e.target.checked })} /> {k === "veil" ? "veil the played part" : "chord symbols"}</label>
                ))}
              </div>
            )}
            {L.type === "roll" && (
              <div className="vd-grid">
                <label>before (s)<input type="number" step={0.5} min={0} value={num("before", L.before, 2)} onChange={(e) => setLayer(sel, { before: +e.target.value })} /></label>
                <label>after (s)<input type="number" step={0.5} min={0.5} value={num("after", L.after, 6)} onChange={(e) => setLayer(sel, { after: +e.target.value })} /></label>
              </div>
            )}
            {L.type === "progress" && (
              <div className="vd-grid"><label>thickness<input type="number" min={1} max={20} value={num("thickness", L.thickness, 3)} onChange={(e) => setLayer(sel, { thickness: +e.target.value })} /></label></div>
            )}
            {L.type === "text" && (
              <div className="vd-grid">
                <label className="wide">text<textarea rows={2} value={String(L.text ?? "")} onChange={(e) => setLayer(sel, { text: e.target.value })} /></label>
                <label>size %<input type="number" step={0.5} value={r3(num("size", L.size, 0.06) * 100)} onChange={(e) => setLayer(sel, { size: +e.target.value / 100 })} /></label>
                <label>align<select value={String(L.align ?? "center")} onChange={(e) => setLayer(sel, { align: e.target.value })}>
                  <option>left</option><option>center</option><option>right</option></select></label>
                <label>colour<input type="color" value={String(L.color ?? "#ffffff")} onChange={(e) => setLayer(sel, { color: e.target.value })} /></label>
                <label>fade (s)<input type="number" step={0.1} min={0} value={num("fade", L.fade, 0.4)} onChange={(e) => setLayer(sel, { fade: +e.target.value })} /></label>
                <label>from (s)<input type="number" step={0.1} value={L.from === undefined || L.from === null ? "" : Number(L.from)} placeholder="start"
                  onChange={(e) => setLayer(sel, { from: e.target.value === "" ? undefined : +e.target.value })} /></label>
                <label>to (s)<input type="number" step={0.1} value={L.to === undefined || L.to === null ? "" : Number(L.to)} placeholder="end"
                  onChange={(e) => setLayer(sel, { to: e.target.value === "" ? undefined : +e.target.value })} /></label>
                <button className="small" onClick={() => setLayer(sel, { from: r3(time) })}>from = playhead</button>
                <button className="small" onClick={() => setLayer(sel, { to: r3(time) })}>to = playhead</button>
                {typeof L.from === "number" && <button className="small ghost" onClick={() => onSeek(L.from as number)}>go to start</button>}
              </div>
            )}
          </>
        )}
        <div className="vd-save">
          <button className="primary" onClick={save}>Save view</button>
          {defaults && <button onClick={() => { commit(defaults); setSel(null); }}>Classic layout</button>}
          <span className="muted small">{saved ? `${saved.file}${saved.at ? " · saved" : ""}` : "not saved yet (exports use what you see)"}</span>
        </div>
      </aside>
    </div>
  );
}
