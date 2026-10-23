"""Keys: modal piano, FM e-piano, tonewheel organ."""
from __future__ import annotations

import numpy as np

from ..base import A, F, P, RR, T, V, X, Instrument, Param, common_vel, glide_freq, register, smooth_noise
from ..dsp import (SR, adsr, ad, drive, eq, ks_string, mtof, n_samples, pan_mono, phase,
                   saw, sine, square, svf, t60_env, t_axis, white)


@register
class Keys(Instrument):
    """Modal piano: stiff-string partials, hammer comb, two-stage decay, damper release."""
    name, family = "keys", "keys"
    PARAMS = (
        Param("partials", 24, 4, 48, "", "lin", T, "how many sine partials make up each note (more = more detail)"),
        Param("inharm", 0.0004, 0, 0.003, "B", "lin", T, "string stiffness: f_n = n f0 sqrt(1 + B n^2)"),
        Param("hardness", 0.5, 0, 1, "", "lin", T, "hammer felt hardness = brightness"),
        Param("hammer_pos", 0.12, 0.05, 0.3, "", "lin", T, "strike point (notches partial 1/pos)"),
        Param("t60", 6.0, 0.5, 30, "s", "log", A, "decay at middle C; lower notes ring longer"),
        Param("aftersound", 0.3, 0, 1, "", "lin", A, "slow second decay stage (piano 'bloom')"),
        Param("unison", 1.2, 0, 6, "cents", "lin", T, "detune between the 2 strings (beating)"),
        Param("thump", 0.15, 0, 1, "", "lin", T, "hammer/action noise"),
        Param("release", 0.25, 0.02, 2, "s", "log", A, "damper speed"),
        Param("spread", 0.6, 0, 1, "", "lin", T, "stereo: low notes left, high right"),
        Param("vel_hard", 1.0, 0, 2, "", "lin", V, "harder hits = brighter"),
        *common_vel(1.6), RR,
    )

    def tail(self, note):
        return self.p["release"]

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        rr = self.rr_rng(note)                          # round robin: no two hammer strikes are identical
        f0 = float(mtof(note.pitch))
        t60 = self.vary(rr, p["t60"], 0.08) * 2 ** (-(note.pitch - 60) / 18)
        n = n_samples(min(note.gate, t60 * 1.5) + p["release"])
        t = t_axis(n)
        hard = np.clip(p["hardness"] + p["vel_hard"] * (v - 0.7) + 0.08 * p["rr"] * rr.standard_normal(), 0, 1.5)
        tilt = np.clip(2.4 - 1.6 * hard, 0.4, 3.0)
        x = np.zeros(n)
        for k in range(1, int(p["partials"]) + 1):
            fk = k * f0 * np.sqrt(1 + p["inharm"] * k * k)
            if fk > 0.45 * SR:
                break
            a = k ** -tilt * abs(np.sin(np.pi * k * p["hammer_pos"]))
            tk = t60 / (1 + 0.25 * (k - 1))
            env = (1 - p["aftersound"]) * np.exp(-6.9 * t / (tk * 0.25)) + p["aftersound"] * np.exp(-6.9 * t / tk)
            unison = self.vary(rr, p["unison"], 0.3) if k == 1 else unison
            for s in (-0.5, 0.5):
                x += a * env * np.sin(2 * np.pi * fk * 2 ** (s * unison / 1200) * t + rng.random() * 6.28)
        x *= np.clip(t / 0.002, 0, 1)
        if p["thump"]:
            x += p["thump"] * v * svf(white(n, rng), 300 + 600 * hard, 0.8, "bp") * t60_env(n, 0.04)
        x *= adsr(n, 0.0005, 0.01, 1.0, p["release"], note.gate)
        x = x / (np.max(np.abs(x)) + 1e-9) * 0.7 * self.vel_gain(v)
        return pan_mono(x, p["spread"] * np.clip((note.pitch - 60) / 30, -1, 1))


@register
class EPiano(Instrument):
    """Two-operator FM tine piano (Rhodes/DX7 EP family) with velocity 'bark'."""
    name, family = "epiano", "keys"
    PARAMS = (
        Param("index", 1.2, 0, 6, "", "lin", T, "FM brightness at medium velocity"),
        Param("index_decay", 0.6, 0.05, 4, "s", "log", T,
              "how fast the brightness fades after the attack (time constant)"),
        Param("tine", 0.25, 0, 1, "", "lin", T, "metallic 14:1 attack transient"),
        Param("t60", 4.0, 0.5, 15, "s", "log", A, "decay time at middle C (higher notes decay faster)"),
        Param("release", 0.3, 0.02, 2, "s", "log", A, "fade after the key is released"),
        Param("trem_rate", 4.5, 0.5, 9, "Hz", "lin", "tremolo", "speed of the stereo auto-pan, in Hz"),
        Param("trem_depth", 0.25, 0, 1, "", "lin", "tremolo", "stereo auto-pan depth"),
        Param("vel_index", 2.5, 0, 6, "", "lin", V, "hard hits bark"),
        *common_vel(1.5), RR,
    )

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        rr = self.rr_rng(note)                          # round robin: each tine barks a little differently
        f = float(mtof(note.pitch))
        t60 = self.vary(rr, p["t60"], 0.08) * 2 ** (-(note.pitch - 60) / 24)
        n = n_samples(min(note.gate, t60 * 1.5) + p["release"])
        t = t_axis(n)
        idx = self.vary(rr, p["index"] + p["vel_index"] * max(v - 0.5, 0), 0.15) * np.exp(-t / p["index_decay"])
        tine = self.vary(rr, p["tine"], 0.3)
        mod = idx * np.sin(2 * np.pi * f * t) + tine * v * np.sin(2 * np.pi * 14 * f * t) * np.exp(-t / 0.02)
        x = np.sin(2 * np.pi * f * t + mod + rng.random()) * t60_env(n, t60)
        x *= adsr(n, 0.001, 0.01, 1.0, p["release"], note.gate) * self.vel_gain(v)
        pan = p["trem_depth"] * np.sin(2 * np.pi * p["trem_rate"] * t + rng.random() * 6.28)
        a = (pan + 1) * np.pi / 4
        return np.stack([x * np.cos(a), x * np.sin(a)], 1) * np.sqrt(2)


@register
class Organ(Instrument):
    """Additive tonewheel organ: nine drawbars, key click, percussion, rotary speaker."""
    name, family = "organ", "keys"
    FOOT = (0.5, 1.5, 1, 2, 3, 4, 5, 6, 8)   # 16', 5 1/3', 8', 4', 2 2/3', 2', 1 3/5', 1 1/3', 1'
    PARAMS = tuple(Param(f"db{i + 1}", d, 0, 8, "", "lin", "drawbars", lbl)
                   for i, (d, lbl) in enumerate(zip((8, 8, 8, 0, 0, 0, 0, 0, 0),
                                                    ("16'", "5 1/3'", "8'", "4'", "2 2/3'", "2'", "1 3/5'", "1 1/3'", "1'")))) + (
        Param("perc", 0.0, 0, 1, "", "lin", T, "2nd-harmonic percussion"),
        Param("click", 0.3, 0, 1, "", "lin", T, "key-contact click"),
        Param("rotor", 0.7, 0, 6.5, "Hz", "lin", "rotary", "0 = off, 0.7 chorale, 6.5 tremolo"),
        Param("release", 0.04, 0.005, 0.5, "s", "log", A, "how quickly the sound stops after the key is released"),
        *common_vel(0.0),
    )

    def render(self, note):
        p, rng = self.p, self.rng(note)
        f = float(mtof(note.pitch))
        n = n_samples(note.gate + p["release"])
        t = t_axis(n)
        x = sum(p[f"db{i + 1}"] / 8 * sine(f * r, n, rng.random()) for i, r in enumerate(self.FOOT) if f * r < 0.45 * SR)
        if p["perc"]:
            x += p["perc"] * sine(f * 2, n) * t60_env(n, 0.5)
        if p["click"]:
            x += p["click"] * svf(white(n, rng), 2500, 1.0, "bp") * t60_env(n, 0.006)
        x *= adsr(n, 0.003, 0.01, 1.0, p["release"], note.gate) / 3
        if not p["rotor"]:
            return x
        ph = 2 * np.pi * p["rotor"] * t + rng.random() * 6.28
        doppler = np.interp(np.arange(n) + 12 * np.sin(ph), np.arange(n), x)
        am = 1 + 0.25 * np.sin(ph)[:, None] * np.array([1, -1])
        return np.stack([doppler, doppler], 1) * am
