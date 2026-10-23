"""Patch instruments: build an instrument from modules and wires (a modular synth, as data).

    patch acid osc1=osc(wave=saw) env1=env(a=.005, d=.25, s=0, r=.08) f1=filter(cutoff=300, q=8) amp=vca out=out
    patch acid osc1>f1 f1>amp amp>out env1>amp.gain env1>f1.cutoff*3 vel>f1.cutoff*1.5
    inst bass=patch/acid(f1.cutoff=500)

A **module** is one block (an oscillator, an envelope, a filter, ...) with its own knobs. A **wire** connects
a source to a destination:

- `a>b`             audio: a's output is added into b's input (oscillator -> filter -> amp -> out); into an
                    oscillator it is FM: it bends the oscillator's phase by its `fm` depth;
- `a>b.knob*amount` modulation: a's output moves b's knob (envelope -> filter cutoff). How it moves depends
                    on the knob: frequencies move in octaves per unit, pitch in semitones, the rest linearly;
                    a VCA's `gain` is *replaced* by its modulation (env1>amp.gain: the envelope shapes the level).

Sources besides modules: `vel` (the note's velocity, 0..1), `key` (octaves above middle C), `gate` (1 while the
key is held), `rand` (a per-note random value in -1..1, from the note's seed). Wiring `vel` into a filter or a
shaper is how a patch makes velocity change the timbre, not just the loudness (instruments/base.py).

Every module knob becomes an instrument param named `<module>.<knob>` (`f1.cutoff`), so songs, presets and the
Studio's knobs set it like any other instrument's. A **macro** is one 0..1 knob that moves several:
`@bright(default=.5, f1.cutoff=200..4000, drive.drive=0..0.8)` (YAML: `macros: {bright: {default: .5, map:
{f1.cutoff: [200, 4000]}}}`); a knob a macro maps follows the macro. Patches live in a song (`patch` lines, YAML `patches:`) or
in the library (songmap/patches/<name>.yaml), and are used as `patch/<name>`.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
from dataclasses import dataclass

import numpy as np
from scipy.signal import lfilter

from .base import Instrument, Note, Param, ParamError
from .dsp import SR, mtof, n_samples, pan_mono, svf, t_axis
from .dsp.osc import pink, saw, sine, square, supersaw, triangle, white
from .dsp.env import adsr
from .dsp.physical import ks_string, modal

LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "patches")
SOURCES = ("vel", "key", "gate", "rand")


@dataclass(frozen=True)
class Knob:
    name: str
    default: float
    lo: float
    hi: float
    unit: str = ""
    curve: str = "lin"
    mod: str = "lin"           # how modulation moves it: lin (added), oct (octaves), semi (semitones), set (replaced)
    doc: str = ""
    choices: tuple = ()        # named values for an index knob (wave=saw)


@dataclass(frozen=True)
class ModuleType:
    name: str
    kind: str                  # osc noise env lfo filter shaper physical modal fx amp mix out (the diagram's colour)
    doc: str
    knobs: tuple
    audio_in: bool             # takes audio wires
    output: str = "audio"      # audio | control


WAVES = ("sine", "saw", "square", "triangle", "supersaw")
MODULES: dict[str, ModuleType] = {m.name: m for m in (
    ModuleType("osc", "osc", "an oscillator at the note's pitch: the raw tone", (
        Knob("wave", 1, 0, 4, "", "lin", "lin", "0 sine (pure), 1 saw (bright, all harmonics), 2 square (hollow, odd "
             "harmonics), 3 triangle (soft), 4 supersaw (7 detuned saws)", WAVES),
        Knob("octave", 0, -3, 3, "oct", "lin", "lin", "octaves above or below the note"),
        Knob("detune", 0, -24, 24, "st", "lin", "semi", "semitones off the note (modulate it for vibrato or a pitch drop)"),
        Knob("fine", 0, -50, 50, "cents", "lin", "lin", "fine tuning; two oscillators a few cents apart beat and widen"),
        Knob("pw", 0.5, 0.05, 0.95, "", "lin", "lin", "pulse width of the square (0.5 = square, thinner = nasal)"),
        Knob("fm", 1, 0, 12, "", "lin", "lin", "FM depth: how far audio wired into this oscillator bends its phase "
             "(frequency modulation: a sine modulating a sine at 1:1 to 14:1 is the electric piano and the bell)"),
        Knob("level", 0.8, 0, 1, "", "lin", "lin", "output level"),
    ), audio_in=True),
    ModuleType("noise", "noise", "noise: every frequency at once (breath, hiss, drum wires)", (
        Knob("color", 0, 0, 1, "", "lin", "lin", "0 white (hissy, bright) .. 1 pink (softer, like rain)"),
        Knob("level", 0.5, 0, 1, "", "lin", "lin", "output level"),
    ), audio_in=False),
    ModuleType("env", "env", "an envelope: a 0..1 shape over the note (attack, decay, sustain, release)", (
        Knob("a", 0.005, 0.0005, 5, "s", "log", "lin", "attack: time to rise to full"),
        Knob("d", 0.2, 0.001, 5, "s", "log", "lin", "decay: time to fall to the sustain level"),
        Knob("s", 0.7, 0, 1, "", "lin", "lin", "sustain: the level while the key is held"),
        Knob("r", 0.2, 0.001, 8, "s", "log", "lin", "release: time to fade after the key is let go"),
    ), audio_in=False, output="control"),
    ModuleType("lfo", "lfo", "a low-frequency oscillator: a slow wobble for vibrato, tremolo, filter sweeps", (
        Knob("rate", 5, 0.05, 30, "Hz", "log", "oct", "cycles per second"),
        Knob("shape", 0, 0, 4, "", "lin", "lin", "0 sine, 1 triangle, 2 square, 3 saw, 4 random steps",
             ("sine", "triangle", "square", "saw", "random")),
        Knob("depth", 1, 0, 1, "", "lin", "lin", "output amount (-depth..+depth)"),
        Knob("delay", 0, 0, 3, "s", "lin", "lin", "fade-in time (vibrato that arrives after the note starts)"),
    ), audio_in=False, output="control"),
    ModuleType("filter", "filter", "a resonant filter: removes highs (low-pass), lows (high-pass) or both (band-pass)", (
        Knob("mode", 0, 0, 2, "", "lin", "lin", "0 low-pass, 1 band-pass, 2 high-pass", ("lp", "bp", "hp")),
        Knob("cutoff", 2000, 20, 20000, "Hz", "log", "oct", "where it starts cutting; modulate it for a sweep"),
        Knob("q", 0.707, 0.3, 20, "", "log", "lin", "resonance: a peak at the cutoff (0.707 flat, 8+ squelchy)"),
        Knob("keytrack", 0.5, 0, 1, "", "lin", "lin", "how much the cutoff follows the note (1 = same tone in every octave)"),
    ), audio_in=True),
    ModuleType("shaper", "shaper", "a waveshaper: bends the wave to add harmonics (warmth, grit, fuzz)", (
        Knob("drive", 0.3, 0, 1, "", "lin", "lin", "tanh saturation: 0 clean .. 1 heavy"),
        Knob("fold", 0, 0, 1, "", "lin", "lin", "wavefolding: folds peaks back (metallic, west-coast)"),
        Knob("mix", 1, 0, 1, "", "lin", "lin", "dry .. shaped"),
    ), audio_in=True),
    ModuleType("string", "physical", "a plucked string (Karplus-Strong): a burst rings through a tuned delay loop", (
        Knob("t60", 2, 0.05, 12, "s", "log", "lin", "how long the string rings (to -60 dB)"),
        Knob("brightness", 0.8, 0.5, 1, "", "lin", "lin", "loop damping: 0.5 dull nylon .. 1 bright steel"),
        Knob("pick", 0.01, 0.001, 0.05, "s", "log", "lin", "length of the pluck burst (when nothing is wired in)"),
        Knob("level", 0.8, 0, 1, "", "lin", "lin", "output level"),
    ), audio_in=True),
    ModuleType("modal", "modal", "a resonator bank: decaying partials at fixed ratios (bells, bars, glass, plates)", (
        Knob("body", 0, 0, 3, "", "lin", "lin", "partial ratios: 0 bell, 1 bar (marimba), 2 glass, 3 plate",
             ("bell", "bar", "glass", "plate")),
        Knob("decay", 2.5, 0.05, 15, "s", "log", "lin", "how long the lowest partial rings"),
        Knob("damp", 0.6, 0, 2, "", "lin", "lin", "how much faster the high partials die"),
        Knob("bright", 0.6, 0, 1, "", "lin", "lin", "how loud the high partials are"),
        Knob("level", 0.6, 0, 1, "", "lin", "lin", "output level"),
    ), audio_in=False),
    ModuleType("comb", "fx", "a comb filter tuned to the note: resonant, metallic, pipe-like", (
        Knob("feedback", 0.7, 0, 0.98, "", "lin", "lin", "resonance of the loop"),
        Knob("tune", 0, -24, 24, "st", "lin", "semi", "semitones off the note"),
        Knob("mix", 0.6, 0, 1, "", "lin", "lin", "dry .. combed"),
    ), audio_in=True),
    ModuleType("delay", "fx", "an echo with feedback", (
        Knob("time", 0.25, 0.005, 2, "s", "log", "lin", "delay time"),
        Knob("feedback", 0.35, 0, 0.95, "", "lin", "lin", "how many repeats"),
        Knob("mix", 0.3, 0, 1, "", "lin", "lin", "dry .. echoes"),
    ), audio_in=True),
    ModuleType("vca", "amp", "an amplifier: sets the level; wire an envelope into `gain` to shape the note", (
        Knob("gain", 1, 0, 2, "", "lin", "set", "level (replaced by what is wired into it)"),
    ), audio_in=True),
    ModuleType("mix", "mix", "a mixer: everything wired in is added, then scaled", (
        Knob("level", 1, 0, 2, "", "lin", "lin", "output level"),
    ), audio_in=True),
    ModuleType("out", "out", "the patch's output: what you hear", (
        Knob("level", 0.8, 0, 2, "", "lin", "lin", "output level"),
        Knob("pan", 0, -1, 1, "", "lin", "lin", "left .. right"),
        Knob("tail", 0.3, 0, 10, "s", "lin", "lin", "extra time after the release (for echoes and long rings)"),
    ), audio_in=True),
)}

BODIES = {0: ([1, 2.0, 2.4, 3.0, 4.5, 5.4, 6.8], "bell"), 1: ([1, 3.93, 9.54, 17.6], "bar"),
          2: ([1, 2.32, 4.25, 6.63, 9.38], "glass"), 3: ([1, 1.59, 2.14, 2.3, 2.65, 2.92, 3.16, 3.5], "plate")}

_WIRE = re.compile(r"^\s*([A-Za-z_]\w*)\s*>\s*([A-Za-z_]\w*)(?:\.([A-Za-z_]\w*))?\s*(?:\*\s*(-?[\d.]+))?\s*$")


@dataclass
class Wire:
    src: str
    dst: str
    knob: str | None = None
    amount: float = 1.0

    def text(self) -> str:
        return f"{self.src}>{self.dst}" + (f".{self.knob}" if self.knob else "") + \
            (f"*{_num(self.amount)}" if self.knob and self.amount != 1 else "")


def _num(x: float) -> str:
    s = f"{round(float(x), 4):g}"
    return s[1:] if s.startswith("0.") else "-" + s[2:] if s.startswith("-0.") else s


def parse_wire(text: str) -> Wire:
    m = _WIRE.match(text)
    if not m:
        raise ParamError(f"wire '{text}' not understood; write a>b (audio) or a>b.knob*amount (modulation)")
    return Wire(m[1], m[2], m[3], float(m[4]) if m[4] else 1.0)


def knob_value(t: ModuleType, k: Knob, v) -> float:
    if isinstance(v, str) and k.choices:
        if v not in k.choices:
            raise ParamError(f"{t.name}.{k.name}: '{v}' is not one of {', '.join(k.choices)}")
        return float(k.choices.index(v))
    try:
        return float(v)
    except (TypeError, ValueError):
        raise ParamError(f"{t.name}.{k.name}: '{v}' is not a number"
                         + (f" or one of {', '.join(k.choices)}" if k.choices else "")) from None


def validate(spec: dict, name: str = "patch") -> dict:
    """Check a patch spec ({modules: {id: {type, knob: value}}, wires: ["a>b", ...]}) and return it normalized:
    knob values as numbers, wires as Wire objects, plus the evaluation order. Raises ParamError."""
    mods = spec.get("modules") or {}
    if not isinstance(mods, dict) or not mods:
        raise ParamError(f"{name}: a patch needs modules, e.g. osc1=osc(wave=saw) amp=vca out=out")
    norm: dict[str, dict] = {}
    for mid, m in mods.items():
        if mid in SOURCES:
            raise ParamError(f"{name}: '{mid}' is a built-in source ({', '.join(SOURCES)}); name the module differently")
        m = dict(m or {})
        typ = m.pop("type", None)
        if typ not in MODULES:
            raise ParamError(f"{name}.{mid}: unknown module type '{typ}'; "
                             + _dym(str(typ), MODULES) + f" (types: {', '.join(MODULES)})")
        t = MODULES[typ]
        knobs = {k.name: k for k in t.knobs}
        vals = {}
        for k, v in m.items():
            if k not in knobs:
                raise ParamError(f"{name}.{mid} ({typ}): unknown knob '{k}'; " + _dym(k, knobs)
                                 + f" (knobs: {', '.join(knobs)})")
            vals[k] = min(max(knob_value(t, knobs[k], v), knobs[k].lo), knobs[k].hi)
        norm[mid] = {"type": typ, **vals}
    if not any(m["type"] == "out" for m in norm.values()):
        raise ParamError(f"{name}: a patch needs an out module (out=out) and a wire into it")
    wires = []
    for w in spec.get("wires") or []:
        w = parse_wire(w) if isinstance(w, str) else Wire(**w)
        if w.src not in norm and w.src not in SOURCES:
            raise ParamError(f"{name}: wire {w.text()}: no module '{w.src}'; " + _dym(w.src, [*norm, *SOURCES]))
        if w.dst not in norm:
            raise ParamError(f"{name}: wire {w.text()}: no module '{w.dst}'; " + _dym(w.dst, norm))
        t = MODULES[norm[w.dst]["type"]]
        if w.knob is None and not t.audio_in:
            raise ParamError(f"{name}: wire {w.text()}: a {t.name} takes no audio input; wire into a knob "
                             f"({w.dst}.{t.knobs[0].name}) or into a filter, shaper, vca, mix or out")
        if w.knob is not None and w.knob not in {k.name for k in t.knobs}:
            raise ParamError(f"{name}: wire {w.text()}: {w.dst} ({t.name}) has no knob '{w.knob}'; "
                             + _dym(w.knob, [k.name for k in t.knobs]))
        if w.knob is None and w.src in norm and MODULES[norm[w.src]["type"]].output == "control":
            raise ParamError(f"{name}: wire {w.text()}: {w.src} is a control signal ({norm[w.src]['type']}); "
                             f"wire it into a knob, e.g. {w.src}>{w.dst}.{t.knobs[0].name}")
        wires.append(w)
    order = _order(norm, wires, name)
    macros = {}
    for mname, mac in (spec.get("macros") or {}).items():
        if not re.fullmatch(r"[A-Za-z_]\w*", str(mname)) or mname in norm or mname in SOURCES:
            raise ParamError(f"{name}: macro '{mname}' needs a plain name that isn't a module or a source")
        mac = dict(mac or {})
        targets = {}
        for tgt, rng_ in (mac.get("map") or {}).items():
            mid, _, kname = str(tgt).partition(".")
            if mid not in norm:
                raise ParamError(f"{name}: macro {mname}: no module '{mid}'; " + _dym(mid, norm))
            kn = {k.name: k for k in MODULES[norm[mid]["type"]].knobs}
            if kname not in kn:
                raise ParamError(f"{name}: macro {mname}: {mid} has no knob '{kname}'; " + _dym(kname, kn))
            lo, hi = (knob_value(MODULES[norm[mid]["type"]], kn[kname], x) for x in rng_)
            targets[f"{mid}.{kname}"] = [min(max(lo, kn[kname].lo), kn[kname].hi), min(max(hi, kn[kname].lo), kn[kname].hi)]
        if not targets:
            raise ParamError(f"{name}: macro {mname} moves nothing; map it to knobs, e.g. f1.cutoff=200..4000")
        macros[mname] = {"default": min(max(float(mac.get("default", 0.5)), 0.0), 1.0), "map": targets}
    return {"modules": norm, "wires": wires, "order": order, "macros": macros}


def _dym(x: str, options) -> str:
    close = difflib.get_close_matches(x, list(options), n=2)
    return f"did you mean {' or '.join(close)}?" if close else "check the spelling"


def _order(mods: dict, wires: list, name: str) -> list:
    deps = {m: {w.src for w in wires if w.dst == m and w.src in mods} for m in mods}
    order, done = [], set()
    while len(order) < len(mods):
        ready = [m for m in mods if m not in done and deps[m] <= done]
        if not ready:
            loop = [m for m in mods if m not in done]
            raise ParamError(f"{name}: the wires make a loop ({' > '.join(loop)}); a patch flows one way")
        for m in ready:
            order.append(m)
            done.add(m)
    return order


def to_text(name: str, spec: dict) -> list[str]:
    """The `.sm` lines for a patch: one line of modules, one of wires."""
    mods = []
    for mid, m in spec["modules"].items():
        t = MODULES[m["type"]]
        args = []
        for k in t.knobs:
            if k.name in m and abs(float(m[k.name]) - k.default) > 1e-9:
                v = m[k.name]
                args.append(f"{k.name}={k.choices[int(round(v))] if k.choices else _num(v)}")
        mods.append(f"{mid}={m['type']}" + (f"({', '.join(args)})" if args else ""))
    wires = [w.text() if isinstance(w, Wire) else parse_wire(w).text() for w in spec.get("wires") or []]
    rng = lambda x: f"{round(float(x), 4):g}"                  # noqa: E731  (0.2, not .2: ".03...2" would misread)
    macros = [f"@{m}(default={_num(mac['default'])}, " + ", ".join(f"{t}={rng(a)}..{rng(b)}" for t, (a, b) in mac["map"].items())
              + ")" for m, mac in (spec.get("macros") or {}).items()]
    return ([f"patch {name} " + " ".join(mods)] + ([f"patch {name} " + " ".join(wires)] if wires else [])
            + ([f"patch {name} " + " ".join(macros)] if macros else []))


def raw_spec(spec: dict) -> dict:
    """A validated spec back to plain data (YAML/JSON): wires as strings."""
    out = {"modules": {k: dict(v) for k, v in spec["modules"].items()},
           "wires": [w.text() if isinstance(w, Wire) else w for w in spec["wires"]]}
    if spec.get("macros"):
        out["macros"] = {m: {"default": mac["default"], "map": {t: list(r) for t, r in mac["map"].items()}}
                         for m, mac in spec["macros"].items()}
    return out


# ---------------------------------------------------------------------------------------------- library
def library() -> dict[str, dict]:
    out = {}
    if os.path.isdir(LIB_DIR):
        import yaml
        for f in sorted(os.listdir(LIB_DIR)):
            if f.endswith(".yaml"):
                with open(os.path.join(LIB_DIR, f), encoding="utf-8") as fh:
                    out[f[:-5]] = yaml.safe_load(fh) or {}
    return out


# ---------------------------------------------------------------------------------------------- the instrument
def build(name: str, spec: dict, **params) -> Instrument:
    """An Instrument for a patch spec; params are `<module>.<knob>` overrides."""
    v = validate(spec, f"patch/{name}")
    knobs = []
    for mid in v["modules"]:
        m = v["modules"][mid]
        for k in MODULES[m["type"]].knobs:
            d = float(m.get(k.name, k.default))
            doc = f"{mid} ({m['type']}): {k.doc}"
            knobs.append(Param(f"{mid}.{k.name}", d, k.lo, k.hi, k.unit, k.curve, mid, doc))
    for mname, mac in v["macros"].items():
        moves = ", ".join(f"{t} {_num(a)}..{_num(b)}" for t, (a, b) in mac["map"].items())
        knobs.insert(0, Param(mname, mac["default"], 0, 1, "", "lin", "macros", f"macro: moves {moves}"))
    digest = hashlib.sha1(json.dumps(raw_spec(v), sort_keys=True).encode()).hexdigest()[:10]
    cls = type("Patch_" + re.sub(r"\W", "_", name), (PatchInstrument,),
               {"name": f"patch/{name}#{digest}", "PARAMS": tuple(knobs), "SPEC": v, "family": "synth"})
    return cls(**params)


class PatchInstrument(Instrument):
    name = "patch"
    family = "synth"
    SPEC: dict = {}

    def tail(self, note: Note) -> float:
        rel = max((self.p[f"{m}.r"] for m, x in self.SPEC["modules"].items() if x["type"] == "env"), default=0.05)
        out = next(m for m, x in self.SPEC["modules"].items() if x["type"] == "out")
        return rel + self.p[f"{out}.tail"]

    def render(self, note: Note) -> np.ndarray:
        spec = self.SPEC
        n = max(n_samples(note.gate + self.tail(note)), 16)
        rng = self.rng(note)
        t = t_axis(n)
        gate_n = min(n, n_samples(note.gate))
        src = {"vel": np.full(n, note.vel), "key": np.full(n, (note.pitch - 60) / 12),
               "gate": np.concatenate([np.ones(gate_n), np.zeros(n - gate_n)]), "rand": np.full(n, rng.uniform(-1, 1))}
        outs: dict[str, np.ndarray] = {}
        for mid in spec["order"]:
            typ = spec["modules"][mid]["type"]
            mt = MODULES[typ]
            ins = [w for w in spec["wires"] if w.dst == mid]
            audio = sum((outs[w.src] if w.src in outs else src[w.src]) for w in ins if w.knob is None) \
                if any(w.knob is None for w in ins) else None
            k = {}
            for kn in mt.knobs:
                base = self._macro(note, f"{mid}.{kn.name}", kn)
                mods = [(outs[w.src] if w.src in outs else src[w.src]) * w.amount for w in ins if w.knob == kn.name]
                if not mods:
                    k[kn.name] = base
                    continue
                m = sum(mods)
                if kn.mod == "oct":
                    k[kn.name] = base * 2.0 ** m
                elif kn.mod == "set":
                    k[kn.name] = m
                else:                                      # lin and semi: added
                    k[kn.name] = base + m
            outs[mid] = self._module(typ, k, audio, note, n, t, rng, gate_n)
        out_id = next(m for m in spec["order"] if spec["modules"][m]["type"] == "out")
        y = outs[out_id]
        if not np.all(np.isfinite(y)):
            y = np.nan_to_num(y)
        pan = float(np.clip(self.p_(note, f"{out_id}.pan"), -1, 1))
        fade = min(n, n_samples(0.004))
        y = y.copy()
        y[-fade:] *= np.linspace(1, 0, fade)
        return pan_mono(y, pan) if abs(pan) > 1e-6 else y

    def _macro(self, note: Note, key: str, kn: Knob) -> float:
        """A knob's value: set by the macro that maps it (the last one, if several), else its own param."""
        for mname, mac in reversed(list(self.SPEC.get("macros", {}).items())):
            if key in mac["map"]:
                a, b = mac["map"][key]
                x = float(self.p_(note, mname))
                if kn.curve == "log" and a > 0 and b > 0:
                    return float(a * (b / a) ** x)
                return a + (b - a) * x
        return self.p_(note, key)

    # one module, one note: knob values may be arrays (modulated) or numbers
    def _module(self, typ, k, audio, note, n, t, rng, gate_n):
        def arr(x):
            return np.broadcast_to(np.asarray(x, float), (n,)).copy()

        if typ == "osc":
            f = mtof(note.pitch + 12 * np.round(k["octave"]) + np.asarray(k["detune"]) + np.asarray(k["fine"]) / 100)
            f = np.clip(arr(f), 1.0, 0.45 * SR)
            w = int(round(float(np.mean(k["wave"]))))
            ph0 = rng.random()
            if audio is not None:                          # FM: the wired-in signal bends the phase
                ph = ph0 + np.cumsum(f) / SR + arr(k["fm"]) * np.asarray(audio, float) / (2 * np.pi)
                frac = ph % 1.0
                y = (np.sin(2 * np.pi * ph) if w in (0, 4) else 2 * frac - 1 if w == 1 else
                     np.where(frac < np.clip(arr(k["pw"]), 0.05, 0.95), 1.0, -1.0) if w == 2 else 2 * np.abs(2 * frac - 1) - 1)
                return y * arr(k["level"])
            y = (sine(f, n, ph0) if w == 0 else saw(f, n, ph0) if w == 1 else
                 square(f, n, np.clip(arr(k["pw"]), 0.05, 0.95), ph0) if w == 2 else triangle(f, n, ph0) if w == 3 else
                 supersaw(f, n))
            if y.ndim == 2:                                # supersaw is stereo; a patch is mono until `out`
                y = y.mean(1)
            return y * arr(k["level"])
        if typ == "noise":
            c = float(np.mean(k["color"]))
            y = (1 - c) * white(n, rng) * 0.5 + c * pink(n, rng)
            return y * arr(k["level"])
        if typ == "env":
            a, d, s, r = (float(np.mean(k[x])) for x in ("a", "d", "s", "r"))
            return adsr(n, a, d, min(max(s, 0), 1), r, gate=gate_n / SR)
        if typ == "lfo":
            rate = arr(k["rate"])
            ph = np.cumsum(rate) / SR + rng.random()
            shape = int(round(float(np.mean(k["shape"]))))
            if shape == 0:
                y = np.sin(2 * np.pi * ph)
            elif shape == 1:
                y = 2 * np.abs(2 * (ph % 1) - 1) - 1
            elif shape == 2:
                y = np.where((ph % 1) < 0.5, 1.0, -1.0)
            elif shape == 3:
                y = 2 * (ph % 1) - 1
            else:
                steps = rng.uniform(-1, 1, int(ph[-1]) + 2)
                y = steps[ph.astype(int)]
            dl = float(np.mean(k["delay"]))
            if dl > 0:
                y = y * np.clip(t / dl, 0, 1)
            return y * arr(k["depth"])
        x = np.zeros(n) if audio is None else np.asarray(audio, float)
        if typ == "filter":
            kt = float(np.mean(k["keytrack"]))
            fc = np.clip(arr(k["cutoff"]) * 2.0 ** (kt * (note.pitch - 60) / 12), 10, 0.45 * SR)
            mode = ("lp", "bp", "hp")[int(round(float(np.mean(k["mode"]))))]
            return svf(x, fc, float(np.mean(k["q"])), mode)
        if typ == "shaper":
            drv = arr(k["drive"])
            g = 1 + 24 * drv ** 2
            y = np.tanh(x * g) / np.tanh(g)
            fold = arr(k["fold"])
            if np.any(fold > 0):
                y = (1 - fold) * y + fold * np.sin(x * (1 + 6 * fold) * np.pi / 2)
            mix = arr(k["mix"])
            return x * (1 - mix) + y * mix
        if typ == "string":
            if audio is None:
                pick = n_samples(float(np.mean(k["pick"])))
                exc = np.zeros(n)
                exc[:pick] = rng.uniform(-1, 1, pick) * np.hanning(pick * 2)[pick:] if pick > 1 else 1.0
            else:
                exc = x
            y = ks_string(float(mtof(note.pitch)), n, exc, float(np.mean(k["t60"])), float(np.mean(k["brightness"])))
            return y * arr(k["level"])
        if typ == "modal":
            ratios = BODIES[int(round(float(np.mean(k["body"]))))][0]
            f0 = float(mtof(note.pitch))
            dec, damp, br = (float(np.mean(k[x])) for x in ("decay", "damp", "bright"))
            amps = [br ** i if i else 1.0 for i in range(len(ratios))]
            y = modal([f0 * r for r in ratios], amps, [dec / r ** damp for r in ratios], n, rng.uniform(0, 6.28, len(ratios)))
            return y / max(1.0, sum(amps) * 0.5) * arr(k["level"])
        if typ == "comb":
            f = float(mtof(note.pitch + float(np.mean(k["tune"]))))
            D = max(1, int(round(SR / f)))
            fb = float(np.clip(np.mean(k["feedback"]), 0, 0.98))
            a = np.zeros(D + 1)
            a[0], a[D] = 1.0, -fb
            y = lfilter([1 - fb], a, x)
            mix = arr(k["mix"])
            return x * (1 - mix) + y * mix
        if typ == "delay":
            D = max(1, n_samples(float(np.mean(k["time"]))))
            fb = float(np.clip(np.mean(k["feedback"]), 0, 0.95))
            b = np.zeros(D + 1)
            b[D] = 1.0
            a = np.zeros(D + 1)
            a[0], a[D] = 1.0, -fb
            wet = lfilter(b, a, x)
            mix = arr(k["mix"])
            return x * (1 - mix) + wet * mix
        if typ == "vca":
            return x * arr(k["gain"])
        if typ == "mix":
            return x * arr(k["level"])
        if typ == "out":
            return x * arr(k["level"])
        raise ParamError(f"unknown module type {typ}")


def describe() -> str:
    """One line per module type, for an LLM's context."""
    return "\n".join(f"{m.name} ({m.kind}): " + " ".join(f"{k.name}={k.choices[int(k.default)] if k.choices else f'{k.default:g}'}"
                                                         for k in m.knobs) + f"  — {m.doc}" for m in MODULES.values())
