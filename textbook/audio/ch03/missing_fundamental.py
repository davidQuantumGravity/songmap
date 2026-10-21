"""A tone on C3 (130.81 Hz) with harmonics 1-10, then with harmonic 1 removed, then 1-2 removed, then 1-3 removed; finally a pure sine at 130.81 Hz for comparison."""
import numpy as np

from _lib import SR, stereo, silence, seq, sine, freq


def partials(f0, ks, dur):
    t = np.arange(int(dur * SR)) / SR
    x = sum(np.sin(2 * np.pi * k * f0 * t + np.pi * k * k / 10) / k ** 0.7 for k in ks)
    x = 0.12 * x / np.sqrt(np.mean(x * x))
    n = int(0.04 * SR)
    x[:n] *= np.linspace(0, 1, n)
    x[-n:] *= np.linspace(1, 0, n)
    return stereo(x)


def render():
    f0 = freq(48)
    clips = [partials(f0, range(lo, 11), 2.2) for lo in (1, 2, 3, 4)]
    return seq(clips + [sine(f0, 2.2, 0.17, 0.04)], gap=0.45)
