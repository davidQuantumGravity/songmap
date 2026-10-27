import { useEffect, useRef, useState } from "react";
import type { Catalog, Summary, Voice } from "./api";
import "./expression.css";

type Point=[number,number];
const names:Record<string,string>={volume:"Performance volume",brightness:"Brightness",body:"Body",vibrato_depth:"Added vibrato depth",vibrato_rate:"Vibrato speed",pitch_cents:"Pitch bend",stereo_width:"Stereo width",blend:"Source balance",morph_x:"Morph X",morph_y:"Morph Y"};

export function ExpressionEditor({summary,catalog,part,voice,time,onApply}:{summary:Summary;catalog:Catalog|null;part:string;voice:Voice;time:number;onApply:(op:string,args:object)=>Promise<void>}) {
  const [index,setIndex]=useState(()=>summary.sections.findIndex(s=>time>=s.start&&time<s.end));
  const [control,setControl]=useState("volume"),[points,setPoints]=useState<Point[]>([]),[tech,setTech]=useState<[number,string][]>([]);
  const [busy,setBusy]=useState(false),[error,setError]=useState(""),[message,setMessage]=useState("");
  const dragging=useRef<number|null>(null);
  const sec=summary.sections[Math.max(0,index)]??summary.sections[0],length=sec.end_beat-sec.start_beat;
  const controls=(catalog?.expression_controls??[]).filter(q=>q.group!=="mix"||voice.schema?.some(s=>s.name===q.name));
  const spec=controls.find(q=>q.name===control)??controls[0];
  const neutral=spec?.group==="mix"?Number(voice.values[control]??spec.default):spec?.default??0;
  const source=JSON.stringify([summary.expression,summary.techniques,part,sec.name,control]);
  useEffect(()=>{
    if(!spec)return;
    const raw=summary.expression?.[sec.name]?.[part]?.[control];
    const earlier=summary.sections.filter(s=>s.start<sec.start).reverse().find(s=>summary.expression?.[s.name]?.[part]?.[control]!==undefined);
    const previous=earlier?summary.expression?.[earlier.name]?.[part]?.[control]:undefined;
    const inherited=Array.isArray(previous)?previous[previous.length-1][1]:typeof previous==="number"?previous:neutral;
    setPoints(Array.isArray(raw)?raw.map(p=>[...p] as Point):[[0,typeof raw==="number"?raw:inherited],[length,typeof raw==="number"?raw:inherited]]);
    setTech((summary.techniques?.[sec.name]?.[part]??[]).map(p=>[...p]));setError("");setMessage("");
  },[source,spec?.name,neutral,length]); // eslint-disable-line react-hooks/exhaustive-deps
  if(!spec)return <p>Loading expression controls…</p>;
  const x=(b:number)=>34+b/length*692,y=(v:number)=>180-(v-spec.lo)/(spec.hi-spec.lo)*150;
  function position(e:React.PointerEvent<SVGSVGElement>):Point {const r=e.currentTarget.getBoundingClientRect();return [Number(Math.max(0,Math.min(length,((e.clientX-r.left)/r.width*760-34)/692*length)).toFixed(3)),Number(Math.max(spec.lo,Math.min(spec.hi,spec.lo+(180-(e.clientY-r.top)/r.height*220)/150*(spec.hi-spec.lo))).toFixed(3))];}
  function down(e:React.PointerEvent<SVGSVGElement>){if(busy)return;e.currentTarget.setPointerCapture(e.pointerId);const p=position(e);const target=e.target as SVGElement;const selected=target.dataset.point;
    if(selected!==undefined)dragging.current=Number(selected);else{const next=[...points,p].sort((a,b)=>a[0]-b[0]);if(p[0]>.001&&p[0]<length-.001&&!points.some(q=>Math.abs(q[0]-p[0])<.001)){dragging.current=next.indexOf(p);setPoints(next);}}
  }
  function move(e:React.PointerEvent<SVGSVGElement>){const i=dragging.current;if(i===null||busy)return;const p=position(e);setPoints(prev=>prev.map((q,j)=>j===i?[i===0?0:i===prev.length-1?length:Math.max(prev[i-1][0]+.001,Math.min(prev[i+1][0]-.001,p[0])),p[1]]:q));}
  async function apply(op:string,args:object){setBusy(true);setError("");setMessage("");try{await onApply(op,{index:sec.index,part,...args});setMessage("Applied to the score. Render to hear it; Save to keep it.");}catch(e){setError(String(e));}finally{setBusy(false);}}
  return <div className="expression-editor" aria-label="Performance expression editor">
    <h3>Expression & techniques</h3><p>Shape held notes continuously. Click to add a point, drag to move it, or enter exact values below. Positions are quarter-note beats from the section start.</p>
    <div className="expression-fields"><label>Section<select aria-label="Expression section" value={sec.index} disabled={busy} onChange={e=>setIndex(+e.target.value)}>{summary.sections.map(s=><option key={s.index} value={s.index}>{s.name}</option>)}</select></label><label>Control<select aria-label="Expression control" value={control} disabled={busy} onChange={e=>setControl(e.target.value)}>{controls.map(q=><option key={q.name} value={q.name}>{names[q.name]??q.name}</option>)}</select></label></div>
    <p className="small muted">{spec.doc}. Final values hold until another curve changes them. Recorded vibrato and written note velocities remain present.</p>
    <svg className="expression-curve" role="img" aria-label="Expression curve editor" viewBox="0 0 760 220" onPointerDown={down} onPointerMove={move} onPointerUp={()=>dragging.current=null} onPointerCancel={()=>dragging.current=null}>
      {[0,.25,.5,.75,1].map(v=><g key={v}><line x1={34} x2={726} y1={30+v*150} y2={30+v*150}/><text x={4} y={34+v*150}>{(spec.hi-v*(spec.hi-spec.lo)).toFixed(2)}</text><text x={34+v*692} y={208}>{(v*length).toFixed(1)} b</text></g>)}
      <polyline points={points.map(p=>`${x(p[0])},${y(p[1])}`).join(" ")}/>{points.map((p,i)=><circle key={i} data-point={i} cx={x(p[0])} cy={y(p[1])} r={6}><title>Beat {p[0].toFixed(2)}: {p[1].toFixed(2)}</title></circle>)}
    </svg>
    <div className="expression-points">{points.map((p,i)=><div key={i}><label>Beat<input aria-label={`Point ${i+1} beat`} type="number" min={0} max={length} step="any" value={p[0]} disabled={busy||i===0||i===points.length-1} onChange={e=>setPoints(prev=>prev.map((q,j)=>j===i?[+e.target.value,q[1]]:q))}/></label><label>Value {spec.unit}<input aria-label={`Point ${i+1} value`} type="number" min={spec.lo} max={spec.hi} step="any" value={p[1]} disabled={busy} onChange={e=>setPoints(prev=>prev.map((q,j)=>j===i?[q[0],+e.target.value]:q))}/></label>{i>0&&i<points.length-1&&<button disabled={busy} onClick={()=>setPoints(prev=>prev.filter((_,j)=>j!==i))}>Remove</button>}</div>)}</div>
    <div className="expression-actions"><button disabled={busy} onClick={()=>setPoints([[0,control==="volume"?.25:neutral],[length/2,control==="volume"?1:Math.min(spec.hi,neutral+(spec.hi-spec.lo)*.25)],[length,control==="volume"?.25:neutral]])}>Swell shape</button><button disabled={busy} onClick={()=>setPoints([[0,neutral],[length,neutral]])}>Neutral shape</button><button className="primary" disabled={busy} onClick={()=>apply("expression",{control,points})}>Apply expression curve</button><button disabled={busy} onClick={()=>apply("expression",{control,points:null})}>Remove lane</button></div>
    {!!voice.techniques?.length&&<div className="expression-techniques"><h4>Recorded technique changes</h4><p className="small muted">Changes affect notes starting at or after the selected beat. Held notes finish their original technique. Auto follows the written articulation when a matching recording exists.</p>{tech.map((p,i)=><div className="expression-fields" key={i}><label>Beat<input aria-label={`Technique ${i+1} beat`} type="number" min={0} max={length-.001} step="any" value={p[0]} disabled={busy} onChange={e=>setTech(prev=>prev.map((q,j)=>j===i?[+e.target.value,q[1]]:q))}/></label><label>Technique<select aria-label={`Technique ${i+1} name`} value={p[1]} disabled={busy} onChange={e=>setTech(prev=>prev.map((q,j)=>j===i?[q[0],e.target.value]:q))}><option value="auto">Auto</option>{voice.techniques!.map(t=><option key={t.name} value={t.name}>{t.name}</option>)}</select></label><button disabled={busy} onClick={()=>setTech(prev=>prev.filter((_,j)=>j!==i))}>Remove</button></div>)}<div className="expression-actions"><button disabled={busy||(tech.length>0&&tech[tech.length-1][0]>=length-1)} onClick={()=>setTech(prev=>[...prev,[prev.length?prev[prev.length-1][0]+1:0,"auto"]])}>Add technique change</button><button className="primary" disabled={busy} onClick={()=>apply("techniques",{techniques:tech})}>Apply technique changes</button></div></div>}
    {error&&<p role="alert" className="warn-text">{error}</p>}{message&&<p role="status">{message}</p>}
  </div>;
}
