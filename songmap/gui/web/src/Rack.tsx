// The instrument rack: every part's voice as knobs (built from the instrument's param schema), instrument and
// preset pickers, and an audition keyboard. A released knob writes the song's `inst`/`kit` line.
import { useEffect, useMemo, useRef, useState } from "react";
import { api, type AuditionNote, type Catalog, type InstrumentSpec, type ParamSpec, type Summary, type Voice } from "./api";
import { Knob } from "./ui";

export type VoiceEdit = { part: string; piece: string | null; use?: string; params?: Record<string, number | null>; clear?: boolean; current_use: string };

const NAMES = ["C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B"];
const noteName = (p: number) => {
  const r = Math.round(p * 3) / 3, k = Math.round(r), off = Math.round((r - k) * 3);
  return (off > 0 ? "^" : off < 0 ? "v" : "") + NAMES[((k % 12) + 12) % 12] + (Math.floor(k / 12) - 1);
};

function fmtValue(v: number, unit: string) {
  const a = Math.abs(v);
  const n = a >= 1000 ? `${(v / 1000).toFixed(a >= 10000 ? 0 : 1)}k` : a >= 100 ? v.toFixed(0) : a >= 10 ? v.toFixed(1) : v.toFixed(2);
  return unit ? `${n} ${unit}` : n;
}

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

export function Rack({ path, text, summary, catalog, onEdit, colorOf, time }: {
  path: string; text: string; summary: Summary; catalog: Catalog | null; time: number;
  onEdit: (e: VoiceEdit) => Promise<void>; colorOf: (p: string) => string;
}) {
  const parts = summary.parts;
  const [sel, setSel] = useState<{ part: string; piece: string | null }>(() => ({ part: parts.find((p) => !p.kit)?.name ?? parts[0]?.name, piece: null }));
  const [live, setLive] = useState<Record<string, number>>({});        // knob values while dragging / before the check returns
  const [vel, setVel] = useState(0.7);
  const [gate, setGate] = useState(0.6);
  const [offset, setOffset] = useState(0);                              // sixth-steps: -1 v, 0, +1 ^
  const [auto, setAuto] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [last, setLast] = useState<number | null>(null);
  const player = useRef<HTMLAudioElement>(new Audio());
  const lastNotes = useRef<AuditionNote[]>([{ t: 0, pitch: 60, vel: 0.7, gate: 0.6 }]);

  const pv = summary.voices[sel.part];
  const partSpec = parts.find((p) => p.name === sel.part);
  const isKit = !!pv && "kit" in pv && pv.kit === true;
  const pieces = isKit ? Object.keys((pv as { pieces: Record<string, Voice> }).pieces) : [];
  const piece = isKit ? (sel.piece && pieces.includes(sel.piece) ? sel.piece : pieces[0]) : null;
  const voice: Voice | null = !pv || "error" in pv && pv.error ? null : isKit ? (pv as { pieces: Record<string, Voice> }).pieces[piece!] : (pv as Voice);
  const spec: InstrumentSpec | undefined = catalog?.instruments.find((i) => i.name === voice?.instrument);
  const presets = (voice && catalog?.presets[voice.instrument]) ?? [];
  const preset = presets.find((p) => p.name === voice?.preset);
  useEffect(() => setLive({}), [summary, sel.part, piece]);

  const groups = useMemo(() => {
    const g = new Map<string, ParamSpec[]>();
    for (const q of spec?.params ?? []) g.set(q.group, [...(g.get(q.group) ?? []), q]);
    return [...g.entries()];
  }, [spec]);

  // the notes this part plays around the playhead (a few seconds), for "phrase"
  const phrase = (): AuditionNote[] => {
    const ns = (partSpec?.notes ?? []).filter((n) => (piece === null || n[4] === piece) && n[0] >= time - 0.01).slice(0, 24);
    if (!ns.length) return [];
    const t0 = ns[0][0];
    return ns.filter((n) => n[0] - t0 < 4).map((n) => ({ t: n[0] - t0, pitch: n[2] ?? 60, vel: n[3], gate: Math.min(n[1], 3) }));
  };

  const play = async (notes: AuditionNote[], overrides: Record<string, number> = live) => {
    if (!notes.length) return;
    lastNotes.current = notes;
    try {
      const url = await api.audition(path, text, sel.part, notes, piece, overrides);
      const a = player.current;
      if (a.src) URL.revokeObjectURL(a.src);
      a.src = url; await a.play();
      setErr(null);
    } catch (e) { setErr(String(e)); }
  };
  const note = (p: number) => { const pitch = p + offset / 3; setLast(pitch); play([{ t: 0, pitch, vel, gate }]); };
  const chord = () => { const r = (last ?? 60); play([0, 4, 7, 12].map((i) => ({ t: 0, pitch: r + i, vel, gate: gate * 2 }))); };
  const arp = () => { const r = (last ?? 60); play([0, 4, 7, 12, 7, 4].map((i, k) => ({ t: k * 0.16, pitch: r + i, vel, gate: 0.15 }))); };
  const sweep = () => { const r = (last ?? 60); play([0.15, 0.35, 0.55, 0.75, 0.95].map((v, k) => ({ t: k * Math.max(0.35, gate + 0.15), pitch: r, vel: v, gate }))); };

  const commit = async (q: ParamSpec, v: number | null) => {
    if (!voice) return;
    const overrides = v === null ? {} : { ...live, [q.name]: v };
    if (auto) play(lastNotes.current, overrides as Record<string, number>);
    await onEdit({ part: sel.part, piece, params: { [q.name]: v }, current_use: voice.use });
  };
  const switchTo = async (use: string, clear: boolean) => {
    if (!voice) return;
    await onEdit({ part: sel.part, piece, use, clear, current_use: voice.use });
  };

  const modified = voice ? Object.keys(voice.params).filter((k) => spec?.params.some((q) => q.name === k)) : [];
  const families = useMemo(() => {
    const f = new Map<string, InstrumentSpec[]>();
    for (const i of catalog?.instruments ?? []) f.set(i.family, [...(f.get(i.family) ?? []), i]);
    return [...f.entries()];
  }, [catalog]);

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
                <b>{sel.part}{piece ? ` · ${piece}` : ""}</b>
                <span className="muted small">{voice.use}{modified.length ? ` · ${modified.length} knob${modified.length > 1 ? "s" : ""} changed` : ""}</span>
              </div>
              <label className="field"><span>instrument</span>
                <select value={voice.instrument} onChange={(e) => switchTo(e.target.value === "sampler" ? "sampler/salamander" : e.target.value, true)}>
                  {families.map(([fam, list]) => (
                    <optgroup key={fam} label={fam}>{list.map((i) => <option key={i.name} value={i.name}>{i.name}</option>)}</optgroup>
                  ))}
                </select>
              </label>
              {voice.instrument === "sampler" ? (
                <label className="field"><span>library</span>
                  <select value={voice.use.split("/").slice(1).join("/")} onChange={(e) => switchTo(`sampler/${e.target.value}`, false)}>
                    {(catalog?.samplers ?? []).map((s) => <option key={s.name} value={s.name}>{s.title}</option>)}
                    {!catalog?.samplers.some((s) => voice.use.endsWith("/" + s.name)) && <option value={voice.use.split("/").slice(1).join("/")}>{voice.use}</option>}
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
              <button disabled={!modified.length} onClick={() => switchTo(voice.use, true)} title="Remove this voice's knob changes (back to the preset)">Reset knobs</button>
            </div>
            {preset?.description && <p className="rack-desc">{preset.description}{preset.tags.length ? <span className="muted"> · {preset.tags.join(", ")}</span> : null}</p>}
            <div className="rack-groups">
              {groups.map(([g, qs]) => (
                <section key={g} className="pgroup">
                  <h5>{g}</h5>
                  <div className="knobs">
                    {qs.map((q) => {
                      const raw = live[q.name] ?? voice.values[q.name];
                      const v = typeof raw === "number" ? raw : q.default;
                      const def = Number(voice.preset_values?.[q.name] ?? q.default);
                      return (
                        <Knob key={q.name} label={q.name} value={v} min={q.lo} max={q.hi} step={0} def={def} curve={q.curve}
                              modified={q.name in voice.params} format={(x) => fmtValue(x, q.unit)}
                              title={`${q.name}${q.doc ? ": " + q.doc : ""}\n${fmtValue(q.lo, q.unit)} … ${fmtValue(q.hi, q.unit)} · preset ${fmtValue(def, q.unit)}\ndrag · shift for fine · double-click resets`}
                              onChange={(x) => setLive((l) => ({ ...l, [q.name]: x }))}
                              onCommit={(x) => commit(q, Math.abs(x - def) < 1e-9 ? null : x)} />
                      );
                    })}
                  </div>
                </section>
              ))}
            </div>
          </>
        )}
      </div>
      {voice && (
        <div className="audition">
          <div className="aud-row">
            <b>Audition</b>
            <button onClick={() => play(lastNotes.current)} title="Play the last audition again">↻</button>
            {!isKit && <button onClick={chord}>chord</button>}
            {!isKit && <button onClick={arp}>arpeggio</button>}
            <button onClick={sweep} title="The same note from soft to hard: velocity shapes the timbre">velocity sweep</button>
            <button onClick={() => play(phrase())} title="This part's notes from the playhead (4 s)">phrase at playhead</button>
            <span className="spacer" />
            <label className="mini"><input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} /> play on knob release</label>
          </div>
          <div className="aud-row">
            <label className="mini">vel <input type="range" min={0.05} max={1} step={0.01} value={vel} onChange={(e) => setVel(+e.target.value)} /> {vel.toFixed(2)}</label>
            <label className="mini">gate <input type="range" min={0.05} max={3} step={0.05} value={gate} onChange={(e) => setGate(+e.target.value)} /> {gate.toFixed(2)} s</label>
            <span className="seg" title="Sixth-step offset (36-EDO): the golden harmony's ^ and v">
              {[-1, 0, 1].map((o) => <button key={o} className={offset === o ? "on" : ""} onClick={() => setOffset(o)}>{o < 0 ? "v" : o > 0 ? "^" : "·"}</button>)}
            </span>
            <span className="muted small">{last !== null ? noteName(last) : ""}</span>
          </div>
          {isKit ? (
            <div className="pads">
              {[0.25, 0.5, 0.75, 1].map((v) => (
                <button key={v} className="pad-btn" onClick={() => play([{ t: 0, pitch: 60, vel: v, gate: 0.3 }])}>{piece}<small>vel {v}</small></button>
              ))}
            </div>
          ) : <Keyboard lo={48} hi={72} onNote={note} active={last} />}
          {err && <p className="warn-text small">{err}</p>}
        </div>
      )}
    </div>
  );
}
