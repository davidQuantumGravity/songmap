// The wiring editor: a patch instrument as modules and wires (instruments/patch.py). Drag from an output (right
// dot) to an input (left dot: audio into the module, or a knob row: modulation), click a wire to change its amount
// or remove it, click a module to turn its knobs. Every change rewrites the song's `patch` lines.
import { useEffect, useMemo, useRef, useState } from "react";
import type { Catalog } from "./api";
import { Knob } from "./ui";

export type PatchSpec = { modules: Record<string, Record<string, number | string>>; wires: string[];
  macros?: Record<string, { default: number; map: Record<string, [number, number]> }> };
type ModType = Catalog["modules"][number];
type Wire = { src: string; dst: string; knob: string | null; amount: number };

const W = 168, HEAD = 26, ROW = 17, SRC_W = 64;
const KIND_COLOR: Record<string, string> = {
  osc: "var(--c1)", noise: "var(--c8)", env: "var(--c5)", lfo: "var(--c6)", filter: "var(--c3)", shaper: "var(--c4)",
  physical: "var(--c7)", modal: "var(--c7)", fx: "var(--c2)", amp: "var(--c4)", mix: "var(--muted)", out: "var(--ink)",
};
const SOURCE_DOC: Record<string, string> = {
  vel: "the note's velocity (0..1): wire it into a filter or shaper so harder notes are brighter, not just louder",
  key: "the note's height in octaves above middle C: wire it into a cutoff so high notes stay bright",
  gate: "1 while the key is held, 0 after",
  rand: "a random value per note (-1..1): small amounts make each note slightly different, like a real player",
};

const parseWire = (s: string): Wire | null => {
  const m = s.match(/^\s*(\w+)\s*>\s*(\w+)(?:\.(\w+))?\s*(?:\*\s*(-?[\d.]+))?\s*$/);
  return m ? { src: m[1], dst: m[2], knob: m[3] ?? null, amount: m[4] ? +m[4] : 1 } : null;
};
const wireText = (w: Wire) => `${w.src}>${w.dst}` + (w.knob ? `.${w.knob}` : "") + (w.knob && w.amount !== 1 ? `*${+w.amount.toFixed(4)}` : "");
const fmt = (v: number, unit: string) => {
  const a = Math.abs(v);
  const n = a >= 1000 ? `${(v / 1000).toFixed(a >= 10000 ? 0 : 1)}k` : a >= 100 ? v.toFixed(0) : a >= 10 ? v.toFixed(1) : v.toFixed(2);
  return unit ? `${n} ${unit}` : n;
};

function FormulaField({ name, unit, text, editable, onSave, onNumber }: {
  name: string; unit: string; text: string; editable: boolean; onSave: (t: string) => void; onNumber: () => void;
}) {
  const [v, setV] = useState(text);
  useEffect(() => setV(text), [text]);
  const commit = () => { if (v.trim() && v.trim() !== text) onSave(v.trim()); };
  return (
    <label className="formula-field" title="A formula of the note; Enter saves">
      <span>ƒ {name}{unit ? ` (${unit})` : ""}</span>
      <input value={v} disabled={!editable} spellCheck={false} onChange={(e) => setV(e.target.value)} onBlur={commit}
             onKeyDown={(e) => { if (e.key === "Enter") commit(); if (e.key === "Escape") setV(text); }} />
      {editable && <button className="ghost small" onClick={onNumber} title="Back to a plain knob (its default)">number</button>}
    </label>
  );
}

export function PatchEditor({ name, spec, editable, catalog, onSave, onCopy, posKey }: {
  name: string; spec: PatchSpec; editable: boolean; catalog: Catalog; posKey: string;
  onSave: (spec: PatchSpec) => Promise<void>; onCopy: () => void;
}) {
  const types = useMemo(() => Object.fromEntries(catalog.modules.map((m) => [m.name, m])), [catalog]) as Record<string, ModType>;
  const wires = useMemo(() => spec.wires.map(parseWire).filter(Boolean) as Wire[], [spec]);
  const [sel, setSel] = useState<{ kind: "node"; id: string } | { kind: "wire"; i: number } | null>(null);
  const [pos, setPos] = useState<Record<string, [number, number]>>(() => {
    try { return JSON.parse(localStorage.getItem(posKey) || "{}"); } catch { return {}; }
  });
  const [live, setLive] = useState<Record<string, number>>({});
  const [drag, setDragState] = useState<null | { from: string; x: number; y: number }>(null);
  const dragRef = useRef<null | { from: string; x: number; y: number }>(null);
  const setDrag = (d: null | { from: string; x: number; y: number }) => { dragRef.current = d; setDragState(d); };
  const capture = (id: number) => { try { svg.current!.setPointerCapture(id); } catch { /* not a live pointer */ } };
  const moving = useRef<null | { id: string; dx: number; dy: number }>(null);
  const svg = useRef<SVGSVGElement>(null);
  useEffect(() => setLive({}), [spec]);
  useEffect(() => { try { localStorage.setItem(posKey, JSON.stringify(pos)); } catch { /* not kept */ } }, [pos, posKey]);

  // auto layout: a column per depth (sources first), unless the user moved a node
  const layout = useMemo(() => {
    const ids = Object.keys(spec.modules);
    const depth: Record<string, number> = {};
    const d = (id: string, seen: Set<string>): number => {
      if (depth[id] !== undefined) return depth[id];
      if (seen.has(id)) return 1;
      seen.add(id);
      const ins = wires.filter((w) => w.dst === id && spec.modules[w.src]);
      depth[id] = ins.length ? 1 + Math.max(...ins.map((w) => d(w.src, seen))) : 1;
      return depth[id];
    };
    ids.forEach((id) => d(id, new Set()));
    const cols: Record<number, string[]> = {};
    ids.forEach((id) => (cols[depth[id]] = [...(cols[depth[id]] ?? []), id]));
    const out: Record<string, [number, number]> = {};
    for (const [c, list] of Object.entries(cols)) {
      let y = 14;
      for (const id of list) {
        out[id] = pos[id] ?? [24 + SRC_W + 40 + (+c - 1) * (W + 46), y];
        y += HEAD + types[spec.modules[id].type as string]?.knobs.length * ROW + 22;
      }
    }
    return out;
  }, [spec, wires, pos, types]);
  const srcPos = (s: string, i: number): [number, number] => pos["@" + s] ?? [12, 14 + i * 34];
  const sources = catalog.sources;

  const portOut = (id: string): [number, number] => {
    if (sources.includes(id)) { const [x, y] = srcPos(id, sources.indexOf(id)); return [x + SRC_W, y + 11]; }
    const [x, y] = layout[id] ?? [0, 0];
    return [x + W, y + HEAD / 2];
  };
  const portIn = (id: string, knob: string | null): [number, number] => {
    const [x, y] = layout[id] ?? [0, 0];
    if (!knob) return [x, y + HEAD / 2];
    const ks = types[spec.modules[id]?.type as string]?.knobs ?? [];
    return [x, y + HEAD + ks.findIndex((k) => k.name === knob) * ROW + ROW / 2];
  };
  const curve = (a: [number, number], b: [number, number]) => {
    const dx = Math.max(40, Math.abs(b[0] - a[0]) / 2);
    return `M ${a[0]} ${a[1]} C ${a[0] + dx} ${a[1]}, ${b[0] - dx} ${b[1]}, ${b[0]} ${b[1]}`;
  };
  const height = Math.max(260, ...Object.entries(layout).map(([id, [, y]]) => y + HEAD + (types[spec.modules[id].type as string]?.knobs.length ?? 0) * ROW + 30), sources.length * 34 + 30);
  const width = Math.max(600, ...Object.values(layout).map(([x]) => x + W + 30));

  const save = (s: PatchSpec) => onSave(s);
  const setWires = (ws: Wire[]) => save({ ...spec, wires: ws.map(wireText) });
  const local = (e: React.PointerEvent | PointerEvent) => {
    const r = svg.current!.getBoundingClientRect();
    return [e.clientX - r.left, e.clientY - r.top] as [number, number];
  };

  const startWire = (e: React.PointerEvent, from: string) => {
    if (!editable) return;
    e.stopPropagation();
    capture(e.pointerId);
    const [x, y] = local(e);
    setDrag({ from, x, y });
  };
  const onMove = (e: React.PointerEvent) => {
    const dr = dragRef.current;
    if (dr) { const [x, y] = local(e); setDrag({ ...dr, x, y }); }
    else if (moving.current) {
      const [x, y] = local(e);
      const m = moving.current;
      setPos((p) => ({ ...p, [m.id]: [x - m.dx, y - m.dy] }));
    }
  };
  const onUp = (e: React.PointerEvent) => {
    moving.current = null;
    const drag = dragRef.current;
    if (!drag) return;
    const el = document.elementFromPoint(e.clientX, e.clientY) as Element | null;
    const port = el?.closest("[data-in]") as Element | null;
    setDrag(null);
    if (!port) return;
    const [dst, knob] = (port.getAttribute("data-in") ?? "").split(".");
    if (!dst || dst === drag.from) return;
    if (wires.some((w) => w.src === drag.from && w.dst === dst && (w.knob ?? "") === (knob ?? ""))) return;
    setWires([...wires, { src: drag.from, dst, knob: knob || null, amount: 1 }]);
  };
  const startMove = (e: React.PointerEvent, id: string) => {
    e.stopPropagation();
    const [x, y] = local(e);
    const [nx, ny] = id.startsWith("@") ? srcPos(id.slice(1), sources.indexOf(id.slice(1))) : layout[id];
    moving.current = { id, dx: x - nx, dy: y - ny };
    capture(e.pointerId);
    if (!id.startsWith("@")) setSel({ kind: "node", id });
  };

  const addModule = (type: string) => {
    let k = 1;
    while (spec.modules[`${type}${k}`]) k++;
    const id = type === "out" && !spec.modules.out ? "out" : `${type}${k}`;
    save({ ...spec, modules: { ...spec.modules, [id]: { type } } });
    setSel({ kind: "node", id });
  };
  const removeModule = (id: string) => {
    const mods = { ...spec.modules };
    delete mods[id];
    const macros = Object.fromEntries(Object.entries(spec.macros ?? {})
      .map(([m, mac]) => [m, { ...mac, map: Object.fromEntries(Object.entries(mac.map).filter(([t]) => !t.startsWith(id + "."))) }] as const)
      .filter(([, mac]) => Object.keys(mac.map).length));
    save({ modules: mods, wires: wires.filter((w) => w.src !== id && w.dst !== id).map(wireText), macros });
    setSel(null);
  };
  const setKnob = (id: string, knob: string, v: number) => {
    const t = types[spec.modules[id].type as string];
    const k = t.knobs.find((x) => x.name === knob)!;
    const m = { ...spec.modules[id] };
    if (Math.abs(v - k.default) < 1e-9) delete m[knob]; else m[knob] = +v.toPrecision(4);
    save({ ...spec, modules: { ...spec.modules, [id]: m } });
  };
  const knobVal = (id: string, k: ModType["knobs"][number]) => {
    const v = live[`${id}.${k.name}`] ?? spec.modules[id][k.name];
    if (typeof v === "string") return k.choices.includes(v) ? k.choices.indexOf(v) : k.default;
    return typeof v === "number" ? v : k.default;
  };
  // a knob written as a formula of the note (instruments/patch.py Expr): text that is no number and no choice
  const formula = (id: string, k: ModType["knobs"][number]): string | null => {
    const v = spec.modules[id]?.[k.name];
    return typeof v === "string" && !k.choices.includes(v) && isNaN(+v) ? v : null;
  };
  const setFormula = (id: string, knob: string, text: string | null) => {
    const m = { ...spec.modules[id] };
    if (text === null || !text.trim()) delete m[knob]; else m[knob] = text.trim();
    save({ ...spec, modules: { ...spec.modules, [id]: m } });
  };

  const selNode = sel?.kind === "node" ? sel.id : null;
  const selWire = sel?.kind === "wire" ? wires[sel.i] : null;
  return (
    <div className="patch">
      <div className="patch-tools">
        <b>patch/{name}</b>
        {!editable && <><span className="pill">library</span><button className="primary" onClick={onCopy} title="Copy this patch into the song so you can rewire it">Copy into song to edit</button></>}
        {editable && (
          <select value="" onChange={(e) => e.target.value && addModule(e.target.value)} title="Add a module">
            <option value="">+ module</option>
            {catalog.modules.map((m) => <option key={m.name} value={m.name}>{m.name} — {m.doc.slice(0, 48)}</option>)}
          </select>
        )}
        <span className="muted small">drag from a right dot to a left dot to connect · click a wire to edit it · drag a title to move</span>
      </div>
      <div className="patch-main">
        <div className="patch-canvas">
          <svg ref={svg} width={width} height={height} onPointerMove={onMove} onPointerUp={onUp} onPointerDown={() => setSel(null)}>
            {wires.map((w, i) => {
              if (!(w.src in spec.modules) && !sources.includes(w.src)) return null;
              const d = curve(portOut(w.src), portIn(w.dst, w.knob));
              return <g key={i} onPointerDown={(e) => { e.stopPropagation(); setSel({ kind: "wire", i }); }}>
                <path d={d} className="wire-hit" />
                <path d={d} className={"wire" + (w.knob ? " mod" : "") + (selWire === w ? " sel" : "")} />
              </g>;
            })}
            {drag && <path d={curve(portOut(drag.from), [drag.x, drag.y])} className="wire dragging" />}
            {sources.map((s, i) => {
              const [x, y] = srcPos(s, i);
              return <g key={s} className="src-node">
                <rect x={x} y={y} width={SRC_W} height={22} rx={11} onPointerDown={(e) => startMove(e, "@" + s)}><title>{SOURCE_DOC[s]}</title></rect>
                <text x={x + 10} y={y + 15}>{s}</text>
                <circle cx={x + SRC_W} cy={y + 11} r={5} className="port out" onPointerDown={(e) => startWire(e, s)} />
              </g>;
            })}
            {Object.entries(spec.modules).map(([id, m]) => {
              const t = types[m.type as string];
              if (!t) return null;
              const [x, y] = layout[id];
              const h = HEAD + t.knobs.length * ROW + 6;
              return (
                <g key={id} className={"node" + (selNode === id ? " sel" : "")}>
                  <rect x={x} y={y} width={W} height={h} rx={7} className="node-bg" onPointerDown={(e) => { e.stopPropagation(); setSel({ kind: "node", id }); }} />
                  <rect x={x} y={y} width={W} height={HEAD} rx={7} className="node-head" style={{ fill: KIND_COLOR[t.kind] }} onPointerDown={(e) => startMove(e, id)} />
                  <text x={x + 9} y={y + 17} className="node-title" pointerEvents="none">{id}<tspan className="node-type"> {t.name}</tspan></text>
                  {t.audio_in && <circle cx={x} cy={y + HEAD / 2} r={6} className="port in" data-in={id}><title>audio in</title></circle>}
                  <circle cx={x + W} cy={y + HEAD / 2} r={6} className={"port out" + (t.output === "control" ? " ctl" : "")} onPointerDown={(e) => startWire(e, id)}>
                    <title>{t.output === "control" ? "control out: wire it into a knob" : "audio out"}</title></circle>
                  {t.knobs.map((k, i) => {
                    const v = knobVal(id, k);
                    const ky = y + HEAD + i * ROW;
                    return <g key={k.name} data-in={`${id}.${k.name}`} onPointerDown={(e) => { e.stopPropagation(); setSel({ kind: "node", id }); }}>
                      <rect x={x + 1} y={ky} width={W - 2} height={ROW} className="knob-row" />
                      <circle cx={x} cy={ky + ROW / 2} r={4} className="port knobport" />
                      <text x={x + 9} y={ky + 12} className="knob-name">{k.name}</text>
                      <text x={x + W - 8} y={ky + 12} className={"knob-val" + (formula(id, k) ? " formula" : "")} textAnchor="end">
                        {formula(id, k) ? `ƒ ${formula(id, k)!.length > 14 ? formula(id, k)!.slice(0, 13) + "…" : formula(id, k)}`
                          : k.choices.length ? k.choices[Math.round(v)] : fmt(v, k.unit)}</text>
                      <title>{k.doc}</title>
                    </g>;
                  })}
                </g>
              );
            })}
          </svg>
        </div>
        <aside className="patch-side">
          {selNode && spec.modules[selNode] ? (() => {
            const t = types[spec.modules[selNode].type as string];
            return <>
              <h4>{selNode} <span className="muted">· {t.name}</span></h4>
              <p className="small">{t.doc}.</p>
              <div className="knobs">
                {t.knobs.filter((k) => !formula(selNode, k)).map((k) => (
                  <div key={k.name} className="knob-f">
                    <Knob label={k.name} value={knobVal(selNode, k)} min={k.lo} max={k.hi} step={k.choices.length ? 1 : 0} def={k.default}
                          curve={k.curve as "lin" | "log"} modified={k.name in spec.modules[selNode]}
                          format={(v) => (k.choices.length ? k.choices[Math.round(v)] : fmt(v, k.unit))} title={k.doc}
                          onChange={(v) => setLive((l) => ({ ...l, [`${selNode}.${k.name}`]: v }))}
                          onCommit={(v) => editable && setKnob(selNode, k.name, v)} />
                    {editable && !k.choices.length && (
                      <button className="ghost small f-btn" title="Write this knob as a formula of the note (velocity, pitch, time...)"
                              onClick={() => setFormula(selNode, k.name, `${+knobVal(selNode, k).toPrecision(4)}*(0.5+vel)`)}>ƒ</button>)}
                  </div>
                ))}
              </div>
              {t.knobs.filter((k) => formula(selNode, k)).map((k) => (
                <FormulaField key={k.name} name={k.name} unit={k.unit} text={formula(selNode, k)!} editable={editable}
                              onSave={(x) => setFormula(selNode, k.name, x)} onNumber={() => setFormula(selNode, k.name, null)} />
              ))}
              {t.knobs.some((k) => formula(selNode, k)) && (
                <p className="small muted">Formulas use vel (0..1), key (octaves above middle C), pitch, freq (Hz), gate (s),
                  rand (-1..1 per note), t (seconds: the knob moves over the note), pi, e, the patch's macros, and sin cos tan
                  tanh exp log log2 log10 sqrt abs floor min max clip.</p>
              )}
              <ul className="small knob-docs">{t.knobs.map((k) => <li key={k.name}><b>{k.name}</b>: {k.doc}</li>)}</ul>
              <p className="small muted">Wired in: {wires.filter((w) => w.dst === selNode).map(wireText).join(", ") || "nothing"}.
                Out to: {wires.filter((w) => w.src === selNode).map(wireText).join(", ") || "nothing"}.</p>
              {editable && <button onClick={() => removeModule(selNode)}>Remove {selNode}</button>}
            </>;
          })() : selWire ? (
            <>
              <h4>Wire {wireText(selWire)}</h4>
              <p className="small">{selWire.knob
                ? `Modulation: ${selWire.src} moves ${selWire.dst}'s ${selWire.knob}. ${types[spec.modules[selWire.dst]?.type as string]?.knobs.find((k) => k.name === selWire.knob)?.mod === "oct" ? "Each unit is an octave." : types[spec.modules[selWire.dst]?.type as string]?.knobs.find((k) => k.name === selWire.knob)?.mod === "semi" ? "Each unit is a semitone." : types[spec.modules[selWire.dst]?.type as string]?.knobs.find((k) => k.name === selWire.knob)?.mod === "set" ? "It replaces the knob: the signal is the level." : "It is added to the knob."}`
                : `Audio: ${selWire.src}'s sound flows into ${selWire.dst}.`}</p>
              {selWire.knob && editable && (
                <label className="row">amount <input type="number" step="0.1" value={selWire.amount}
                  onChange={(e) => setWires(wires.map((w) => (w === selWire ? { ...w, amount: +e.target.value } : w)))} /></label>
              )}
              {editable && <button onClick={() => { setWires(wires.filter((w) => w !== selWire)); setSel(null); }}>Remove wire</button>}
            </>
          ) : (
            <>
              <h4>How a patch works</h4>
              <p className="small">Sound starts at a <b>source</b> (an oscillator, noise, a string or a resonator), flows through
                <b> shapers</b> (filters, waveshapers, echoes) and an <b>amplifier</b>, and ends at <b>out</b>.</p>
              <p className="small"><b>Envelopes</b> and <b>LFOs</b> don't make sound: they move knobs. An envelope into an amplifier's
                gain is the note's loudness shape; into a filter's cutoff it is the "wah" at each note.</p>
              <p className="small"><b>vel</b> into a filter makes harder notes brighter: the reason real instruments sound alive.</p>
              <p className="small"><b>FM:</b> wire one oscillator's sound into another's input and it bends its phase
                (the <code>fm</code> knob sets how far): a sine into a sine is the electric piano and the bell.</p>
              {spec.macros && Object.keys(spec.macros).length > 0 && (
                <>
                  <h4>Macros</h4>
                  <p className="small muted">One knob that moves several (turn them in the Knobs view):</p>
                  <ul className="small knob-docs">{Object.entries(spec.macros).map(([m, mac]) => (
                    <li key={m}><b>{m}</b> moves {Object.entries(mac.map).map(([t, [a, b]]) => `${t} ${a}→${b}`).join(", ")}</li>))}</ul>
                </>
              )}
              <p className="small muted">Click a module or a wire to see what it does.</p>
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
