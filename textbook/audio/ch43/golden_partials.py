"""A golden spectrum, built partial by partial on A3 = 220 Hz.

The clean instrument's golden spectrum (spectrum: 1) uses the ratios 2^m * phi^n sorted by size.
The first ten are 1, phi, 2, phi^2, 2phi, 4, phi^3, 2phi^2, 4phi, phi^4
(1, 1.618, 2, 2.618, 3.236, 4, 4.236, 5.236, 6.472, 6.854). They enter one per second with
amplitudes k^-1.3 (k = rank), the rolloff of the clean/glass preset; then the whole tone holds 3 s.
"""
import numpy as np
from _lib import SR, PHI, seq

F0 = 220.0
RATIOS = sorted({2 ** m * PHI ** n for m in range(8) for n in range(8)})[:10]


def render():
    dur = 13.0
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k, r in enumerate(RATIOS, start=1):
        on = np.clip((t - (k - 1) * 1.0) / 0.15, 0, 1)
        x += k ** -1.3 * (0.5 - 0.5 * np.cos(np.pi * on)) * np.sin(2 * np.pi * F0 * r * t + np.pi * k * k / 10)
    m = int(0.5 * SR)
    x[-m:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(m) / m)
    return np.stack([x, x], 1) * 0.25
