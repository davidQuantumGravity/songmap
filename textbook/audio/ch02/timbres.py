"""One pitch (C3), five spectra at equal loudness: sine; soft (1/k^2); bright (1/k); hollow (odd harmonics only); golden (partials 2^m phi^n)."""
import numpy as np

from _lib import SR, PHI, stereo, silence, seq, freq


def additive(f0, ratios, amps, dur):
    t = np.arange(int(dur * SR)) / SR
    x = sum(a * np.sin(2 * np.pi * f0 * r * t + np.pi * i * i / len(ratios))
            for i, (r, a) in enumerate(zip(ratios, amps)) if f0 * r < 0.45 * SR)
    x = 0.12 * x / np.sqrt(np.mean(x * x))
    k = int(0.04 * SR)
    x[:k] *= np.linspace(0, 1, k)
    x[-k:] *= np.linspace(1, 0, k)
    return stereo(x)


def render():
    f0 = freq(48)
    h = list(range(1, 17))
    odd = list(range(1, 17, 2))
    gold = sorted({2 ** m * PHI ** n for m in range(6) for n in range(6)})[:12]
    clips = [additive(f0, [1], [1], 2.0),
             additive(f0, h, [1 / k ** 2 for k in h], 2.0),
             additive(f0, h, [1 / k for k in h], 2.0),
             additive(f0, odd, [1 / k for k in odd], 2.0),
             additive(f0, gold, [1 / (i + 1) for i in range(len(gold))], 2.0)]
    return seq(clips, gap=0.5)
