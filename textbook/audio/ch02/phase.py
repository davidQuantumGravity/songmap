"""The same ten harmonics of C3 (amplitudes 1/k) with two different sets of phases, A B A B: very different waveforms, nearly the same sound."""
import numpy as np

from _lib import SR, stereo, silence, seq, freq


def tone_with_phases(f0, ph, dur):
    t = np.arange(int(dur * SR)) / SR
    x = sum(np.sin(2 * np.pi * k * f0 * t + ph[k - 1]) / k for k in range(1, 11))
    x = 0.12 * x / np.sqrt(np.mean(x * x))
    k = int(0.03 * SR)
    x[:k] *= np.linspace(0, 1, k)
    x[-k:] *= np.linspace(1, 0, k)
    return stereo(x)


def render():
    f0 = freq(48)
    a = tone_with_phases(f0, [0.0] * 10, 2.0)
    rng = np.random.default_rng(7)
    b = tone_with_phases(f0, list(rng.uniform(0, 2 * np.pi, 10)), 2.0)
    return seq([a, silence(0.4), b, silence(0.4), a, silence(0.4), b])
