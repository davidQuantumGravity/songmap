"""Instrument contract (moved from the sketch)."""
import numpy as np
import pytest

import songmap.instruments as I
from songmap.instruments import dsp

SR = dsp.SR


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
