"""Preface: the Fibonacci staircase. Dyads on middle C at the convergents of phi's continued fraction
[1; 1, 1, 1, ...]: 2/1, 3/2, 5/3, 8/5, 13/8, 21/13, then exact phi (the golden sixth, 833.09 c).

The upper note alternates above and below phi: 1200.00, 701.96, 884.36, 813.69, 840.53, 830.25 c,
against 833.09 c (gaps +366.91, -131.14, +51.27, -19.40, +7.44, -2.84 c).
"""
from _lib import PHI, chord, freq, seq, silence

C4 = freq(60)
STEPS = [(2, 1), (3, 2), (5, 3), (8, 5), (13, 8), (21, 13)]


def render():
    parts = []
    for p, q in STEPS:
        parts += [chord([C4, C4 * p / q], 1.8), silence(0.35)]
    parts += [silence(0.4), chord([C4, C4 * PHI], 3.2)]
    return seq(parts)
