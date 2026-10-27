"""Validated, unsaved edits for performance curves and named technique changes."""
from __future__ import annotations

import copy
import yaml

from .project import parse_text
from .conductor import _set
from ..arrange.expand import expand
from ..parse import yaml_form


def edit(text,path,*,index,part,control=None,points=None,techniques=None):
    song=parse_text(text,path)
    if isinstance(index,bool) or not isinstance(index,int) or not 0<=index<len(song.sections):raise ValueError('Choose an existing section')
    if part not in song.parts():raise ValueError('Choose a played part')
    key='techniques' if control is None else 'expression'
    mapping=copy.deepcopy(getattr(song,key));section=song.sections[index].name
    values=mapping.setdefault(section,{});raw=techniques if control is None else points
    if control is None:
        if raw:values[part]=raw
        else:values.pop(part,None)
    else:
        lanes=values.setdefault(part,{})
        if raw is None:lanes.pop(control,None)
        else:lanes[control]=raw
        if not lanes:values.pop(part,None)
    if not values:mapping.pop(section,None)
    if path.lower().endswith(('.sm','.sml')):new=_set(text,key,mapping)
    else:
        raw=yaml_form._plain(yaml_form.load_raw_text(text,path));raw[key]=mapping
        new=yaml.safe_dump(raw,sort_keys=False,allow_unicode=True)
    expand(parse_text(new,path))
    return new
