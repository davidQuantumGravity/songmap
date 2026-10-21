"""Ch. 5, the Pythagorean comma: C4, then the C reached by twelve pure fifths from C and folded down
seven octaves (B#, 531441/524288 above C4 = 23.46 c), then both together: they beat at about 3.57 Hz
(261.63 Hz against 265.20 Hz)."""
from _lib import chord, freq, seq, silence, tone

C4 = freq(60)
BS = C4 * 3 ** 12 / 2 ** 19


def render():
    return seq([tone(C4, 1.6), silence(0.3), tone(BS, 1.6), silence(0.3), tone(C4, 1.0), tone(BS, 1.0),
                silence(0.5), chord([C4, BS], 6.0)])
