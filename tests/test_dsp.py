"""DSP building blocks (moved from the sketch)."""
import numpy as np
import pytest

from songmap.instruments import dsp

SR = dsp.SR


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
