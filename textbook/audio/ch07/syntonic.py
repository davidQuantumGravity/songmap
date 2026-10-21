"""Ch. 7, the syntonic comma: over C4, the Pythagorean major third E = 81/64 (407.82 c), then the
just major third 5/4 (386.31 c); then the Pythagorean triad C E G (64:81:96) and the just triad
4:5:6. They differ only in E, by 81/80 = 21.51 c. The Pythagorean third beats fast (the fifth
partial of C against the fourth of E: about 16.4 Hz at C4); the just third is still."""
from _lib import chord, freq, seq, silence

C4 = freq(60)


def render():
    return seq([
        chord([C4, C4 * 81 / 64], 3.0), silence(0.5), chord([C4, C4 * 5 / 4], 3.0), silence(0.9),
        chord([C4, C4 * 81 / 64, C4 * 3 / 2], 3.0), silence(0.5), chord([C4, C4 * 5 / 4, C4 * 3 / 2], 3.0),
    ])
