"""The comma pump in just intonation: C - Am - Dm - G - C, every common tone held exactly, every new note a pure third or fifth.
Then the first C chord and the last C chord side by side, and their top C's together as sines (beating about 3.2 times a second)."""
from fractions import Fraction as F

from _lib import chord, sine, silence, seq, freq

# ratios to C4; each chord shares a held note with the one before
PUMP = [
    [F(1, 2), F(3, 4), F(1), F(5, 4)],              # C : C3 G3 C4 E4
    [F(5, 12), F(5, 6), F(1), F(5, 4)],             # Am: A2 A3 C4 E4   (A = 5/3; C, E held)
    [F(5, 9), F(5, 6), F(10, 9), F(4, 3)],          # Dm: D3 A3 D4 F4   (A held; D = 10/9, F = 4/3)
    [F(10, 27), F(25, 27), F(10, 9), F(40, 27)],    # G : G2 B3 D4 G4   (D held; G = 40/27, B = 50/27)
    [F(40, 81), F(80, 81), F(100, 81), F(40, 27)],  # C : C3 C4 E4 G4   (G held; C = 80/81)
]


def render():
    c4 = freq(60)
    fr = lambda rs: [c4 * float(r) for r in rs]  # noqa: E731
    first = fr([F(1, 2), F(1), F(5, 4), F(3, 2)])  # the opening chord in the closing voicing
    last = fr(PUMP[-1])
    return seq([seq([chord(fr(v), 1.7, "clean/organ") for v in PUMP]), silence(0.9),
                chord(first, 2.2, "clean/organ"), silence(0.3), chord(last, 2.2, "clean/organ"), silence(0.8),
                sine(c4, 4.0, 0.25, 0.05) + sine(c4 * 80 / 81, 4.0, 0.25, 0.05)])
