"""Per-section meters (`meter=7/8`, `meter="7/8 2+2+3"`) and the named golden modes (`key="C golden7_51"`)."""
import pytest

from songmap.arrange.expand import expand
from songmap.arrange.timeline import Timeline
from songmap.export import cues as cues_mod
from songmap.parse import fmt, lang
from songmap.parse.errors import SongError
from songmap.parse.positions import resolve
from songmap.parse.yaml_form import parse_meter
from songmap.perform.pipeline import metric_weight
from songmap.theory.keys import MODES, degree_to_midi

HEAD = 'song "Meters" 120 4/4 C\n'


def song(src):
    return lang.loads(HEAD + src, "meters.sm")


def test_parse_meter_forms_and_errors():
    assert parse_meter("7/8") == (7, 8)
    assert parse_meter("7/8 2+2+3") == (7, 8, (2, 2, 3))
    assert parse_meter("13/16(3+3+3+2+2)") == (13, 16, (3, 3, 3, 2, 2))
    with pytest.raises(SongError, match="add up to 4, not 7"):
        parse_meter("7/8 2+2")
    with pytest.raises(SongError, match="not understood"):
        parse_meter("7/9")


def test_sections_take_their_own_bar_length():
    s = song('a 2 | bass="c1 | c1"\n'
             'b 4 | bass="c4. c4. c8 | c4. c4. c8" meter=7/8\n'
             'c 2 | bass="c4 c c c c | c4 c c c c" meter=5/4\n')
    tl = Timeline(s)
    assert [(x.start, x.end, x.bpb) for x in tl.sections] == [(0, 8, 4), (8, 22, 3.5), (22, 32, 5)]
    assert tl.total_beats == 32 and tl.total_bars == 8
    assert tl.seconds == pytest.approx(32 * 0.5 + s.tail_seconds)
    # bars <-> beats, piecewise
    assert [tl.bar_to_beat(b) for b in (0, 2, 3, 6, 7, 8, 9)] == [0, 8, 11.5, 22, 27, 32, 37]
    assert tl.beat_to_bar(11.5) == 3 and tl.beat_to_bar(27) == 7
    assert tl.bar_start(13) == 11.5 and tl.beat_in_bar(13) == 1.5 and tl.bpb_at(13) == 3.5
    assert tl.bars_after(22, -1) == 18.5                   # the bar before c is a 7/8 bar
    arr = expand(s)
    assert [e.beat for e in arr.parts["bass"] if e.section == "b"][:4] == [8, 9.5, 11, 11.5]


def test_bar_sums_follow_the_section_meter():
    with pytest.raises(SongError, match="has 4 beats, expected 3.5"):
        expand(song('a 2 | lead:{deg: "0/4 1 2 3 | 0/4 1 2 3"} meter=7/8\n'))


def test_step_grids_and_progressions_use_the_section_bar():
    s = song('a 1 | drums:{kick: "X...X...X...X..."}\n'
             'b 2 | drums:{kick: "X...X.....X..."} chords="Fm:1 C:1" meter="7/8 2+2+3"\n'
             'c 1 | like=b meter=5/4 drums:{kick: "X...X...X...X...X..."}\n')
    arr = expand(s)
    kicks = [e.beat for e in arr.parts["drums"]]
    assert kicks == [0, 1, 2, 3, 4, 5, 6.5, 7.5, 8.5, 10, 11, 12, 13, 14, 15]
    assert [(round(sp.start, 6), sp.chord.symbol) for sp in arr.harmony.spans if sp.chord][:3] == [
        (4, "Fm"), (7.5, "C"), (11, "Fm")]
    assert Timeline(s).sections[1].groups == (1.0, 1.0, 1.5)


def test_positions_and_event_lengths_cross_meters():
    s = song('a 2 | pad:warm chords="C:1"\n'
             'b 2 | like=a meter=7/8 | !riser:2 !impact@+1:2\n'
             'c 1 | like=a meter=5/4 | !drop:1@-1 !impact@+0:5\n')
    tl = Timeline(s)
    assert resolve("+1:2", tl, section="b").beat == 8 + 3.5 + 1
    assert resolve("+0:5", tl, section="c").beat == 15 + 4
    with pytest.raises(SongError, match="outside the bar"):
        resolve("+0:5", tl, section="b")
    assert resolve("3", tl).beat == 11.5 and resolve("c-1", tl).beat == 11.5
    arr = expand(s)
    riser = next(e for e in arr.events if e.type == "riser")
    assert (riser.start, riser.beat) == (0, 8)                       # two 4/4 bars before b
    drop = next(e for e in arr.events if e.type == "drop")
    assert drop.beat == 11.5                                         # one 7/8 bar before c
    assert not [e for e in arr.parts["pad"] if 11.5 <= e.beat < 15]


def test_metric_groups_accent_group_starts():
    g = (1.0, 1.0, 1.5)                                              # 7/8 2+2+3
    assert metric_weight(0, 3.5, g) == 1.08
    assert metric_weight(1, 3.5, g) == metric_weight(2, 3.5, g) == 1.04
    assert metric_weight(3, 3.5, g) < 1.0 and metric_weight(1.25, 3.5, g) == 0.91
    assert metric_weight(2, 4) == 1.04 and metric_weight(1, 4) == 1.0   # 4/4 unchanged


def test_meter_round_trips_and_shows_in_cues():
    s = song('a 2 | pad:warm chords="C:1"\nb 3 | like=a meter="7/8 3+2+2"\nc 1 | like=b\n')
    printed = fmt.to_sm(s)
    assert 'meter="7/8 3+2+2"' in printed
    back = lang.loads(printed, "printed.sm")
    assert fmt.song_to_raw(back) == fmt.song_to_raw(s)
    assert back.sections[2].meter == (7, 8, (3, 2, 2))               # like= keeps the meter
    c = cues_mod.build(expand(s))
    assert cues_mod.validate(c) == []
    assert [x["beats_per_bar"] for x in c["sections"]] == [4, 3.5, 3.5]
    assert c["grid"]["bar_frames"] == [0, 60, 120, 172, 225, 278, 330]   # 52.5 frames per 7/8 bar, rounded


def test_unknown_meter_setting_is_an_error_with_a_fix():
    with pytest.raises(SongError) as e:
        song('a 2 | pad:warm meter="7/8 2+3"\n')
    assert "add up to 5, not 7" in str(e.value) and "2+2+3" in str(e.value)


def test_golden_mode_names():
    assert MODES["golden7_33"] == MODES["golden7"] and MODES["golden10_45"] == MODES["golden10"]
    sixth = lambda m: [round(x * 3) for x in MODES[m]]                # noqa: E731
    assert sixth("golden7_60") == [0, 8, 11, 19, 22, 30, 33]           # ch36: steps 8 3 8 3 8 3 3
    assert sixth("golden7_06") == [0, 3, 6, 14, 17, 25, 28]           # steps 3 3 8 3 8 3 8
    assert sixth("golden10_36") == [0, 3, 6, 11, 14, 17, 22, 25, 28, 33]   # the "35" decatonic
    assert sixth("golden10_63") == [0, 3, 8, 11, 14, 19, 22, 25, 30, 33]   # the "53" decatonic
    assert sixth("golden_penta") == [0, 6, 14, 22, 28]                # C D vF ^G ^A
    assert degree_to_midi(1, "C golden7_51") == pytest.approx(60 + 8 / 3)     # vEb
    assert degree_to_midi(2, "^C golden7_51") == pytest.approx(60 + 12 / 3)   # ^C + 11 sixth-steps = E
    assert [degree_to_midi(d, "C phrygian_dominant") - 60 for d in range(7)] == [0, 1, 4, 5, 7, 8, 10]
