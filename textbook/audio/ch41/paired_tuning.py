"""Beating on purpose: two struck-bar tones in unison, then tuned a few hertz apart.

An illustration of the paired-tuning idea of Balinese gamelan (instruments made in pairs, one tuned
slightly above the other, so that their sum shimmers). This is a synthetic tone, not a recording,
and the 6 Hz offset is an illustrative choice, not a measured gamelan tuning.
The tone has the partial ratios of an ideal free-free bar (1, 2.756, 5.404), each decaying.
  1. two identical tones at 400 Hz, struck four times
  2. one at 397 Hz and one at 403 Hz (6 Hz apart), struck four times: the sum beats 6 times a second
"""
import numpy as np
from _lib import SR, seq, silence

BAR = [(1.0, 1.0, 2.2), (2.756, 0.35, 0.9), (5.404, 0.15, 0.45)]   # (ratio, amp, t60 seconds)


def bar(f, dur=2.4):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for r, a, t60 in BAR:
        x += a * np.exp(-6.9078 * t / t60) * np.sin(2 * np.pi * f * r * t)
    x *= 1 - np.exp(-t / 0.002)
    return x


def strikes(f1, f2):
    hits = [bar(f1) + bar(f2) for _ in range(4)]
    x = np.concatenate(hits)
    return np.stack([x, x], 1) * 0.3


def render():
    return seq([strikes(400.0, 400.0), silence(1.0), strikes(397.0, 403.0)])
