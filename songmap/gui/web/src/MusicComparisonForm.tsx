import { useEffect, useState } from "react";
import { PassagePicker } from "./PassagePicker";

export type ComparisonType = "instrument" | "riff" | "arrangement" | "snippet";
type Source = {path:string;title:string;seconds:number};
type Occurrence = {path:string;part:string;piece:string|null};
export const comparisonNames = {instrument:"Instrument", riff:"Riff", arrangement:"Arrangement", snippet:"Song snippet"};
export const scopeDescription = (scope:ComparisonType, part:string) => scope === "riff"
  ? `Edit ${part}'s notes and expression across the score; backing and instrument sounds stay fixed. The window is an audition of that change.`
  : scope === "arrangement" ? "Edit parts, orchestration, harmony and mix across the score. Section timing stays aligned; the window is an audition of the full change."
  : scope === "snippet" ? "Compare saved excerpts from any two places or songs. Each side has its own start time. This is a listening comparison."
  : `Edit instrument sound for ${part}. Notes and expression stay fixed.`;

export function MusicComparisonForm({type,sources,occurrences,currentPath,pending,onCreate,initial}: {
  type:ComparisonType;sources:Source[];occurrences:Occurrence[];currentPath:string|null;pending:boolean;
  onCreate:(body:Record<string,unknown>)=>Promise<unknown>;
  initial?:{start:number;seconds:number;bPath?:string;bStart?:number};
}) {
  const [path,setPath]=useState(currentPath??""), [bPath,setBPath]=useState(initial?.bPath??currentPath??"");
  const [part,setPart]=useState("");
  const [start,setStart]=useState(initial?.start??0), [bStart,setBStart]=useState(initial?.bStart??0), [seconds,setSeconds]=useState(initial?.seconds??12);
  const [brief,setBrief]=useState("");
  const parts=[...new Set(occurrences.filter(o=>o.path===path).map(o=>o.part))];
  useEffect(()=>{if(!path&&sources.length)setPath(sources[0].path);if(!bPath&&sources.length)setBPath(sources[0].path);},[sources,path,bPath]);
  useEffect(()=>{if(!parts.includes(part))setPart(parts[0]??"");},[path,parts.join("|")]);
  const sourceSelect=(label:string,value:string,change:(p:string)=>void)=><label>{label}<select aria-label={label} value={value} onChange={e=>change(e.target.value)}>{!sources.some(s=>s.path===value)&&value&&<option value={value}>{value}</option>}{sources.map(s=><option key={s.path} value={s.path}>{s.title} · {s.path}</option>)}</select></label>;
  return <div className="lab-focus lab-music-form">
    <h3>New {comparisonNames[type].toLowerCase()} comparison</h3>
    <p className="small">{scopeDescription(type,part||"the selected part")}</p>
    {sourceSelect(type==="snippet"?"A source score":"Source score",path,setPath)}
    {type==="riff"&&<label>Riff part<select aria-label="Riff part" value={part} onChange={e=>setPart(e.target.value)}>{parts.map(p=><option key={p}>{p}</option>)}</select></label>}
    <PassagePicker path={path} start={start} seconds={seconds} onChange={(a,b)=>{setStart(a);setSeconds(b);}} label={type==="snippet"?"A passage":"Audition passage"}/>
    {type==="snippet"&&<>{sourceSelect("B source score",bPath,setBPath)}<PassagePicker path={bPath} start={bStart} seconds={seconds} onChange={(a,b)=>{setBStart(a);setSeconds(b);}} label="B passage"/><p className="small muted">Both sides use the same {seconds.toFixed(1)}-second audition length.</p></>}
    <label>Musical direction<textarea aria-label="Musical direction" value={brief} maxLength={4000} placeholder="What are we comparing or improving? What should stay?" onChange={e=>setBrief(e.target.value)}/></label>
    <p className="small muted">Uses saved scores. Save any editor changes first.</p>
    <button className="primary" disabled={pending||!path||(type==="riff"&&!part)||(type==="snippet"&&!bPath)} onClick={()=>onCreate({scope:type,path,part,start,seconds,brief,...(type==="snippet"?{comparison:{path:bPath,start:bStart,label:"B excerpt"}}:{})})}>Start {comparisonNames[type].toLowerCase()} comparison</button>
  </div>;
}
