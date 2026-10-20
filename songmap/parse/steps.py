"""Drum step strings: 'X..x..x.|X.ox.x..'."""
from __future__ import annotations

from .errors import NotationError
from .notes import Ev


STEP_VEL = {"X": 1.0, "x": 0.78, "-": 0.55, "o": 0.38}


def parse_steps(s: str, beats_per_bar: float = 4, name: str = "steps") -> tuple[list[Ev], int]:
    """'X..x..x.|X.ox.x..' -> events. Chars per bar set the grid (16 = 16ths, 12 = 8th triplets).

    X accent  x normal  - soft  o ghost  . rest  f flam  r ratchet (two quick hits)
    """
    bars = [b.replace(" ", "") for b in s.split("|")]
    evs: list[Ev] = []
    for bi, seg in enumerate(bars):
        if not seg:
            raise NotationError(f"{name}: empty bar {bi + 1} in '{s}'")
        step = beats_per_bar / len(seg)
        for i, c in enumerate(seg):
            b = bi * beats_per_bar + i * step
            if c == ".":
                continue
            if c in STEP_VEL:
                evs.append(Ev(b, step, (), STEP_VEL[c], tags={"ghost"} if c == "o" else set()))
            elif c == "f":
                evs.append(Ev(b - 0.06, step, (), 0.45, tags={"flam"}))
                evs.append(Ev(b, step, (), 0.85))
            elif c == "r":
                evs.append(Ev(b, step / 2, (), 0.6))
                evs.append(Ev(b + step / 2, step / 2, (), 0.72))
            else:
                raise NotationError(f"{name}: unknown step '{c}' in bar {bi + 1}. Use X x - o . f r")
    return evs, len(bars)
