"""Additive synthesis, one partial at a time, on A3 = 220 Hz.

Partials k = 1, 2, ..., 8 at frequencies 220k Hz and amplitudes 1/k enter one by one, 1.2 s apart
(the tone grows from a pure sine toward a sawtooth-like buzz). Then the same eight partials with
amplitudes 1/k^2 (a softer, rounder colour) for 4 s. Every partial is an exact sine with a fixed phase.
"""
import numpy as np
from _lib import SR, seq, silence

F0 = 220.0


def tone(amps, starts, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k, (a, t0) in enumerate(zip(amps, starts), start=1):
        ph = np.pi * k * k / len(amps)                               # Schroeder phase
        on = np.clip((t - t0) / 0.15, 0, 1)
        x += a * (0.5 - 0.5 * np.cos(np.pi * on)) * np.sin(2 * np.pi * F0 * k * t + ph)
    k = int(0.3 * SR)
    x[-k:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(k) / k)
    return np.stack([x, x], 1) * 0.25


def render():
    build = tone([1 / k for k in range(1, 9)], [1.2 * (k - 1) for k in range(1, 9)], 11.0)
    soft = tone([1 / k ** 2 for k in range(1, 9)], [0.0] * 8, 4.0)
    return seq([build, silence(0.8), soft])
