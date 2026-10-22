"""A linear sweep 110 -> 1760 Hz (constant hertz per second), then an exponential one (constant octaves per second), 10 s each."""
import numpy as np

from _lib import SR, stereo, sweep, silence, seq


def linear_sweep(f0, f1, dur, amp=0.25):
    t = np.arange(int(dur * SR)) / SR
    x = amp * np.sin(2 * np.pi * (f0 * t + (f1 - f0) * t * t / (2 * dur)))
    k = int(0.02 * SR)
    x[:k] *= np.linspace(0, 1, k)
    x[-k:] *= np.linspace(1, 0, k)
    return stereo(x)


def render():
    return seq([linear_sweep(110.0, 1760.0, 10.0), silence(1.0), sweep(110.0, 1760.0, 10.0)])
