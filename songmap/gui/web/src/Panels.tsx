// The inspector tabs: Problems, QA, Video, Export.
import { useEffect, useRef, useState } from "react";
import { api, type Check, type QA, type Summary, type View } from "./api";

export function Problems({ check, onLine }: { check: Check | null; onLine: (line: number) => void }) {
  if (!check) return <p className="muted pad">checking…</p>;
  const s = check.summary;
  return (
    <div className="pad">
      {check.diagnostics.length === 0 && <p className="ok">No problems · checked in {check.ms} ms</p>}
      <ul className="diags">
        {check.diagnostics.map((d, i) => (
          <li key={i} className={d.severity} onClick={() => d.line && onLine(d.line)}>
            <b>{d.severity}{d.line ? ` · line ${d.line}` : ""}</b>
            <span>{d.message}</span>
            {d.suggestion && <em>{d.suggestion}</em>}
          </li>
        ))}
      </ul>
      {s && (
        <table className="facts">
          <tbody>
            <tr><th>title</th><td>{s.title}</td></tr>
            <tr><th>tempo · meter</th><td>{s.tempo} bpm · {s.meter}</td></tr>
            <tr><th>key · tuning</th><td>{s.key} · {s.tuning}</td></tr>
            <tr><th>mood</th><td>{s.mood ?? "balanced (default)"}</td></tr>
            <tr><th>length</th><td>{s.length} · {s.bars} bars · {s.frames} frames @ {s.fps}</td></tr>
            <tr><th>digest</th><td><code>{s.digest}</code></td></tr>
          </tbody>
        </table>
      )}
    </div>
  );
}

function Meter({ label, value, lo, hi, warn }: { label: string; value: number; lo: number; hi: number; warn?: boolean }) {
  const f = Math.min(1, Math.max(0, (value - lo) / (hi - lo)));
  return (
    <div className={"meter" + (warn ? " warn" : "")}>
      <span>{label}</span>
      <div><i style={{ width: `${f * 100}%` }} /></div>
      <b>{value.toFixed(1)}</b>
    </div>
  );
}

export function QAPanel({ qa, stale }: { qa: QA | null; stale: boolean }) {
  if (!qa) return <p className="muted pad">Render the song (Ctrl+Enter) to measure it.</p>;
  return (
    <div className="pad">
      {stale && <p className="warn-text">The code changed since this render.</p>}
      <div className="big-numbers">
        <div><b>{qa.lufs.toFixed(1)}</b><span>LUFS</span></div>
        <div className={qa.true_peak_db > -1 ? "warn-text" : ""}><b>{qa.true_peak_db.toFixed(2)}</b><span>dBTP</span></div>
        <div className={qa.clipped ? "warn-text" : ""}><b>{qa.clipped}</b><span>clipped</span></div>
      </div>
      <h4>Sections (LUFS)</h4>
      {qa.sections.map((s, i) => <Meter key={i} label={s.name} value={s.loudness} lo={-40} hi={-8} />)}
      <h4>Stems (LUFS)</h4>
      {Object.entries(qa.stems).sort((a, b) => b[1] - a[1]).map(([k, v]) =>
        <Meter key={k} label={k} value={v} lo={-50} hi={-10} warn={v > -14} />)}
    </div>
  );
}

const SIZES: [string, [number, number]][] = [["720p", [1280, 720]], ["1080p", [1920, 1080]], ["square", [1080, 1080]],
  ["vertical", [1080, 1920]], ["small", [640, 360]]];

export function VideoPanel({ path, text, time, summary, view, setView, ok }: {
  path: string; text: string; time: number; summary: Summary | null; view: View; setView: (v: View) => void; ok: boolean;
}) {
  const [img, setImg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [follow, setFollow] = useState(true);
  const pending = useRef<number | null>(null);
  const t = Math.round(time * 4) / 4;                     // refresh every quarter second of song time at most

  useEffect(() => {
    if (!ok || !follow) return;
    if (pending.current) window.clearTimeout(pending.current);
    pending.current = window.setTimeout(async () => {
      setBusy(true);
      try {
        const url = await api.frameUrl(path, text, t, view);
        setImg((old) => { if (old) URL.revokeObjectURL(old); return url; });
        setErr(null);
      } catch (e) { setErr(String(e)); }
      setBusy(false);
    }, 250);
  }, [path, text, t, view, ok, follow]);

  const parts = summary?.parts.filter((p) => !p.kit).map((p) => p.name) ?? [];
  const shown = view.parts ?? parts;
  const toggle = (p: string) => {
    const next = shown.includes(p) ? shown.filter((x) => x !== p) : [...shown, p];
    setView({ ...view, parts: next.length === parts.length ? null : next });
  };
  return (
    <div className="pad video">
      <div className="frame">{img ? <img src={img} alt="frame" /> : <span className="muted">{ok ? "…" : "fix the errors to preview"}</span>}
        {busy && <span className="busy">rendering frame…</span>}</div>
      {err && <p className="warn-text">{err}</p>}
      <label className="row"><input type="checkbox" checked={follow} onChange={(e) => setFollow(e.target.checked)} /> follow the playhead</label>
      <div className="row">
        <span>theme</span>
        <select value={view.theme} onChange={(e) => setView({ ...view, theme: e.target.value as View["theme"] })}>
          <option value="light">light</option><option value="dark">dark</option>
        </select>
        <span>size</span>
        <select value={view.size.join("x")} onChange={(e) => setView({ ...view, size: SIZES.find((s) => s[1].join("x") === e.target.value)![1] })}>
          {SIZES.map(([n, s]) => <option key={n} value={s.join("x")}>{n} {s[0]}×{s[1]}</option>)}
        </select>
      </div>
      <label className="row"><span>page</span>
        <input type="range" min={2} max={16} step={0.5} value={view.page_seconds}
               onChange={(e) => setView({ ...view, page_seconds: +e.target.value })} />
        <span>{view.page_seconds}s</span></label>
      <h4>Parts on screen</h4>
      <div className="chips">
        {parts.map((p) => <button key={p} className={"chip" + (shown.includes(p) ? " on" : "")} onClick={() => toggle(p)}>{p}</button>)}
      </div>
      <p className="muted small">Layers, placement and styling per element come with the video designer (S6).</p>
    </div>
  );
}

const FORMATS: [string, string][] = [["wav", "song.wav (24-bit)"], ["mp3", "song.mp3"], ["stems", "stems/*.wav"],
  ["cues", "cues.json + qa.json"], ["qa_png", "QA plot (png)"], ["png", "poster frame (png)"], ["mp4", "video (mp4)"]];

export function ExportPanel({ path, text, view, time, ok }: { path: string; text: string; view: View; time: number; ok: boolean }) {
  const [sel, setSel] = useState<Set<string>>(new Set(["wav", "mp3", "cues"]));
  const [busy, setBusy] = useState(false);
  const [files, setFiles] = useState<Record<string, string> | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const run = async () => {
    setBusy(true); setErr(null);
    try {
      const r = await api.exportFiles(path, text, [...sel], { ...view, t: time });
      if (r.ok && r.files) setFiles(r.files); else setErr("the song has errors");
    } catch (e) { setErr(String(e)); }
    setBusy(false);
  };
  const toggle = (f: string) => setSel((s) => { const n = new Set(s); n.has(f) ? n.delete(f) : n.add(f); return n; });
  return (
    <div className="pad">
      {FORMATS.map(([f, label]) => (
        <label key={f} className="row"><input type="checkbox" checked={sel.has(f)} onChange={() => toggle(f)} /> {label}</label>
      ))}
      <p className="muted small">Written next to the song in <code>renders/</code>. The video and poster use the Video tab's settings; the poster is taken at the playhead.</p>
      <button className="primary" disabled={!ok || busy || sel.size === 0} onClick={run}>{busy ? "Exporting…" : "Export"}</button>
      {err && <p className="warn-text">{err}</p>}
      {files && (
        <ul className="files-out">
          {Object.entries(files).map(([k, p]) => (
            <li key={k}><b>{k}</b> <a href={api.fileUrl(p)} target="_blank" rel="noreferrer">{p}</a></li>
          ))}
        </ul>
      )}
    </div>
  );
}
