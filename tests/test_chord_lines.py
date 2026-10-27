"""Every bad chord symbol is reported on the line that wrote it, in .sm (long form, `with`, dotted,
form-line edits, `set harmony...`) and in YAML (harmony default, progressions, a section's harmony)."""
import glob
import os

import pytest

from songmap.gui.project import Project, parse_text

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SM = 'song "T" 120 4/4 Am\nchords Am F C G\n'
YAML = "songmap: 0.2\ntempo: 100\nkey: C\n"
SEC = "sections:\n  - {name: a, bars: 2, parts: {bass: sub}}\n"
CHORD = "chord 'Qx' not understood; qualities:"


def _first(path, text):
    d = Project(path, text).check()["diagnostics"]
    assert d and d[0]["severity"] == "error", d
    return d[0]


@pytest.mark.parametrize("body, line, section", [
    ('verse = {chords: "C Am Qx", keys: hold}\nform:\n  verse 4\n', 3, "verse"),
    ('verse = {prog: "C:2 Qx:2", keys: hold}\nform:\n  verse 4\n', 3, "verse"),
    ('verse = {harmony: "C Qx", keys: hold}\nform:\n  verse 4\n', 3, "verse"),
    ('verse = {keys: hold}\nv2 = verse with {chords: "Qx"}\nform:\n  verse 4\n  v2 4\n', 4, "v2"),
    ('verse = {keys: hold}\nv2 = verse with {prog: "C:2 Qx:2"}\nform:\n  v2 4\n', 4, "v2"),
    ('verse = {keys: hold}\nverse.chords = "Qx"\nform:\n  verse 4\n', 4, "verse"),
    ('verse = {keys: hold}\nverse.prog = "C Qx"\nform:\n  verse 4\n', 4, "verse"),
    # a section built from another keeps the line of the harmony it inherits
    ('verse = {chords: "C Qx", keys: hold}\nv2 = verse with {pad: warm}\nform:\n  v2 4\n', 3, "v2"),
    # an edit under a form line
    ('verse = {keys: hold}\nform:\n  verse 4:\n    chords = "C Qx"\n', 6, "verse"),
])
def test_sm_section_chords_report_the_defining_line(body, line, section):
    d = _first("x.sm", SM + body)
    assert d["line"] == line and d["section"] == section
    assert d["message"].startswith(CHORD)


@pytest.mark.parametrize("body, line, prefix", [
    ("set harmony.default=[C, Qx]\nverse 4 | keys:hold\n", 3, "harmony default: "),
    ('set harmony.progressions={a: "C:2 Qx:2"}\nverse 4 | keys:hold\n', 3, "prog a: "),
    ('set harmony={default: [C, G], progressions: {a: "C:2 Qx:2"}}\nverse 4 | keys:hold\n', 3, "prog a: "),
])
def test_sm_set_harmony_reports_the_set_line(body, line, prefix):
    d = _first("x.sm", SM + body)
    assert d["line"] == line and d["message"].startswith(prefix + CHORD)


def test_sm_unknown_progression_name_reports_the_defining_line():
    d = _first("x.sm", SM + 'verse = {prog: "nope", keys: hold}\nprog nopf "C:2 G:2"\nform:\n  verse 4\n')
    assert d["line"] == 3 and d["message"] == "unknown progression 'nope'" and "nopf" in d["suggestion"]


@pytest.mark.parametrize("text, line, section, prefix", [
    (YAML + "harmony: {default: [C, Qx]}\n" + SEC, 4, None, "harmony default: "),
    (YAML + "harmony:\n  chord_bars: 1\n  default: [C, Qx]\n" + SEC, 6, None, "harmony default: "),
    (YAML + 'harmony: {default: [C], progressions: {a: "C:2 Qx:2"}}\n' + SEC, 4, None, "prog a: "),
    (YAML + 'harmony:\n  default: [C]\n  progressions:\n    b: "C:2 G:2"\n    a: "C:2 Qx:2"\n' + SEC, 8, None,
     "prog a: "),
    (YAML + "harmony: {default: [C]}\n" + SEC + '  - name: b\n    bars: 2\n    harmony: "C Qx"\n', 9, "b", ""),
    (YAML + "harmony: {default: [C]}\n" + SEC + '  - {name: b, bars: 2, harmony: "C Qx"}\n', 7, "b", ""),
])
def test_yaml_chords_report_their_line(text, line, section, prefix):
    d = _first("x.yaml", text)
    assert d["line"] == line and d["section"] == section
    assert d["message"].startswith(prefix + CHORD)


def test_good_harmony_still_parses():
    for path, text in [
        ("x.sm", SM + 'verse = {chords: "C Am F G", keys: hold}\nv2 = verse with {chords: hold}\n'
                      'v3 = verse with {prog: later}\nprog later "Am:2 Dm7:2"\nform:\n  verse 4\n  v2 4\n  v3 4\n'),
        ("x.sm", SM + 'set harmony.default=[C, G]\nverse 4 | keys:hold prog="C:2 G:2"\n'),
        ("x.yaml", YAML + 'harmony: {default: [C, G], progressions: {a: "C:2 G:2"}}\nsections:\n'
                          '  - {name: a, bars: 2, harmony: a, parts: {bass: sub}}\n  - {name: b, bars: 2, harmony: "Am F"}\n'),
    ]:
        assert Project(path, text).check()["ok"], path
    song = parse_text(SM + 'verse = {chords: "C:2 G:2", keys: hold}\nform:\n  verse 4\n', "x.sm")
    assert song.sections[0].harmony == "C:2 G:2" and type(song.sections[0].harmony) is str
    assert "chords" not in song.sections[0].parts


@pytest.mark.parametrize("path", sorted(glob.glob(os.path.join(ROOT, "songs", "**", "*.sm"), recursive=True)
                                        + glob.glob(os.path.join(ROOT, "songs", "**", "*.yaml"), recursive=True)))
def test_every_song_still_parses(path, tmp_path, monkeypatch):
    from songmap.arrange.expand import expand
    from songmap.instruments.sampler import library
    # Score expansion must also work on a fresh checkout without optional audio packs.
    monkeypatch.setattr(library, "roots", lambda: [str(tmp_path)])
    if path.endswith(".view.yaml"):
        pytest.skip("a video view, not a song")
    with open(path, encoding="utf-8") as f:
        expand(parse_text(f.read(), path))
