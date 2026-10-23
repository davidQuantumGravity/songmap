// The mixer: one strip per part (inserts, sends, pan, fader, mute/solo, loudness), the returns and the master.
// Faders, pans and sends write the song's `mix` line and remix the last render's stems; insert chains write
// its `inserts` line (a part's chain re-renders, with unchanged notes from the cache; the master's remixes).
import { useEffect, useMemo, useState } from "react";
import type { Catalog, InsertSpec, ParamSpec, QA, Summary, UnitSpec } from "./api";
import { Fader, Knob } from "./ui";

export type MixEdit = { gain_db?: number; pan?: number; sends?: Record<string, number> };
type Live = Record<string, { gain_db: number; pan: number; send: Record<string, number> }>;

const db = (v: number) => (v > 0 ? "+" : "") + v.toFixed(1);
const pan = (v: number) => (Math.abs(v) < 0.005 ? "C" : v < 0 ? `L${Math.round(-v * 100)}` : `R${Math.round(v * 100)}`);
function fmtValue(v: number, unit: string) {
  const a = Math.abs(v);
  const n = a >= 1000 ? `${(v / 1000).toFixed(a >= 10000 ? 0 : 1)}k` : a >= 100 ? v.toFixed(0) : a >= 10 ? v.toFixed(1) : v.toFixed(2);
  return unit ? `${n} ${unit}` : n;
}

function Slots({ part, chain, units, selected, onSelect, onChain }: {
  part: string; chain: InsertSpec[]; units: UnitSpec[]; selected: number | null;
  onSelect: (i: number | null) => void; onChain: (c: InsertSpec[]) => void;
}) {
  return (
    <div className="slots">
      {chain.map((u, i) => (
        <button key={i} className={"slot" + (selected === i ? " on" : "") + (Number(u.on ?? 1) < 0.5 ? " bypassed" : "")}
                onClick={() => onSelect(selected === i ? null : i)} title={`${part}: ${u.fx} (click to edit)`}>
          <i />{u.fx}
        </button>
      ))}
      <select className="slot-add" value="" onChange={(e) => { if (e.target.value) { onChain([...chain, { fx: e.target.value }]); onSelect(chain.length); } }}
              title="Add an insert effect">
        <option value="">+ insert</option>
        {units.map((u) => <option key={u.name} value={u.name}>{u.name}</option>)}
      </select>
    </div>
  );
}

function UnitEditor({ part, chain, index, spec, onChain, onClose }: {
  part: string; chain: InsertSpec[]; index: number; spec: UnitSpec | undefined;
  onChain: (c: InsertSpec[]) => void; onClose: () => void;
}) {
  const u = chain[index];
  const [live, setLive] = useState<Record<string, number>>({});
  useEffect(() => setLive({}), [chain, index]);
  if (!u || !spec) return null;
  const set = (k: string, v: number | null) => {
    const next = { ...u } as InsertSpec;
    const q = spec.params.find((p) => p.name === k)!;
    if (v === null || Math.abs(v - q.default) < 1e-9) delete next[k]; else next[k] = Number(v.toPrecision(4));
    onChain(chain.map((x, i) => (i === index ? next : x)));
  };
  const move = (d: number) => {
    const j = index + d;
    if (j < 0 || j >= chain.length) return;
    const c = [...chain]; [c[index], c[j]] = [c[j], c[index]];
    onChain(c);
  };
  const groups = new Map<string, ParamSpec[]>();
  for (const q of spec.params) if (q.name !== "on") groups.set(q.group, [...(groups.get(q.group) ?? []), q]);
  const on = Number(u.on ?? 1) >= 0.5;
  return (
    <div className="unit-editor">
      <div className="ue-head">
        <b>{part} · {u.fx}</b>
        <span className="muted small">{spec.doc}</span>
        <span className="spacer" />
        <button className={on ? "on" : ""} onClick={() => set("on", on ? 0 : 1)} title="bypass keeps the settings">{on ? "on" : "bypassed"}</button>
        <button onClick={() => move(-1)} disabled={index === 0} title="earlier in the chain">↑</button>
        <button onClick={() => move(1)} disabled={index === chain.length - 1} title="later in the chain">↓</button>
        <button onClick={() => { onChain(chain.filter((_, i) => i !== index)); onClose(); }} title="remove">✕</button>
      </div>
      <div className="ue-groups">
        {[...groups.entries()].map(([g, qs]) => (
          <section key={g} className="pgroup">
            <h5>{g}</h5>
            <div className="knobs">
              {qs.map((q) => {
                const v = live[q.name] ?? (typeof u[q.name] === "number" ? (u[q.name] as number) : q.default);
                return <Knob key={q.name} label={q.name} value={v} min={q.lo} max={q.hi} step={0} def={q.default} curve={q.curve}
                             modified={q.name in u} format={(x) => fmtValue(x, q.unit)}
                             title={`${q.name}${q.doc ? ": " + q.doc : ""}\ndouble-click: ${fmtValue(q.default, q.unit)}`}
                             onChange={(x) => setLive((l) => ({ ...l, [q.name]: x }))} onCommit={(x) => set(q.name, x)} />;
              })}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

export function Mixer({ summary, qa, mute, solo, busy, catalog, onMute, onSolo, onEdit, onInserts, colorOf }: {
  summary: Summary; qa: QA | null; mute: Set<string>; solo: Set<string>; busy: boolean; catalog: Catalog | null;
  onMute: (p: string) => void; onSolo: (p: string) => void;
  onEdit: (part: string, edit: MixEdit, defaultGain: number) => void;
  onInserts: (part: string, chain: InsertSpec[]) => void;
  colorOf: (part: string) => string;
}) {
  const fresh = (): Live => Object.fromEntries(summary.parts.map((p) => [p.name, { gain_db: p.mix.gain_db, pan: p.mix.pan, send: { ...p.mix.send } }]));
  const [live, setLive] = useState<Live>(fresh);
  const [sel, setSel] = useState<{ part: string; index: number } | null>(null);
  useEffect(() => setLive(fresh()), [summary]);   // eslint-disable-line react-hooks/exhaustive-deps
  const set = (part: string, f: (x: Live[string]) => Live[string]) => setLive((l) => ({ ...l, [part]: f(l[part]) }));
  const units = catalog?.inserts ?? [];
  const chainOf = useMemo(() => {
    const m: Record<string, InsertSpec[]> = { master: summary.master_inserts ?? [], ...(summary.return_inserts ?? {}) };
    for (const p of summary.parts) m[p.name] = p.mix.inserts ?? [];
    return m;
  }, [summary]);
  const selChain = sel ? chainOf[sel.part] ?? [] : [];

  return (
    <div className="mixer">
      <div className="strips">
        {summary.parts.map((p) => {
          const v = live[p.name] ?? { gain_db: p.mix.gain_db, pan: p.mix.pan, send: p.mix.send };
          const lufs = qa?.stems[p.name];
          const heard = !mute.has(p.name) && (solo.size === 0 || solo.has(p.name));
          return (
            <div key={p.name} className={"strip" + (heard ? "" : " silent")}>
              <div className="strip-head" style={{ borderTopColor: colorOf(p.name) }}>
                <b title={p.name}>{p.name}</b>
                <small title={p.kit ? "drum kit" : p.instrument ?? ""}>{p.kit ? "kit" : p.instrument}</small>
              </div>
              <Slots part={p.name} chain={chainOf[p.name]} units={units} selected={sel?.part === p.name ? sel.index : null}
                     onSelect={(i) => setSel(i === null ? null : { part: p.name, index: i })} onChain={(c) => onInserts(p.name, c)} />
              <div className="sends">
                {summary.returns.map((r) => (
                  <Knob key={r} label={r} size={28} min={0} max={1} step={0.01} value={v.send[r] ?? 0} def={p.mix.send[r] ?? 0}
                        format={(x) => x.toFixed(2)} title={`${p.name} → ${r} send`}
                        onChange={(x) => set(p.name, (s) => ({ ...s, send: { ...s.send, [r]: x } }))}
                        onCommit={(x) => onEdit(p.name, { sends: { [r]: x } }, p.mix.gain_db)} />
                ))}
              </div>
              <Knob label="pan" min={-1} max={1} step={0.01} value={v.pan} def={0} format={pan} bipolar title={`${p.name} pan`}
                    onChange={(x) => set(p.name, (s) => ({ ...s, pan: x }))}
                    onCommit={(x) => onEdit(p.name, { pan: x }, p.mix.gain_db)} />
              <Fader min={-48} max={24} step={0.5} value={v.gain_db} def={0} format={db} title={`${p.name} fader (dB): drag, wheel, double-click for 0`}
                     onChange={(x) => set(p.name, (s) => ({ ...s, gain_db: x }))}
                     onCommit={(x) => onEdit(p.name, { gain_db: x }, p.mix.gain_db)} />
              <div className="ms">
                <button className={"m" + (mute.has(p.name) ? " on" : "")} onClick={() => onMute(p.name)} title="mute (listening only)">M</button>
                <button className={"s" + (solo.has(p.name) ? " on" : "")} onClick={() => onSolo(p.name)} title="solo (listening only)">S</button>
              </div>
              <div className="strip-foot" title="the stem's loudness in the last render">
                {lufs !== undefined ? `${lufs.toFixed(1)} LU` : "–"}
                {p.mix.sidechain && <span className="tag" title="ducked by the kick (sc=)">sc</span>}
              </div>
            </div>
          );
        })}
        <div className="strip returns">
          <div className="strip-head"><b>returns</b><small>reverb</small></div>
          {summary.returns.map((r) => (
            <div key={r} className="ret-block">
              <div className="ret"><span>{r}</span><b>{qa?.stems[`return_${r}`]?.toFixed(1) ?? "–"}</b></div>
              <Slots part={r} chain={chainOf[r] ?? []} units={units} selected={sel?.part === r ? sel.index : null}
                     onSelect={(i) => setSel(i === null ? null : { part: r, index: i })} onChain={(c) => onInserts(r, c)} />
            </div>
          ))}
          <div className="strip-foot">{busy ? "remixing…" : ""}</div>
        </div>
        <div className="strip master">
          <div className="strip-head"><b>master</b><small>{qa ? "measured" : "render first"}</small></div>
          <Slots part="master" chain={chainOf.master} units={units} selected={sel?.part === "master" ? sel.index : null}
                 onSelect={(i) => setSel(i === null ? null : { part: "master", index: i })} onChain={(c) => onInserts("master", c)} />
          <div className="master-num"><b>{qa ? qa.lufs.toFixed(1) : "–"}</b><span>LUFS</span></div>
          <div className="master-num"><b className={qa && qa.true_peak_db > -1 ? "warn-text" : ""}>{qa ? qa.true_peak_db.toFixed(2) : "–"}</b><span>dBTP</span></div>
          <p className="muted small">Faders, pans and sends write the <code>mix</code> line; inserts write the <code>inserts</code> line. M/S are for listening only.</p>
        </div>
      </div>
      {sel && selChain[sel.index] && (
        <UnitEditor part={sel.part} chain={selChain} index={sel.index} spec={units.find((u) => u.name === selChain[sel.index].fx)}
                    onChain={(c) => onInserts(sel.part, c)} onClose={() => setSel(null)} />
      )}
    </div>
  );
}
