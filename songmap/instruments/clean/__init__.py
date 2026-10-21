"""Clean additive instrument: stable, undistorted tones for hearing overtones and tuning.

No vibrato, drift, detune, noise, filter or saturation: every partial is an exact sine at a
fixed frequency with a deterministic (Schroeder) phase, so beats between chord tones come
only from the tuning itself. Envelopes are raised-cosine (click-free, no overshoot).
"""
from __future__ import annotations

import numpy as np

from ..base import A, T, V, Instrument, Param, common_vel, register
from ..dsp import SR, mtof, n_samples, t_axis

PHI = (1 + 5 ** 0.5) / 2


def _spectrum(mode: int, count: int) -> list[float]:
    """Partial frequency ratios: 0 harmonic (1, 2, 3 ...), 1 golden (2^m * phi^n), 2 odd (1, 3, 5 ...)."""
    if mode == 1:
        golden = sorted({2 ** m * PHI ** n for m in range(8) for n in range(8)})
        return golden[:count]
    if mode == 2:
        return [2 * k + 1 for k in range(count)]
    return [k + 1 for k in range(count)]


@register
class Clean(Instrument):
    name, family = "clean", "keys"
    PARAMS = (
        Param("partials", 8, 1, 32, "", "lin", T, "number of partials (1 = pure sine)"),
        Param("rolloff", 1.0, 0, 3, "", "lin", T, "partial k amplitude = k^-rolloff (1 = sawtooth-like, 2 = soft)"),
        Param("even", 1.0, 0, 1, "", "lin", T, "weight of even harmonics (0 = clarinet-like odd only)"),
        Param("spectrum", 0, 0, 2, "", "lin", T, "0 harmonic, 1 golden (2^m phi^n), 2 odd"),
        Param("attack", 0.02, 0.002, 4, "s", "log", A, "raised-cosine attack"),
        Param("decay", 0.0, 0, 30, "s", "lin", A, "t60 of the fundamental; 0 = sustain while held"),
        Param("damp", 0.0, 0, 2, "", "lin", A, "higher partials decay faster: t60_k = decay / (1 + damp (k-1))"),
        Param("release", 0.25, 0.005, 6, "s", "log", A, "raised-cosine release"),
        Param("pan", 0.0, -1, 1, "", "lin", T, "static stereo position"),
        Param("vel_bright", 0.6, 0, 2, "", "lin", V, "harder notes: lower rolloff (brighter)"),
        *common_vel(1.2),
    )

    def tail(self, note):
        return self.p["release"]

    def render(self, note):
        p, v = self.p, note.vel
        f0 = float(mtof(note.pitch))
        n = n_samples(note.gate + p["release"])
        t = t_axis(n)
        ratios = _spectrum(int(round(p["spectrum"])), int(round(p["partials"])))
        roll = max(p["rolloff"] - p["vel_bright"] * (v - 0.7), 0.0)
        x = np.zeros(n)
        count = len(ratios)
        for k, r in enumerate(ratios, start=1):
            f = f0 * r
            if f >= 0.45 * SR:
                break
            a = k ** -roll
            if p["spectrum"] < 0.5 and k % 2 == 0:
                a *= p["even"]
            if a < 1e-4:
                continue
            ph = np.pi * k * k / count                       # Schroeder phases: low crest factor, no randomness
            part = np.sin(2 * np.pi * f * t + ph)
            if p["decay"] > 0:
                part *= np.exp(-6.907755 * t / (p["decay"] / (1 + p["damp"] * (k - 1))))
            x += a * part
        norm = sum((k ** -roll) for k in range(1, count + 1)) or 1.0
        x /= norm
        # raised-cosine attack and release around the gate
        env = np.ones(n)
        na = min(n_samples(p["attack"]), n)
        env[:na] = 0.5 - 0.5 * np.cos(np.pi * np.arange(na) / na)
        g = min(n_samples(note.gate), n)
        nr = n - g
        if nr > 0:
            env[g:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(nr) / nr)
        y = x * env * self.vel_gain(v)
        a = (p["pan"] + 1) * np.pi / 4
        return np.stack([y * np.cos(a), y * np.sin(a)], 1) * np.sqrt(2)
