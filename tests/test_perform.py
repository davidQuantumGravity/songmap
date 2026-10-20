"""Performance layer (moved from the sketch)."""
import numpy as np
import pytest

from songmap.parse import notes as N
from songmap.perform import pipeline as P


def test_swing_moves_offbeats_only():
    assert P.swing_beat(0.5, 0.66) == pytest.approx(0.66)
    assert P.swing_beat(1.0, 0.66) == 1.0


def test_perform_is_seeded_and_shaped():
    evs = N.parse_motif("c8 c c c c c c c | c c c c c c c c")
    feel = P.Feel(time_ms=5, vel_sd=0.03, seed=3)
    a = P.perform(evs, start_beat=0, spb=0.5, feel=feel, section_shape="p<f")
    b = P.perform(evs, start_beat=0, spb=0.5, feel=feel, section_shape="p<f")
    assert [x.time for x in a] == [x.time for x in b]
    assert np.mean([x.note.vel for x in a[-4:]]) > np.mean([x.note.vel for x in a[:4]]) * 1.5
