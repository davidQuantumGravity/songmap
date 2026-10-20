"""Drums: kick, snare, clap, hat."""
from __future__ import annotations

import numpy as np

from ..base import A, F, P, RR, T, V, X, Instrument, Param, common_vel, glide_freq, register, smooth_noise
from ..dsp import (SR, adsr, ad, drive, eq, ks_string, mtof, n_samples, pan_mono, phase,
                   saw, sine, square, svf, t60_env, t_axis, white)


@register
class Kick(Instrument):
    name, family = "kick", "drum"
    PARAMS = (
        Param("tune", 48, 30, 90, "Hz", "log", P, "resting pitch of the body"),
        Param("sweep", 30, 0, 48, "st", "lin", P, "start pitch above tune"),
        Param("sweep_time", 0.035, 0.005, 0.2, "s", "log", P),
        Param("decay", 0.45, 0.05, 2.0, "s", "log", A, "t60 of the body"),
        Param("sub", 0.0, 0, 1, "", "lin", A, "extra pure-sine tail (808 boom)"),
        Param("click", 0.3, 0, 1, "", "lin", T, "beater click level"),
        Param("click_tone", 3500, 1000, 9000, "Hz", "log", T),
        Param("drive", 1.6, 1, 8, "x", "log", T),
        Param("vel_sweep", 0.5, 0, 1, "", "lin", V, "harder hits sweep further"),
        Param("vel_click", 0.8, 0, 1, "", "lin", V, "harder hits click more"),
        *common_vel(1.4), RR,
    )

    def tail(self, note):
        return self.p["decay"] * 1.3

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        n = n_samples(self.tail(note))
        t = t_axis(n)
        sweep = p["sweep"] * (1 - p["vel_sweep"] + p["vel_sweep"] * v) * self.vary(rng, 1, 0.05)
        f = p["tune"] * 2 ** (sweep / 12 * np.exp(-t / p["sweep_time"]))
        x = sine(f, n) * t60_env(n, self.vary(rng, p["decay"], 0.06))
        if p["sub"]:
            x += p["sub"] * sine(p["tune"], n) * t60_env(n, p["decay"] * 1.6) * np.clip(t / 0.01, 0, 1)
        ck = p["click"] * (1 - p["vel_click"] + p["vel_click"] * v)
        x += ck * svf(white(n, rng), p["click_tone"], 1.0, "bp") * t60_env(n, 0.012)
        return drive(x, p["drive"]) * self.vel_gain(v)


@register
class Snare(Instrument):
    name, family = "snare", "drum"
    PARAMS = (
        Param("tone", 185, 120, 320, "Hz", "log", P, "shell fundamental"),
        Param("tone_decay", 0.12, 0.02, 0.5, "s", "log", A),
        Param("tone_mix", 0.45, 0, 1, "", "lin", T, "shell vs. wires"),
        Param("noise_decay", 0.22, 0.04, 0.8, "s", "log", A, "wire rattle t60"),
        Param("noise_hp", 1500, 300, 5000, "Hz", "log", F),
        Param("noise_lp", 9000, 2000, 18000, "Hz", "log", F),
        Param("snap", 0.4, 0, 1, "", "lin", T, "stick transient"),
        Param("drive", 1.3, 1, 6, "x", "log", T),
        Param("vel_bright", 1.5, 0, 4, "oct", "lin", V, "ghost notes darker, accents brighter"),
        *common_vel(1.6), RR,
    )

    def tail(self, note):
        return max(self.p["noise_decay"], self.p["tone_decay"]) * 1.3

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        n = n_samples(self.tail(note))
        t = t_axis(n)
        f = self.vary(rng, p["tone"], 0.01) * (1 + 0.4 * np.exp(-t / 0.008))
        shell = (sine(f, n) + 0.45 * sine(f * 1.59, n)) * t60_env(n, p["tone_decay"])
        nd = p["noise_decay"] * (0.6 + 0.4 * v) * self.vary(rng, 1, 0.08)
        wires = svf(white(n, rng), p["noise_hp"], 0.7, "hp")
        wires = svf(wires, self.vel_oct(p["noise_lp"], v, p["vel_bright"]), 0.7, "lp") * t60_env(n, nd)
        snap = p["snap"] * v * svf(white(n, rng), 5000, 0.8, "bp") * t60_env(n, 0.006)
        x = p["tone_mix"] * shell + (1 - p["tone_mix"]) * 0.9 * wires + snap
        return drive(x, p["drive"]) * self.vel_gain(v)


@register
class Clap(Instrument):
    name, family = "clap", "drum"
    PARAMS = (
        Param("bursts", 4, 1, 8, "", "lin", T, "number of hand claps in the cluster"),
        Param("spread", 0.011, 0.003, 0.03, "s", "log", T, "gap between bursts"),
        Param("decay", 0.14, 0.03, 0.8, "s", "log", A, "tail of the last burst"),
        Param("center", 1400, 600, 4000, "Hz", "log", F),
        Param("q", 1.2, 0.5, 4, "", "lin", F),
        Param("vel_bright", 1.0, 0, 3, "oct", "lin", V),
        *common_vel(1.5), RR,
    )

    def tail(self, note):
        return self.p["spread"] * self.p["bursts"] + self.p["decay"] * 1.3

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        n = n_samples(self.tail(note))
        t = t_axis(n)
        e = np.zeros(n)
        nb = int(round(p["bursts"]))
        off = 0.0
        for k in range(nb):
            i = n_samples(off)
            last = k == nb - 1
            e[i:] += np.exp(-t[: n - i] / (p["decay"] / 6.9 if last else 0.0025))
            off += p["spread"] * (1 + 0.6 * p["rr"] * (rng.random() - 0.5))
        x = svf(white(n, rng), self.vel_oct(p["center"], v, p["vel_bright"]), p["q"], "bp")
        return x * e * 1.4 * self.vel_gain(v)


@register
class Hat(Instrument):
    """808-style: six detuned square waves (metal) + noise, band-passed high."""
    name, family = "hat", "drum"
    RATIOS = (205.3, 304.4, 369.6, 522.7, 540.0, 800.0)
    PARAMS = (
        Param("tune", 1.0, 0.5, 2.0, "x", "log", P, "scales the metallic partials"),
        Param("decay", 0.05, 0.015, 1.2, "s", "log", A, "0.05 closed, 0.4+ open"),
        Param("metal", 0.6, 0, 1, "", "lin", T, "square-wave metal vs. noise"),
        Param("hp", 7000, 3000, 12000, "Hz", "log", F),
        Param("color", 10000, 5000, 16000, "Hz", "log", F, "band-pass center"),
        Param("vel_decay", 0.5, 0, 1, "", "lin", V, "harder hits ring longer"),
        Param("vel_bright", 1.0, 0, 3, "oct", "lin", V),
        *common_vel(1.4), RR,
    )

    def tail(self, note):
        return self.p["decay"] * 1.5

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        n = n_samples(self.tail(note))
        metal = sum(square(r * p["tune"] * self.vary(rng, 1, 0.003), n, phase0=rng.random()) for r in self.RATIOS) / 6
        x = p["metal"] * metal + (1 - p["metal"]) * white(n, rng) * 0.5
        x = svf(x, self.vel_oct(p["color"], v, p["vel_bright"]), 0.9, "bp")
        x = svf(x, p["hp"], 0.7, "hp")
        d = p["decay"] * (1 - p["vel_decay"] + p["vel_decay"] * v * 1.3) * self.vary(rng, 1, 0.1)
        return x * ad(n, 0.0005, d) * 2.0 * self.vel_gain(v)
