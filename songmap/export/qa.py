"""Loudness (ITU-R BS.1770-4), true peak, band balance and the QA report an LLM reads instead of listening."""
from __future__ import annotations

import numpy as np
from scipy.signal import lfilter, resample_poly

from ..instruments.dsp import SR, as_stereo, n_samples


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
    cs = np.concatenate([[0.0], np.cumsum((y ** 2).sum(1))])      # block power from a running sum
    starts = np.arange(0, len(y) - blk + 1, hop)
    ms = (cs[starts + blk] - cs[starts]) / blk
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
