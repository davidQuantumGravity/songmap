"""Synths: pad, pluck, lead."""
from __future__ import annotations

import numpy as np

from ..base import A, F, P, RR, T, V, X, Instrument, Param, common_vel, glide_freq, register, smooth_noise
from ..dsp import (SR, adsr, ad, drive, eq, ks_string, mtof, n_samples, pan_mono, phase,
                   saw, sine, square, svf, t60_env, t_axis, white)


@register
class Pad(Instrument):
    name, family = "pad", "synth"
    PARAMS = (
        Param("voices", 5, 1, 9, "", "lin", "osc", "unison saws per note"),
        Param("detune", 12, 0, 40, "cents", "lin", "osc", "how far apart the outer voices are tuned, in cents"),
        Param("drift", 3, 0, 15, "cents", "lin", "osc", "slow analog pitch wander"),
        Param("cutoff", 1800, 200, 12000, "Hz", "log", F, "low-pass cutoff in Hz"),
        Param("res", 0.8, 0.5, 6, "q", "log", F, "filter resonance (Q)"),
        Param("lfo_rate", 0.15, 0.02, 2, "Hz", "log", F, "slow filter movement"),
        Param("lfo_depth", 0.3, 0, 2, "oct", "lin", F, "how many octaves the LFO moves the cutoff"),
        Param("attack", 0.35, 0.005, 4, "s", "log", A, "fade-in time"),
        Param("decay", 0.5, 0.01, 4, "s", "log", A, "time from the peak down to the sustain level"),
        Param("sustain", 0.85, 0, 1, "", "lin", A, "level held while the note is down (0-1)"),
        Param("release", 0.8, 0.01, 6, "s", "log", A, "fade-out after the note ends"),
        Param("width", 0.8, 0, 1, "", "lin", T, "stereo spread of unison voices"),
        Param("vel_cutoff", 1.0, 0, 3, "oct", "lin", V, "octaves the cutoff moves per unit of velocity around 0.7"),
        *common_vel(1.0), RR,
    )

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        rr = self.rr_rng(note)                          # round robin: each note's detune, filter and swell differ
        detune = self.vary(rr, p["detune"], 0.25)
        n = n_samples(note.gate + p["release"])
        f0 = float(mtof(note.pitch))
        nv = int(round(p["voices"]))
        out = np.zeros((n, 2))
        for k, o in enumerate(np.linspace(-1, 1, nv) if nv > 1 else [0.0]):
            cents = o * detune + p["drift"] * smooth_noise(n, 0.4, rng)
            out += pan_mono(saw(f0 * 2 ** (cents / 1200), n, rng.random()), o * p["width"])
        out /= np.sqrt(nv)
        lfo = np.sin(2 * np.pi * p["lfo_rate"] * t_axis(n) + rng.random() * 6.28)
        cutoff = self.vary(rr, self.p_(note, "cutoff"), 0.12)
        fc = self.vel_oct(cutoff, v, p["vel_cutoff"]) * 2 ** (p["lfo_depth"] * lfo)
        out = svf(out, fc, p["res"], "lp")
        env = adsr(n, max(0.001, self.vary(rr, p["attack"], 0.2)), p["decay"], p["sustain"], p["release"], note.gate,
                   curve=3)
        return out * env[:, None] * self.vel_gain(v)


@register
class Pluck(Instrument):
    name, family = "pluck", "synth"
    PARAMS = (
        Param("pw", 0.35, 0.05, 0.5, "", "lin", "osc", "pulse width"),
        Param("saw_mix", 0.45, 0, 1, "", "lin", "osc", "balance between saw (1) and pulse (0)"),
        Param("cutoff", 2500, 200, 12000, "Hz", "log", F, "where the filter settles after the pluck, in Hz"),
        Param("res", 1.2, 0.5, 8, "q", "log", F, "filter resonance (Q)"),
        Param("env_amt", 2.5, 0, 6, "oct", "lin", F, "how many octaves above cutoff the filter starts"),
        Param("env_decay", 0.08, 0.01, 0.8, "s", "log", F, "how fast the filter closes (time constant)"),
        Param("decay", 0.25, 0.03, 2, "s", "log", A, "amplitude t60"),
        Param("release", 0.03, 0.005, 0.5, "s", "log", A, "fade-out when the note is released early"),
        Param("vel_cutoff", 2.0, 0, 4, "oct", "lin", V, "octaves the cutoff moves per unit of velocity around 0.7"),
        *common_vel(1.5), RR,
    )

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        n = n_samples(min(note.gate, p["decay"] * 1.2) + p["release"])
        t = t_axis(n)
        f = float(mtof(note.pitch))
        x = (1 - p["saw_mix"]) * square(f, n, p["pw"]) + p["saw_mix"] * saw(f, n, rng.random())
        fc = self.vel_oct(self.p_(note, "cutoff"), v, p["vel_cutoff"]) * 2 ** (p["env_amt"] * np.exp(-t / p["env_decay"]))
        x = svf(x, fc, p["res"], "lp")
        env = t60_env(n, self.vary(rng, p["decay"], 0.05)) * adsr(n, 0.001, 0.01, 1.0, p["release"], note.gate)
        return x * env * self.vel_gain(v)


@register
class Lead(Instrument):
    name, family, mono = "lead", "synth", True
    PARAMS = (
        Param("voices", 5, 1, 9, "", "lin", "osc", "how many saws play in unison (rounded to a whole number)"),
        Param("detune", 10, 0, 40, "cents", "lin", "osc", "spread of the unison voices in cents"),
        Param("cutoff", 4500, 300, 16000, "Hz", "log", F, "low-pass cutoff in Hz"),
        Param("res", 0.9, 0.5, 8, "q", "log", F, "filter resonance (Q)"),
        Param("attack", 0.01, 0.001, 1, "s", "log", A, "fade-in time"),
        Param("decay", 0.2, 0.01, 2, "s", "log", A, "time from the peak down to sustain"),
        Param("sustain", 0.75, 0, 1, "", "lin", A, "level while the note is held (0-1)"),
        Param("release", 0.15, 0.01, 2, "s", "log", A, "fade-out after the note ends"),
        Param("vib_rate", 5.5, 1, 9, "Hz", "lin", "vibrato", "vibrato speed in Hz"),
        Param("vib_depth", 14, 0, 60, "cents", "lin", "vibrato", "vibrato width in cents"),
        Param("vib_delay", 0.25, 0, 1.5, "s", "lin", "vibrato", "vibrato fades in, like a singer"),
        Param("glide", 0.06, 0, 0.5, "s", "log", P, "portamento time on slurred notes"),
        Param("breath", 0.04, 0, 0.5, "", "lin", T, "filtered noise riding the note"),
        Param("vel_cutoff", 1.5, 0, 4, "oct", "lin", V, "octaves the cutoff moves per unit of velocity around 0.7"),
        *common_vel(1.2), RR,
    )

    def render(self, note):
        p, v, rng = self.p, note.vel, self.rng(note)
        n = n_samples(note.gate + p["release"])
        t = t_axis(n)
        rate = p["vib_rate"] * self.vary(rng, 1, 0.05)
        vib = p["vib_depth"] * np.sin(2 * np.pi * rate * t) * np.clip((t - p["vib_delay"]) * 3, 0, 1)
        f = glide_freq(note, n, p["glide"]) * 2 ** (vib / 1200)
        nv = int(round(p["voices"]))
        out = np.zeros((n, 2))
        for o in (np.linspace(-1, 1, nv) if nv > 1 else [0.0]):
            out += pan_mono(saw(f * 2 ** (o * p["detune"] / 1200), n, rng.random()), o * 0.5)
        out /= np.sqrt(nv)
        if p["breath"]:
            out += p["breath"] * svf(white(n, rng), f * 3, 2.0, "bp")[:, None]
        out = svf(out, self.vel_oct(self.p_(note, "cutoff"), v, p["vel_cutoff"]), p["res"], "lp")
        return out * adsr(n, p["attack"], p["decay"], p["sustain"], p["release"], note.gate)[:, None] * self.vel_gain(v)
