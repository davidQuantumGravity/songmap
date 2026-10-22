"""Harmonics 1 to 16 of C2 (65.41 Hz) as pure sines, one at a time, then all sixteen together (amplitudes 1/n)."""
import numpy as np

from _lib import SR, sine, silence, seq, stereo, freq


def render():
    f0 = freq(36)
    one = [sine(f0 * n, 0.6, amp=0.3, fade=0.02) for n in range(1, 17)]
    t = np.arange(int(4.0 * SR)) / SR
    x = sum(np.sin(2 * np.pi * f0 * n * t + np.pi * n * n / 16) / n for n in range(1, 17))
    x = 0.3 * x / np.max(np.abs(x))
    k = int(0.05 * SR)
    x[:k] *= np.linspace(0, 1, k)
    x[-k:] *= np.linspace(1, 0, k)
    return seq([seq(one, gap=0.08), silence(0.6), stereo(x)])
