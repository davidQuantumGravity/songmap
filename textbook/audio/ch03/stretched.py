"""Octaves on A3 (220 Hz). Harmonic tones: 2:1 then 2.1:1. Stretched tones (partials k^log2(2.1)): 2:1 then 2.1:1. The smooth one swaps."""
import numpy as np

from _lib import SR, stereo, silence, seq


def additive(f0, ratios, dur):
    t = np.arange(int(dur * SR)) / SR
    x = sum(0.88 ** i * np.sin(2 * np.pi * f0 * r * t + np.pi * i * i / len(ratios)) for i, r in enumerate(ratios))
    n = int(0.05 * SR)
    env = np.ones_like(t)
    env[:n] = np.linspace(0, 1, n)
    env[-n:] = np.linspace(1, 0, n)
    return x * env


def dyad(f0, r, spec, dur=2.8):
    return stereo(0.05 * (additive(f0, spec, dur) + additive(f0 * r, spec, dur)))


def render():
    harm = [k for k in range(1, 9)]
    st = [k ** np.log2(2.1) for k in range(1, 9)]
    return seq([dyad(220, 2.0, harm), dyad(220, 2.1, harm), silence(0.6),
                dyad(220, 2.0, st), dyad(220, 2.1, st)], gap=0.45)
