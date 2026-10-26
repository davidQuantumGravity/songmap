"""Patch instruments: modules and wires, the `patch` directive, the library, fmt round trips, Studio edits."""
import numpy as np
import pytest

from songmap.arrange.expand import expand
from songmap.gui.project import parse_text
from songmap.gui.rack import set_patch, voices
from songmap.instruments import Note
from songmap.instruments.base import ParamError
from songmap.instruments import REGISTRY
from songmap.instruments.patch import MODULES, build, library, raw_spec, validate
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


# ---------------------------------------------------------------------------------------------- waveguides, wavetables
def _pitch(y, hz):
    from songmap.instruments.dsp.waveguide import _sustained_pitch
    env = np.ones(len(y))
    return _sustained_pitch(y, env, hz)


@pytest.mark.parametrize("mode", ["bow", "reed", "flute"])
@pytest.mark.parametrize("pitch", [57, 64, 69, 76])
def test_waveguides_speak_in_tune(mode, pitch):
    spec = {"modules": {"w": {"type": "waveguide", "mode": mode, "attack": 0.03}, "out": {"type": "out", "tail": 0.05}},
            "wires": ["w>out"]}
    y = build("w", spec).render(Note(pitch, 0.7, 1.0, seed=1))
    seg = y[int(0.2 * 48000):int(0.9 * 48000)]
    assert np.sqrt(np.mean(seg ** 2)) > 0.05                     # it keeps sounding while held
    hz = 440 * 2 ** ((pitch - 69) / 12)
    got = _pitch(seg, hz)
    assert got and abs(1200 * np.log2(got / hz)) < 10           # in tune (measured and corrected per note)


def test_pressure_changes_the_tone():
    def centroid(mode, pressure):
        spec = {"modules": {"w": {"type": "waveguide", "mode": mode, "pressure": pressure}, "out": {"type": "out"}},
                "wires": ["w>out"]}
        y = build("w", spec).render(Note(57 if mode != "flute" else 69, 0.7, 1.0, seed=1))[12000:40000]
        sp = np.abs(np.fft.rfft(y * np.hanning(len(y)))) ** 2
        return (sp * np.arange(len(sp))).sum() / sp.sum()
    assert centroid("bow", 0.5) > 1.2 * centroid("bow", 0.1)          # a barely touching bow is airy and dark
    for mode in ("bow", "reed", "flute"):
        assert abs(centroid(mode, 0.9) - centroid(mode, 0.3)) > 0.03 * centroid(mode, 0.3), mode


def test_wavetables_are_band_limited_and_scan():
    from songmap.instruments.dsp.waveguide import TABLES, wavetable
    n = 48000
    for k in range(len(TABLES)):
        y = wavetable(k, np.full(n, 3000.0), np.linspace(0, 1, n))
        sp = np.abs(np.fft.rfft(y * np.hanning(n)))                         # windowed: no leakage
        f = np.fft.rfftfreq(n, 1 / 48000)
        assert np.isfinite(y).all() and np.abs(y).max() <= 1.0 + 1e-9
        assert sp[f > 21600].sum() < 1e-4 * sp.sum(), TABLES[k]          # nothing above Nyquist (below -80 dB)
    first, last = (wavetable(0, np.full(n, 220.0), np.full(n, p)) for p in (0.0, 1.0))
    assert np.allclose(first, first.max() * np.sin(2 * np.pi * 220 * np.arange(1, n + 1) / 48000), atol=1e-6)
    sp = np.abs(np.fft.rfft(last))
    assert sp[np.argmin(np.abs(np.fft.rfftfreq(n, 1 / 48000) - 660))] > 0.2 * sp.max()     # the square's 3rd


# ---------------------------------------------------------------------------------------------- formulas
def test_formula_knobs_follow_the_note():
    spec = {"modules": {"o": {"type": "osc", "wave": "saw"}, "f": {"type": "filter", "cutoff": "300*2**(3*vel)"},
                        "out": {"type": "out"}}, "wires": ["o>f", "f>out"]}
    inst = build("f", spec)
    assert "f.cutoff" not in {q.name for q in inst.PARAMS}             # a formula is not a param

    def centroid(v):
        y = inst.render(Note(48, v, 0.5, seed=1))[2000:20000]
        sp = np.abs(np.fft.rfft(y * np.hanning(len(y)))) ** 2
        return (sp * np.arange(len(sp))).sum() / sp.sum()
    assert centroid(1.0) > 1.5 * centroid(0.2)
    moving = {"modules": {"o": {"type": "osc", "wave": "square", "pw": "0.5+0.4*sin(2*pi*2*t)"}, "out": {"type": "out"}},
              "wires": ["o>out"]}
    y = build("m", moving).render(Note(60, 0.7, 1.0, seed=1))
    assert np.isfinite(y).all() and np.abs(y).max() > 0.1


@pytest.mark.parametrize("bad, msg", [("300*velo", "did you mean vel"), ("__import__('os')", "unknown function"),
                                      ("vel.real", "can't"), ("lambda: 1", "can't"), ("open('x')", "unknown function"),
                                      ("1 +", "not a formula"), ("[1, 2]", "can't")])
def test_formulas_are_safe_and_explained(bad, msg):
    with pytest.raises(ParamError, match=msg):
        validate({"modules": {"f": {"type": "filter", "cutoff": bad}, "out": {"type": "out"}}, "wires": ["f>out"]})


def test_formulas_and_new_modules_in_a_song_round_trip():
    song = """song "Bowed" 72 4/4 Dm fps=30 seed=7 tail=1
chords Dm Bb
patch cello w=waveguide(pressure="0.35+0.5*vel", position=.11) f1=filter(cutoff="clip(700*2**(2*vel+key), 200, 9000)") out=out
patch cello w>f1 f1>out
patch vox o=wavetable(table=vowel, position="0.5+0.5*sin(2*pi*0.25*t)") out=out | o>out
inst cello=patch/cello pad=patch/vox lead=patch/clarinet
verse 2 | cello:{deg: "=mf 0/2 2 | 4/1"} pad:hold lead:{deg: "=mp 4/2 5 | 6/1"}
"""
    s = parse_text(song, "b.sm")
    r = render(s)
    assert all(np.abs(r.stems[p]).max() > 0.01 for p in ("cello", "pad", "lead")) and np.isfinite(r.audio).all()
    text = to_sm(s)
    assert 'cutoff="clip(700*2**(2*vel+key), 200, 9000)"' in text
    for back in (parse_text(text, "b.sm"), parse_text(to_yaml(s), "b.yaml")):
        assert expand(back).digest() == expand(s).digest()
        assert {k: raw_spec(validate(v, k)) for k, v in back.patches.items()} == \
            {k: raw_spec(validate(v, k)) for k, v in s.patches.items()}
    with pytest.raises(SongError, match=r"b\.sm:3 .*did you mean clip"):
        parse_text(song.replace('"clip(', '"clipp('), "b.sm")
