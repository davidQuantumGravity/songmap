"""ch30: the same five dyads on C4 in exact ratios, first on a harmonic tone, then on a
golden-spectrum tone with the identical envelope (only the partial ratios change).
Order: perfect fifth 3/2, major third 5/4, golden sixth phi, golden third 2/phi, golden fifth 4/phi^2."""
from _lib import PHI, chord, silence, seq

F0 = 261.63
RATIOS = [3 / 2, 5 / 4, PHI, 2 / PHI, 4 / PHI ** 2]


def block(spectrum):
    out = []
    for r in RATIOS:
        out += [chord([F0, F0 * r], 1.8, "clean/organ", spectrum=spectrum, vel_bright=0), silence(0.35)]
    return seq(out)


def render():
    return seq([block(0), silence(1.0), block(1)])
