"""Polyrhythms on the Fibonacci ratios 3:2, 5:3, 8:5, then the golden ratio itself.

A low pulse ticks 1.6 times a second throughout. A high pulse ticks r times as fast, with
r = 3/2, 5/3, 8/5 and then phi = 1.618... (7.5 s each). For r = p/q the two pulses coincide every
q low ticks, so the pattern repeats; the repeats get longer as p/q approaches phi. With r = phi the
two pulses never coincide again after the first beat: the rhythm is quasi-periodic.
Every section starts with both pulses together.
"""
import numpy as np
from _lib import SR, PHI, silence, seq

BASE = 1.6          # low pulses per second
SECTION = 7.5


def blip(f, dur=0.09, amp=0.35):
    n = int(dur * SR)
    t = np.arange(n) / SR
    env = np.exp(-t / 0.025) * (1 - np.exp(-t / 0.002))
    return amp * env * np.sin(2 * np.pi * f * t)


def section(r):
    n = int(SECTION * SR)
    x = np.zeros(n)
    lo, hi = blip(220.0), blip(1320.0, amp=0.25)
    for rate, b in ((BASE, lo), (BASE * r, hi)):
        k = 0
        while True:
            i = int(round(k / rate * SR))
            if i + len(b) >= n:
                break
            x[i:i + len(b)] += b
            k += 1
    return np.stack([x, x], 1)


def render():
    return seq([section(r) for r in (3 / 2, 5 / 3, 8 / 5, PHI)], gap=1.0)
