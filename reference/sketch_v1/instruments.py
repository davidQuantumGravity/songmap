"""Instrument model + a starter suite (reference sketch, v1).

Every instrument:
- declares its knobs as `PARAMS` (name, default, range, unit, knob curve, group, doc).
  The GUI builds knobs from this schema, the parser validates song-map overrides
  against it, and `describe()` prints it compactly for an LLM's context.
- renders ONE note: `render(Note) -> mono (n,) or stereo (n, 2)` array, starting at
  the note-on. The engine places it on the timeline, so instruments never see bars.
- maps velocity to TIMBRE, not just loudness (brighter, longer, more click/noise
  when hit harder). That, plus per-hit variation (`rr`), is most of what makes a
  synthesized part sound played rather than sequenced.
"""
from __future__ import annotations

import difflib
import zlib
from dataclasses import asdict, dataclass, field

import numpy as np

from dsp import (SR, adsr, ad, drive, eq, ks_string, mtof, n_samples, pan_mono, phase,
                 saw, sine, square, svf, t60_env, t_axis, white)


# ----------------------------------------------------------------------------
# schema
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class Param:
    name: str
    default: float
    lo: float
    hi: float
    unit: str = ""
    curve: str = "lin"      # knob mapping: 'lin' or 'log' (log for Hz and seconds)
    group: str = "main"     # GUI panel grouping
    doc: str = ""

    def clamp(self, v: float) -> float:
        return float(min(max(v, self.lo), self.hi))


@dataclass
class Note:
    pitch: float = 60.0                 # MIDI number; fractional = microtonal
    vel: float = 0.7                    # 0..1 (MIDI velocity / 127)
    gate: float = 0.5                   # seconds the key is held (after articulation)
    seed: int = 0                       # per-note seed: round-robin + humanize variation
    glide_from: float | None = None     # previous pitch when slurred (mono instruments glide)
    params: dict = field(default_factory=dict)  # per-note automation snapshot


REGISTRY: dict[str, type["Instrument"]] = {}


def register(cls):
    REGISTRY[cls.name] = cls
    return cls


class ParamError(ValueError):
    pass


class Instrument:
    name = "instrument"
    family = "synth"        # drum | bass | keys | synth | string | fx
    mono = False            # mono instruments glide between slurred notes
    PARAMS: tuple[Param, ...] = ()

    def __init__(self, **values):
        self.spec = {q.name: q for q in self.PARAMS}
        self.p = {q.name: q.default for q in self.PARAMS}
        self.set(**values)

    def set(self, **values):
        for k, v in values.items():
            if k not in self.spec:
                close = difflib.get_close_matches(k, self.spec, n=3)
                hint = f" did you mean {', '.join(close)}?" if close else ""
                raise ParamError(f"{self.name}: unknown param '{k}'.{hint} "
                                 f"valid: {', '.join(self.spec)}")
            self.p[k] = self.spec[k].clamp(v)
        return self

    @classmethod
    def schema(cls) -> dict:
        return {"name": cls.name, "family": cls.family, "mono": cls.mono,
                "params": [asdict(q) for q in cls.PARAMS]}

    # --- helpers shared by all instruments ---------------------------------
    def rng(self, note: Note) -> np.random.Generator:
        return np.random.default_rng(zlib.crc32(self.name.encode()) ^ (note.seed * 2654435761 % 2**32))

    def vary(self, rng, value: float, rel: float) -> float:
        """Round-robin variation: value * (1 + rel * rr * N(0,1))."""
        return value * (1.0 + rel * self.p.get("rr", 0.0) * rng.standard_normal())

    def vel_gain(self, v: float) -> float:
        return v ** self.p.get("vel_curve", 1.5)

    @staticmethod
    def vel_oct(base: float, v: float, octaves: float, ref: float = 0.7) -> float:
        """Velocity -> frequency scaling: `octaves` per unit of velocity around ref."""
        return base * 2.0 ** (octaves * (v - ref))

    def tail(self, note: Note) -> float:
        return self.p.get("release", 0.2)

    def p_(self, note: Note, k: str) -> float:
        """Param value with per-note automation override."""
        return note.params.get(k, self.p[k])

    def render(self, note: Note) -> np.ndarray:
        raise NotImplementedError


def make(name: str, **params) -> Instrument:
    if name not in REGISTRY:
        close = difflib.get_close_matches(name, REGISTRY, n=3)
        raise ParamError(f"unknown instrument '{name}'. did you mean {close}? valid: {sorted(REGISTRY)}")
    return REGISTRY[name](**params)


def describe() -> str:
    """One line per instrument, for an LLM's context window (~40 tokens each)."""
    lines = []
    for cls in REGISTRY.values():
        ps = " ".join(f"{q.name}={q.default:g}{q.unit}" for q in cls.PARAMS)
        lines.append(f"{cls.name} ({cls.family}{', mono' if cls.mono else ''}): {ps}")
    return "\n".join(lines)


def smooth_noise(n: int, rate_hz: float, rng, sr: int = SR) -> np.ndarray:
    """Slowly wandering control signal in about [-1, 1] (analog drift, breath, bow pressure)."""
    k = max(2, int(n / sr * rate_hz) + 2)
    pts = rng.standard_normal(k)
    return np.interp(np.linspace(0, k - 1, n), np.arange(k), pts) / 1.5


def glide_freq(note: Note, n: int, glide: float, sr: int = SR) -> np.ndarray:
    f1 = float(mtof(note.pitch))
    if note.glide_from is None or glide <= 0:
        return np.full(n, f1)
    f0 = float(mtof(note.glide_from))
    k = np.clip(t_axis(n, sr) / glide, 0, 1)
    return f0 * (f1 / f0) ** (1 - (1 - k) ** 2)   # fast-then-settle, like a finger slide


V = "velocity"   # common group names
P = "pitch"
A = "amp"
F = "filter"
T = "tone"
X = "variation"


def common_vel(curve=1.5):
    return (Param("vel_curve", curve, 0.3, 3.0, "", "lin", V, "loudness curve: gain = vel**curve"),)


RR = Param("rr", 0.3, 0.0, 1.0, "", "lin", X, "per-hit random variation (round-robin feel)")


# ----------------------------------------------------------------------------
# drums
# ----------------------------------------------------------------------------
@register
class Kick(Instrument):
    name, family = "kick", "drum"
    PARAMS = (
        Param("tune", 48, 30, 90, "Hz", "log", P, "resting pitch of the body"),
        Param("sweep", 30, 0, 48, "st", "lin", P, "start pitch above tune"),
        Param("sweep_time", 0.035, 0.005, 0.2, "s", "log", P),
        Param("decay", 0.45, 0.05, 2.0, "s", "log", A, "t60 of the body"),
        Param("sub", 0.0, 0, 1, "", "lin", A, "extra pure-sine tail (808 boom)"),
        Param("click", 0.3, 0, 1, "", "lin", T, "beater click level"),
        Param("click_tone", 3500, 1000, 9000, "Hz", "log", T),
        Param("drive", 1.6, 1, 8, "x", "log", T),
        Param("vel_sweep", 0.5, 0, 1, "", "lin", V, "harder hits sweep further"),
        Param("vel_click", 0.8, 0, 1, "", "lin", V, "harder hits click more"),
        *common_vel(1.4), RR,
    )

    def tail(self, note):
        return self.p["decay"] * 1.3

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        n = n_samples(self.tail(note))
        t = t_axis(n)
        sweep = p["sweep"] * (1 - p["vel_sweep"] + p["vel_sweep"] * v) * self.vary(rng, 1, 0.05)
        f = p["tune"] * 2 ** (sweep / 12 * np.exp(-t / p["sweep_time"]))
        x = sine(f, n) * t60_env(n, self.vary(rng, p["decay"], 0.06))
        if p["sub"]:
            x += p["sub"] * sine(p["tune"], n) * t60_env(n, p["decay"] * 1.6) * np.clip(t / 0.01, 0, 1)
        ck = p["click"] * (1 - p["vel_click"] + p["vel_click"] * v)
        x += ck * svf(white(n, rng), p["click_tone"], 1.0, "bp") * t60_env(n, 0.012)
        return drive(x, p["drive"]) * self.vel_gain(v)


@register
class Snare(Instrument):
    name, family = "snare", "drum"
    PARAMS = (
        Param("tone", 185, 120, 320, "Hz", "log", P, "shell fundamental"),
        Param("tone_decay", 0.12, 0.02, 0.5, "s", "log", A),
        Param("tone_mix", 0.45, 0, 1, "", "lin", T, "shell vs. wires"),
        Param("noise_decay", 0.22, 0.04, 0.8, "s", "log", A, "wire rattle t60"),
        Param("noise_hp", 1500, 300, 5000, "Hz", "log", F),
        Param("noise_lp", 9000, 2000, 18000, "Hz", "log", F),
        Param("snap", 0.4, 0, 1, "", "lin", T, "stick transient"),
        Param("drive", 1.3, 1, 6, "x", "log", T),
        Param("vel_bright", 1.5, 0, 4, "oct", "lin", V, "ghost notes darker, accents brighter"),
        *common_vel(1.6), RR,
    )

    def tail(self, note):
        return max(self.p["noise_decay"], self.p["tone_decay"]) * 1.3

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        n = n_samples(self.tail(note))
        t = t_axis(n)
        f = self.vary(rng, p["tone"], 0.01) * (1 + 0.4 * np.exp(-t / 0.008))
        shell = (sine(f, n) + 0.45 * sine(f * 1.59, n)) * t60_env(n, p["tone_decay"])
        nd = p["noise_decay"] * (0.6 + 0.4 * v) * self.vary(rng, 1, 0.08)
        wires = svf(white(n, rng), p["noise_hp"], 0.7, "hp")
        wires = svf(wires, self.vel_oct(p["noise_lp"], v, p["vel_bright"]), 0.7, "lp") * t60_env(n, nd)
        snap = p["snap"] * v * svf(white(n, rng), 5000, 0.8, "bp") * t60_env(n, 0.006)
        x = p["tone_mix"] * shell + (1 - p["tone_mix"]) * 0.9 * wires + snap
        return drive(x, p["drive"]) * self.vel_gain(v)


@register
class Clap(Instrument):
    name, family = "clap", "drum"
    PARAMS = (
        Param("bursts", 4, 1, 8, "", "lin", T, "number of hand claps in the cluster"),
        Param("spread", 0.011, 0.003, 0.03, "s", "log", T, "gap between bursts"),
        Param("decay", 0.14, 0.03, 0.8, "s", "log", A, "tail of the last burst"),
        Param("center", 1400, 600, 4000, "Hz", "log", F),
        Param("q", 1.2, 0.5, 4, "", "lin", F),
        Param("vel_bright", 1.0, 0, 3, "oct", "lin", V),
        *common_vel(1.5), RR,
    )

    def tail(self, note):
        return self.p["spread"] * self.p["bursts"] + self.p["decay"] * 1.3

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        n = n_samples(self.tail(note))
        t = t_axis(n)
        e = np.zeros(n)
        nb = int(round(p["bursts"]))
        off = 0.0
        for k in range(nb):
            i = n_samples(off)
            last = k == nb - 1
            e[i:] += np.exp(-t[: n - i] / (p["decay"] / 6.9 if last else 0.0025))
            off += p["spread"] * (1 + 0.6 * p["rr"] * (rng.random() - 0.5))
        x = svf(white(n, rng), self.vel_oct(p["center"], v, p["vel_bright"]), p["q"], "bp")
        return x * e * 1.4 * self.vel_gain(v)


@register
class Hat(Instrument):
    """808-style: six detuned square waves (metal) + noise, band-passed high."""
    name, family = "hat", "drum"
    RATIOS = (205.3, 304.4, 369.6, 522.7, 540.0, 800.0)
    PARAMS = (
        Param("tune", 1.0, 0.5, 2.0, "x", "log", P, "scales the metallic partials"),
        Param("decay", 0.05, 0.015, 1.2, "s", "log", A, "0.05 closed, 0.4+ open"),
        Param("metal", 0.6, 0, 1, "", "lin", T, "square-wave metal vs. noise"),
        Param("hp", 7000, 3000, 12000, "Hz", "log", F),
        Param("color", 10000, 5000, 16000, "Hz", "log", F, "band-pass center"),
        Param("vel_decay", 0.5, 0, 1, "", "lin", V, "harder hits ring longer"),
        Param("vel_bright", 1.0, 0, 3, "oct", "lin", V),
        *common_vel(1.4), RR,
    )

    def tail(self, note):
        return self.p["decay"] * 1.5

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        n = n_samples(self.tail(note))
        metal = sum(square(r * p["tune"] * self.vary(rng, 1, 0.003), n, phase0=rng.random()) for r in self.RATIOS) / 6
        x = p["metal"] * metal + (1 - p["metal"]) * white(n, rng) * 0.5
        x = svf(x, self.vel_oct(p["color"], v, p["vel_bright"]), 0.9, "bp")
        x = svf(x, p["hp"], 0.7, "hp")
        d = p["decay"] * (1 - p["vel_decay"] + p["vel_decay"] * v * 1.3) * self.vary(rng, 1, 0.1)
        return x * ad(n, 0.0005, d) * 2.0 * self.vel_gain(v)


# ----------------------------------------------------------------------------
# bass / synths
# ----------------------------------------------------------------------------
@register
class Bass(Instrument):
    name, family, mono = "bass", "bass", True
    PARAMS = (
        Param("saw", 1.0, 0, 1, "", "lin", "osc"),
        Param("square", 0.0, 0, 1, "", "lin", "osc"),
        Param("sub", 0.5, 0, 1, "", "lin", "osc", "sine one octave down"),
        Param("cutoff", 700, 60, 8000, "Hz", "log", F),
        Param("res", 1.0, 0.5, 12, "q", "log", F),
        Param("env_amt", 2.0, 0, 6, "oct", "lin", F, "filter-envelope depth"),
        Param("env_decay", 0.15, 0.01, 1.5, "s", "log", F),
        Param("attack", 0.003, 0.001, 0.2, "s", "log", A),
        Param("decay", 0.25, 0.01, 2.0, "s", "log", A),
        Param("sustain", 0.8, 0, 1, "", "lin", A),
        Param("release", 0.06, 0.01, 1.0, "s", "log", A),
        Param("drive", 1.4, 1, 8, "x", "log", T),
        Param("glide", 0.04, 0, 0.5, "s", "log", P, "portamento time on slurred notes"),
        Param("vel_cutoff", 1.5, 0, 4, "oct", "lin", V),
        *common_vel(1.2), RR,
    )

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        n = n_samples(note.gate + p["release"])
        t = t_axis(n)
        f = glide_freq(note, n, p["glide"]) * (1 + 0.002 * p["rr"] * rng.standard_normal())
        x = p["saw"] * saw(f, n, rng.random()) + p["square"] * square(f, n) + p["sub"] * sine(f / 2, n)
        fenv = np.exp(-t / p["env_decay"]) if note.glide_from is None else 0.3 * np.exp(-t / p["env_decay"])
        fc = self.vel_oct(self.p_(note, "cutoff"), v, p["vel_cutoff"]) * 2 ** (p["env_amt"] * v * fenv)
        x = drive(svf(x, fc, p["res"], "lp"), p["drive"])
        return x * adsr(n, p["attack"], p["decay"], p["sustain"], p["release"], note.gate) * self.vel_gain(v)


@register
class Pad(Instrument):
    name, family = "pad", "synth"
    PARAMS = (
        Param("voices", 5, 1, 9, "", "lin", "osc", "unison saws per note"),
        Param("detune", 12, 0, 40, "cents", "lin", "osc"),
        Param("drift", 3, 0, 15, "cents", "lin", "osc", "slow analog pitch wander"),
        Param("cutoff", 1800, 200, 12000, "Hz", "log", F),
        Param("res", 0.8, 0.5, 6, "q", "log", F),
        Param("lfo_rate", 0.15, 0.02, 2, "Hz", "log", F, "slow filter movement"),
        Param("lfo_depth", 0.3, 0, 2, "oct", "lin", F),
        Param("attack", 0.35, 0.005, 4, "s", "log", A),
        Param("decay", 0.5, 0.01, 4, "s", "log", A),
        Param("sustain", 0.85, 0, 1, "", "lin", A),
        Param("release", 0.8, 0.01, 6, "s", "log", A),
        Param("width", 0.8, 0, 1, "", "lin", T, "stereo spread of unison voices"),
        Param("vel_cutoff", 1.0, 0, 3, "oct", "lin", V),
        *common_vel(1.0), RR,
    )

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        n = n_samples(note.gate + p["release"])
        f0 = float(mtof(note.pitch))
        nv = int(round(p["voices"]))
        out = np.zeros((n, 2))
        for k, o in enumerate(np.linspace(-1, 1, nv) if nv > 1 else [0.0]):
            cents = o * p["detune"] + p["drift"] * smooth_noise(n, 0.4, rng)
            out += pan_mono(saw(f0 * 2 ** (cents / 1200), n, rng.random()), o * p["width"])
        out /= np.sqrt(nv)
        lfo = np.sin(2 * np.pi * p["lfo_rate"] * t_axis(n) + rng.random() * 6.28)
        fc = self.vel_oct(self.p_(note, "cutoff"), v, p["vel_cutoff"]) * 2 ** (p["lfo_depth"] * lfo)
        out = svf(out, fc, p["res"], "lp")
        env = adsr(n, p["attack"], p["decay"], p["sustain"], p["release"], note.gate, curve=3)
        return out * env[:, None] * self.vel_gain(v)


@register
class Pluck(Instrument):
    name, family = "pluck", "synth"
    PARAMS = (
        Param("pw", 0.35, 0.05, 0.5, "", "lin", "osc", "pulse width"),
        Param("saw_mix", 0.45, 0, 1, "", "lin", "osc"),
        Param("cutoff", 2500, 200, 12000, "Hz", "log", F),
        Param("res", 1.2, 0.5, 8, "q", "log", F),
        Param("env_amt", 2.5, 0, 6, "oct", "lin", F),
        Param("env_decay", 0.08, 0.01, 0.8, "s", "log", F),
        Param("decay", 0.25, 0.03, 2, "s", "log", A, "amplitude t60"),
        Param("release", 0.03, 0.005, 0.5, "s", "log", A),
        Param("vel_cutoff", 2.0, 0, 4, "oct", "lin", V),
        *common_vel(1.5), RR,
    )

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        n = n_samples(min(note.gate, p["decay"] * 1.2) + p["release"])
        t = t_axis(n)
        f = float(mtof(note.pitch))
        x = (1 - p["saw_mix"]) * square(f, n, p["pw"]) + p["saw_mix"] * saw(f, n, rng.random())
        fc = self.vel_oct(self.p_(note, "cutoff"), v, p["vel_cutoff"]) * 2 ** (p["env_amt"] * np.exp(-t / p["env_decay"]))
        x = svf(x, fc, p["res"], "lp")
        env = t60_env(n, self.vary(rng, p["decay"], 0.05)) * adsr(n, 0.001, 0.01, 1.0, p["release"], note.gate)
        return x * env * self.vel_gain(v)


@register
class Lead(Instrument):
    name, family, mono = "lead", "synth", True
    PARAMS = (
        Param("voices", 5, 1, 9, "", "lin", "osc"),
        Param("detune", 10, 0, 40, "cents", "lin", "osc"),
        Param("cutoff", 4500, 300, 16000, "Hz", "log", F),
        Param("res", 0.9, 0.5, 8, "q", "log", F),
        Param("attack", 0.01, 0.001, 1, "s", "log", A),
        Param("decay", 0.2, 0.01, 2, "s", "log", A),
        Param("sustain", 0.75, 0, 1, "", "lin", A),
        Param("release", 0.15, 0.01, 2, "s", "log", A),
        Param("vib_rate", 5.5, 1, 9, "Hz", "lin", "vibrato"),
        Param("vib_depth", 14, 0, 60, "cents", "lin", "vibrato"),
        Param("vib_delay", 0.25, 0, 1.5, "s", "lin", "vibrato", "vibrato fades in, like a singer"),
        Param("glide", 0.06, 0, 0.5, "s", "log", P),
        Param("breath", 0.04, 0, 0.5, "", "lin", T, "filtered noise riding the note"),
        Param("vel_cutoff", 1.5, 0, 4, "oct", "lin", V),
        *common_vel(1.2), RR,
    )

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        n = n_samples(note.gate + p["release"])
        t = t_axis(n)
        rate = p["vib_rate"] * self.vary(rng, 1, 0.05)
        vib = p["vib_depth"] * np.sin(2 * np.pi * rate * t) * np.clip((t - p["vib_delay"]) * 3, 0, 1)
        f = glide_freq(note, n, p["glide"]) * 2 ** (vib / 1200)
        nv = int(round(p["voices"]))
        out = np.zeros((n, 2))
        for o in (np.linspace(-1, 1, nv) if nv > 1 else [0.0]):
            out += pan_mono(saw(f * 2 ** (o * p["detune"] / 1200), n, rng.random()), o * 0.5)
        out /= np.sqrt(nv)
        if p["breath"]:
            out += p["breath"] * svf(white(n, rng), f * 3, 2.0, "bp")[:, None]
        out = svf(out, self.vel_oct(self.p_(note, "cutoff"), v, p["vel_cutoff"]), p["res"], "lp")
        return out * adsr(n, p["attack"], p["decay"], p["sustain"], p["release"], note.gate)[:, None] * self.vel_gain(v)


# ----------------------------------------------------------------------------
# acoustic-style models
# ----------------------------------------------------------------------------
@register
class StringPluck(Instrument):
    """Karplus-Strong guitar / harp / koto. Pick position and body EQ make it woody."""
    name, family = "string_pluck", "string"
    PARAMS = (
        Param("t60", 3.0, 0.2, 12, "s", "log", A, "ring time while held"),
        Param("brightness", 0.75, 0.5, 1.0, "", "lin", T, "loop damping (0.5 dull, 1 bright)"),
        Param("pick_pos", 0.2, 0.03, 0.5, "", "lin", T, "0.5 = middle (hollow), 0.05 = bridge (twangy)"),
        Param("pick_tone", 6000, 800, 16000, "Hz", "log", T, "excitation brightness"),
        Param("body", 0.5, 0, 1, "", "lin", T, "wooden body resonance"),
        Param("release", 0.08, 0.01, 1.0, "s", "log", A, "damping when the note is released"),
        Param("vel_bright", 2.0, 0, 4, "oct", "lin", V),
        *common_vel(1.3), RR,
    )

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        n = n_samples(note.gate + p["release"])
        f = float(mtof(note.pitch))
        per = SR / f
        m = int(per) + 1
        exc = svf(white(m, rng), self.vel_oct(p["pick_tone"], v, p["vel_bright"]), 0.7, "lp")
        d = max(1, int(p["pick_pos"] * per))
        exc[d:] -= exc[:-d].copy()                     # comb = pick position
        y = ks_string(f, n, exc, self.vary(rng, p["t60"], 0.05), p["brightness"])
        if p["body"]:
            b = p["body"] * 6
            y = eq(eq(eq(y, "peak", 110, b, 1.5), "peak", 230, b * 0.7, 2.0), "peak", 2800, -b * 0.5, 0.8)
        y *= adsr(n, 0.0005, 0.01, 1.0, p["release"], note.gate)
        return y / (np.max(np.abs(y)) + 1e-9) * 0.8 * self.vel_gain(v)


@register
class Keys(Instrument):
    """Modal piano: stiff-string partials, hammer comb, two-stage decay, damper release."""
    name, family = "keys", "keys"
    PARAMS = (
        Param("partials", 24, 4, 48, "", "lin", T),
        Param("inharm", 0.0004, 0, 0.003, "B", "lin", T, "string stiffness: f_n = n f0 sqrt(1 + B n^2)"),
        Param("hardness", 0.5, 0, 1, "", "lin", T, "hammer felt hardness = brightness"),
        Param("hammer_pos", 0.12, 0.05, 0.3, "", "lin", T, "strike point (notches partial 1/pos)"),
        Param("t60", 6.0, 0.5, 30, "s", "log", A, "decay at middle C; lower notes ring longer"),
        Param("aftersound", 0.3, 0, 1, "", "lin", A, "slow second decay stage (piano 'bloom')"),
        Param("unison", 1.2, 0, 6, "cents", "lin", T, "detune between the 2 strings (beating)"),
        Param("thump", 0.15, 0, 1, "", "lin", T, "hammer/action noise"),
        Param("release", 0.25, 0.02, 2, "s", "log", A, "damper speed"),
        Param("spread", 0.6, 0, 1, "", "lin", T, "stereo: low notes left, high right"),
        Param("vel_hard", 1.0, 0, 2, "", "lin", V, "harder hits = brighter"),
        *common_vel(1.6), RR,
    )

    def tail(self, note):
        return self.p["release"]

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        f0 = float(mtof(note.pitch))
        t60 = p["t60"] * 2 ** (-(note.pitch - 60) / 18)
        n = n_samples(min(note.gate, t60 * 1.5) + p["release"])
        t = t_axis(n)
        hard = np.clip(p["hardness"] + p["vel_hard"] * (v - 0.7), 0, 1.5)
        tilt = np.clip(2.4 - 1.6 * hard, 0.4, 3.0)
        x = np.zeros(n)
        for k in range(1, int(p["partials"]) + 1):
            fk = k * f0 * np.sqrt(1 + p["inharm"] * k * k)
            if fk > 0.45 * SR:
                break
            a = k ** -tilt * abs(np.sin(np.pi * k * p["hammer_pos"]))
            tk = t60 / (1 + 0.25 * (k - 1))
            env = (1 - p["aftersound"]) * np.exp(-6.9 * t / (tk * 0.25)) + p["aftersound"] * np.exp(-6.9 * t / tk)
            for s in (-0.5, 0.5):
                x += a * env * np.sin(2 * np.pi * fk * 2 ** (s * p["unison"] / 1200) * t + rng.random() * 6.28)
        x *= np.clip(t / 0.002, 0, 1)
        if p["thump"]:
            x += p["thump"] * v * svf(white(n, rng), 300 + 600 * hard, 0.8, "bp") * t60_env(n, 0.04)
        x *= adsr(n, 0.0005, 0.01, 1.0, p["release"], note.gate)
        x = x / (np.max(np.abs(x)) + 1e-9) * 0.7 * self.vel_gain(v)
        return pan_mono(x, p["spread"] * np.clip((note.pitch - 60) / 30, -1, 1))


@register
class EPiano(Instrument):
    """Two-operator FM tine piano (Rhodes/DX7 EP family) with velocity 'bark'."""
    name, family = "epiano", "keys"
    PARAMS = (
        Param("index", 1.2, 0, 6, "", "lin", T, "FM brightness at medium velocity"),
        Param("index_decay", 0.6, 0.05, 4, "s", "log", T),
        Param("tine", 0.25, 0, 1, "", "lin", T, "metallic 14:1 attack transient"),
        Param("t60", 4.0, 0.5, 15, "s", "log", A),
        Param("release", 0.3, 0.02, 2, "s", "log", A),
        Param("trem_rate", 4.5, 0.5, 9, "Hz", "lin", "tremolo"),
        Param("trem_depth", 0.25, 0, 1, "", "lin", "tremolo", "stereo auto-pan depth"),
        Param("vel_index", 2.5, 0, 6, "", "lin", V, "hard hits bark"),
        *common_vel(1.5), RR,
    )

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        f = float(mtof(note.pitch))
        t60 = p["t60"] * 2 ** (-(note.pitch - 60) / 24)
        n = n_samples(min(note.gate, t60 * 1.5) + p["release"])
        t = t_axis(n)
        idx = (p["index"] + p["vel_index"] * max(v - 0.5, 0)) * np.exp(-t / p["index_decay"])
        mod = idx * np.sin(2 * np.pi * f * t) + p["tine"] * v * np.sin(2 * np.pi * 14 * f * t) * np.exp(-t / 0.02)
        x = np.sin(2 * np.pi * f * t + mod + rng.random()) * t60_env(n, t60)
        x *= adsr(n, 0.001, 0.01, 1.0, p["release"], note.gate) * self.vel_gain(v)
        pan = p["trem_depth"] * np.sin(2 * np.pi * p["trem_rate"] * t + rng.random() * 6.28)
        a = (pan + 1) * np.pi / 4
        return np.stack([x * np.cos(a), x * np.sin(a)], 1) * np.sqrt(2)


@register
class Organ(Instrument):
    """Additive tonewheel organ: nine drawbars, key click, percussion, rotary speaker."""
    name, family = "organ", "keys"
    FOOT = (0.5, 1.5, 1, 2, 3, 4, 5, 6, 8)   # 16', 5 1/3', 8', 4', 2 2/3', 2', 1 3/5', 1 1/3', 1'
    PARAMS = tuple(Param(f"db{i + 1}", d, 0, 8, "", "lin", "drawbars", lbl)
                   for i, (d, lbl) in enumerate(zip((8, 8, 8, 0, 0, 0, 0, 0, 0),
                                                    ("16'", "5 1/3'", "8'", "4'", "2 2/3'", "2'", "1 3/5'", "1 1/3'", "1'")))) + (
        Param("perc", 0.0, 0, 1, "", "lin", T, "2nd-harmonic percussion"),
        Param("click", 0.3, 0, 1, "", "lin", T, "key-contact click"),
        Param("rotor", 0.7, 0, 6.5, "Hz", "lin", "rotary", "0 = off, 0.7 chorale, 6.5 tremolo"),
        Param("release", 0.04, 0.005, 0.5, "s", "log", A),
        *common_vel(0.0),
    )

    def render(self, note):
        p, rng = self.p, self.rng(note)
        f = float(mtof(note.pitch))
        n = n_samples(note.gate + p["release"])
        t = t_axis(n)
        x = sum(p[f"db{i + 1}"] / 8 * sine(f * r, n, rng.random()) for i, r in enumerate(self.FOOT) if f * r < 0.45 * SR)
        if p["perc"]:
            x += p["perc"] * sine(f * 2, n) * t60_env(n, 0.5)
        if p["click"]:
            x += p["click"] * svf(white(n, rng), 2500, 1.0, "bp") * t60_env(n, 0.006)
        x *= adsr(n, 0.003, 0.01, 1.0, p["release"], note.gate) / 3
        if not p["rotor"]:
            return x
        ph = 2 * np.pi * p["rotor"] * t + rng.random() * 6.28
        doppler = np.interp(np.arange(n) + 12 * np.sin(ph), np.arange(n), x)
        am = 1 + 0.25 * np.sin(ph)[:, None] * np.array([1, -1])
        return np.stack([doppler, doppler], 1) * am


# ----------------------------------------------------------------------------
# fx (ported from synth_v0)
# ----------------------------------------------------------------------------
@register
class Riser(Instrument):
    name, family = "riser", "fx"
    PARAMS = (Param("start", 300, 50, 2000, "Hz", "log", F), Param("end", 9300, 2000, 18000, "Hz", "log", F),
              Param("tone", 0.25, 0, 1, "", "lin", T, "rising sine under the noise"),
              Param("curve", 2.2, 0.5, 5, "", "lin", A))

    def tail(self, note):
        return 0.05

    def render(self, note):
        p, rng = self.p, self.rng(note)
        n = n_samples(note.gate)
        k = np.arange(n) / n
        fc = p["start"] + (p["end"] - p["start"]) * k ** p["curve"]
        nz = svf(white(n, rng), fc, 1.4, "bp")
        tone = p["tone"] * sine(110 * 2 ** (3 * k), n)
        return (0.8 * nz + tone) * k ** 2 * note.vel


@register
class Impact(Instrument):
    name, family = "impact", "fx"
    PARAMS = (Param("decay", 3.0, 0.5, 8, "s", "log", A), Param("boom", 1.0, 0, 1, "", "lin", T),
              Param("crash", 0.25, 0, 1, "", "lin", T))

    def tail(self, note):
        return self.p["decay"]

    def render(self, note):
        p, rng = self.p, self.rng(note)
        n = n_samples(p["decay"])
        t = t_axis(n)
        boom = p["boom"] * sine(30 + 70 * np.exp(-t * 6), n) * np.exp(-t * 1.6)
        nz = svf(white(n, rng), 2500, 0.7, "lp") * np.exp(-t * 3) * 0.5
        crash = p["crash"] * svf(white(n, rng), 5000, 0.7, "hp") * np.exp(-t * 1.2)
        return drive(boom + nz + crash, 1.5) * note.vel
