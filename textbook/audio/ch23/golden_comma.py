"""The golden comma: C4, then the note 13 golden sixths up folded down 9 octaves (C4 * phi^13 / 2^9),
then both together. 30.17 c apart: on pure sines they beat at about 4.6 Hz."""
from _lib import PHI, at, freq, silence, seq, sine

C4 = freq(60)


def render():
    up = C4 * PHI ** 13 / 2 ** 9          # 266.23 Hz
    both = at([(0, sine(C4, 6.0, 0.25)), (0, sine(up, 6.0, 0.25))])
    return seq([sine(C4, 2.0), silence(0.4), sine(up, 2.0), silence(0.6), both])
