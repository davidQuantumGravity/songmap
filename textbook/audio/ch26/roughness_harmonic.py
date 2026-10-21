"""Three triads on C4 with a harmonic tone (8 partials, as in the roughness model):
12-ET C major, the exact golden triad 1 : 2/phi : 4/phi^2, and 12-ET C diminished.
Modelled roughness (Sethares): major 1.32, golden 1.50, diminished 1.67."""
from _lib import PHI, chord, freq, seq, silence

C4 = freq(60)


def render():
    major = [C4, freq(64), freq(67)]
    golden = [C4, C4 * 2 / PHI, C4 * 4 / PHI ** 2]
    dim = [C4, freq(63), freq(66)]
    out = []
    for c in (major, golden, dim):
        out += [chord(c, 3.0, "clean/organ", partials=8), silence(0.6)]
    return seq(out)
