"""Chord symbols, keys, progressions and the harmony timeline."""
import pytest

from songmap.theory import harmony as H
from songmap.theory import keys as K


def test_chords_and_keys():
    assert H.parse_chord("F#m7/C#") == (6, (0, 3, 7, 10), 1)
    assert H.parse_chord("Bbmaj7")[0] == 10
    assert K.parse_key("D dorian") == (2, K.MODES["dorian"])


# ---------------------------------------------------------------- progressions and the harmony timeline
from songmap.theory.keys import tonic_midi  # noqa: E402


def test_home_register_matches_synth_v0():
    # synth_v0 wrote its chords as (root midi, tones): Dm Bb F C from D4, Em C G D from E4, Am F C G from A3
    for key, chords, roots in [("D minor", "Dm Bb F C", (62, 58, 65, 60)), ("E minor", "Em C G D", (64, 60, 67, 62)),
                               ("A minor", "Am F C G", (57, 53, 60, 55))]:
        t = tonic_midi(key)
        assert tuple(H.Chord.parse(c).home_root(t) for c in chords.split()) == roots
    assert H.Chord.parse("Bb").tones(tonic_midi("D minor")) == (58, 62, 65)


def test_parse_progression():
    prog = H.parse_progression("Em:2 C:1 | Am7:1 B7:0.5 N.C.", bpb=4)
    assert [(c.symbol if c else None, b) for c, b in prog] == [("Em", 8), ("C", 4), ("Am7", 4), ("B7", 2), (None, 4)]
    assert [b for _, b in H.parse_progression(["Dm", "Bb"], 4, chord_bars=2)] == [8, 8]
    with pytest.raises(H.NotationError, match="chord:bars"):
        H.parse_progression("Em:x")


def test_timeline_loops_default_and_keeps_chords_across_sections():
    default = H.parse_progression(["Dm", "Bb", "F", "C"], 4, chord_bars=2)
    # sections at bars 0-7 and 7-13: the Dm chord block at bars 6-8 spans the boundary
    tl = H.build_harmony(default, [(0, 28, None), (28, 52, None)], 52, 62)
    assert tl.chord_at(29).symbol == "C" and tl.chord_at(32).symbol == "Dm"
    onsets = [s.start for s in tl.changes(28, 52)]
    assert onsets == [32, 40, 48]            # no new onset at the section boundary (beat 28)


def test_section_progression_replaces_its_span():
    default = H.parse_progression(["Em", "C"], 4, chord_bars=1)
    verse = H.parse_progression("Am:1 D:1", 4)
    tl = H.build_harmony(default, [(0, 8, None), (8, 16, verse), (16, 24, None)], 24, 64)
    assert [tl.chord_at(b).symbol for b in (0, 4, 8, 12, 16, 20)] == ["Em", "C", "Am", "D", "Em", "C"]
    assert [s.start for s in tl.changes(0, 24)] == [0, 4, 8, 12, 16, 20]
