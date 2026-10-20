"""Positions -> absolute beats (SONGMAP_SPEC §8).

| Form         | Meaning                                                       |
|--------------|---------------------------------------------------------------|
| `56`         | bar 56 (counted from 0), downbeat                             |
| `56:3.5`     | bar 56, the "and" of beat 3 (beats are 1-based)               |
| `agents`     | start of section `agents`                                     |
| `agents+8:2` | 8 bars into `agents`, beat 2; `agents-1` = one bar before     |
| `+8:2`       | relative to the current section (compact form)                |
| `f3960`      | video frame 3960, snapped to the nearest 16th unless snap=none |
| `cue:x`      | a named cue from `cues:`                                      |
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import SongError, did_you_mean

_BAR = re.compile(r"(-?\d+(?:\.\d+)?)(?::(\d+(?:\.\d+)?))?")
_NAMED = re.compile(r"([A-Za-z_][\w]*)?(?:([+-]\d+(?:\.\d+)?))?(?::(\d+(?:\.\d+)?))?")


@dataclass(frozen=True)
class Pos:
    beat: float
    text: str
    frame_error: int = 0      # frames between the requested f#### and the snapped position


def resolve(value, tl, cues: dict | None = None, *, section: str | None = None, snap: str = "16",
            _seen: tuple = ()) -> Pos:
    """Resolve a position to absolute beats against a Timeline."""
    cues = cues or {}
    text = str(value).strip()
    bpb = tl.bpb

    def beat_in_bar(b: str | None) -> float:
        if b is None:
            return 0.0
        x = float(b)
        if not 1 <= x < bpb + 1:
            raise SongError(f"position '{text}': beat {b} is outside the bar (1..{bpb:g}.x)")
        return x - 1

    if text.startswith("cue:"):
        name = text[4:]
        if name not in cues:
            raise SongError(f"unknown cue '{name}'", suggestion=did_you_mean(name, cues) if cues else "define it under cues:")
        if name in _seen:
            raise SongError(f"cue '{name}' refers to itself")
        p = resolve(cues[name], tl, cues, section=section, snap=snap, _seen=_seen + (name,))
        return Pos(p.beat, text, p.frame_error)
    if re.fullmatch(r"f\d+", text):
        frame = int(text[1:])
        exact = tl.frame_to_beat(frame)
        if snap == "none":
            return Pos(exact, text, 0)
        grid = {"16": 0.25, "8": 0.5, "4": 1.0, "32": 0.125}.get(str(snap))
        if grid is None:
            raise SongError(f"snap '{snap}' unknown", suggestion="valid: 4 8 16 32 none")
        beat = round(exact / grid) * grid
        return Pos(beat, text, tl.beat_to_frame(beat) - frame)
    m = _BAR.fullmatch(text)
    if m and not text.startswith(("+", "-")):
        return Pos(tl.bar_to_beat(float(m[1])) + beat_in_bar(m[2]), text)
    m = _NAMED.fullmatch(text)
    if not m or not (m[1] or m[2]):
        raise SongError(f"position '{text}' not understood",
                        suggestion="write 56, 56:3, name, name+8:2, f3960 or cue:name")
    if m[1]:
        base = tl.section(m[1]).start
    elif section is not None:
        base = tl.section(section).start
    else:
        raise SongError(f"relative position '{text}' needs a section", suggestion="write name+8 instead")
    off = float(m[2]) if m[2] else 0.0
    return Pos(base + tl.bar_to_beat(off) + beat_in_bar(m[3]), text)
