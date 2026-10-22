"""Ch. 5, the wolf: in a twelve-note Pythagorean tuning from Eb to G#, every fifth is pure (701.96 c)
except G#-Eb, which is short by the whole comma (678.49 c). We hear C-G, E-B and A-E, then the wolf
G#-Eb, then C-G again. Root notes around G3."""
from _lib import chord, freq, seq, silence

C4 = freq(60)


def fold(r):
    while r >= 2:
        r /= 2
    while r < 1:
        r *= 2
    return r


def p(k, octave=0):
    """Chain position k (C = 0, G = 1, ... ; Eb = -3), folded into the octave above C4, shifted."""
    return C4 * fold(1.5 ** k) * 2 ** octave


def render():
    pure = [(0, 1), (4, 5), (3, 4)]          # C-G, E-B, A-E
    clips = []
    for lo, hi in pure:
        a = p(lo, -1)
        b = p(hi, -1)
        while b <= a:
            b *= 2
        clips += [chord([a, b], 2.0), silence(0.3)]
    gs, eb = p(8, -1), p(-3, 0)               # G#3 and Eb4: 678.49 c apart
    clips += [silence(0.4), chord([gs, eb], 3.2), silence(0.6), chord([p(0, -1), p(1, -1)], 2.4)]
    return seq(clips)
