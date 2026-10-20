"""Physical models: Karplus-Strong strings and modal banks."""
from __future__ import annotations

import numpy as np
from numba import njit

from .core import SR, t_axis


@njit(cache=True)
def _ks(exc, n, period, loss, s):
    # Karplus-Strong string with fractional delay. Loop filter s*y[n] + (1-s)*y[n-1]
    # adds (1-s) samples of delay, which we subtract so the pitch stays exact.
    y = np.zeros(n)
    D = period - (1.0 - s)
    N = int(D)
    frac = D - N
    m = exc.shape[0]
    for i in range(n):
        v = exc[i] if i < m else 0.0
        j = i - N
        a0 = y[j] if j >= 0 else 0.0
        a1 = y[j - 1] if j - 1 >= 0 else 0.0
        a2 = y[j - 2] if j - 2 >= 0 else 0.0
        d0 = (1.0 - frac) * a0 + frac * a1
        d1 = (1.0 - frac) * a1 + frac * a2
        y[i] = v + loss * (s * d0 + (1.0 - s) * d1)
    return y


def ks_string(freq: float, n: int, exc: np.ndarray, t60: float = 3.0,
              brightness: float = 0.7, sr: int = SR) -> np.ndarray:
    """Plucked string. brightness in (0.5, 1]: 0.5 = classic dull KS, 1 = no loop damping."""
    period = sr / freq
    loss = 10 ** (-3.0 * period / (t60 * sr))
    return _ks(np.ascontiguousarray(exc, float), n, float(period), float(loss),
               float(np.clip(brightness, 0.5, 1.0)))


def modal(freqs, amps, t60s, n: int, phases=None, sr: int = SR) -> np.ndarray:
    """Bank of exponentially decaying sinusoids (modal synthesis).

    Use for mallets, bells, piano partials, drum shells, plates.
    """
    t = t_axis(n, sr)
    out = np.zeros(n)
    phases = np.zeros(len(freqs)) if phases is None else phases
    for f, a, t60, ph in zip(freqs, amps, t60s, phases):
        if f <= 0 or f >= 0.45 * sr or a == 0:
            continue
        out += a * np.sin(2 * np.pi * f * t + ph) * np.exp(-6.907755 * t / t60)
    return out
