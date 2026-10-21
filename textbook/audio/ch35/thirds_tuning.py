"""Why medieval thirds were 'imperfect': the same third in three tunings, on A3 = 220 Hz (clean organ).

Major third: Pythagorean 81/64 (beats 13.75 Hz), just 5/4 (no beat), 12-ET 2^(4/12) (beats 8.73 Hz).
Minor third: Pythagorean 32/27 (beats 16.30 Hz), just 6/5 (no beat), 12-ET 2^(3/12) (beats 11.87 Hz).
Beat = the gap between the 5th partial of the lower note and the 4th of the upper (major third),
or the 6th of the lower and the 5th of the upper (minor third). 4 s each.
"""
from _lib import chord, silence, seq

A3 = 220.0
RATIOS = [81 / 64, 5 / 4, 2 ** (4 / 12), None, 32 / 27, 6 / 5, 2 ** (3 / 12)]


def render():
    out = []
    for r in RATIOS:
        if r is None:
            out.append(silence(1.0))
            continue
        out.append(chord([A3, A3 * r], 4.0, "clean/organ", attack=0.1, release=0.4))
        out.append(silence(0.4))
    return seq(out)
