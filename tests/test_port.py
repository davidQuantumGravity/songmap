"""Port check (ROADMAP P1 "done when"): the three Oct-13 songs against synth_v0 and the original audio.

- section boundaries frame-exact against docs/SCENE_TIMELINES.md, total length = the video's frames;
- every note synth_v0 played, and no other (tools/v0_oracle.py runs synth_v0's own build());
- golden event-list hashes (tests/golden/, rewritten only by tools/update_golden.py);
- per-section loudness correlates >= 0.9 with the original audio (assets/oct13, from P0).
"""
import json
import os

import pytest

import port_check as pc
from songmap.arrange.expand import expand
from songmap.parse import yaml_form

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMES = list(pc.SONGS)


@pytest.fixture(scope="module", params=NAMES)
def port(request):
    name = request.param
    return name, expand(yaml_form.load(pc.port_path(name)))


def test_sections_are_frame_exact(port):
    name, arr = port
    tl = arr.timeline
    assert {s.name: tl.beat_to_frame(s.start) for s in tl.sections} == pc.SCENE_FRAMES[name]
    assert tl.frames == pc.SONGS[name][3] == arr.song.video["frames"]


def test_every_note_matches_synth_v0(port):
    name, arr = port
    report = pc.compare_notes(arr, pc.SONGS[name][0])
    diffs = {k: v for k, v in report.items() if v["missing"] or v["extra"]}
    assert not diffs
    assert pc.compare_params(arr, pc.SONGS[name][0]) == []


@pytest.mark.parametrize("path", sorted(
    os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(ROOT, "examples")) for f in fs if f.endswith(".yaml")))
def test_golden_event_hashes(path):
    import update_golden
    golden = os.path.join(update_golden.GOLDEN, update_golden.golden_name(path))
    with open(golden, encoding="utf-8") as f:
        want = json.load(f)
    got = update_golden.snapshot(path)
    assert got["counts"] == want["counts"] and got["sections"] == want["sections"]
    assert got["digest"] == want["digest"], "notes changed: if intended, run tools/update_golden.py and commit"


@pytest.mark.port
@pytest.mark.parametrize("name", NAMES)
def test_section_loudness_correlates_with_the_original(name):
    from songmap.render import render
    audio = os.path.join(pc.ASSETS, pc.SONGS[name][2])
    if not os.path.isfile(audio):
        pytest.skip(f"{audio} missing (ROADMAP P0 step 4 recovers it)")
    r = render(yaml_form.load(pc.port_path(name)))
    spans = r.section_spans()
    ours = pc.section_loudness(r.audio, spans)
    orig = pc.section_loudness(pc.decode(audio), spans)
    assert pc.pearson(ours, orig) >= 0.9
