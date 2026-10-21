"""Why the clean tones use raised-cosine envelopes: the same 0.5 s organ-like tone (A4 = 440 Hz, six
harmonics) four times each with
  1. an abrupt gate (the waveform jumps from silence to full level and back): audible clicks
  2. a linear 5 ms ramp: softer clicks
  3. a raised-cosine 30 ms ramp (the shape used by the clean instruments): no click
"""
import numpy as np
from _lib import SR, seq, silence


def note(shape, ramp, dur=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = sum(k ** -1.2 * np.sin(2 * np.pi * 440 * k * t + 0.7 * k) for k in range(1, 7))
    env = np.ones(n)
    m = max(1, int(ramp * SR))
    if shape == "linear":
        w = np.arange(m) / m
    elif shape == "cosine":
        w = 0.5 - 0.5 * np.cos(np.pi * np.arange(m) / m)
    else:
        w = np.ones(m)
    env[:m] = w
    env[-m:] = w[::-1]
    y = 0.2 * x * env
    return np.stack([y, y], 1)


def render():
    out = []
    for shape, ramp in (("abrupt", 0.0), ("linear", 0.005), ("cosine", 0.03)):
        for _ in range(4):
            out += [note(shape, ramp), silence(0.35)]
        out.append(silence(0.8))
    return seq(out)
