"""Struck sounds with different partial ratios, each with fundamental 262 Hz and a decay:
1. harmonic (1, 2, 3, 4, 5, 6: a string-like tone);
2. an ideal free bar, as in a xylophone or glockenspiel bar before tuning (1, 2.756, 5.404, 8.933);
3. an ideal circular membrane, as in a drum head (1, 1.593, 2.136, 2.295, 2.653, 2.917);
4. an idealized church bell (hum 0.5, prime 1, minor-third "tierce" 1.2, quint 1.5, nominal 2).
"""
import numpy as np
from _lib import SR, seq, silence, stereo

F0 = 262.0


def struck(ratios, amps, dur=2.6, t60=2.2):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k, (r, a) in enumerate(zip(ratios, amps)):
        decay = t60 / (1 + 0.35 * k)                       # higher partials die away faster
        x += a * np.sin(2 * np.pi * F0 * r * t + 0.7 * k) * np.exp(-6.9078 * t / decay)
    att = int(0.003 * SR)
    x[:att] *= np.linspace(0, 1, att)
    x[-int(0.05 * SR):] *= np.linspace(1, 0, int(0.05 * SR))
    return stereo(0.25 * x / sum(amps))


def render():
    harmonic = struck([1, 2, 3, 4, 5, 6], [1, 0.5, 0.33, 0.25, 0.2, 0.17])
    bar = struck([1, 2.7565, 5.4039, 8.9330], [1, 0.5, 0.3, 0.2])
    membrane = struck([1, 1.5933, 2.1355, 2.2954, 2.6531, 2.9173], [1, 0.7, 0.55, 0.45, 0.4, 0.35], t60=1.2)
    bell = struck([0.5, 1, 1.2, 1.5, 2], [0.6, 0.8, 0.7, 0.4, 1.0], t60=3.0)
    return seq([harmonic, silence(0.3), bar, silence(0.3), membrane, silence(0.3), bell])
