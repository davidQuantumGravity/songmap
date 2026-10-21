"""Two major thirds on C4: Pythagorean 81/64 (331.12 Hz, four fifths up, two octaves down), then just 5/4 (327.03 Hz).
Then the two upper notes alone as pure sines, together: they beat about 4 times a second (the syntonic comma, 21.51 c)."""
from _lib import chord, sine, silence, seq, freq


def render():
    c4 = freq(60)
    e_p, e_j = c4 * 81 / 64, c4 * 5 / 4
    return seq([chord([c4, e_p], 3.0, "clean/organ"), silence(0.5), chord([c4, e_j], 3.0, "clean/organ"), silence(0.8),
                sine(e_p, 1.5, 0.3), silence(0.2), sine(e_j, 1.5, 0.3), silence(0.5),
                sine(e_p, 4.0, 0.25, 0.05) + sine(e_j, 4.0, 0.25, 0.05)])
