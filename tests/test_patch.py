"""Patch instruments: modules and wires, the `patch` directive, the library, fmt round trips, Studio edits."""
import numpy as np
import pytest

from songmap.arrange.expand import expand
from songmap.gui.project import parse_text
from songmap.gui.rack import set_patch, voices
from songmap.instruments import Note
from songmap.instruments.base import ParamError
from songmap.instruments import REGISTRY
from songmap.instruments.patch import MODULES, build, library, validate
from songmap.parse.errors import SongError
from songmap.parse.fmt import to_sm, to_yaml
from songmap.render import render

SONG = """song "P" 120 4/4 A fps=30 seed=4 tail=1
chords Am F C G
patch zap osc1=osc(wave=square, pw=.3) e=env(a=.002, d=.15, s=.2, r=.1) f1=filter(cutoff=900, q=6) amp=vca out=out
patch zap osc1>f1 e>f1.cutoff*2 vel>f1.cutoff f1>amp e>amp.gain amp>out
inst lead=patch/zap(f1.q=9) bass=patch/acid
kit snare=patch/snare808
verse 2 | lead:{deg: "=mf 4/8 2 0 2 4 5 4 2 | 0/2 r"} bass:sub drums:four_floor snare="....x.......x..."
"""


def test_every_library_patch_renders_every_module_type():
    used = set()
    for name, spec in library().items():
        v = validate(spec, name)
        used |= {m["type"] for m in v["modules"].values()}
        y = build(name, spec).render(Note(48, 0.8, 0.4, seed=1))
        assert np.isfinite(y).all() and 0 < np.abs(y).max() < 2, name
    rare = {"comb": {"type": "comb"}, "delay": {"type": "delay"}, "mix": {"type": "mix"}, "noise": {"type": "noise"}}
    spec = {"modules": {"n": {"type": "noise"}, "c": {"type": "comb"}, "d": {"type": "delay"}, "m": {"type": "mix"},
                        "s": {"type": "shaper", "fold": 0.5}, "out": {"type": "out"}},
            "wires": ["n>c", "c>d", "d>m", "m>s", "s>out", "rand>c.tune*2", "key>d.mix*.1"]}
    assert np.abs(build("rare", spec).render(Note(60, 0.7, 0.3, seed=2))).max() > 0
    assert used | set(rare) | {"shaper"} >= set(MODULES)


def test_velocity_wired_into_the_filter_changes_the_timbre():
    inst = build("acid", library()["acid"])
    soft, hard = (inst.render(Note(45, v, 0.4, seed=3)) for v in (0.2, 1.0))
    spec = lambda y: np.abs(np.fft.rfft(y[:8192]))           # noqa: E731
    centroid = lambda y: (spec(y) * np.arange(len(spec(y)))).sum() / spec(y).sum()   # noqa: E731
    assert centroid(hard) > centroid(soft) * 1.2


@pytest.mark.parametrize("spec, msg", [
    ({"modules": {"o": {"type": "osc"}}}, "needs an out"),
    ({"modules": {"o": {"type": "osk"}, "out": {"type": "out"}}}, "did you mean osc"),
    ({"modules": {"o": {"type": "osc", "wav": 1}, "out": {"type": "out"}}}, "did you mean wave"),
    ({"modules": {"e": {"type": "env"}, "out": {"type": "out"}}, "wires": ["e>out"]}, "control signal"),
    ({"modules": {"a": {"type": "vca"}, "b": {"type": "vca"}, "out": {"type": "out"}}, "wires": ["a>b", "b>a"]}, "loop"),
    ({"modules": {"o": {"type": "osc"}, "out": {"type": "out"}}, "wires": ["o>out.levle"]}, "did you mean level"),
])
def test_validation_explains(spec, msg):
    with pytest.raises(ParamError, match=msg):
        validate(spec)


def test_song_patches_render_round_trip_and_report_lines():
    song = parse_text(SONG, "p.sm")
    r = render(song)
    assert all(np.abs(r.stems[p]).max() > 0 for p in ("lead", "bass", "drums"))
    for text, name in ((to_sm(song), "p.sm"), (to_yaml(song), "p.yaml")):
        back = parse_text(text, name)
        assert expand(back).digest() == expand(song).digest() and set(back.patches) == {"zap"}
    with pytest.raises(SongError, match=r"p\.sm:3 .*did you mean 'osc'"):
        parse_text(SONG.replace("osc1=osc(", "osc1=osk("), "p.sm")
    with pytest.raises(SongError, match="no patch 'zapp'.*did you mean 'zap'"):
        parse_text(SONG.replace("patch/zap(", "patch/zapp("), "p.sm")


def test_studio_set_patch_and_voice_info():
    lib = library()["string_pluck"]
    t = set_patch(SONG, "mine", lib)
    assert "patch mine string=string(" in t
    arr = expand(parse_text(t.replace("bass=patch/acid", "bass=patch/mine"), "p.sm"))
    v = voices(arr.ensemble, arr.parts)
    assert v["bass"]["patch"] == "mine" and v["bass"]["patch_source"] == "song" and "string.t60" in v["bass"]["values"]
    assert v["drums"]["pieces"]["snare"]["patch_source"] == "library"
    assert set_patch(t, "mine", None) == SONG


def test_fm_and_macros():
    song = """song "F" 100 4/4 C fps=30 seed=1 tail=1
patch ep mod=osc(wave=sine, level=1) car=osc(wave=sine) env=env(d=2, s=.3) amp=vca out=out
patch ep mod>car car>amp env>amp.gain amp>out
patch ep @bark(default=.4, car.fm=.5..6, mod.level=.3..1)
inst keys=patch/ep(bark=.9)
verse 1 | keys:hold
"""
    s = parse_text(song, "f.sm")
    assert s.patches["ep"]["macros"]["bark"]["map"]["car.fm"] == [0.5, 6.0]
    assert "@bark(default=.4, car.fm=0.5..6, mod.level=0.3..1)" in to_sm(s)
    spec = s.patches["ep"]
    inst = build("ep", spec)
    assert inst.PARAMS[0].name == "bark" and "car.fm" in inst.PARAMS[0].doc

    def centroid(y):                                             # power-weighted, Hann-windowed (no leakage)
        sp = np.abs(np.fft.rfft(y[:16384] * np.hanning(16384))) ** 2
        return (sp * np.arange(len(sp))).sum() / sp.sum()
    dull, bright = (centroid(build("ep", spec, bark=b).render(Note(60, .7, .5, seed=1))) for b in (0, 1))
    assert bright > dull * 1.3                                   # FM depth (via the macro) adds harmonics
    with pytest.raises(ParamError, match="no knob 'fmm'"):
        validate({**spec, "macros": {"x": {"map": {"car.fmm": [0, 1]}}}})


def test_every_builtin_has_a_patch_sketch():
    lib = library()
    alias = {"snare": "snare808"}
    for name in REGISTRY:
        assert alias.get(name, name) in lib, f"no patch sketch of {name}"
