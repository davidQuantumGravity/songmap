// The instrument rack, as a tutorial. For each part's voice:
//   Learn  — what it imitates, how it is built (a clickable signal-flow diagram), why it sounds that way,
//            every knob in plain words, and recipes to try (A/B against your sound, keep the ones you like);
//   Knobs  — every param as knobs, grouped by the instrument's schema;
//   Wiring — a patch instrument's modules and wires (PatchEditor), or "build your own" from a starter patch.
// The audition column plays notes (or drum patterns) with the current knobs and shows the waveform and spectrum.
// Released knobs write the song's `inst`/`kit` lines; patches write `patch` lines.
import { useEffect, useMemo, useRef, useState } from "react";
import { api, type AuditionNote, type Catalog, type Guide, type GuideBlock, type InstrumentSpec, type ParamSpec, type Summary, type Voice } from "./api";
import { PatchEditor, type PatchSpec } from "./PatchEditor";
import { Knob } from "./ui";

export type VoiceEdit = { part: string; piece: string | null; use?: string; params?: Record<string, number | null>; clear?: boolean; current_use: string };

const NAMES = ["C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B"];
const noteName = (p: number) => {
  const r = Math.round(p * 3) / 3, k = Math.round(r), off = Math.round((r - k) * 3);
  return (off > 0 ? "↑" : off < 0 ? "↓" : "") + NAMES[((k % 12) + 12) % 12] + (Math.floor(k / 12) - 1);
};
function fmtValue(v: number, unit: string) {
  const a = Math.abs(v);
  const n = a >= 1000 ? `${(v / 1000).toFixed(a >= 10000 ? 0 : 1)}k` : a >= 100 ? v.toFixed(0) : a >= 10 ? v.toFixed(1) : v.toFixed(2);
  return unit ? `${n} ${unit}` : n;
}
const KIND_COLOR: Record<string, string> = {
  osc: "var(--c1)", noise: "var(--c8)", env: "var(--c5)", lfo: "var(--c6)", filter: "var(--c3)", shaper: "var(--c4)",
  physical: "var(--c7)", modal: "var(--c7)", fx: "var(--c2)", amp: "var(--c4)", mix: "var(--muted)", pitch: "var(--c6)",
};
const STARTER: Record<string, string> = { snare: "snare808", bass: "acid", pluck: "pluck", string_pluck: "pluck", clean: "bell", pad: "glass_pad", lead: "acid" };
const BLANK: PatchSpec = { modules: { osc1: { type: "osc" }, env1: { type: "env" }, amp: { type: "vca" }, out: { type: "out" } },
                           wires: ["osc1>amp", "env1>amp.gain", "amp>out"] };

/** k hits spread as evenly as possible over n steps (a Euclidean rhythm: 3 of 8 is the tresillo). */
export const euclid = (k: number, n = 16, rot = 0) =>
  Array.from({ length: n }, (_, i) => ((((i + rot) % n) * k) % n) < k ? "x" : ".").join("");

function Keyboard({ lo, hi, onNote, active }: { lo: number; hi: number; onNote: (p: number) => void; active: number | null }) {
  const keys = [];
  for (let p = lo; p <= hi; p++) keys.push(p);
  const black = (p: number) => [1, 3, 6, 8, 10].includes(((p % 12) + 12) % 12);
  const whites = keys.filter((p) => !black(p));
  const w = 100 / whites.length;
  return (
    <div className="kbd">
      {whites.map((p, i) => (
        <div key={p} className={"kw" + (active !== null && Math.round(active) === p ? " on" : "")} style={{ left: `${i * w}%`, width: `${w}%` }}
             onPointerDown={() => onNote(p)} title={noteName(p)}>{p % 12 === 0 && <span>{noteName(p)}</span>}</div>
      ))}
      {keys.filter(black).map((p) => {
        const i = whites.filter((x) => x < p).length;
        return <div key={p} className={"kb" + (active !== null && Math.round(active) === p ? " on" : "")} style={{ left: `${i * w - w * 0.3}%`, width: `${w * 0.6}%` }}
                    onPointerDown={() => onNote(p)} title={noteName(p)} />;
      })}
    </div>
  );
}

/** Signal flow: the guide's chain as blocks in columns (left to right), arrows between them. */
function Flow({ chain, sel, onSel }: { chain: GuideBlock[]; sel: string | null; onSel: (id: string | null) => void }) {
  const depth: Record<string, number> = {};
  const into = (id: string) => chain.filter((b) => b.to.includes(id));
  const d = (id: string, seen = new Set<string>()): number => {
    if (depth[id] !== undefined) return depth[id];
    if (seen.has(id)) return 0;
    seen.add(id);
    const ins = into(id);
    return (depth[id] = ins.length ? 1 + Math.max(...ins.map((b) => d(b.id, seen))) : 0);
  };
  chain.forEach((b) => d(b.id));
  const cols: Record<number, GuideBlock[]> = {};
  chain.forEach((b) => (cols[depth[b.id]] = [...(cols[depth[b.id]] ?? []), b]));
  const BW = 112, BH = 38, GX = 34, GY = 12;
  const pos: Record<string, [number, number]> = {};
  const ncols = Object.keys(cols).length;
  const maxRows = Math.max(...Object.values(cols).map((c) => c.length));
  const H = maxRows * (BH + GY) + GY;
  Object.entries(cols).forEach(([c, bs]) => {
    const top = (H - bs.length * (BH + GY) + GY) / 2;
    bs.forEach((b, i) => (pos[b.id] = [8 + +c * (BW + GX), top + i * (BH + GY)]));
  });
  const outX = 8 + ncols * (BW + GX);
  const W = outX + 50;
  return (
    <svg className="flow" width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
      <defs><marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="var(--muted)" /></marker></defs>
      {chain.flatMap((b) => b.to.map((t) => {
        const [x1, y1] = pos[b.id];
        const [x2, y2] = t === "out" || !pos[t] ? [outX, H / 2 - BH / 2] : pos[t];
        const ax = x1 + BW, ay = y1 + BH / 2, bx = x2, by = y2 + BH / 2;
        return <path key={b.id + t} d={`M${ax},${ay} C${ax + GX / 2},${ay} ${bx - GX / 2},${by} ${bx - 2},${by}`} className="flow-edge" markerEnd="url(#arr)" />;
      }))}
      {chain.map((b) => {
        const [x, y] = pos[b.id];
        return (
          <g key={b.id} className={"flow-block" + (sel === b.id ? " sel" : "")} onClick={() => onSel(sel === b.id ? null : b.id)}>
            <rect x={x} y={y} width={BW} height={BH} rx={7} style={{ stroke: KIND_COLOR[b.kind] ?? "var(--line2)" }} />
            <rect x={x} y={y} width={5} height={BH} rx={2} style={{ fill: KIND_COLOR[b.kind] ?? "var(--line2)" }} />
            <text x={x + 12} y={y + 16} className="fb-label">{b.label}</text>
            <text x={x + 12} y={y + 30} className="fb-kind">{b.kind}{b.params.length ? ` · ${b.params.length} knob${b.params.length > 1 ? "s" : ""}` : ""}</text>
            <title>{b.what}</title>
          </g>
        );
      })}
      <g className="flow-out"><circle cx={outX + 18} cy={H / 2} r={16} /><text x={outX + 18} y={H / 2 + 4} textAnchor="middle">out</text></g>
    </svg>
  );
}

/** Waveform (top) and spectrum (bottom, log frequency) of the last audition. */
function Scope({ url, label }: { url: string | null; label: string }) {
  const cv = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    if (!url) return;
    let live = true;
    (async () => {
      const buf = await (await fetch(url)).arrayBuffer();
      const ctx = new OfflineAudioContext(1, 1, 48000);
      const audio = await ctx.decodeAudioData(buf);
      if (!live || !cv.current) return;
      const x = audio.getChannelData(0);
      const c = cv.current, g = c.getContext("2d")!, W = c.width, H = c.height, h1 = H * 0.45;
      const css = (n: string) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
      g.fillStyle = css("--panel"); g.fillRect(0, 0, W, H);
      g.strokeStyle = css("--line"); g.beginPath(); g.moveTo(0, h1 / 2); g.lineTo(W, h1 / 2); g.stroke();
      g.fillStyle = css("--c3");
      const per = Math.max(1, Math.floor(x.length / W));
      for (let i = 0; i < W; i++) {
        let lo = 0, hi = 0;
        for (let j = i * per; j < Math.min(x.length, (i + 1) * per); j++) { lo = Math.min(lo, x[j]); hi = Math.max(hi, x[j]); }
        g.fillRect(i, h1 / 2 - hi * h1 / 2, 1, Math.max(1, (hi - lo) * h1 / 2));
      }
      // spectrum: 8192-point FFT over the loudest part (the attack), Hann window
      const N = 8192;
      let start = 0, peak = 0;
      for (let i = 0; i < x.length; i += 256) if (Math.abs(x[i]) > peak) { peak = Math.abs(x[i]); start = i; }
      start = Math.max(0, Math.min(start - 512, x.length - N));
      const re = new Float64Array(N), im = new Float64Array(N);
      for (let i = 0; i < N; i++) re[i] = (x[start + i] ?? 0) * (0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (N - 1)));
      fft(re, im);
      const y0 = h1 + 8, h2 = H - y0 - 14;
      g.fillStyle = css("--muted"); g.font = "9px system-ui";
      const fx = (f: number) => (Math.log10(f / 30) / Math.log10(20000 / 30)) * W;
      for (const f of [100, 1000, 10000]) { g.fillRect(fx(f), y0, 1, h2); g.fillText(f >= 1000 ? `${f / 1000}k` : `${f}`, fx(f) + 2, H - 3); }
      g.strokeStyle = css("--accent"); g.lineWidth = 1.5; g.beginPath();
      let first = true;
      for (let k = 2; k < N / 2; k++) {
        const f = (k * 48000) / N;
        if (f < 30) continue;
        const mag = 20 * Math.log10(Math.hypot(re[k], im[k]) / (N / 4) + 1e-9);
        const yy = y0 + h2 * Math.min(1, Math.max(0, -mag / 90));
        if (first) { g.moveTo(fx(f), yy); first = false; } else g.lineTo(fx(f), yy);
      }
      g.stroke();
    })().catch(() => undefined);
    return () => { live = false; };
  }, [url]);
  return <div className="scope"><canvas ref={cv} width={276} height={150} /><span className="muted small">{label}</span></div>;
}

function fft(re: Float64Array, im: Float64Array) {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const a = (-2 * Math.PI) / len, wr = Math.cos(a), wi = Math.sin(a);
    for (let i = 0; i < n; i += len) {
      let cr = 1, ci = 0;
      for (let k = 0; k < len / 2; k++) {
        const ur = re[i + k], ui = im[i + k];
        const vr = re[i + k + len / 2] * cr - im[i + k + len / 2] * ci, vi = re[i + k + len / 2] * ci + im[i + k + len / 2] * cr;
        re[i + k] = ur + vr; im[i + k] = ui + vi; re[i + k + len / 2] = ur - vr; im[i + k + len / 2] = ui - vi;
        [cr, ci] = [cr * wr - ci * wi, cr * wi + ci * wr];
      }
    }
  }
}

export function Rack({ path, text, summary, catalog, onEdit, onApply, colorOf, time }: {
  path: string; text: string; summary: Summary; catalog: Catalog | null; time: number;
  onEdit: (e: VoiceEdit) => Promise<void>; onApply: (op: string, args: object) => Promise<void>; colorOf: (p: string) => string;
}) {
  const parts = summary.parts;
  const [sel, setSel] = useState<{ part: string; piece: string | null }>(() => ({ part: parts.find((p) => !p.kit)?.name ?? parts[0]?.name, piece: null }));
  const [view, setView] = useState<"learn" | "knobs" | "wiring">("learn");
  const [block, setBlock] = useState<string | null>(null);
  const [live, setLive] = useState<Record<string, number>>({});
  const [vel, setVel] = useState(0.7);
  const [gate, setGate] = useState(0.6);
  const [offset, setOffset] = useState(0);
  const [auto, setAuto] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [last, setLast] = useState<number | null>(null);
  const [scope, setScope] = useState<{ url: string; label: string } | null>(null);
  const [pattern, setPattern] = useState<string>("....x.......x...");
  const [hits, setHits] = useState(2);
  const player = useRef<HTMLAudioElement>(new Audio());
  const lastNotes = useRef<AuditionNote[]>([{ t: 0, pitch: 60, vel: 0.7, gate: 0.6 }]);

  const pv = summary.voices[sel.part];
  const partSpec = parts.find((p) => p.name === sel.part);
  const isKit = !!pv && "kit" in pv && pv.kit === true;
  const pieces = isKit ? Object.keys((pv as { pieces: Record<string, Voice> }).pieces) : [];
  const piece = isKit ? (sel.piece && pieces.includes(sel.piece) ? sel.piece : pieces[0]) : null;
  const voice: Voice | null = !pv || ("error" in pv && pv.error) ? null : isKit ? (pv as { pieces: Record<string, Voice> }).pieces[piece!] : (pv as Voice);
  const isPatch = voice?.instrument === "patch";
  const spec: InstrumentSpec | undefined = isPatch
    ? (voice?.schema ? { name: voice.use, family: "synth", mono: false, params: voice.schema } : undefined)
    : catalog?.instruments.find((i) => i.name === voice?.instrument);
  const guide: Guide | undefined = voice && !isPatch ? catalog?.guides?.[voice.instrument] : undefined;
  const presets = (voice && catalog?.presets[voice.instrument]) ?? [];
  const preset = presets.find((p) => p.name === voice?.preset);
  const patchName = isPatch ? voice!.patch ?? voice!.use.split("/")[1] : null;
  const patchSpec: PatchSpec | null = patchName ? (summary.patches?.[patchName] ?? catalog?.patch_library?.[patchName] ?? null) as PatchSpec | null : null;
  const secNow = summary.sections.find((s) => time >= s.start && time < s.end) ?? summary.sections[0];
  useEffect(() => setLive({}), [summary, sel.part, piece]);
  useEffect(() => { setBlock(null); if (isPatch) setView("wiring"); else if (view === "wiring") setView("learn"); }, [voice?.use]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (guide?.pattern) setPattern(guide.pattern); }, [guide]);

  const groups = useMemo(() => {
    const g = new Map<string, ParamSpec[]>();
    for (const q of spec?.params ?? []) g.set(q.group, [...(g.get(q.group) ?? []), q]);
    return [...g.entries()];
  }, [spec]);
  const paramSpec = (name: string) => spec?.params.find((q) => q.name === name);

  const phrase = (): AuditionNote[] => {
    const ns = (partSpec?.notes ?? []).filter((n) => (piece === null || n[4] === piece) && n[0] >= time - 0.01).slice(0, 24);
    if (!ns.length) return [];
    const t0 = ns[0][0];
    return ns.filter((n) => n[0] - t0 < 4).map((n) => ({ t: n[0] - t0, pitch: n[2] ?? 60, vel: n[3], gate: Math.min(n[1], 3) }));
  };

  const play = async (notes: AuditionNote[], overrides: Record<string, number> = live, label = "your sound") => {
    if (!notes.length) return;
    lastNotes.current = notes;
    try {
      const url = await api.audition(path, text, sel.part, notes, piece, overrides);
      const a = player.current;
      a.src = url; await a.play();
      setScope((old) => { if (old) URL.revokeObjectURL(old.url); return { url, label }; });
      setErr(null);
    } catch (e) { setErr(String(e)); }
  };
  const note = (p: number) => { const pitch = p + offset / 3; setLast(pitch); play([{ t: 0, pitch, vel, gate }]); };
  const chord = () => { const r = (last ?? 60); play([0, 4, 7, 12].map((i) => ({ t: 0, pitch: r + i, vel, gate: gate * 2 }))); };
  const arp = () => { const r = (last ?? 60); play([0, 4, 7, 12, 7, 4].map((i, k) => ({ t: k * 0.16, pitch: r + i, vel, gate: 0.15 }))); };
  const sweep = () => { const r = (last ?? 60); play([0.15, 0.35, 0.55, 0.75, 0.95].map((v, k) => ({ t: k * Math.max(0.35, gate + 0.15), pitch: r, vel: v, gate }))); };
  const stepSec = 60 / summary.tempo / 4;
  const LEVEL: Record<string, number> = { X: 1, x: 0.78, "-": 0.55, o: 0.38 };
  const playPattern = (p = pattern, overrides = live, label = "your sound") =>
    play([...p].flatMap((c, i) => (c === "." ? [] : [{ t: i * stepSec, pitch: 60, vel: LEVEL[c] ?? 0.78, gate: 0.2 }])), overrides, label);

  const commit = async (q: ParamSpec, v: number | null) => {
    if (!voice) return;
    const overrides = v === null ? {} : { ...live, [q.name]: v };
    if (auto) isKit ? playPattern(pattern, overrides as Record<string, number>) : play(lastNotes.current, overrides as Record<string, number>);
    await onEdit({ part: sel.part, piece, params: { [q.name]: v }, current_use: voice.use });
  };
  const switchTo = async (use: string, clear: boolean) => {
    if (!voice) return;
    await onEdit({ part: sel.part, piece, use, clear, current_use: voice.use });
  };
  const tryRecipe = (set: Record<string, number>, ab: boolean) => {
    const notes = isKit ? null : lastNotes.current;
    const run = (o: Record<string, number>, label: string) => (isKit ? playPattern(pattern, o, label) : play(notes!, o, label));
    if (!ab) return run({ ...live, ...set }, "recipe");
    run(live, "A: your sound");
    window.setTimeout(() => run({ ...live, ...set }, "B: recipe"), isKit ? 16 * stepSec * 1000 + 400 : 1600);
  };
  const keepRecipe = (set: Record<string, number>) =>
    voice && onEdit({ part: sel.part, piece, params: Object.fromEntries(Object.entries(set)), current_use: voice.use });
  const buildOwn = async () => {
    if (!voice || !catalog) return;
    const starter = STARTER[voice.instrument] ?? "";
    const choice = prompt(`Build a patch for ${sel.part}${piece ? "." + piece : ""}.\nStart from: ${["blank", ...Object.keys(catalog.patch_library)].join(", ")}`, starter || "blank");
    if (!choice) return;
    const base = choice === "blank" ? BLANK : catalog.patch_library[choice];
    if (!base) { setErr(`no starter patch '${choice}'`); return; }
    const name = (prompt("Name your patch (letters, digits, _)", `my_${(piece ?? sel.part).replace(/\W/g, "_")}`) ?? "").trim();
    if (!/^[A-Za-z_]\w*$/.test(name)) return;
    await onApply("patch", { name, spec: { modules: base.modules, wires: base.wires } });
    await switchTo(`patch/${name}`, true);
    setView("wiring");
  };
  const writePattern = () => secNow && onApply("steps", { index: secNow.index, part: sel.part, piece,
    steps: Array.from({ length: secNow.bars }, () => pattern).join("|") });

  const modified = voice ? Object.keys(voice.params).filter((k) => spec?.params.some((q) => q.name === k)) : [];
  const families = useMemo(() => {
    const f = new Map<string, InstrumentSpec[]>();
    for (const i of catalog?.instruments ?? []) f.set(i.family, [...(f.get(i.family) ?? []), i]);
    return [...f.entries()];
  }, [catalog]);

  const knob = (q: ParamSpec, explained = false) => {
    const raw = live[q.name] ?? voice!.values[q.name];
    const v = typeof raw === "number" ? raw : q.default;
    const def = Number(voice!.preset_values?.[q.name] ?? q.default);
    const g = guide?.params[q.name];
    const k = <Knob key={q.name} label={q.name} value={v} min={q.lo} max={q.hi} step={0} def={def} curve={q.curve}
                    modified={q.name in voice!.params} format={(x) => fmtValue(x, q.unit)}
                    title={`${q.name}${g ? ": " + g.says : q.doc ? ": " + q.doc : ""}\n${fmtValue(q.lo, q.unit)} … ${fmtValue(q.hi, q.unit)} · preset ${fmtValue(def, q.unit)}\ndrag · shift for fine · double-click resets`}
                    onChange={(x) => setLive((l) => ({ ...l, [q.name]: x }))}
                    onCommit={(x) => commit(q, Math.abs(x - def) < 1e-9 ? null : x)} />;
    if (!explained || !g) return k;
    return <div key={q.name} className="kx">{k}<div><p>{g.says}</p><p className="small"><b>↑</b> {g.up}<br /><b>↓</b> {g.down}</p></div></div>;
  };
  const selBlock = guide?.chain.find((b) => b.id === block) ?? null;

  return (
    <div className="rack">
      <div className="rack-parts">
        {parts.map((p) => {
          const v = summary.voices[p.name];
          const kitPieces = v && "kit" in v && v.kit ? Object.keys(v.pieces) : [];
          return (
            <div key={p.name}>
              <div className={"rack-part" + (sel.part === p.name && (!kitPieces.length) ? " on" : "")} onClick={() => setSel({ part: p.name, piece: null })}>
                <i style={{ background: colorOf(p.name) }} /><b>{p.name}</b><small>{p.kit ? "kit" : p.instrument}</small>
              </div>
              {sel.part === p.name && kitPieces.map((k) => (
                <div key={k} className={"rack-piece" + (piece === k ? " on" : "")} onClick={() => setSel({ part: p.name, piece: k })}>
                  {k}<small>{v && "kit" in v && v.kit ? v.pieces[k].use : ""}</small>
                </div>
              ))}
            </div>
          );
        })}
      </div>
      <div className="rack-body">
        {!voice ? <p className="pad muted">{pv && "error" in pv ? pv.error : "Pick a part."}</p> : (
          <>
            <div className="rack-head">
              <div className="rack-title">
                <b>{sel.part}{piece ? ` · ${piece}` : ""}{guide ? <span className="muted"> — {guide.title}</span> : null}</b>
                <span className="muted small">{voice.use}{modified.length ? ` · ${modified.length} knob${modified.length > 1 ? "s" : ""} changed` : ""}</span>
              </div>
              <span className="seg">
                {!isPatch && <button className={view === "learn" ? "on" : ""} onClick={() => setView("learn")}>Learn</button>}
                <button className={view === "knobs" ? "on" : ""} onClick={() => setView("knobs")}>Knobs</button>
                <button className={view === "wiring" ? "on" : ""} onClick={() => setView("wiring")}>Wiring</button>
              </span>
              <label className="field"><span>instrument</span>
                <select value={isPatch ? "patch" : voice.instrument} onChange={(e) => switchTo(e.target.value === "sampler" ? "sampler/salamander" : e.target.value, true)}>
                  {families.map(([fam, list]) => (
                    <optgroup key={fam} label={fam}>{list.map((i) => <option key={i.name} value={i.name}>{i.name}</option>)}</optgroup>
                  ))}
                  {isPatch && <option value="patch">patch</option>}
                </select>
              </label>
              {isPatch ? (
                <label className="field"><span>patch</span>
                  <select value={patchName ?? ""} onChange={(e) => switchTo(`patch/${e.target.value}`, true)}>
                    {[...new Set([...Object.keys(summary.patches ?? {}), ...Object.keys(catalog?.patch_library ?? {})])].map((n) =>
                      <option key={n} value={n}>{n}{summary.patches?.[n] ? " (song)" : ""}</option>)}
                  </select>
                </label>
              ) : voice.instrument === "sampler" ? (
                <label className="field"><span>library</span>
                  <select value={voice.use.split("/").slice(1).join("/")} onChange={(e) => switchTo(`sampler/${e.target.value}`, false)}>
                    {(catalog?.samplers ?? []).map((s) => <option key={s.name} value={s.name}>{s.title}</option>)}
                  </select>
                </label>
              ) : (
                <label className="field"><span>preset</span>
                  <select value={voice.preset ?? ""} onChange={(e) => switchTo(e.target.value ? `${voice.instrument}/${e.target.value}` : voice.instrument, false)}>
                    <option value="">(defaults)</option>
                    {presets.map((p) => <option key={p.name} value={p.name}>{p.name}</option>)}
                  </select>
                </label>
              )}
              <button disabled={!modified.length} onClick={() => switchTo(voice.use, true)} title="Remove this voice's knob changes">Reset knobs</button>
            </div>

            {view === "learn" && guide && (
              <div className="learn">
                <p className="lead-in">{guide.summary}</p>
                <p className="small muted"><b>Ancestor:</b> {guide.ancestor}</p>
                <h5>How it's built <span className="muted">— click a block</span></h5>
                <div className="flow-wrap"><Flow chain={guide.chain} sel={block} onSel={setBlock} /></div>
                {selBlock ? (
                  <div className="block-detail" style={{ borderLeftColor: KIND_COLOR[selBlock.kind] }}>
                    <b>{selBlock.label}</b> <span className="muted small">({selBlock.kind})</span>
                    <p>{selBlock.what}</p>
                    <div className="kx-list">{selBlock.params.map((n) => paramSpec(n)).filter(Boolean).map((q) => knob(q!, true))}</div>
                  </div>
                ) : <p className="small">{guide.how}</p>}
                <details open><summary>Why it sounds like this</summary><p className="small">{guide.why}</p></details>
                <details><summary>Velocity: soft vs hard</summary><p className="small">{guide.velocity}</p>
                  <button onClick={() => (isKit ? play([0.2, 0.45, 0.7, 0.95].map((v, i) => ({ t: i * 0.4, pitch: 60, vel: v, gate: 0.25 }))) : sweep())}>Hear it: soft → hard</button></details>
                <h5>Try these</h5>
                <div className="recipes">
                  {guide.recipes.map((r) => (
                    <div key={r.name} className="recipe">
                      <b>{r.name}</b>
                      <code className="small">{Object.entries(r.set).map(([k, v]) => `${k}=${v}`).join(" ")}</code>
                      <p className="small">{r.listen}</p>
                      <div className="recipe-btns">
                        <button onClick={() => tryRecipe(r.set, false)}>▶ try</button>
                        <button onClick={() => tryRecipe(r.set, true)} title="Your sound, then the recipe">A/B</button>
                        <button className="primary" onClick={() => keepRecipe(r.set)} title="Write these values into the song">keep</button>
                      </div>
                    </div>
                  ))}
                </div>
                <p className="small muted"><b>Next:</b> {guide.try_next}</p>
                <div className="build-own">
                  <b>Build your own</b>
                  <p className="small">Every instrument here is a recipe of oscillators, noise, filters and envelopes. Rebuild this one as a
                    patch you can rewire module by module{STARTER[voice.instrument] ? ` (starting from ${STARTER[voice.instrument]})` : ""}.</p>
                  <button onClick={buildOwn}>Build a patch…</button>
                </div>
              </div>
            )}
            {view === "learn" && !guide && <p className="pad muted">No guide for {voice.instrument} yet; the Knobs view shows its params.</p>}

            {view === "knobs" && (
              <>
                {preset?.description && <p className="rack-desc">{preset.description}{preset.tags.length ? <span className="muted"> · {preset.tags.join(", ")}</span> : null}</p>}
                <div className="rack-groups">
                  {groups.map(([g, qs]) => (
                    <section key={g} className="pgroup"><h5>{g}</h5><div className="knobs">{qs.map((q) => knob(q))}</div></section>
                  ))}
                </div>
              </>
            )}

            {view === "wiring" && (isPatch && patchSpec && catalog ? (
              <PatchEditor name={patchName!} spec={patchSpec} editable={voice.patch_source === "song"} catalog={catalog}
                           posKey={`patchpos:${path}:${patchName}`}
                           onSave={(s) => onApply("patch", { name: patchName, spec: s })}
                           onCopy={() => onApply("patch", { name: patchName, spec: { modules: patchSpec.modules, wires: patchSpec.wires } })} />
            ) : (
              <div className="pad">
                <p><b>{voice.instrument}</b> is built in Python, so its wiring is fixed: the Learn view shows its signal flow.</p>
                <p className="small">To wire your own, build a patch: modules (oscillators, noise, strings, resonators, filters, envelopes, LFOs)
                  connected by wires, saved in the song as <code>patch</code> lines and played as <code>patch/&lt;name&gt;</code>.</p>
                <button className="primary" onClick={buildOwn}>Build a patch…</button>
              </div>
            ))}
          </>
        )}
      </div>
      {voice && (
        <div className="audition">
          <div className="aud-row">
            <b>Audition</b>
            <button onClick={() => (isKit ? playPattern() : play(lastNotes.current))} title="Play again">↻</button>
            {!isKit && <button onClick={chord}>chord</button>}
            {!isKit && <button onClick={arp}>arpeggio</button>}
            <button onClick={sweep} title="The same note from soft to hard: velocity shapes the timbre">vel sweep</button>
            <button onClick={() => play(phrase())} title="This part's notes from the playhead (4 s)">phrase</button>
          </div>
          <div className="aud-row">
            <label className="mini"><input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} /> play on knob release</label>
          </div>
          {isKit ? (
            <div className="pattern">
              <div className="aud-row">
                <b className="small">Pattern</b>
                <label className="mini">hits <input type="number" min={0} max={16} value={hits} style={{ width: 44 }}
                  onChange={(e) => { const k = Math.max(0, Math.min(16, +e.target.value)); setHits(k); setPattern(euclid(k)); }} /></label>
                <button onClick={() => playPattern()}>▶</button>
              </div>
              <div className="pat-cells">
                {[...pattern].map((c, i) => (
                  <span key={i} className={"pc" + (c !== "." ? " on" : "") + (i % 4 === 0 ? " beat" : "")} title="click: . x X - o"
                        onClick={() => { const cyc = [".", "x", "X", "-", "o"]; const p = [...pattern]; p[i] = cyc[(cyc.indexOf(p[i]) + 1) % cyc.length]; setPattern(p.join("")); }}>
                    {c === "." ? "" : c}</span>
                ))}
              </div>
              <p className="small muted">{[...pattern].filter((c) => c !== ".").length} hits spread over 16 steps (a Euclidean rhythm spaces them as evenly as possible).</p>
              {secNow && <button onClick={writePattern} title={`Write ${piece}="${pattern}" on the ${secNow.name} line`}>Use in {secNow.name}</button>}
            </div>
          ) : (
            <>
              <div className="aud-row">
                <label className="mini">vel <input type="range" min={0.05} max={1} step={0.01} value={vel} onChange={(e) => setVel(+e.target.value)} /> {vel.toFixed(2)}</label>
                <label className="mini">gate <input type="range" min={0.05} max={3} step={0.05} value={gate} onChange={(e) => setGate(+e.target.value)} /> {gate.toFixed(2)}s</label>
              </div>
              <div className="aud-row">
                <span className="seg" title="Sixth-step offset (36-EDO): the golden harmony's ↑ and ↓">
                  {[-1, 0, 1].map((o) => <button key={o} className={offset === o ? "on" : ""} onClick={() => setOffset(o)}>{o < 0 ? "↓" : o > 0 ? "↑" : "·"}</button>)}
                </span>
                <span className="muted small">{last !== null ? noteName(last) : ""}</span>
              </div>
              <Keyboard lo={48} hi={72} onNote={note} active={last} />
            </>
          )}
          <Scope url={scope?.url ?? null} label={scope ? `${scope.label}: waveform, then spectrum (30 Hz – 20 kHz)` : "play something to see its waveform and spectrum"} />
          {err && <p className="warn-text small">{err}</p>}
        </div>
      )}
    </div>
  );
}
