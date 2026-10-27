"""Saved sound recipes: one, two or four sources and neutral-by-default tone controls.

Blends use complementary linear gains, so identical material stays unchanged.
The same note, seed, velocity and round-robin slot reach both sources. Tone
envelopes operate per note, rather than chopping the full musical passage.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from .base import Instrument, Param, ParamError
from .dsp import SR, as_stereo, eq, pan_mono
from ..parse.errors import SongError

TONE_PARAMS = (
    Param("tone_brightness", 0, -1, 1, "", "lin", "tone", "dark to bright; neutral at 0"),
    Param("tone_body", 0, -1, 1, "", "lin", "tone", "lean to full; neutral at 0"),
    Param("tone_attack", 0, 0, 1, "", "lin", "tone", "soften each note's attack; original at 0"),
    Param("tone_tightness", 0, 0, 1, "", "lin", "tone", "shorten each note's body and tail; original at 0"),
    Param("tone_grit", 0, 0, 1, "", "lin", "tone", "add saturation; clean at 0"),
    Param("tone_width", 0, -1, 1, "", "lin", "tone", "narrow or widen recorded stereo; original at 0, mono at -1"),
    Param("tone_vibrato", 0, 0, 1, "", "lin", "tone", "added delayed pitch vibrato, up to 35 cents; recorded vibrato remains"),
)
BLEND = Param("blend", .5, 0, 1, "", "lin", "mix", "0 = source A, 1 = source B")
MORPH_PARAMS = (
    Param("morph_x", 0, 0, 1, "", "lin", "mix", "four-corner crossfade: A/C to B/D"),
    Param("morph_y", 0, 0, 1, "", "lin", "mix", "four-corner crossfade: A/B to C/D"),
)


def library():
    """Named hybrid recipes; scores can override them with their own definitions."""
    import yaml
    return yaml.safe_load(Path(__file__).with_name("sounds.yaml").read_text(encoding="utf-8")) or {}


def build(name, definition, ensemble, _stack=(), **values):
    if name in _stack or len(_stack) >= 4:
        raise SongError("Recursive sound definition or sound nesting exceeds four levels")
    if not isinstance(definition, dict) or set(definition) not in ({"a"}, {"a", "b"}, {"a", "b", "c", "d"}):
        raise ParamError("A sound definition needs a, a/b, or all four sources a/b/c/d")
    layers = []
    for key in ("a", "b", "c", "d"):
        if key not in definition:
            continue
        item = definition[key]
        if (not isinstance(item, dict) or set(item)-{"use", "params", "patch"}
                or not isinstance(item.get("use"), str) or not isinstance(item.get("params", {}), dict)):
            raise ParamError("A sound source needs use and numeric params")
        use, params = item["use"], item.get("params", {})
        if "patch" in item and not use.startswith("patch/"):
            raise ParamError("An embedded patch needs a patch/<name> source")
        if use.startswith("sound/"):
            child_name = use.partition("/")[2]
            inst = build(child_name, ensemble.sound_spec(child_name), ensemble, (*_stack, name), **params)
        elif use.startswith("patch/"):
            from .patch import build as patch
            child_name = use.partition("/")[2]
            inst = patch(child_name, item["patch"] if "patch" in item else ensemble.patch_spec(child_name), **params)
        else:
            from . import make
            inst = make(use, **params)
        schema = {q.name:q for q in inst.PARAMS}
        for k, v in params.items():
            if (k not in schema or isinstance(v, bool) or not isinstance(v, (int, float))
                    or not math.isfinite(v) or not schema[k].lo <= v <= schema[k].hi):
                raise ParamError(f"Invalid sound source parameter: {k}")
        layers.append(inst)
    if sum(getattr(i, "leaf_count", 1) for i in layers) > 8:
        raise ParamError("A sound may contain at most eight source voices")
    sound = Sound(name, definition, layers, **values)
    sound.fingerprint = hashlib.sha256(json.dumps([definition, ensemble.song.sounds, ensemble.song.patches, library()], sort_keys=True).encode()).hexdigest()
    return sound


class Sound(Instrument):
    name = "sound"
    PARAMS = (BLEND, *MORPH_PARAMS, *TONE_PARAMS)

    def __init__(self, recipe_name, definition, layers, **values):
        self.layers = layers
        self.recipe_name = recipe_name
        self.family = layers[0].family
        self.mono = all(i.mono for i in layers)
        self.leaf_count = sum(getattr(i, "leaf_count", 1) for i in layers)
        self.full_rr = any(getattr(i, "program", None) is not None or getattr(i, "full_rr", False) for i in layers)
        # Common names preserve existing style/note overrides. Prefixed names
        # allow a designer to adjust one source independently in the rack.
        params = {q.name:q for q in ((*MORPH_PARAMS, *TONE_PARAMS) if len(layers)==4 else (BLEND, *TONE_PARAMS))}
        for prefix, inst in zip(("a", "b", "c", "d"), layers):
            for q in inst.PARAMS:
                q = replace(q, default=inst.p.get(q.name, q.default))
                params.setdefault(q.name, q)
                params[f"{prefix}.{q.name}"] = replace(q, name=f"{prefix}.{q.name}")
        self.PARAMS = tuple(params.values())
        self.explicit = set(values)
        self.fingerprint = hashlib.sha256(json.dumps(definition, sort_keys=True).encode()).hexdigest()
        self.warnings = [w for i in layers for w in getattr(i, "warnings", [])]
        if any(isinstance(v, bool) or not isinstance(v, (int,float)) or not math.isfinite(v) for v in values.values()):
            raise ParamError("Sound parameters must be finite numbers")
        super().__init__(**values)

    def _control(self, note, key):
        value = self.p_(note, key)
        if not isinstance(value, (int,float)) or not math.isfinite(value):
            raise ParamError(f"Sound control {key} must be a finite number")
        return self.spec[key].clamp(value)

    @property
    def sources(self):
        return [s for i in self.layers for s in (i.sources if isinstance(i, Sound) else [i.source] if hasattr(i, "source") else [])]

    def _active(self, note, moving=False):
        if moving and any(k in note.curves for k in ('blend','morph_x','morph_y')):
            return [(p,i,1.) for p,i in zip('abcd',self.layers)]
        if len(self.layers)==4:
            x,y = (self._control(note,k) for k in ("morph_x","morph_y"))
            weights = ((1-x)*(1-y), x*(1-y), (1-x)*y, x*y)
        else:
            mix = self._control(note, "blend") if len(self.layers) == 2 else 0
            weights = (1-mix, mix)
        return [(prefix, inst, w) for prefix, inst, w in zip(("a", "b", "c", "d"), self.layers, weights) if w > 0]

    def _note(self, note, prefix, inst):
        p = {}
        outer_controls = {q.name for q in Sound.PARAMS}
        for q in inst.PARAMS:
            if q.name in self.explicit and q.name not in outer_controls:
                p[q.name] = self.p[q.name]
            if f"{prefix}.{q.name}" in self.explicit:
                p[q.name] = self.p[f"{prefix}.{q.name}"]
            if q.name in note.params and q.name not in outer_controls:
                p[q.name] = note.params[q.name]
            if f"{prefix}.{q.name}" in note.params:
                p[q.name] = note.params[f"{prefix}.{q.name}"]
        return replace(note, params=p, curves={})

    def tail(self, note):
        return max(i.tail(self._note(note, p, i)) for p, i, _ in self._active(note, moving=True))

    def choke(self, note):
        # A single engine note has one choke identity; use its dominant layer.
        p, i, _ = max(self._active(note), key=lambda x:x[2])
        return i.choke(self._note(note, p, i))

    def render(self, note):
        return self._render(note, None)

    def render_at_pan(self, note, pan, finish=None):
        """Preserve each source's mono/stereo placement law before combining it."""
        return self._render(note, pan, finish)

    def _render(self, note, pan, finish=None):
        signals = []
        for prefix, inst, weight in self._active(note, moving=True):
            child_note = self._note(note, prefix, inst)
            if pan is not None and isinstance(inst, Sound):
                audio = inst.render_at_pan(child_note, pan, finish)
            else:
                audio = inst.render(child_note)
                if finish is not None:
                    audio = finish(audio)
                if pan is not None:
                    audio = pan_mono(audio, pan) if audio.ndim == 1 else audio*np.array([1-max(pan,0),1+min(pan,0)])
            if any(k in note.curves for k in ('blend','morph_x','morph_y')):
                def lane(key):
                    return note.curves[key].samples(len(audio)) if key in note.curves else self._control(note,key)
                if len(self.layers)==4:
                    x,y=lane('morph_x'),lane('morph_y')
                    weight={'a':(1-x)*(1-y),'b':x*(1-y),'c':(1-x)*y,'d':x*y}[prefix]
                elif len(self.layers)==2:
                    x=lane('blend');weight=1-x if prefix=='a' else x
            signals.append((audio, weight))
        stereo = any(y.ndim == 2 for y, _ in signals)
        y = np.zeros((max(len(x) for x, _ in signals), 2) if stereo else max(len(x) for x, _ in signals))
        for x, w in signals:
            y[:len(x)] += (as_stereo(x) if stereo else x) * (w[:,None] if stereo and isinstance(w,np.ndarray) else w)
        bright, body = self._control(note, "tone_brightness"), self._control(note, "tone_body")
        if bright:
            y = eq(y, "highshelf", 3500, 12*bright)
        if body:
            y = eq(y, "lowshelf", 180, 9*body)
        attack, tight, grit = (self._control(note, k) for k in ("tone_attack", "tone_tightness", "tone_grit"))
        if attack or tight:
            t = np.arange(len(y))/SR
            env = np.exp(-4*t*tight/max(note.gate, .08)) if tight else np.ones(len(y))
            if attack:
                env *= .5-.5*np.cos(np.pi*np.minimum(t/(.08*attack), 1))
            y *= env[:, None] if y.ndim == 2 else env
        if grit:
            drive = 1+9*grit
            y = np.tanh(drive*y)/np.tanh(drive)
        width, vibrato = (self._control(note,k) for k in ("tone_width","tone_vibrato"))
        if width and y.ndim==2:
            mid = (y[:,0]+y[:,1])*.5
            side = (y[:,0]-y[:,1])*.5*(1+width)
            y = np.column_stack((mid+side,mid-side))
        if vibrato and len(y)>1:
            # Integrate instantaneous pitch ratio; delay modulation until after the
            # attack. Both channels share positions so the stereo image stays intact.
            t = np.arange(len(y))/SR
            depth = vibrato*35*np.clip((t-.18)/.3,0,1)
            rate = 5.2 + (note.seed % 11)*.035
            ratio = 2**(depth*np.sin(2*np.pi*rate*t)/1200)
            positions = np.cumsum(np.r_[0.,ratio[:-1]])
            indices = np.arange(len(y))
            y = np.interp(positions,indices,y,right=0) if y.ndim==1 else np.column_stack([np.interp(positions,indices,y[:,c],right=0) for c in range(2)])
        if finish is not None and any((bright,body,attack,tight,grit,width,vibrato)):
            y = finish(y)
        return y
