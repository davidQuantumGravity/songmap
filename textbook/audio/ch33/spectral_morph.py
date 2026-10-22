"""ch33: the timbre continuum between the two worlds. An exact golden triad on C4
(1 : 2/phi : 4/phi^2) on an additive tone whose 8 partial ratios glide from harmonic (1..8)
to golden (1, phi, 2, phi^2, 2phi, 4, phi^3, 2phi^2) and stay there; then a just C major
triad (4:5:6) through the same glide. The golden chord smooths out; the major triad roughens."""
import numpy as np
from _lib import PHI, SR, seq, silence

HARM = np.arange(1, 9, dtype=float)
GOLD = np.array(sorted({2 ** m * PHI ** n for m in range(6) for n in range(6)})[:8])


def morph_chord(freqs, hold0=2.0, glide=8.0, hold1=3.0, amp=0.18):
    dur = hold0 + glide + hold1
    n = int(dur * SR)
    t = np.arange(n) / SR
    a = np.clip((t - hold0) / glide, 0.0, 1.0)
    a = 0.5 - 0.5 * np.cos(np.pi * a)                      # smooth glide
    out = np.zeros(n)
    for f0 in freqs:
        for k in range(8):
            r = (1 - a) * HARM[k] + a * GOLD[k]
            ph = 2 * np.pi * np.cumsum(f0 * r) / SR + np.pi * (k + 1) ** 2 / 8
            out += amp * (k + 1) ** -1.2 * np.sin(ph)
    f = int(0.05 * SR)
    env = np.ones(n)
    env[:f] = np.linspace(0, 1, f)
    env[-int(0.6 * SR):] = np.linspace(1, 0, int(0.6 * SR))
    x = out * env
    return np.stack([x, x], 1)


def render():
    c4 = 261.63
    golden = [c4, c4 * 2 / PHI, c4 * 4 / PHI ** 2]
    major = [c4, c4 * 5 / 4, c4 * 3 / 2]
    return seq([morph_chord(golden), silence(1.0), morph_chord(major)])
