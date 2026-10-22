"""Combination tones of the exact chain voicing 1 : phi : phi^2 : phi^3 on f0 = 220 Hz (pure sines).

First the four chord tones (220, 355.97, 575.97, 931.93 Hz). Then, quietly, the six combination
tones f2 - f1 and 2 f1 - f2 they generate: 220 phi^-2, 220 phi^-1, 220, 220 phi, 220 phi^2 and
2 * 220 phi (84.03, 135.97, 220, 355.97, 575.97, 711.93 Hz), every one a golden-chain pitch.
Then the chord again with those tones underneath."""
from _lib import PHI, at, seq, silence, sine

F0 = 220.0


def render():
    tones = [F0 * PHI ** k for k in range(4)]
    combos = [F0 * PHI ** -2, F0 / PHI, F0, F0 * PHI, F0 * PHI ** 2, 2 * F0 * PHI]
    ch = at([(0, sine(f, 5.0, 0.18)) for f in tones])
    cs = at([(0, sine(f, 5.0, 0.07)) for f in combos])
    both = at([(0, sine(f, 6.0, 0.16)) for f in tones] + [(0, sine(f, 6.0, 0.05)) for f in combos])
    return seq([ch, silence(0.6), cs, silence(0.6), both])
