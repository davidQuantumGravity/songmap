import { useEffect, useRef, useState } from "react";
import "./harmony-library.css";

type Kind = "progressions" | "chords" | "transitions";
type Entry = { id:string; kind:Kind; name:string; family:string; mode:string; summary:string; description:string;
  symbols:string[]; bars:number[]; tuning:string; roman?:string; formula?:string; intervals?:number[];
  total_bars?:number; loop?:boolean; chord_ids?:string[]; progression_ids?:string[]; transition_ids?:string[];
  transition_links?:{id:string;position:number;loop_closure:boolean}[]; common_tones?:string[]; root_motion?:number;
  function?:string; catalog_uses?:number; provenance:string; source_ids:string[] };
type Source = {id:string;title:string;url?:string;path?:string;scope:string};
type Meta = {title:string;selection_note:string;counts:Record<Kind,number>;families:Record<Kind,string[]>;names:Record<Kind,Record<string,string>>;sources:Source[];tonics:string[]};
type Event = {symbol:string;start:number;duration:number;bars:number;pitches:number[];notes:string[]};
type Plan = {tonic:string;bpm:number;seconds:number;events:Event[];score:string;chord_line:string;preview_note:string};
type Detail = {entry:Entry;realization:Plan};
const labels:Record<Kind,string> = {progressions:"Progressions",chords:"Chords",transitions:"Transitions"};
const query = () => new URLSearchParams(location.search);
const initialKind = () => ["chords","transitions"].includes(query().get("database")??"") ? query().get("database") as Kind : "progressions";
const timeLabel = (t:number) => `${Math.floor(t/60)}:${Math.floor(t%60).toString().padStart(2,"0")}`;
async function get<T>(path:string, signal?:AbortSignal):Promise<T> {
  const r=await fetch(`/api/harmony${path}`,{signal}); const data=await r.json();
  if(!r.ok) throw new Error(typeof data.detail==="string"?data.detail:JSON.stringify(data.detail));
  return data;
}

export function HarmonyLibrary() {
  const [kind,setKind]=useState<Kind>(initialKind),[selected,setSelected]=useState(query().get("entry")??(initialKind()==="chords"?"major":initialKind()==="progressions"?"p001":""));
  const [tonic,setTonic]=useState(query().get("tonic")??"C"),[bpm,setBpm]=useState(100);
  const [meta,setMeta]=useState<Meta|null>(null),[items,setItems]=useState<Entry[]>([]),[detail,setDetail]=useState<Detail|null>(null);
  const [search,setSearch]=useState(""),[family,setFamily]=useState(""),[mode,setMode]=useState("");
  const [error,setError]=useState(""),[listError,setListError]=useState(""),[metaError,setMetaError]=useState("");
  const [loading,setLoading]=useState(true),[listLoading,setListLoading]=useState(true),[copied,setCopied]=useState("");
  const [playing,setPlaying]=useState(false),[time,setTime]=useState(0),[audioStatus,setAudioStatus]=useState("");
  const [trail,setTrail]=useState<{kind:Kind;id:string}[]>([]);
  const audio=useRef<HTMLAudioElement>(null),activeCard=useRef<HTMLButtonElement|null>(null);
  const activeEvent = detail?.realization.events.findIndex(e=>time>=e.start&&time<e.start+e.duration)??-1;

  useEffect(()=>{get<Meta>("/meta").then(setMeta).catch(e=>setMetaError(String(e)));},[]);
  useEffect(()=>{
    const c=new AbortController();setListLoading(true);setListError("");
    const timer=setTimeout(()=>get<{items:Entry[]}>(`/${kind}?${new URLSearchParams({q:search,family,mode})}`,c.signal)
      .then(r=>{setItems(r.items);setListLoading(false);}).catch(e=>{if(e.name!=="AbortError"){setListError(String(e));setListLoading(false);}}),150);
    return()=>{clearTimeout(timer);c.abort();};
  },[kind,search,family,mode]);
  useEffect(()=>{
    const c=new AbortController();audio.current?.pause();setPlaying(false);setTime(0);setAudioStatus("");
    setLoading(true);setError("");setDetail(null);setCopied("");
    if(!selected){setLoading(false);return()=>c.abort();}
    get<Detail>(`/${kind}/${encodeURIComponent(selected)}?${new URLSearchParams({tonic,bpm:String(bpm)})}`,c.signal)
      .then(r=>{setDetail(r);setLoading(false);}).catch(e=>{if(e.name!=="AbortError"){setError(String(e));setLoading(false);}});
    return()=>c.abort();
  },[kind,selected,tonic,bpm]);
  useEffect(()=>{
    const u=new URL(location.href);u.searchParams.set("harmony","1");u.searchParams.set("database",kind);
    u.searchParams.set("entry",selected);u.searchParams.set("tonic",tonic);history.replaceState(null,"",u);
  },[kind,selected,tonic]);
  useEffect(()=>{
    const a=audio.current;return()=>{a?.pause();};
  },[]);
  useEffect(()=>{
    if(playing) activeCard.current?.scrollIntoView({block:"nearest",inline:"nearest",behavior:"smooth"});
  },[activeEvent,playing]);
  function navigate(next:Kind,id:string,remember=true) {
    if(remember&&selected)setTrail(t=>[...t.slice(-15),{kind,id:selected}]);
    setKind(next);setSelected(id);setSearch("");setFamily("");setMode("");
  }
  function selectDatabase(next:Kind){
    const defaults:Record<Kind,string>={progressions:"p001",chords:"major",transitions:""};
    navigate(next,defaults[next]);
    if(next==="transitions")get<{items:Entry[]}>("/transitions?limit=1").then(r=>setSelected(r.items[0]?.id??"")).catch(e=>setError(String(e)));
  }
  async function play(){
    const a=audio.current;if(!a||!detail)return;
    if(!a.paused){a.pause();return;}
    if(a.ended)a.currentTime=0;
    setAudioStatus("Loading piano preview…");
    try{await a.play();setAudioStatus("");}catch(e){setAudioStatus(`Preview unavailable: ${String(e)}`);}
  }
  async function copy(text:string,label:string){
    try{await navigator.clipboard.writeText(text);setCopied(`${label} copied`);}catch{setCopied("Clipboard unavailable; select and copy the score below.");}
  }
  const item=detail?.entry,plan=detail?.realization;
  const sourceNames=(item?.source_ids??[]).map(id=>meta?.sources.find(s=>s.id===id)).filter((s):s is Source=>!!s);
  const link=(next:Kind,id:string,label?:string)=><button className="hl-text-link" key={`${next}-${id}`} onClick={()=>navigate(next,id)}>{label??`${next==="progressions"?id.toUpperCase()+" · ":""}${meta?.names[next]?.[id]??id.replace(/-/g," ")}`} <span aria-hidden>↗</span></button>;

  return <section className="harmony-library" aria-label="Harmony Library">
    <aside className="hl-browser">
      <div className="hl-brand"><span className="hl-emblem" aria-hidden>♮</span><div><span className="hl-eyebrow">THE COMPOSER’S REFERENCE</span><h1>Harmony Library</h1></div></div>
      <p className="hl-intro">Find a color. Hear the connection.<br/>Build the next phrase.</p>
      <nav className="hl-databases" aria-label="Harmony databases">{(["progressions","chords","transitions"] as Kind[]).map(k=><button key={k} className={kind===k?"active":""} aria-pressed={kind===k} onClick={()=>selectDatabase(k)}>{labels[k]}<b>{meta?.counts[k]??"…"}</b></button>)}</nav>
      <label className="hl-search"><span>Search {labels[kind].toLowerCase()}</span><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Try minor, ninth, plagal, ii7…" type="search"/></label>
      <div className="hl-filters"><label><span>Family</span><select value={family} onChange={e=>setFamily(e.target.value)}><option value="">All families</option>{meta?.families[kind].map(f=><option key={f}>{f}</option>)}</select></label>
        {kind!=="chords"&&<label><span>Context</span><select value={mode} onChange={e=>setMode(e.target.value)}><option value="">All modes</option>{["major","minor","dorian","mixolydian","phrygian","lydian",...(kind==="transitions"?["golden bridge"]:[])].map(m=><option key={m}>{m}</option>)}</select></label>}</div>
      <div className="hl-results-label" role="status">{listLoading?"Searching…":`${items.length} ${labels[kind].toLowerCase()}`}{(search||family||mode)&&<button className="ghost" onClick={()=>{setSearch("");setFamily("");setMode("");}}>Clear</button>}</div>
      {(listError||metaError)&&<p role="alert">{listError||metaError} <button onClick={()=>location.reload()}>Retry</button></p>}
      <div className="hl-results" aria-label={`${labels[kind]} results`} aria-busy={listLoading}>
        {!listLoading&&!items.length&&!listError&&<p className="hl-no-results">No matches. Try fewer words or clear a filter.</p>}
        {items.map((e,i)=><button className={`hl-result ${e.id===selected?"selected":""}`} key={e.id} onClick={()=>setSelected(e.id)} aria-current={e.id===selected?"true":undefined}>
          <span className="hl-result-number">{kind==="progressions"?e.id.slice(1):String(i+1).padStart(2,"0")}</span><span><b>{e.name}</b><span className="hl-result-symbols">{e.roman??e.symbols.join(" → ")}</span><small>{e.family}{e.mode?` · ${e.mode}`:""}</small></span>
        </button>)}
      </div>
      <a className="hl-export" href="/api/harmony/export" download>↓ Export all three databases <span>JSON</span></a>
    </aside>

    <main className="hl-main">
      <div className="hl-topline"><div>{trail.length>0&&<button className="ghost" onClick={()=>{const prev=trail[trail.length-1];setTrail(t=>t.slice(0,-1));navigate(prev.kind,prev.id,false);}}>← Back</button>}<span>{labels[kind]} <span className="muted">/ {selected.toUpperCase()}</span></span></div><span className="hl-curated">CURATED · 100 ESSENTIAL PROGRESSIONS</span></div>
      {loading&&<p role="status" className="hl-empty">Opening reference…</p>}
      {error&&<p role="alert" className="hl-empty">{error} <button onClick={()=>navigate("progressions","p001")}>Open first progression</button></p>}
      {!loading&&!selected&&<p className="hl-empty">Choose a reference from the list.</p>}
      {item&&plan&&<>
        <div className="hl-title"><div className="hl-tags"><span>{item.family}</span>{item.mode&&<span>{item.mode}</span>}<span>{item.tuning==="36edo"?"36-ET · golden":"12-ET"}</span>{item.total_bars&&<span>{item.total_bars} bars</span>}</div><h2>{item.name}</h2><p>{item.summary}</p></div>
        <section className="hl-listen" aria-label="Listen to harmony">
          <div className="hl-listen-controls"><button className="primary hl-play" onClick={play} disabled={loading}>{playing?"Ⅱ Pause":"▶ Listen"}</button><button aria-label="Stop preview" onClick={()=>{if(audio.current){audio.current.pause();audio.current.currentTime=0;}setTime(0);}}>■</button>
            <label>Tonic <select aria-label="Preview tonic" value={tonic} onChange={e=>setTonic(e.target.value)}>{(meta?.tonics??["C"]).map(t=><option key={t}>{t}</option>)}</select></label>
            <label>Tempo <select aria-label="Preview tempo" value={bpm} onChange={e=>setBpm(Number(e.target.value))}>{[60,80,100,120,140,160,180].map(t=><option key={t} value={t}>{t} bpm</option>)}</select></label><span className="hl-play-clock">{timeLabel(time)} <span>/ {timeLabel(plan.seconds)}</span></span><span className="hl-preview-voice">Soft stable piano</span>
          </div>
          <input className="hl-seek" aria-label="Preview position" type="range" min="0" max={plan.seconds} step=".05" value={Math.min(time,plan.seconds)} onChange={e=>{if(audio.current){audio.current.currentTime=Number(e.target.value);setTime(Number(e.target.value));}}}/>
          <div className="hl-chord-strip" aria-label="Chord and note sequence">{plan.events.map((event,i)=><button key={i} ref={i===activeEvent?activeCard:undefined} className={`hl-chord ${i===activeEvent?"sounding":""}`} onClick={()=>{if(audio.current){audio.current.currentTime=event.start;setTime(event.start);}}} title={`Seek to ${timeLabel(event.start)}`}>
            <span className="hl-chord-overline"><span>{item.roman?.split(" ")[i]??`0${i+1}`}</span><span>{event.bars} {event.bars===1?"bar":"bars"}</span></span><strong>{event.symbol}</strong><div className="hl-note-chips">{event.notes.map((n,j)=><span className={j===0?"bass":""} key={j}>{n}</span>)}</div><span className="hl-chord-meter"><i style={{width:`${i<activeEvent?100:i===activeEvent?Math.min(100,(time-event.start)/event.duration*100):0}%`}}/></span>
          </button>)}</div>
          <div className="hl-listen-foot"><span>{playing&&activeEvent>=0?`Now: ${plan.events[activeEvent].symbol} · ${plan.events[activeEvent].notes.join("  ")}`:"Individual played notes shown above · bass in amber"}</span><span>{item.loop?"Loopable form · preview plays once":"Single phrase"}</span></div>
          {audioStatus&&<p role="status">{audioStatus}</p>}
        </section>

        <div className="hl-reading-grid"><section className="hl-story"><span className="hl-eyebrow">HOW TO USE IT</span><h3>{item.function??(kind==="chords"?"Voice the color":"Make it a phrase")}</h3><p>{item.description}</p><small className="hl-reference-note">Analysis uses the C reference. The notes and copied score follow your selected tonic.</small>
          {item.formula&&<div className="hl-facts"><span>Formula <code>{item.formula}</code></span><span>Semitones <code>{item.intervals?.map(v=>Number(v.toFixed(4))).join(" · ")}</code></span></div>}
          {item.common_tones&&<div className="hl-facts"><span>Shared tones in C <b>{item.common_tones.join(" · ")||"None"}</b></span><span>Root motion <b>{item.root_motion!>0?"+":""}{item.root_motion} semitones</b></span><span>Appears in <b>{item.catalog_uses} catalog entries</b></span></div>}
          <details className="hl-sources"><summary>Sources & selection notes</summary><p>{meta?.selection_note}</p><p><b>This entry:</b> {item.provenance}.</p>{sourceNames.map(s=><div key={s.id}>{s.url?<a href={s.url} target="_blank" rel="noreferrer">{s.title} ↗</a>:<span>{s.title} · <code>{s.path}</code></span>}<p>{s.scope}</p></div>)}</details>
        </section><section className="hl-score"><span className="hl-eyebrow">TAKE IT INTO SONGMAP</span><h3>Keep it editable</h3><div className="hl-copy-buttons"><button onClick={()=>copy(plan.score,"Score")}>Copy .sm score</button><button className="ghost" onClick={()=>copy(plan.chord_line,"Chord line")}>Copy chord line</button></div><pre tabIndex={0} aria-label="Editable score example">{plan.score}</pre><p role="status" className="hl-copy-status">{copied||"Copy into a new score or your arrangement."}</p></section></div>

        {item.chord_ids&&<section className="hl-related"><span className="hl-eyebrow">CHORD VOCABULARY</span><div className="hl-related-chords">{Array.from(new Set(item.chord_ids)).map(id=>link("chords",id))}</div></section>}
        {item.transition_links&&<section className="hl-related"><span className="hl-eyebrow">EXPLORE THE CONNECTIONS</span><div className="hl-pair-links">{item.transition_links.map((t,i)=><button key={`${t.id}-${i}`} onClick={()=>navigate("transitions",t.id)}><b>{plan.events[t.position].symbol} <span>→</span> {plan.events[(t.position+1)%plan.events.length].symbol}</b><small>{t.loop_closure?"Loop return":"Chord pair"} ↗</small></button>)}</div></section>}
        {!!item.progression_ids?.length&&<section className="hl-related"><span className="hl-eyebrow">IN THESE PROGRESSIONS · {item.progression_ids.length}</span><div className="hl-related-chords">{item.progression_ids.map(id=>link("progressions",id))}</div></section>}
        {!!item.transition_ids?.length&&<details className="hl-related"><summary>Explore {item.transition_ids.length} connected transitions</summary><div className="hl-related-chords">{item.transition_ids.map(id=>link("transitions",id))}</div></details>}
      </>}
    </main>
    <audio ref={audio} src={detail?`/api/harmony/${kind}/${encodeURIComponent(selected)}/audio?tonic=${encodeURIComponent(tonic)}&bpm=${bpm}`:undefined} preload="none" onPlay={()=>setPlaying(true)} onPause={()=>setPlaying(false)} onEnded={()=>{setPlaying(false);setAudioStatus("Preview finished");}} onTimeUpdate={e=>setTime(e.currentTarget.currentTime)} onError={()=>setAudioStatus("Preview could not load. Try Listen again.")}/>
  </section>;
}
