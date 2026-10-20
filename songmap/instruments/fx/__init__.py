"""FX: riser, impact, zap, tick (ported from synth_v0)."""
from __future__ import annotations

import numpy as np

from ..base import A, F, P, RR, T, V, X, Instrument, Param, common_vel, glide_freq, register, smooth_noise
from ..dsp import (SR, adsr, ad, drive, eq, ks_string, mtof, n_samples, pan_mono, phase,
                   saw, sine, square, svf, t60_env, t_axis, white)


@register
class Riser(Instrument):
    name, family = "riser", "fx"
    PARAMS = (Param("start", 300, 50, 2000, "Hz", "log", F), Param("end", 9300, 2000, 18000, "Hz", "log", F),
              Param("tone", 0.25, 0, 1, "", "lin", T, "rising sine under the noise"),
              Param("curve", 2.2, 0.5, 5, "", "lin", A))

    def tail(self, note):
        return 0.05

    def render(self, note):
        p, rng = self.p, self.rng(note)
        n = n_samples(note.gate)
        k = np.arange(n) / n
        fc = p["start"] + (p["end"] - p["start"]) * k ** p["curve"]
        nz = svf(white(n, rng), fc, 1.4, "bp")
        tone = p["tone"] * sine(110 * 2 ** (3 * k), n)
        return (0.8 * nz + tone) * k ** 2 * note.vel


@register
class Impact(Instrument):
    name, family = "impact", "fx"
    PARAMS = (Param("decay", 3.0, 0.5, 8, "s", "log", A), Param("boom", 1.0, 0, 1, "", "lin", T),
              Param("crash", 0.25, 0, 1, "", "lin", T))

    def tail(self, note):
        return self.p["decay"]

    def render(self, note):
        p, rng = self.p, self.rng(note)
        n = n_samples(p["decay"])
        t = t_axis(n)
        boom = p["boom"] * sine(30 + 70 * np.exp(-t * 6), n) * np.exp(-t * 1.6)
        nz = svf(white(n, rng), 2500, 0.7, "lp") * np.exp(-t * 3) * 0.5
        crash = p["crash"] * svf(white(n, rng), 5000, 0.7, "hp") * np.exp(-t * 1.2)
        return drive(boom + nz + crash, 1.5) * note.vel


@register
class Zap(Instrument):
    """Downward square-wave chirp (synth_v0 `zap`): sci-fi blip for lists and reveals."""
    name, family = "zap", "fx"
    PARAMS = (
        Param("f0", 2400, 200, 8000, "Hz", "log", P, "start pitch of the chirp"),
        Param("floor", 80, 20, 400, "Hz", "log", P, "pitch the chirp falls to"),
        Param("sweep", 14, 2, 60, "1/s", "log", P, "chirp speed (exponential rate)"),
        Param("length", 0.35, 0.05, 2, "s", "log", A),
        Param("t60", 0.77, 0.05, 4, "s", "log", A, "amplitude decay"),
        Param("cutoff", 6000, 500, 16000, "Hz", "log", F),
        Param("vel_pitch", 0.5, 0, 2, "oct", "lin", V, "harder hits start higher"),
        Param("vel_bright", 1.0, 0, 3, "oct", "lin", V),
        *common_vel(1.0),
    )

    def tail(self, note):
        return self.p["length"]

    def render(self, note):
        p, v = self.p, note.vel
        n = n_samples(p["length"])
        t = t_axis(n)
        f0 = self.vel_oct(self.p_(note, "f0"), v, p["vel_pitch"])
        x = square(f0 * np.exp(-t * p["sweep"]) + p["floor"], n) * t60_env(n, p["t60"])
        x = svf(x, self.vel_oct(p["cutoff"], v, p["vel_bright"]), 0.707, "lp")
        return x * 0.5 * self.vel_gain(v)


@register
class Tick(Instrument):
    """Short sine ping (synth_v0 `tick`): clock / data texture."""
    name, family = "tick", "fx"
    PARAMS = (
        Param("tone", 3200, 500, 12000, "Hz", "log", P),
        Param("t60", 0.031, 0.005, 0.5, "s", "log", A),
        Param("length", 0.03, 0.005, 0.5, "s", "log", A),
        Param("click", 0.0, 0, 1, "", "lin", T, "noise click on the attack"),
        Param("vel_pitch", 0.3, 0, 2, "oct", "lin", V, "harder hits ping higher"),
        Param("vel_decay", 0.5, 0, 1, "", "lin", V, "harder hits ring longer"),
        *common_vel(1.0), RR,
    )

    def tail(self, note):
        return self.p["length"]

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        n = n_samples(p["length"])
        f = self.vel_oct(self.vary(rng, self.p_(note, "tone"), 0.01), v, p["vel_pitch"])
        d = p["t60"] * (1 - p["vel_decay"] + p["vel_decay"] * v / 0.7)
        x = sine(f, n) * t60_env(n, d)
        if p["click"]:
            x += p["click"] * v * svf(white(n, rng), 6000, 0.8, "hp") * t60_env(n, 0.003)
        return x * self.vel_gain(v)
