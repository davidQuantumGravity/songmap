import { useEffect, useState } from "react";
import type { Catalog, Summary } from "./api";
import { tempoText } from "./musicTiming";
import "./conductor.css";

export function Conductor({ summary, catalog, selected, onSelect, onSeek, onApply, disabled }: {
  summary: Summary; catalog: Catalog | null; selected: number | null; onSelect: (i: number | null) => void;
  onSeek: (t: number) => void; onApply: (index: number | null, values: object) => Promise<void>; disabled: boolean;
}) {
  const sec = selected === null ? null : summary.sections.find(s => s.index === selected) ?? null;
  const [tempoMode, setTempoMode] = useState("inherit"), [start, setStart] = useState("120"), [end, setEnd] = useState("90");
  const [meterOn, setMeterOn] = useState(false), [meter, setMeter] = useState("4/4");
  const [keyOn, setKeyOn] = useState(false), [tonic, setTonic] = useState("C"), [scale, setScale] = useState("major");
  const [busy, setBusy] = useState(false), [error, setError] = useState(""), [message, setMessage] = useState("");
  const sourceState = JSON.stringify([selected, summary.tempo, summary.meter, summary.key, sec?.tempo_override,
    sec?.tempo_start, sec?.tempo_end, sec?.meter, sec?.meter_override, sec?.key, sec?.key_override]);
  useEffect(() => {
    setTempoMode(!sec ? "constant" : sec.tempo_override === null ? "inherit" : sec.tempo_start === sec.tempo_end ? "constant" : "ramp");
    setStart(String(sec?.tempo_start ?? summary.tempo)); setEnd(String(sec?.tempo_end ?? summary.tempo));
    setMeterOn(!sec || sec.meter_override !== null); setMeter(sec?.meter ?? summary.meter);
    setKeyOn(!sec || sec.key_override !== null); setTonic(sec?.tonic ?? summary.tonic); setScale(sec?.scale ?? summary.scale);
    setError("");
  }, [sourceState]); // eslint-disable-line react-hooks/exhaustive-deps
  const select = (i: number | null) => { setMessage(""); onSelect(i); };
  const apply = async (e: React.FormEvent) => {
    e.preventDefault(); setError(""); setMessage(""); setBusy(true);
    try {
      const a = Number(start), b = Number(end);
      if (tempoMode !== "inherit" && (!Number.isFinite(a) || a <= 0 || (tempoMode === "ramp" && (!Number.isFinite(b) || b <= 0)))) throw new Error("Enter a positive, finite BPM.");
      await onApply(selected, { tempo: tempoMode === "inherit" ? null : tempoMode === "ramp" ? `${a > b ? "rit" : "accel"} ${a}>${b}` : a,
        meter: meterOn ? meter.trim() : null, key: keyOn ? `${tonic.trim()} ${scale}` : null });
      setMessage("Applied to the score. Save to keep this edit; Render to hear it.");
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  };
  const modes = catalog?.scales ?? [{ name: scale, microtonal: false }];
  return <div className="conductor-panel" aria-label="Conductor editor">
    <div className="conductor-heading"><div><h2>Conductor</h2><p>Tempo, meter, tonic and scale across the song</p></div>
      <label>Edit <select aria-label="Conductor target" value={selected ?? "song"} disabled={busy} onChange={e => select(e.target.value === "song" ? null : Number(e.target.value))}>
        <option value="song">Song defaults</option>{summary.sections.map(s => <option key={s.index} value={s.index}>{s.name} · bar {s.bar + 1}</option>)}
      </select></label>{sec && <button onClick={() => onSeek(sec.start)}>Seek to section</button>}</div>
    <form onSubmit={apply}>
      <fieldset disabled={busy || disabled}><legend>{sec ? sec.name : "Song defaults"}</legend>
        <div className="conductor-fields">
          <div className="conductor-field"><b>Tempo</b>
            <select aria-label="Tempo behavior" value={tempoMode} onChange={e => setTempoMode(e.target.value)}>
              {sec && <option value="inherit">Use song default · {summary.tempo} BPM</option>}<option value="constant">Constant</option>{sec && <option value="ramp">Ramp across section</option>}
            </select><div className="conductor-inline">
              <label>{tempoMode === "ramp" ? "Start BPM" : "BPM"}<input aria-label="Tempo start BPM" type="number" min="0.01" step="any" value={start} disabled={tempoMode === "inherit"} onChange={e => setStart(e.target.value)} /></label>
              {tempoMode === "ramp" && <label>End BPM<input aria-label="Tempo end BPM" type="number" min="0.01" step="any" value={end} onChange={e => setEnd(e.target.value)} /></label>}
            </div><small>Quarter-note BPM. Ramps change linearly with beats.</small></div>
          <div className="conductor-field"><b>Time signature</b>
            {sec && <label className="conductor-check"><input type="checkbox" checked={meterOn} onChange={e => setMeterOn(e.target.checked)} /> Override song meter</label>}
            <label>Meter{sec ? " / additive groups" : ""}<input aria-label="Time signature" value={meter} disabled={!meterOn} onChange={e => setMeter(e.target.value)} placeholder={sec ? "7/8 2+2+3" : "4/4"} /></label>
            <small>{sec ? "Examples: 3/4, 6/8, 7/8 2+2+3. Groups must sum to the numerator." : "Sections can use additive groups and different meters."}</small></div>
          <div className="conductor-field"><b>Key & scale</b>
            {sec && <label className="conductor-check"><input type="checkbox" checked={keyOn} onChange={e => setKeyOn(e.target.checked)} /> Override song key & scale</label>}
            <div className="conductor-inline"><label>Tonic<input aria-label="Tonic" value={tonic} disabled={!keyOn} onChange={e => setTonic(e.target.value)} placeholder="F#" /></label>
              <label>Scale / mode<select aria-label="Scale or mode" value={scale} disabled={!keyOn} onChange={e => setScale(e.target.value)}>{modes.map(m => <option key={m.name} value={m.name}>{m.name}{m.microtonal ? " · microtonal" : ""}</option>)}</select></label></div>
            <small>Tuning: {summary.tuning}. Microtonal scales require a compatible tuning in the score.</small></div>
        </div><div className="conductor-actions"><button className="primary" type="submit">{busy ? "Applying…" : "Apply to score"}</button><span className="muted">{sec ? `Bars ${sec.bar + 1}–${sec.bar + sec.bars} · ${sec.bars} bars` : "Defaults apply to sections without an override."}</span></div>
      </fieldset>
    </form>
    {error && <p className="warn-text" role="alert">{error}</p>}{message && <p className="ok" role="status">{message}</p>}
    {disabled && <p className="muted">Fix score errors or wait for the render before applying changes.</p>}
    <p className="conductor-note">Changes start at section boundaries. Ramps run through the selected section. Each section inherits song defaults independently. Scale-degree notes follow the section key; motifs with their own key stay pinned. Letter pitches and chord symbols keep their written pitches.</p>
    <table aria-label="Song conductor map"><thead><tr><th>Section / bars</th><th>Tempo · BPM</th><th>Meter</th><th>Key / scale</th><th /></tr></thead>
      <tbody>{summary.sections.map(s => <tr key={s.index} className={selected === s.index ? "selected" : ""}>
        <td><button type="button" onClick={() => select(s.index)} aria-label={`Edit conductor ${s.name}`}>{s.name}</button><small>{s.bar + 1}–{s.bar + s.bars}</small></td>
        <td>{tempoText(s)}<small>{s.tempo_override === null ? "song default" : s.tempo_start !== s.tempo_end ? "ramp" : "override"}</small></td>
        <td>{s.meter}<small>{s.meter_override === null ? "song default" : "override"}</small></td>
        <td>{s.key}<small>{s.key_override === null ? "song default" : "override"}</small></td>
        <td><button type="button" onClick={() => onSeek(s.start)} aria-label={`Seek ${s.name}`}>↗ Seek</button></td>
      </tr>)}</tbody></table>
  </div>;
}
