"""songmap.visual: 36-ET spelling, the score read from an arrangement, and frames that render."""
import pytest

from songmap.arrange.expand import expand
from songmap.theory.passing import name36
from songmap.visual import score_of, spell
from songmap.visual.draw import Renderer


def test_spelling_matches_the_passing_engine_names():
    for st in range(3 * 36, 3 * 84):
        sp = spell(st / 3)
        assert sp.name.replace("♯", "#").replace("♭", "b") == name36(st)
        assert sp.layer == st % 3


@pytest.mark.parametrize("pitch, text, diatonic", [(60, "C4", 28), (60 + 1 / 3, "^C4", 28), (60 + 2 / 3, "vC♯4", 28),
                                                   (71 + 2 / 3, "vC5", 35), (59 + 2 / 3, "vC4", 28), (63, "E♭4", 30)])
def test_spelled_text_and_staff_position(pitch, text, diatonic):
    sp = spell(pitch)
    assert sp.text == text and sp.diatonic == diatonic


def _song(make_song, harmony, parts, bars):
    return make_song({"tuning": "36edo", "instruments": {"chords": "clean/organ"},
                      "sections": [{"name": "a", "bars": bars, "harmony": harmony, "parts": parts}]})


def test_score_follows_the_arrangement(make_song):
    arr = expand(_song(make_song, "G:1 ~:0.5 ~:0.5 C:2", {"chords": "hold"}, 4))
    sc = score_of(arr)
    assert sc.edo == 36
    assert [c.symbol for c in sc.chords] == ["G", "vEbT13/G", "vCg/G", "C"]
    spb = arr.timeline.beat_to_sec(1)
    t = sc.chords[2].start + 0.1                       # inside vCg/G
    assert sorted(round(n.pitch * 3) for n in sc.sounding(t)) == sorted(round(p * 3) for p in arr.parts["chords"][2].pitches)
    assert abs(sc.chords[1].start - 4 * spb) < 1e-9
    assert len(sc.bars) == 5 and sc.bar_at(t) == 1             # 3.1 s is in the second bar (2-4 s)


def test_frames_render_light_and_dark(make_song):
    sc = score_of(expand(_song(make_song, "F:1 ~g:0.5 ~g:0.5 G:2", {"chords": "hold", "melody": "top"}, 4)))
    for theme in ("light", "dark"):
        r = Renderer(sc, (640, 360), theme)
        for t in (0.0, sc.chords[1].start + 0.01, sc.seconds - 0.01):
            im = r.frame(t)
            assert im.size == (640, 360)
