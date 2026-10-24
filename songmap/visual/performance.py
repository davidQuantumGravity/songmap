"""Instrument performance cards: explicit sounding pitches, staff and fractional pitch strip.

All animation follows written note gates. Activity indicators describe note events,
not measured audio levels; release and reverb tails are deliberately not inferred.
"""
from __future__ import annotations

from functools import lru_cache
import math

from PIL import Image, ImageDraw

from ..theory.tuning import OCTAVE
from .draw import InstrumentPanel, _BOLD, _BOLD_SYM, _TEXT, _SYM, _font, _mix
from .score import spell


@lru_cache(maxsize=256)
def chord_names(symbol):
    from ..theory.harmony import Chord
    chord = Chord.parse(symbol)
    return tuple(spell(5 * OCTAVE + chord.root + iv).name for iv in chord.intervals)


def stage_background(width, height, theme):
    """Subtle vertical depth, cached by the parent frame renderer."""
    a, b = theme['bg'], _mix(theme['bg'], theme['panel'], .65)
    strip = Image.new('RGB', (1, height))
    strip.putdata([_mix(a, b, y/max(1, height-1)) for y in range(height)])
    return strip.resize((width, height))


def draw_header(renderer, draw, t):
    th, sc = renderer.th, renderer.sc
    layer = renderer.first['header']
    x0,y0,x1,y1 = renderer.r_header
    k = (y1-y0)/100
    left=x0+18*k
    if layer.get('title',True):
        title=layer.get('text') or sc.title
        font=_font(_BOLD,32*k)
        while draw.textlength(title,font=font)>(x1-x0)*.56 and font.size>14:
            font=_font(_BOLD,font.size-1)
        draw.text((left,y0+30*k),title,font=font,fill=th['ink'],anchor='lm')
    if layer.get('info',True):
        section=sc.section_at(t).replace('_',' ')
        bar=min(sc.bar_at(t)+1,max(1,len(sc.bars)-1))
        label=f'{section}  /  BAR {bar:02d}'
        subtitle=str(layer.get('subtitle') or '')
        draw.text((left,y0+64*k),label,font=_font(_TEXT,16*k),fill=th['muted'],anchor='lm')
        if subtitle:
            draw.text((left,y0+85*k),subtitle,font=_font(_TEXT,12*k),fill=th['muted'],anchor='lm')
    chord=sc.chord_at(t)
    if not chord or not layer.get('chord',True):
        return
    col=th[chord.kind]
    pop=math.exp(-max(0,t-chord.start)/.16)
    f=_font(_BOLD,35*k)
    w=draw.textlength(chord.symbol,font=f)+42*k
    right=x1-20*k
    cy=y0+37*k
    draw.rounded_rectangle((right-w,cy-26*k,right,cy+26*k),radius=12*k,
                           fill=_mix(col,th['panel'],.06+.1*(1-pop)))
    draw.text((right-w/2,cy),chord.symbol,font=f,fill=th['bg'],anchor='mm')
    names='  ·  '.join(chord_names(chord.symbol))
    f=_font(_BOLD_SYM,16*k)
    while draw.textlength(names,font=f)>(x1-x0)*.4 and f.size>12:
        f=_font(_BOLD_SYM,f.size-1)
    draw.text((right,y0+82*k),names,font=f,fill=th['ink'],anchor='rm')
    draw.text((right-w-17*k,cy),'HARMONY',font=_font(_BOLD,11*k),fill=th['muted'],anchor='rm')


class PerformancePanel(InstrumentPanel):
    """Opt-in card with large per-pitch chips and a true 12/36-ET pitch strip."""

    def __init__(self,score,layer,theme,color_of):
        super().__init__(score,layer,theme,color_of)
        self.scale=max(.45,min(self.W/720,self.H/250))
        self.pad=max(8,round(17*self.scale))
        self.f_label=_font(_BOLD,max(12,20*self.scale))
        self.f_info=_font(_TEXT,max(9,11*self.scale))
        self.f_pitch=_font(_BOLD_SYM,max(14,26*self.scale))
        self._layout_key=None
        self._base={}
        self.chip_bottom=round(96*self.scale)
        self.strip_top=self.H-round(38*self.scale)
        self.subdivisions=self.score.edo/OCTAVE
        self.accent=(color_of(self.score.notes[0]) if self.score.notes else theme['gold'])

    def active_notes(self,t):
        """One chip per exact pitch; retain distinct sixth-steps and octave doublings."""
        notes={}
        for note in self.score.sounding(t):
            key=round(note.pitch*self.subdivisions)
            if key not in notes or note.start>notes[key].start:
                notes[key]=note
        return [notes[key] for key in sorted(notes)]

    def note_names(self,t):
        return [spell(n.pitch).text for n in self.active_notes(t)]

    def chip_layout(self,t):
        """Fit all current pitches in wrapped rows, reserving staff space below."""
        notes=self.active_notes(t)
        if not notes:
            return [],self.f_pitch,self.chip_bottom
        measure=ImageDraw.Draw(Image.new('RGB',(1,1)))
        font=self.f_pitch
        gap=max(4,round(7*self.scale))
        pad=max(7,round(12*self.scale))
        available=self.W-2*self.pad
        while True:
            widths=[math.ceil(measure.textlength(spell(n.pitch).text,font=font))+2*pad for n in notes]
            rows=[];row=[];used=0
            for note,width in zip(notes,widths):
                if row and used+width>available:
                    rows.append(row);row=[];used=0
                row.append((note,width));used+=width+gap
            rows.append(row)
            if len(rows)<=2 or font.size<=max(10,round(14*self.scale)):
                break
            font=_font(_BOLD_SYM,font.size-1)
        height=font.size+max(10,round(12*self.scale))
        y=round(43*self.scale)
        positions=[]
        for row in rows:
            x=self.pad
            for note,width in row:
                positions.append((note,(x,y,min(self.W-self.pad,x+width),y+height)))
                x+=width+gap
            y+=height+gap
        return positions,font,max(self.chip_bottom,y+max(3,round(5*self.scale)))

    def note_x(self,n,window):
        x=super().note_x(n,window)
        same=sorted({round(m.pitch*self.subdivisions) for m in self.score.between(n.start,n.start+.0001)
                     if abs(m.start-n.start)<.0001 and spell(m.pitch).diatonic==spell(n.pitch).diatonic})
        key=round(n.pitch*self.subdivisions)
        return x+(same.index(key) if key in same else 0)*2.2*self.unit

    def _prepare(self,window,chip_bottom):
        key=(window,chip_bottom)
        if key==self._layout_key:
            return
        self._layout_key=key
        a,b=window
        notes=[n for n in self.score.between(a,b) if n.start<b-1e-8]
        pitches=sorted(n.pitch for n in notes)
        self.treble=not pitches or pitches[len(pitches)//2]>=60
        self.lines=(30,32,34,36,38) if self.treble else (16,18,20,22,24)
        ds=[spell(n.pitch).diatonic for n in notes]
        self.lo=min(min(ds,default=self.lines[0]),self.lines[0])-2
        self.hi=max(max(ds,default=self.lines[-1]),self.lines[-1])+2
        self.top=chip_bottom+round(8*self.scale)
        self.bottom=self.strip_top-round(10*self.scale) if self.layer.get('pitch_strip',True) else self.H-round(23*self.scale)
        self.bottom=max(self.top+10,self.bottom)
        self.unit=min(8.8*self.scale,max(1,(self.bottom-self.top)/max(1,self.hi-self.lo)))
        self.ytop=(self.top+self.bottom-(self.hi-self.lo)*self.unit)/2
        self.x0=self.pad+max(26,round(36*self.scale))
        self.x1=self.W-self.pad-8
        lo=min(pitches,default=60);hi=max(pitches,default=72)
        span=max(OCTAVE,math.ceil(hi)-math.floor(lo)+2)
        self.strip_low=math.floor((lo+hi)/2-span/2)
        self.strip_high=self.strip_low+span

    def pitch_cells(self):
        start=round(self.strip_low*self.subdivisions)
        end=round(self.strip_high*self.subdivisions)+1
        x0,x1=self.pad,self.W-self.pad
        width=(x1-x0)/max(1,end-start)
        return [(key,(x0+i*width,self.strip_top,x0+(i+1)*width,self.strip_top+13*self.scale))
                for i,key in enumerate(range(start,end))]

    def _background(self,window):
        cache_key=(self._layout_key,self.layer.get('pitch_strip',True))
        if cache_key in self._base:
            return self._base[cache_key].copy()
        th=self.th;k=self.scale
        im=Image.new('RGB',(self.W,self.H),th['bg']);d=ImageDraw.Draw(im)
        if self.layer.get('panel',True):
            d.rounded_rectangle((0,0,self.W-1,self.H-1),radius=round(17*k),fill=th['panel'],
                                outline=_mix(th['line'],th['panel'],.35),width=max(1,round(k)))
        d.line((self.pad,31*k,self.W-self.pad,31*k),fill=_mix(self.accent,th['panel'],.72),width=max(1,round(k)))
        d.text((self.pad,17*k),self.label,font=self.f_label,fill=th['ink'],anchor='lm')
        for line in self.lines:
            d.line((self.pad,self.y(line),self.x1,self.y(line)),fill=th['line'],width=max(1,round(k)))
        f=_font(_SYM,max(15,self.unit*7))
        d.text((self.pad+2,self.y(sum(self.lines)/5)),'𝄞' if self.treble else '𝄢',font=f,fill=th['muted'],anchor='lm')
        if self.mode=='bar':
            a,b=window
            for n in self.score.between(a,b):
                if n.start<b-1e-8:
                    self._note(d,n,window,self.color_of(n,.46))
        if self.layer.get('pitch_strip',True):
            footer_width=d.textlength(f'{self.score.edo}-ET  /  ONE BAR',font=self.f_info)+15*k
            for key,box in self.pitch_cells():
                whole=abs(key/self.subdivisions-round(key/self.subdivisions))<1e-8
                color=_mix(th['ink'],th['panel'],.72 if whole else .9)
                d.rectangle((box[0]+.5,box[1],max(box[0]+.5,box[2]-.5),box[3]),fill=color)
                if whole and round(key/self.subdivisions)%OCTAVE==0 and box[0]<self.W-self.pad-footer_width:
                    d.text((box[0],box[3]+2*k),spell(key/self.subdivisions).text,font=self.f_info,fill=th['muted'],anchor='la')
        self._base[cache_key]=im.copy()
        if len(self._base)>3:
            self._base.pop(next(iter(self._base)))
        return im

    def frame(self,t):
        if self.W<120 or self.H<90:
            im=Image.new('RGB',(self.W,self.H),self.th['panel'])
            d=ImageDraw.Draw(im)
            d.text((3,3),self.label,font=_font(_BOLD,10),fill=self.th['ink'])
            d.text((3,20),' '.join(self.note_names(t)) or 'rest',font=_font(_BOLD_SYM,10),fill=self.accent)
            return im
        window=self.window_at(t)
        chips,font,chip_bottom=self.chip_layout(t)
        if not self.layer.get('note_chips',True):
            chips=[];chip_bottom=round(43*self.scale)
        self._prepare(window,chip_bottom)
        im=self._background(window);d=ImageDraw.Draw(im)
        th=self.th;k=self.scale
        now=self.active_notes(t)
        status='PLAYING' if now else 'REST'
        if now and self.layer.get('glow',True):
            d.rounded_rectangle((1,1,self.W-2,self.H-2),radius=round(17*k),
                                outline=_mix(self.accent,th['panel'],.38),width=max(1,round(2*k)))
        d.text((self.W-self.pad,17*k),status,font=self.f_info,fill=self.accent if now else th['muted'],anchor='rm')
        for n,box in chips:
            color=self.color_of(n)
            pop=math.exp(-max(0,t-n.start)/.13)
            fill=_mix(color,th['panel'],.76-.12*pop)
            d.rounded_rectangle(box,radius=max(3,round(8*k)),fill=fill,outline=_mix(color,th['panel'],.25))
            d.text(((box[0]+box[2])/2,(box[1]+box[3])/2-1),spell(n.pitch).text,font=font,fill=th['ink'],anchor='mm')
            fraction=min(1,max(0,(t-n.start)/max(n.end-n.start,.001)))
            d.line((box[0]+7*k,box[3]-3*k,box[0]+7*k+(box[2]-box[0]-14*k)*fraction,box[3]-3*k),fill=color,width=max(1,round(2*k)))
        if not now and self.layer.get('note_chips',True):
            d.text((self.pad,61*k),'—',font=self.f_pitch,fill=th['muted'],anchor='lm')
        for n in now:
            if self.layer.get('glow',True):
                x=self.note_x(n,window)
                y=self.y(spell(n.pitch).diatonic);r=2.1*self.unit
                d.ellipse((x-r,y-r,x+r,y+r),fill=_mix(self.color_of(n),th['panel'],.78))
            self._note(d,n,window,self.color_of(n),now=t)
        if self.mode=='bar':
            x=self.x(t,window)
            d.line((x,self.top,x,self.bottom),fill=th['cursor'],width=max(1,round(1.6*k)))
        if self.layer.get('pitch_strip',True):
            active={round(n.pitch*self.subdivisions):n for n in now}
            for key,box in self.pitch_cells():
                if key in active:
                    d.rectangle(box,fill=self.color_of(active[key]))
                    d.line((box[0],box[1]-2*k,box[2],box[1]-2*k),fill=th['ink'],width=max(1,round(k)))
        label=f'{self.score.edo}-ET  /  '+('LIVE NOTES' if self.mode=='active' else 'ONE BAR' if self.bars==1 else f'{self.bars} BARS')
        d.text((self.W-self.pad,self.H-5*k),label,font=self.f_info,fill=th['muted'],anchor='rd')
        return im
