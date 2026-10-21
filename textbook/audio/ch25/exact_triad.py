"""The golden triad in exact ratios on C4: close position 1 : 2/phi : 4/phi^2 (C vE ^G),
then the chain voicing 1 : phi : phi^2 (^G3 vE4 C5: fifth, third, root, each a golden sixth apart),
then the 36-ET close triad (0, 11, 22 sixth-steps) for comparison."""
from _lib import PHI, chord, freq, seq, silence, tone

C4 = freq(60)


def render():
    close = [C4, C4 * 2 / PHI, C4 * 4 / PHI ** 2]              # 261.63, 323.39, 399.73 Hz
    g3 = C4 * 4 / PHI ** 2 / 2                                  # ^G3 = 199.86 Hz
    chain = [g3, g3 * PHI, g3 * PHI ** 2]                       # 199.86, 323.39, 523.25 Hz
    et36 = [C4 * 2 ** (s / 36) for s in (0, 11, 22)]
    arp = [tone(f, 0.5, "clean/keys") for f in chain]
    return seq([chord(close, 3.0), silence(0.6), *arp, chord(chain, 3.0), silence(0.6), chord(et36, 3.0)])
