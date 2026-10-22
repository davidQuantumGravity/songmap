"""YAML song maps: parsing, inheritance, errors, v0.1 migration."""
import os

import pytest

from songmap.arrange.expand import expand
from songmap.parse import yaml_form
from songmap.parse.errors import SongError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V01 = os.path.join(ROOT, "examples", "v0.1_yaml")


def test_v01_durations_become_explicit():
    assert yaml_form.explicit_durations("4/4. 3/8 2 4 | 7/2 6 4", "deg") == "4/4. 3/8 2/4 4 | 7/2 6/4 4"
    assert yaml_form.explicit_durations("e8 d c4 =f g", "letter") == "e8 d4 c4 =f g"
    assert yaml_form.explicit_durations("R8 R R+2 5", "rel") == "R8 R/4 R+2 5/4"


def test_v01_loads_with_warning_and_equals_its_migration(tmp_path):
    path = os.path.join(V01, "week_oct13_bench.songmap.yaml")
    old = yaml_form.load(path)
    assert any("v0.1" in w for w in old.warnings)
    assert old.master.mode == "legacy"
    raw, notes = yaml_form.migrate(yaml_form.load_raw(path))
    assert raw["songmap"] == 0.2 and any("durations" in n for n in notes)
    out = tmp_path / "bench.yaml"
    out.write_text(yaml_form.dump(raw, yaml_form.leading_comments(path)), encoding="utf-8")
    new = yaml_form.load(str(out))
    assert not any("v0.1" in w for w in new.warnings)
    assert expand(new).digest() == expand(old).digest()


def test_part_forms(make_song):
    s = make_song({"motifs": {"m1": {"deg": "0 1 2 3"}}, "sections": [
        {"name": "a", "bars": 1, "parts": {"drums": "full+fill+hats16", "lead": "m1", "pad": [],
                                           "bass": {"style": "eighths", "gain_db": -3},
                                           "keys": {"notes": "=p c4 d e f"}}}]})
    p = s.sections[0].parts
    assert (p["drums"].style, p["drums"].mods) == ("full", ["fill", "hats16"])
    assert p["lead"].motifs == ["m1"] and p["bass"].opts == {"gain_db": -3}
    assert p["keys"].notes == "=p c4 d e f" and p["keys"].notes_mode == "letter"


def test_like_add_drop(make_song):
    s = make_song({"sections": [
        {"name": "a", "bars": 2, "dyn": "mf", "parts": {"drums": "full", "bass": "eighths", "pad": "warm"}},
        {"name": "b", "bars": 2, "like": "a", "add": {"arp": "up", "drums": "half"}, "drop": ["pad"]}]})
    b = s.sections[1]
    assert sorted(b.parts) == ["arp", "bass", "drums"] and b.parts["drums"].style == "half" and b.dyn == "mf"


def test_drum_lanes_in_a_part_mapping(make_song):
    s = make_song({"sections": [{"name": "a", "bars": 1, "parts": {"drums": {"kick": "X...x...", "hat": "x-x-x-x-"}}}]})
    assert s.sections[0].parts["drums"].steps == {"kick": "X...x...", "hat": "x-x-x-x-"}
    arr = expand(s)
    assert [e.beat for e in arr.parts["drums"] if e.piece == "kick"] == [0, 2]


@pytest.mark.parametrize("raw, msg", [
    ({"tempo": 120, "sectoins": []}, "did you mean 'sections'"),
    ({"sections": [{"name": "a", "bars": 1, "parst": {}}]}, "did you mean 'parts'"),
    ({"sections": [{"name": "a", "bars": 1}, {"name": "a", "bars": 1}]}, "duplicate section"),
    ({"sections": [{"name": "a", "bars": 1, "like": "zz"}]}, "not an earlier section"),
    ({"master": "loud", "sections": [{"name": "a", "bars": 1}]}, "master 'loud' unknown"),
    ({"key": "H minor", "sections": [{"name": "a", "bars": 1}]}, "not understood"),
])
def test_errors_name_the_problem(make_song, raw, msg):
    with pytest.raises(SongError, match=msg):
        make_song(raw)


@pytest.mark.parametrize("parts, msg", [
    ({"bass": "eigths"}, "did you mean 'eighths'"),
    ({"drums": "full+fil"}, "did you mean 'fill'"),
    ({"lead": ["m9"]}, "unknown motif 'm9'"),
    ({"lead": ["m1:wobble"]}, "unknown transform .wobble."),
    ({"zither": "warm"}, "no styles for role"),
])
def test_expand_errors_carry_section_and_suggestion(make_song, parts, msg):
    s = make_song({"motifs": {"m1": {"deg": "0 1 2 3"}}, "sections": [{"name": "sec", "bars": 2, "parts": parts}]})
    with pytest.raises(SongError, match=msg) as e:
        expand(s)
    assert "sec" in str(e.value)


def test_line_numbers_in_errors(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("songmap: 0.2\nsections:\n  - {name: a, bars: 1}\n  - {name: b, bars: 1, partz: {}}\n", encoding="utf-8")
    with pytest.raises(SongError, match=r"bad.yaml:4 b: unknown section key 'partz'"):
        yaml_form.load(str(p))


def test_x_keys_hold_shared_anchors(tmp_path):
    p = tmp_path / "anchors.yaml"
    p.write_text("songmap: 0.2\nx-arp:\n  up: &up {style: up, order: [0, 2, 1]}\n"
                 "sections:\n  - {name: a, bars: 1, parts: {arp: *up}}\n", encoding="utf-8")
    s = yaml_form.load(str(p))
    assert s.sections[0].parts["arp"].opts["order"] == [0, 2, 1]
