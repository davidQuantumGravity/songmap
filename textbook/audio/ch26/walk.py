"""A walk from the exact golden triad to the just major triad 4:5:6, in four equal steps in the
(third, fifth) plane: (366.91, 733.82) -> (371.76, 725.85) -> (376.61, 717.89) -> (381.46, 709.92)
-> (386.31, 701.96) cents above C4. First on harmonic tones (partials 1-8), then on golden-spectrum tones
(the eleven partials 2^m phi^n, 0 <= m, n <= 3, below 9). Amplitudes 0.88^i, as in the roughness model
of reference/golden/explore.py. Modelled roughness along the walk:
harmonic 1.50, 1.48, 1.42, 1.33, 1.19 (downhill to major); golden 2.08, 2.50, 2.77, 2.94, 3.05 (uphill)."""
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


def triad(f0, cents, spec, dur=1.8):
    return stereo(0.03 * sum(additive(f0 * 2 ** (c / 1200), spec, dur) for c in cents))


def render():
    c4 = freq(60)
    c = lambda r: 1200 * np.log2(r)
    g3, g5 = c(2 / PHI), c(4 / PHI ** 2)
    j3, j5 = c(5 / 4), c(3 / 2)
    path = [(0, g3 + s * (j3 - g3), g5 + s * (j5 - g5)) for s in (0, 0.25, 0.5, 0.75, 1)]
    harm = list(range(1, 9))
    gold = sorted({2 ** m * PHI ** n for m in range(4) for n in range(4) if 2 ** m * PHI ** n < 9})
    return seq([seq([triad(c4, p, harm) for p in path], gap=0.25), silence(0.8),
                seq([triad(c4, p, gold) for p in path], gap=0.25)])
