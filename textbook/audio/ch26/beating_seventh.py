"""Close-voiced golden chords in exact ratios on harmonic tones (6 equal-ish partials), f0 = 110 Hz.

Cg (1 : 2/phi : 4/phi^2): beats at 6.13, 7.58 and 12.26 Hz.
Cg7 (1 : 2/phi : 4/phi^2 : 8/phi^3): beats at 6.13, 7.58, 9.37 Hz = 110 phi^-6 x (1, 2/phi, 4/phi^2),
the golden triad in rhythm, plus 12.26 Hz = 2 x 110 phi^-6, the seventh against the root's octave.
Then Cg7 on f0 = 10 phi^6 = 179.44 Hz, where the slowest beat is 10 Hz."""
from _lib import PHI, chord, seq, silence

TONE = dict(partials=6, rolloff=0.6, attack=0.3, release=0.8)


def cg(f0, seventh=False):
    r = [1, 2 / PHI, 4 / PHI ** 2] + ([8 / PHI ** 3] if seventh else [])
    return [f0 * x for x in r]


def render():
    return seq([chord(cg(110.0), 7.0, "clean/organ", **TONE), silence(0.7),
                chord(cg(110.0, True), 9.0, "clean/organ", **TONE), silence(0.7),
                chord(cg(10 * PHI ** 6, True), 7.0, "clean/organ", **TONE)])
