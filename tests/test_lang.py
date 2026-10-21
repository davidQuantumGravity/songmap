"""The SongMap language (docs/LANGUAGE.md, songmap/parse/lang.py): the Swarm rewrite, loops, conditions, errors."""
import os
import re

import pytest

from songmap.arrange.expand import expand
from songmap.parse import lang, yaml_form
from songmap.parse.errors import SongError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWARM_SML = os.path.join(ROOT, "examples", "lang", "week_oct13_swarm.sml")
SWARM_YAML = os.path.join(ROOT, "examples", "v0.2_yaml", "week_oct13_swarm.songmap.yaml")
DOC = os.path.join(ROOT, "docs", "LANGUAGE.md")
HEAD = 'song "Test" 120 4/4 Am\nchords Am F C G\nmotif a deg "0 2 4 2"\nmotif b deg "4 2 0/2"\n'


def raw(src):
    return lang.compile_raw(HEAD + src, "song.sml")


def arr(src):
    return expand(lang.loads(HEAD + src, "song.sml"))


def secs(src):
    return [(s["name"], s["bars"]) for s in raw(src)["sections"]]


def hits(a, piece):
    return [e.beat for e in a.parts.get("drums", []) if e.piece == piece]


def doc_blocks():
    with open(DOC, encoding="utf-8") as f:
        return re.findall(r"```\n(.*?)```", f.read(), re.S)


# ----------------------------------------------------------------------------
# The Swarm: the rewrite is the YAML port, note for note
# ----------------------------------------------------------------------------
def test_swarm_rewrite_matches_the_yaml_port():
    a, b = expand(lang.load(SWARM_SML)), expand(yaml_form.load(SWARM_YAML))
    assert a.digest() == b.digest()
    assert a.counts() == b.counts()
    assert a.timeline.frames == b.timeline.frames == 3690
    assert [(s.name, s.bars) for s in a.song.sections] == [(s.name, s.bars) for s in b.song.sections]
    assert [(e.type, e.at, e.params) for e in a.song.events] == [(e.type, e.at, e.params) for e in b.song.events]
    for k in ("title", "tempo", "meter", "fps", "seed", "tail_seconds", "mood", "video", "instruments", "master"):
        assert getattr(a.song, k) == getattr(b.song, k), k


def test_swarm_rewrite_in_the_doc_is_the_example_file():
    with open(SWARM_SML, encoding="utf-8") as f:
        assert f.read() in doc_blocks()


def test_swarm_rewrite_is_smaller():
    def code(path):
        with open(path, encoding="utf-8") as f:
            return sum(len(ln.split(" #")[0].rstrip()) + 1 for ln in f
                       if ln.strip() and not ln.lstrip().startswith("#"))
    assert code(SWARM_SML) < 0.65 * code(SWARM_YAML)


def test_cli_checks_and_loads_sml(capsys):
    from songmap.cli import main
    assert main(["check", SWARM_SML]) == 0
    out = capsys.readouterr().out
    assert "60 bars" in out and "3690 frames" in out and "fe4ba61f" in out


def test_doc_examples_compile():
    first = doc_blocks()[0]
    a = expand(lang.loads(first, "doc.sml"))
    assert [s.name for s in a.song.sections] == ["verse", "verse_2", "chorus", "chorus_2", "chorus_3", "outro"]
    assert [s.bars for s in a.song.sections] == [8, 8, 4, 8, 12, 4]
    assert a.timeline.total_bars == 44


# ----------------------------------------------------------------------------
# definitions and composition
# ----------------------------------------------------------------------------
def test_with_copies_and_none_removes():
    r = raw("v = {drums: full, bass: sub, pad: warm}\nc = v with {pad: none, lead: [a, b]}\nv.bass = eighths\n"
            "form:\n  v 4\n  c 4\n")
    v, c = (s["parts"] for s in r["sections"])
    assert v == {"drums": "full", "bass": "eighths", "pad": "warm"}
    assert c == {"drums": "full", "bass": "sub", "lead": ["a", "b"]}     # c copied v before the edit


def test_plus_layers_mods_and_lanes():
    r = raw('v = {drums: full + fill + {kick: "......x.......x."}}\n'
            'v.drums.hat = "x.x."\nv.drums.snare += "..x."\nv.drums -= fill\nform:\n  v 1\n')
    d = r["sections"][0]["parts"]["drums"]
    assert d["style"] == "full"
    assert d["steps"]["kick"] == "x...x.x.x...x.x."            # style kick x...x...x...x... layered
    assert d["steps"]["hat"] == "x.x."
    assert d["steps"]["snare"] == "....x...x...x..."            # style snare layered with ..x. on a 16 grid


def test_lane_maps_layer_and_style_options():
    r = raw('a1 = {kick: "x..."}\na2 = {kick: "..x.", hat: "xxxx"}\nv = {drums: a1 + a2, arp: up(order=[0, 2, 1])}\n'
            'form:\n  v 1\n')
    p = r["sections"][0]["parts"]
    assert p["drums"] == {"steps": {"kick": "x.x.", "hat": "xxxx"}}
    assert p["arp"] == {"style": "up", "order": [0, 2, 1]}


def test_step_string_operators():
    assert lang.euclid(3, 8) == "x..x..x."
    assert lang.euclid(5, 8) == "x.xx.xx."
    assert lang.euclid(3, 8, 1) == ".x..x..x"
    assert lang.rotate("x..x|xx..", -1) == "..xx|x..x"
    assert lang.reverse("x..x....") == "....x..x"
    assert lang.overlay("x...|..x.", "--x.") == "x-x.|--x."
    assert lang.overlay("x...", "o.o.o.o.") == "x.o.o.o."
    r = raw('s = "x..." + "..x."\nt = "x." * 4 | rot(euclid(3, 8), 2)\nu = "x..." & ".X.."\n'
            'v = {drums: {kick: s, hat: t, snare: u}}\nform:\n  v 1\n')
    assert r["sections"][0]["parts"]["drums"]["steps"] == {"kick": "x.....x.", "hat": "x.x.x.x.|x.x..x..",
                                                           "snare": "xX.."}


def test_functions():
    r = raw('def four(acc=0.8): {kick: "x...x...", hat: {steps: "-.x.", vel: [0.4, acc]}}\n'
            'def build(n, base=full):\n  h = euclid(n, 16)\n  return base + {hat16: h}\n'
            'v = {drums: four(acc=1)}\nw = {drums: build(4)}\nform:\n  v 1\n  w 1\n')
    v, w = (s["parts"]["drums"] for s in r["sections"])
    assert v["steps"]["hat"] == {"steps": "-.x.", "vel": [0.4, 1]}
    assert w == {"style": "full", "steps": {"hat16": "x...x...x...x..."}}


# ----------------------------------------------------------------------------
# repetition
# ----------------------------------------------------------------------------
def test_xn_repeats_with_names_and_rep():
    r = raw('v = {drums: full}\nform:\n  v 4 x3:\n    if rep == last: drums += fill\n  v 2 as outro\n')
    assert [(s["name"], s["bars"]) for s in r["sections"]] == [("v", 4), ("v_2", 4), ("v_3", 4), ("outro", 2)]
    assert [s["parts"]["drums"] for s in r["sections"]] == ["full", "full", {"style": "full+fill"}, "full"]


def test_for_index_in_expressions():
    r = raw('v = {drums: full, lead: [a]}\nform:\n  for i in 1..3:\n    v 2*i:\n      lead = [a, b][i]\n'
            '      drums.kick = euclid(i + 1, 8)\n')
    assert [(s["name"], s["bars"]) for s in r["sections"]] == [("v", 2), ("v_2", 4), ("v_3", 6)]
    assert [s["parts"]["lead"] for s in r["sections"]] == ["b", "a", "b"]          # cyclic, 0-based
    assert [s["parts"]["drums"]["steps"]["kick"] for s in r["sections"]] == [
        lang.euclid(2, 8), lang.euclid(3, 8), lang.euclid(4, 8)]


def test_for_over_a_list_with_if_elif_else_and_form_assignments():
    src = ('v = {bass: sub}\nc = {bass: eighths}\nform:\n  for s in [1, 2, 3, 4]:\n'
           '    if s == first:\n      v 1\n    elif s % 2 == 0:\n      c 2\n    else:\n      v 3\n'
           '    v.bass = eighths\n')
    assert secs(src) == [("v", 1), ("c", 2), ("v_2", 3), ("c_2", 2)]
    assert raw(src)["sections"][2]["parts"]["bass"] == "eighths"     # rebinding in the loop reaches later lines


def test_nested_loops_and_last():
    src = 'v = {bass: sub}\nform:\n  for i in 1..2:\n    for j in 1..3:\n      if j == last and i == 2: v 1\n'
    assert secs(src) == [("v", 1)]


# ----------------------------------------------------------------------------
# conditions: per iteration and per bar
# ----------------------------------------------------------------------------
def test_if_per_iteration_expands():
    a = arr('v = {drums: {kick: "x..."}}\nform:\n  for i in 1..3:\n    v 1:\n'
            '      if i == last: drums += {clap: "..x."}\n')
    assert hits(a, "clap") == [8 + 2]           # only the last (third) bar
    assert hits(a, "kick") == [0, 4, 8]


def test_every_counts_instance_bars():
    a = arr('v = {drums: {kick: "x..."}}\nform:\n  v 2\n  v 8:\n    every 4 bars: drums += {clap: "x..."}\n'
            '    every 4 bars at 1: drums.kick += "..x."\n')
    start = 2 * 4
    assert hits(a, "clap") == [start + 12, start + 28]                      # bars 4 and 8 of the instance
    kicks = hits(a, "kick")
    assert start + 2 in kicks and start + 16 + 2 in kicks and start + 4 + 2 not in kicks


def test_every_at_form_level_counts_song_bars():
    a = arr('x = {drums: {kick: "x..."}}\ny = {drums: full}\nz = {bass: sub}\n'
            'form:\n  every 4 bars: drums += {ohat: "...x"}\n  x 2\n  z 2\n  y 4\n')
    assert hits(a, "ohat") == [28 + 3]      # song bars 4 (in z, which has no drums: skipped) and 8
    assert {e.section for e in a.parts["drums"] if e.piece == "ohat"} == {"y"}


def test_every_on_a_style_lane_keeps_the_style():
    r = raw('v = {drums: full}\nform:\n  v 2:\n    every 2 bars: drums.snare += "...............x"\n')
    d = r["sections"][0]["parts"]["drums"]
    assert d == {"style": "full", "steps": {"snare": "....x.......x...|....x.......x..x"}}


# ----------------------------------------------------------------------------
# errors: file:line and a suggestion
# ----------------------------------------------------------------------------
ERRORS = [
    ("v = {drums: ful}\nform:\n  v 4\n", 5, "unknown drums style 'ful'", "did you mean 'full'"),
    ("v = {drums: full + hat16}\nform:\n  v 4\n", 7, "no mod '+hat16'", "did you mean 'hats16'"),
    ("verse = {bass: sub}\nform:\n  vrese 4\n", 7, "unknown section 'vrese'", "did you mean 'verse'"),
    ("verse = {bass: sub}\nchorus = vers with {pad: warm}\nform:\n  chorus 4\n", 6, "built from 'vers'",
     "did you mean 'verse'"),
    ("verse = {bass: sub}\nvrse.bass = eighths\nform:\n  verse 4\n", 6, "'vrse' is not defined", "did you mean 'verse'"),
    ("v = {bass: sub}\nform:\n  for i in 1..2:\n    v 4:\n      if j == last: bass = eighths\n", 9,
     "'j' is not defined", "valid: first i last"),
    ("def f(g): g(g)\nx = f(f)\nform:\n  x 4\n", 5, "can't recurse", "unroll it"),
    ("v = {bass: sub}\nform:\n  for i in 1..100000:\n    v 1\n", 7, "more than 4096", "static, small bounds"),
    ("v = {bass: sub}\nform:\n  v 1 x5000\n", 7, "x5000", None),
    ("v = {bass: sub}\nform:\n  v 4 !impakt\n", 7, "unknown event type 'impakt'", "did you mean 'impact'"),
    ("v = {arp: up with {oder: [0, 1]}}\nform:\n  v 4\n", 5, "unknown part option 'oder'", "did you mean 'order'"),
    ("v = {bass: sub}\nform:\n  v 4:\n    every 2 bars: bass += {kick: \"x...\"}\n", 8, "drum kits", "split the section"),
    ("v = {drums: full}\nform:\n  v 8:\n    every 8 bars: drums += fill\n", 8, "already plays every 8 bars",
     "without 'every'"),
    ("v = {drums: \"x...\"}\nform:\n  v 4\n", 7, "ambiguous", "{kick:"),
    ("v = {bass: sub\nform:\n  v 4\n", 5, "unclosed bracket", "close every"),
    ("for i in 1..2:\n  x = 1\n", 5, "go in the form block", "every N bars"),
    ("groove swing=.5\n", 5, "not in the language prototype", "P6"),
    ("v = {bass: sub}\n", None, "no form block", "form:"),
    ("v = {bass: sub}\nform:\n  v\n", 7, "how many bars", "v 8"),
    ("v = {bass: sub}\nform:\n    v 4\n  v 4\n", 8, "indent", None),
    ("v = {bass: sub}\nx = v + 1\n", 6, "can't use '+'", "layers beats"),
]


@pytest.mark.parametrize("src,line,what,hint", ERRORS, ids=[e[2][:28] for e in ERRORS])
def test_errors_carry_file_line_and_a_suggestion(src, line, what, hint):
    with pytest.raises(SongError) as ei:
        expand(lang.loads(HEAD + src, "song.sml"))
    e = ei.value
    assert e.file == "song.sml"
    assert e.line == line, str(e)
    assert what in e.message, str(e)
    if hint:
        assert e.suggestion and hint in e.suggestion, str(e)
    assert str(e).startswith(f"song.sml:{line} " if line else "song.sml ")
