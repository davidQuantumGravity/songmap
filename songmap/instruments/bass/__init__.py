"""Bass: mono subtractive bass."""
from __future__ import annotations

import numpy as np

from ..base import A, F, P, RR, T, V, X, Instrument, Param, common_vel, glide_freq, register, smooth_noise
from ..dsp import (SR, adsr, ad, drive, eq, ks_string, mtof, n_samples, pan_mono, phase,
                   saw, sine, square, svf, t60_env, t_axis, white)


@register
class Bass(Instrument):
    name, family, mono = "bass", "bass", True
    PARAMS = (
        Param("saw", 1.0, 0, 1, "", "lin", "osc", "level of the sawtooth oscillator (all harmonics)"),
        Param("square", 0.0, 0, 1, "", "lin", "osc", "level of the square oscillator (odd harmonics only)"),
        Param("sub", 0.5, 0, 1, "", "lin", "osc", "sine one octave down"),
        Param("cutoff", 700, 60, 8000, "Hz", "log", F, "base frequency of the low-pass filter in Hz"),
        Param("res", 1.0, 0.5, 12, "q", "log", F, "filter resonance (Q): boosts harmonics near the cutoff"),
        Param("env_amt", 2.0, 0, 6, "oct", "lin", F, "filter-envelope depth"),
        Param("env_decay", 0.15, 0.01, 1.5, "s", "log", F,
              "how fast the filter closes after the attack (time constant)"),
        Param("attack", 0.003, 0.001, 0.2, "s", "log", A, "amplitude fade-in time"),
        Param("decay", 0.25, 0.01, 2.0, "s", "log", A, "time to fall from the peak to the sustain level"),
        Param("sustain", 0.8, 0, 1, "", "lin", A, "level held while the note is down (0-1)"),
        Param("release", 0.06, 0.01, 1.0, "s", "log", A, "fade-out after the note is released"),
        Param("drive", 1.4, 1, 8, "x", "log", T, "tanh saturation after the filter (1 = clean)"),
        Param("glide", 0.04, 0, 0.5, "s", "log", P, "portamento time on slurred notes"),
        Param("vel_cutoff", 1.5, 0, 4, "oct", "lin", V,
              "octaves the base cutoff moves per unit of velocity around 0.7"),
        *common_vel(1.2), RR,
    )

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        n = n_samples(note.gate + p["release"])
        t = t_axis(n)
        f = glide_freq(note, n, p["glide"]) * (1 + 0.002 * p["rr"] * rng.standard_normal())
        x = p["saw"] * saw(f, n, rng.random()) + p["square"] * square(f, n) + p["sub"] * sine(f / 2, n)
        fenv = np.exp(-t / p["env_decay"]) if note.glide_from is None else 0.3 * np.exp(-t / p["env_decay"])
        fc = self.vel_oct(self.p_(note, "cutoff"), v, p["vel_cutoff"]) * 2 ** (p["env_amt"] * v * fenv)
        x = drive(svf(x, fc, p["res"], "lp"), p["drive"])
        return x * adsr(n, p["attack"], p["decay"], p["sustain"], p["release"], note.gate) * self.vel_gain(v)
