"""36edo golden harmony in the engine: passing placeholders, voiced styles, clean instrument, clean master."""
import numpy as np
import pytest

from songmap.arrange.expand import expand
from songmap.instruments import Note, make
from songmap.instruments.dsp import SR
from songmap.mix.master import master_clean


def _song(make_song, harmony, parts, bars):
    return make_song({"tuning": "36edo", "instruments": {"chords": "clean/organ", "melody": "clean/lead"},
                      "sections": [{"name": "a", "bars": bars, "harmony": harmony, "parts": parts}]})


def test_voiced_chords_move_by_sixth_steps_through_golden_passing(make_song):
    arr = expand(_song(make_song, "G:1 ~:0.5 ~:0.5 C:2", {"chords": "hold"}, 4))
    evs = arr.parts["chords"]
    assert [arr.harmony.chord_at(e.beat).symbol for e in evs] == ["G", "vEbT13/G", "vCg/G", "C"]
    # the engine's own four lines (docs/GOLDEN_THEORY.md, golden six-four): G pedal, upper voices by sixth-steps
    assert [e.pitches[0] for e in evs] == [43, 43, 43, 48]
    for a, b in zip(evs, evs[1:]):
        assert max(abs(x - y) for x, y in zip(a.pitches[1:], b.pitches[1:])) <= 2 / 3 + 1e-9     # a whole step is 2+2+2 sixth-steps
    steps = {round(p * 3) % 3 for e in evs[1:3] for p in e.pitches}
    assert steps - {0}                                    # the passing chords really leave the 12-ET grid


def test_top_voice_is_the_soprano_of_hold(make_song):
    arr = expand(_song(make_song, "F:1 ~g:0.5 ~g:0.5 G:2", {"chords": "hold", "melody": "top"}, 4))
    tops = [max(e.pitches) for e in arr.parts["chords"]]
    mel = [e.pitches[0] - 12 for e in arr.parts["melody"]]           # `top` sounds an octave up
    assert mel == pytest.approx(tops)


def test_clean_instrument_is_steady_and_in_tune():
    y = make("clean/organ").render(Note(60 + 1 / 3, 0.6, 2.0)).mean(1)
    seg = y[int(0.3 * SR):int(1.8 * SR)]
    w = int(0.1 * SR)
    rms = np.array([np.sqrt(np.mean(seg[i:i + w] ** 2)) for i in range(0, len(seg) - w, w)])
    assert rms.std() / rms.mean() < 0.01                               # no tremolo or drift
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), 8 * len(seg)))
    f = np.fft.rfftfreq(8 * len(seg), 1 / SR)
    m = (f > 250) & (f < 280)
    target = 440 * 2 ** ((60 + 1 / 3 - 69) / 12)
    assert abs(1200 * np.log2(f[m][np.argmax(spec[m])] / target)) < 1.0


def test_clean_master_only_scales():
    x = np.random.default_rng(0).standard_normal((1000, 2))
    y = master_clean(x, -1.0)
    assert np.allclose(y / x, (y / x)[0, 0]) and np.max(np.abs(y)) == pytest.approx(10 ** (-1 / 20))
