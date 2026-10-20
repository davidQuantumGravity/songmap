"""Chord voicings and voice leading."""
from __future__ import annotations

from itertools import combinations

import numpy as np

from ..parse.errors import NotationError
from .tuning import DEFAULT, FIFTH, OCTAVE, Tuning


def voicings(root: float, intervals: tuple, lo: float, hi: float, voices: int = 4, tuning: Tuning = DEFAULT):
    """All playable voicings of a chord inside [lo, hi]: every chord tone present
    (the 5th may be dropped when there are more tones than voices), no unisons,
    no gap over an octave between neighbours, total span <= 2 octaves."""
    pc = tuning.pc
    pcs = [pc(root + i) for i in intervals]
    need = set(pcs)
    if len(need) > voices and pc(root + FIFTH) in need:
        need.discard(pc(root + FIFTH))
    if len(need) > voices:
        need = set(pcs[:voices])
    pool = [m for m in tuning.grid(lo, hi) if pc(m) in pcs]
    for c in combinations(pool, voices):
        if need <= {pc(m) for m in c} and c[-1] - c[0] <= 2 * OCTAVE and all(b - a <= OCTAVE for a, b in zip(c, c[1:])):
            yield c


def _voicing_cost(c: tuple, root: float, intervals: tuple, tuning: Tuning = DEFAULT) -> float:
    """Taste: prefer doubling the root, avoid a 9th/2nd as the lowest voice."""
    pcs = [tuning.pc(m) for m in c]
    doubled = [pc for pc in set(pcs) if pcs.count(pc) > 1 and pc != tuning.pc(root)]
    low = (c[0] - root) % OCTAVE
    return 1.0 * len(doubled) + (2.0 if 0 < low <= 2 else 0.5 if low != 0 else 0.0)


def voice_lead(prev: tuple | None, root: float, intervals: tuple, lo: float = 52, hi: float = 76,
               voices: int = 4, tuning: Tuning = DEFAULT) -> tuple:
    """Pick the voicing with the least total motion from `prev` (smooth pads, real-sounding comping)."""
    cands = list(voicings(root, intervals, lo, hi, voices, tuning))
    if not cands:
        raise NotationError(f"no voicing of chord in range {lo}-{hi}; widen `range`")
    center = (lo + hi) / 2
    if prev is None:
        return min(cands, key=lambda c: abs(np.mean(c) - center) + 0.1 * (c[-1] - c[0]) + _voicing_cost(c, root, intervals, tuning))
    return min(cands, key=lambda c: sum(abs(a - b) for a, b in zip(c, prev)) + 0.05 * abs(np.mean(c) - center)
               + _voicing_cost(c, root, intervals, tuning))
