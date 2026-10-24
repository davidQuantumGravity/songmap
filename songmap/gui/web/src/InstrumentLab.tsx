import { useEffect, useMemo, useRef, useState } from "react";
import "./instrument-lab.css";

type Occurrence = { path: string; title: string; kind: string; part: string; piece: string | null; use: string; notes: number; sections: string[]; first_seconds: number };
type Assessment = { need: number; note: string };
type SessionInfo = { id: string; path: string; part: string; piece: string | null; use: string; brief: string; status: string; updated: number };
type Inventory = { sources: {path: string; title: string; kind: string; seconds: number; instruments: string[]}[]; occurrences: Occurrence[]; errors: {path: string; message: string}[]; assessments: Record<string, Assessment>; sessions: SessionInfo[] };
type Candidate = { id: string; take: number; display_name: string; verified_use: string; changes: {field:string;before:unknown;after:unknown}[]; label: string; origin: string; reason: string; source: string; change: { use: string; params: Record<string, number> }; audio: Record<string, string>; loudness: Record<string, number> };
type Vote = {event_id: string; choice: string; text: string; pair: string[]; mode?: string; selected_take?:number; selected_voice?:string};
type Session = SessionInfo & { start: number; seconds: number; candidates: Candidate[]; pair: string[]; previous_pair?:string[]; incumbent: string; feedback: Vote[]; error: string; updated:number; generation?:{base_candidate:string;candidate?:string;feedback_events:string[];completed_at?:number}; audition?:{target:{part:string;piece:string|null};accompaniment:{part:string;name:string;use:string}[];solo_label:string}; applied: {id: string; restored?: number; files: {path: string}[]}[] };
type Preview = {path: string; before: string; hash: string; text: string; targets: [string, string | null][]};

async function request<T>(path: string, body?: unknown, method = "POST"): Promise<T> {
  const res = await fetch(`/api/lab${path}`, body === undefined ? undefined : {method, headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
  const data = await res.json();
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail));
  return data;
}
const busy = (s: Session | null) => !!s && ["queued", "generating", "rendering"].includes(s.status);
const titleOf = (o: Occurrence) => `${o.title} · ${o.part}${o.piece ? ` / ${o.piece}` : ""} · ${o.path}`;

export function AILab({currentPath, dirty, onApplied}: {currentPath: string | null; dirty: boolean; onApplied: (paths: string[]) => void}) {
  const [inventory, setInventory] = useState<Inventory | null>(null);
  const [status, setStatus] = useState("Scanning saved scores…");
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [scope, setScope] = useState("main");
  const [order, setOrder] = useState("reach");
  const [selected, setSelected] = useState("");
  const [occurrence, setOccurrence] = useState<Occurrence | null>(null);
  const [start, setStart] = useState(0);
  const [seconds, setSeconds] = useState(12);
  const [brief, setBrief] = useState("Make this instrument more convincing in the song. Preserve the notes and expression.");
  const [session, setSession] = useState<Session | null>(null);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [need, setNeed] = useState(0);
  const [note, setNote] = useState("");
  const [feedback, setFeedback] = useState("");
  const [auto, setAuto] = useState(true);
  const [pending, setPending] = useState(false);
  const [mode, setMode] = useState("solo");
  const [side, setSide] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [position, setPosition] = useState(0);
  const [match, setMatch] = useState(true);
  const [loop, setLoop] = useState(true);
  const [manualUse, setManualUse] = useState("");
  const [manualParams, setManualParams] = useState("{}");
  const [targets, setTargets] = useState<string[]>([]);
  const [preview, setPreview] = useState<Preview[]>([]);
  const [provider, setProvider] = useState<{available: boolean; detail: string} | null>(null);
  const players = useRef<[HTMLAudioElement, HTMLAudioElement]>([new Audio(), new Audio()]);
  const sideRef = useRef(0);
  const lastPair = useRef("");
  const loopRef = useRef(loop); loopRef.current = loop;
  const available = useMemo(() => {
    const groups = new Map<string, {use: string; occurrences: Occurrence[]; count: number; notes: number; priority: number}>();
    for (const o of inventory?.occurrences ?? []) {
      if (scope === "main" && !["song", "textbook"].includes(o.kind)) continue;
      if (!["main", "all"].includes(scope) && o.kind !== scope) continue;
      const g = groups.get(o.use) ?? {use: o.use, occurrences: [], count: 0, notes: 0, priority: 0};
      g.occurrences.push(o); g.notes += o.notes; groups.set(o.use, g);
    }
    for (const g of groups.values()) {g.count = new Set(g.occurrences.map(o => o.path)).size; g.priority = g.count * (1 + (inventory?.assessments[g.use]?.need ?? 0));}
    const q = search.toLowerCase();
    return [...groups.values()].filter(g => `${g.use} ${g.occurrences.map(o => `${o.title} ${o.path} ${o.part} ${o.piece ?? ""}`).join(" ")}`.toLowerCase().includes(q))
      .sort((a,b) => (order === "priority" ? b.priority - a.priority : b.count - a.count) || b.notes - a.notes || a.use.localeCompare(b.use));
  }, [inventory, scope, order, search]);
  const group = available.find(g => g.use === selected);
  const audioMode = mode === "solo" && match ? "focus" : mode;
  const proposedPair = session?.pair.map(id => session.candidates.find(c => c.id === id)!) ?? [];
  const pair = busy(session) && !proposedPair.every(c=>c.audio[audioMode]) && session?.previous_pair?.length === 2
    ? session.previous_pair.map(id=>session.candidates.find(c=>c.id===id)!) : proposedPair;
  const loadedPair = pair.length === 2 && pair.every(c => c.audio[audioMode]);
  const pairKey = pair.map(c=>c.id).join(":");
  const takeName = (id:string) => {const c=session?.candidates.find(c=>c.id===id);return c?`Take ${c.take}`:"Original take";};
  const selectedTake = pair[side]?.take;
  const background = session?.audition?.accompaniment.map(a=>`${a.name} (${a.part})`).join(", ") ?? "";

  async function run<T>(fn: () => Promise<T>) {setPending(true); setError(""); try {return await fn();} catch(e) {setError(String(e));} finally {setPending(false);}}
  async function scan() {
    setStatus("Scanning saved scores…");
    const r = await request<Inventory>("/inventory"); setInventory(r); setSessions(r.sessions);
    setStatus(`${r.sources.length} saved scores · ${new Set(r.occurrences.map(o => o.use)).size} played voices`);
  }
  useEffect(() => {run(async()=>{await scan();const saved=new URLSearchParams(location.search).get("comparison");if(saved)await loadSession(saved);}); request<typeof provider>("/provider").then(setProvider).catch(e => setError(String(e)));}, []);
  useEffect(() => {
    if (!busy(session)) return;
    let active=true, timer=0;
    const poll=async()=>{try {const r=await request<Session>(`/sessions/${session!.id}`);if(active)setSession(prev=>prev?.id===r.id && r.updated>=prev.updated?r:prev);}catch(e){if(active)setError(String(e));}finally{if(active)timer=window.setTimeout(poll,1500);}};
    timer=window.setTimeout(poll,500);
    return () => {active=false;clearTimeout(timer);};
  }, [session?.id, session?.status]);
  useEffect(() => {if (!selected && available.length) select(available[0].use);}, [available, selected]);
  useEffect(() => {
    if (!session || !inventory) return;
    const o=inventory.occurrences.find(o=>o.path===session.path && o.part===session.part && o.piece===session.piece);
    const a=inventory.assessments[session.use];
    setSelected(session.use);setSearch("");setNeed(a?.need ?? 0);setNote(a?.note ?? "");
    setOccurrence(o ?? null);setStart(session.start);setSeconds(session.seconds);setBrief(session.brief);
    if(o && ["study","example"].includes(o.kind))setScope("all");
  }, [session?.id, !!inventory]);
  useEffect(() => {
    const [a,b] = players.current;
    const ended = () => {if (loopRef.current) {const p = players.current[sideRef.current]; p.currentTime=0; p.play().catch(e => setError(String(e)));} else setPlaying(false);};
    const tick = () => setPosition(players.current[sideRef.current].currentTime || 0);
    a.addEventListener("ended", ended); b.addEventListener("ended", ended); a.addEventListener("timeupdate", tick); b.addEventListener("timeupdate", tick);
    return () => {for(const p of [a,b]) {p.pause(); p.removeEventListener("ended",ended); p.removeEventListener("timeupdate",tick);} };
  }, []);
  useEffect(() => {
    const current=players.current[sideRef.current], wasPlaying=!current.paused, oldTime=current.currentTime||0;
    const changed=lastPair.current!==pairKey, nextSide=changed && pair.length===2?1:sideRef.current;
    lastPair.current=pairKey;sideRef.current=nextSide;setSide(nextSide);setPlaying(false);setPosition(changed?0:oldTime);setPreview([]);
    const cleanups:(()=>void)[]=[];
    pair.forEach((c,i) => {const p=players.current[i];p.pause();const loaded=()=>{p.currentTime=changed?0:Math.min(oldTime,Math.max(0,p.duration-.01));if(i===nextSide && wasPlaying)p.play().then(()=>setPlaying(true)).catch(e=>setError(String(e)));};p.addEventListener("loadedmetadata",loaded,{once:true});cleanups.push(()=>p.removeEventListener("loadedmetadata",loaded));p.src=c.audio[audioMode]??"";p.load();});
    return () => cleanups.forEach(f=>f());
  }, [pairKey, audioMode, loadedPair]);
  useEffect(() => {
    const levels = pair.map(c=>c.loudness[audioMode] ?? -99);
    const target = Math.min(...levels);
    pair.forEach((_,i) => {players.current[i].volume = match ? Math.max(0, Math.min(1, 10 ** ((target-levels[i])/20))) : 1;});
  }, [pairKey, audioMode, match, loadedPair]);

  function select(use: string) {
    setSelected(use); const a=inventory?.assessments[use]; setNeed(a?.need ?? 0); setNote(a?.note ?? "");
    const first=available.find(g=>g.use===use)?.occurrences[0] ?? null; chooseOccurrence(first);
  }
  function chooseOccurrence(o: Occurrence | null) {setOccurrence(o); setStart(o?.first_seconds ?? 0);}
  function linkSession(id:string) {const url=new URL(location.href);url.searchParams.set("lab","1");url.searchParams.set("comparison",id);history.replaceState(null,"",url);}
  async function loadSession(id: string) {players.current.forEach(p=>p.pause()); const s=await request<Session>(`/sessions/${id}`);setSession(s);setFeedback("");setMode("solo");setManualUse(s.candidates.find(c=>c.id===s.incumbent)?.change.use ?? s.use);setManualParams("{}");setPreview([]);setTargets([s.path]);linkSession(s.id);}
  async function create() {
    if (!occurrence) return;
    const s=await request<Session>("/sessions", {path: occurrence.path, part: occurrence.part, piece: occurrence.piece, start, seconds, brief});
    setSession(await request<Session>(`/sessions/${s.id}`));setMode("solo");setFeedback(""); setTargets([s.path]); setSessions(prev=>[s,...prev]); setManualUse(s.use); setManualParams("{}");
    linkSession(s.id);
  }
  async function generate() {
    if(!session)return;
    const text=feedback;
    const draft=text.trim()?{event_id:crypto.randomUUID(),pair:session.pair,text,mode}:undefined;
    await request<Session>(`/sessions/${session.id}/generate`, {feedback:draft});
    setSession(await request<Session>(`/sessions/${session.id}`));setFeedback(prev=>prev===text?"":prev);
  }
  async function vote(choice: string) {
    if (!session) return;
    const text=feedback;
    const s=await request<Session>(`/sessions/${session.id}/feedback`, {event_id: crypto.randomUUID(), pair: session.pair, choice, text, mode});
    setSession(await request<Session>(`/sessions/${s.id}`));setFeedback(prev=>prev===text?"":prev); setPreview([]);
    if(auto && choice !== "comment" && provider?.available) {await request(`/sessions/${s.id}/generate`, {});setSession(await request<Session>(`/sessions/${s.id}`));}
  }
  async function switchSide(i: number) {
    if (!loadedPair) return;
    const old=players.current[sideRef.current], next=players.current[i];
    const wasPlaying=!old.paused, t=old.currentTime;
    old.pause();
    if (next.readyState < 1) await new Promise<void>((resolve,reject)=>{next.addEventListener("loadedmetadata",()=>resolve(),{once:true});next.addEventListener("error",()=>reject(new Error("Audio could not load")),{once:true});});
    next.currentTime=Math.min(t,Math.max(0,(next.duration || session!.seconds)-.01)); sideRef.current=i; setSide(i);
    if(wasPlaying) {await next.play(); setPlaying(true);} else setPlaying(false);
  }
  async function play() {const p=players.current[sideRef.current]; if(p.paused) {await p.play();setPlaying(true);} else {p.pause();setPlaying(false);}}
  const matches = inventory?.occurrences.filter(o=>o.use===session?.use) ?? [];
  const targetPaths = [...new Set([...(session ? [session.path] : []), ...matches.map(o=>o.path)])];

  return <div className="instrument-lab" onKeyDown={e=>e.stopPropagation()}>
    <section className="lab-library">
      <div className="lab-heading"><div><h2>AI Lab</h2><p>Compare and refine music with AI.</p></div><button disabled={pending} onClick={()=>run(scan)}>Refresh inventory</button></div>
      <p className="small muted">Current tool: instrument sound. Melody and mastering tools will join this workspace.</p>
      <p className="small muted">{status}. Counts refer to source files; study copies can be filtered out. {inventory&&<a href="/api/lab/inventory.csv" download>Export song–instrument map (CSV)</a>}</p>
      {error && <p role="alert" className="lab-error">{error}</p>}
      <div className="lab-filters">
        <input aria-label="Find instrument or song" placeholder="Find an instrument, song, or kit piece" value={search} onChange={e=>setSearch(e.target.value)}/>
        <select aria-label="Inventory scope" value={scope} onChange={e=>setScope(e.target.value)}><option value="main">Songs + textbook</option><option value="song">Songs</option><option value="textbook">Textbook</option><option value="study">Studies + revisits</option><option value="example">Examples</option><option value="all">All saved scores</option></select>
        <select aria-label="Instrument order" value={order} onChange={e=>setOrder(e.target.value)}><option value="reach">Most used</option><option value="priority">Improvement priority</option></select>
      </div>
      <div className="lab-list" role="region" aria-label="Instrument usage"><table><thead><tr><th>Played voice</th><th>Scores</th><th>Notes / hits</th><th>Need</th></tr></thead><tbody>{available.map(g=><tr key={g.use} className={g.use===selected?"selected":""}><td><button onClick={()=>select(g.use)}>{g.use}</button></td><td>{g.count}</td><td>{g.notes.toLocaleString()}</td><td>{["Unrated","Some","High","Highest"][inventory?.assessments[g.use]?.need ?? 0]}</td></tr>)}</tbody></table></div>
      {group && <div className="lab-focus">
        <h3>Original voice: {group.use}</h3>
        <label>Improvement need <select value={need} onChange={e=>setNeed(+e.target.value)}><option value={0}>Unrated / no extra priority</option><option value={1}>Some improvement</option><option value={2}>High need</option><option value={3}>Highest need</option></select></label>
        <textarea aria-label="Instrument improvement notes" placeholder="What needs work? These notes also go to the AI." value={note} maxLength={4000} onChange={e=>setNote(e.target.value)}/>
        <button disabled={pending} onClick={()=>run(async()=>{const a=await request<Assessment>("/assessment",{use:selected,need,note},"PUT");setInventory(prev=>prev?{...prev,assessments:{...prev.assessments,[selected]:a}}:prev);})}>Save priority and notes</button>
        <p className="small muted">Priority = score count × (1 + improvement need). Usage is measured; improvement need is your assessment.</p>
        <label>Song and part <select aria-label="Song and part" value={occurrence?`${occurrence.path}|${occurrence.part}|${occurrence.piece}`:""} onChange={e=>chooseOccurrence(group.occurrences.find(o=>`${o.path}|${o.part}|${o.piece}`===e.target.value) ?? null)}>{group.occurrences.map(o=><option key={`${o.path}|${o.part}|${o.piece}`} value={`${o.path}|${o.part}|${o.piece}`}>{titleOf(o)}</option>)}</select></label>
        <div className="lab-time"><label>Start (seconds)<input type="number" min={0} step={.5} value={start} onChange={e=>setStart(+e.target.value)}/></label><label>Length (seconds)<input type="number" min={1} max={30} value={seconds} onChange={e=>setSeconds(+e.target.value)}/></label></div>
        <textarea aria-label="Comparison direction" value={brief} maxLength={4000} onChange={e=>setBrief(e.target.value)}/>
        <button className="primary" disabled={pending || !occurrence} onClick={()=>run(create)}>Start instrument comparison</button>
      </div>}
      {!!inventory?.errors.length && <details><summary>{inventory.errors.length} scores could not be indexed</summary>{inventory.errors.map(e=><p key={e.path}><b>{e.path}</b><br/>{e.message}</p>)}</details>}
    </section>
    <section className="lab-workspace">
      <div className="lab-heading"><h2>Compare and refine</h2><select aria-label="Saved comparisons" value={session?.id ?? ""} onChange={e=>e.target.value && run(()=>loadSession(e.target.value))}><option value="">Saved comparisons…</option>{sessions.map(s=><option key={s.id} value={s.id}>{s.path} · {s.piece ?? s.part} · {new Date(s.updated*1000).toLocaleDateString()}</option>)}</select></div>
      {!session ? <p className="lab-empty">Choose a voice and an actual passage from the music, then start a comparison. Every vote, comment, and candidate is saved locally.</p> : <>
        <p><b>{session.part}{session.piece?` / ${session.piece}`:""}</b> · {session.path}<br/><span className="muted">{session.start.toFixed(1)}–{(session.start+session.seconds).toFixed(1)}s · {session.brief}</span></p>
        <p className="small"><b>Editing: instrument sound for {session.part}{session.piece?` / ${session.piece}`:""}.</b> Notes and expression stay fixed.</p>
        <div className="lab-listening"><label>Listen to <select aria-label="Listening context" value={mode} onChange={e=>setMode(e.target.value)}><option value="solo">{session.audition?.solo_label ?? "Changed part only"} — isolated</option><option value="context">Full song — includes accompaniment</option></select></label><p className="small">{mode==="context"?`You are hearing the full song${background?`, including ${background}`:""}. Only ${session.part}${session.piece?` / ${session.piece}`:""} changes.`:`You are hearing ${session.part} alone${session.piece?" (the whole kit; only the selected piece changes)":""}${background?`; ${background} is muted`:""}.`}</p></div>
        <div className="lab-actions"><button className="primary" disabled={pending || busy(session) || !provider?.available || session.candidates.length>=24} onClick={()=>run(generate)}>Generate next challenger</button><button disabled={pending || busy(session)} onClick={()=>run(async()=>setSession(await request<Session>(`/sessions/${session.id}/render`,{})))}>Render comparison</button>{busy(session)&&<button onClick={()=>run(async()=>setSession(await request<Session>(`/sessions/${session.id}/stop`,{})))}>Stop</button>}</div>
        <p role="status" aria-live="polite" className="lab-progress">{busy(session)?`${session.status === "queued"?"Queued":session.status === "generating"?"AI is writing":"Rendering audio for"} the next challenger to ${takeName(session.generation?.base_candidate ?? session.incumbent)}. ${session.generation?.feedback_events.length ?? session.feedback.length} saved feedback entries included.`:session.status==="ready"&&pair.length===2?`Take ${pair[1].take} is ready. Compare A (Take ${pair[0].take}) with B (Take ${pair[1].take}).`:session.status==="ready"?"Original take saved. Generate a challenger to begin.":session.status} <span className="muted">{session.candidates.length}/24 takes</span></p>
        <p className="small muted">{provider?.available ? "AI uses your configured Codex CLI model and sign-in. One request generates one challenger." : "Codex CLI is unavailable. Manual challengers and saved comparisons still work."}</p>
        {session.error && <p role="alert" className="lab-error">{session.error}</p>}
        <div className="lab-candidates">{pair.map((c,i)=><article key={c.id} className={side===i?"active":""}><button aria-pressed={side===i} disabled={!loadedPair} onClick={()=>run(()=>switchSide(i))}>{i===0?"A":"B"} · Take {c.take}</button><p><b>{c.display_name}</b><br/><code>{c.verified_use}</code></p><p className="small">{session.incumbent===c.id?"Your current pick":i===1?"Challenger — not yet chosen":"Reference take"}</p>{i===1 && c.changes?.length?<ul className="lab-changes">{c.changes.map((ch,k)=><li key={k}>{ch.field}: {String(ch.before)} → {String(ch.after)}</li>)}</ul>:<p className="small muted">{i===0?"Reference for this round.":"Original score’s instrument settings."}</p>}<details><summary>Verified instrument settings</summary><pre>{JSON.stringify(c.change,null,2)}</pre></details>{c.origin==="codex"&&<details><summary>AI proposal notes</summary><p className="small">Suggested name: {c.label}</p><p className="small">{c.reason}</p></details>}</article>)}</div>
        <div className="lab-player"><button disabled={!loadedPair} onClick={()=>run(play)}>{playing?"Pause":"Play"} {side===0?"A":"B"} · Take {selectedTake ?? 1}</button><input aria-label="Comparison position" type="range" min={0} max={session.seconds} step={.01} value={position} disabled={!loadedPair} onChange={e=>{const t=+e.target.value;players.current.forEach(p=>{if(p.readyState)p.currentTime=t;});setPosition(t);}}/><span>{position.toFixed(1)}s</span></div>
        <div className="lab-actions"><label><input type="checkbox" checked={match} onChange={e=>setMatch(e.target.checked)}/> Match audition loudness</label><label><input type="checkbox" checked={loop} onChange={e=>setLoop(e.target.checked)}/> Loop</label></div>
        <textarea aria-label="Listening feedback" placeholder="What is better or worse? E.g. B has better attacks, but the release is too short." maxLength={4000} value={feedback} onChange={e=>setFeedback(e.target.value)}/>
        <div className="lab-actions">{[["a","Prefer A"],["b","Prefer B"],["tie","Tie"],["neither","Neither"],["comment","Save comment"]].map(([value,label])=><button key={value} disabled={pending || busy(session) || (value === "comment" ? pair.length !== 2 : !loadedPair)} onClick={()=>run(()=>vote(value))}>{label}</button>)}</div>
        <p className="small muted">Your comment is included when you vote or generate the next challenger. Take numbers stay fixed when A/B changes.</p>
        <label className="small"><input type="checkbox" checked={auto} onChange={e=>setAuto(e.target.checked)}/> After each vote, generate the next challenger using all feedback</label>
        <details><summary>Manual challenger</summary><p className="small">Use a catalog voice and numeric parameters. Other writing stays fixed.</p><label>Voice<input value={manualUse} onChange={e=>setManualUse(e.target.value)} placeholder={session.use}/></label><label>Parameters (JSON)<textarea value={manualParams} onChange={e=>setManualParams(e.target.value)}/></label><button disabled={pending || busy(session)} onClick={()=>run(async()=>{setSession(await request<Session>(`/sessions/${session.id}/candidate`,{change:{use:manualUse||session.use,params:JSON.parse(manualParams)},label:"Manual challenger"}));})}>Add and render</button></details>
        <details><summary>Feedback history ({session.feedback.length}) and takes ({session.candidates.length})</summary>{session.feedback.map(f=><p key={f.event_id}><b>{f.selected_take?`You picked Take ${f.selected_take} (${f.selected_voice}; then ${f.choice.toUpperCase()})`:f.choice.toUpperCase()}</b><br/>{f.mode==="context"?"Heard the full song":f.mode==="solo"?"Heard the isolated part":"Listening mode was not recorded"} · {f.text || "No comment"}</p>)}{session.candidates.map(c=><details key={c.id}><summary>Take {c.take} · {c.display_name} · {c.origin==="codex"?"AI proposal":c.origin==="source"?"Original score":"Manual edit"}</summary><pre>{JSON.stringify(c.change,null,2)}</pre><a href={c.audio.focus ?? c.audio.solo} target="_blank" rel="noreferrer">Isolated {session.part} audio</a>{" · "}<a href={c.audio.context} target="_blank" rel="noreferrer">Full song with accompaniment</a>{c.origin==="codex"&&<p className="small">AI proposal notes: {c.reason}</p>}</details>)}</details>
        <details className="lab-apply"><summary>Apply the current favorite to saved scores</summary><p>The vote chooses a favorite. Applying changes the selected score files, with saved preimages. Preview before applying.</p><div className="lab-targets">{targetPaths.map(p=><label key={p}><input type="checkbox" checked={targets.includes(p)} onChange={e=>{setTargets(prev=>e.target.checked?[...prev,p]:prev.filter(x=>x!==p));setPreview([]);}}/>{p}</label>)}</div><button disabled={pending || busy(session) || !targets.length} onClick={()=>run(async()=>{if(dirty && currentPath && targets.includes(currentPath))throw new Error("Save your open score before previewing an applied change.");const r=await request<{files:Preview[]}>(`/sessions/${session.id}/preview`,{candidate:session.incumbent,paths:targets});setPreview(r.files);})}>Preview selected changes</button>
          {preview.map(p=><details key={p.path}><summary>{p.path} · {p.targets.length} voice edits</summary><div className="lab-diff"><pre>{p.before}</pre><pre>{p.text}</pre></div></details>)}
          {!!preview.length&&<button className="primary" disabled={pending || busy(session)} onClick={()=>run(async()=>{if(dirty && currentPath && targets.includes(currentPath))throw new Error("Save the open score first.");await request(`/sessions/${session.id}/apply`,{candidate:session.incumbent,paths:targets,expected:Object.fromEntries(preview.map(p=>[p.path,p.hash]))});setPreview([]);onApplied(targets);setSession(await request<Session>(`/sessions/${session.id}`));setStatus(`Applied favorite to ${targets.length} score(s).`);})}>Apply favorite to {preview.length} selected score(s)</button>}
        </details>
        {session.applied.filter(r=>!r.restored).map(r=><p key={r.id}><button disabled={pending || busy(session)} onClick={()=>run(async()=>{const paths=r.files.map(f=>f.path);if(dirty && currentPath && paths.includes(currentPath)) throw new Error("Save the open score first.");await request(`/sessions/${session.id}/undo`,{receipt:r.id});onApplied(paths);setSession(await request<Session>(`/sessions/${session.id}`));})}>Undo applied changes to {r.files.length} score(s)</button></p>)}
      </>}
    </section>
  </div>;
}
