"""Printing songs (songmap/parse/fmt.py): YAML and .sm round trips are lossless on every example."""
import glob
import os

import pytest

from songmap.arrange.expand import expand
from songmap.parse import fmt, lang, yaml_form

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = sorted(p for ext in ("yaml", "sm", "sml")
                  for p in glob.glob(os.path.join(ROOT, "examples", "**", f"*.{ext}"), recursive=True))


def load(path):
    return lang.load(path) if path.endswith((".sm", ".sml")) else yaml_form.load(path)


def reparse_sm(song):
    return lang.loads(fmt.to_sm(song), "printed.sm")


def reparse_yaml(song):
    return yaml_form.from_raw(yaml_form.load_raw_text(fmt.to_yaml(song)), "printed.yaml")


@pytest.mark.parametrize("path", EXAMPLES, ids=[os.path.relpath(p, ROOT) for p in EXAMPLES])
def test_examples_round_trip(path):
    song = load(path)
    want = fmt.song_to_raw(song)
    for back in (reparse_sm(song), reparse_yaml(song)):
        assert fmt.song_to_raw(back) == want
        assert expand(back).digest() == expand(song).digest()
    printed = fmt.to_sm(song)
    assert fmt.to_sm(lang.loads(printed, "printed.sm")) == printed        # printing is idempotent


def test_printed_swarm_reads_like_the_hand_written_one():
    text = fmt.to_sm(yaml_form.load(os.path.join(ROOT, "examples", "v0.2_yaml", "week_oct13_swarm.songmap.yaml")))
    assert "arp_dark = dark(order=[0, 2, 1, 3, 0, 2, 4, 3, 1, 2, 0, 3])" in text
    assert "agents     16 | like=goals drums:full+fill+open lead:m1,m2,m3,m4 | !impact !riser:2 !riser:1@+8" in text
    assert "guardrails  4 | like=so_what -fx" in text
    assert len(text) < 0.65 * len(open(os.path.join(ROOT, "examples", "v0.2_yaml",
                                                    "week_oct13_swarm.songmap.yaml"), encoding="utf-8").read())


AWKWARD = {
    "title": 'A "quoted" title — with a dash', "tempo": 100, "meter": "6/8", "key": "D dorian", "fps": 25, "seed": 3,
    "tail_seconds": 2.5, "mood": "late night", "video": {"composition": "X", "frames": 999, "fps_note": "ntsc"},
    "instruments": {"bass": {"use": "bass/sub", "cutoff": 640, "glide": 0.05}, "keys": "keys",
                    "pad": {"voices": 7}, "drums": {"kit": {"kick": {"use": "kick/v0", "tune": 44}, "snare": "snare"}},
                    "fx": {"riser": "riser", "impact": "impact/v0"}, "lead": {"use": "lead"}},
    "groove": {"swing": 0.56, "swing_grid": 16, "template": "push", "humanize": {"time_ms": 4, "drift_ms": 3, "vel": 0.03}},
    "parts_feel": {"bass": {"offset_ms": -3, "gate": 0.85}, "keys": {"high_loud": 0.4, "time_ms": 7}},
    "harmony": {"default": ["Dm", "G"], "chord_bars": 1.5, "progressions": {"turn": "Dm:1 Em:1 F:1 G:1"},
                "voicing": {"range": ["d3", "a4"], "style": "drop2"}},
    "motifs": {"a": "d e f g", "b": {"deg": "0 2 4 | 2/2.", "octave": 5, "key": "D dorian"}},
    "cues": {"big": "f300", "bar": 12},
    "sections": [
        {"name": "intro", "bars": 4, "dyn": "pp<p", "feel": {"template": "laid_back", "swing": 0.6},
         "parts": {"pad": "warm", "keys": {"notes": "=p d f a | e g b", "art": "tenuto"}, "lead": ["a", "b"]}},
        {"name": "groove", "bars": 8, "harmony": "turn", "tempo": "rit 100>90", "key": "Am",
         "parts": {"drums": {"style": "full+fill", "steps": {"kick": "X..x..X..x..", "hat": {"steps": "x.x.x.", "vel": [0.3, 0.6]}},
                             "gain_db": -1.5},
                   "bass": {"style": "sub", "vary": [{"bars": [3, 7], "part": "eighths"},
                                                     {"bars": [5], "part": {"mute": True}}]},
                   "fx": {"style": "ticks", "pan": 0.2}, "lead": {"motifs": ["a"], "oct": 1}}},
        {"name": "groove2", "bars": 2.5, "harmony": "Dm:2 C:0.5", "feel": {"push": 1},
         "parts": {"pad": "dark", "bass": "sub"}},
    ],
    "events": [
        {"at": "groove+2:3", "type": "hit", "size": "xl"},
        {"at": "intro", "type": "impact"},
        {"at": 3, "type": "drop", "bars": 1, "keep": ["pad", "keys"]},
        {"at": "cue:big", "type": "riser", "beats": 6},
        {"at": "f450", "type": "zaps", "count": 3, "every": 8},
        {"at": "groove2:2", "type": "stop", "beats": 2},
        {"at": "intro+1", "type": "swell", "part": "pad", "dyn": "p<ff"},
    ],
    "mix": {"bass": {"gain_db": -2, "sidechain": {"from": "kick", "depth": 0.5}},
            "lead": {"gain_db": -4, "send": {"hall": 0.25}, "eq": [{"peak": 3000, "gain": 2, "q": 1}]},
            "pad": {"pan": 0.1}},
    "returns": {"hall": {"type": "reverb", "seconds": 2.4}},
    "master": {"target_lufs": -16, "glue": "punchy", "preserve_contrast": 4},
    "qa": {"target_lufs": [-15, -13], "contrast": [["intro", "groove", 6]], "never_silent": ["groove"],
           "max_low_ratio": 0.6, "hits_audible": True, "custom_rule": {"x": 1}},
}


def test_awkward_song_round_trips(make_song):
    song = make_song(AWKWARD)
    want = fmt.song_to_raw(song)
    sm = fmt.to_sm(song)
    assert fmt.song_to_raw(lang.loads(sm, "printed.sm")) == want, sm
    assert fmt.song_to_raw(reparse_yaml(song)) == want
    assert "set returns=" in sm and "set harmony.voicing=" in sm and "set qa.custom_rule=" in sm
    assert "| !hit@+2:3(size=xl)" in sm and "\n!impact@intro\n" in sm   # an event for an earlier section: own line
    assert "\nintro     4 | " in sm and "\ngroove2 2.5 | " in sm


def test_value_formatting():
    assert fmt.value("warm") == "warm" and fmt.value("true") == '"true"' and fmt.value("12") == '"12"'
    assert fmt.value([1, "a b", None, 0.5]) == '[1, "a b", none, 0.5]'
    assert fmt.value({"from": "kick", "x-y": 1e-6}) == '{from: "kick", "x-y": 0.000001}'


def test_cli_fmt(tmp_path, capsys):
    from songmap.cli import main
    src = os.path.join(ROOT, "examples", "v0.2_yaml", "week_oct13_bench.songmap.yaml")
    out = tmp_path / "bench.sm"
    assert main(["fmt", src, "--to", "sm", "-o", str(out)]) == 0
    back = lang.load(str(out))
    assert expand(back).digest() == expand(yaml_form.load(src)).digest()
    assert out.read_text(encoding="utf-8").startswith("# Bench / Fields / Thruster")    # leading comments kept
    assert main(["fmt", str(out), "--to", "yaml"]) == 0
    assert "sections:" in capsys.readouterr().out
