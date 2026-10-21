"""Preface: from the golden sixth to the golden triad, in exact ratios on C4, then a diminished triad for contrast.

Golden sixth 1 : phi (833.09 c); golden third 1 : 2/phi (366.91 c); golden triad 1 : 2/phi : 4/phi^2;
12-ET diminished triad C4 Eb4 Gb4; golden triad again.
"""
from _lib import PHI, chord, freq, seq, silence

C4 = freq(60)


def render():
    sixth = [C4, C4 * PHI]
    third = [C4, C4 * 2 / PHI]
    golden = [C4, C4 * 2 / PHI, C4 * 4 / PHI ** 2]
    dim = [freq(60), freq(63), freq(66)]
    return seq([
        chord(sixth, 2.2), silence(0.6),
        chord(third, 2.2), silence(0.6),
        chord(golden, 3.0), silence(0.9),
        chord(dim, 3.0), silence(0.9),
        chord(golden, 3.5),
    ])
