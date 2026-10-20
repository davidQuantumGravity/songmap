"""Mixing, mastering, loudness and QA (reference sketch, v1).

- Bus: sums placed notes into a stereo buffer, with gain, pan and sends.
- reverb_ir(): stereo, frequency-dependent decay, early reflections (much better than
  synth_v0's single mono noise tail).
- compressor(), sidechain_env(), limiter(): numba kernels.
- lufs() / true_peak(): ITU-R BS.1770-4 integrated loudness (gated) at 48 kHz.
- qa(): the numbers an LLM reads instead of listening.
"""
from __future__ import annotations

import numpy as np
from numba import njit
from scipy.ndimage import minimum_filter1d, uniform_filter1d
from scipy.signal import fftconvolve, lfilter, resample_poly

from dsp import SR, as_stereo, eq, n_samples, pan_mono, svf, t_axis


# ----------------------------------------------------------------------------
# buses
# ----------------------------------------------------------------------------
class Bus:
    def __init__(self, seconds: float, name: str = "bus"):
        self.name = name
        self.x = np.zeros((n_samples(seconds), 2))

    def add(self, t: float, sig: np.ndarray, gain: float = 1.0, pan: float = 0.0):
        i = int(round(t * SR))
        if i >= len(self.x):
            return
        s = pan_mono(sig, pan) if sig.ndim == 1 else sig * np.array([1 - max(pan, 0), 1 + min(pan, 0)])
        s = s[: len(self.x) - i] * gain
        self.x[i:i + len(s)] += s


# ----------------------------------------------------------------------------
# reverb
# ----------------------------------------------------------------------------
def reverb_ir(seconds: float = 2.2, predelay: float = 0.015, damping: float = 0.5,
              early: int = 10, width: float = 1.0, seed: int = 1) -> np.ndarray:
    """Synthetic stereo room/hall impulse response.

    damping: how much faster highs die than lows (0 = flat, 1 = very dark tail).
    """
    rng = np.random.default_rng(seed)
    n = n_samples(seconds * 1.2)
    t = t_axis(n)
    ir = np.zeros((n, 2))
    for c in range(2):
        nz = rng.standard_normal(n)
        lo = svf(nz, 500, 0.7, "lp") * np.exp(-6.9 * t / (seconds * 1.15))
        mid = svf(nz, 2000, 0.6, "bp") * np.exp(-6.9 * t / seconds)
        hi = svf(nz, 5000, 0.7, "hp") * np.exp(-6.9 * t / (seconds * (1 - 0.7 * damping)))
        ir[:, c] = lo + mid + 0.8 * hi
    ir *= np.clip(t / 0.03, 0, 1)[:, None]                    # diffuse tail builds up
    for k in range(early):                                     # discrete early reflections
        i = n_samples(rng.uniform(0.004, 0.045))
        ir[i] += rng.uniform(0.3, 0.8) * np.array([rng.uniform(0.4, 1), rng.uniform(0.4, 1)]) * 6
    mid_, side = ir.mean(1), (ir[:, 0] - ir[:, 1]) / 2
    ir = np.stack([mid_ + width * side, mid_ - width * side], 1)
    ir = np.concatenate([np.zeros((n_samples(predelay), 2)), ir])
    return ir / np.sqrt(np.sum(ir ** 2) / 2)


def convolve(x: np.ndarray, ir: np.ndarray) -> np.ndarray:
    x = as_stereo(x)
    return np.stack([fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1)


# ----------------------------------------------------------------------------
# dynamics processors
# ----------------------------------------------------------------------------
def sidechain_env(times: list[float], n: int, depth: float = 0.6, release: float = 0.18,
                  attack: float = 0.004) -> np.ndarray:
    """Gain curve that ducks at each trigger time (kick -> bass/pads pumping)."""
    g = np.ones(n)
    r = n_samples(release * 2)
    shape = 1 - depth * np.exp(-t_axis(r) / (release / 3))
    a = n_samples(attack)
    shape[:a] = np.linspace(1, shape[a], a)
    for tt in times:
        i = int(tt * SR)
        if i < n:
            k = min(r, n - i)
            g[i:i + k] = np.minimum(g[i:i + k], shape[:k])
    return g


@njit(cache=True)
def _comp_gain(lvl_db, thr, ratio, knee, att, rel):
    n = lvl_db.shape[0]
    g = np.zeros(n)
    env = 0.0
    for i in range(n):
        over = lvl_db[i] - thr
        if over <= -knee / 2:
            red = 0.0
        elif over >= knee / 2:
            red = over * (1 - 1 / ratio)
        else:
            red = (1 - 1 / ratio) * (over + knee / 2) ** 2 / (2 * knee)
        c = att if red > env else rel
        env = c * env + (1 - c) * red
        g[i] = -env
    return g


def compressor(x: np.ndarray, threshold_db=-18.0, ratio=3.0, attack=0.01, release=0.15,
               knee_db=6.0, makeup_db=0.0, key: np.ndarray | None = None) -> np.ndarray:
    """Feed-forward RMS-ish compressor (stereo-linked). `key` = external sidechain."""
    det = as_stereo(x if key is None else key)
    lvl = 10 * np.log10(uniform_filter1d(np.max(det ** 2, 1), n_samples(0.005)) + 1e-12)
    ca, cr = np.exp(-1 / (attack * SR)), np.exp(-1 / (release * SR))
    g = _comp_gain(lvl, threshold_db, ratio, max(knee_db, 1e-3), ca, cr) + makeup_db
    return as_stereo(x) * (10 ** (g / 20))[:, None]


@njit(cache=True)
def _release(g, coef):
    out = np.empty_like(g)
    cur = 1.0
    for i in range(g.shape[0]):
        cur = g[i] if g[i] < cur else cur + (g[i] - cur) * coef
        out[i] = cur
    return out


def limiter(x: np.ndarray, ceiling_db: float = -1.0, lookahead: float = 0.005,
            release: float = 0.08) -> np.ndarray:
    """Look-ahead brickwall limiter (sample peak; leave ~0.3 dB for true-peak overs)."""
    x = as_stereo(x)
    ceil = 10 ** (ceiling_db / 20)
    need = np.minimum(1.0, ceil / (np.max(np.abs(x), 1) + 1e-12))
    la = max(1, n_samples(lookahead))
    fwd = minimum_filter1d(need, la, origin=-(la // 2))      # min over [i, i+la)
    smooth = uniform_filter1d(fwd, la, origin=(la - 1) // 2)   # avg over (i-la, i]: never above need
    g = _release(np.minimum(smooth, fwd), 1 - np.exp(-1 / (release * SR)))
    return x * g[:, None]


# ----------------------------------------------------------------------------
# loudness (BS.1770-4)
# ----------------------------------------------------------------------------
_K1 = ([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585])
_K2 = ([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621])


def k_weight(x: np.ndarray) -> np.ndarray:
    assert SR == 48000, "K-weighting constants are for 48 kHz"
    return lfilter(*_K2, lfilter(*_K1, as_stereo(x), axis=0), axis=0)


def lufs(x: np.ndarray) -> float:
    """Integrated loudness, gated (absolute -70 LUFS, relative -10 LU)."""
    y = k_weight(x)
    blk, hop = n_samples(0.4), n_samples(0.1)
    if len(y) < blk:
        return -70.0
    ms = np.array([np.mean(y[i:i + blk] ** 2, 0).sum() for i in range(0, len(y) - blk + 1, hop)])
    l = -0.691 + 10 * np.log10(ms + 1e-15)
    ms = ms[l > -70]
    if not len(ms):
        return -70.0
    rel = -0.691 + 10 * np.log10(ms.mean()) - 10
    ms = ms[(-0.691 + 10 * np.log10(ms)) > rel]
    return float(-0.691 + 10 * np.log10(ms.mean()))


def true_peak_db(x: np.ndarray) -> float:
    up = resample_poly(as_stereo(x), 4, 1, axis=0)
    return float(20 * np.log10(np.max(np.abs(up)) + 1e-12))


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


# ----------------------------------------------------------------------------
# QA
# ----------------------------------------------------------------------------
def band_balance(x: np.ndarray) -> dict:
    m = as_stereo(x).mean(1)
    spec = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
    f = np.fft.rfftfreq(len(m), 1 / SR)
    tot = spec.sum() + 1e-12
    return {"low": float(spec[f < 250].sum() / tot), "mid": float(spec[(f >= 250) & (f < 4000)].sum() / tot),
            "high": float(spec[f >= 4000].sum() / tot)}


def qa(x: np.ndarray, sections: list[tuple[str, float, float]] = ()) -> dict:
    x = as_stereo(x)
    rep = {"lufs": round(lufs(x), 2), "true_peak_db": round(true_peak_db(x), 2),
           "clipped_samples": int(np.sum(np.abs(x) >= 0.999)),
           "seconds": round(len(x) / SR, 3), "sections": []}
    for name, t0, t1 in sections:
        seg = x[int(t0 * SR):int(t1 * SR)]
        rms = float(10 * np.log10(np.mean(k_weight(seg) ** 2) * 2 + 1e-12) - 0.691) if len(seg) else -99
        rep["sections"].append({"name": name, "start": t0, "loudness": round(rms, 1),
                                **{k: round(v, 3) for k, v in band_balance(seg).items()},
                                "silent": rms < -50})
    return rep
