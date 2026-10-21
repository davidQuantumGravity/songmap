"""What the golden band ladder's rates sound like: 3.82, 6.18, 10 and 16.18 pulses per second.

A soft 330 Hz tone, amplitude-modulated (raised-cosine pulses, no clicks) at each rate for 5 s.
The rates are 10 * phi^k for k = -2, -1, 0, 1: the series the golden-ratio EEG hypothesis is
usually illustrated with (anchored here at 10 Hz for illustration). This is a listening aid for the
rates themselves; it is not a claim that hearing them changes brain rhythms.
"""
import numpy as np
from _lib import SR, PHI, silence, seq

RATES = [10 / PHI ** 2, 10 / PHI, 10.0, 10 * PHI]


def pulsed(f, rate, dur, depth=0.85):
    n = int(dur * SR)
    t = np.arange(n) / SR
    am = 1 - depth * (0.5 + 0.5 * np.cos(2 * np.pi * rate * t))   # smooth isochronic pulse
    x = 0.3 * am * (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t))
    k = int(0.3 * SR)
    w = 0.5 - 0.5 * np.cos(np.pi * np.arange(k) / k)
    x[:k] *= w
    x[-k:] *= w[::-1]
    return np.stack([x, x], 1)


def render():
    return seq([pulsed(330.0, r, 5.0) for r in RATES], gap=0.8)
