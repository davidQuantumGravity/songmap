"""Reading, audio: the golden triad on C4 in 36-ET (C vE ^G = 0, 11, 22 sixth-steps), then in exact
ratios 1 : 2/phi : 4/phi^2. The third differs by 0.24 c and the fifth by 0.49 c."""
from _lib import PHI, chord, freq, seq, silence

C4 = freq(60)


def render():
    edo36 = [C4, C4 * 2 ** (11 / 36), C4 * 2 ** (22 / 36)]
    exact = [C4, C4 * 2 / PHI, C4 * 4 / PHI ** 2]
    return seq([chord(edo36, 4.0), silence(1.0), chord(exact, 4.0)])
