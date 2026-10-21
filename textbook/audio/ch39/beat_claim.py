"""The corrected claim, by ear: golden triad and golden seventh in exact close voicing on 110 Hz.

Harmonic clean organ (8 partials), 10 s each.
  1. Cg  = 1 : 2/phi : 4/phi^2: strongest beats at 6.13 and 7.58 Hz = 110 phi^-6 x (1, 2/phi),
     plus 12.26 Hz = 2 x 6.13 Hz. The rates go 1 : 2/phi : 2, a golden third and an octave.
  2. Cg7 = 1 : 2/phi : 4/phi^2 : 8/phi^3: beats at 6.13, 7.58 and 9.37 Hz = 110 phi^-6 x (1, 2/phi, 4/phi^2),
     a golden triad in rhythm, plus 12.26 Hz (the seventh against the root's octave).
"""
from _lib import PHI, chord, silence, seq


def render():
    tri = [110 * r for r in (1, 2 / PHI, 4 / PHI ** 2)]
    sev = tri + [110 * 8 / PHI ** 3]
    return seq([chord(tri, 10.0, "clean/organ", attack=0.8, release=1.2), silence(0.8),
                chord(sev, 10.0, "clean/organ", attack=0.8, release=1.2)])
