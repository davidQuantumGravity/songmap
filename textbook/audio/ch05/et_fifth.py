"""Ch. 5, why twelve: a pure fifth C4-G4 (3:2, 701.96 c), then the 12-ET fifth (700 c, 1.96 c
narrow). The pure fifth is still; in the tempered one the third partial of C (784.88 Hz) and the
second partial of G (783.99 Hz) beat slowly, a little under once a second (0.89 Hz)."""
from _lib import chord, freq, seq, silence

C4 = freq(60)


def render():
    return seq([chord([C4, C4 * 1.5], 6.0), silence(0.8), chord([C4, freq(67)], 6.0)])
