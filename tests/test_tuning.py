"""The pitch grid (theory/tuning.py) and the notation reserved for 36edo (ROADMAP P10)."""
import pytest

from songmap.parse import notes as N
from songmap.parse.errors import NotationError, SongError
from songmap.theory import harmony as H
from songmap.theory import keys as K
from songmap.theory import voicing as V
from songmap.theory.tuning import DEFAULT, Tuning, centered, parse_tuning


def test_grid_and_pitch_classes():
    assert DEFAULT.step == 1 and DEFAULT.pc(64) == 4 and DEFAULT.pc(-1) == 11
    t36 = Tuning(36)
    assert t36.step == pytest.approx(1 / 3)
    assert t36.pc(60 + 1 / 3) == 1 and t36.pc(64) == 12 and t36.pc(72) == 0
    assert t36.grid(60, 61) == pytest.approx([60, 60 + 1 / 3, 60 + 2 / 3, 61])
    assert centered(10) == -2 and centered(5) == 5 and centered(6) == -6


def test_12edo_results_stay_integers():
    """Seeds and golden hashes depend on this: int in, int out."""
    assert isinstance(K.degree_to_midi(4, "D minor", 5), int) and isinstance(K.tonic_midi("A minor"), int)
    assert all(isinstance(m, int) for m in V.voice_lead(None, 0, (0, 4, 7)))


def test_voicing_runs_on_a_finer_grid():
    """Nothing in voicing assumes 12 pitch classes: a golden third (11 steps of 36) voices on the 36 grid."""
    t36 = Tuning(36)
    golden = (0, 11 / 3, 7)                      # C, vE, G
    c = V.voice_lead(None, 0, golden, 52, 76, voices=3, tuning=t36)
    assert {t36.pc(m) for m in c} == {0, 11, 21}


@pytest.mark.parametrize("text, deg", [("^c4 d", False), ("e4 vd8", False), ("v3/4 2", True), ("(^c8)", False),
                                       ("{^d}e4", False)])
def test_microtone_prefixes_are_reserved(text, deg):
    with pytest.raises(NotationError, match="reserved for sixth-step accidentals"):
        N.parse_motif(text, deg=deg)


def test_accent_suffix_still_works():
    evs = N.parse_motif("c4^ d8^ e8 f2")
    assert evs[0].art == "accent" and evs[1].art == "accent"


@pytest.mark.parametrize("fn, arg", [(H.parse_chord, "^F#m"), (H.parse_chord, "vC"), (K.parse_key, "^E minor")])
def test_prefixed_chords_and_keys_are_reserved(fn, arg):
    with pytest.raises(NotationError, match="reserved"):
        fn(arg)


def test_tuning_key(make_song):
    assert make_song({"tuning": "12edo", "sections": [{"name": "a", "bars": 1}]}).tuning == "12edo"
    assert parse_tuning("12-TET") is DEFAULT
    with pytest.raises(SongError, match="36edo arrives with ROADMAP P10"):
        make_song({"tuning": "36edo", "sections": [{"name": "a", "bars": 1}]})
