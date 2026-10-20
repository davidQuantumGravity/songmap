"""Mix effects: reverb IR + convolution, compressor, sidechain envelope, limiter."""
from __future__ import annotations

import numpy as np
from numba import njit
from scipy.ndimage import minimum_filter1d, uniform_filter1d
from scipy.signal import fftconvolve

from ..instruments.dsp import SR, as_stereo, n_samples, svf, t_axis


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
