"""FX: riser, impact, zap, tick (ported from synth_v0)."""
from __future__ import annotations

import numpy as np

from ..base import A, F, P, RR, T, V, X, Instrument, Param, common_vel, glide_freq, register, smooth_noise
from ..dsp import (SR, adsr, ad, drive, eq, ks_string, mtof, n_samples, pan_mono, phase,
                   saw, sine, square, svf, t60_env, t_axis, white)


def _fade_end(x: np.ndarray, frac: float = 0.15, most: float = 0.4) -> np.ndarray:
    """Fade the last `frac` of a sound (at most `most` seconds) to silence with a raised cosine, so a sound
    whose length is shorter than its decay stops smoothly instead of clicking."""
    n = len(x)
    k = min(int(n * frac), n_samples(most))
    if k > 1:
        x = x.copy()
        x[-k:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(1, k + 1) / k)
    return x


@register
class Riser(Instrument):
    name, family = "riser", "fx"
    PARAMS = (Param("start", 300, 50, 2000, "Hz", "log", F, "where the noise sweep starts"),
              Param("end", 9300, 2000, 18000, "Hz", "log", F, "where the noise sweep ends"),
              Param("tone", 0.25, 0, 1, "", "lin", T, "rising sine under the noise"),
              Param("curve", 2.2, 0.5, 5, "", "lin", F, "sweep shape: 1 steady, higher = slow then rushing"),
              Param("vel_bright", 1.0, 0, 3, "oct", "lin", V, "harder risers sweep higher and narrower"))

    def tail(self, note):
        return 0.05

    def render(self, note):
        p, rng = self.p, self.rng(note)
        n = n_samples(note.gate)
        k = np.arange(n) / n
        end = min(self.vel_oct(p["end"], note.vel, p["vel_bright"]), 0.45 * SR)
        fc = p["start"] + (end - p["start"]) * k ** p["curve"]
        q = 1.4 * 2 ** (0.5 * p["vel_bright"] * (note.vel - 0.7))     # harder: a more focused, whistling band
        nz = svf(white(n, rng), fc, q, "bp")
        tone = p["tone"] * sine(110 * 2 ** (3 * k), n)
        return _fade_end((0.8 * nz + tone) * k ** 2 * note.vel)


@register
class Impact(Instrument):
    name, family = "impact", "fx"
    PARAMS = (Param("decay", 3.0, 0.5, 8, "s", "log", A, "how long the hit rings; it fades to silence by then"),
              Param("boom", 1.0, 0, 1, "", "lin", T, "the sub drop: a sine falling from 100 to 30 Hz"),
              Param("crash", 0.25, 0, 1, "", "lin", T, "high noise wash"),
              Param("vel_bright", 1.0, 0, 3, "oct", "lin", V, "harder hits are brighter (noise opens, more crash)"))

    def tail(self, note):
        return self.p["decay"]

    def render(self, note):
        p, rng = self.p, self.rng(note)
        n = n_samples(p["decay"])
        t = t_axis(n)
        v = note.vel
        slow = 3.0 / p["decay"]                        # shorter decays die faster (3 s keeps the original rates)
        boom = p["boom"] * sine(30 + 70 * np.exp(-t * 6), n) * np.exp(-t * 1.6 * max(slow, 1))
        nz = svf(white(n, rng), self.vel_oct(2500, v, p["vel_bright"]), 0.7, "lp") * np.exp(-t * 3 * max(slow, 1)) * 0.5
        crash = (p["crash"] * (1 + 0.5 * p["vel_bright"] * (v - 0.7)) * svf(white(n, rng), 5000, 0.7, "hp")
                 * np.exp(-t * 1.2 * max(slow, 1)))
        return _fade_end(drive(boom + nz + crash, 1.5) * v, 0.25)


@register
class Zap(Instrument):
    """Downward square-wave chirp (synth_v0 `zap`): sci-fi blip for lists and reveals."""
    name, family = "zap", "fx"
    PARAMS = (
        Param("f0", 2400, 200, 8000, "Hz", "log", P, "start pitch of the chirp"),
        Param("floor", 80, 20, 400, "Hz", "log", P, "pitch the chirp falls to"),
        Param("sweep", 14, 2, 60, "1/s", "log", P, "chirp speed (exponential rate)"),
        Param("length", 0.35, 0.05, 2, "s", "log", A, "total length of the sound in seconds (a hard stop)"),
        Param("t60", 0.77, 0.05, 4, "s", "log", A, "amplitude decay"),
        Param("cutoff", 6000, 500, 16000, "Hz", "log", F, "low-pass cutoff in Hz"),
        Param("vel_pitch", 0.5, 0, 2, "oct", "lin", V, "harder hits start higher"),
        Param("vel_bright", 1.0, 0, 3, "oct", "lin", V, "octaves the low-pass moves per unit of velocity around 0.7"),
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
        return _fade_end(x * 0.5 * self.vel_gain(v))


@register
class Tick(Instrument):
    """Short sine ping (synth_v0 `tick`): clock / data texture."""
    name, family = "tick", "fx"
    PARAMS = (
        Param("tone", 3200, 500, 12000, "Hz", "log", P, "pitch of the ping in Hz"),
        Param("t60", 0.031, 0.005, 0.5, "s", "log", A, "decay time of the ping"),
        Param("length", 0.03, 0.005, 0.5, "s", "log", A, "total length of the sound in seconds (a hard stop)"),
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
        return _fade_end(x * self.vel_gain(v))
