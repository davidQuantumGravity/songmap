"""Section-aware tempo, meter and tonal metadata, including structured-score overrides."""
from __future__ import annotations

import re

from ..parse.errors import NotationError, SongError
from ..theory.keys import MODES, parse_key
from .timeline import parse_tempo

FIELDS = {"tempo", "meter", "key"}


def meter_text(meter):
    return f"{meter[0]}/{meter[1]}" + (" "+"+".join(map(str,meter[2])) if len(meter)>2 else "")


def key_parts(key):
    parse_key(key)
    m = re.fullmatch(r"\s*([\^v]*[A-Ga-g][#b]?)\s*(.*?)\s*",key)
    if not m:
        raise NotationError(f"key '{key}' not understood")
    return m[1], {"":"major","m":"minor"}.get(m[2],m[2])


def apply_overrides(song, mapping):
    from ..parse.yaml_form import parse_meter
    if not isinstance(mapping,dict):
        raise SongError("conductor must be a mapping from section names to tempo, meter and key",file=song.file)
    for name, values in mapping.items():
        matches = [s for s in song.sections if s.name==name]
        if len(matches)!=1:
            raise SongError(f"conductor: section '{name}' must identify one section instance",file=song.file,
                            suggestion="use a unique expanded section name from the Conductor view")
        sec = matches[0]
        if not isinstance(values,dict) or set(values)-FIELDS:
            raise SongError("conductor fields are tempo, meter and key",file=song.file,section=name)
        for key,value in values.items():
            setattr(sec,key,parse_meter(value,file=song.file,section=name) if key=="meter" and value is not None else value)
    for sec in song.sections:
        parse_tempo(song.tempo if sec.tempo is None else sec.tempo,song,sec)
        if sec.key is not None:
            try:
                if not isinstance(sec.key,str):
                    raise NotationError("section key must be a key and scale name")
                parse_key(sec.key)
            except NotationError as e:
                raise SongError(str(e),file=song.file,line=sec.line,section=sec.name) from None


def section_metadata(song, tl, span):
    sec = song.sections[span.index]
    key = sec.key or song.key
    tonic, scale = key_parts(key)
    a,b = parse_tempo(song.tempo if sec.tempo is None else sec.tempo,song,sec)
    return {"tempo_start":a,"tempo_end":b,"tempo_override":sec.tempo,
            "meter":meter_text(sec.meter or song.meter),"meter_override":meter_text(sec.meter) if sec.meter else None,
            "key":key,"key_override":sec.key,"tonic":tonic,"scale":scale,
            "beats_per_bar":span.bpb,"start_beat":span.start,"end_beat":span.end,"groups":list(span.groups)}


def scale_catalog():
    from ..theory.tuning import on_grid, parse_tuning
    grid = parse_tuning("12edo")
    return [{"name":name,"intervals":list(intervals),"microtonal":any(not on_grid(x,grid) for x in intervals)}
            for name,intervals in MODES.items()]
