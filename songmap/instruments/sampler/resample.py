"""Repitching: band-limited windowed-sinc interpolation at any (fractional) ratio.

Float MIDI pitch means ratios are rarely rational with small terms (36edo, `tune` cents), so
this reads the sample at `step` source samples per output sample through a Kaiser-windowed
sinc. Reading faster than 1:1 lowers the cutoff to 1/step, so pitching up does not alias.
"""
from __future__ import annotations

import numpy as np
from numba import njit

ZEROS = 16          # zero crossings each side at full bandwidth
OVERSAMPLE = 512    # kernel table points per zero crossing
ROLLOFF = 0.97      # cutoff as a fraction of the lower Nyquist
BETA = 8.6          # Kaiser window: ~ -90 dB stopband


def _table() -> np.ndarray:
    u = np.arange(ZEROS * OVERSAMPLE + 2) / OVERSAMPLE
    w = np.kaiser(2 * len(u) - 1, BETA)[len(u) - 1:]
    return (np.sinc(u) * w).astype(np.float64)


_KERNEL = _table()


@njit(cache=True)
def _sinc_read(x, start, step, n_out, fc, kernel, zeros, over):
    ch = x.shape[1]
    n_in = x.shape[0]
    out = np.zeros((n_out, ch))
    half = int(np.ceil(zeros / fc))
    for i in range(n_out):
        pos = start + i * step
        n0 = int(np.floor(pos))
        for k in range(n0 - half + 1, n0 + half + 1):
            if k < 0 or k >= n_in:
                continue
            u = abs(pos - k) * fc
            if u >= zeros:
                continue
            f = u * over
            j = int(f)
            a = f - j
            h = fc * (kernel[j] * (1.0 - a) + kernel[j + 1] * a)
            for c in range(ch):
                out[i, c] += h * x[k, c]
    return out


def repitch(x: np.ndarray, ratio: float, n_out: int) -> np.ndarray:
    """Play `x` (n,) or (n, ch) at `ratio` x speed (2.0 = an octave up), for n_out samples.

    Output past the end of the source is silence. `ratio` includes any sample-rate change.
    """
    x2 = x.reshape(len(x), -1).astype(np.float64, copy=False)
    if abs(ratio - 1.0) < 1e-9:
        out = np.zeros((n_out, x2.shape[1]))
        k = min(n_out, len(x2))
        out[:k] = x2[:k]
    else:
        fc = ROLLOFF * min(1.0, 1.0 / ratio)
        out = _sinc_read(x2, 0.0, float(ratio), int(n_out), fc, _KERNEL, ZEROS, OVERSAMPLE)
    return out[:, 0] if x.ndim == 1 else out
