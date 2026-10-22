"""Three classic waves on C3, each built from sines: sawtooth (all harmonics, 1/k), square (odd harmonics, 1/k), triangle (odd harmonics, 1/k^2)."""
import numpy as np

from _lib import SR, stereo, silence, seq, freq


def wave(f0, ks, amp, dur):
    t = np.arange(int(dur * SR)) / SR
    x = sum(a * np.sin(2 * np.pi * k * f0 * t) for k, a in zip(ks, amp))
    x = 0.12 * x / np.sqrt(np.mean(x * x))            # equal loudness (equal RMS)
    k = int(0.02 * SR)
    x[:k] *= np.linspace(0, 1, k)
    x[-k:] *= np.linspace(1, 0, k)
    return stereo(x)


def render():
    f0 = freq(48)
    K = 40
    saw = wave(f0, range(1, K + 1), [(-1) ** (k + 1) / k for k in range(1, K + 1)], 2.5)
    odd = list(range(1, K + 1, 2))
    sq = wave(f0, odd, [1 / k for k in odd], 2.5)
    tri = wave(f0, odd, [(-1) ** ((k - 1) // 2) / k ** 2 for k in odd], 2.5)
    return seq([saw, silence(0.5), sq, silence(0.5), tri])
