"""Stable versus drifting: the beats of an exact golden seventh survive only if the pitches hold still.

Cg7 in exact close voicing on 110 Hz (1 : 2/phi : 4/phi^2 : 8/phi^3), eight harmonics each, 10 s:
  1. stable: every partial an exact sine at a fixed frequency (the clean instruments)
  2. drifting: each voice wanders slowly (a few cents, different for each voice) and carries a
     5 Hz vibrato of +/-10 cents, as many 'analog' and 'chorus' patches do: the 6.13-12.26 Hz beat
     pattern smears into a generic shimmer
"""
import numpy as np
from _lib import SR, PHI, seq, silence

SHAPE = [1, 2 / PHI, 4 / PHI ** 2, 8 / PHI ** 3]
DUR = 10.0


def voice(f, drift, seed):
    n = int(DUR * SR)
    t = np.arange(n) / SR
    cents = np.zeros(n)
    if drift:
        rng = np.random.default_rng(seed)
        ph = rng.uniform(0, 2 * np.pi, 3)
        cents = (3.0 * np.sin(2 * np.pi * 0.11 * t + ph[0]) + 2.0 * np.sin(2 * np.pi * 0.37 * t + ph[1])
                 + 10.0 * np.sin(2 * np.pi * 5.0 * t + ph[2]))
    inst = f * 2 ** (cents / 1200)
    phase = 2 * np.pi * np.cumsum(inst) / SR
    x = sum(k ** -1.2 * np.sin(k * phase + np.pi * k * k / 8) for k in range(1, 9))
    m = int(0.8 * SR)
    w = 0.5 - 0.5 * np.cos(np.pi * np.arange(m) / m)
    x[:m] *= w
    x[-m:] *= w[::-1]
    return x


def chord(drift):
    x = sum(voice(110 * r, drift, i) for i, r in enumerate(SHAPE)) * 0.12
    return np.stack([x, x], 1)


def render():
    return seq([chord(False), silence(1.0), chord(True)])
