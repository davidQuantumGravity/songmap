// SongMap Studio (docs/GUI.md): files, arrangement, code / mixer dock, inspector, transport.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, type Catalog, type Check, type Files, type InsertSpec, type QA, type Summary, type View } from "./api";
import { CodeEditor } from "./CodeEditor";
import { Arrangement } from "./Arrangement";
import { Mixer, type MixEdit } from "./Mixer";
import { ExportPanel, Problems, QAPanel } from "./Panels";
import { VideoDesigner } from "./VideoDesigner";
import { Rack, type VoiceEdit } from "./Rack";
import { PianoRoll } from "./PianoRoll";
import { Teacher } from "./Teacher";
import { AILab } from "./InstrumentLab";
import { Splitter, useStored } from "./ui";

type Tab = "teacher" | "problems" | "qa" | "export";
type Dock = "code" | "mixer" | "rack" | "roll" | "video" | "lab";
const fmt = (t: number) => `${Math.floor(t / 60)}:${(t % 60).toFixed(1).padStart(4, "0")}`;
const css = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const baseName = (s: string) => s.replace(/[_\s-]*\d+$/, "");

function Logo() {
  // a golden-ratio spiral of quarter arcs: the golden harmony's emblem
  return (
    <svg width="22" height="22" viewBox="0 0 34 21" className="logo-mark" aria-hidden>
      <path d="M21 21 A21 21 0 0 1 0 0 M21 0 A13 13 0 0 1 34 13 M34 13 A8 8 0 0 1 26 21 M26 21 A5 5 0 0 1 21 16 M21 16 A3 3 0 0 1 24 13"
            fill="none" stroke="currentColor" strokeWidth="2.2" />
      <rect x="0.6" y="0.6" width="32.8" height="19.8" fill="none" stroke="currentColor" strokeOpacity=".35" strokeWidth="1.2" />
    </svg>
  );
}

function FileBrowser({ files, current, onOpen, onNew }: {
  files: Files | null; current: string | null; onOpen: (p: string) => void; onNew: () => void;
}) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<Record<string, boolean>>({ songs: true });
  return (
    <aside className="files">
      <div className="files-head">
        <input placeholder="Filter songs" value={q} onChange={(e) => setQ(e.target.value)} />
        <button title="New song" onClick={onNew}>New</button>
      </div>
      {files && Object.entries(files).map(([group, list]) => {
        const shown = list.filter((f) => f.toLowerCase().includes(q.toLowerCase()));
        const isOpen = q ? true : open[group];
        return (
          <div key={group} className="group">
            <div className="group-head" onClick={() => setOpen({ ...open, [group]: !open[group] })}>
              <span className="caret">{isOpen ? "▾" : "▸"}</span> {group} <span className="count">{shown.length}</span>
            </div>
            {isOpen && shown.map((f) => {
              const rel = f.split("/").slice(1);
              return (
                <div key={f} className={"file" + (f === current ? " current" : "")} title={f} onClick={() => onOpen(f)}>
                  {rel.length > 1 && <span className="dir">{rel.slice(0, -1).join("/")}/</span>}{rel[rel.length - 1]}
                </div>
              );
            })}
          </div>
        );
      })}
    </aside>
  );
}

export function App() {
  const [files, setFiles] = useState<Files | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [path, setPath] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [saved, setSaved] = useState("");
  const [check, setCheck] = useState<Check | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);   // the last good one: panes stay up while you type
  const [tab, setTab] = useState<Tab>("teacher");
  const [dock, setDock] = useState<Dock>(new URLSearchParams(location.search).get("lab") === "1" ? "lab" : "code");
  const [goto, setGoto] = useState<{ line: number; n: number } | null>(null);
  const [rendering, setRendering] = useState<"" | "render" | "remix">("");
  const [rendered, setRendered] = useState<{ text: string; listen: string; audio: string } | null>(null);
  const [qa, setQA] = useState<QA | null>(null);
  const [status, setStatus] = useState("");
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [loop, setLoop] = useState<[number, number] | null>(null);
  const [mute, setMute] = useState<Set<string>>(new Set());
  const [solo, setSolo] = useState<Set<string>>(new Set());
  const [view, setView] = useState<View>({ size: [1280, 720], theme: "light", page_seconds: 6, parts: null, colors: {},
                                           color_by: "spelling", part_colors: {}, layers: [] });
  const [filesW, setFilesW] = useStored("studio.files", 230);
  const [inspW, setInspW] = useStored("studio.insp", 340);
  const [arrH, setArrH] = useStored("studio.arr", 300);
  const [filesOpen, setFilesOpen] = useState(true);
  const audio = useRef<HTMLAudioElement>(new Audio());
  const checkSeq = useRef(0);
  const busy = useRef(false);
  const again = useRef(false);
  const latest = useRef({ path, text, mute, solo });
  latest.current = { path, text, mute, solo };

  const dirty = text !== saved;
  const listenKey = [...mute].sort().join(",") + "|" + [...solo].sort().join(",");
  const stale = !!rendered && (rendered.text !== text || rendered.listen !== listenKey);

  // colors: parts by order, sections by base name (chorus_2 shares chorus's color)
  const colorOf = useMemo(() => {
    const pal = Array.from({ length: 8 }, (_, i) => css(`--c${i + 1}`));
    const idx = new Map(summary?.parts.map((p, i) => [p.name, i]) ?? []);
    return (p: string) => pal[(idx.get(p) ?? 0) % pal.length];
  }, [summary]);
  const sectionColor = useMemo(() => {
    const pal = Array.from({ length: 8 }, (_, i) => css(`--s${i + 1}`));
    const order: string[] = [];
    for (const s of summary?.sections ?? []) if (!order.includes(baseName(s.name))) order.push(baseName(s.name));
    return (name: string) => pal[Math.max(0, order.indexOf(baseName(name))) % pal.length];
  }, [summary]);

  // ------------------------------------------------------------------ files
  useEffect(() => {
    api.files().then(setFiles).catch((e) => setStatus(String(e)));
    api.catalog().then(setCatalog).catch((e) => setStatus(String(e)));
  }, []);
  const open = useCallback(async (p: string) => {
    if (dirty && !confirm("Discard unsaved changes?")) return;
    audio.current.pause();
    audio.current.removeAttribute("src");
    setStatus(`opening ${p}…`);
    const r = await api.project(p);
    setPath(r.path); setText(r.text); setSaved(r.text); setCheck(r.check);
    setSummary(r.check.summary); setRendered(null); setQA(null); setTime(0); setLoop(null);
    setMute(new Set()); setSolo(new Set());
    api.getView(r.path).then((x) => setView(x.view)).catch(() => undefined);
    history.replaceState(null, "", `?song=${encodeURIComponent(r.path)}`);
    setStatus(r.check.ok ? `opened · checked in ${r.check.ms} ms` : "opened · has errors");
  }, [dirty]);
  useEffect(() => {
    const s = new URLSearchParams(location.search).get("song");
    if (s) open(s).catch((e) => setStatus(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const create = async () => {
    const name = prompt("New song path (repo-relative)", "songs/untitled.sm");
    if (!name) return;
    try {
      const r = await api.create(name);
      setFiles(await api.files());
      await open(r.path);
    } catch (e) { alert(String(e)); }
  };
  const save = useCallback(async () => {
    if (!path) return;
    const r = await api.save(path, text);
    setSaved(text); setCheck(r.check);
    setStatus("saved");
  }, [path, text]);

  // ------------------------------------------------------------------ live check
  useEffect(() => {
    if (!path) return;
    const seq = ++checkSeq.current;
    const id = window.setTimeout(async () => {
      try {
        const c = await api.check(path, text);
        if (seq !== checkSeq.current) return;
        setCheck(c);
        if (c.summary) setSummary(c.summary);
      } catch (e) { setStatus(String(e)); }
    }, 350);
    return () => window.clearTimeout(id);
  }, [path, text]);

  // ------------------------------------------------------------------ render / remix
  // Always renders the latest text and mute/solo; a request made while one runs is folded into one more run.
  const render = useCallback(async (play?: boolean) => {
    if (busy.current) { again.current = true; return; }
    busy.current = true;
    const a = audio.current;
    try {
      do {
        again.current = false;
        const { path: p, text: t, mute: m, solo: s } = latest.current;
        if (!p) break;
        setRendering(rendered && rendered.text.replace(/^(mix|inserts)\s.*$/gm, "") === t.replace(/^(mix|inserts)\s.*$/gm, "") ? "remix" : "render");
        setStatus("rendering…");
        const r = await api.render(p, t, [...m], [...s]);
        setCheck(r.check);
        if (!r.ok) { setTab("problems"); setStatus("can't render: the song has errors"); break; }
        const wasPlaying = !a.paused, pos = a.src ? a.currentTime : time;     // where we are now, at the swap
        setRendered({ text: t, listen: [...m].sort().join(",") + "|" + [...s].sort().join(","), audio: r.audio });
        setQA(r.qa);
        a.src = r.audio;
        await new Promise((res) => { a.addEventListener("loadedmetadata", res, { once: true }); a.addEventListener("error", res, { once: true }); });
        a.currentTime = Math.min(pos, a.duration || pos);
        if (play || wasPlaying) await a.play().catch(() => undefined);
        setStatus(`${r.remixed ? "remixed" : "rendered"} ${fmt(r.seconds)} in ${r.elapsed}s`);
      } while (again.current);
    } catch (e) { setStatus(String(e)); }
    busy.current = false;
    setRendering("");
  }, [rendered, time]);

  const play = useCallback(async () => {
    const a = audio.current;
    if (!rendered || stale) return render(true);
    if (a.paused) await a.play(); else a.pause();
  }, [rendered, stale, render]);
  const seek = useCallback((t: number) => { setTime(t); if (audio.current.src) audio.current.currentTime = t; }, []);
  const stop = () => { audio.current.pause(); seek(loop ? loop[0] : 0); };

  // the clock: rAF while visible, timeupdate as a fallback (rAF pauses in hidden tabs)
  useEffect(() => {
    const a = audio.current;
    let raf = 0;
    const sync = () => {
      if (loop && a.currentTime >= loop[1]) a.currentTime = loop[0];
      setTime(a.currentTime);
    };
    const tick = () => { sync(); raf = requestAnimationFrame(tick); };
    const on = () => { setPlaying(true); cancelAnimationFrame(raf); raf = requestAnimationFrame(tick); };
    const off = () => { setPlaying(false); cancelAnimationFrame(raf); sync(); };
    a.addEventListener("play", on); a.addEventListener("pause", off); a.addEventListener("ended", off); a.addEventListener("timeupdate", sync);
    return () => {
      a.removeEventListener("play", on); a.removeEventListener("pause", off); a.removeEventListener("ended", off);
      a.removeEventListener("timeupdate", sync); cancelAnimationFrame(raf);
    };
  }, [loop]);

  // listening changes (mute/solo) remix the current render
  const toggle = (set: React.Dispatch<React.SetStateAction<Set<string>>>) => (p: string) =>
    set((s) => { const n = new Set(s); n.has(p) ? n.delete(p) : n.add(p); return n; });
  const firstListen = useRef(true);
  useEffect(() => {
    if (firstListen.current) { firstListen.current = false; return; }
    if (rendered) render();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listenKey]);

  // a GUI edit is a text operation on the server; the new text is the state
  const applyOp = async (op: string, args: object, remix: boolean) => {
    if (!path) return;
    try {
      const r = await api.op(path, latest.current.text, op, args);
      latest.current = { ...latest.current, text: r.text };
      setText(r.text); setCheck(r.check);
      if (r.check.summary) setSummary(r.check.summary);
      if (remix && rendered) render();
    } catch (e) { setStatus(String(e)); throw e; }
  };
  const mixEdit = (part: string, edit: MixEdit, defaultGain: number) =>
    applyOp("mix", { part, ...edit, default_gain: defaultGain }, true).catch(() => undefined);
  const voiceEdit = (e: VoiceEdit) => applyOp("voice", e, false).catch(() => undefined);
  const insertsEdit = (part: string, chain: InsertSpec[]) => applyOp("inserts", { part, chain }, true).catch(() => undefined);

  const section = summary?.sections.find((s) => time >= s.start && time < s.end) ?? null;
  const jump = (dir: 1 | -1) => {
    if (!summary) return;
    const ss = summary.sections;
    const i = ss.findIndex((s) => time >= s.start && time < s.end);
    const cur = i < 0 ? ss.length - 1 : i;
    const target = dir < 0 ? (time - ss[cur].start > 1 ? cur : Math.max(0, cur - 1)) : Math.min(ss.length - 1, cur + 1);
    seek(ss[target].start);
  };
  const gotoSection = (i: number) => {
    const s = summary?.sections.find((x) => x.index === i);
    if (s?.line) { setDock("code"); setGoto({ line: s.line, n: Date.now() }); }
  };
  const barBeat = (() => {
    if (!summary) return "–";
    const bt = summary.bar_times;
    const i = Math.max(0, bt.findIndex((b) => b > time) - 1);
    const len = (bt[i + 1] ?? bt[i] + 1) - bt[i];
    const beats = +summary.meter.split("/")[0] || 4;
    const beat = Math.floor(((time - bt[i]) / Math.max(len, 1e-6)) * beats) + 1;
    return `${i + 1}.${Math.min(beat, beats)}`;
  })();

  // ------------------------------------------------------------------ keys
  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if (dock === "lab") return;
      const mod = e.ctrlKey || e.metaKey;
      const typing = !!(e.target as HTMLElement).closest(".cm-editor, input, select, textarea");
      if (mod && e.key === "s") { e.preventDefault(); save(); }
      else if (mod && e.key === "Enter") { e.preventDefault(); render(true); }
      else if (typing) return;
      else if (e.key === " ") { e.preventDefault(); play(); }
      else if (e.key === "Home") seek(0);
      else if (e.key === "[") jump(-1);
      else if (e.key === "]") jump(1);
      else if (e.key === "l") setLoop((l) => (l ? null : section ? [section.start, section.end] : null));
      else if (e.key === "m") setDock((d) => (d === "mixer" ? "code" : "mixer"));
      else if (e.key === "i") setDock((d) => (d === "rack" ? "code" : "rack"));
      else if (e.key === "p") setDock((d) => (d === "roll" ? "code" : "roll"));
      else if (e.key === "v") setDock((d) => (d === "video" ? "code" : "video"));
    };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  });
  useEffect(() => {
    const b = (e: BeforeUnloadEvent) => { if (dirty) e.preventDefault(); };
    window.addEventListener("beforeunload", b);
    return () => window.removeEventListener("beforeunload", b);
  }, [dirty]);

  const nErr = check?.diagnostics.filter((d) => d.severity === "error").length ?? 0;
  const nWarn = check?.diagnostics.filter((d) => d.severity === "warning").length ?? 0;
  const tabs: [Tab, string, number][] = [["teacher", "Teacher", 0], ["problems", "Problems", nErr || nWarn], ["qa", "QA", 0], ["export", "Export", 0]];
  const cols = dock === "lab" ? "0px 0px minmax(0, 1fr) 0px 0px" : `${filesOpen ? filesW : 0}px ${filesOpen ? 4 : 0}px minmax(0, 1fr) 4px ${inspW}px`;

  return (
    <div className={`app${dock === "lab" ? " lab-mode" : ""}`} style={{ gridTemplateColumns: cols, gridTemplateRows: dock === "lab" ? "46px 0px 0px minmax(0, 1fr) 0px" : `46px ${arrH}px 4px minmax(0, 1fr) 58px` }}>
      <header>
        <button className="ghost icon" title="Show or hide the file list" onClick={() => setFilesOpen((o) => !o)}>☰</button>
        <span className="logo"><Logo /> SongMap <em>Studio</em></span>
        <span className="path">{path ?? "no song open"}{dirty && <i className="dot" title="unsaved changes" />}</span>
        {summary && (
          <span className="facts-bar">
            <b>{summary.title}</b>
            <span className="pill">{summary.tempo} bpm</span><span className="pill">{summary.meter}</span>
            <span className="pill">{summary.key}</span><span className={"pill" + (summary.tuning !== "12edo" ? " gold" : "")}>{summary.tuning}</span>
            <span className="pill">{summary.length}</span>
          </span>
        )}
        <span className="spacer" />
        {check && <span className={"pill check " + (check.ok ? "ok" : "bad")} onClick={() => setTab("problems")}>
          {check.ok ? `✓ checked · ${check.ms} ms` : `✗ ${nErr} error${nErr === 1 ? "" : "s"}`}</span>}
        <button disabled={!path || !dirty} onClick={save} title="Ctrl+S">Save</button>
      </header>
      {filesOpen ? <FileBrowser files={files} current={path} onOpen={(p) => open(p).catch((e) => setStatus(String(e)))} onNew={create} /> : <div className="files" />}
      {filesOpen ? <Splitter area="s1" dir="x" value={filesW} set={setFilesW} min={160} max={480} /> : <div style={{ gridArea: "s1" }} />}
        {summary ? (
          <Arrangement summary={summary} time={time} loop={loop} mute={mute} solo={solo} colorOf={colorOf} sectionColor={sectionColor}
                       onSeek={seek} onLoop={setLoop} onSection={gotoSection} onMute={toggle(setMute)} onSolo={toggle(setSolo)} />
        ) : (
          <div className="arr empty">
            <div className="welcome">
              <Logo />
              <h2>{path ? "Fix the errors to see the arrangement" : "SongMap Studio"}</h2>
              {!path && <p className="muted">Open a song on the left, or start a new one. Write it as code; shape it with the mixer, arrangement and video panes; render audio, stems and video.</p>}
            </div>
          </div>
        )}
        <Splitter area="sy" dir="y" value={arrH} set={setArrH} min={120} max={900} />
        <div className="dock">
          <nav className="dock-tabs">
            <button className={dock === "code" ? "on" : ""} onClick={() => setDock("code")}>Code</button>
            <button className={dock === "lab" ? "on" : ""} onClick={() => { audio.current.pause(); setDock("lab"); }}>AI Lab</button>
            <button className={dock === "roll" ? "on" : ""} onClick={() => setDock("roll")} disabled={!summary}>Piano roll <kbd>P</kbd></button>
            <button className={dock === "rack" ? "on" : ""} onClick={() => setDock("rack")} disabled={!summary}>Instruments <kbd>I</kbd></button>
            <button className={dock === "mixer" ? "on" : ""} onClick={() => setDock("mixer")} disabled={!summary}>Mixer <kbd>M</kbd></button>
            <button className={dock === "video" ? "on" : ""} onClick={() => setDock("video")} disabled={!path}>Video <kbd>V</kbd></button>
            <span className="spacer" />
            {dock === "code" && <span className="muted small">Ctrl+S save · Ctrl+Enter render · Space play · [ ] sections · L loop</span>}
          </nav>
          <div className="dock-body">
            {dock === "lab" && <AILab currentPath={path} dirty={dirty} onApplied={(paths) => {
              if (path && paths.includes(path)) api.project(path).then(r => {
                setText(r.text); setSaved(r.text); setCheck(r.check); setSummary(r.check.summary); setRendered(null); setQA(null);
              }).catch(e => setStatus(String(e)));
              setStatus(`Applied instrument edits to ${paths.length} score(s)`);
            }} />}
            {path && <div className="code-wrap" style={{ display: dock === "code" ? "block" : "none" }}>
              <CodeEditor value={text} onChange={setText} diagnostics={check?.diagnostics ?? []} gotoLine={goto} />
            </div>}
            {dock === "video" && path && (
              <VideoDesigner path={path} text={text} time={time} summary={summary} view={view} setView={setView} ok={!!check?.ok} onSeek={seek} />
            )}
            {dock === "roll" && summary && path && (
              <PianoRoll path={path} text={text} summary={summary} time={time} partHint={null} colorOf={colorOf} onSeek={seek}
                         onApply={(op, args) => applyOp(op, args, false)} />
            )}
            {dock === "rack" && summary && path && (
              <Rack path={path} text={text} summary={summary} catalog={catalog} onEdit={voiceEdit} colorOf={colorOf} time={time}
                    onApply={(op, args) => applyOp(op, args, false)} />
            )}
            {dock === "mixer" && summary && (
              <Mixer summary={summary} qa={qa} mute={mute} solo={solo} busy={rendering === "remix"} colorOf={colorOf} catalog={catalog}
                     onMute={toggle(setMute)} onSolo={toggle(setSolo)} onEdit={mixEdit} onInserts={insertsEdit} />
            )}
          </div>
        </div>
      <Splitter area="s2" dir="x" value={inspW} set={setInspW} min={260} max={720} invert />
      <section className="inspector">
        <nav>{tabs.map(([k, l, n]) => <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>
          {l}{n > 0 && <span className={"badge" + (nErr ? " bad" : "")}>{n}</span>}</button>)}</nav>
        <div className="tab-body">
          {tab === "teacher" && path && <Teacher path={path} text={text} summary={summary} time={time} onSeek={seek} ok={!!check?.ok} />}
          {tab === "problems" && <Problems check={check} onLine={(line) => { setDock("code"); setGoto({ line, n: Date.now() }); }} />}
          {tab === "qa" && <QAPanel qa={qa} stale={stale} />}
          {tab === "export" && path && <ExportPanel path={path} text={text} view={view} time={time} ok={!!check?.ok} />}
        </div>
      </section>
      <footer className="transport">
        <button className={"render-btn" + (rendering ? " busy" : "")} disabled={!path || !!rendering} onClick={() => render(true)} title="Ctrl+Enter">
          {rendering === "render" ? "Rendering…" : rendering === "remix" ? "Remixing…" : stale || !rendered ? "Render" : "Re-render"}
        </button>
        <div className="tbuttons">
          <button className="ghost" disabled={!summary} onClick={() => jump(-1)} title="Previous section  [">⏮</button>
          <button className="play" disabled={!path} onClick={play} title="Space">{playing ? "❚❚" : "▶"}</button>
          <button className="ghost" disabled={!summary} onClick={() => jump(1)} title="Next section  ]">⏭</button>
          <button className="ghost" disabled={!rendered} onClick={stop} title="Stop (back to the start or the loop)">■</button>
          <button className={"ghost" + (loop ? " on" : "")} disabled={!section && !loop}
                  onClick={() => setLoop((l) => (l ? null : section ? [section.start, section.end] : null))} title="Loop the current section  L">⟲</button>
        </div>
        <div className="lcd">
          <div><b>{barBeat}</b><span>bar.beat</span></div>
          <div><b>{fmt(time)}</b><span>/ {summary?.length ?? "–"}</span></div>
          <div className="lcd-sec">
            <b style={{ color: section ? sectionColor(section.name) : undefined }}>{section?.name ?? "–"}</b>
            <span>{loop ? `loop ${fmt(loop[0])}–${fmt(loop[1])}` : "section"}</span>
          </div>
        </div>
        {stale && <span className="pill warn" title="The audio is from an earlier version of the song or of mute/solo">audio out of date</span>}
        <span className="spacer" />
        <span className="muted status">{status}</span>
        <label className="vol" title="Monitor volume (not the song's)">
          <span>monitor</span>
          <input type="range" min={0} max={1} step={0.01} defaultValue={1} onChange={(e) => { audio.current.volume = +e.target.value; }} />
        </label>
      </footer>
    </div>
  );
}
