"""Envelopes."""
from __future__ import annotations

import numpy as np

from .core import SR, n_samples, t60_env


def _seg(n: int, start: float, end: float, curve: float) -> np.ndarray:
    """Curved segment. curve > 0: fast start, slow finish (analog RC shape)."""
    if n <= 0:
        return np.zeros(0)
    x = np.arange(n) / n
    k = x if abs(curve) < 1e-6 else (1.0 - np.exp(-curve * x)) / (1.0 - np.exp(-curve))
    return start + (end - start) * k


def adsr(n: int, a=0.005, d=0.1, s=0.7, r=0.2, gate: float | None = None,
         curve: float = 4.0, sr: int = SR) -> np.ndarray:
    """Analog-style ADSR of total length n samples.

    gate: seconds until key-up (release starts). Default: n minus the release time.
    If the gate closes during attack/decay, release starts from the current level.
    """
    rn = n_samples(r, sr)
    gate_n = n - rn if gate is None else n_samples(gate, sr)
    gate_n = int(np.clip(gate_n, 0, n))
    env = np.full(n, float(s))
    an, dn = n_samples(a, sr), n_samples(d, sr)
    att = _seg(an, 0.0, 1.0, 2.0)
    k = min(an, gate_n)
    env[:k] = att[:k]
    i = k
    if i < gate_n:
        dec = _seg(dn, 1.0, s, curve)
        k = min(dn, gate_n - i)
        env[i:i + k] = dec[:k]
    level = env[gate_n - 1] if gate_n > 0 else 0.0
    tail = n - gate_n
    rel = _seg(rn, level, 0.0, curve)
    k = min(tail, rn)
    env[gate_n:gate_n + k] = rel[:k]
    env[gate_n + k:] = 0.0
    return env


def ad(n: int, a=0.001, decay=0.3, sr: int = SR) -> np.ndarray:
    """Percussive attack + t60 decay."""
    env = t60_env(n, decay, sr)
    an = min(n_samples(a, sr), n)
    env[:an] *= np.linspace(0.0, 1.0, an)
    return env
