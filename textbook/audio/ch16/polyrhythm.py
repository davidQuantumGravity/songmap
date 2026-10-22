"""Polyrhythm: three against two, then four against three.

Each cycle lasts 1.5 s. The higher tone (E5) divides the cycle into 3 (then 4) equal parts, the lower
tone (C4) into 2 (then 3). Both coincide only on the first beat of each cycle, so a cycle has
a + b - gcd(a, b) distinct onsets: 4 for 3:2 and 6 for 4:3.
"""
from math import gcd
from _lib import tone, at, freq

CYCLE = 1.5


def layer(n, cycles, f, t0, vel):
    return [(t0 + c * CYCLE + k * CYCLE / n, tone(f, 0.09, "clean/keys", vel=vel)) for c in range(cycles) for k in range(n)]


def render():
    hi, lo = freq(76), freq(60)            # E5, C4
    clips = []
    clips += layer(2, 4, lo, 0.0, 0.7) + layer(3, 4, hi, 0.0, 0.55)          # 3:2 for 4 cycles
    t1 = 4 * CYCLE + 1.0
    clips += layer(3, 4, lo, t1, 0.7) + layer(4, 4, hi, t1, 0.55)            # 4:3 for 4 cycles
    clips.append((t1 + 4 * CYCLE, tone(lo, 0.09, "clean/keys", vel=0.7)))     # closing downbeat
    clips.append((t1 + 4 * CYCLE, tone(hi, 0.09, "clean/keys", vel=0.55)))
    assert 3 + 2 - gcd(3, 2) == 4 and 4 + 3 - gcd(4, 3) == 6
    return at(clips)
