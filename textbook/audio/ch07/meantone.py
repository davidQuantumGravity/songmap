"""Ch. 7, quarter-comma meantone (fifth = 5^(1/4) = 696.58 c, the Eb..G# twelve-note layout).
A C major triad in meantone (third pure 386.31 c, fifth 696.58 c), then the Pythagorean triad for
comparison; then the meantone wolf G#3-Eb4 (737.64 c); then the meantone "major third" C#4-F4,
really a diminished fourth (427.37 c)."""
from math import log2
from _lib import chord, freq, seq, silence

C4 = freq(60)
FIFTH = 5 ** 0.25          # quarter-comma meantone fifth as a ratio


def mt(k, octave=0):
    """Chain position k of quarter-comma meantone (C = 0), folded into C4's octave, shifted."""
    c = (k * 1200 * log2(FIFTH)) % 1200
    return C4 * 2 ** (c / 1200 + octave)


def render():
    triad_mt = [mt(0), mt(4), mt(1)]
    triad_py = [C4, C4 * 81 / 64, C4 * 3 / 2]
    return seq([
        chord(triad_mt, 3.0), silence(0.5), chord(triad_py, 3.0), silence(0.9),
        chord([mt(8, -1), mt(-3)], 3.0), silence(0.7),
        chord([mt(7), mt(-1)], 3.0),
    ])
