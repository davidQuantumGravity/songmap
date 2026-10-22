"""Note language (moved from the sketch)."""
import pytest

from songmap.parse import notes as N
from songmap.parse.errors import NotationError


def test_motif_sticky_durations_and_marks():
    evs = N.parse_motif("=mf e4^ d8' c' e4_ g | a2~ g4 (e8) r", name="t")
    assert [e.dur for e in evs] == [1, 0.5, 0.5, 1, 1, 2, 1, 0.5]
    assert evs[0].art == "accent" and evs[0].vel > N.DYN["mf"]
    assert evs[1].art == "staccato" and evs[2].art == "staccato"
    assert evs[5].slur and "ghost" in evs[7].tags and evs[7].vel < 0.35
    assert evs[0].pitches == (64,)


def test_bar_check_message():
    with pytest.raises(NotationError, match="bar 1 has 3 beats"):
        N.parse_motif("c4 d e | f1")


def test_degree_mode_and_hairpin():
    evs = N.parse_motif("=p < 0 -3 0 2 | 1/2 0 =f", deg=True, key="E minor")
    assert evs[0].pitches == (64,) and evs[1].pitches == (59,)       # E4, B3
    vels = [e.vel for e in evs]
    assert vels == sorted(vels) and vels[0] == pytest.approx(N.DYN["p"])


def test_dynamics_need_equals_sign():
    with pytest.raises(NotationError, match="'=mf'"):
        N.parse_motif("mf c4")


# ---------------------------------------------------------------- rel mode (chord-relative)
def _rel(text, chord="Em", oct_=0):
    from songmap.theory.harmony import Chord
    c = Chord.parse(chord)
    evs = N.parse_motif(text, rel=True)
    root = c.home_root(64) + 12 * oct_
    return [tuple(N.rel_to_midi(t, o, c.intervals, root) for t, o in e.rel) for e in evs], evs


def test_rel_octave_bounce_like_synth_v0():
    pitches, evs = _rel("R8 R+ R R+ R R+ R R+", "C", -2)
    assert [p[0] for p in pitches] == [36, 48] * 4 and all(e.dur == 0.5 for e in evs)


def test_rel_degrees_follow_the_chord():
    assert _rel("[R,3,5]1", "Em")[0] == [(64, 67, 71)]          # minor third from the chord
    assert _rel("[R,3,5]1", "E")[0] == [(64, 68, 71)]           # major third
    assert _rel("7", "Em7")[0] == [(74,)] and _rel("7", "Emaj7")[0] == [(75,)]
    assert _rel("7", "Em")[0] == [(74,)] and _rel("b7", "E")[0] == [(74,)]
    assert _rel("9 #11 5- R+")[0] == [(78,), (82,), (59,), (76,)]
    assert _rel("9", "Em9")[0] == [(78,)] and _rel("9", "Cm")[0] == [(74,)]


def test_rel_durations_and_ambiguity():
    _, evs = _rel("R4 5/8 5 3+8 r8 R2")
    assert [e.dur for e in evs] == [1, 0.5, 0.5, 0.5, 2]
    with pytest.raises(NotationError, match="slash"):
        N.parse_motif("516", rel=True)
    with pytest.raises(NotationError, match="out of range"):
        N.parse_motif("58", rel=True)


def test_trailing_rests_count_in_the_written_length():
    evs = N.parse_motif("c1 | r1 | r1 | r1", name="t")
    assert len(evs) == 1 and N.motif_length(evs) == 16


def test_a_phrase_ending_in_rests_loops_at_its_written_length(make_song):
    from songmap.arrange.expand import expand
    s = make_song({"sections": [{"name": "a", "bars": 8, "parts": {"keys": {"notes": "c1 | r1 | r1 | r1"}}}]})
    assert [e.beat for e in expand(s).parts["keys"]] == [0, 16]
