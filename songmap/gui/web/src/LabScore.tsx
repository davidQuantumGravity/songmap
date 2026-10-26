import { useMemo } from "react";
import { usePlotWidth, type Bar } from "./PassagePicker";

export type ScoreNote={start:number;end:number;pitch:number|null;label:string;hz:number|null;micro:boolean;velocity:number;piece:string|null};
export type ScorePart={part:string;voice:string;uses:string[];kit:boolean;notes:ScoreNote[];changes:string[]};
export type TakeScore={id:string;title:string;tuning:string;seconds:number;start:number;parts:ScorePart[];bars:Bar[];chords:{start:number;end:number;symbol:string}[]};
export type ComparisonScore={takes:TakeScore[];changes:Record<string,string[]>};

export function NoteRoll({part,start,end,position,compact=false,onSeek}:{part:ScorePart;start:number;end:number;position:number;compact?:boolean;onSeek?:(time:number)=>void}) {
  const notes=part.notes.filter(n=>n.end>start&&n.start<end);
  const {ref,width}=usePlotWidth();
  const pitches=notes.map(n=>n.pitch).filter((p):p is number=>p!==null);
  const pieces=[...new Set(notes.map(n=>n.piece??part.part))];
  const lo=(pitches.length?Math.min(...pitches):60)-1,hi=(pitches.length?Math.max(...pitches):72)+1;
  const height=compact?76:104,duration=Math.max(.01,end-start);
  const y=(n:ScoreNote)=>n.pitch===null?10+pieces.indexOf(n.piece??part.part)*Math.min(14,(height-18)/pieces.length):8+(hi-n.pitch)/(hi-lo)*(height-26);
  return <svg ref={ref} className={`lab-note-roll${compact?" compact":""}`} role="img" aria-label={`${part.part} performed notes`} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" onClick={e=>{if(onSeek){const box=e.currentTarget.getBoundingClientRect();onSeek(start+(e.clientX-box.left)/box.width*duration);}}}>
    {[0,1,2,3,4].map(i=><line key={i} x1={width*i/4} x2={width*i/4} y1={0} y2={height}/>)}
    {notes.map((n,i)=>{const active=n.start<=position&&n.end>position;const x=Math.max(0,(n.start-start)/duration*width),w=(Math.min(end,n.end)-Math.max(start,n.start))/duration*width;return <g key={i} className={`${active?"sounding":""} ${n.micro?"micro":""}`}><rect x={x+1} y={y(n)} width={Math.max(3,w-2)} height={compact?9:12} rx={2}/><title>{n.label}{n.hz?` · ${n.hz.toFixed(2)} Hz`:""} · {n.start.toFixed(2)}–{n.end.toFixed(2)}s</title>{!compact&&w>33&&<text x={x+5} y={y(n)+9}>{n.label}</text>}</g>;})}
    {position>=start&&position<=end&&<line className="note-playhead" x1={(position-start)/duration*width} x2={(position-start)/duration*width} y1={0} y2={height}/>}
  </svg>;
}

export function LabScore({take,position,onSeek,focusPart}:{take:TakeScore;position:number;onSeek:(time:number)=>void;focusPart?:string}) {
  const bar=take.bars.find(b=>b.start<=position+1e-5&&b.end>position);
  const start=bar?.start??take.bars[take.bars.length-1]?.end??0,end=bar?.end??take.seconds;
  const parts=useMemo(()=>[...take.parts].sort((a,b)=>Number(b.part===focusPart)-Number(a.part===focusPart)||Number(!!b.changes.length)-Number(!!a.changes.length)),[take,focusPart]);
  return <section className="lab-score-view" aria-label="Instrument score lanes">
    <div className="lab-score-heading"><b>{bar?`${bar.label} · ${bar.section}`:"Release tail"}</b><span className="small muted">{take.tuning} · click notes to seek</span></div>
    <div className="lab-chord-line">{take.chords.filter(c=>c.end>start&&c.start<end).map((c,i)=><span key={i}>{c.symbol}</span>)}</div>
    {parts.map(part=>{const sounding=part.notes.filter(n=>n.start<=position&&n.end>position);return <div key={part.part} className={`lab-score-lane ${part.changes.length?"changed":"unchanged"}`}>
      <div className="lab-lane-name"><b>{part.part}</b><span className="small muted">{part.voice}</span><span className="lab-change-label">{part.changes.length?part.changes.join(" · "):"Notes / sound unchanged"}</span></div>
      <NoteRoll part={part} start={start} end={end} position={position} onSeek={onSeek}/>
      <div className="lab-active-notes" aria-label={`${part.part} active notes`}>{sounding.length?[...new Set(sounding.map(n=>n.label))].join(" · "):"—"}</div>
    </div>;})}
    {!parts.length&&<p className="small muted">No performed notes in this passage.</p>}
  </section>;
}
