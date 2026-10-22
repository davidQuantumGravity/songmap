"""Register sets the beat band: one close-voiced golden seventh, exact, at two roots.

Cg7 in exact close voicing 1 : 2/phi : 4/phi^2 : 8/phi^3 on a harmonic clean organ tone (8 partials).
Its beats fall at f0*phi^-6 * (1, 2/phi, 4/phi^2) and 2*f0*phi^-6 (GOLDEN_THEORY 3.3).
  1. f0 = 10*phi^6 = 179.44 Hz: beats at 10.00, 12.36, 15.28 and 20.00 Hz (12 s)
  2. f0 = 110 Hz:               beats at  6.13,  7.58,  9.37 and 12.26 Hz (12 s)
"""
from _lib import PHI, chord, silence, seq

SHAPE = [1, 2 / PHI, 4 / PHI ** 2, 8 / PHI ** 3]


def render():
    hi = 10 * PHI ** 6
    return seq([chord([hi * r for r in SHAPE], 12.0, "clean/organ", attack=0.8, release=1.5),
                silence(0.5),
                chord([110.0 * r for r in SHAPE], 12.0, "clean/organ", attack=0.8, release=1.5)])
