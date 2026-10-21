"""Reading, layers demo: on C4, the 12-ET major third (400 c), the 12-ET minor third (300 c), then the
exact golden third 2/phi (366.91 c), first as melodic pairs and then together."""
from _lib import PHI, chord, freq, seq, silence, tone

C4 = freq(60)


def render():
    maj, mnr, gold = freq(64), freq(63), C4 * 2 / PHI
    out = []
    for top in (maj, mnr, gold):
        out += [tone(C4, 0.7), tone(top, 0.7), chord([C4, top], 1.8), silence(0.7)]
    return seq(out)
