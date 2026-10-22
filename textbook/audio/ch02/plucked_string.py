"""A plucked string built from its modes: plucked at the middle (odd modes only), then near the end (1/10 of the length).

A string of length L plucked at x = pL from a triangle shape has mode amplitudes
b_n = 2h sin(n pi p) / (n^2 pi^2 p (1 - p)); each mode n vibrates at n times the fundamental.
Higher modes are given shorter decay times, as on a real string.
"""
import numpy as np

from _lib import SR, stereo, silence, seq, freq


def pluck(f0, p, dur, modes=30):
    t = np.arange(int(dur * SR)) / SR
    x = np.zeros_like(t)
    for n in range(1, modes + 1):
        if f0 * n > 0.45 * SR:
            break
        b = 2 * np.sin(n * np.pi * p) / (n * n * np.pi ** 2 * p * (1 - p))
        t60 = 3.0 / (1 + 0.25 * (n - 1))
        x += b * np.sin(2 * np.pi * f0 * n * t) * np.exp(-6.9 * t / t60)
    k = int(0.002 * SR)
    x[:k] *= np.linspace(0, 1, k)
    x[-int(0.05 * SR):] *= np.linspace(1, 0, int(0.05 * SR))
    return stereo(x / np.max(np.abs(x)) * 0.5)


def render():
    f0 = freq(45)                    # A2 = 110 Hz
    return seq([pluck(f0, 0.5, 2.5), silence(0.3), pluck(f0, 0.5, 2.5), silence(0.8),
                pluck(f0, 0.1, 2.5), silence(0.3), pluck(f0, 0.1, 2.5)])
