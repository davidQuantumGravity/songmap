"""Clips and the note writer: layers (&), long durations (*N), explicit velocity, and exact baking."""
from songmap.arrange.expand import expand
from songmap.gui.clips import _sec, bake, section_clip, set_section_part
from songmap.gui.project import parse_text
from songmap.parse.clip import ClipNote, q, spell, write_notes
from songmap.parse.notes import parse_duration, parse_motif


def test_layers_and_multiplied_durations():
    evs = parse_motif("c1*2 & e4 f g a | b1")
    assert [(e.beat, e.dur, e.pitches[0]) for e in evs][:3] == [(0, 8, 60), (0, 1, 64), (1, 1, 65)]
    assert evs.length == 8
    assert parse_duration("1*3") == 12 and parse_duration("8.*2") == 1.5


def test_spelling_covers_sixth_steps_and_octaves():
    assert [spell(p) for p in (60, 61, 48, 72, 60 + 1 / 3, 71 + 2 / 3, 35)] == \
        ["c", "c#", "c-", "c+", "^c", "vc+", "b---"]


def test_writer_round_trips_chords_overlaps_and_rests():
    clip = [ClipNote(0, 4, (48.0,), .5), ClipNote(0, 1, (64.0, 67.0), .7, "staccato"), ClipNote(1.5, .5, (65 + 1 / 3,), .9),
            ClipNote(2, 1 / 3, (62.0,), .4), ClipNote(6, 6, (55.0,), .6, slur=True)]
    text = write_notes(clip, bars=3, beats_per_bar=4)
    back = parse_motif(text)
    got = sorted((q(e.beat), q(e.dur), e.pitches, round(e.vel * 127), e.art, e.slur) for e in back)
    want = sorted((q(n.beat), q(n.dur), tuple(sorted(n.pitches)), round(n.vel * 127), n.art, n.slur) for n in clip)
    assert got == want and back.length == 12
    assert "&" in text                        # the held bass note is its own layer


SONG = """song "Bake" 100 4/4 G fps=30 seed=5 tail=1 tuning=36edo
chords G Em C D
motif hook deg oct=5 "=mf 0/8 2 4 2 {3}4/4 2/8 0 | ^2/2 0/4 r"
verse 4 | keys:comp bass:sub lead:hook dyn=p<f   # the verse
"""


def test_bake_is_exact_and_explicit_velocity_ignores_section_dynamics():
    arr = expand(parse_text(SONG, "b.sm"))
    sec = arr.timeline.sections[0]

    def evs(a, part):
        s = _sec(a, 0)
        return sorted((float(q(e.beat - s.start)), tuple(round(p, 3) for p in e.pitches), round(e.vel * 127),
                       float(q(e.dur)), e.art, e.slur) for e in a.parts[part] if s.start <= e.beat < s.end)
    for part in ("keys", "lead", "bass"):
        new = bake(SONG, arr, sec.index, part)
        assert f'{part}="' in new and "# the verse" in new
        arr2 = expand(parse_text(new, "b.sm"))
        assert evs(arr2, part) == evs(arr, part), part
        assert section_clip(arr2, 0, part)["written"]


def test_set_section_part_adds_replaces_and_refuses_other_lines():
    line = SONG.splitlines().index(next(ln for ln in SONG.splitlines() if ln.startswith("verse"))) + 1
    out = set_section_part(SONG, line, "pad", '"c1"')
    assert 'lead:hook dyn=p<f pad="c1"   # the verse' in out
    out = set_section_part(out, line, "lead", '"g4 a b c+"')
    assert 'lead="g4 a b c+"' in out and "lead:hook" not in out
    try:
        set_section_part(SONG, 1, "lead", '"c"')
        raise AssertionError("expected a refusal")
    except ValueError:
        pass


def test_step_lanes_replace_one_lane_of_the_style():
    from songmap.gui.clips import section_hits, set_steps
    song = 'song "S" 100 4/4 C fps=30 seed=1 tail=1\nchords C\nverse 1 | drums:four_floor\n'
    arr = expand(parse_text(song, "s.sm"))
    h = section_hits(arr, 0, "drums", song)
    assert [b for b, _ in h["pieces"]["kick"]] == [0, 1, 2, 3] and h["written"] == []
    new = set_steps(song, arr, 0, "kick", "X.x.x.x.x.x.x.x.")
    h2 = section_hits(expand(parse_text(new, "s.sm")), 0, "drums", new)
    assert len(h2["pieces"]["kick"]) == 8 and h2["pieces"]["hat"] == h["pieces"]["hat"] and h2["written"] == ["kick"]
