// The mixer: one strip per part (fader, pan, sends, mute/solo, loudness) and the returns.
// A released control writes the song's `mix` line; the audio is remixed from the last render's stems.
import { useEffect, useState } from "react";
import type { QA, Summary } from "./api";
import { Fader, Knob } from "./ui";

export type MixEdit = { gain_db?: number; pan?: number; sends?: Record<string, number> };
type Live = Record<string, { gain_db: number; pan: number; send: Record<string, number> }>;

const db = (v: number) => (v > 0 ? "+" : "") + v.toFixed(1);
const pan = (v: number) => (Math.abs(v) < 0.005 ? "C" : v < 0 ? `L${Math.round(-v * 100)}` : `R${Math.round(v * 100)}`);

export function Mixer({ summary, qa, mute, solo, busy, onMute, onSolo, onEdit, colorOf }: {
  summary: Summary; qa: QA | null; mute: Set<string>; solo: Set<string>; busy: boolean;
  onMute: (p: string) => void; onSolo: (p: string) => void;
  onEdit: (part: string, edit: MixEdit, defaultGain: number) => void;
  colorOf: (part: string) => string;
}) {
  const fresh = (): Live => Object.fromEntries(summary.parts.map((p) => [p.name, { gain_db: p.mix.gain_db, pan: p.mix.pan, send: { ...p.mix.send } }]));
  const [live, setLive] = useState<Live>(fresh);
  useEffect(() => setLive(fresh()), [summary]);   // eslint-disable-line react-hooks/exhaustive-deps
  const set = (part: string, f: (x: Live[string]) => Live[string]) => setLive((l) => ({ ...l, [part]: f(l[part]) }));

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
            <div key={r} className="ret"><span>{r}</span><b>{qa?.stems[`return_${r}`]?.toFixed(1) ?? "–"}</b></div>
          ))}
          <div className="strip-foot">{busy ? "remixing…" : ""}</div>
        </div>
        <div className="strip master">
          <div className="strip-head"><b>master</b><small>{qa ? "measured" : "render first"}</small></div>
          <div className="master-num"><b>{qa ? qa.lufs.toFixed(1) : "–"}</b><span>LUFS</span></div>
          <div className="master-num"><b className={qa && qa.true_peak_db > -1 ? "warn-text" : ""}>{qa ? qa.true_peak_db.toFixed(2) : "–"}</b><span>dBTP</span></div>
          <p className="muted small">Faders, pans and sends write the song's <code>mix</code> line. M/S are for listening and stay out of the song.</p>
        </div>
      </div>
    </div>
  );
}
