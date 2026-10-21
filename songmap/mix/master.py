"""Mastering chains: `master()` (glue, loudness target, limiter) and `master_legacy()` (synth_v0's)."""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfilt

from ..export.qa import lufs, true_peak_db
from ..instruments.dsp import SR, as_stereo, eq
from .fx import compressor, limiter


def master_legacy(mix: np.ndarray, fade: float = 2.5) -> np.ndarray:
    """synth_v0's master, kept for the port check (`master: legacy`): 28 Hz high-pass, peak
    normalize, tanh saturation, 2.5 s fade-out, x0.89 (about -1 dBFS peak)."""
    y = sosfilt(butter(2, 28, "high", fs=SR, output="sos"), as_stereo(mix), axis=0)
    y = y / (np.max(np.abs(y)) + 1e-9)
    y = np.tanh(y * 1.6) / np.tanh(1.6)
    fo = min(int(fade * SR), len(y))
    y[len(y) - fo:] *= np.linspace(1, 0, fo)[:, None]
    return y * 0.89


def master_clean(mix: np.ndarray, ceiling_db: float = -1.0) -> np.ndarray:
    """`master: clean`: peak-normalize only. No EQ, compression, limiting or saturation, so the
    instruments' exact partials and the tuning's beats reach the listener unaltered."""
    y = as_stereo(mix)
    return y / (np.max(np.abs(y)) + 1e-12) * 10 ** (ceiling_db / 20)


def master(mix: np.ndarray, target_lufs: float = -14.0, ceiling_db: float = -1.0,
           glue: bool = True) -> np.ndarray:
    """High-pass, gentle glue compression, tilt EQ, loudness normalize, limit."""
    y = eq(as_stereo(mix), "lowshelf", 30, -12, 0.7)          # clear sub rumble
    if glue:
        y = compressor(y, threshold_db=-20, ratio=2.0, attack=0.03, release=0.2, knee_db=8)
    for _ in range(3):                                         # converge: limiting lowers loudness
        y = y * 10 ** ((target_lufs - lufs(y)) / 20)
        y = limiter(y, ceiling_db - 0.5)
        if abs(lufs(y) - target_lufs) < 0.3:
            break
    tp = true_peak_db(y)                 # sample-peak limiter lets inter-sample overs through;
    if tp > ceiling_db:                  # trim them (Phase 4: oversampled true-peak limiter)
        y = y * 10 ** ((ceiling_db - tp) / 20)
    return y
