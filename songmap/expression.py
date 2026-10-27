"""Beat-based continuous expression, evaluated inside held notes at audio rate.

Explicit section lanes hold their final value until the next lane for the same part/control.
Timing uses the conductor's exact inverse, including beat-linear tempo ramps. Neutral lanes
return source audio unchanged. Original scores without lanes retain their existing rendering.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math

import numpy as np

from .instruments.base import Param
from .instruments.dsp import SR,eq
from .parse.errors import SongError

CONTROLS=(
    Param('volume',1,0,1,'','lin','expression','continuous performance volume; retains written note velocities'),
    Param('brightness',0,-1,1,'','lin','expression','dark to bright high-shelf tone'),
    Param('body',0,-1,1,'','lin','expression','lean to full low-shelf tone'),
    Param('vibrato_depth',0,0,100,'cents','lin','expression','added pitch vibrato; recorded vibrato remains'),
    Param('vibrato_rate',5.2,.1,12,'Hz','lin','expression','added vibrato speed'),
    Param('pitch_cents',0,-200,200,'cents','lin','expression','continuous pitch bend, added to exact score pitch'),
    Param('stereo_width',1,0,2,'x','lin','expression','side signal gain; 1 preserves the source'),
    Param('blend',.5,0,1,'','lin','mix','two-source sound balance'),
    Param('morph_x',0,0,1,'','lin','mix','four-source horizontal balance'),
    Param('morph_y',0,0,1,'','lin','mix','four-source vertical balance'),
)
SPECS={q.name:q for q in CONTROLS}
MIX={'blend','morph_x','morph_y'}


def points(raw,length,spec):
    if isinstance(raw,(float,int)) and not isinstance(raw,bool):raw=[[0,raw],[length,raw]]
    if not isinstance(raw,list) or len(raw)<2:raise SongError('An expression curve needs at least two [beat, value] points')
    out=[]
    for row in raw:
        if not isinstance(row,(list,tuple)) or len(row)!=2:raise SongError('Expression points are [quarter-note beat, value] pairs')
        b,v=row
        if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in row):raise SongError('Expression points must contain finite numbers')
        if not 0<=b<=length or not spec.lo<=v<=spec.hi:raise SongError(f'{spec.name}: beats must be 0..{length:g}, values {spec.lo:g}..{spec.hi:g}')
        if out and b<=out[-1][0]:raise SongError('Expression point beats must increase strictly')
        out.append((float(b),float(v)))
    if out[0][0]!=0 or out[-1][0]!=length:raise SongError(f'Expression curves must begin at beat 0 and end at beat {length:g}')
    return out


@dataclass(frozen=True)
class Bound:
    owner: object
    part: str
    name: str
    start: float
    default: float | None = None

    def samples(self,n):return self.owner.values(self.part,self.name,self.start+np.arange(n)/SR,default=self.default)


class Expression:
    def __init__(self,arr):
        self.arr=arr;self.tracks={};self.defaults={};raw=arr.song.expression
        if not isinstance(raw,dict):raise SongError('expression must map sections to parts and control curves')
        sections={s.name:s for s in arr.timeline.sections}
        for name,parts in raw.items():
            if name not in sections or not isinstance(parts,dict):raise SongError(f'Expression needs an existing section: {name}')
            sec=sections[name]
            for part,lanes in parts.items():
                if part not in arr.parts or not isinstance(lanes,dict):raise SongError(f'Expression needs an existing played part: {part}')
                # Layout and static mix defaults are score metadata. Do not build
                # sampled layers just to validate a curve on a fresh checkout.
                layout=set();voice=None
                if any(key in MIX for key in lanes) and not arr.ensemble.is_kit(part):
                    voice=arr.ensemble.voice(part)
                    if voice.use.startswith('sound/'):
                        definition=arr.ensemble.sound_spec(voice.use.partition('/')[2])
                        if isinstance(definition,dict):layout=set(definition)
                supported={'blend'} if layout=={'a','b'} else {'morph_x','morph_y'} if layout=={'a','b','c','d'} else set()
                for key,value in lanes.items():
                    if key not in SPECS:raise SongError(f'Unknown continuous expression control: {key}')
                    if key in MIX:
                        if key not in supported:raise SongError(f'{part}: {key} needs a sound with that source layout')
                        default=voice.params.get(key,SPECS[key].default)
                        if isinstance(default,bool) or not isinstance(default,(int,float)) or not math.isfinite(default):raise SongError(f'{part}: {key} must be a finite number')
                        self.defaults[part,key]=SPECS[key].clamp(default)
                    ps=points(value,sec.end-sec.start,SPECS[key])
                    self.tracks.setdefault((part,key),[]).append((sec.start,ps))
        for segments in self.tracks.values():segments.sort(key=lambda x:x[0])
        timing=[(s.b0,s.b1,s.t0,s.t1,s.bpm0,s.bpm1) for s in arr.timeline._segs]
        self.fingerprint=hashlib.sha256(json.dumps([raw,timing],sort_keys=True).encode()).hexdigest() if raw else ''

    def beats(self,times):
        ts=np.asarray(times,dtype=float);out=np.empty_like(ts)
        for i,s in enumerate(self.arr.timeline._segs):
            mask=(ts>=s.t0) & ((ts< s.t1) if i<len(self.arr.timeline._segs)-1 else True)
            dt=ts[mask]-s.t0
            if s.bpm0==s.bpm1:out[mask]=s.b0+dt*s.bpm0/60
            else:
                k=(s.bpm1-s.bpm0)/(s.b1-s.b0)
                out[mask]=s.b0+s.bpm0*np.expm1(k*np.minimum(dt,s.t1-s.t0)/60)/k
                tail=mask & (ts>s.t1);out[tail]=s.b1+(ts[tail]-s.t1)*s.bpm1/60
        first=self.arr.timeline._segs[0];mask=ts<first.t0;out[mask]=first.b0+(ts[mask]-first.t0)*first.bpm0/60
        return out

    def values(self,part,key,times,default=None):
        bs=self.beats(times);out=np.full(bs.shape,self.defaults.get((part,key),SPECS[key].default) if default is None else default,dtype=float)
        segments=self.tracks.get((part,key),[])
        for i,(start,ps) in enumerate(segments):
            mask=(bs>=start-1e-10)
            if i+1<len(segments):mask &= bs<segments[i+1][0]-1e-10
            out[mask]=np.interp(bs[mask]-start,[p[0] for p in ps],[p[1] for p in ps])
        return out

    def bind(self,part,start,defaults=None):
        defaults=defaults or {}
        return {k:Bound(self,part,k,start,defaults.get(k,self.defaults.get((part,k),SPECS[k].default)) if k in MIX else None) for p,k in self.tracks if p==part}


def apply(audio,note):
    curves=note.curves
    if not curves:return audio
    y=audio;cached={}
    def control(k):
        if k not in cached:cached[k]=curves[k].samples(len(y)) if k in curves else np.full(len(y),SPECS[k].default)
        return cached[k]
    # Variable shelf processing is a smooth interpolation between fixed endpoint
    # filters. It does not re-trigger notes or change the underlying sample velocity.
    for key,kind,freq,db in [('brightness','highshelf',3500,12),('body','lowshelf',180,9)]:
        if key not in curves:continue
        v=control(key)
        if np.any(v):
            lo,hi=eq(y,kind,freq,-db),eq(y,kind,freq,db)
            a=np.maximum(-v,0);b=np.maximum(v,0)
            y=y*(1-a-b)[:,None]+lo*a[:,None]+hi*b[:,None] if y.ndim==2 else y*(1-a-b)+lo*a+hi*b
    if 'pitch_cents' in curves or 'vibrato_depth' in curves:
        pitch=control('pitch_cents');depth=control('vibrato_depth')
        phase=2*np.pi*np.cumsum(control('vibrato_rate'))/SR
        cents=pitch+depth*np.sin(phase)
        if np.any(cents) and len(y)>1:
            ratio=2**(cents/1200);pos=np.cumsum(np.r_[0.,ratio[:-1]]);indices=np.arange(len(y))
            y=np.interp(pos,indices,y,right=0) if y.ndim==1 else np.column_stack([np.interp(pos,indices,y[:,i],right=0) for i in range(y.shape[1])])
            # Downward bends can end before the source buffer's existing fade.
            # Keep the renderer's short end fade after non-neutral resampling.
            from .render import declick
            y=declick(y)
    if 'stereo_width' in curves and y.ndim==2:
        width=control('stereo_width')
        if np.any(width!=1):
            mid=y.mean(axis=1);side=(y[:,0]-y[:,1])*.5*width;y=np.column_stack([mid+side,mid-side])
    if 'volume' in curves:
        v=control('volume')
        if np.any(v!=1):y=y*v[:,None] if y.ndim==2 else y*v
    return y
