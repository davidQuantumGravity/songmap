"""Motif transforms, written lengths with trailing rests, and tempo ramps (rit/accel)."""
import math

import pytest

from songmap.arrange.expand import expand
from songmap.arrange.timeline import Timeline
from songmap.parse import lang
from songmap.parse.errors import SongError
from songmap.parse.notes import motif_length, parse_motif
from songmap.theory import transforms

HEAD = ('song "T" 120 4/4 Am fps=30 seed=1 tail=1\nchords Am F\nmotif m deg oct=5 "0/4 2 4 2 | 4/2 r/2"\n'
        'tune = {deg: "0/4 2 4 2 | 4/2 r/2", oct: 1}\n')


def lead(body):
    a = expand(lang.loads(HEAD + body, "t.sm"))
    return [(e.beat, e.pitches[0]) for e in a.parts["lead"]]


def test_trailing_rests_count_in_a_motifs_length():
    evs = parse_motif("0/4 2 4 2 | r/1", deg=True, key="A minor")
    assert motif_length(evs) == 8
    # so a call-and-response line loops every 2 bars, not every bar
    assert [b for b, _ in lead('x 4 | lead:{deg: "0/4 2 4 2 | r/1", oct: 1}')] == [0, 1, 2, 3, 8, 9, 10, 11]


@pytest.mark.parametrize("body, want", [
    ("x 2 | lead:m", [(0, 81), (1, 84), (2, 88), (3, 84), (4, 88)]),
    ("x 2 | lead:m:t+2", [(0, 84), (1, 88), (2, 91), (3, 88), (4, 91)]),          # degrees in A minor
    ("x 2 | lead:m:t-1", [(0, 79), (1, 83), (2, 86), (3, 83), (4, 86)]),
    ("x 2 | lead:m:oct-1", [(0, 69), (1, 72), (2, 76), (3, 72), (4, 76)]),
    ("x 2 | lead:m:inv", [(0, 81), (1, 77), (2, 74), (3, 77), (4, 74)]),          # mirrored by degrees
    ("x 2 | lead:m:rev", [(2, 88), (4, 84), (5, 88), (6, 84), (7, 81)]),          # the trailing rest leads
    ("x 4 | lead:m:aug", [(0, 81), (2, 84), (4, 88), (6, 84), (8, 88)]),
    ("x 1 | lead:m:frag=1", [(0, 81), (1, 84), (2, 88), (3, 84)]),
    ("x 4 | lead:m:x2", [(0, 81), (1, 84), (2, 88), (3, 84), (4, 88), (8, 81), (9, 84), (10, 88), (11, 84), (12, 88)]),
    ("x 4 | lead:tune:aug:t+1", [(0, 83), (2, 86), (4, 89), (6, 86), (8, 89)]),  # a melody variable, chained
])
def test_transforms(body, want):
    assert lead(body) == want


def test_canon_thin_and_dyn():
    canon = lead("x 2 | lead:m:canon=2@4")
    assert (0.0, 81) in canon and (1.0, 81) in canon and len(canon) == 10
    assert len(lead("x 2 | lead:m:thin=0.5")) == 2
    a = expand(lang.loads(HEAD + 'x 2 | lead:{motifs: ["m:dyn=pp"]}', "t.sm"))
    assert {round(e.vel, 2) for e in a.parts["lead"]} == {0.25}


def test_transform_errors():
    with pytest.raises(SongError, match="not a transform or an option"):
        lang.loads(HEAD + "x 2 | lead:m:wobble", "t.sm")
    with pytest.raises(SongError, match="frag=3: the motif has 2 bars"):
        expand(lang.loads(HEAD + "x 2 | lead:m:frag=3", "t.sm"))
    with pytest.raises(Exception, match="rel"):
        transforms.apply(parse_motif("R/4 3 5 3", rel=True), "t+1", key="C major", deg=False)


def test_tempo_ramps_integrate_exactly():
    s = lang.loads('song "T" 120 4/4 Am fps=30 seed=1 tail=0\nchords Am\na 4 | pad:warm\n'
                   'b 2 | pad:warm tempo="rit 120>60"\nc 2 | pad:warm tempo=90\n', "t.sm")
    tl = Timeline(s)
    ramp = tl.beat_to_sec(24) - tl.beat_to_sec(16)
    assert ramp == pytest.approx(60 * 8 / (60 - 120) * math.log(60 / 120))
    assert tl.bpm_at(20) == pytest.approx(90)
    for b in (0, 3.5, 17, 23.9, 30):
        assert tl.sec_to_beat(tl.beat_to_sec(b)) == pytest.approx(b)
    assert not tl.whole_frame_beats()
    with pytest.raises(SongError, match="rit goes down"):
        Timeline(lang.loads('song "T" 120 4/4 Am\na 2 | pad:warm tempo="rit 90>120"\n', "t.sm"))
