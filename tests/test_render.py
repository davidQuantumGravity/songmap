"""End to end: render, exporters (24-bit WAV, stems, cues.json), CLI."""
import json
import os

import numpy as np
import pytest

from songmap import cli
from songmap.arrange.expand import expand
from songmap.export import cues as cues_mod
from songmap.export.wav import read_wav
from songmap.instruments.dsp import SR
from songmap.render import render, write_outputs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWARM = os.path.join(ROOT, "examples", "v0.2_yaml", "week_oct13_swarm.songmap.yaml")

SMALL = {"title": "small", "key": "E minor", "tail_seconds": 1, "harmony": {"default": ["Em", "C"], "chord_bars": 1},
         "motifs": {"m": {"deg": "0 2 4 2"}},
         "sections": [{"name": "a", "bars": 1, "parts": {"pad": "warm", "bass": "sub", "fx": "ticks"}},
                      {"name": "b", "bars": 1, "parts": {"drums": "full", "bass": "eighths", "arp": "up", "lead": ["m"]}}],
         "events": [{"at": "b", "type": "impact"}, {"at": "b", "type": "riser", "bars": 1},
                    {"at": "0:3", "type": "zaps", "count": 2}]}


@pytest.fixture(scope="module")
def small_render():
    from songmap.parse import yaml_form
    return render(yaml_form.from_raw({"songmap": 0.2, **SMALL}, file="small.yaml"))


def test_render_is_deterministic_and_finite(small_render, make_song):
    r2 = render(make_song(SMALL))
    assert np.array_equal(small_render.audio, r2.audio)
    assert np.all(np.isfinite(small_render.audio)) and small_render.audio.shape == (int(5 * SR), 2)
    assert np.max(np.abs(small_render.audio)) <= 1.0


def test_outputs(small_render, tmp_path):
    paths = write_outputs(small_render, str(tmp_path))
    sr, x = read_wav(paths["song"])
    assert sr == SR and x.shape == small_render.audio.shape
    assert np.max(np.abs(x - small_render.audio)) < 2 ** -22          # 24-bit
    assert sorted(os.listdir(paths["stems"])) == sorted(f"{k}.wav" for k in small_render.stems)
    c = json.load(open(paths["cues"], encoding="utf-8"))
    assert cues_mod.validate(c) == [] and [s["start_frame"] for s in c["sections"]] == [0, 60]
    assert {e["type"] for e in c["events"]} == {"impact", "riser", "zaps"}
    riser = next(e for e in c["events"] if e["type"] == "riser")
    assert riser["frame"] == 60 and riser["start_frame"] == 0            # risers END at `at`
    qa = json.load(open(paths["qa"], encoding="utf-8"))
    assert set(qa["stems"]) == set(small_render.stems)


def test_legacy_master_is_synth_v0s(small_render):
    from songmap.mix.master import master_legacy
    y = master_legacy(small_render.premaster)
    assert np.max(np.abs(y)) <= 0.89 + 1e-9 and np.allclose(y[-1], 0)


def test_cues_validator_catches_problems():
    from songmap.parse import yaml_form
    c = cues_mod.build(expand(yaml_form.load(SWARM)))
    assert cues_mod.validate(c) == []
    assert c["frames"] == 3690 and c["video"]["frames"] == 3690
    bad = json.loads(json.dumps(c))
    bad["sections"][3]["start_frame"] += 1
    assert any("starts at frame" in p for p in cues_mod.validate(bad))
    bad = json.loads(json.dumps(c))
    del bad["events"][0]["frame"]
    assert any("missing 'frame'" in p for p in cues_mod.validate(bad))


def test_cli_check_render_migrate(tmp_path, capsys):
    assert cli.main(["check", SWARM]) == 0
    assert "3690 frames" in capsys.readouterr().out
    old = os.path.join(ROOT, "examples", "v0.1_yaml", "week_oct13_swarm.songmap.yaml")
    out = tmp_path / "swarm.yaml"
    assert cli.main(["migrate", old, "-o", str(out)]) == 0
    assert out.read_text(encoding="utf-8").startswith("# Port of the Video B")
    assert cli.main(["check", str(out)]) == 0
    bad = tmp_path / "bad.yaml"
    bad.write_text("songmap: 0.2\nsections:\n  - {name: a, bars: 1, parts: {bass: eigths}}\n", encoding="utf-8")
    assert cli.main(["check", str(bad)]) == 1
    assert "did you mean 'eighths'" in capsys.readouterr().err
    small = tmp_path / "small.yaml"
    small.write_text(json.dumps({"songmap": 0.2, **SMALL}), encoding="utf-8")      # JSON is YAML
    assert cli.main(["render", str(small), "-o", str(tmp_path / "out"), "--no-stems"]) == 0
    assert os.path.isfile(tmp_path / "out" / "song.wav") and not os.path.isdir(tmp_path / "out" / "stems")
