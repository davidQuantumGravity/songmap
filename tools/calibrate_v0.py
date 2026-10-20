"""Level calibration of the default ensemble (songmap/arrange/defaults.yaml) against synth_v0.

    python tools/calibrate_v0.py           # prints, per voice: synth_v0 level, ours, and the gain_db to use

Each synth_v0 voice is rendered as synth_v0 played it (its function, its gain), resampled to
48 kHz, and compared by K-weighted energy with the engine's replacement (preset, velocity and
current kit/part gain from defaults.yaml). `suggested` is the gain_db that makes them equal.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from scipy.signal import resample_poly

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from songmap.arrange.ensemble import defaults  # noqa: E402
from songmap.export.qa import k_weight  # noqa: E402
from songmap.instruments import Note, make  # noqa: E402
from songmap.instruments.dsp import as_stereo, pan_mono  # noqa: E402
from v0_oracle import _load  # noqa: E402

V0 = _load(60)
BEAT = 0.5


def energy_db(x: np.ndarray) -> float:
    y = k_weight(as_stereo(x))
    return float(10 * np.log10(np.sum(y ** 2) + 1e-20))


def v0(sig, gain):
    """synth_v0 places mono voices with pan 0: L = R = sig * gain * 1.414 * cos(pi/4) = sig * gain."""
    x = resample_poly(np.asarray(sig, float), 160, 147) * gain
    return np.stack([x, x], 1)


def ours(ref, pitch, vel, gate, gain_db, params=None, pitches=None, pan=0.0):
    inst = make(ref)
    y = 0
    for p in pitches or [pitch]:
        s = inst.render(Note(p, vel, gate, seed=1, params=params or {}))
        s = pan_mono(s, pan) if s.ndim == 1 else s
        y = s if isinstance(y, int) else _add(y, s)
    return y * 10 ** (gain_db / 20)


def _add(a, b):
    n = max(len(a), len(b))
    out = np.zeros((n, 2))
    out[:len(a)] += a
    out[:len(b)] += b
    return out


def main():
    d = defaults()["instruments"]
    kit, fx = d["drums"]["kit"], d["fx"]["kit"]
    rng_avg = 8          # average noisy voices over several renders
    rows = []

    def row(name, v0_sigs, ours_fn, cur):
        a = np.mean([10 ** (energy_db(s) / 10) for s in v0_sigs])
        b = np.mean([10 ** (energy_db(ours_fn(k)) / 10) for k in range(rng_avg)])
        da, db_ = 10 * np.log10(a), 10 * np.log10(b)
        rows.append((name, da, db_, cur, cur + da - db_))

    vel_x = 0.78
    row("drums.kick", [v0(V0.kick(), 0.95) for _ in range(rng_avg)],
        lambda k: ours(kit["kick"]["use"], 60, vel_x, 0.1, kit["kick"]["gain_db"]), kit["kick"]["gain_db"])
    row("drums.snare", [v0(V0.snare(), 0.45) for _ in range(rng_avg)],
        lambda k: ours(kit["snare"]["use"], 60, vel_x, 0.1, kit["snare"]["gain_db"]), kit["snare"]["gain_db"])
    row("drums.clap", [v0(V0.clap(), 0.35) for _ in range(rng_avg)],
        lambda k: ours(kit["clap"]["use"], 60, vel_x, 0.1, kit["clap"]["gain_db"]), kit["clap"]["gain_db"])
    row("drums.fill", [v0(V0.snare(0.15), 0.46) for _ in range(rng_avg)],
        lambda k: ours(kit["fill"]["use"], 60, 0.79, 0.1, kit["fill"]["gain_db"]), kit["fill"]["gain_db"])
    row("drums.hat", [v0(V0.hat(), 0.16) for _ in range(rng_avg)],
        lambda k: ours(kit["hat"]["use"], 60, vel_x, 0.1, kit["hat"]["gain_db"]), kit["hat"]["gain_db"])
    row("drums.ohat", [v0(V0.hat(open_=True), 0.16) for _ in range(rng_avg)],
        lambda k: ours(kit["ohat"]["use"], 60, vel_x, 0.1, kit["ohat"]["gain_db"]), kit["ohat"]["gain_db"])
    row("drums.hat16", [v0(V0.hat(0.04), 0.11) for _ in range(rng_avg)],
        lambda k: ours(kit["hat16"]["use"], 60, vel_x, 0.1, kit["hat16"]["gain_db"]), kit["hat16"]["gain_db"])
    # pitched parts: typical notes of track B (E minor), at the gates the styles use
    b = d["bass"]
    row("bass (8ths, 900 Hz)", [v0(V0.bass_note(40, BEAT / 2 * 0.9, 900), 0.32)],
        lambda k: ours(b["use"], 40, 0.62, BEAT / 2 * 0.9, b["gain_db"]), b["gain_db"])
    p = d["pad"]
    row("pad (Em triad)", [v0(V0.pad_chord([76, 79, 83], 4.0, 1800, 1.0), 0.5) for _ in range(2)],
        lambda k: ours(p["use"], 0, 0.62, 3.4, p["gain_db"], pitches=[76, 79, 83]), p["gain_db"])
    a = d["arp"]
    row("arp (pluck 2500 Hz)", [v0(V0.pluck(76, 0.2, 2500), 0.13)],
        lambda k: ours(a["use"], 76, 0.62, 0.2, a["gain_db"], params={"cutoff": 2500}), a["gain_db"])
    ld = d["lead"]
    row("lead (1 beat)", [v0(V0.lead_note(76, BEAT * 0.95), 0.16)],
        lambda k: ours(ld["use"], 76, 0.62, BEAT * 0.9, ld["gain_db"]), ld["gain_db"])
    row("fx.riser (2 bars)", [v0(V0.riser(4.0), 0.35) for _ in range(2)],
        lambda k: ours(fx["riser"]["use"], 60, 1.0, 4.0, fx["riser"]["gain_db"]), fx["riser"]["gain_db"])
    row("fx.impact", [v0(V0.impact(), 0.75) for _ in range(2)],
        lambda k: ours(fx["impact"]["use"], 60, 1.0, 2.0, fx["impact"]["gain_db"]), fx["impact"]["gain_db"])
    row("fx.zap", [v0(V0.zap(f0=2000), 0.25)],
        lambda k: ours(fx["zap"]["use"], 60, 0.7, 0.3, fx["zap"]["gain_db"], params={"f0": 2000}), fx["zap"]["gain_db"])
    row("fx.tick", [v0(V0.tick(), 0.12)],
        lambda k: ours(fx["tick"]["use"], 60, vel_x, 0.03, fx["tick"]["gain_db"]), fx["tick"]["gain_db"])
    print(f"{'voice':22s} {'synth_v0':>9s} {'ours':>9s} {'gain_db':>8s} {'suggested':>10s}")
    for name, da, db_, cur, sug in rows:
        print(f"{name:22s} {da:9.2f} {db_:9.2f} {cur:8.2f} {sug:10.1f}")


if __name__ == "__main__":
    main()
