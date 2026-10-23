"""Error locations and suggestions: chord symbols carry their line, unknown styles list real options."""
import pytest

from songmap.gui.project import Project, parse_text
from songmap.parse.errors import SongError

HEAD = 'song "S" 100 4/4 C\n'


def _err(text, name="x.sm"):
    with pytest.raises(SongError) as e:
        parse_text(text, name)
    return e.value


@pytest.mark.parametrize("body, line, section", [
    ("chords C Am F Qx\nverse 4 | keys:hold\n", 2, None),
    ("chords C Am F G\nprog dd \"Am:2 Qz:2\"\nverse 4 | keys:hold prog=dd\n", 3, None),
    ("chords C Am F G\nverse 4 | keys:hold prog=\"Am:2 Qz:2\"\n", 3, "verse"),
    ("chords C Am F G\nverse 4 | keys:hold chords=\"Am Qz\"\n", 3, "verse"),
])
def test_bad_chord_reports_its_line(body, line, section):
    e = _err(HEAD + body)
    assert e.line == line and e.section == section
    assert "chord 'Q" in e.message and "not understood; qualities:" in e.message


def test_bad_default_chord_keeps_its_message_and_reaches_the_studio():
    e = _err(HEAD + "chords C Am F Qx\nverse 4 | keys:hold\n")
    assert e.message.startswith("harmony default: chord 'Qx' not understood; qualities: maj, m,")
    diags = Project("x.sm", HEAD + "chords C Am F Qx\nverse 4 | keys:hold\n").check()["diagnostics"]
    assert [d["line"] for d in diags] == [2]


def test_good_progressions_still_parse():
    song = parse_text(HEAD + "chords C Am F G /2\nverse 4 | keys:hold prog=later\nprog later \"Am:2 Dm7:2\"\n", "x.sm")
    assert song.harmony.default == ["C", "Am", "F", "G"] and song.harmony.chord_bars == 2
    assert song.harmony.progressions == {"later": "Am:2 Dm7:2"}


def test_yaml_bad_chord_still_reported():
    from songmap.arrange.expand import expand
    song = parse_text("tempo: 100\nkey: C\nharmony: {default: [C, Qx]}\n"
                      "sections: [{name: a, bars: 2, parts: {bass: sub}}]\n", "x.yaml")
    with pytest.raises(SongError, match="harmony default: chord 'Qx' not understood"):
        expand(song)


def test_unknown_style_lists_the_roles_styles_motifs_and_variables():
    e = _err(HEAD + "chords C Am F G\nmotif hook deg \"0 2 4\"\nsoft = hold\nverse 4 | keys:holdd\n")
    assert e.message == "'holdd' is not a style, motif or variable" and e.line == 5
    s = e.suggestion
    assert s.startswith("did you mean 'hold'?")
    assert "keys styles:" in s and "comp" in s and "pulse" in s
    assert "motifs: hook" in s and "variables: soft" in s


def test_unknown_style_of_a_styled_role_includes_the_shared_styles():
    e = _err(HEAD + "chords C Am F G\nverse 4 | bass:zzzzz\n")
    assert e.message == "unknown bass style 'zzzzz'"
    assert "bass styles:" in e.suggestion and "eighths" in e.suggestion and "hold" in e.suggestion
