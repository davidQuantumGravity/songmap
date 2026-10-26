import { useEffect, useRef, useState } from "react";

export function usePlotWidth(initial=600){
  const ref=useRef<SVGSVGElement|null>(null),[width,setWidth]=useState(initial);
  useEffect(()=>{const el=ref.current;if(!el)return;const resize=()=>setWidth(Math.max(1,el.getBoundingClientRect().width));resize();const observer=new ResizeObserver(resize);observer.observe(el);return()=>observer.disconnect();},[]);
  return {ref,width};
}

export type Bar = {index:number;label:string;section:string;start:number;end:number;beats:number};
export type SourceStructure = {title:string;tuning:string;seconds:number;music_seconds:number;bars:Bar[];sections:{name:string;first_bar:number;bars:number;start:number;end:number}[]};

export function PassagePicker({path,start,seconds,onChange,label="Passage"}:{path:string;start:number;seconds:number;onChange:(start:number,seconds:number)=>void;label?:string}) {
  const [data,setData]=useState<SourceStructure|null>(null),[error,setError]=useState("");
  const [retry,setRetry]=useState(0);
  useEffect(()=>{
    setData(null);setError("");if(!path)return;
    const controller=new AbortController();
    fetch(`/api/lab/source?path=${encodeURIComponent(path)}`,{signal:controller.signal}).then(async r=>{const d=await r.json();if(!r.ok)throw new Error(d.detail??"Could not read sections");return d;}).then(setData).catch(e=>{if(!controller.signal.aborted)setError(String(e));});
    return ()=>controller.abort();
  },[path,retry]);
  const first=data?.bars.findIndex(b=>b.end>start+1e-5)??0;
  const last=data?.bars.findIndex(b=>b.end>=start+seconds-1e-5)??0;
  function choose(a:number,b:number){
    if(!data?.bars.length)return;
    a=Math.max(0,Math.min(a,data.bars.length-1));b=Math.max(a,Math.min(b,data.bars.length-1));
    const begin=data.bars[a].start;
    while(b>a&&data.bars[b].end-begin>30+1e-5)b--;
    onChange(begin,Math.max(1,Math.min(30,data.bars[b].end-begin)));
  }
  return <fieldset className="lab-passage"><legend>{label}</legend>
    {data&&<>
      <label>Section<select aria-label={`${label} section`} value={data.sections.find(s=>s.start<=start+1e-5&&s.end>start)?.name??""} onChange={e=>{const s=data.sections.find(s=>s.name===e.target.value);if(s)choose(Math.floor(s.first_bar),Math.ceil(s.first_bar+s.bars)-1);}}><option value="">Custom passage</option>{data.sections.map(s=><option key={s.name} value={s.name}>{s.name} · bars {s.first_bar+1}–{s.first_bar+s.bars}</option>)}</select></label>
      <div className="lab-time"><label>First bar<select aria-label={`${label} first bar`} value={Math.max(0,first)} onChange={e=>choose(+e.target.value,Math.max(+e.target.value,last))}>{data.bars.map((b,i)=><option key={b.index} value={i}>{b.label}</option>)}</select></label><label>Last bar<select aria-label={`${label} last bar`} value={Math.max(0,last)} onChange={e=>choose(Math.min(first,+e.target.value),+e.target.value)}>{data.bars.map((b,i)=><option key={b.index} value={i}>{b.label}</option>)}</select></label></div>
      <BarRange bars={data.bars} duration={data.music_seconds} range={[start,start+seconds]} onChange={(a,b)=>choose(a,b)} label={`${label} bar range`}/>
    </>}
    {!data&&!error&&<p className="small muted">Reading sections…</p>}
    {error&&<p className="small lab-error">{error} <button onClick={()=>setRetry(v=>v+1)}>Retry sections</button></p>}
    <details><summary>Precise seconds · {start.toFixed(1)}–{(start+seconds).toFixed(1)}s</summary><div className="lab-time"><label>Start (seconds)<input aria-label={`${label} start seconds`} type="number" min={0} step={.1} value={start} onChange={e=>onChange(+e.target.value,seconds)}/></label><label>Length (seconds)<input aria-label={`${label} length seconds`} type="number" min={1} max={30} step={.1} value={seconds} onChange={e=>onChange(start,+e.target.value)}/></label></div></details>
    <p className="small muted">Up to 30 seconds per audition.</p>
  </fieldset>;
}

export function BarRange({bars,duration,range,onChange,label,position}:{bars:Bar[];duration:number;range:[number,number];onChange:(first:number,last:number)=>void;label:string;position?:number}) {
  const anchor=useRef<number|null>(null);
  const {ref,width}=usePlotWidth();
  const safeDuration=Math.max(.001,duration);
  const at=(event:React.PointerEvent<SVGSVGElement>)=>{
    const box=event.currentTarget.getBoundingClientRect();const t=Math.max(0,Math.min(safeDuration,(event.clientX-box.left)/box.width*safeDuration));
    const index=bars.findIndex(b=>b.end>t+1e-6);return index<0?Math.max(0,bars.length-1):index;
  };
  return <svg ref={ref} className="lab-bar-range" role="img" aria-label={label} viewBox={`0 0 ${width} 46`} preserveAspectRatio="none"
    onPointerDown={e=>{if(!bars.length)return;e.preventDefault();anchor.current=at(e);e.currentTarget.setPointerCapture(e.pointerId);onChange(anchor.current,anchor.current);}}
    onPointerMove={e=>{if(anchor.current!==null){const b=at(e);onChange(Math.min(anchor.current,b),Math.max(anchor.current,b));}}}
    onPointerUp={e=>{anchor.current=null;if(e.currentTarget.hasPointerCapture(e.pointerId))e.currentTarget.releasePointerCapture(e.pointerId);}}
    onPointerCancel={()=>{anchor.current=null;}}>
    {bars.map((b,i)=>{const x=Math.max(0,b.start/safeDuration*width),w=(b.end-b.start)/safeDuration*width;return <g key={b.index}><rect x={x+1} y={2} width={Math.max(1,w-2)} height={30} className={b.end>range[0]+1e-5&&b.start<range[1]-1e-5?"selected":""}/>{i%Math.max(1,Math.ceil(bars.length/(width/24)))===0&&<text x={x+w/2} y={22} textAnchor="middle">{b.index+1}</text>}</g>;})}
    {position!==undefined&&<line className="loop-playhead" x1={position/safeDuration*width} x2={position/safeDuration*width} y1={0} y2={37}/>}
  </svg>;
}
