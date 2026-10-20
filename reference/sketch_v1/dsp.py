"""DSP building blocks for SongMap instruments (reference sketch, v1).

Conventions
- Mono float64 arrays at SR unless a function says otherwise. Stereo is shape (n, 2).
- Frequencies in Hz, times in seconds, gains linear unless the name ends in _db.
- Anything that needs a per-sample loop (time-varying filters, feedback delays,
  physical models) is a numba kernel prefixed with `_`, wrapped by a friendly function.

This file is meant to be lifted into `songmap/instruments/dsp.py` in Phase 1.
"""
from __future__ import annotations

import numpy as np
from numba import njit
from scipy.signal import lfilter

SR = 48000  # video audio is 48 kHz; keep the engine at the delivery rate


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
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


# ----------------------------------------------------------------------------
# oscillators (band-limited)
# ----------------------------------------------------------------------------
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


# ----------------------------------------------------------------------------
# noise
# ----------------------------------------------------------------------------
def white(n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.standard_normal(n)


def pink(n: int, rng: np.random.Generator) -> np.ndarray:
    """1/f noise by spectral shaping; unit RMS."""
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.arange(spec.size)
    f[0] = 1
    y = np.fft.irfft(spec / np.sqrt(f), n)
    return y / (np.std(y) + 1e-12)


# ----------------------------------------------------------------------------
# envelopes
# ----------------------------------------------------------------------------
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


# ----------------------------------------------------------------------------
# filters
# ----------------------------------------------------------------------------
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


# ----------------------------------------------------------------------------
# non-linearities
# ----------------------------------------------------------------------------
def drive(x: np.ndarray, amount: float) -> np.ndarray:
    """tanh saturation with unity gain for small signals at any amount >= 1."""
    amount = max(amount, 1e-3)
    return np.tanh(x * amount) / amount if amount <= 1.0 else np.tanh(x * amount) / np.tanh(amount)


def fold(x: np.ndarray, amount: float) -> np.ndarray:
    """Sine wavefolder (west-coast style)."""
    return np.sin(x * amount * np.pi / 2.0)


# ----------------------------------------------------------------------------
# physical models
# ----------------------------------------------------------------------------
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


# ----------------------------------------------------------------------------
# effects with feedback
# ----------------------------------------------------------------------------
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
