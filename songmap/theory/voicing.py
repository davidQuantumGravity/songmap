"""Chord voicings and voice leading."""
from __future__ import annotations

from itertools import combinations

import numpy as np

from ..parse.errors import NotationError


def voicings(root: int, intervals: tuple, lo: int, hi: int, voices: int = 4):
    """All playable voicings of a chord inside [lo, hi]: every chord tone present
    (the 5th may be dropped when there are more tones than voices), no unisons,
    no gap over an octave between neighbours, total span <= 2 octaves."""
    pcs = [(root + i) % 12 for i in intervals]
    need = set(pcs)
    if len(need) > voices and (root + 7) % 12 in need:
        need.discard((root + 7) % 12)
    if len(need) > voices:
        need = set(pcs[:voices])
    pool = [m for m in range(lo, hi + 1) if m % 12 in pcs]
    for c in combinations(pool, voices):
        if need <= {m % 12 for m in c} and c[-1] - c[0] <= 24 and all(b - a <= 12 for a, b in zip(c, c[1:])):
            yield c


def _voicing_cost(c: tuple, root: int, intervals: tuple) -> float:
    """Taste: prefer doubling the root, avoid a 9th/2nd as the lowest voice."""
    pcs = [m % 12 for m in c]
    doubled = [pc for pc in set(pcs) if pcs.count(pc) > 1 and pc != root % 12]
    low = (c[0] - root) % 12
    return 1.0 * len(doubled) + (2.0 if low in (1, 2) else 0.5 if low != 0 else 0.0)


def voice_lead(prev: tuple | None, root: int, intervals: tuple, lo: int = 52, hi: int = 76,
               voices: int = 4) -> tuple:
    """Pick the voicing with the least total motion from `prev` (smooth pads, real-sounding comping)."""
    cands = list(voicings(root, intervals, lo, hi, voices))
    if not cands:
        raise NotationError(f"no voicing of chord in range {lo}-{hi}; widen `range`")
    center = (lo + hi) / 2
    if prev is None:
        return min(cands, key=lambda c: abs(np.mean(c) - center) + 0.1 * (c[-1] - c[0]) + _voicing_cost(c, root, intervals))
    return min(cands, key=lambda c: sum(abs(a - b) for a, b in zip(c, prev)) + 0.05 * abs(np.mean(c) - center)
               + _voicing_cost(c, root, intervals))
