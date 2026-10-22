"""The binaural layer (songmap/mix/binaural.py): exact pure-tone pairs, one frequency per ear, hidden in the music."""
import glob
import os

import numpy as np
import pytest

from songmap.arrange.expand import expand
from songmap.export.qa import lufs
from songmap.listen import listen
from songmap.mix import binaural as bn
from songmap.parse import fmt, lang, yaml_form
from songmap.parse.errors import SongError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000
PHI = (1 + 5 ** 0.5) / 2
HEAD = 'song "B" 60 4/4 A fps=30 seed=1 tail=1 tuning=36edo\n'


def song(body):
    return lang.loads(HEAD + body, "b.sm")


def plan_of(body):
    s = song(body)
    return bn.plan(s, expand(s).timeline)


def peak(x, lo, hi):
    """Frequency of the strongest component in [lo, hi] Hz (Hann window, 8x zero padding)."""
    X = np.abs(np.fft.rfft(x * np.hanning(len(x)), 8 * len(x)))
    f = np.fft.rfftfreq(8 * len(x), 1 / SR)
    i = (f > lo) & (f < hi)
    return f[i][np.argmax(X[i])]


def test_carriers_in_every_spelling():
    s = song("binaural A3 ^F4 57 220hz A3*phi^2 A4*phi^-1\nx 2 | pad:warm\n")
    hz = [c.hz for c in bn.plan(s, expand(s).timeline).states[0].carriers]
    assert hz[0] == pytest.approx(220.0) and hz[2] == pytest.approx(220.0) and hz[3] == 220.0
    assert hz[1] == pytest.approx(349.228 * 2 ** (1 / 36), rel=1e-6)       # ^F4: a sixth-step above F4
    assert hz[4] == pytest.approx(220 * PHI ** 2) and hz[5] == pytest.approx(440 / PHI)


def test_golden_ladder_ramps_and_sticky_sections():
    p = plan_of("binaural A3 A3*phi A3*phi^2 beat=10\na 2 | pad:warm\nb 2 | pad:warm beat=10>6.18\nc 2 | pad:warm\n"
                "d 2 | pad:warm binaural={carriers: [A3, E4]}\n")
    a, b, c, d = p.states
    assert p.rates(a) == pytest.approx([10, 10 / PHI, 10 / PHI ** 2])
    assert p.rates(a)[0] - p.rates(a)[1] == pytest.approx(p.rates(a)[2])     # self-similar: d0 - d1 = d2
    assert b.beat == (10, 6.18) and c.beat == (6.18, 6.18) and d.beat == (6.18, 6.18)   # a ramp's end carries over
    assert [x.label for x in d.carriers] == ["A3", "E4"]
    assert bn.describe(p)[0].startswith("a: A3 220.00 Hz @ 10.00")


@pytest.mark.parametrize("body, msg, hint", [
    ("binaural A3 beat=60\n", "too fast", "theta 4-8"),
    ("binaural A3 ^E4\n", "sixth-step", "36edo"),
    ("binaural A3 E4 ladder=[1]\n", "1 rungs for 2 carriers", "one multiplier per carrier"),
    ("binaural H3\n", "carrier 'H3' not understood", "A3*phi^2"),
    ("binaural A1\n", "55.0 Hz", "200-500"),
    ("set binaural={carriers: [A3], beet: 4}\n", "unknown key 'beet'", "beat"),
    ("set binaural={beat: 4}\n", "needs carriers", "carriers: [A3, E4]"),
])
def test_errors_carry_file_line_and_a_suggestion(body, msg, hint):
    src = body.replace("\n", "") + "\nx 2 | pad:warm\n"
    head = HEAD.replace(" tuning=36edo", "") if "sixth-step" in msg else HEAD
    with pytest.raises(SongError) as e:
        s = lang.loads(head + src, "b.sm")
        bn.plan(s, expand(s).timeline)
    assert msg in str(e.value) and hint in str(e.value) and "b.sm" in str(e.value)


def test_section_errors_point_at_the_section_line():
    with pytest.raises(SongError) as e:
        plan_of("binaural A3\nx 2 | pad:warm\ny 2 | pad:warm binaural={carriers: [Q9]}\n")
    assert "b.sm:4" in str(e.value) and "Q9" in str(e.value)


def layer(body, seconds=None):
    s = song(body)
    tl = expand(s).timeline
    p = bn.plan(s, tl)
    n = int((seconds or tl.seconds) * SR)
    music = 0.1 * np.sin(2 * np.pi * 440 * np.arange(n) / SR)[:, None] * np.ones((1, 2))
    return p, music, bn.render_layer(p, tl, n, music, SR)


def test_each_ear_hears_one_exact_steady_tone():
    p, music, y = layer("binaural A3 A3*phi beat=10 fade=0 glide=0.1\nx 4 | pad:warm\n")
    seg = y[2 * SR:12 * SR]
    for ch, sign in ((0, -1), (1, 1)):
        assert peak(seg[:, ch], 200, 240) == pytest.approx(220 + sign * 5, abs=0.02)
        assert peak(seg[:, ch], 340, 370) == pytest.approx(220 * PHI + sign * 5 / PHI, abs=0.02)
    # no beat inside one ear: a lone A3 pair's envelope is flat (the beat exists only between the ears)
    _, _, y1 = layer("binaural A3 beat=10 fade=0\nx 4 | pad:warm\n")
    from scipy.signal import hilbert
    env = np.abs(hilbert(y1[2 * SR:12 * SR, 0]))
    assert env[SR:-SR].std() / env[SR:-SR].mean() < 0.01


def test_level_is_relative_to_the_music_and_changes_never_click():
    p, music, y = layer("binaural A3 E4 beat=16 level=-12 glide=1 breathe=2\na 2 | pad:warm\n"
                        "b 2 | pad:warm binaural={carriers: [A3, \"^F4\"], beat: 6}\n")
    assert lufs(y) - lufs(music) == pytest.approx(-12, abs=0.05)
    step = np.abs(np.diff(y, axis=0)).max()
    assert step < 2 * np.pi * 400 / SR * np.abs(y).max()          # no jump bigger than a 400 Hz sine's slope


def test_carve_replaces_the_music_at_each_carrier():
    s = song("binaural A3 beat=10 fade=0\nx 4 | pad:warm\n")
    tl = expand(s).timeline
    p = bn.plan(s, tl)
    n = int(tl.seconds * SR)
    t = np.arange(n) / SR
    music = (0.1 * np.sin(2 * np.pi * 220 * t) + 0.1 * np.sin(2 * np.pi * 440 * t))[:, None] * np.ones((1, 2))
    out = music - bn.carve(p, music, SR)
    seg = slice(3 * SR, 13 * SR)
    X = lambda x, hz: np.abs(np.fft.rfft(x[seg, 0] * np.hanning(10 * SR)))[int(round(hz * 10))]   # noqa: E731
    assert X(out, 220) < 1e-3 * X(music, 220)            # the held A3 is gone (it would beat at 5 Hz per ear)
    assert X(out, 440) == pytest.approx(X(music, 440), rel=1e-3)     # an octave away nothing changes


def test_the_layer_renders_as_a_dry_stem():
    from songmap.render import render
    r = render(song("binaural A3 beat=8 level=-10\ninst host=clean/organ\nx 2 | host:{notes: \"a-1\"}\nmaster clean\n"))
    assert "binaural" in r.stems and r.stats["binaural"][0]["beats_hz"] == [[8.0, 8.0]]
    seg = r.audio[int(1.5 * SR):int(5.5 * SR)]
    assert peak(seg[:, 0], 210, 230) == pytest.approx(216, abs=0.05)
    assert peak(seg[:, 1], 210, 230) == pytest.approx(224, abs=0.05)


def test_round_trips_through_sm_and_yaml():
    s = song('binaural A3 A3*phi beat=16.18 level=-11 fade=6 glide=4 breathe=2 breath=3 carve=false\n'
             'a 2 | pad:warm beat=16.18>10\nb 2 | pad:warm binaural={carriers: [A3, "A4*phi^-1"], gain_db: -3}\n')
    want = fmt.song_to_raw(s)
    sm = fmt.to_sm(s)
    assert "binaural A3 A3*phi beat=16.18 level=-11" in sm and "beat=16.18>10" in sm
    assert fmt.song_to_raw(lang.loads(sm, "p.sm")) == want
    assert fmt.song_to_raw(yaml_form.from_raw(yaml_form.load_raw_text(fmt.to_yaml(s)), "p.yaml")) == want


def test_yaml_section_shorthand_is_the_beat():
    raw = {"songmap": 0.2, "title": "Y", "key": "A", "binaural": {"carriers": ["A3"]},
           "sections": [{"name": "a", "bars": 2, "parts": {"pad": "warm"}, "binaural": 6.18}]}
    s = yaml_form.from_raw(raw, "y.yaml")
    assert s.sections[0].binaural == {"beat": 6.18}


def test_the_ear_hears_a_carrier_that_rubs_the_harmony():
    rep = listen(expand(song("binaural A3 ^E4\nx 4 | pad:warm chords=\"A:4\"\n")))
    assert any(f.kind == "binaural" and f.severity == "problem" and "^E4" in f.message for f in rep.findings)
    rep = listen(expand(song("binaural A3 E4\nx 4 | pad:warm chords=\"A:4\"\n")))
    assert not any(f.kind == "binaural" for f in rep.findings)
    assert rep.facts["binaural beats (Hz)"] == "6.18 10"


def test_cli_check_reports_the_layer(tmp_path, capsys):
    from songmap.cli import main
    p = tmp_path / "b.sm"
    p.write_text(HEAD + "binaural A3 beat=10>6.18\nx 2 | pad:warm\n", encoding="utf-8")
    assert main(["check", str(p)]) == 0
    assert "binaural (headphones): x: A3 220.00 Hz @ 10.00>6.18" in capsys.readouterr().out


STILL_WATER = sorted(glob.glob(os.path.join(ROOT, "songs", "still_water", "*.sm")))


@pytest.mark.parametrize("path", STILL_WATER, ids=[os.path.basename(p) for p in STILL_WATER])
def test_still_water_passes_the_ear_and_walks_the_ladder(path):
    s = lang.load(path)
    arr = expand(s)
    rep = listen(arr)
    assert rep.counts()["problem"] == 0 and rep.counts()["warning"] == 0, rep.text()
    rates = bn.beat_rates(bn.plan(s, arr.timeline))
    assert any(abs(r - 6.18) < 0.01 or abs(r - 10) < 0.01 for r in rates)


def test_still_water_is_one_continuous_layer():
    """Each song begins with the carriers and beat the previous one ended on (A3 never stops)."""
    plans = []
    for path in STILL_WATER:
        s = lang.load(path)
        plans.append(bn.plan(s, expand(s).timeline))
    for prev, nxt in zip(plans, plans[1:]):
        end, start = prev.states[-1], nxt.states[0]
        assert [round(c.hz, 2) for c in end.carriers] == [round(c.hz, 2) for c in start.carriers]
        assert end.beat[1] == pytest.approx(start.beat[0], abs=0.01)
        assert all(round(st.carriers[0].hz, 6) == 220.0 for p in plans for st in p.states)


def test_an_unquoted_microtone_in_a_section_map_says_where_and_how():
    with pytest.raises(SongError) as e:
        song("binaural A3\nx 2 | pad:warm binaural={carriers: [A3, ^F4]}\n")
    assert "b.sm:3" in str(e.value) and '"^F4"' in str(e.value)
