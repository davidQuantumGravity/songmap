"""Building a sawtooth on C3 (130.81 Hz): add harmonic k with amplitude 1/k, one per second, up to 10; then the 40-harmonic sawtooth."""
import numpy as np

from _lib import SR, stereo, silence, seq, freq


def partial_sum(f0, kmax, dur):
    t = np.arange(int(dur * SR)) / SR
    x = sum(((-1) ** (k + 1)) * np.sin(2 * np.pi * k * f0 * t) / k for k in range(1, kmax + 1))
    return x


def render():
    f0 = freq(48)
    clips = []
    for K in list(range(1, 11)) + [40]:
        d = 1.1 if K < 40 else 3.0
        x = 0.25 * partial_sum(f0, K, d)
        k = int(0.015 * SR)
        x[:k] *= np.linspace(0, 1, k)
        x[-k:] *= np.linspace(1, 0, k)
        clips += [stereo(x), silence(0.12 if K < 10 else 0.6)]
    return seq(clips)
