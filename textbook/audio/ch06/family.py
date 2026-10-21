"""Ch. 6, one family: the Pythagorean pentatonic C D E G A (chain C..E, steps 203.91 and 294.13 c),
the diatonic C D E F G A B (chain F..B, steps 203.91 and 90.22 c) and the chromatic scale from Eb to
G# (steps 113.69 and 90.22 c), each played up from C4 to C5 in exact ratios."""
from _lib import freq, seq, silence, tone

C4 = freq(60)


def fold(r):
    while r >= 2:
        r /= 2
    while r < 1:
        r *= 2
    return r


def scale(lo, hi):
    return sorted(fold(1.5 ** k) for k in range(lo, hi + 1)) + [2.0]


def render():
    out = []
    for (lo, hi), d in (((0, 4), 0.45), ((-1, 5), 0.4), ((-3, 8), 0.3)):
        out += [tone(C4 * r, d) for r in scale(lo, hi)] + [silence(0.9)]
    return seq(out)
