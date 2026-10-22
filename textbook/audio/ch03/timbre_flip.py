"""C major (12-ET) and the exact golden triad 1 : 2/phi : 4/phi^2 on C4. First on harmonic tones (partials 1-8): major, golden.
Then on golden-spectrum tones (the eleven partials 2^m phi^n with 0 <= m, n <= 3 below 9; phi^4 is left out, as in explore.py): golden, major. Amplitudes 0.88^i, as in the roughness measurements."""
import numpy as np

from _lib import SR, PHI, stereo, silence, seq, freq


def additive(f0, ratios, dur):
    t = np.arange(int(dur * SR)) / SR
    x = sum(0.88 ** i * np.sin(2 * np.pi * f0 * r * t + np.pi * i * i / len(ratios)) for i, r in enumerate(ratios))
    n = int(0.06 * SR)
    env = np.ones_like(t)
    env[:n] = 0.5 - 0.5 * np.cos(np.pi * np.arange(n) / n)
    env[-n:] = env[:n][::-1]
    return x * env


def triad(f0, ratios, spec, dur=3.0):
    x = sum(additive(f0 * r, spec, dur) for r in ratios)
    return stereo(0.03 * x)


def render():
    c4 = freq(60)
    major = [1, 2 ** (4 / 12), 2 ** (7 / 12)]
    golden = [1, 2 / PHI, 4 / PHI ** 2]
    harm = list(range(1, 9))
    gold = sorted({2 ** m * PHI ** n for m in range(4) for n in range(4) if 2 ** m * PHI ** n < 9})
    return seq([triad(c4, major, harm), triad(c4, golden, harm), silence(0.8),
                triad(c4, golden, gold), triad(c4, major, gold)], gap=0.5)
