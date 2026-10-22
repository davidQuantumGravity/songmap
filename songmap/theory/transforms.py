"""Motif transforms (SONGMAP_SPEC §4): develop a theme instead of writing new tunes.

    t+2  t-1      transpose: scale degrees for deg motifs, semitones for letter motifs
    oct+1 oct-1   octaves
    inv           melodic inversion around the first note (in degrees for deg motifs)
    rev           retrograde (the rhythm reversed too)
    aug  dim      durations x2 / /2
    dyn=p         re-level the written dynamics (accents keep their ratio)
    frag=2 frag=-1  the first 2 bars / the last bar
    x2            repeat
    thin=0.5      keep the strongest half of the notes by metric position
    canon=3@8     3 copies, each entering an 8th later

Transforms chain left to right: `theme:aug:t+2`. They work on parsed events, so a motif's
rhythm, articulation and ghosts survive them.
"""
from __future__ import annotations

import math
import re
from dataclasses import replace

from ..parse.errors import NotationError
from ..parse.notes import DYN, Ev, EvList, motif_length, parse_duration
from .keys import MODES, parse_key
from .tuning import OCTAVE, octaves

NAMES = ("t", "oct", "inv", "rev", "aug", "dim", "dyn", "frag", "x", "thin", "canon")
_TOK = re.compile(r"(t|oct)([+-]\d+)|(inv|rev|aug|dim)|(dyn)=(\w+)|(frag)=(-?\d+)|x(\d+)|(thin)=(\d*\.?\d+)"
                  r"|(canon)=(\d+)@(\d+\.?)")


def split(spec: str) -> list[str]:
    """'aug:t+2' or 'aug t+2' -> ['aug', 't+2']."""
    return [t for t in re.split(r"[:\s]+", spec.strip()) if t]


def is_transform(tok: str) -> bool:
    return bool(_TOK.fullmatch(tok))


def _degree(p: float, key: str) -> tuple[int, float]:
    """MIDI pitch -> (scale degree from the key's tonic in octave 4, chromatic alteration)."""
    tonic, scale = parse_key(key)
    base = octaves(5) + tonic                    # degree_to_midi(0, key, 4)
    octs, semis = divmod(p - base, OCTAVE)
    idx = max(i for i, s in enumerate(scale) if s <= semis + 1e-9)
    return int(octs) * len(scale) + idx, semis - scale[idx]


def _pitch(deg: int, alter: float, key: str) -> float:
    tonic, scale = parse_key(key)
    o, i = divmod(deg, len(scale))
    p = octaves(5 + o) + tonic + scale[i] + alter
    return int(p) if float(p).is_integer() else p


def _map_pitches(evs, fn, rel_fn=None, what=""):
    out = EvList()
    for e in evs:
        if e.rel:
            if rel_fn is None:
                raise NotationError(f"transform {what} doesn't apply to chord-relative (rel) notes; use oct+n")
            out.append(replace(e, rel=tuple(rel_fn(t) for t in e.rel)))
        else:
            out.append(replace(e, pitches=tuple(fn(p) for p in e.pitches)))
    out.length = getattr(evs, "length", motif_length(evs))
    return out


def apply(evs: list[Ev], spec: str, *, key: str, deg: bool, beats_per_bar: float = 4,
          name: str = "motif") -> EvList:
    """Apply a chain of transforms to parsed events."""
    from ..perform.pipeline import metric_weight
    cur = evs if isinstance(evs, EvList) else EvList(evs, length=motif_length(evs))
    for tok in split(spec):
        m = _TOK.fullmatch(tok)
        if not m:
            raise NotationError(f"{name}: unknown transform '{tok}'; transforms: t+n t-n oct+n inv rev aug dim "
                                f"dyn=<level> frag=<bars> x<n> thin=<0..1> canon=<n>@<note> (to= arrives later)")
        L = cur.length
        if m[1]:                                       # t+n / oct+n
            n = int(m[2])
            if m[1] == "oct":
                cur = _map_pitches(cur, lambda p: p + octaves(n), lambda t: (t[0], t[1] + n), tok)
            elif deg:
                def step(p, n=n):
                    d, alter = _degree(p, key)
                    return _pitch(d + n, alter, key)
                cur = _map_pitches(cur, step, None, tok)
            else:
                cur = _map_pitches(cur, lambda p: p + n, None, tok)
        elif m[3] == "inv":
            first = next((e.pitches[0] for e in cur if e.pitches), None)
            if first is None:
                continue
            if deg:
                d0, _ = _degree(first, key)
                cur = _map_pitches(cur, lambda p: _pitch(2 * d0 - _degree(p, key)[0], _degree(p, key)[1], key), None,
                                   tok)
            else:
                cur = _map_pitches(cur, lambda p: 2 * first - p, None, tok)
        elif m[3] == "rev":
            out = EvList(replace(e, beat=L - e.beat - e.dur) for e in cur)
            out.sort(key=lambda e: e.beat)
            out.length = L
            cur = out
        elif m[3] in ("aug", "dim"):
            k = 2.0 if m[3] == "aug" else 0.5
            out = EvList(replace(e, beat=e.beat * k, dur=e.dur * k) for e in cur)
            out.length = L * k
            cur = out
        elif m[4]:                                     # dyn=level
            if m[5] not in DYN:
                raise NotationError(f"{name}: dyn={m[5]}: use one of {' '.join(DYN)}")
            vels = sorted(e.vel for e in cur if not e.explicit_vel) or [DYN["mf"]]
            mid = vels[len(vels) // 2]
            out = EvList(e if e.explicit_vel else replace(e, vel=min(1.0, DYN[m[5]] * e.vel / mid)) for e in cur)
            out.length = L
            cur = out
        elif m[6]:                                     # frag=n bars
            n = int(m[7])
            bars = max(1, math.ceil(L / beats_per_bar - 1e-9))
            if n == 0 or abs(n) > bars:
                raise NotationError(f"{name}: frag={n}: the motif has {bars} bars")
            lo, hi = (0.0, n * beats_per_bar) if n > 0 else ((bars + n) * beats_per_bar, bars * beats_per_bar)
            out = EvList(replace(e, beat=e.beat - lo) for e in cur if lo - 1e-9 <= e.beat < hi - 1e-9)
            out.length = hi - lo
            cur = out
        elif m[8]:                                     # xN
            n = int(m[8])
            out = EvList(replace(e, beat=e.beat + k * L) for k in range(n) for e in cur)
            out.length = L * n
            cur = out
        elif m[9]:                                     # thin=f
            f = float(m[10])
            if not 0 < f <= 1:
                raise NotationError(f"{name}: thin={m[10]}: keep a fraction between 0 and 1")
            ranked = sorted(range(len(cur)), key=lambda i: (-metric_weight(cur[i].beat, beats_per_bar), i))
            keep = set(ranked[:max(1, round(f * len(cur)))])
            out = EvList(e for i, e in enumerate(cur) if i in keep)
            out.length = L
            cur = out
        elif m[11]:                                    # canon=n@note
            n, d = int(m[12]), parse_duration(m[13])
            out = EvList(replace(e, beat=e.beat + k * d) for k in range(n) for e in cur)
            out.sort(key=lambda e: e.beat)
            out.length = L + (n - 1) * d
            cur = out
    return cur


__all__ = ["apply", "split", "is_transform", "NAMES"]
