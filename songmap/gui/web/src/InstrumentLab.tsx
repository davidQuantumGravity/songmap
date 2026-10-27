import { useEffect, useMemo, useRef, useState } from "react";
import "./instrument-lab.css";
import { MusicComparisonForm, comparisonNames, scopeDescription, type ComparisonType } from "./MusicComparisonForm";
import { LabScore, NoteRoll, type ComparisonScore } from "./LabScore";
import { BarRange, PassagePicker } from "./PassagePicker";
import { SoundDesigner } from "./SoundDesigner";

type Occurrence = { path: string; title: string; kind: string; part: string; piece: string | null; use: string; notes: number; sections: string[]; first_seconds: number };
type Assessment = { need: number; note: string };
type SessionInfo = { id: string; scope?:ComparisonType; path: string; part: string; piece: string | null; use: string; brief: string; status: string; updated: number };
type Inventory = { sources: {path: string; title: string; kind: string; seconds: number; instruments: string[]}[]; occurrences: Occurrence[]; errors: {path: string; message: string}[]; assessments: Record<string, Assessment>; scanned_at: number; cached: boolean };
type Candidate = { id: string; take: number; display_name: string; verified_use: string; changes: {field:string;before:unknown;after:unknown}[]; label: string; origin: string; reason: string; source: string; excerpt?:{path:string;start:number;seconds:number}; change: { use?: string; params?: Record<string, number> }; audio: Record<string, string>; loudness: Record<string, number> };
type Vote = {event_id: string; choice: string; text: string; pair: string[]; mode?: string; tags?:string[]; selected_take?:number; selected_voice?:string};
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
  const [comparisonType,setComparisonType]=useState<ComparisonType>("instrument");
  const [drawer,setDrawer]=useState<"setup"|"history"|"apply"|"revise"|null>(null);
  const [view,setView]=useState<"listening"|"score">(()=>localStorage.getItem("songmap.lab.view")==="score"?"score":"listening");
  const [scoreData,setScoreData]=useState<ComparisonScore|null>(null),[scoreError,setScoreError]=useState("");
  const [scoreRetry,setScoreRetry]=useState(0);
  const [tags,setTags]=useState<string[]>([]);
  const [loopRange,setLoopRange]=useState<[number,number]>([0,12]);
  const [developScope,setDevelopScope]=useState<"riff"|"arrangement">("riff"),[developPart,setDevelopPart]=useState("");
  const drawerRef=useRef<HTMLElement|null>(null),returnFocus=useRef<HTMLElement|null>(null);
  const drawerWasOpen=useRef(false);
  const [manualSource,setManualSource]=useState("");
  const [manualLabel,setManualLabel]=useState("Manual challenger");
  const [excerptPath,setExcerptPath]=useState(currentPath??"");
  const [excerptStart,setExcerptStart]=useState(0);
  const [inventory, setInventory] = useState<Inventory | null>(null);
  const [inventoryLoading, setInventoryLoading] = useState(true);
  const [inventoryError, setInventoryError] = useState("");
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sessionsError, setSessionsError] = useState("");
  const [sessionLoading, setSessionLoading] = useState(false);
  const [sessionError, setSessionError] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [scope, setScope] = useState(currentPath || new URLSearchParams(location.search).get("song") ? "current" : "main");
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
  const [auto, setAuto] = useState(false);
  const [pending, setPending] = useState(false);
  const [mode, setMode] = useState("solo");
  const [side, setSide] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [soundAudition,setSoundAudition]=useState<"shape"|"blend"|null>(null);
  const [soundStopSignal,setSoundStopSignal]=useState(0);
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
  const rangeRef=useRef(loopRange);rangeRef.current=loopRange;
  const keyboardRef=useRef<((e:KeyboardEvent)=>void)|null>(null);
  const sessionRequest = useRef(0);
  const requestedSession = useRef("");
  const currentSessionId=useRef(session?.id);currentSessionId.current=session?.id;
  const available = useMemo(() => {
    const groups = new Map<string, {use: string; occurrences: Occurrence[]; count: number; notes: number; priority: number}>();
    for (const o of inventory?.occurrences ?? []) {
      if (scope === "current" && o.path !== currentPath) continue;
      if (scope === "main" && !["song", "textbook"].includes(o.kind)) continue;
      if (!["main", "all", "current"].includes(scope) && o.kind !== scope) continue;
      const g = groups.get(o.use) ?? {use: o.use, occurrences: [], count: 0, notes: 0, priority: 0};
      g.occurrences.push(o); g.notes += o.notes; groups.set(o.use, g);
    }
    for (const g of groups.values()) {g.count = new Set(g.occurrences.map(o => o.path)).size; g.priority = g.count * (1 + (inventory?.assessments[g.use]?.need ?? 0));}
    const q = search.toLowerCase();
    return [...groups.values()].filter(g => `${g.use} ${g.occurrences.map(o => `${o.title} ${o.path} ${o.part} ${o.piece ?? ""}`).join(" ")}`.toLowerCase().includes(q))
      .sort((a,b) => (order === "priority" ? b.priority - a.priority : b.count - a.count) || b.notes - a.notes || a.use.localeCompare(b.use));
  }, [inventory, scope, order, search, currentPath]);
  const group = available.find(g => g.use === selected);
  const audioMode = mode === "solo" && match ? "focus" : mode;
  const proposedPair = session?.pair.map(id => session.candidates.find(c => c.id === id)!) ?? [];
  const pair = busy(session) && !proposedPair.every(c=>c.audio[audioMode]) && session?.previous_pair?.length === 2
    ? session.previous_pair.map(id=>session.candidates.find(c=>c.id===id)!) : proposedPair;
  const loadedPair = pair.length === 2 && pair.every(c => c.audio[audioMode]);
  const pairKey = pair.map(c=>c.id).join(":");
  const takeName = (id:string) => {const c=session?.candidates.find(c=>c.id===id);return c?`Take ${c.take}`:"Original take";};
  const selectedTake = pair[side]?.take;
  const sessionScope=session?.scope??"instrument";
  const musical=sessionScope!=="instrument";
  const snippets=sessionScope==="snippet";
  const canSolo=sessionScope==="instrument"||sessionScope==="riff";
  const selectedScore=scoreData?.takes.find(t=>t.id===pair[side]?.id);
  const favorite=session?.candidates.find(c=>c.id===session.incumbent);
  const favoriteSide=pair.findIndex(c=>c.id===session?.incumbent);
  const appliedFavorite=session?.applied.some(r=>!r.restored&&(r as {candidate?:string}).candidate===session.incumbent);
  const feedbackText=[...tags.map(t=>`[${t}]`),feedback.trim()].filter(Boolean).join(" ").slice(0,4000);
  const loopBars=selectedScore?.bars??[];
  const firstLoopBar=Math.max(0,loopBars.findIndex(b=>b.end>loopRange[0]+1e-5));
  const loopEndIndex=loopBars.findIndex(b=>b.end>=loopRange[1]-1e-5);
  const lastLoopBar=loopEndIndex<0?Math.max(0,loopBars.length-1):loopEndIndex;
  useEffect(()=>{if(session){setComparisonType(session.scope??"instrument");setManualSource(session.candidates.find(c=>c.id===session.incumbent)?.source??"");setExcerptPath(session.path);}},[session?.id,session?.incumbent]);
  useEffect(()=>{try{localStorage.setItem("songmap.lab.view",view);}catch{/* private browser */}},[view]);
  useEffect(()=>{
    setScoreData(null);setScoreError("");if(!session||!pairKey)return;
    const controller=new AbortController();
    fetch(`/api/lab/sessions/${session.id}/score?candidates=${pair.map(c=>c.id).join(",")}`,{signal:controller.signal}).then(async r=>{const d=await r.json();if(!r.ok)throw new Error(d.detail??"Could not read the score");return d;}).then(setScoreData).catch(e=>{if(!controller.signal.aborted)setScoreError(String(e));});
    return ()=>controller.abort();
  },[session?.id,pairKey,scoreRetry]);
  useEffect(()=>{setLoopRange([0,session?.seconds??12]);},[session?.id,pairKey]);
  useEffect(()=>{const parts=selectedScore?.parts??[];if(parts.length&&!parts.some(p=>p.part===developPart))setDevelopPart(parts.find(p=>p.part==="melody")?.part??parts.find(p=>p.changes.length)?.part??parts[0].part);},[selectedScore?.id,!!selectedScore]);
  useEffect(()=>{
    if(!drawer){drawerWasOpen.current=false;returnFocus.current?.focus();return;}
    if(!drawerWasOpen.current)returnFocus.current=document.activeElement as HTMLElement;
    drawerWasOpen.current=true;
    const timer=window.setTimeout(()=>drawerRef.current?.querySelector<HTMLElement>("button")?.focus(),0);
    return ()=>clearTimeout(timer);
  },[drawer]);
  useEffect(()=>{const handler=(e:KeyboardEvent)=>keyboardRef.current?.(e);window.addEventListener("keydown",handler);return()=>window.removeEventListener("keydown",handler);},[]);

  async function run<T>(fn: () => Promise<T>) {setPending(true); setError(""); try {return await fn();} catch(e) {setError(String(e));} finally {setPending(false);}}
  async function scan(refresh = false) {
    setInventoryLoading(true); setInventoryError("");
    try {setInventory(await request<Inventory>(`/inventory${refresh?"?refresh=true":""}`));}
    catch(e) {setInventoryError(String(e));}
    finally {setInventoryLoading(false);}
  }
  async function listSessions() {
    setSessionsLoading(true);setSessionsError("");
    try {const r=await request<{sessions:SessionInfo[]}>("/sessions");setSessions(r.sessions);}
    catch(e) {setSessionsError(String(e));}
    finally {setSessionsLoading(false);}
  }
  useEffect(() => {
    void scan(); void listSessions();
    const saved=new URLSearchParams(location.search).get("comparison");
    if(saved) void loadSession(saved);
    let active=true;
    request<NonNullable<typeof provider>>("/provider").then(r=>{if(active)setProvider(r);}).catch(e=>{if(active)setProvider({available:false,detail:String(e)});});
    return ()=>{active=false;sessionRequest.current++;};
  }, []);
  useEffect(() => {
    if (!busy(session)) return;
    let active=true, timer=0;
    const poll=async()=>{try {const r=await request<Session>(`/sessions/${session!.id}`);if(active)setSession(prev=>prev?.id===r.id && r.updated>=prev.updated?r:prev);}catch(e){if(active)setError(String(e));}finally{if(active)timer=window.setTimeout(poll,1500);}};
    timer=window.setTimeout(poll,500);
    return () => {active=false;clearTimeout(timer);};
  }, [session?.id, session?.status]);
  useEffect(() => {if (available.length && !available.some(g=>g.use===selected)) select(available[0].use);}, [available, selected]);
  useEffect(() => {
    if (!session || !inventory || (session.scope??"instrument")!=="instrument") return;
    const o=inventory.occurrences.find(o=>o.path===session.path && o.part===session.part && o.piece===session.piece);
    const a=inventory.assessments[session.use];
    setSelected(session.use);setSearch("");setNeed(a?.need ?? 0);setNote(a?.note ?? "");
    setOccurrence(o ?? null);setStart(session.start);setSeconds(session.seconds);setBrief(session.brief);
    if((scope==="current" && session.path!==currentPath) || (o && ["study","example"].includes(o.kind)))setScope("all");
  }, [session?.id, !!inventory]);
  useEffect(() => {
    const [a,b] = players.current;
    const ended = () => {if (loopRef.current) {const p = players.current[sideRef.current]; p.currentTime=rangeRef.current[0]; p.play().catch(e => setError(String(e)));} else setPlaying(false);};
    const tick = () => setPosition(players.current[sideRef.current].currentTime || 0);
    a.addEventListener("ended", ended); b.addEventListener("ended", ended); a.addEventListener("timeupdate", tick); b.addEventListener("timeupdate", tick);
    return () => {for(const p of [a,b]) {p.pause(); p.removeEventListener("ended",ended); p.removeEventListener("timeupdate",tick);} };
  }, []);
  useEffect(()=>{
    if(!playing)return;
    let frame=0,last=0;
    const tick=(now:number)=>{const p=players.current[sideRef.current];if(now-last>35){if(loopRef.current&&p.currentTime>=rangeRef.current[1]-.015)p.currentTime=rangeRef.current[0];setPosition(p.currentTime||0);last=now;}frame=requestAnimationFrame(tick);};
    frame=requestAnimationFrame(tick);return()=>cancelAnimationFrame(frame);
  },[playing]);
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
  async function loadSession(id: string) {
    const seq=++sessionRequest.current;requestedSession.current=id;setSessionLoading(true);setSessionError("");
    setStatus("");setError("");
    try {
      const s=await request<Session>(`/sessions/${id}`);
      if(seq!==sessionRequest.current)return;
      players.current.forEach(p=>p.pause());setPlaying(false);
      setSession(s);setFeedback("");setMode(["arrangement","snippet"].includes(s.scope??"")?"context":"solo");setManualUse(s.candidates.find(c=>c.id===s.incumbent)?.change.use ?? s.use);setManualParams("{}");setPreview([]);setTargets([s.path]);linkSession(s.id);
      setTags([]);setDrawer(null);
    } catch(e) {if(seq===sessionRequest.current)setSessionError(String(e));}
    finally {if(seq===sessionRequest.current)setSessionLoading(false);}
  }
  async function create() {
    if (!occurrence) return;
    const s=await request<Session>("/sessions", {path: occurrence.path, part: occurrence.part, piece: occurrence.piece, start, seconds, brief});
    setSession(await request<Session>(`/sessions/${s.id}`));setMode("solo");setFeedback(""); setTargets([s.path]); setSessions(prev=>[s,...prev]); setManualUse(s.use); setManualParams("{}");
    linkSession(s.id);
    setDrawer(null);setSession(await request<Session>(`/sessions/${s.id}/render`,{}));
  }
  async function generate() {
    if(!session)return;
    const text=feedback;
    const draft=feedbackText?{event_id:crypto.randomUUID(),pair:session.pair,text:feedbackText,tags,mode,audition_range:loopRange}:undefined;
    await request<Session>(`/sessions/${session.id}/generate`, {feedback:draft});
    setSession(await request<Session>(`/sessions/${session.id}`));setFeedback(prev=>prev===text?"":prev);
    setTags([]);setDrawer(null);
  }
  async function createMusic(body:Record<string,unknown>) {
    await run(async()=>{
      if(dirty&&body.path===currentPath)throw new Error("Save your open score before comparing its saved source.");
      const s=await request<Session>("/sessions",body);await listSessions();await loadSession(s.id);
      setSession(await request<Session>(`/sessions/${s.id}/render`,{}));
    });
  }
  async function vote(choice: string) {
    if (!session) return;
    const text=feedback;
    const s=await request<Session>(`/sessions/${session.id}/feedback`, {event_id: crypto.randomUUID(), pair: session.pair, choice, text:feedbackText, tags, mode, audition_range:loopRange});
    setSession(await request<Session>(`/sessions/${s.id}`));setFeedback(prev=>prev===text?"":prev); setPreview([]);
    setTags([]);setStatus(choice==="comment"?"Feedback saved.":choice==="a"||choice==="b"?`Favorite saved: ${takeName(s.incumbent)}. Score files unchanged.`:"Listening choice saved.");
    if(auto && !snippets && choice !== "comment" && provider?.available) {await request(`/sessions/${s.id}/generate`, {});setSession(await request<Session>(`/sessions/${s.id}`));}
  }
  async function switchSide(i: number) {
    setSoundStopSignal(n=>n+1);
    if (!loadedPair) return;
    const old=players.current[sideRef.current], next=players.current[i];
    const wasPlaying=!old.paused, t=old.currentTime;
    old.pause();
    if (next.readyState < 1) await new Promise<void>((resolve,reject)=>{next.addEventListener("loadedmetadata",()=>resolve(),{once:true});next.addEventListener("error",()=>reject(new Error("Audio could not load")),{once:true});});
    next.currentTime=Math.min(t,Math.max(0,(next.duration || session!.seconds)-.01)); sideRef.current=i; setSide(i);
    if(wasPlaying) {await next.play(); setPlaying(true);} else setPlaying(false);
  }
  async function play() {setSoundStopSignal(n=>n+1);const p=players.current[sideRef.current]; if(p.paused) {if(p.ended||(loop&&(p.currentTime<loopRange[0]||p.currentTime>=loopRange[1])))p.currentTime=loopRange[0];await p.play();setPlaying(true);} else {p.pause();setPlaying(false);}}
  function seek(t:number){setSoundStopSignal(n=>n+1);const value=Math.max(0,Math.min(session?.seconds??0,t));players.current.forEach(p=>{if(p.readyState)p.currentTime=Math.min(value,p.duration||value);});setPosition(value);}
  async function develop(){
    if(!session||!favorite)return;
    const s=await request<Session>(`/sessions/${session.id}/develop`,{candidate:favorite.id,scope:developScope,part:developPart,brief:[session.brief,feedbackText].filter(Boolean).join("\n")});
    await listSessions();await loadSession(s.id);setSession(await request<Session>(`/sessions/${s.id}/generate`,{}));
  }
  keyboardRef.current=(e)=>{
    if(e.key==="Escape"&&drawer){e.preventDefault();setDrawer(null);return;}
    if(drawer){if(e.key==="Tab"){const items=[...drawerRef.current!.querySelectorAll<HTMLElement>("button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),summary,a[href]")].filter(el=>el.offsetParent!==null);const first=items[0],last=items[items.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}}return;}
    if(e.ctrlKey||e.metaKey||e.altKey||(e.target as HTMLElement)?.closest("input,textarea,select,[contenteditable=true]"))return;
    const key=e.key.toLowerCase();
    if(key===" "&&!(e.target as HTMLElement)?.closest("button,summary")){e.preventDefault();if(loadedPair)void run(play);}
    else if((key==="a"||key==="b")&&loadedPair){e.preventDefault();void run(()=>switchSide(key==="a"?0:1));}
    else if(key==="l"){e.preventDefault();setLoop(v=>!v);}
  };
  const matches = inventory?.occurrences.filter(o=>o.use===session?.use) ?? [];
  const targetPaths = [...new Set([...(session ? [session.path] : []), ...(!musical?matches.map(o=>o.path):[])])];
  const recentSessions = [...sessions].sort((a,b)=>Number(b.path===currentPath)-Number(a.path===currentPath) || b.updated-a.updated).slice(0,4);

  return <div className="instrument-lab listening-workspace">
    <div className="lab-shell" aria-hidden={drawer?true:undefined}>
      <aside className="lab-nav" aria-label="Comparison navigation">
        <button className="primary lab-new" onClick={()=>setDrawer("setup")}>＋ New comparison</button>
        <p className="lab-nav-label">SAVED COMPARISONS</p>
        {recentSessions.map(s=><button key={s.id} className={s.id===session?.id?"selected":""} onClick={()=>loadSession(s.id)}><b>{inventory?.sources.find(source=>source.path===s.path)?.title??s.path.split("/").pop()?.replace(/[_-]/g," ").replace(/\.sm$/,"")}</b><span>{comparisonNames[s.scope??"instrument"]} · {s.part}</span></button>)}
        {sessionsLoading&&<span className="small muted">Loading comparisons…</span>}
        <button className="ghost" onClick={()=>setDrawer("history")}>History &amp; saved takes</button>
        <button className="ghost" onClick={()=>{setComparisonType("instrument");setDrawer("setup");}}>Instrument library</button>
        <span className="lab-nav-foot small muted">Votes choose a favorite.<br/>Apply changes a saved score.</span>
      </aside>
      <main className="lab-workspace">
        <header className="lab-workspace-header">
          <div><span className="lab-eyebrow">AI LAB · {comparisonNames[sessionScope].toUpperCase()}</span><h2>{selectedScore?.title??(session?session.path.split("/").pop()?.replace(/\.sm$/,""):"A musical choice, one comparison at a time")}</h2>{session&&<span className="small muted">{session.seconds.toFixed(1)}-second excerpts · {selectedScore?.tuning??"saved score"}</span>}</div>
          <div className="lab-header-actions"><button className="lab-mobile-new" onClick={()=>setDrawer("setup")}>＋ New comparison</button><select aria-label="Saved comparisons" value={session?.id??""} onChange={e=>e.target.value&&loadSession(e.target.value)}><option value="">{sessionsLoading?"Loading saved comparisons…":"Saved comparisons…"}</option>{sessions.map(s=><option key={s.id} value={s.id}>{comparisonNames[s.scope??"instrument"]} · {s.path}</option>)}</select><button onClick={()=>setDrawer("history")}>Details</button></div>
        </header>
        {sessionsError&&<p className="lab-error" role="alert">{sessionsError} <button onClick={listSessions}>Retry saved comparisons</button></p>}
        {sessionLoading&&<p className="lab-loading" role="status">Opening saved comparison and audio…</p>}
        {sessionError&&<p className="lab-error" role="alert">{sessionError} <button onClick={()=>loadSession(requestedSession.current)}>Retry comparison</button></p>}
        {!session?<div className="lab-empty"><h3>Start with something you want to hear differently.</h3><p>Compare an instrument, a riff, an arrangement or two saved song passages.</p><button className="primary" onClick={()=>setDrawer("setup")}>New comparison</button><p className="small muted">Your saved comparisons open independently of the instrument inventory.</p></div>:<>
          <p className="lab-musical-question">{session.brief||scopeDescription(sessionScope,session.part)}</p>
          <section className="lab-transport" aria-label="Shared comparison transport">
            <div className="lab-transport-main"><button className="lab-play primary" disabled={!loadedPair} onClick={()=>run(play)}>{playing?"Pause":"Play"} {side===0?"A":"B"} · Take {selectedTake??1}</button><div className="lab-switch" aria-label="Audition take">{pair.map((c,i)=><button key={c.id} aria-pressed={side===i} disabled={!loadedPair} onClick={()=>run(()=>switchSide(i))}>{i===0?"A":"B"} · Take {c.take}</button>)}</div><input aria-label="Comparison position" type="range" min={0} max={session.seconds} step={.01} value={position} disabled={!loadedPair} onChange={e=>seek(+e.target.value)}/><output className="lab-clock">{position.toFixed(1)} / {session.seconds.toFixed(1)}s</output></div>
            <div className="lab-transport-options"><label>Listen to <select aria-label="Listening context" value={mode} onChange={e=>setMode(e.target.value)}>{canSolo&&<option value="solo">{session.audition?.solo_label??"Changed part"} — isolated</option>}<option value="context">Full mix — all instruments</option></select></label><label><input type="checkbox" checked={match} onChange={e=>setMatch(e.target.checked)}/> Match audition loudness</label><label><input type="checkbox" checked={loop} onChange={e=>setLoop(e.target.checked)}/> Loop</label><span className="lab-shortcuts muted small"><kbd>Space</kbd> play <kbd>A</kbd><kbd>B</kbd> switch <kbd>L</kbd> loop</span></div>
            {!!loopBars.length&&<details className="lab-loop-controls"><summary>Loop {loopRange[0].toFixed(1)}–{loopRange[1].toFixed(1)}s · drag bars to change</summary><BarRange bars={loopBars} duration={session.seconds} range={loopRange} position={position} label="Audition loop bar range" onChange={(a,b)=>{setLoopRange([loopBars[a].start,loopBars[b].end]);setLoop(true);}}/><div className="lab-loop-selects"><label>First bar<select aria-label="Loop first bar" value={firstLoopBar} onChange={e=>{const a=+e.target.value,b=Math.max(a,lastLoopBar);setLoopRange([loopBars[a].start,loopBars[b].end]);}}>{loopBars.map((b,i)=><option key={i} value={i}>{b.label}</option>)}</select></label><label>Last bar<select aria-label="Loop last bar" value={lastLoopBar} onChange={e=>{const b=+e.target.value,a=Math.min(firstLoopBar,b);setLoopRange([loopBars[a].start,loopBars[b].end]);}}>{loopBars.map((b,i)=><option key={i} value={i}>{b.label}</option>)}</select></label><button onClick={()=>setLoopRange([0,session.seconds])}>Whole excerpt</button></div></details>}
            <div className="lab-transport-status" aria-live="polite"><span>{busy(session)?`${session.status==="generating"?"Writing":session.status==="queued"?"Queued":"Rendering"} · ${session.candidates.length}/24 takes`:loadedPair?`${playing?"Playing":"Selected for audition"} ${side===0?"A":"B"} · Take ${selectedTake}`:"Original saved · add a challenger"}</span><span className="lab-favorite">Favorite: {favoriteSide>=0?`${favoriteSide===0?"A":"B"} · `:""}Take {favorite?.take??1}</span><span className={appliedFavorite?"ok":"muted"}>{appliedFavorite?"Applied to saved score":"Score files unchanged"}</span>{busy(session)&&<button onClick={()=>run(async()=>setSession(await request<Session>(`/sessions/${session.id}/stop`,{})))}>Stop job</button>}</div>
            {(error||session.error)&&<p role="alert" className="lab-error">{error||session.error}</p>}
            {status&&<p role="status" className="lab-inline-status">{status}</p>}
          </section>
          <div className="lab-view-heading"><div className="lab-view-switch" aria-label="Comparison view"><button aria-pressed={view==="listening"} onClick={()=>setView("listening")}>Listening room</button><button aria-pressed={view==="score"} onClick={()=>setView("score")}>Score focus</button></div><span className="small muted">{mode==="solo"?`${session.part} isolated`:"Full mix"} · {snippets?"each take keeps its own source window":"aligned score timing"}</span></div>
          {scoreError&&<p role="status" className="small muted">Notes could not load. Audio is still available. {scoreError} <button onClick={()=>setScoreRetry(v=>v+1)}>Retry notes</button></p>}
          {view==="listening"?<div className="lab-candidates">{pair.map((c,i)=>{const score=scoreData?.takes.find(t=>t.id===c.id),part=score?.parts.find(p=>p.part===session.part)??score?.parts.find(p=>p.changes.length)??score?.parts[0];const excerptStart=c.excerpt?.start??session.start;return <article key={c.id} className={side===i?"active":""} aria-label={`${i===0?"A":"B"} take ${c.take}`}><div className="lab-take-heading"><span className="lab-take-letter">{i===0?"A":"B"}</span><span className="small muted">Take {c.take}</span>{session.incumbent===c.id&&<span className="lab-favorite-badge">Favorite</span>}</div><h3>{c.display_name}</h3>{!musical&&<span className="small muted">{c.verified_use}</span>}{part&&<NoteRoll part={part} start={0} end={session.seconds} position={position} compact onSeek={seek}/>}<p className="small muted lab-excerpt">Source {excerptStart.toFixed(1)}–{(excerptStart+session.seconds).toFixed(1)}s</p><p className="lab-take-change small">{side===i?"Audition selected":"Ready to audition"}{part?` · ${part.part}`:""}</p>{i===1&&!snippets&&c.changes?.length>0&&<p className="small muted">{c.changes.map(ch=>`${ch.field}: ${String(ch.after)}`).join(" · ")}</p>}</article>;})}</div>:selectedScore?<LabScore take={selectedScore} position={position} onSeek={seek} focusPart={session.part}/>:<p className="lab-loading">{scoreError?"Listening controls remain available above.":"Reading performed notes…"}</p>}
          {!musical&&pair.length>0&&<SoundDesigner key={session.id} sessionId={session.id} pair={pair} selected={side} part={session.part+(session.piece?` / ${session.piece}`:"")} disabled={pending||busy(session)||session.candidates.length>=24} mainPlaying={playing} stopSignal={soundStopSignal} onPreview={setSoundAudition} loop={loop} range={loopRange} onAudition={()=>{players.current.forEach(p=>p.pause());setPlaying(false);setMode("solo");}} onBusy={setPending} onSaved={async()=>{const r=await request<Session>(`/sessions/${session.id}`);if(currentSessionId.current!==r.id)return;setSession(r);setStatus("Sound saved as a new take. Compare it, then vote or add feedback.");setPreview([]);}}/>}
          <section className="lab-feedback" aria-label="Listening decision">
            <div className="lab-feedback-heading"><h3>Which version works better?</h3><span className="small muted">A vote saves your favorite. Applying is separate.</span></div>
            <div className="lab-votes">{[["a","Prefer A"],["b","Prefer B"],["tie","Tie"],["neither","Neither"]].map(([choice,label])=><button key={choice} className={(choice==="a"&&favoriteSide===0)||(choice==="b"&&favoriteSide===1)?"favorite-choice":""} disabled={pending||busy(session)||!loadedPair||!!soundAudition} onClick={()=>run(()=>vote(choice))}>{label}</button>)}</div>
            <div className="lab-feedback-tags" aria-label="Quick feedback">{["Better phrasing","Too busy","Too bright","Better groove","Too loud"].map(tag=><button key={tag} aria-pressed={tags.includes(tag)} onClick={()=>setTags(prev=>prev.includes(tag)?prev.filter(t=>t!==tag):[...prev,tag])}>{tag}</button>)}</div>
            <textarea aria-label="Listening feedback" value={feedback} maxLength={4000} placeholder="What should the next version keep or change?" onChange={e=>setFeedback(e.target.value)}/>
            <div className="lab-next-actions"><button disabled={pending||busy(session)||!feedbackText} onClick={()=>run(()=>vote("comment"))}>Save comment</button><span className="spacer"/>{snippets?<><button className="primary" disabled={pending||busy(session)||!favorite} onClick={()=>setDrawer("revise")}>Develop favorite · Take {favorite?.take}</button><button onClick={()=>setDrawer("history")}>Compare another excerpt</button></>:<><button className="primary" disabled={pending||busy(session)||!provider?.available||session.candidates.length>=24} onClick={()=>setDrawer("revise")}>Revise favorite · Take {favorite?.take}</button><button disabled={pending||busy(session)||!provider?.available||session.candidates.length>=24} onClick={()=>run(generate)}>Try another</button><button disabled={pending||busy(session)} onClick={()=>{setPreview([]);setDrawer("apply");}}>Review &amp; apply</button></>}</div>
            {snippets&&<p className="small muted">Develop opens an editable riff or arrangement branch; the original listening comparison stays saved.</p>}
          </section>
          {!loadedPair&&!busy(session)&&<div className="lab-actions"><button disabled={pending} onClick={()=>run(async()=>setSession(await request<Session>(`/sessions/${session.id}/render`,{})))}>Render comparison</button><button onClick={()=>setDrawer("history")}>Add a manual challenger</button></div>}
        </>}
      </main>
    </div>
    {drawer&&<div className="lab-drawer-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)setDrawer(null);}}><aside className={`lab-drawer ${drawer==="apply"?"wide":""}`} role="dialog" aria-modal="true" aria-labelledby="lab-drawer-title" ref={drawerRef}><div className="lab-drawer-heading"><h2 id="lab-drawer-title">{drawer==="setup"?"New comparison":drawer==="apply"?"Review & apply":drawer==="revise"?"Develop the favorite":"Saved takes & details"}</h2><button aria-label="Close panel" onClick={()=>setDrawer(null)}>Close ✕</button></div>
      {error&&drawer!=="setup"&&drawer!=="revise"&&<p role="alert" className="lab-error">{error}</p>}
      {drawer==="setup"&&<>
    <section className="lab-library">
      <div className="lab-heading"><div><h3>Choose your musical question</h3></div><button disabled={inventoryLoading} onClick={()=>scan(true)}>{inventoryLoading?"Loading map…":"Refresh inventory"}</button></div>
      <label>Compare<select aria-label="Comparison type" value={comparisonType} onChange={e=>setComparisonType(e.target.value as ComparisonType)}>{Object.entries(comparisonNames).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
      {currentPath && <p className="small lab-current">Open song: <b>{currentPath}</b></p>}
      {inventory && <p className="small muted">{inventory.sources.length} saved scores · {new Set(inventory.occurrences.map(o=>o.use)).size} played voices. Map {inventory.cached?"saved":"scanned"} {new Date(inventory.scanned_at*1000).toLocaleString()}. Refresh after editing scores. Counts refer to source files. <a href="/api/lab/inventory.csv" download>Export song–instrument map (CSV)</a></p>}
      {inventoryLoading && <p role="status" className="lab-loading">{inventory?"Refreshing the instrument map. Keep comparing while it scans.":"Loading the instrument map. A first scan can take a little while; saved comparisons open separately."}</p>}
      {inventoryError && <div role="alert" className="lab-error">Instrument map could not load. {inventoryError}<br/><button onClick={()=>scan()}>Retry instrument map</button></div>}
      {error && <p role="alert" className="lab-error">{error}</p>}
      {status && <p role="status">{status}</p>}
      {comparisonType!=="instrument"&&<MusicComparisonForm type={comparisonType} sources={inventory?.sources??[]} occurrences={inventory?.occurrences??[]} currentPath={currentPath??session?.path??null} pending={pending} onCreate={createMusic} initial={session?{start:session.start,seconds:session.seconds,bPath:pair[1]?.excerpt?.path,bStart:pair[1]?.excerpt?.start}:undefined}/>}
      {comparisonType==="instrument"&&<>
      <div className="lab-filters">
        <input aria-label="Find instrument or song" placeholder="Find an instrument, song, or kit piece" value={search} onChange={e=>setSearch(e.target.value)}/>
        <select aria-label="Inventory scope" value={scope} onChange={e=>setScope(e.target.value)}>{currentPath&&<option value="current">Current song</option>}<option value="main">Songs + textbook</option><option value="song">Songs</option><option value="textbook">Textbook</option><option value="study">Studies + revisits</option><option value="example">Examples</option><option value="all">All saved scores</option></select>
        <select aria-label="Instrument order" value={order} onChange={e=>setOrder(e.target.value)}><option value="reach">Most used</option><option value="priority">Improvement priority</option></select>
      </div>
      {inventory && !available.length && <p className="small">{scope==="current"&&!search?"This song has no entries in the saved map yet. Refresh inventory after saving, or choose another scope.":"No instruments match these filters. Try another scope or search."}</p>}
      <div className="lab-list" role="region" aria-label="Instrument usage"><table><thead><tr><th>Played voice</th><th>Scores</th><th>Notes / hits</th><th>Need</th></tr></thead><tbody>{available.map(g=><tr key={g.use} className={g.use===selected?"selected":""}><td><button onClick={()=>select(g.use)}>{g.use}</button></td><td>{g.count}</td><td>{g.notes.toLocaleString()}</td><td>{["Unrated","Some","High","Highest"][inventory?.assessments[g.use]?.need ?? 0]}</td></tr>)}</tbody></table></div>
      {group && <div className="lab-focus">
        <h3>Original voice: {group.use}</h3>
        <label>Improvement need <select value={need} onChange={e=>setNeed(+e.target.value)}><option value={0}>Unrated / no extra priority</option><option value={1}>Some improvement</option><option value={2}>High need</option><option value={3}>Highest need</option></select></label>
        <textarea aria-label="Instrument improvement notes" placeholder="What needs work? These notes also go to the AI." value={note} maxLength={4000} onChange={e=>setNote(e.target.value)}/>
        <button disabled={pending} onClick={()=>run(async()=>{const a=await request<Assessment>("/assessment",{use:selected,need,note},"PUT");setInventory(prev=>prev?{...prev,assessments:{...prev.assessments,[selected]:a}}:prev);})}>Save priority and notes</button>
        <p className="small muted">Priority = score count × (1 + improvement need). Usage is measured; improvement need is your assessment.</p>
        <label>Song and part <select aria-label="Song and part" value={occurrence?`${occurrence.path}|${occurrence.part}|${occurrence.piece}`:""} onChange={e=>chooseOccurrence(group.occurrences.find(o=>`${o.path}|${o.part}|${o.piece}`===e.target.value) ?? null)}>{group.occurrences.map(o=><option key={`${o.path}|${o.part}|${o.piece}`} value={`${o.path}|${o.part}|${o.piece}`}>{titleOf(o)}</option>)}</select></label>
        <PassagePicker path={occurrence?.path??""} start={start} seconds={seconds} onChange={(a,b)=>{setStart(a);setSeconds(b);}} label="Instrument passage"/>
        <textarea aria-label="Comparison direction" value={brief} maxLength={4000} onChange={e=>setBrief(e.target.value)}/>
        <button className="primary" disabled={pending || !occurrence} onClick={()=>run(create)}>Start instrument comparison</button>
      </div>}
      </>}
      {!!inventory?.errors.length && <details><summary>{inventory.errors.length} scores could not be indexed</summary>{inventory.errors.map(e=><p key={e.path}><b>{e.path}</b><br/>{e.message}</p>)}</details>}
    </section>

      </>}
      {drawer==="history"&&<>
        {session?<><p><b>{session.path}</b><br/>{scopeDescription(sessionScope,session.part)}</p><p className="small muted">{session.candidates.length}/24 saved takes · {session.feedback.length} feedback entries</p>
        {!musical&&<details><summary>Manual challenger</summary><p className="small">Use a catalog voice and numeric parameters. Other writing stays fixed.</p><label>Voice<input value={manualUse} onChange={e=>setManualUse(e.target.value)} placeholder={session.use}/></label><label>Parameters (JSON)<textarea value={manualParams} onChange={e=>setManualParams(e.target.value)}/></label><button disabled={pending || busy(session)} onClick={()=>run(async()=>{setSession(await request<Session>(`/sessions/${session.id}/candidate`,{change:{use:manualUse||session.use,params:JSON.parse(manualParams)},label:"Manual challenger"}));})}>Add and render</button></details>}
        {musical&&<details><summary>{snippets?"Compare another saved excerpt":"Write a musical challenger"}</summary><label>Take label<input aria-label="Musical take label" value={manualLabel} onChange={e=>setManualLabel(e.target.value)}/></label>{snippets?<><label>Saved score<select aria-label="Challenger source" value={excerptPath} onChange={e=>setExcerptPath(e.target.value)}>{!(inventory?.sources??[]).some(s=>s.path===excerptPath)&&<option value={excerptPath}>{excerptPath}</option>}{inventory?.sources.map(s=><option key={s.path} value={s.path}>{s.title} · {s.path}</option>)}</select></label><label>Start (seconds)<input aria-label="Challenger start" type="number" min={0} step={.5} value={excerptStart} onChange={e=>setExcerptStart(+e.target.value)}/></label></>:<><p className="small">Edit the complete incumbent score below. {scopeDescription(sessionScope,session.part)}</p><textarea className="lab-score-editor" aria-label="Challenger score" value={manualSource} onChange={e=>setManualSource(e.target.value)}/></>}<button disabled={pending||busy(session)||session.candidates.length>=24} onClick={()=>run(async()=>setSession(await request<Session>(`/sessions/${session.id}/candidate`,{change:snippets?{path:excerptPath,start:excerptStart}:{source:manualSource},label:manualLabel})))}>Add and render musical challenger</button></details>}

        <details><summary>Feedback history ({session.feedback.length}) and takes ({session.candidates.length})</summary>{session.feedback.map(f=><p key={f.event_id}><b>{f.selected_take?`You picked Take ${f.selected_take} (${f.selected_voice}; then ${f.choice.toUpperCase()})`:f.choice.toUpperCase()}</b><br/>{f.mode==="context"?"Heard the full song":f.mode==="solo"?"Heard the isolated part":"Listening mode was not recorded"} · {f.text || "No comment"}</p>)}{session.candidates.map(c=><details key={c.id}><summary>Take {c.take} · {c.display_name} · {c.origin==="codex"?"AI proposal":c.origin==="source"?"Original score":"Manual edit"}</summary><pre>{JSON.stringify(c.change,null,2)}</pre>{canSolo&&<><a href={c.audio.focus ?? c.audio.solo} target="_blank" rel="noreferrer">Isolated {session.part} audio</a>{" · "}</>}<a href={c.audio.context} target="_blank" rel="noreferrer">Full song with accompaniment</a>{c.origin==="codex"&&<p className="small">AI proposal notes: {c.reason}</p>}</details>)}</details>

          <details><summary>Full source snapshots</summary>{session.candidates.map(c=><details key={c.id}><summary>Take {c.take} · {c.display_name}</summary><pre>{c.source}</pre></details>)}</details>
          <button disabled={pending||busy(session)} onClick={()=>run(async()=>setSession(await request<Session>(`/sessions/${session.id}/render`,{})))}>Render comparison</button>
          {!snippets&&<button onClick={()=>setDrawer("apply")}>Review &amp; apply favorite</button>}
        </>:<p className="muted">Open a saved comparison to see its takes and feedback.</p>}
        <p className="small muted">{!provider?"Checking AI connection…":provider.available?"AI uses your configured Codex CLI model and sign-in.":`AI is unavailable. Manual challengers remain available. ${provider.detail}`}</p>
      </>}
      {drawer==="revise"&&session&&<><p>Build from <b>Take {favorite?.take} · {favorite?.display_name}</b>.</p>{snippets&&<><label>Develop as<select aria-label="Develop comparison type" value={developScope} onChange={e=>setDevelopScope(e.target.value as "riff"|"arrangement")}><option value="riff">Riff — keep the backing</option><option value="arrangement">Arrangement — develop the ensemble</option></select></label>{developScope==="riff"&&<label>Part<select aria-label="Develop part" value={developPart} onChange={e=>setDevelopPart(e.target.value)}>{selectedScore?.parts.map(p=><option key={p.part}>{p.part}</option>)}</select></label>}</>}<label>What should change?<textarea aria-label="Revision direction" value={feedback} maxLength={4000} onChange={e=>setFeedback(e.target.value)} placeholder="Keep the momentum, soften the attacks, and leave more room after the arrival…"/></label><p className="small muted">Includes the original direction and saved feedback. Each request writes one challenger.</p><button className="primary" disabled={pending||busy(session)||!provider?.available||(!snippets&&session.candidates.length>=24)||(snippets&&developScope==="riff"&&!developPart)} onClick={()=>run(snippets?develop:generate)}>{snippets?"Create branch & generate":"Generate one revision"}</button>{!snippets&&<label className="small"><input type="checkbox" checked={auto} onChange={e=>setAuto(e.target.checked)}/> After each vote, generate the next challenger using all feedback</label>}{error&&<p role="alert" className="lab-error">{error}</p>}</>}
      {drawer==="apply"&&session&&<>
        {!snippets&&<details className="lab-apply" open><summary>Apply the current favorite to saved scores</summary><p>The vote chooses a favorite. Applying changes the selected score files, with saved preimages. Preview before applying.</p><div className="lab-targets">{targetPaths.map(p=><label key={p}><input type="checkbox" checked={targets.includes(p)} onChange={e=>{setTargets(prev=>e.target.checked?[...prev,p]:prev.filter(x=>x!==p));setPreview([]);}}/>{p}</label>)}</div><button disabled={pending || busy(session) || !targets.length} onClick={()=>run(async()=>{if(dirty && currentPath && targets.includes(currentPath))throw new Error("Save your open score before previewing an applied change.");const r=await request<{files:Preview[]}>(`/sessions/${session.id}/preview`,{candidate:session.incumbent,paths:targets});setPreview(r.files);})}>Preview selected changes</button>
          {preview.map(p=><details key={p.path}><summary>{p.path} · {p.targets.length} {musical?"musical edits":"voice edits"}</summary><div className="lab-diff"><pre>{p.before}</pre><pre>{p.text}</pre></div></details>)}
          {!!preview.length&&<button className="primary" disabled={pending || busy(session)} onClick={()=>run(async()=>{if(dirty && currentPath && targets.includes(currentPath))throw new Error("Save the open score first.");await request(`/sessions/${session.id}/apply`,{candidate:session.incumbent,paths:targets,expected:Object.fromEntries(preview.map(p=>[p.path,p.hash]))});setPreview([]);onApplied(targets);setSession(await request<Session>(`/sessions/${session.id}`));setStatus(`Applied favorite to ${targets.length} score(s).`);})}>Apply favorite to {preview.length} selected score(s)</button>}
        </details>}
        {session.applied.filter(r=>!r.restored).map(r=><p key={r.id}><button disabled={pending || busy(session)} onClick={()=>run(async()=>{const paths=r.files.map(f=>f.path);if(dirty && currentPath && paths.includes(currentPath)) throw new Error("Save the open score first.");await request(`/sessions/${session.id}/undo`,{receipt:r.id});onApplied(paths);setSession(await request<Session>(`/sessions/${session.id}`));})}>Undo applied changes to {r.files.length} score(s)</button></p>)}

      </>}
    </aside></div>}
  </div>;
}
