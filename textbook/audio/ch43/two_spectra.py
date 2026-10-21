"""The same two chords on two spectra (exact ratios, root C4 = 261.63 Hz, 4 s each):

  harmonic spectrum (partials 1, 2, 3, ...):  just major 4:5:6, then golden 1 : 2/phi : 4/phi^2
  golden spectrum (partials 2^m * phi^n):     just major 4:5:6, then golden 1 : 2/phi : 4/phi^2

Both spectra: 10 partials, amplitudes k^-1.3, the same envelope. On the harmonic spectrum the major
triad is the calmer chord; on the golden spectrum the golden triad is (the timbre flip).
"""
from _lib import PHI, chord, silence, seq

C4 = 261.63
MAJOR = [1, 5 / 4, 3 / 2]
GOLD = [1, 2 / PHI, 4 / PHI ** 2]


def render():
    out = []
    for spec in (0, 1):
        for shape in (MAJOR, GOLD):
            out += [chord([C4 * r for r in shape], 4.0, "clean/organ", partials=10, rolloff=1.3,
                          spectrum=spec, attack=0.15, release=0.6), silence(0.5)]
        out.append(silence(0.8))
    return seq(out)
