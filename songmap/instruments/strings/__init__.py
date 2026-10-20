"""Plucked strings (Karplus-Strong)."""
from __future__ import annotations

import numpy as np

from ..base import A, F, P, RR, T, V, X, Instrument, Param, common_vel, glide_freq, register, smooth_noise
from ..dsp import (SR, adsr, ad, drive, eq, ks_string, mtof, n_samples, pan_mono, phase,
                   saw, sine, square, svf, t60_env, t_axis, white)


@register
class StringPluck(Instrument):
    """Karplus-Strong guitar / harp / koto. Pick position and body EQ make it woody."""
    name, family = "string_pluck", "string"
    PARAMS = (
        Param("t60", 3.0, 0.2, 12, "s", "log", A, "ring time while held"),
        Param("brightness", 0.75, 0.5, 1.0, "", "lin", T, "loop damping (0.5 dull, 1 bright)"),
        Param("pick_pos", 0.2, 0.03, 0.5, "", "lin", T, "0.5 = middle (hollow), 0.05 = bridge (twangy)"),
        Param("pick_tone", 6000, 800, 16000, "Hz", "log", T, "excitation brightness"),
        Param("body", 0.5, 0, 1, "", "lin", T, "wooden body resonance"),
        Param("release", 0.08, 0.01, 1.0, "s", "log", A, "damping when the note is released"),
        Param("vel_bright", 2.0, 0, 4, "oct", "lin", V),
        *common_vel(1.3), RR,
    )

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        n = n_samples(note.gate + p["release"])
        f = float(mtof(note.pitch))
        per = SR / f
        m = int(per) + 1
        exc = svf(white(m, rng), self.vel_oct(p["pick_tone"], v, p["vel_bright"]), 0.7, "lp")
        d = max(1, int(p["pick_pos"] * per))
        exc[d:] -= exc[:-d].copy()                     # comb = pick position
        y = ks_string(f, n, exc, self.vary(rng, p["t60"], 0.05), p["brightness"])
        if p["body"]:
            b = p["body"] * 6
            y = eq(eq(eq(y, "peak", 110, b, 1.5), "peak", 230, b * 0.7, 2.0), "peak", 2800, -b * 0.5, 0.8)
        y *= adsr(n, 0.0005, 0.01, 1.0, p["release"], note.gate)
        return y / (np.max(np.abs(y)) + 1e-9) * 0.8 * self.vel_gain(v)
