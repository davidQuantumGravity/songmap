"""The performance stage: written events -> played events (docs/PERFORMANCE.md), between expand and render.

For every note: metric accent and melodic shaping (pitched parts), swing and the groove
template, the part's timing offset, humanize (white jitter plus slow drift, scaled per part),
velocity variation, gate, and rolled chords. A feel resolves, last wins:

    mood.groove < song groove < section feel < mood parts_feel[part] < song parts_feel[part]
                < mood parts_feel[piece] < song parts_feel[piece]          (piece = a kit lane)

Event sounds (impact, riser, zaps) are never moved: they land on their frames. The written
arrangement and its digest are untouched; only render sees played events. Mood `v0` turns the
stage off (unless the song writes its own groove or part feel), so the faithful ports render
exactly as written.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace

import numpy as np

from ..parse.errors import SongError, did_you_mean
from .grooves import GROOVES
from .pipeline import GATE, drift_curve, groove_offset, metric_weight, swing_beat

GRID = {8: 0.5, 16: 0.25}
PHRASE_BARS = 4


@dataclass
class Feel:
    swing: float = 0.5           # 0.5 straight, 0.54-0.58 light, 0.66 triplet shuffle
    swing_grid: float = 0.5      # beats: 0.5 swings 8ths, 0.25 swings 16ths
    template: str = "straight"   # a groove template (perform/grooves.py)
    groove_amt: float = 1.0
    time_ms: float = 0.0         # humanize: timing jitter (sd)
    drift_ms: float = 0.0        # humanize: slow drift amplitude
    vel_sd: float = 0.0          # humanize: velocity variation (sd, 0..1 scale)
    hum_scale: float = 1.0       # this part's share of the humanize amounts (kick 0.15, pads 1.5, ...)
    metric: float = 0.0          # metric accents on pitched parts (downbeats louder)
    offset_ms: float = 0.0       # + lays back, - pushes
    gate: float = 1.0            # note-length multiplier
    high_loud: float = 0.0       # higher notes a little louder
    arch: float = 0.0            # swell and ease over each 4-bar phrase
    strum_ms: float = 0.0        # roll chords low to high, this many ms between notes


NAMES = tuple(f.name for f in fields(Feel))
ALIASES = {"tpl": "template", "offset": "offset_ms", "hum": "humanize"}


def _merge(feel: Feel, d, where: str, file=None) -> Feel:
    if not d:
        return feel
    if not isinstance(d, dict):
        raise SongError(f"{where}: write a mapping like {{swing: 0.56, humanize: {{time_ms: 5}}}}", file=file)
    f = replace(feel)
    for k, v in d.items():
        k = ALIASES.get(k, k)
        try:
            if k == "humanize":
                h = v if isinstance(v, dict) else {}
                f.time_ms = float(h.get("time_ms", f.time_ms))
                f.drift_ms = float(h.get("drift_ms", f.drift_ms))
                f.vel_sd = float(h.get("vel", h.get("vel_sd", f.vel_sd)))
            elif k == "swing_grid":
                grid = GRID.get(int(v))
                if grid is None:
                    raise SongError(f"{where}: swing_grid {v}: write 8 or 16", file=file)
                f.swing_grid = grid
            elif k == "template":
                if v not in GROOVES:
                    raise SongError(f"{where}: unknown groove template '{v}'", file=file,
                                    suggestion=did_you_mean(str(v), GROOVES))
                f.template = str(v)
            elif k in NAMES:
                setattr(f, k, float(v))
            else:
                raise SongError(f"{where}: unknown feel '{k}'", file=file,
                                suggestion=did_you_mean(k, [*NAMES, "humanize"]))
        except SongError:
            raise
        except (TypeError, ValueError):
            raise SongError(f"{where}: {k}={v!r} is not a number", file=file) from None
    if not 0.3 <= f.swing <= 0.8:
        raise SongError(f"{where}: swing {f.swing:g}: use 0.5 (straight) to 0.75", file=file)
    return f


class Performer:
    def __init__(self, arr):
        self.arr, self.song, self.tl = arr, arr.song, arr.timeline
        mood = arr.ensemble.mood
        self.on = bool(mood.get("perform", True)) or bool(self.song.groove or self.song.parts_feel)
        self.base = _merge(_merge(Feel(), mood.get("groove"), f"mood {mood.get('mood')} groove"),
                           self.song.groove, "groove", self.song.file)
        self.mood_parts = mood.get("parts_feel") or {}
        self.sections = {s.name: s for s in self.song.sections}
        self.spans = {s.name: s for s in self.tl.sections}
        self._cache: dict = {}

    def feel(self, part: str, piece: str | None, section: str) -> Feel:
        key = (part, piece, section)
        if key not in self._cache:
            sec = self.sections.get(section)
            f = _merge(self.base, sec.feel if sec else None, f"{section} feel", self.song.file)
            for name in (part, piece):
                if name:
                    f = _merge(f, self.mood_parts.get(name), f"mood feel {name}")
                    f = _merge(f, self.song.parts_feel.get(name), f"feel {name}", self.song.file)
            self._cache[key] = f
        return self._cache[key]

    def play(self) -> dict:
        if not self.on:
            return self.arr.parts
        from ..arrange.expand import seed_for
        out = {}
        for part, evs in self.arr.parts.items():
            kit = self.arr.ensemble.is_kit(part)
            groups: dict = {}
            for i, e in enumerate(evs):
                groups.setdefault((e.piece, e.section), []).append(i)
            played = list(evs)
            for (piece, section), idx in groups.items():
                f = self.feel(part, piece, section)
                rng = np.random.default_rng(seed_for(self.song.seed, "perform", part, piece or "", section))
                drift = drift_curve(len(idx), rng)
                span = self.spans.get(section)
                pitched = [p for i in idx for p in evs[i].pitches]
                mean_p = float(np.mean(pitched)) if pitched else 60.0
                for j, i in enumerate(idx):
                    e = evs[i]
                    if any(t.startswith("event:") for t in e.tags):
                        continue                                   # hits stay on their frames
                    v = e.vel
                    if e.pitches and not kit:
                        v *= 1 + f.metric * (metric_weight(self.tl.beat_in_bar(e.beat), self.tl.bpb_at(e.beat),
                                                           self.tl.groups_at(e.beat)) - 1)
                        if f.high_loud:
                            v *= 1 + f.high_loud * (float(np.mean(e.pitches)) - mean_p) / 24
                        if f.arch and span is not None:
                            x = ((e.beat - span.start) % (PHRASE_BARS * span.bpb)) / (PHRASE_BARS * span.bpb)
                            v *= 1 + f.arch * (np.sin(np.pi * x) - 0.5) * 0.3
                    b = swing_beat(e.beat, f.swing, f.swing_grid)
                    g_off, g_vf = groove_offset(e.beat, f.template)
                    b += g_off * f.groove_amt
                    v *= 1 + (g_vf - 1) * f.groove_amt
                    ms = f.offset_ms + f.hum_scale * (f.time_ms * rng.standard_normal() + f.drift_ms * drift[j])
                    spb = self.tl.spb(e.beat)
                    b = max(0.0, b + ms / 1000 / spb)
                    v = float(np.clip(v + f.hum_scale * f.vel_sd * rng.standard_normal(), 0.02, 1.0))
                    gate = e.gate
                    if f.gate != 1.0:
                        gate = (e.gate if e.gate is not None else GATE.get("legato" if e.slur else e.art, 0.9)) * f.gate
                    p = replace(e, beat=b, vel=v, gate=gate)
                    if f.strum_ms and len(e.pitches) > 1:
                        step = f.strum_ms / 1000 / spb
                        notes = sorted(e.pitches)
                        p = [replace(p, beat=b + k * step, pitches=(q,), vel=v * (1 - 0.04 * k))
                             for k, q in enumerate(notes)]
                    played[i] = p
            flat = []
            for p in played:
                flat += p if isinstance(p, list) else [p]
            flat.sort(key=lambda e: (e.beat, e.piece or "", e.pitches))
            out[part] = flat
        return out


def play(arr) -> dict:
    """Written arrangement -> {part: played XEvs} (the same dict when the performance stage is off)."""
    return Performer(arr).play()


def played_digest(parts: dict) -> str:
    import hashlib
    h = hashlib.sha256()
    for part in sorted(parts):
        for e in parts[part]:
            h.update(e.key().encode())
            h.update(b"\n")
    return h.hexdigest()


__all__ = ["Feel", "Performer", "play", "played_digest"]
