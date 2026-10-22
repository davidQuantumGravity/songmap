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


def doc_blocks(path=DOC):
    with open(path, encoding="utf-8") as f:
        return re.findall(r"```\n(.*?)```", f.read(), re.S)


@pytest.mark.parametrize("doc", ["LANGUAGE.md", "COMPACT_FORMAT.md"])
def test_every_complete_program_in_the_docs_expands(doc):
    programs = [b for b in doc_blocks(os.path.join(ROOT, "docs", doc))
                if b.startswith(("song ", "# ")) and "<title>" not in b]      # not the syntax listings
    assert programs
    for b in programs:
        assert expand(lang.loads(b, doc)).timeline.total_bars > 0


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
    ("v = {bass: sub}\nform:\n  v 4:\n    every 2 bars: bass += {kick: \"x...\"}\n", 5, "unknown part option 'kick'",
     "valid:"),
    ("v = {drums: full}\nform:\n  v 8:\n    every 8 bars: drums += fill\n", 8, "already plays every 8 bars",
     "without 'every'"),
    ("v = {drums: \"x...\"}\nform:\n  v 4\n", 7, "ambiguous", "{kick:"),
    ("v = {bass: sub\nform:\n  v 4\n", 5, "unclosed bracket", "close every"),
    ("for i in 1..2:\n  x = 1\n", 5, "go in the form block", "every N bars"),
    ("groove swang=.5\n", 5, "groove: 'swang=.5' not understood", "swing="),
    ("v = {bass: sub}\n", None, "no sections", "form:"),
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


# ----------------------------------------------------------------------------
# .sm: the compact ports are the YAML ports
# ----------------------------------------------------------------------------
PORTS = ["week_oct13_swarm", "week_oct13_bench", "deepdive_kapton"]


@pytest.mark.parametrize("name", PORTS)
def test_compact_ports_match_the_yaml_ports(name):
    from songmap.theory.keys import parse_key
    a = expand(lang.load(os.path.join(ROOT, "examples", f"{name}.sm")))
    b = expand(yaml_form.load(os.path.join(ROOT, "examples", "v0.2_yaml", f"{name}.songmap.yaml")))
    assert a.digest() == b.digest()
    assert [(s.name, s.bars) for s in a.song.sections] == [(s.name, s.bars) for s in b.song.sections]
    assert [(e.type, e.at, e.params) for e in a.song.events] == [(e.type, e.at, e.params) for e in b.song.events]
    for k in ("title", "tempo", "fps", "seed", "tail_seconds", "video", "instruments", "harmony", "master"):
        assert getattr(a.song, k) == getattr(b.song, k), k
    assert parse_key(a.song.key) == parse_key(b.song.key)          # 'Em' vs 'E minor'


@pytest.mark.parametrize("ext", [".sm", ".sml"])
def test_cli_loads_both_extensions(tmp_path, capsys, ext):
    from songmap.cli import main
    p = tmp_path / f"song{ext}"
    p.write_text(HEAD + "verse 4 | bass:sub\n", encoding="utf-8")
    assert main(["check", str(p)]) == 0
    assert "4 bars" in capsys.readouterr().out


# ----------------------------------------------------------------------------
# section lines (the compact grammar)
# ----------------------------------------------------------------------------
def test_section_lines_define_and_place():
    r = raw('lit = up(order=[0, 2, 1])\n'
            'x 4 | drums:full+fill bass:8ths(art=staccato) arp:lit lead:a,b:t+2 | !impact\n'
            'y 2 x2 | like=x -lead drums:half kick="X...x..." keys="=p a c e" | !riser:1@+1\n'
            'z 2 | pad:warm:dyn=pp lead:a:oct=1\n')
    s = {x["name"]: x for x in r["sections"]}
    assert list(s) == ["x", "y", "y_2", "z"]
    assert s["x"]["parts"] == {"drums": {"style": "full+fill"}, "bass": {"art": "staccato", "style": "8ths"},
                               "arp": {"style": "up", "order": [0, 2, 1]}, "lead": {"motifs": ["a", "b:t+2"]}}
    assert s["y"]["parts"] == {"drums": {"style": "half", "steps": {"kick": "X...x..."}},
                               "bass": {"art": "staccato", "style": "8ths"}, "arp": {"style": "up", "order": [0, 2, 1]},
                               "keys": {"notes": "=p a c e"}}
    assert s["z"]["parts"] == {"pad": {"dyn": "pp", "style": "warm"}, "lead": {"oct": 1, "motifs": ["a"]}}
    assert [(e["at"], e["type"]) for e in r["events"]] == [("x", "impact"), ("y+1", "riser"), ("y_2+1", "riser")]


def test_section_line_settings():
    r = raw('prog doubt "Am:2 Dm:2"\n'
            'a 4 | arp:up dyn=p<mf prog=doubt feel=push swing=.58 tempo=120 key=Am auto="arp.cutoff:1500>4000 exp"\n'
            'b 2 | pad:warm chords="Am:1 G:1" tempo=rit120>96\n')
    a, b = r["sections"]
    assert (a["dyn"], a["harmony"], a["feel"], a["tempo"], a["key"]) == (
        "p<mf", "doubt", {"template": "push", "swing": 0.58}, 120, "Am")
    assert a["parts"]["arp"] == {"auto": {"cutoff": "1500>4000 exp"}, "style": "up"}
    assert (b["harmony"], b["tempo"]) == ("Am:1 G:1", "rit 120>96")


def test_header_directives_map_onto_song_fields():
    song = lang.loads(HEAD + 'inst bass(cutoff=600) keys=keys/felt(hardness=.35) lead=lead\n'
                      'kit kick=kick/v0(tune=44) clap=clap\n'
                      'groove swing=.54/16 tpl=push hum=4,3,.03 metric=.5\n'
                      'feel bass offset=-3 gate=.85\nfeel keys high_loud=.4 arch=.5 hum=7,2,.02\n'
                      'mix bass -2 sc=.5 | pad -6 hall=.35 | lead -4 room=.1 pan=.2\n'
                      'qa lufs=-15..-13 contrast=a<b:6 silent!=b low<=.6 peak<=-1 hits=true\n'
                      'cue big=f300\nmaster standard lufs=-14 ceiling=-1 glue=punchy contrast=4\n'
                      'a 4 | bass:sub\nb 4 | pad:warm\n', "song.sm")
    assert song.instruments == {"bass": {"cutoff": 600}, "keys": {"use": "keys/felt", "hardness": 0.35}, "lead": "lead",
                                "drums": {"kit": {"kick": {"use": "kick/v0", "tune": 44}, "clap": "clap"}}}
    assert song.groove == {"swing": 0.54, "swing_grid": 16, "template": "push",
                           "humanize": {"time_ms": 4, "drift_ms": 3, "vel": 0.03}, "metric": 0.5}
    assert song.parts_feel == {"bass": {"offset_ms": -3, "gate": 0.85}, "keys": {
        "high_loud": 0.4, "arch": 0.5, "humanize": {"time_ms": 7, "drift_ms": 2, "vel": 0.02}}}
    assert song.mix["bass"]["gain_db"] == -2 and song.mix["bass"]["sidechain"]["depth"] == 0.5
    assert song.mix["bass"]["sidechain"]["from"] == "kick" and "release" in song.mix["bass"]["sidechain"]
    assert song.mix["pad"]["send"] == {"hall": 0.35} and song.mix["lead"]["pan"] == 0.2
    assert song.qa == {"target_lufs": [-15, -13], "contrast": [["a", "b", 6]], "never_silent": ["b"],
                       "max_low_ratio": 0.6, "true_peak_max_db": -1, "hits_audible": True}
    assert song.cues == {"big": "f300"}
    assert (song.master.mode, song.master.target_lufs, song.master.glue, song.master.preserve_contrast) == (
        "standard", -14, "punchy", 4)


# ----------------------------------------------------------------------------
# named events
# ----------------------------------------------------------------------------
def test_named_events():
    r = raw('lift = !impact !riser:2\nbig = !lift !riser:1@+8\nzz = !zaps(count=3, every=8, keep=[pad, bass])\n'
            'end = lift + zz\nx 16 | bass:sub | !big\ny 2 | pad:warm | !end !impact@+1 !hit@3:2 !stop@2\n')
    assert [(e["at"], e["type"], {k: v for k, v in e.items() if k not in ("at", "type")}) for e in r["events"]] == [
        ("x", "impact", {}), ("x", "riser", {"bars": 2}), ("x+8", "riser", {"bars": 1}),
        ("y", "impact", {}), ("y", "riser", {"bars": 2}), ("y", "zaps", {"count": 3, "every": 8, "keep": ["pad", "bass"]}),
        ("y+1", "impact", {}), ("3:2", "hit", {}), (2, "stop", {})]


def test_named_events_on_form_lines_and_in_edits():
    r = raw('lift = !impact !riser:2\nv = {bass: sub}\nform:\n  v 4 !lift\n  v 4:\n    !lift\n')
    assert [(e["at"], e["type"]) for e in r["events"]] == [("v", "impact"), ("v", "riser"), ("v_2", "impact"),
                                                            ("v_2", "riser")]


# ----------------------------------------------------------------------------
# per-bar edits on any part
# ----------------------------------------------------------------------------
def test_per_bar_variants_on_pitched_parts():
    src = ('v = {bass: sub, pad: warm, lead: [a]}\nform:\n  v 8:\n    every 4 bars: bass = eighths\n'
           '    bar 2, -1: lead = [b]\n    bar 3: pad = none\n')
    parts = raw(src)["sections"][0]["parts"]
    assert parts["bass"] == {"style": "sub", "vary": [{"bars": [3, 7], "part": {"style": "eighths"}}]}
    assert parts["lead"] == {"motifs": ["a"], "vary": [{"bars": [1, 7], "part": {"motifs": ["b"]}}]}
    assert parts["pad"] == {"style": "warm", "vary": [{"bars": [2], "part": {"mute": True}}]}
    a = arr(src)
    eighths = sorted({int(e.beat // 4) for e in a.parts["bass"] if e.dur < 1})
    assert eighths == [3, 7]                                   # eighths only in bars 4 and 8
    assert not [e for e in a.parts["pad"] if 8 <= e.beat < 12]  # pad starts nothing in bar 3
    tags = {int(e.beat // 4): {t for t in e.tags if t.startswith("motif:")} for e in a.parts["lead"]}
    assert tags[1] == tags[7] == {"motif:b"} and tags[0] == {"motif:a"}


def test_per_bar_variant_adds_a_part_the_section_lacks():
    src = 'v = {bass: sub}\nform:\n  v 4:\n    bar 4: lead = [a]\n'
    assert raw(src)["sections"][0]["parts"]["lead"] == {"mute": True, "vary": [{"bars": [3], "part": {"motifs": ["a"]}}]}
    assert {int(e.beat // 4) for e in arr(src).parts["lead"]} == {3}


def test_every_song_bars_inside_a_section():
    src = ('v = {bass: sub}\nform:\n  v 2\n  v 6:\n    every 4 song bars: bass = eighths\n'
           '    every 4 bars: bass.oct = 1\n')
    parts = raw(src)["sections"][1]["parts"]
    # song bars 4 and 8 are this section's offsets 1 and 5; its own 4th bar is offset 3
    assert parts["bass"]["vary"] == [{"bars": [1, 5], "part": {"style": "eighths"}},
                                     {"bars": [3], "part": {"oct": 1, "style": "sub"}}]


def test_form_level_every_reaches_pitched_parts():
    src = 'x = {bass: sub}\ny = {pad: warm}\nform:\n  every 2 bars: bass = eighths\n  x 2\n  y 2\n  x 2\n'
    s = raw(src)["sections"]
    assert s[0]["parts"]["bass"]["vary"] == [{"bars": [1], "part": {"style": "eighths"}}]
    assert "bass" not in s[1]["parts"]
    assert s[2]["parts"]["bass"]["vary"] == [{"bars": [1], "part": {"style": "eighths"}}]


def test_yaml_vary(make_song):
    song = make_song({"tempo": 120, "key": "A minor", "harmony": {"default": ["Am", "F"]}, "sections": [
        {"name": "v", "bars": 4, "parts": {"bass": {"style": "sub", "vary": [{"bars": [1, 3], "part": "eighths"}]}}}]})
    a = expand(song)
    assert sorted({int(e.beat // 4) for e in a.parts["bass"] if e.dur < 1}) == [1, 3]
    with pytest.raises(SongError, match="vary bars are whole bar offsets"):
        make_song({"sections": [{"name": "v", "bars": 4, "parts": {"bass": {
            "style": "sub", "vary": [{"bars": [-1], "part": "eighths"}]}}}]})


def test_variants_leave_other_songs_untouched():
    a = expand(lang.load(SWARM_SML))
    assert not [p for s in a.song.sections for p in s.parts.values() if p.variants]


# ----------------------------------------------------------------------------
# errors in the new features
# ----------------------------------------------------------------------------
NEW_ERRORS = [
    ("hit = !impact\n", 5, "'hit' is an event type", "pick another name"),
    ("lift = !impact\nv = {bass: sub}\nform:\n  v 4 !lift@+2\n", 8, "named event list", "inside its definition"),
    ("a 4 | bass:sub\nv = {bass: sub}\nform:\n  v 4\n", 7, "can't be mixed", "the first section line is line 5"),
    ("a 4 | like=b bass:sub\n", 5, "like=b: not an earlier section", None),
    ("a 4 | bass:sub vibe=chill\n", 5, "unknown setting 'vibe'", "valid:"),
    ("a 4 | bass:sub ??\n", 5, "'??' not understood", "role:style"),
    ("a 4 | lead:a,zz\n", 5, "unknown motif 'zz'", "valid:"),
    ("a 4 | bass:sub auto=lead.cutoff:1>2\n", 5, "auto for 'lead'", None),
    ("mix bass loud\n", 5, "needs a part and a gain", "mix bass -2"),
    ("mix bass -2 reverb=.3\n", 5, "unknown option 'reverb'", "valid:"),
    ("qa contrast=a>b:6\n", 5, "qa contrast 'a>b:6'", "quiet<loud"),
    ("feel bass swing=.6\n", 5, "feel bass: 'swing=.6' not understood", "valid:"),
    ("kit kick\n", 5, "kit: write kick=", None),
    ("v = {bass: sub}\nform:\n  v 4:\n    bar 5: bass = eighths\n", 8, "bar 5: the section has 4 bars", "1..4"),
    ("v = {bass: sub}\nform:\n  v 4:\n    every 2 bars: dyn = \"p\"\n", 8, "not the section's dyn", "split the section"),
    ("v = {bass: sub}\nbar 2: bass = eighths\n", 6, "goes under a section line", None),
]


@pytest.mark.parametrize("src,line,what,hint", NEW_ERRORS, ids=[e[2][:28] for e in NEW_ERRORS])
def test_new_feature_errors(src, line, what, hint):
    test_errors_carry_file_line_and_a_suggestion(src, line, what, hint)


def test_sharp_glued_to_a_word_is_not_a_comment():
    s = lang.loads('song "T" 120 4/4 C#m\nchords C#m F#:2 G#7  # a real comment\nintro 2 | pad:warm\n', "t.sm")
    assert s.key == "C#m" and s.harmony.default == ["C#m", "F#:2", "G#7"]


def test_a_part_named_chords_is_not_the_harmony_setting():
    s = lang.loads('song "T" 120 4/4 C\nchords C F\na 2 | chords:hold chords="Am:1 G:1"\n', "t.sm")
    assert s.sections[0].harmony == "Am:1 G:1" and s.sections[0].parts["chords"].style == "hold"


# ----------------------------------------------------------------------------
# brackets join physical lines: a map, list or call written over several lines is its one-line form
# ----------------------------------------------------------------------------
MULTILINE = [
    ('pocket = {kick: "X.....x...x.....", snare: "....X..o....X.o.", hat: "x-x-x-x-x-x-x-x-"}\n'
     'intro 2 | drums:pocket\n',
     'pocket = {kick: "X.....x...x.....",\n'
     '          snare: "....X..o....X.o.",   # backbeat\n'
     '\n'
     '          hat: "x-x-x-x-x-x-x-x-"}\n'
     'intro 2 | drums:pocket\n'),
    ('intro 2 | drums:{kick: "X...x...", hat: "x-x-x-x-"} bass:sub | !impact !riser:1(size=xl)\n',
     'intro 2 | drums:{kick: "X...x...",\n'
     '                 hat: "x-x-x-x-"} bass:sub | !impact !riser:1(size=\n'
     '   xl)\n'),
    ('v = {drums: {kick: "x...", hat: {steps: "-.x.", vel: [0.4, 0.9]}}, arp: up(order=[0, 2, 1]), lead: [a, b]}\n'
     'form:\n  v 2:\n    bar 2: drums += {clap: "..x."}\n',
     'v = {\n'
     '  drums: {kick: "x...",\n'
     '          hat: {steps: "-.x.",\n'
     '                vel: [0.4,\n'
     '                      0.9]}},  # nested\n'
     '  arp: up(order=[0,\n'
     '                 2, 1]),\n'
     '  lead: [a,\n'
     '         b]\n'
     '}\n'
     'form:\n  v 2:\n    bar 2: drums += {clap:\n                     "..x."}\n'),
]


@pytest.mark.parametrize("one,multi", MULTILINE, ids=["variable", "section_line", "nested"])
def test_multiline_brackets_parse_like_one_line(one, multi):
    assert arr(multi).digest() == arr(one).digest()


def test_multiline_lines_keep_their_line_numbers():
    s = lang.loads(HEAD + 'pocket = {kick: "x...",\n          hat: "x-x-"}\n'
                   'intro 2 | drums:pocket\nlater 2 | drums:pocket bass:sub\n', "song.sml")
    assert [(x.name, x.line) for x in s.sections] == [("intro", 7), ("later", 8)]


@pytest.mark.parametrize("src,line,what,hint", [
    ('pocket = {kick: "x...",\n          snare: "....X..."\n          hat: "x-x-"}\nintro 2 | drums:pocket\n',
     7, "expected ',', got 'hat'", "separate items with ','"),
    ('pocket = {kick: "x...",\n          hat: "x-x-"\nintro 2 | drums:pocket\n', 5, "unclosed bracket", "close every"),
], ids=["missing_comma", "unclosed"])
def test_malformed_multiline_map_is_a_song_error(src, line, what, hint):
    test_errors_carry_file_line_and_a_suggestion(src, line, what, hint)


@pytest.mark.parametrize("src,what", [
    ('song "T" 120 4/4 Am video=Clip:12ab\nchords Am\na 2 | pad:warm\n', "video frames '12ab'"),
    ('song "T" 120 4/4 Am\nchords Am\nmotif m deg oct=x5 "0 2"\na 2 | lead:m\n', "octave 'x5'"),
    ('song "T" 120 4/4 Am seed=7x\nchords Am\na 2 | pad:warm\n', "seed must be a number"),
])
def test_bad_numbers_in_header_lines_are_song_errors(src, what):
    with pytest.raises(SongError, match=re.escape(what)) as ei:
        lang.loads(src, "t.sm")
    assert ei.value.file == "t.sm"
