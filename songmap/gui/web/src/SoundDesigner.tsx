import { useEffect, useRef, useState } from "react";

type Take = {id:string; take:number; audio:Record<string,string>; loudness:Record<string,number>};
type Tone = Record<string,number>;
export type SoundRecipe = {base?:string; pair?:string[]; amount?:number; tone:Tone};
type Control = {name:string;lo:number;hi:number;default:number;doc:string};
const labels:Record<string,string>={tone_brightness:"Brightness",tone_body:"Body",tone_attack:"Attack",tone_tightness:"Tightness",tone_grit:"Grit",tone_width:"Stereo width",tone_vibrato:"Added vibrato",morph_x:"Morph X · A/C ↔ B/D",morph_y:"Morph Y · A/B ↔ C/D",blend:"Source A ↔ B"};

async function api<T>(url:string, recipe?:SoundRecipe):Promise<T> {
  const r=await fetch(url,recipe?{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(recipe)}:undefined);
  const d=await r.json();if(!r.ok)throw new Error(d.detail??"Could not update this sound");return d;
}

export function SoundDesigner({sessionId,pair,selected,part,disabled,mainPlaying,stopSignal,loop,range,onAudition,onSaved,onBusy,onPreview}:{
  sessionId:string;pair:Take[];selected:number;part:string;disabled:boolean;mainPlaying:boolean;
  loop:boolean;range:[number,number];onAudition:()=>void;onSaved:()=>Promise<void>;onBusy:(busy:boolean)=>void;
  stopSignal:number;onPreview:(kind:"shape"|"blend"|null)=>void;
}) {
  const [panel,setPanel]=useState<"shape"|"blend"|null>(null);
  const [tone,setTone]=useState<Tone>({});
  const [original,setOriginal]=useState<Tone>({});
  const [ready,setReady]=useState(false);
  const [knobs,setKnobs]=useState<Control[]>([]);
  const [amount,setAmount]=useState(.5);
  const [error,setError]=useState("");
  const [operation,setOperation]=useState<"shape"|"blend"|"save"|null>(null);
  const [retry,setRetry]=useState(0);
  const [previewing,setPreviewing]=useState<"shape"|"blend"|null>(null);
  const [previewUrl,setPreviewUrl]=useState("");
  const [previewDirty,setPreviewDirty]=useState(false);
  const previewAudio=useRef<HTMLAudioElement|null>(null);
  const graph=useRef<{ctx:AudioContext;sources:AudioBufferSourceNode[];gains:GainNode[];output:GainNode}|null>(null);
  const sequence=useRef(0),alive=useRef(true),amountRef=useRef(amount);
  amountRef.current=amount;
  const take=pair[selected],pairKey=pair.map(c=>c.id).join(":");
  const endpoint=`/api/lab/sessions/${sessionId}/design`;

  function stop() {
    sequence.current++;
    previewAudio.current?.pause();
    if(graph.current){const g=graph.current;graph.current=null;g.output.gain.setTargetAtTime(0,g.ctx.currentTime,.003);g.sources.forEach(s=>{try{s.stop(g.ctx.currentTime+.02);}catch{/* already ended */}});window.setTimeout(()=>{if(g.ctx.state!=="closed")void g.ctx.close();},35);}
    if(alive.current)setPreviewing(null);
  }
  useEffect(()=>()=>{alive.current=false;stop();onPreview(null);},[]);
  useEffect(()=>{onPreview(previewing);},[previewing]);
  useEffect(()=>{stop();},[stopSignal]);
  useEffect(()=>{stop();setPreviewUrl("");setPreviewDirty(false);setError("");setAmount(.5);},[pairKey,selected]);
  useEffect(()=>{if(mainPlaying)stop();},[mainPlaying]);
  useEffect(()=>{stop();},[loop,range[0],range[1]]);
  useEffect(()=>{
    setReady(false);if(!take)return;
    let active=true;
    api<{values:Tone;params:Control[]}>(`${endpoint}?candidate=${take.id}`).then(d=>{if(active){setKnobs(d.params);setOriginal(d.values);setTone(d.values);setReady(true);}}).catch(e=>{if(active)setError(String(e));});
    return()=>{active=false;};
  },[sessionId,take?.id,retry]);
  useEffect(()=>{
    const g=graph.current;if(!g)return;
    [1-amount,amount].forEach((v,i)=>{g.gains[i].gain.setTargetAtTime(v,g.ctx.currentTime,.015);});
  },[amount]);

  async function playBlend() {
    if(previewing==="blend"){stop();return;}
    stop();onAudition();setOperation("blend");setError("");const seq=sequence.current;
    const ctx=new AudioContext();
    try {
      await ctx.resume();
      const buffers=await Promise.all(pair.map(async c=>{
        const r=await fetch(c.audio.solo);if(!r.ok)throw new Error("Source audio could not load");
        return ctx.decodeAudioData(await r.arrayBuffer());
      }));
      if(!alive.current||seq!==sequence.current){await ctx.close();return;}
      let peak=0;
      for(const b of buffers)for(let channel=0;channel<b.numberOfChannels;channel++){const data=b.getChannelData(channel);for(let i=0;i<data.length;i++)peak=Math.max(peak,Math.abs(data[i]));}
      const level=Math.max(...pair.map(c=>c.loudness.solo??-20));
      const output=ctx.createGain();output.gain.value=Math.min(10**((-20-level)/20),.94/(peak||1));output.connect(ctx.destination);
      const gains=buffers.map((_,i)=>{const g=ctx.createGain();g.gain.value=i?amountRef.current:1-amountRef.current;g.connect(output);return g;});
      const end=Math.min(range[1],...buffers.map(b=>b.duration)),start=Math.min(range[0],Math.max(0,end-.02));
      const sources=buffers.map((buffer,i)=>{const s=ctx.createBufferSource();s.buffer=buffer;s.loop=loop;s.loopStart=start;s.loopEnd=end;s.connect(gains[i]);return s;});
      graph.current={ctx,sources,gains,output};
      const when=ctx.currentTime+.03;
      sources.forEach(s=>loop?s.start(when,start):s.start(when,start,end-start));
      sources[0].onended=()=>{if(graph.current?.ctx===ctx){void ctx.close();graph.current=null;if(alive.current)setPreviewing(null);}};
      setPreviewing("blend");
    } catch(e){if(ctx.state!=="closed")await ctx.close();if(alive.current)setError(String(e));}
    finally {if(alive.current)setOperation(null);}
  }
  async function playShape() {
    if(previewing==="shape"){stop();return;}
    stop();onAudition();setOperation("shape");setError("");const seq=sequence.current;
    try {
      const url=previewUrl&&!previewDirty?previewUrl:(await api<{audio:string}>(endpoint+"/preview",{base:take.id,tone})).audio;
      if(!alive.current||seq!==sequence.current)return;
      setPreviewUrl(url);setPreviewDirty(false);
      const audio=new Audio(url);previewAudio.current=audio;
      audio.onloadedmetadata=()=>{audio.currentTime=Math.min(range[0],Math.max(0,audio.duration-.02));};
      audio.ontimeupdate=()=>{if(audio.currentTime>=range[1]-.015){if(loop)audio.currentTime=range[0];else{audio.pause();if(alive.current)setPreviewing(null);}}};
      audio.onended=()=>{if(alive.current)setPreviewing(null);};
      await audio.play();setPreviewing("shape");
    }catch(e){if(alive.current)setError(String(e));}
    finally {if(alive.current)setOperation(null);}
  }
  async function save(recipe:SoundRecipe) {
    stop();setOperation("save");onBusy(true);setError("");
    try {await api(endpoint,recipe);await onSaved();}
    catch(e){if(alive.current)setError(String(e));}
    finally {if(alive.current)setOperation(null);onBusy(false);}
  }
  function show(next:"shape"|"blend"){stop();setPanel(prev=>prev===next?null:next);setError("");}
  const changed=knobs.some(q=>tone[q.name]!==original[q.name]);
  const locked=disabled||operation!==null;
  return <section className="lab-sound-designer" aria-label="Sound design">
    <div className="lab-sound-tabs"><button aria-expanded={panel==="shape"} onClick={()=>show("shape")}>Shape this sound</button><button aria-expanded={panel==="blend"} disabled={pair.length!==2} onClick={()=>show("blend")}>Blend A ↔ B</button><span className="small muted">Preview freely. Save to create a new take.</span></div>
    {panel==="shape"&&<div className="lab-sound-panel">
      <h3>Shape Take {take?.take}</h3><p className="small muted">Tone and envelopes for {part} only. Adjust the controls, then preview.</p>
      <div className="lab-tone-knobs">{knobs.map(q=><label key={q.name} title={q.doc}>{labels[q.name]??q.name}<output>{Math.round((tone[q.name]??q.default)*100)}%</output><input aria-label={`Sound ${(labels[q.name]??q.name).toLowerCase()}`} type="range" min={q.lo} max={q.hi} step={.01} value={tone[q.name]??q.default} disabled={!ready||locked} onChange={e=>{stop();setTone(prev=>({...prev,[q.name]:+e.target.value}));setPreviewDirty(true);}}/><span className="small muted">{q.doc}</span></label>)}</div>
      <div className="lab-actions"><button disabled={!ready||locked} onClick={playShape}>{previewing==="shape"?"Stop shape preview":operation==="shape"?"Rendering preview…":"Preview shape"}</button><button disabled={!ready||locked||!changed} onClick={()=>{stop();setTone({...original});setPreviewDirty(true);}}>Reset to take</button><button className="primary" disabled={!ready||locked||!changed} onClick={()=>save({base:take.id,tone})}>{operation==="save"?"Saving take…":"Save shaped take"}</button></div>
      {previewDirty&&previewUrl&&<p className="small muted">Settings changed. Preview again to hear them.</p>}
    </div>}
    {panel==="blend"&&<div className="lab-sound-panel">
      <h3>Blend A ↔ B</h3><p className="small muted">Play the blend, then move the slider continuously. Only {part}{part.includes("/")?" changes; the other kit pieces stay fixed":" is heard"}. Preview gain keeps quiet parts audible and is not saved into the mix.</p>
      <label className="lab-blend-slider">A · Take {pair[0]?.take}<output>{Math.round((1-amount)*100)}% A / {Math.round(amount*100)}% B</output><input aria-label="A/B blend" type="range" min={0} max={1} step={.01} value={amount} disabled={locked} onChange={e=>setAmount(+e.target.value)}/><span>B · Take {pair[1]?.take}</span></label>
      <div className="lab-actions"><button disabled={locked||!pair.every(c=>c.audio.solo)} onClick={playBlend}>{previewing==="blend"?"Stop blend preview":operation==="blend"?"Loading blend…":"Play blend"}</button><button className="primary" disabled={locked||amount===0||amount===1} onClick={()=>save({pair:pair.map(c=>c.id),amount,tone:{}})}>{operation==="save"?"Saving take…":"Save blended take"}</button></div>
      <p className="small muted">At either endpoint, use the existing take. A blend uses complementary gains so shared material stays at its original level. Save a blend, then shape that take if you want both.</p>
    </div>}
    {error&&<p role="alert" className="lab-error">{error}</p>}
    {previewing&&<p role="status" className="small">Previewing an unsaved {previewing}. Save it as a take before voting on this sound.</p>}
    {!ready&&error&&<button disabled={locked} onClick={()=>{setError("");setRetry(n=>n+1);}}>Retry sound controls</button>}
  </section>;
}
