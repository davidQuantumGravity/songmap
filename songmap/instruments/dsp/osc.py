"""Band-limited oscillators (PolyBLEP) and noise sources."""
from __future__ import annotations

import numpy as np

from .core import SR, pan_mono


def phase(freq, n: int, phase0: float = 0.0, sr: int = SR):
    """Phase in [0, 1) and per-sample increment for a scalar or per-sample freq."""
    inc = np.broadcast_to(np.asarray(freq, float) / sr, (n,)).astype(float)
    ph = (phase0 + np.cumsum(inc) - inc) % 1.0
    return ph, inc


def _blep(t: np.ndarray, dt: np.ndarray) -> np.ndarray:
    """PolyBLEP residual (2-sample polynomial band-limited step)."""
    out = np.zeros_like(t)
    m = t < dt
    x = t[m] / dt[m]
    out[m] = x + x - x * x - 1.0
    m = t > 1.0 - dt
    x = (t[m] - 1.0) / dt[m]
    out[m] = x * x + x + x + 1.0
    return out


def saw(freq, n: int, phase0: float = 0.0, sr: int = SR) -> np.ndarray:
    """Band-limited sawtooth (PolyBLEP). Replaces synth_v0's aliasing `saw`."""
    ph, dt = phase(freq, n, phase0, sr)
    return 2.0 * ph - 1.0 - _blep(ph, dt)


def square(freq, n: int, pw=0.5, phase0: float = 0.0, sr: int = SR) -> np.ndarray:
    """Band-limited pulse wave; pw may be an array (PWM)."""
    ph, dt = phase(freq, n, phase0, sr)
    pw = np.broadcast_to(np.asarray(pw, float), (n,))
    y = np.where(ph < pw, 1.0, -1.0)
    y = y + _blep(ph, dt) - _blep((ph - pw) % 1.0, dt)
    return y


def sine(freq, n: int, phase0: float = 0.0, sr: int = SR) -> np.ndarray:
    ph, _ = phase(freq, n, phase0, sr)
    return np.sin(2.0 * np.pi * ph)


def triangle(freq, n: int, phase0: float = 0.0, sr: int = SR) -> np.ndarray:
    """Naive triangle; its harmonics fall at 12 dB/oct so aliasing is negligible."""
    ph, _ = phase(freq, n, phase0, sr)
    return 2.0 * np.abs(2.0 * ph - 1.0) - 1.0


def supersaw(freq, n: int, voices: int = 7, detune_cents: float = 18.0,
             rng: np.random.Generator | None = None, width: float = 0.8,
             sr: int = SR) -> np.ndarray:
    """Unison saws spread across the stereo field. Returns (n, 2)."""
    rng = rng or np.random.default_rng()
    out = np.zeros((n, 2))
    offs = np.linspace(-1.0, 1.0, voices) if voices > 1 else np.zeros(1)
    for k, o in enumerate(offs):
        f = np.asarray(freq, float) * 2.0 ** (o * detune_cents / 1200.0)
        out += pan_mono(saw(f, n, rng.random(), sr), o * width)
    return out / np.sqrt(voices)


def white(n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.standard_normal(n)


def pink(n: int, rng: np.random.Generator) -> np.ndarray:
    """1/f noise by spectral shaping; unit RMS."""
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.arange(spec.size)
    f[0] = 1
    y = np.fft.irfft(spec / np.sqrt(f), n)
    return y / (np.std(y) + 1e-12)
