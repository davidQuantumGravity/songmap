"""A walk on the Tonnetz in 12-ET, alternating the R and L moves: C, Am, F, Dm, Bb, Gm, Eb.
In the upper three voices exactly one note moves, by a step, at each change; the bass plays the root."""
from _lib import chord, seq, freq

VOICES = [(48, 60, 64, 67), (45, 60, 64, 69), (41, 60, 65, 69), (50, 62, 65, 69),
          (46, 62, 65, 70), (43, 62, 67, 70), (51, 63, 67, 70)]


def render():
    return seq([chord([freq(m) for m in v], 1.6, "clean/organ") for v in VOICES])
