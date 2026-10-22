"""The golden sixth over C4 in three tunings: exact phi (833.09 c), 36-ET (25 steps, 833.33 c) and
13-ET (9 steps, 830.77 c); then the exact and 13-ET versions of the upper note together."""
from _lib import PHI, at, chord, freq, seq, silence, sine

C4 = freq(60)


def render():
    exact = C4 * PHI                       # 423.33 Hz
    et36 = C4 * 2 ** (25 / 36)             # 423.39 Hz (0.06 Hz above exact)
    et13 = C4 * 2 ** (9 / 13)              # 422.76 Hz (0.57 Hz below exact)
    clips = [chord([C4, f], 2.2) for f in (exact, et36, et13)]
    out = []
    for c in clips:
        out += [c, silence(0.5)]
    out += [at([(0, sine(exact, 6.0, 0.25)), (0, sine(et13, 6.0, 0.25))])]
    return seq(out)
