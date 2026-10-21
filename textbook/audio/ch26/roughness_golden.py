"""The same three triads (C major, exact golden, C diminished) on a golden-spectrum tone whose
partials are 2^m * phi^n (1, 1.618, 2, 2.618, 3.236, 4, ...). Modelled roughness flips:
golden 2.08, major 3.17, diminished 3.19."""
from _lib import PHI, chord, freq, seq, silence

C4 = freq(60)
GOLD = dict(spectrum=1, partials=10, rolloff=1.3, attack=0.05, release=0.4)


def render():
    major = [C4, freq(64), freq(67)]
    golden = [C4, C4 * 2 / PHI, C4 * 4 / PHI ** 2]
    dim = [C4, freq(63), freq(66)]
    out = []
    for c in (major, golden, dim):
        out += [chord(c, 3.0, "clean/organ", **GOLD), silence(0.6)]
    return seq(out)
