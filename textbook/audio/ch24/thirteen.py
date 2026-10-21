"""golden13 on C4 in three tunings, each up one octave:
exact phi (steps 99.27 c and 69.10 c), 36-ET (100 c and 66.67 c) and 13-ET (13 equal steps of 92.31 c)."""
from _lib import PHI, freq, seq, silence, tone

C4 = freq(60)


def fold(f):
    while f >= 2 * C4:
        f /= 2
    while f < C4:
        f *= 2
    return f


def render():
    exact = sorted(fold(C4 * PHI ** j) for j in range(-6, 7))
    et36 = sorted(fold(C4 * 2 ** ((25 * j % 36) / 36)) for j in range(-6, 7))
    et13 = [C4 * 2 ** (k / 13) for k in range(13)]
    out = []
    for sc in (exact, et36, et13):
        out += [tone(f, 0.3, "clean/keys", vel=0.5) for f in sc + [2 * C4]] + [silence(0.9)]
    return seq(out)
