"""Insert effects: schema'd units in a part's (or the master's) signal chain, before the fader.

    inserts lead eq(high=2, hp=120) comp(threshold=-20, ratio=3) | bass drive(amount=.3) | master eq(low=1)

Each unit declares its knobs with the instruments' `Param` schema (name, default, range, unit, curve,
group, doc), so the parser validates them, the Studio draws them and `describe()` lists them. A unit
processes a stereo (n, 2) buffer and returns one; `mix` (where a unit has it) blends dry and wet.
Every unit takes `on=0` to bypass it without losing its settings.
"""
from __future__ import annotations

import difflib

import numpy as np

from ..instruments.base import Param
from ..instruments.dsp import SR, as_stereo, eq, n_samples, pingpong_delay, svf
from .fx import compressor, convolve, reverb_ir

ON = Param("on", 1, 0, 1, "", "lin", "main", "1 = active, 0 = bypassed (settings kept)")


class Unit:
    name = "unit"
    doc = ""
    PARAMS: tuple[Param, ...] = ()

    @classmethod
    def params(cls) -> tuple[Param, ...]:
        return (*cls.PARAMS, ON)

    @classmethod
    def schema(cls) -> dict:
        from dataclasses import asdict
        return {"name": cls.name, "doc": cls.doc, "params": [asdict(q) for q in cls.params()]}

    def __init__(self, **values):
        spec = {q.name: q for q in self.params()}
        self.p = {q.name: q.default for q in self.params()}
        for k, v in values.items():
            if k not in spec:
                close = difflib.get_close_matches(k, spec, n=2)
                raise ValueError(f"{self.name}: unknown param '{k}'" + (f"; did you mean {', '.join(close)}?" if close
                                 else f"; valid: {', '.join(spec)}"))
            self.p[k] = spec[k].clamp(float(v))

    def __call__(self, x: np.ndarray, ctx: dict) -> np.ndarray:
        x = as_stereo(x)
        if self.p["on"] < 0.5 or not len(x):
            return x
        return as_stereo(self.process(x, ctx))

    def process(self, x: np.ndarray, ctx: dict) -> np.ndarray:
        raise NotImplementedError


def _blend(dry, wet, mix):
    return dry * (1 - mix) + wet * mix if mix < 1 else wet


UNITS: dict[str, type[Unit]] = {}


def unit(cls):
    UNITS[cls.name] = cls
    return cls


@unit
class EQ(Unit):
    name, doc = "eq", "high-pass, low shelf, mid bell, high shelf, low-pass"
    PARAMS = (
        Param("hp", 20, 20, 1000, "Hz", "log", "cut", "high-pass (20 = off)"),
        Param("low", 0, -18, 18, "dB", "lin", "low", "low shelf gain"),
        Param("low_freq", 200, 40, 800, "Hz", "log", "low", "low shelf corner"),
        Param("mid", 0, -18, 18, "dB", "lin", "mid", "bell gain"),
        Param("mid_freq", 1000, 150, 8000, "Hz", "log", "mid", "bell center"),
        Param("mid_q", 1.0, 0.3, 6, "", "log", "mid", "bell width (higher = narrower)"),
        Param("high", 0, -18, 18, "dB", "lin", "high", "high shelf gain"),
        Param("high_freq", 6000, 1500, 16000, "Hz", "log", "high", "high shelf corner"),
        Param("lp", 20000, 1000, 20000, "Hz", "log", "cut", "low-pass (20000 = off)"),
    )

    def process(self, x, ctx):
        p = self.p
        if p["hp"] > 21:
            x = svf(x, p["hp"], 0.707, "hp")
        if abs(p["low"]) > 1e-3:
            x = eq(x, "lowshelf", p["low_freq"], p["low"])
        if abs(p["mid"]) > 1e-3:
            x = eq(x, "peak", p["mid_freq"], p["mid"], p["mid_q"])
        if abs(p["high"]) > 1e-3:
            x = eq(x, "highshelf", p["high_freq"], p["high"])
        if p["lp"] < 19900:
            x = svf(x, p["lp"], 0.707, "lp")
        return x


@unit
class Comp(Unit):
    name, doc = "comp", "compressor (stereo-linked); `sc` ducks it from the kick"
    PARAMS = (
        Param("threshold", -18, -60, 0, "dB", "lin", "main"),
        Param("ratio", 3, 1, 20, ":1", "log", "main"),
        Param("attack", 0.01, 0.0005, 0.2, "s", "log", "time"),
        Param("release", 0.15, 0.01, 1.5, "s", "log", "time"),
        Param("knee", 6, 0, 18, "dB", "lin", "main"),
        Param("makeup", 0, -12, 24, "dB", "lin", "out"),
        Param("mix", 1, 0, 1, "", "lin", "out", "parallel compression: 0 dry .. 1 wet"),
    )

    def process(self, x, ctx):
        p = self.p
        wet = compressor(x, p["threshold"], p["ratio"], p["attack"], p["release"], p["knee"], p["makeup"])
        return _blend(x, wet, p["mix"])


@unit
class Drive(Unit):
    name, doc = "drive", "tanh saturation with a tone low-pass"
    PARAMS = (
        Param("amount", 0.3, 0, 1, "", "lin", "main", "0 clean .. 1 heavy"),
        Param("tone", 12000, 500, 20000, "Hz", "log", "main", "low-pass after the saturation"),
        Param("output", 0, -24, 12, "dB", "lin", "out"),
        Param("mix", 1, 0, 1, "", "lin", "out"),
    )

    def process(self, x, ctx):
        p = self.p
        k = 1 + 24 * p["amount"] ** 2
        peak = max(float(np.max(np.abs(x))), 1e-9)          # drive relative to the part's level: peak stays put
        wet = np.tanh(x * k / peak) / np.tanh(k) * peak
        if p["tone"] < 19900:
            wet = svf(wet, p["tone"], 0.707, "lp")
        rms_dry, rms_wet = float(np.sqrt(np.mean(x ** 2))), float(np.sqrt(np.mean(wet ** 2)))
        if rms_wet > 1e-12:                                # same loudness as the dry part: drive changes tone
            wet *= rms_dry / rms_wet
        return _blend(x, wet, p["mix"]) * 10 ** (p["output"] / 20)


@unit
class Filter(Unit):
    name, doc = "filter", "resonant state-variable filter (mode 0 low-pass, 1 band-pass, 2 high-pass)"
    PARAMS = (
        Param("mode", 0, 0, 2, "", "lin", "main", "0 low-pass, 1 band-pass, 2 high-pass"),
        Param("cutoff", 2000, 20, 20000, "Hz", "log", "main"),
        Param("q", 0.707, 0.3, 12, "", "log", "main", "resonance (0.707 flat)"),
        Param("mix", 1, 0, 1, "", "lin", "out"),
    )

    def process(self, x, ctx):
        p = self.p
        wet = svf(x, p["cutoff"], p["q"], ("lp", "bp", "hp")[int(round(p["mode"]))])
        return _blend(x, wet, p["mix"])


@unit
class Delay(Unit):
    name, doc = "delay", "ping-pong delay, synced to the tempo"
    PARAMS = (
        Param("time", 0.75, 0.125, 4, "beats", "log", "main", "delay time in beats (0.75 = dotted eighth)"),
        Param("feedback", 0.35, 0, 0.95, "", "lin", "main"),
        Param("damp", 4500, 500, 16000, "Hz", "log", "tone", "each repeat loses the top above this"),
        Param("mix", 0.25, 0, 1, "", "lin", "out"),
    )

    def process(self, x, ctx):
        p = self.p
        sec = p["time"] * 60.0 / float(ctx.get("tempo", 120))
        return x + pingpong_delay(x, sec, p["feedback"], p["damp"]) * p["mix"]


@unit
class Chorus(Unit):
    name, doc = "chorus", "two modulated voices, spread left and right"
    PARAMS = (
        Param("rate", 0.6, 0.05, 6, "Hz", "log", "main"),
        Param("depth", 4, 0.3, 15, "ms", "log", "main"),
        Param("delay", 12, 3, 30, "ms", "lin", "main", "center delay"),
        Param("mix", 0.4, 0, 1, "", "lin", "out"),
    )

    def process(self, x, ctx):
        p = self.p
        n = len(x)
        t = np.arange(n) / SR
        out = np.empty_like(x)
        for c in range(2):
            lfo = np.sin(2 * np.pi * p["rate"] * t + c * np.pi / 2)
            d = (p["delay"] + p["depth"] * lfo) * SR / 1000
            idx = np.arange(n) - d
            out[:, c] = np.interp(idx, np.arange(n), x[:, c], left=0.0)
        return _blend(x, out, p["mix"])


@unit
class Reverb(Unit):
    name, doc = "reverb", "an insert reverb (the hall/room returns are shared; this one is the part's own)"
    PARAMS = (
        Param("seconds", 1.6, 0.2, 10, "s", "log", "main", "decay time"),
        Param("predelay", 0.012, 0, 0.2, "s", "lin", "main"),
        Param("damping", 0.5, 0, 1, "", "lin", "tone"),
        Param("mix", 0.25, 0, 1, "", "lin", "out"),
    )

    def process(self, x, ctx):
        p = self.p
        ir = reverb_ir(p["seconds"], predelay=p["predelay"], damping=p["damping"], seed=int(ctx.get("seed", 1)) % 2**31)
        wet = convolve(x, ir)[:len(x)]
        return x * (1 - p["mix"]) + wet * p["mix"]


@unit
class Width(Unit):
    name, doc = "width", "stereo width (mid/side): 0 mono, 1 as is, 2 wide"
    PARAMS = (Param("amount", 1.0, 0, 2, "", "lin", "main"),)

    def process(self, x, ctx):
        mid, side = (x[:, 0] + x[:, 1]) / 2, (x[:, 0] - x[:, 1]) / 2 * self.p["amount"]
        return np.stack([mid + side, mid - side], 1)


@unit
class Gain(Unit):
    name, doc = "gain", "trim"
    PARAMS = (Param("db", 0, -24, 24, "dB", "lin", "main"),)

    def process(self, x, ctx):
        return x * 10 ** (self.p["db"] / 20)


@unit
class Tremolo(Unit):
    name, doc = "tremolo", "amplitude modulation synced to the tempo (stereo phase for auto-pan)"
    PARAMS = (
        Param("rate", 0.5, 0.0625, 4, "beats", "log", "main", "one cycle every N beats"),
        Param("depth", 0.4, 0, 1, "", "lin", "main"),
        Param("stereo", 0, 0, 1, "", "lin", "main", "0 tremolo .. 1 auto-pan"),
    )

    def process(self, x, ctx):
        p = self.p
        hz = float(ctx.get("tempo", 120)) / 60.0 / p["rate"]
        ph = 2 * np.pi * hz * np.arange(len(x)) / SR
        l = 1 - p["depth"] * (0.5 + 0.5 * np.sin(ph))
        r = 1 - p["depth"] * (0.5 + 0.5 * np.sin(ph + np.pi * p["stereo"]))
        return x * np.stack([l, r], 1)


ALIASES = {"compressor": "comp", "saturate": "drive", "lowpass": "filter", "trem": "tremolo"}


def make(spec: dict) -> Unit:
    """{fx: 'eq', high: 2} -> an EQ unit."""
    name = str(spec.get("fx", ""))
    name = ALIASES.get(name, name)
    if name not in UNITS:
        close = difflib.get_close_matches(name, UNITS, n=2)
        raise ValueError(f"unknown insert '{name}'" + (f"; did you mean {', '.join(close)}?" if close
                                                        else f"; valid: {', '.join(UNITS)}"))
    return UNITS[name](**{k: v for k, v in spec.items() if k != "fx"})


def apply_chain(x: np.ndarray, chain: list[dict], ctx: dict) -> np.ndarray:
    for spec in chain or ():
        x = make(spec)(x, ctx)
    return x


def describe() -> str:
    """One line per unit, for an LLM's context."""
    return "\n".join(f"{c.name}: " + " ".join(f"{q.name}={q.default:g}{q.unit}" for q in c.PARAMS) + f"  ({c.doc})"
                     for c in UNITS.values())
