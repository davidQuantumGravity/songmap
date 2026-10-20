"""Performance layer: turns written events into played notes.

Order of operations for one part in one section (each step is optional and seeded):

    written Ev (beats, written vel, articulation)
      -> section dynamics shape     (=mp<=f across the section)
      -> metric accent              (downbeats a little louder, off-16ths softer)
      -> melodic shaping            (KTH "high-loud" + phrase arch)
      -> groove                     (swing, groove template, per-part feel offset)
      -> humanize                   (slow drift + small jitter, timing and velocity)
      -> articulation -> gate time  (staccato, tenuto, slur/legato overlap)
      -> Note(pitch, vel, gate, seed, glide_from)     handed to the instrument

All randomness comes from np.random.default_rng(seed) so renders are reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..instruments.base import Note
from ..parse.errors import NotationError
from ..parse.notes import DYN, Ev
from .grooves import GROOVES


GATE = {"normal": 0.9, "staccato": 0.45, "staccatissimo": 0.25, "tenuto": 1.0,
        "marcato": 0.7, "accent": 0.85, "legato": 1.04}


@dataclass
class Feel:
    swing: float = 0.5          # 0.5 straight, 0.58 light, 0.66 triplet shuffle
    swing_grid: float = 0.5     # beats: 0.5 = swing 8ths, 0.25 = swing 16ths
    groove: str = "straight"
    groove_amt: float = 1.0
    offset_ms: float = 0.0      # + = lays back, - = pushes
    time_ms: float = 0.0        # humanize timing sd
    drift_ms: float = 0.0       # humanize slow drift amplitude
    vel_sd: float = 0.0         # humanize velocity sd (0..1 scale)
    metric: float = 0.5         # strength of metric accents
    high_loud: float = 0.0      # louder as melody rises (KTH rule)
    arch: float = 0.0           # phrase crescendo-decrescendo over each motif instance
    gate: float = 1.0           # global gate multiplier (0.5 = choppier part)
    seed: int = 0


@dataclass
class Played:
    time: float                 # seconds from song start
    note: Note
    tags: set = field(default_factory=set)


def parse_shape(shape: str) -> list[tuple[float, float]]:
    """'mp<f', 'p<ff>mp', 'mf' -> [(position 0..1, level), ...]."""
    import re
    toks = re.findall(r"ppp|pp|p|mp|mf|fff|ff|f|<|>", shape)
    levels = [DYN[t] for t in toks if t in DYN]
    if not levels:
        raise NotationError(f"dyn '{shape}': use marks like mp, mp<f, p<ff>mp")
    if len(levels) == 1:
        return [(0.0, levels[0]), (1.0, levels[0])]
    return [(i / (len(levels) - 1), l) for i, l in enumerate(levels)]


def shape_at(shape: list[tuple[float, float]], x: float) -> float:
    xs, ys = zip(*shape)
    return float(np.interp(x, xs, ys))


def metric_weight(beat_in_bar: float, beats_per_bar: float = 4) -> float:
    """Downbeat 1.08, mid-bar 1.04, beats 1.0, 8th off-beats 0.95, 16ths 0.91."""
    b = beat_in_bar % beats_per_bar
    if abs(b) < 1e-6:
        return 1.08
    if abs(b - beats_per_bar / 2) < 1e-6:
        return 1.04
    if abs(b - round(b)) < 1e-6:
        return 1.0
    if abs(b * 2 - round(b * 2)) < 1e-6:
        return 0.95
    return 0.91


def swing_beat(beat: float, amount: float, grid: float = 0.5) -> float:
    """Delay notes on the off-step of each `grid` pair. amount 0.5 = straight."""
    pair = 2 * grid
    pos = beat % pair
    if abs(pos - grid) < 1e-6:
        return beat + (amount - 0.5) * pair
    return beat


def groove_offset(beat: float, name: str) -> tuple[float, float]:
    tpl = GROOVES[name]
    step = beat / 0.25
    if abs(step - round(step)) > 1e-6:
        return 0.0, 1.0
    off, vf = tpl[int(round(step)) % len(tpl)]
    return off * 0.25, vf


def drift_curve(n: int, rng, smooth: int = 8) -> np.ndarray:
    """Slow random walk in [-1, 1]: humans drift, they don't jitter like white noise."""
    w = np.cumsum(rng.standard_normal(n + smooth))
    w = np.convolve(w, np.ones(smooth) / smooth, "valid")[:n]
    w -= w.mean() if n else 0
    return w / (np.max(np.abs(w)) + 1e-9) if n else w


def perform(evs: list[Ev], *, start_beat: float, spb: float, feel: Feel,
            section_shape: str | None = None, section_beats: float | None = None,
            section_start: float = 0.0,
            beats_per_bar: float = 4, mono: bool = False, phrase_len: float | None = None,
            transpose: int = 0) -> list[Played]:
    """Expand written events of one part into Played notes.

    start_beat: where this block starts in the song (beats); spb = seconds per beat.
    section_shape/section_beats/section_start: the section's dynamic curve and its extent
    in song beats, so a 2-bar pattern repeated 4x still follows one 8-bar crescendo.
    phrase_len: motif length in beats (for the phrase arch); defaults to the block length.
    """
    rng = np.random.default_rng(feel.seed)
    shape = parse_shape(section_shape) if section_shape else None
    total = section_beats or max((e.beat + e.dur for e in evs), default=1.0)
    plen = phrase_len or total
    pitched = [p for e in evs for p in e.pitches]
    mean_p = float(np.mean(pitched)) if pitched else 60.0
    drift = drift_curve(len(evs), rng)
    out: list[Played] = []
    prev_pitch = None
    for i, e in enumerate(evs):
        v = e.vel
        if not e.explicit_vel:
            if shape:
                v *= shape_at(shape, (start_beat + e.beat - section_start) / total) / DYN["mf"]
            v *= 1 + feel.metric * (metric_weight(start_beat + e.beat, beats_per_bar) - 1)
            if e.pitches and feel.high_loud:
                v *= 1 + feel.high_loud * (np.mean(e.pitches) - mean_p) / 24
            if feel.arch:
                x = (e.beat % plen) / plen
                v *= 1 + feel.arch * (np.sin(np.pi * x) - 0.5) * 0.3
        b = swing_beat(e.beat, feel.swing, feel.swing_grid)
        g_off, g_vf = groove_offset(e.beat, feel.groove)
        b += g_off * feel.groove_amt
        v *= 1 + (g_vf - 1) * feel.groove_amt
        t = (start_beat + b) * spb + feel.offset_ms / 1000
        t += (feel.time_ms * rng.standard_normal() + feel.drift_ms * drift[i]) / 1000
        v = float(np.clip(v + feel.vel_sd * rng.standard_normal(), 0.02, 1.0))
        art = "legato" if e.slur else e.art
        gate = e.dur * spb * GATE.get(art, 0.9) * feel.gate
        for p in (e.pitches or (None,)):
            pitch = 60.0 if p is None else float(p + transpose)
            glide = prev_pitch if (mono and i > 0 and evs[i - 1].slur) else None
            out.append(Played(max(t, 0.0), Note(pitch, v, gate, seed=int(rng.integers(2**31)),
                                                glide_from=glide), set(e.tags)))
        if e.pitches:
            prev_pitch = float(e.pitches[-1] + transpose)
    return out
