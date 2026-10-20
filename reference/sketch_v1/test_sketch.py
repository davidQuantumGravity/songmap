"""Checks that the reference sketch does what the docs claim.  Run:  python -m pytest -q"""
import numpy as np
import pytest

import dsp
import instruments as I
import mix
import notation as N
import perform as P

SR = dsp.SR


# ---------------------------------------------------------------- notation
def test_motif_sticky_durations_and_marks():
    evs = N.parse_motif("=mf e4^ d8' c' e4_ g | a2~ g4 (e8) r", name="t")
    assert [e.dur for e in evs] == [1, 0.5, 0.5, 1, 1, 2, 1, 0.5]
    assert evs[0].art == "accent" and evs[0].vel > N.DYN["mf"]
    assert evs[1].art == "staccato" and evs[2].art == "staccato"
    assert evs[5].slur and "ghost" in evs[7].tags and evs[7].vel < 0.35
    assert evs[0].pitches == (64,)


def test_bar_check_message():
    with pytest.raises(N.NotationError, match="bar 1 has 3 beats"):
        N.parse_motif("c4 d e | f1")


def test_degree_mode_and_hairpin():
    evs = N.parse_motif("=p < 0 -3 0 2 | 1/2 0 =f", deg=True, key="E minor")
    assert evs[0].pitches == (64,) and evs[1].pitches == (59,)       # E4, B3
    vels = [e.vel for e in evs]
    assert vels == sorted(vels) and vels[0] == pytest.approx(N.DYN["p"])


def test_dynamics_need_equals_sign():
    with pytest.raises(N.NotationError, match="'=mf'"):
        N.parse_motif("mf c4")


def test_steps():
    evs, bars = N.parse_steps("X...x...x...x..o|f.r.")
    assert bars == 2 and evs[0].vel == 1.0 and evs[-1].beat == pytest.approx(6.5)
    assert "ghost" in evs[4].tags


def test_chords_and_keys():
    assert N.parse_chord("F#m7/C#") == (6, (0, 3, 7, 10), 1)
    assert N.parse_chord("Bbmaj7")[0] == 10
    assert N.parse_key("D dorian") == (2, N.MODES["dorian"])


# ---------------------------------------------------------------- perform
def test_swing_moves_offbeats_only():
    assert P.swing_beat(0.5, 0.66) == pytest.approx(0.66)
    assert P.swing_beat(1.0, 0.66) == 1.0


def test_voice_leading_is_smooth():
    c = P.voice_lead(None, 0, (0, 4, 7))
    f = P.voice_lead(c, 5, (0, 4, 7))
    assert sum(abs(a - b) for a, b in zip(c, f)) <= 6     # C -> F moves by step, not jumps
    assert set(c) & set(f)                                 # keeps a common tone


def test_perform_is_seeded_and_shaped():
    evs = N.parse_motif("c8 c c c c c c c | c c c c c c c c")
    feel = P.Feel(time_ms=5, vel_sd=0.03, seed=3)
    a = P.perform(evs, start_beat=0, spb=0.5, feel=feel, section_shape="p<f")
    b = P.perform(evs, start_beat=0, spb=0.5, feel=feel, section_shape="p<f")
    assert [x.time for x in a] == [x.time for x in b]
    assert np.mean([x.note.vel for x in a[-4:]]) > np.mean([x.note.vel for x in a[:4]]) * 1.5


# ---------------------------------------------------------------- dsp
def _alias_ratio(x, f0):
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    f = np.fft.rfftfreq(len(x), 1 / SR)
    harm = np.zeros_like(f, bool)
    for k in range(1, int(SR / 2 / f0) + 1):
        harm |= np.abs(f - k * f0) < 8
    return spec[~harm].sum() / spec[harm].sum()


def test_polyblep_reduces_aliasing():
    f0, n = 3520.0, SR
    t = np.arange(n) / SR
    naive = 2 * ((f0 * t) % 1) - 1
    assert _alias_ratio(dsp.saw(f0, n), f0) < 0.25 * _alias_ratio(naive, f0)


@pytest.mark.parametrize("f", [82.4, 196.0, 440.0, 1046.5])
def test_ks_pitch_is_accurate(f):
    exc = np.random.default_rng(0).standard_normal(int(SR / f) + 1)
    y = dsp.ks_string(f, 2 * SR, exc, t60=4, brightness=0.8)[SR // 10:]
    spec = np.abs(np.fft.rfft(y * np.hanning(len(y)), 8 * len(y)))
    fr = np.fft.rfftfreq(8 * len(y), 1 / SR)
    m = (fr > 0.7 * f) & (fr < 1.3 * f)
    assert abs(fr[m][np.argmax(spec[m])] - f) / f < 0.002     # within ~3 cents


def test_svf_cutoff_sweep_runs():
    y = dsp.svf(np.random.default_rng(0).standard_normal(SR), np.geomspace(100, 10000, SR), 2.0)
    assert np.all(np.isfinite(y))


# ---------------------------------------------------------------- instruments
def _centroid(x):
    m = x.mean(1) if x.ndim == 2 else x
    s = np.abs(np.fft.rfft(m))
    f = np.fft.rfftfreq(len(m), 1 / SR)
    return (s * f).sum() / (s.sum() + 1e-12)


@pytest.mark.parametrize("name", sorted(I.REGISTRY))
def test_every_instrument_renders(name):
    inst = I.make(name)
    pitch = 36 if name == "bass" else 60
    for v in (0.3, 1.0):
        y = inst.render(I.Note(pitch, v, 0.6, seed=1))
        assert np.all(np.isfinite(y)) and 0.001 < np.max(np.abs(y)) < 4


@pytest.mark.parametrize("name", ["snare", "hat", "bass", "pluck", "keys", "epiano", "string_pluck", "kick", "clap"])
def test_velocity_changes_timbre_not_just_level(name):
    inst = I.make(name, rr=0) if "rr" in I.REGISTRY[name]().spec else I.make(name)
    soft = inst.render(I.Note(48, 0.3, 0.5, seed=1))
    hard = inst.render(I.Note(48, 1.0, 0.5, seed=1))
    assert _centroid(hard) > _centroid(soft) * 1.05


def test_unknown_param_suggests_fix():
    with pytest.raises(I.ParamError, match="did you mean cutoff"):
        I.make("bass", cutof=500)


def test_schema_is_json_ready():
    import json
    s = json.dumps([c.schema() for c in I.REGISTRY.values()])
    assert '"vel_curve"' in s


# ---------------------------------------------------------------- mix
def test_lufs_matches_ebu_3341_case1():
    t = np.arange(20 * SR) / SR
    s = 10 ** (-23 / 20) * np.sin(2 * np.pi * 1000 * t)
    assert mix.lufs(np.stack([s, s], 1)) == pytest.approx(-23.0, abs=0.1)


def test_limiter_respects_ceiling():
    x = np.random.default_rng(0).standard_normal((SR, 2)) * 0.5
    y = mix.limiter(x, -1.0)
    assert np.max(np.abs(y)) <= 10 ** (-1 / 20) + 1e-6


def test_master_hits_target():
    rng = np.random.default_rng(0)
    x = dsp.svf(rng.standard_normal(SR * 6), 2000, 0.7) * 0.1
    y = mix.master(np.stack([x, x], 1), -14)
    assert mix.lufs(y) == pytest.approx(-14, abs=0.5) and mix.true_peak_db(y) < -0.5
