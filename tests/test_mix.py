"""Loudness, limiter, master (moved from the sketch)."""
import numpy as np
import pytest

from songmap.export import qa as mix_qa
from songmap.instruments import dsp
from songmap.mix import fx as mix_fx
from songmap.mix import master as mix_master

SR = dsp.SR


def test_lufs_matches_ebu_3341_case1():
    t = np.arange(20 * SR) / SR
    s = 10 ** (-23 / 20) * np.sin(2 * np.pi * 1000 * t)
    assert mix_qa.lufs(np.stack([s, s], 1)) == pytest.approx(-23.0, abs=0.1)


def test_limiter_respects_ceiling():
    x = np.random.default_rng(0).standard_normal((SR, 2)) * 0.5
    y = mix_fx.limiter(x, -1.0)
    assert np.max(np.abs(y)) <= 10 ** (-1 / 20) + 1e-6


def test_master_hits_target():
    rng = np.random.default_rng(0)
    x = dsp.svf(rng.standard_normal(SR * 6), 2000, 0.7) * 0.1
    y = mix_master.master(np.stack([x, x], 1), -14)
    assert mix_qa.lufs(y) == pytest.approx(-14, abs=0.5) and mix_qa.true_peak_db(y) < -0.5


def test_a_send_to_a_missing_return_is_a_song_error_at_check_time():
    import pytest
    from songmap.arrange.expand import expand
    from songmap.parse import lang
    from songmap.parse.errors import SongError
    s = lang.loads('song "S" 120 4/4 C\nx 2 | pad:warm lead="e+1 | d+1"\nmix lead 6 delay=.2\n', "s.sm")
    arr = expand(s)
    with pytest.raises(SongError) as e:
        arr.ensemble.check(s.parts())
    assert "unknown return 'delay'" in str(e.value) and "inserts lead delay(" in str(e.value)
