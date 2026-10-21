"""The golden sixth phi (833.09 c) between the 12-ET minor sixth (800 c) and major sixth (900 c), on C4."""
from _lib import PHI, chord, freq, silence, seq, tone

C4 = freq(60)                      # 261.63 Hz


def render():
    m6, g6, M6 = freq(68), C4 * PHI, freq(69)        # Ab4 415.30 Hz, 423.33 Hz, A4 440.00 Hz
    return seq([chord([C4, m6], 2.4), silence(0.5),
                chord([C4, g6], 2.4), silence(0.5),
                chord([C4, M6], 2.4), silence(0.8),
                tone(C4, 0.9), tone(g6, 1.6), silence(0.3),
                chord([C4, g6], 3.0)])
