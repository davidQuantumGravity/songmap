"""Effect kernels with feedback."""
from __future__ import annotations

import numpy as np
from numba import njit

from .core import SR, n_samples


@njit(cache=True)
def _pingpong(x, d, fb, damp):
    # First echo on the left after d samples, then alternating right/left, each
    # repeat scaled by fb and darkened by a one-pole low-pass in the loop.
    n = x.shape[0]
    L = np.zeros(n)
    R = np.zeros(n)
    lpl = 0.0
    lpr = 0.0
    for i in range(d, n):
        lpr += damp * (R[i - d] - lpr)
        lpl += damp * (L[i - d] - lpl)
        L[i] = x[i - d] + fb * lpr
        R[i] = fb * lpl
    return L, R


def pingpong_delay(x: np.ndarray, seconds: float, feedback: float = 0.35,
                   damp_hz: float = 4500.0, sr: int = SR) -> np.ndarray:
    """Stereo ping-pong delay, wet signal only. Input mono or stereo; output (n, 2)."""
    m = x.mean(1) if x.ndim == 2 else x
    damp = 1.0 - np.exp(-2.0 * np.pi * damp_hz / sr)
    L, R = _pingpong(np.ascontiguousarray(m, float), n_samples(seconds, sr), float(feedback), float(damp))
    return np.stack([L, R], 1)
