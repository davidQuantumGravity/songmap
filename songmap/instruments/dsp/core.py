"""Shared DSP helpers and the engine sample rate.

Conventions
- Mono float64 arrays at SR unless a function says otherwise. Stereo is shape (n, 2).
- Frequencies in Hz, times in seconds, gains linear unless the name ends in _db.
- Anything that needs a per-sample loop is a numba kernel prefixed with `_`, wrapped by a friendly function.
"""
from __future__ import annotations

import numpy as np


SR = 48000  # video audio is 48 kHz; keep the engine at the delivery rate


def mtof(m):
    """MIDI note (float OK) -> Hz."""
    return 440.0 * 2.0 ** ((np.asarray(m, float) - 69.0) / 12.0)


def n_samples(seconds: float, sr: int = SR) -> int:
    return max(1, int(round(seconds * sr)))


def t_axis(n: int, sr: int = SR) -> np.ndarray:
    return np.arange(n) / sr


def db(x):
    return 20.0 * np.log10(np.maximum(np.abs(x), 1e-12))


def undb(d):
    return 10.0 ** (np.asarray(d, float) / 20.0)


def t60_env(n: int, t60: float, sr: int = SR) -> np.ndarray:
    """Exponential decay reaching -60 dB after t60 seconds."""
    return np.exp(-6.907755 * t_axis(n, sr) / max(t60, 1e-4))


def pan_mono(x: np.ndarray, pan: float) -> np.ndarray:
    """Constant-power pan, pan in [-1, 1]. Returns (n, 2)."""
    a = (pan + 1.0) * np.pi / 4.0
    return np.stack([x * np.cos(a), x * np.sin(a)], 1) * np.sqrt(2.0)


def as_stereo(x: np.ndarray) -> np.ndarray:
    return x if x.ndim == 2 else np.stack([x, x], 1)
