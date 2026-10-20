import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))


def song_from(raw: dict):
    """Build a Song from a v0.2 mapping (tests write songs inline)."""
    from songmap.parse import yaml_form
    return yaml_form.from_raw({"songmap": 0.2, **raw}, file="test.yaml")


@pytest.fixture
def make_song():
    return song_from
