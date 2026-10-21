"""The timbre flip. Two chords on C4 = 261.63 Hz: C major (12-ET, 0 400 700 c) and the exact golden
triad (1 : 2/phi : 4/phi^2 = 0, 366.91, 733.82 c). First on a harmonic spectrum (10 partials k^-1.2),
then on a golden spectrum (10 partials 2^m * phi^n, same amplitudes). 2.4 s per chord.
"""
from _lib import PHI, chord, seq, silence

C4 = 261.63
MAJOR = [C4, C4 * 2 ** (4 / 12), C4 * 2 ** (7 / 12)]
GOLDEN = [C4, C4 * 2 / PHI, C4 * 4 / PHI ** 2]


def render():
    out = []
    for spec in (0, 1):
        p = dict(partials=10, rolloff=1.2, spectrum=spec)
        out += [chord(MAJOR, 2.4, "clean/organ", vel=0.5, **p), silence(0.5),
                chord(GOLDEN, 2.4, "clean/organ", vel=0.5, **p), silence(1.0)]
    return seq(out)
