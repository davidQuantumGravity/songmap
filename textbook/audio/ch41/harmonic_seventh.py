"""The seventh the harmonic series offers, and the one 12-ET uses.

On A2 = 110 Hz, clean organ (8 harmonics), 5 s each:
  1. 4:5:6:7 = 440, 550, 660, 770 Hz: the harmonic seventh chord (7/4 = 968.83 c); no beats
  2. 12-ET dominant seventh A7 on A4 = 440: 440, 554.37, 659.26, 783.99 Hz (seventh 1000 c)
"""
from _lib import chord, freq, silence, seq


def render():
    just = [440.0 * r for r in (1, 5 / 4, 3 / 2, 7 / 4)]
    et = [freq(69 + s) for s in (0, 4, 7, 10)]
    return seq([chord(just, 5.0, "clean/organ", attack=0.1, release=0.5), silence(0.6),
                chord(et, 5.0, "clean/organ", attack=0.1, release=0.5)])
