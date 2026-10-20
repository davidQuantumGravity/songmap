"""Drum step strings (moved from the sketch)."""
import pytest

from songmap.parse import steps as S


def test_steps():
    evs, bars = S.parse_steps("X...x...x...x..o|f.r.")
    assert bars == 2 and evs[0].vel == 1.0 and evs[-1].beat == pytest.approx(6.5)
    assert "ghost" in evs[4].tags
