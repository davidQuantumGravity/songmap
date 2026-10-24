"""Sampler backend (SFZ subset) on a tiny synthetic library of generated sine samples."""
import os

import numpy as np
import pytest
from scipy.signal import butter, sosfilt

sf = pytest.importorskip("soundfile")

import songmap.instruments as I  # noqa: E402
from songmap.instruments.dsp import SR, mtof  # noqa: E402
from songmap.instruments.sampler import Sampler, sfz  # noqa: E402
from songmap.parse.errors import SongError  # noqa: E402
from songmap.render import _apply_chokes, render, write_outputs  # noqa: E402

SFZ = r"""
// tiny test program: comments, #define, inheritance, note names, backslash paths
#define $REL 0.25
<control> default_path=wav\
<global> amp_veltrack=0 ampeg_release=$REL
<group> lokey=c4 hikey=b4 pitch_keycenter=60
<region> sample=soft c4.wav lovel=1 hivel=63
<region> sample=hard c4.wav lovel=64 hivel=127 volume=-6
<group> lokey=48 hikey=59 pitch_keycenter=c3
<region> sample=low.wav
<group> key=72 seq_length=2
<region> sample=rr1.wav seq_position=1
<region> sample=rr2.wav seq_position=2
<group> trigger=release lokey=48 hikey=72 pitch_keytrack=0 rt_decay=0 xfin_lovel=1 cutoff=4000
<region> sample=rel.wav
<group> amp_veltrack=0
<region> sample=open.wav key=84 group=1 off_by=2 ampeg_release=1
<region> sample=closed.wav key=86 group=2
"""


def _sine(f, secs=1.0, sr=44100, amp=0.5, harm=0.0):
    t = np.arange(int(secs * sr)) / sr
    # start at the crest (cos) and end abruptly: the sampler must ramp both ends itself
    return (amp * (np.cos(2 * np.pi * f * t) + harm * np.cos(2 * np.pi * 3 * f * t))).astype(np.float32)


@pytest.fixture(scope="module")
def lib(tmp_path_factory):
    root = tmp_path_factory.mktemp("samples")
    d = root / "testlib"
    (d / "wav").mkdir(parents=True)
    c4 = float(mtof(60))
    files = {"soft c4.wav": _sine(c4, amp=0.2), "hard c4.wav": _sine(c4, amp=0.8, harm=0.5),
             "low.wav": _sine(float(mtof(48))), "rr1.wav": _sine(float(mtof(72))),
             "rr2.wav": _sine(float(mtof(72)), harm=0.8), "rel.wav": _sine(1000.0, secs=0.2, amp=0.3),
             "open.wav": _sine(3000.0, secs=2.0), "closed.wav": _sine(5000.0, secs=0.1)}
    for name, x in files.items():
        sf.write(str(d / "wav" / name), x, 44100)
    (d / "testlib.sfz").write_text(SFZ, encoding="utf-8")
    (d / "LICENSE.txt").write_text("CC0 test tones\n", encoding="utf-8")
    return root


@pytest.fixture
def inst(lib, monkeypatch):
    monkeypatch.setenv("SONGMAP_SAMPLES", str(lib))
    return I.make("sampler/testlib")


def _peak_hz(y, sr=SR):
    m = y.mean(1) if y.ndim == 2 else y
    m = m[: sr // 2] * np.hanning(min(len(m), sr // 2))
    s = np.abs(np.fft.rfft(m, 8 * len(m)))
    return np.fft.rfftfreq(8 * len(m), 1 / sr)[np.argmax(s)]


def _samples(inst, note):
    return [os.path.basename(r.sample) for r, _ in inst.regions(note)]


def test_parser_subset(lib):
    p = sfz.parse(str(lib / "testlib" / "testlib.sfz"))
    soft = next(r for r in p.regions if r.sample.endswith("soft c4.wav"))
    assert os.path.isfile(soft.sample)                                   # default_path + backslash + spaces
    assert (soft.lokey, soft.hikey, soft.pitch_keycenter) == (60, 71, 60)  # note names, group inheritance
    assert soft.ampeg_release == 0.25 and soft.amp_veltrack == 0          # #define, <global>
    low = next(r for r in p.regions if r.sample.endswith("low.wav"))
    assert (low.lokey, low.hikey, low.pitch_keycenter) == (48, 59, 48)
    rr = [r for r in p.regions if r.seq_length == 2]
    assert [(r.lokey, r.hikey, r.seq_position) for r in rr] == [(72, 72, 1), (72, 72, 2)]
    assert [r.is_release for r in p.regions].count(True) == 1
    assert "cutoff" in p.unsupported                                     # reported, not silently wrong


def test_region_selection_by_key_and_float_pitch(inst):
    assert _samples(inst, I.Note(50, 0.7, 0.3)) == ["low.wav"]
    assert _samples(inst, I.Note(65, 0.2, 0.3)) == ["soft c4.wav"]
    assert _samples(inst, I.Note(40, 0.7, 0.3)) == []
    for pitch in (50.0, 62.0, 60 + 1 / 3):                              # 36edo step: repitched, not snapped
        f = _peak_hz(inst.render(I.Note(pitch, 0.2, 0.6)))
        assert abs(1200 * np.log2(f / float(mtof(pitch)))) < 3, pitch


def test_velocity_layers_crossfade(inst):
    def w(vel, x=None):
        s = inst if x is None else I.make("sampler/testlib", xfade=x)
        return {os.path.basename(r.sample): g for r, g in s.regions(I.Note(60, vel, 0.3))}
    assert w(0.1) == {"soft c4.wav": 1.0} and w(1.0) == {"hard c4.wav": 1.0}
    mid = w(63.5 / 127)
    assert mid["soft c4.wav"] == pytest.approx(np.sqrt(0.5)) and mid["hard c4.wav"] == pytest.approx(np.sqrt(0.5))
    vels = np.linspace(0.3, 0.7, 41)
    hard = [w(v).get("hard c4.wav", 0.0) for v in vels]
    assert np.all(np.diff(hard) >= -1e-12) and 0 < hard[20] < 1        # monotone blend, not a step
    for v in vels:
        assert sum(g * g for g in w(v).values()) == pytest.approx(1.0)    # equal power
    assert set(w(0.49, x=0)) == {"soft c4.wav"} and set(w(0.51, x=0)) == {"hard c4.wav"}
    # the rendered level moves smoothly through the crossfade (no jump between neighbours)
    rms = [np.sqrt(np.mean(inst.render(I.Note(60, v, 0.3))[:9000] ** 2)) for v in vels]
    assert np.max(np.abs(np.diff(np.log(rms)))) < 0.15


def test_round_robin_cycles_with_the_slot(inst):
    names = [_samples(inst, I.Note(72, 0.7, 0.3, rr=k)) for k in range(4)]
    assert names == [["rr1.wav"], ["rr2.wav"], ["rr1.wav"], ["rr2.wav"]]
    a, b = (inst.render(I.Note(72, 0.7, 0.3, rr=k)) for k in (0, 1))
    assert not np.allclose(a, b)
    assert np.array_equal(a, inst.render(I.Note(72, 0.7, 0.3, rr=2)))


def test_release_sample_on_note_off(inst):
    gate = 0.4
    g = int(gate * SR)

    def tone_1k(y, a, b):
        seg = y[a:b]
        t = np.arange(len(seg)) / SR
        return abs(np.sum(seg * np.exp(-2j * np.pi * 1000 * t))) / len(seg)
    y = inst.render(I.Note(48, 0.7, gate))
    assert tone_1k(y, g + 200, g + 4000) > 20 * tone_1k(y, 2000, g - 200)   # starts at note-off
    assert len(y) >= g + int(0.19 * SR)                                     # plays the whole release sample
    quiet = I.make("sampler/testlib", release_level=0).render(I.Note(48, 0.7, gate))
    assert tone_1k(quiet, g + 200, g + 4000) < 0.05 * tone_1k(y, g + 200, g + 4000)


def _hf_click(y, edge="start", pad=512):
    m = y.mean(1) if y.ndim == 2 else y
    x = np.concatenate([np.zeros(pad), m, np.zeros(pad)])
    hp = sosfilt(butter(4, 8000, "hp", fs=SR, output="sos"), x)
    i = pad if edge == "start" else pad + len(m)
    body = np.sqrt(np.mean(m[: 4800] ** 2)) + 1e-12
    return np.sqrt(np.mean(hp[i - 64:i + 64] ** 2)) / body


def test_no_clicks_at_note_start_and_end(inst, lib):
    raw, _ = sf.read(str(lib / "testlib" / "wav" / "low.wav"))
    assert _hf_click(raw[:20000]) > 0.05                                    # the detector does hear a raw edge
    for note in (I.Note(50, 0.7, 0.5), I.Note(60, 1.0, 0.05), I.Note(72, 0.5, 0.5, rr=1),
                 I.Note(50, 0.7, 3.0)):                                    # 3 s gate outlasts the 1 s sample
        y = inst.render(note)
        assert abs(y[0]).max() < 1e-6 and abs(y[-1]).max() < 1e-4
        assert _hf_click(y, "start") < 0.01 and _hf_click(y, "end") < 0.01, note


def test_choke_group(inst):
    open_, closed = I.Note(84, 0.7, 1.0), I.Note(86, 0.7, 0.05)
    assert inst.choke(open_) == (1, 2) and inst.choke(closed) == (2, 0)
    y_open, y_closed = inst.render(open_), inst.render(closed)
    placed = [[0, y_open, 1.0, 0.0, *inst.choke(open_)], [12000, y_closed, 1.0, 0.0, *inst.choke(closed)]]
    _apply_chokes(placed)
    cut = placed[0][1]
    assert len(cut) == 12000 and abs(cut[-1]) < 1e-3 and len(y_open) > 40000
    assert len(placed[1][1]) == len(y_closed)                                # the choker is untouched


def test_missing_library_says_where_to_download(tmp_path, monkeypatch):
    monkeypatch.setenv("SONGMAP_SAMPLES", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SongError) as e:
        I.make("sampler/salamander")
    assert "freepats" in e.value.suggestion and "CC BY" in e.value.suggestion
    with pytest.raises(SongError) as e:
        I.make("sampler/whatever")
    assert "VSCO-2" in e.value.suggestion and "CC0" in e.value.suggestion
    with pytest.raises(I.ParamError, match="needs a library"):
        I.make("sampler")


def test_song_swaps_in_the_sampler(lib, monkeypatch, make_song, tmp_path):
    monkeypatch.setenv("SONGMAP_SAMPLES", str(lib))
    song = {"title": "s", "key": "C major", "tail_seconds": 1, "instruments": {"lead": "sampler/testlib"},
            "motifs": {"m": {"deg": "0 2 4 2"}},
            "sections": [{"name": "a", "bars": 1, "parts": {"lead": ["m"]}}]}
    r = render(make_song(song))
    assert np.all(np.isfinite(r.audio)) and np.max(np.abs(r.stems["lead"])) > 0.01
    assert r.stats["samples"] == ["sampler/testlib"]
    assert any("cutoff" in w for w in r.song.warnings)
    paths = write_outputs(r, str(tmp_path / "out"), stems=False)
    text = open(paths["licenses"], encoding="utf-8").read()
    assert "sampler/testlib" in text and "LICENSE.txt" in text and "unknown" in text
    monkeypatch.setenv("SONGMAP_SAMPLES", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SongError, match="instruments lead: sampler library 'testlib' not found"):
        render(make_song(song))


def test_sampler_schema_is_an_instrument():
    s = Sampler.schema()
    assert s["name"] == "sampler" and {"xfade", "release_level", "tune"} <= {p["name"] for p in s["params"]}
