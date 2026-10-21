"""Ch. 7, other equal divisions: the major triad on C4 in 12-ET (thirds 400 c, fifth 700 c), 19-ET
(6 and 11 steps: 378.95 c, 694.74 c), 31-ET (10 and 18 steps: 387.10 c, 696.77 c), 53-ET (17 and 31
steps: 384.91 c, 701.89 c), and finally just 4:5:6 (386.31 c, 701.96 c)."""
from _lib import chord, freq, seq, silence

C4 = freq(60)


def render():
    out = []
    for n, third, fifth in ((12, 4, 7), (19, 6, 11), (31, 10, 18), (53, 17, 31)):
        out += [chord([C4, C4 * 2 ** (third / n), C4 * 2 ** (fifth / n)], 2.6), silence(0.5)]
    out.append(chord([C4, C4 * 5 / 4, C4 * 3 / 2], 3.0))
    return seq(out)
