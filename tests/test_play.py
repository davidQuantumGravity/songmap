"""The performance stage (perform/play.py) and mood presets (arrange/moods)."""
import os

import numpy as np
import pytest

from songmap.arrange.expand import expand
from songmap.arrange.moods import load_moods
from songmap.parse import lang, yaml_form
from songmap.parse.errors import SongError
from songmap.perform.play import play

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def arr(body, head='song "P" 120 4/4 Am fps=30 seed=3 tail=1'):
    return expand(lang.loads(head + "\nchords Am F C G\n" + body, "p.sm"))


@pytest.mark.parametrize("name", ["week_oct13_swarm", "week_oct13_bench", "deepdive_kapton"])
def test_ports_are_unperformed(name):
    a = expand(yaml_form.load(os.path.join(ROOT, "examples", "v0.2_yaml", f"{name}.songmap.yaml")))
    assert a.ensemble.mood["mood"] == "v0"
    assert play(a) is a.parts                                   # v0: exactly the written notes
    assert a.ensemble.mix["drums"]["gain_db"] == 0              # and the synth_v0 levels


def test_new_songs_default_to_the_balanced_mood():
    a = arr("x 2 | drums:full lead:{deg: \"0/4 2 4 2\", oct: 1}")
    assert a.ensemble.mood["mood"] == "balanced"
    assert a.ensemble.mix["drums"]["gain_db"] == -6 and a.ensemble.mix["lead"]["gain_db"] == 7
    assert play(a) is not a.parts


def test_swing_moves_the_off_beats():
    a = arr('x 2 | drums:{hat: "x.x.x.x.x.x.x.x."}\ngroove swing=.58/8 hum=0,0,0 metric=0')
    beats = sorted(e.beat for e in play(a)["drums"])
    assert beats[:4] == pytest.approx([0.0, 0.58, 1.0, 1.58])  # the 8th off-beats land +0.08 beat late


def test_humanize_is_bounded_seeded_and_keeps_the_kick_tight():
    a = arr('x 8 | drums:{kick: "x...x...x...x...", hat: "x.x.x.x.x.x.x.x."} keys:{rel: "[R,3,5]/2 [R,3,5]"}')
    p1, p2 = play(a), play(a)
    assert [e.beat for e in p1["drums"]] == [e.beat for e in p2["drums"]]          # reproducible
    written = {(e.piece, e.beat) for e in a.parts["drums"]}
    dev = {"kick": [], "hat": []}
    for e in p1["drums"]:
        w = min((b for (pc, b) in written if pc == e.piece), key=lambda b: abs(b - e.beat))
        dev[e.piece].append(abs(e.beat - w) * 0.5 * 1000)                          # ms at 120 BPM
    assert max(dev["kick"]) < 5 and max(dev["hat"]) < 40 and np.mean(dev["hat"]) > np.mean(dev["kick"])
    vels = [e.vel for e in p1["drums"] if e.piece == "hat"]
    assert len(set(round(v, 3) for v in vels)) > 10                              # no two hats alike


def test_chords_roll_and_events_stay_on_their_frames():
    a = arr('x 2 | gtr:{rel: "[R,3,5]/1"} | !impact@+1')
    p = play(a)
    first = [e for e in p["gtr"] if e.beat < 1]
    assert len(first) == 3 and sorted(e.pitches[0] for e in first) == [e.pitches[0] for e in sorted(first, key=lambda e: e.beat)]
    assert {e.beat for e in p["fx"]} == {e.beat for e in a.parts["fx"]} == {4.0}


def test_moods_and_feel_errors():
    assert {"v0", "balanced", "techno", "cinematic", "documentary", "ambient", "lofi"} <= set(load_moods())
    with pytest.raises(SongError, match="unknown mood 'cinematik'"):
        arr("x 1 | pad:warm", head='song "P" 120 4/4 Am mood=cinematik')
    with pytest.raises(SongError, match="unknown groove template"):
        play(arr("x 1 | pad:warm\ngroove tpl=wonky"))
    lofi = arr("x 1 | pad:warm", head='song "P" 120 4/4 Am mood=lofi')
    assert lofi.ensemble.mood["groove"]["swing"] == 0.58


def test_section_feel_and_part_feel_override():
    a = arr('x 2 | drums:{hat: "x.x.x.x.x.x.x.x."} swing=.66\ngroove hum=0,0,0 metric=0\nfeel hat offset=10')
    beats = sorted(e.beat for e in play(a)["drums"])
    assert beats[1] == pytest.approx(0.66 + 0.02)               # section swing 0.66, plus 10 ms (0.02 beat)
