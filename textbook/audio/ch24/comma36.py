"""The 36-comma: C4, then the note 36 golden sixths up folded down 25 octaves (C4 * phi^36 / 2^25,
8.75 c flat), then both together on pure sines: a slow beat of about 1.3 Hz."""
from _lib import PHI, at, freq, seq, silence, sine

C4 = freq(60)


def render():
    low = C4 * PHI ** 36 / 2 ** 25        # 260.31 Hz
    both = at([(0, sine(C4, 8.0, 0.25)), (0, sine(low, 8.0, 0.25))])
    return seq([sine(C4, 2.0), silence(0.4), sine(low, 2.0), silence(0.6), both])
