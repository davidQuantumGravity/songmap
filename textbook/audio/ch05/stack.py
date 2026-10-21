"""Ch. 5, stacking fifths: pure 3:2 fifths climb from C3 (C3-G3, G3-D4, D4-A4, A4-E5), then the
Pythagorean major scale on C4 with every note folded into one octave from the chain F C G D A E B:
1, 9/8, 81/64, 4/3, 3/2, 27/16, 243/128, 2 (0, 203.91, 407.82, 498.04, 701.96, 905.87, 1109.78, 1200 c)."""
from _lib import chord, freq, seq, silence, tone

C3 = freq(48)
C4 = freq(60)


def render():
    q = 1.5
    climb = [chord([C3 * q ** k, C3 * q ** (k + 1)], 1.3) for k in range(4)]
    scale = [1, 9 / 8, 81 / 64, 4 / 3, 3 / 2, 27 / 16, 243 / 128, 2]
    melody = [tone(C4 * r, 0.55) for r in scale]
    return seq(climb + [silence(0.8)] + melody + [silence(0.3), chord([C4, C4 * 81 / 64, C4 * 3 / 2], 2.5)])
