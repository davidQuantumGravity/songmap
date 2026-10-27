"""One playable instrument with named, real recorded techniques and shared tone controls."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import yaml

from .base import Instrument,Param,ParamError
from .response import CALIBRATION
from .sampler import Sampler
from .sound import Sound,TONE_PARAMS


def library():return yaml.safe_load(Path(__file__).with_name('families.yaml').read_text(encoding='utf-8')) or {}


def load(name,**params):return Family(name,library().get(name),**params)


def assign(song,tl,ens,parts):
    import math
    from ..parse.errors import SongError
    if not isinstance(song.techniques,dict):raise SongError('techniques must map section names to parts and beat/technique lists')
    sections={s.name:s for s in tl.sections}
    for name,changes in song.techniques.items():
        if name not in sections or not isinstance(changes,dict):raise SongError(f'Unknown technique section: {name}')
        sec=sections[name]
        for part,points in changes.items():
            if part not in parts or not isinstance(points,list):raise SongError(f'Invalid technique part: {part}')
            inst=ens.instrument(part)
            if not isinstance(inst,Family):raise SongError(f'{part}: named techniques need a family/<instrument> voice')
            previous=-1
            for row in points:
                if not isinstance(row,(list,tuple)) or len(row)!=2:raise SongError('Technique changes are [beat, name] pairs')
                beat,tech=row
                if isinstance(beat,bool) or not isinstance(beat,(int,float)) or not math.isfinite(beat) or not 0<=beat<sec.end-sec.start or not previous<beat:raise SongError('Technique beats must increase and lie within the section')
                if not isinstance(tech,str):raise SongError('A technique name must be text')
                inst.select(tech);previous=beat
            for e in parts[part]:
                if e.section==name:
                    applicable=[v for b,v in points if b<=e.beat-sec.start+1e-9]
                    if applicable:e.technique=applicable[-1]


class Family(Instrument):
    name='family';full_rr=True
    PARAMS=(*Sampler.PARAMS,*TONE_PARAMS,replace(CALIBRATION,default=1))

    def __init__(self,name,definition,**params):
        if not definition:raise ParamError(f'Unknown instrument family: {name}')
        self.recipe_name=name;self.definition=definition;self._voices={}
        self.choices=list(definition['techniques']);self.family=definition.get('family','string');self.mono=False
        from .sampler.library import manifest
        ref=definition['techniques'][definition['default']]
        defaults=manifest()['voices'].get(ref.removeprefix('sampler/'),{}).get('params',{}) if ref.startswith('sampler/') else {}
        self.PARAMS=(*(replace(q,default=defaults.get(q.name,q.default)) for q in self.PARAMS),Param('technique',-1,-1,len(self.choices)-1,'','lin','technique','-1 follows written articulation; named choices are in the technique selector'))
        super().__init__(**params)
        self.fingerprint=hashlib.sha256(json.dumps(definition,sort_keys=True).encode()).hexdigest()
        self.warnings=[]

    def select(self,technique=None,art='normal'):
        if technique and technique!='auto':choice=technique
        elif technique is None and self.p['technique']>=0:choice=self.choices[int(round(self.p['technique']))]
        else:choice=self.definition.get('automatic',{}).get(art,self.definition['default'])
        if choice not in self.choices:raise ParamError(f'{self.recipe_name}: unknown technique {choice}; choices: '+', '.join(self.choices))
        return choice

    def _voice(self,note):
        choice=self.select(note.technique)
        if choice not in self._voices:
            from . import make
            use=self.definition['techniques'][choice];child=make(use)
            self._voices[choice]=Sound(self.recipe_name,{'a':{'use':use,'params':{}}},[child])
        voice=self._voices[choice]
        child=voice.layers[0]
        if getattr(child,'program',None) is not None and not any(r.lokey<=round(note.pitch)<=r.hikey and not r.is_release for r in child.program.regions):
            raise ParamError(f'{self.recipe_name}/{choice}: MIDI {note.pitch:g} is outside the recorded range')
        params={k:v for k,v in {**self.p,**note.params}.items() if k!='technique'}
        # Forward shared controls as per-note overrides so edits never stale the cached source.
        return voice,replace(note,params=params)

    @property
    def sources(self):return [s for v in self._voices.values() for s in v.sources]

    def tail(self,note):
        v,n=self._voice(note);return v.tail(n)

    def choke(self,note):
        v,n=self._voice(note);return v.choke(n)

    def render(self,note):
        v,n=self._voice(note);return v.render(n)

    def render_at_pan(self,note,pan,finish=None):
        v,n=self._voice(note);return v.render_at_pan(n,pan,finish)
