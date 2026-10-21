"""The three just major triads that make up the just C major scale, each tuned 4:5:6: F A C, C E G, G B D; then the scale they build.
On the ratio lattice they are three neighbouring triangles: F = 4/3, A = 5/3, C = 1, E = 5/4, G = 3/2, B = 15/8, D = 9/8."""
from _lib import chord, tone, silence, seq, freq


def render():
    c4 = freq(60)
    tri = [[4 / 3, 5 / 3, 2], [1, 5 / 4, 3 / 2], [3 / 4, 15 / 16, 9 / 8], [1, 5 / 4, 3 / 2]]
    scale = [1, 9 / 8, 5 / 4, 4 / 3, 3 / 2, 5 / 3, 15 / 8, 2]
    return seq([seq([chord([c4 * r for r in t], 1.8, "clean/organ") for t in tri], gap=0.15), silence(0.6),
                seq([tone(c4 * r, 0.55, "clean/organ") for r in scale], gap=0.05)])
