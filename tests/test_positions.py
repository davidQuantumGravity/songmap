"""Positions -> absolute beats (SONGMAP_SPEC §8)."""
import pytest

from songmap.arrange.timeline import Timeline
from songmap.parse.errors import SongError
from songmap.parse.positions import resolve


@pytest.fixture
def tl(make_song):
    return Timeline(make_song({"tempo": 120, "fps": 30, "sections": [
        {"name": "intro", "bars": 4}, {"name": "agents", "bars": 16}, {"name": "outro", "bars": 2}]}))


def test_bars_and_beats(tl):
    assert resolve(56, tl).beat == 224
    assert resolve("56:3", tl).beat == 226
    assert resolve("56:3.5", tl).beat == 226.5


def test_section_names_and_offsets(tl):
    assert resolve("agents", tl).beat == 16
    assert resolve("agents+8", tl).beat == 48
    assert resolve("agents+8:2", tl).beat == 49
    assert resolve("agents-1", tl).beat == 12
    assert resolve("+2:3", tl, section="outro").beat == 80 + 8 + 2


def test_frames_snap_to_16ths_and_report_error(tl):
    p = resolve("f3960", tl)                 # 132 s = beat 264 exactly
    assert p.beat == 264 and p.frame_error == 0
    p = resolve("f3961", tl)                 # 1 frame late: snaps back to the 16th
    assert p.beat == 264 and p.frame_error == -1
    p = resolve("f3962", tl)                 # nearer the next 16th (a 16th is 3.75 frames)
    assert p.beat == 264.25 and p.frame_error == 2
    assert resolve("f3962", tl, snap="none").beat == pytest.approx(264 + 2 / 30 * 2)


def test_cues(tl):
    cues = {"big": "f3960", "after": "cue:big", "loop": "cue:loop"}
    assert resolve("cue:after", tl, cues).beat == 264
    with pytest.raises(SongError, match="refers to itself"):
        resolve("cue:loop", tl, cues)
    with pytest.raises(SongError, match="did you mean 'big'"):
        resolve("cue:bgi", tl, cues)


def test_errors_suggest_fixes(tl):
    with pytest.raises(SongError, match="did you mean 'agents'"):
        resolve("agnets+8", tl)
    with pytest.raises(SongError, match="outside the bar"):
        resolve("56:5", tl)
    with pytest.raises(SongError, match="not understood"):
        resolve("56::3", tl)


def test_timeline_frames(tl):
    assert tl.beat_to_frame(4) == 60 and tl.frames == (22 * 60) + 90
    assert tl.whole_frame_beats()
    assert tl.section_at(17).name == "agents"
