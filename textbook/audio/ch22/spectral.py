"""ch22: a spectral chord. Harmonics 1-16 of E1 (41.20 Hz) enter one at a time from the bottom as pure sines and are
held; then the same chord with every partial rounded to the nearest 12-ET pitch; then rounded to the nearest
quarter-tone (24-ET). Exact frequencies: f_k = k * 41.2034 Hz."""
import numpy as np
from _lib import sine, silence, seq, at, freq, midi

F0 = freq(28)          # E1 = 41.2034 Hz
N = 16


def amp(k):
    return 0.22 / k ** 0.5


def chord_of(freqs, dur):
    return at([(0.0, sine(f, dur, amp(k + 1), fade=0.25)) for k, f in enumerate(freqs)])


def render():
    exact = [F0 * k for k in range(1, N + 1)]
    build = at([(0.5 * i, sine(f, 10.0 - 0.5 * i, amp(i + 1), fade=0.25)) for i, f in enumerate(exact)])
    et12 = [freq(round(midi(f))) for f in exact]
    et24 = [freq(round(midi(f) * 2) / 2) for f in exact]
    return seq([build, silence(0.8), chord_of(exact, 4.0), silence(0.6), chord_of(et12, 4.0),
                silence(0.6), chord_of(et24, 4.0)])
