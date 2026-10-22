"""Each golden interval against its nearest 12-ET neighbour, on C4 (exact phi ratios).

golden third 2/phi = 366.91 c vs major third 400 c; golden fifth 4/phi^2 = 733.82 c vs perfect fifth 700 c;
golden seventh 8/phi^3 = 1100.73 c vs major seventh 1100 c; then the golden triad and seventh.
"""
from _lib import PHI, chord, freq, silence, seq

C4 = freq(60)


def render():
    g3, g5, g7 = C4 * 2 / PHI, C4 * 4 / PHI ** 2, C4 * 8 / PHI ** 3
    pairs = [(freq(64), g3), (freq(67), g5), (freq(71), g7)]
    clips = []
    for west, gold in pairs:
        clips += [chord([C4, west], 1.8), silence(0.3), chord([C4, gold], 1.8), silence(0.7)]
    clips += [chord([C4, g3, g5], 3.0), silence(0.5), chord([C4, g3, g5, g7], 3.5)]
    return seq(clips)
