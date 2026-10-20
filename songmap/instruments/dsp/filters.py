"""Filters (numba SVF with per-sample cutoff, RBJ EQ) and non-linearities."""
from __future__ import annotations

import numpy as np
from numba import njit
from scipy.signal import lfilter

from .core import SR


@njit(cache=True)
def _svf(x, fc, q, mode, sr):
    # Cytomic / Simper trapezoidal state-variable filter; fc may change per sample.
    n = x.shape[0]
    y = np.empty(n)
    ic1 = 0.0
    ic2 = 0.0
    k = 1.0 / q
    for i in range(n):
        f = fc[i]
        if f > 0.49 * sr:
            f = 0.49 * sr
        if f < 5.0:
            f = 5.0
        g = np.tan(np.pi * f / sr)
        a1 = 1.0 / (1.0 + g * (g + k))
        a2 = g * a1
        a3 = g * a2
        v3 = x[i] - ic2
        v1 = a1 * ic1 + a2 * v3
        v2 = ic2 + a2 * ic1 + a3 * v3
        ic1 = 2.0 * v1 - ic1
        ic2 = 2.0 * v2 - ic2
        if mode == 0:
            y[i] = v2                    # low-pass
        elif mode == 1:
            y[i] = k * v1                # band-pass, unity peak
        else:
            y[i] = x[i] - k * v1 - v2    # high-pass
    return y


_SVF_MODES = {"lp": 0, "bp": 1, "hp": 2}


def svf(x: np.ndarray, cutoff, q: float = 0.707, mode: str = "lp", sr: int = SR) -> np.ndarray:
    """Resonant 12 dB/oct filter with per-sample cutoff (for filter envelopes/LFOs).

    q = 0.707 is flat (Butterworth); q > 5 rings audibly. Stereo input is handled per channel.
    """
    if x.ndim == 2:
        return np.stack([svf(x[:, c], cutoff, q, mode, sr) for c in range(2)], 1)
    fc = np.ascontiguousarray(np.broadcast_to(np.asarray(cutoff, float), x.shape))
    return _svf(np.ascontiguousarray(x, float), fc, float(max(q, 0.05)), _SVF_MODES[mode], float(sr))


def onepole_lp(x: np.ndarray, fc: float, sr: int = SR) -> np.ndarray:
    a = np.exp(-2.0 * np.pi * fc / sr)
    return lfilter([1.0 - a], [1.0, -a], x, axis=0)


def _rbj(kind: str, f0: float, gain_db: float, q: float, sr: int):
    A = 10 ** (gain_db / 40.0)
    w = 2 * np.pi * f0 / sr
    cw, sw = np.cos(w), np.sin(w)
    al = sw / (2 * q)
    if kind == "peak":
        b = [1 + al * A, -2 * cw, 1 - al * A]
        a = [1 + al / A, -2 * cw, 1 - al / A]
    elif kind == "lowshelf":
        s = 2 * np.sqrt(A) * al
        b = [A * ((A + 1) - (A - 1) * cw + s), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - s)]
        a = [(A + 1) + (A - 1) * cw + s, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - s]
    elif kind == "highshelf":
        s = 2 * np.sqrt(A) * al
        b = [A * ((A + 1) + (A - 1) * cw + s), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - s)]
        a = [(A + 1) - (A - 1) * cw + s, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - s]
    else:
        raise ValueError(kind)
    return np.array(b) / a[0], np.array(a) / a[0]


def eq(x: np.ndarray, kind: str, f0: float, gain_db: float, q: float = 0.707, sr: int = SR) -> np.ndarray:
    """RBJ cookbook EQ band: kind in {'peak', 'lowshelf', 'highshelf'}."""
    b, a = _rbj(kind, f0, gain_db, q, sr)
    return lfilter(b, a, x, axis=0)


def drive(x: np.ndarray, amount: float) -> np.ndarray:
    """tanh saturation with unity gain for small signals at any amount >= 1."""
    amount = max(amount, 1e-3)
    return np.tanh(x * amount) / amount if amount <= 1.0 else np.tanh(x * amount) / np.tanh(amount)


def fold(x: np.ndarray, amount: float) -> np.ndarray:
    """Sine wavefolder (west-coast style)."""
    return np.sin(x * amount * np.pi / 2.0)
