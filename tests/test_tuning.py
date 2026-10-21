"""The pitch grid (theory/tuning.py) and 36edo notation (ROADMAP P10, docs/GOLDEN_HARMONY.md)."""
import pytest

from songmap.arrange.expand import expand
from songmap.parse import notes as N
from songmap.parse.errors import NotationError, SongError
from songmap.theory import harmony as H
from songmap.theory import keys as K
from songmap.theory import voicing as V
from songmap.theory.tuning import DEFAULT, EDO36, Tuning, centered, parse_tuning, split_updown


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
    assert split_updown("c4") == (0, "c4") and isinstance(split_updown("c4")[0], int)


def test_voicing_runs_on_a_finer_grid():
    t36 = Tuning(36)
    golden = (0, 11 / 3, 22 / 3)                 # C, vE, ^G
    c = V.voice_lead(None, 0, golden, 52, 76, voices=3, tuning=t36)
    assert {t36.pc(m) for m in c} == {0, 11, 22}


@pytest.mark.parametrize("text, deg, want", [
    ("^c4 d", False, [60 + 1 / 3, 62]), ("e4 vd8", False, [64, 62 - 1 / 3]), ("v3/4 2", True, [65 - 1 / 3, 64]),
    ("(^c8)", False, [60 + 1 / 3]), ("^^c4", False, [60 + 2 / 3]), ("[c,ve,^g]4", False, [60, 64 - 1 / 3, 67 + 1 / 3])])
def test_sixth_step_prefixes(text, deg, want):
    evs = N.parse_motif(text, deg=deg)
    assert [p for e in evs for p in e.pitches] == pytest.approx(want)


def test_grace_with_prefix_and_accent_suffix():
    evs = N.parse_motif("{^d}e4 c4^ d8^ e8 f4")
    assert evs[0].pitches == pytest.approx((62 + 1 / 3,)) and "grace" in evs[0].tags
    assert evs[2].art == "accent" and evs[3].art == "accent"


@pytest.mark.parametrize("sym, root, ivs", [
    ("Cg", 0, (0, 11, 22)), ("Cg7", 0, (0, 11, 22, 33)), ("Cs", 0, (0, 10, 20)), ("CT13", 0, (0, 13, 26)),
    ("^F#m", 19, (0, 9, 21)), ("vC", 35, (0, 12, 21)), ("C(v3,^5)", 0, (0, 11, 22)), ("vEbg7", 8, (0, 11, 22, 33))])
def test_chord_symbols_36(sym, root, ivs):
    r, iv, _ = H.parse_chord(sym)
    assert round(r * 3) % 36 == root and tuple(round(i * 3) for i in iv) == ivs


def test_bad_alteration_message():
    with pytest.raises(NotationError, match="alteration"):
        H.parse_chord("C(v9)")


def test_golden_scales():
    _, g13 = K.parse_key("C golden13")
    assert [round(x * 3) for x in g13] == [0, 3, 6, 8, 11, 14, 17, 19, 22, 25, 28, 30, 33]
    _, s13 = K.parse_key("C silver13")
    assert {0, 10, 20} <= {round(x * 3) for x in s13}           # tonic silver triad C ^Eb vG
    assert K.parse_key("^D minor")[0] == pytest.approx(2 + 1 / 3)
    assert K.degree_to_midi(13, "C golden13", 4) == 72              # 13 degrees per octave


def test_passing_placeholders():
    seq = [c.symbol for c, _ in H.parse_progression("G ~ ~ C")]
    assert seq == ["G", "vEbT13/G", "vCg/G", "C"]                    # the unique strict path (V -> I)
    assert [c.symbol for c, _ in H.parse_progression("F ~g ~g G")] == ["F", "vF#g", "^F#g", "G"]
    with pytest.raises(NotationError, match="placeholder"):
        H.parse_progression("C ~x F")


def test_tuning_key_and_grid_check(make_song):
    assert make_song({"tuning": "12edo", "sections": [{"name": "a", "bars": 1}]}).tuning == "12edo"
    assert parse_tuning("12-TET") is DEFAULT and parse_tuning("36edo") is EDO36
    song = {"harmony": {"default": ["C", "Cg"], "chord_bars": 1},
            "sections": [{"name": "a", "bars": 2, "parts": {"chords": "hold"}}]}
    with pytest.raises(SongError, match="needs? `tuning: 36edo`|need `tuning: 36edo`"):
        expand(make_song(song))
    arr = expand(make_song({**song, "tuning": "36edo"}))
    assert any(abs(p * 3 - round(p * 3)) < 1e-6 and p % 1 for e in arr.parts["chords"] for p in e.pitches)
