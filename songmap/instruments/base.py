"""Instrument model: Param schema, Note, Instrument base class, registry and describe().

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

from .dsp import SR, mtof, t_axis


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
    rr: int = 0                         # round-robin slot (the part's note counter); samplers cycle layers by it
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

    def choke(self, note: Note) -> tuple[int, int]:
        """(group, off_by): a later note of group `off_by` in the same part cuts this one. 0 = none."""
        return 0, 0

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
    return (Param("vel_curve", curve, min(0.3, curve), 3.0, "", "lin", V,
                  "loudness curve: gain = vel**curve (0 = every note equally loud)"),)


RR = Param("rr", 0.3, 0.0, 1.0, "", "lin", X, "per-hit random variation (round-robin feel)")
