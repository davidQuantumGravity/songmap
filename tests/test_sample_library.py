"""The curated library is useful before installation and shared by CLI and Studio."""
from pathlib import Path

import numpy as np
import pytest

from songmap.instruments import Note, make
from songmap.instruments.sampler import sfz


def test_curated_voices_have_install_state_and_musical_descriptions(tmp_path, monkeypatch):
    from songmap.instruments.sampler import library
    monkeypatch.setattr(library, "roots", lambda: [str(tmp_path)])
    entries = library.voices()
    assert len(entries) >= 12
    piano = next(v for v in entries if v["name"] == "grand_piano")
    assert piano["ref"] == "sampler/grand_piano" and piano["description"]
    assert piano["license"] == "CC0 1.0" and not piano["installed"]
    assert "songmap samples install" in piano["install"]


def test_explicit_velocity_fades_and_random_groups_do_not_double_layers(tmp_path):
    sf = pytest.importorskip("soundfile")
    from songmap.instruments.sampler import Sampler
    sf.write(tmp_path / "tone.wav", np.ones(4800) * .1, 48000)
    p = tmp_path / "voice.sfz"
    p.write_text("""<group> amp_veltrack=0
<region> sample=tone.wav xfout_lovel=60 xfout_hivel=100
<region> sample=tone.wav xfin_lovel=60 xfin_hivel=100
""")
    s = Sampler.from_sfz(str(p))
    assert len(s.regions(Note(60, .2))) == 1
    assert len(s.regions(Note(60, 1))) == 1
    assert sum(w*w for _, w in s.regions(Note(60, 80/127))) == pytest.approx(1)
    p.write_text("""<group> lorand=0 hirand=.5
<region> sample=tone.wav
<group> lorand=.5 hirand=1
<region> sample=tone.wav
""")
    s = Sampler("random", sfz.parse(str(p)))
    choices = [s.regions(Note(60, .7, seed=k))[0][0].lorand for k in range(30)]
    assert set(choices) == {0, .5}
    assert all(len(s.regions(Note(60, .7, seed=k))) == 1 for k in range(30))


def test_offset_decay_and_sustain_loop_are_rendered(tmp_path):
    sf = pytest.importorskip("soundfile")
    from songmap.instruments.sampler import Sampler
    x = np.r_[np.zeros(480), .2*np.sin(2*np.pi*440*np.arange(4800)/48000)]
    sf.write(tmp_path / "tone.wav", x, 48000, subtype="FLOAT")
    p = tmp_path / "voice.sfz"
    p.write_text("""<region> sample=tone.wav key=69 offset=480
loop_mode=loop_sustain loop_start=480 loop_end=5279
ampeg_attack=.001 ampeg_decay=.1 ampeg_sustain=50 ampeg_release=.05 amp_veltrack=0
""")
    s = Sampler.from_sfz(str(p))
    y = s.render(Note(69 + 1/3, 1, .7))
    assert not s.warnings
    assert np.max(np.abs(y[50:400])) > .05  # offset skipped the initial silence
    assert np.sqrt(np.mean(y[24000:29000]**2)) == pytest.approx(.2*.5/np.sqrt(2), rel=.05)
    assert abs(y[-1]) < 1e-4 and np.isfinite(y).all()


def test_sampler_programs_are_in_both_catalogs():
    from songmap.describe import catalog
    from songmap.gui.rack import catalog as gui_catalog
    assert "sampler/grand_piano" in catalog(compact=True)
    assert "sampler/flute" in catalog(compact=False)
    piano = next(s for s in gui_catalog()["samplers"] if s["name"] == "grand_piano")
    assert piano["ref"] == "sampler/grand_piano" and "installed" in piano


def test_installer_checks_upstream_bytes_and_detects_local_corruption(tmp_path, monkeypatch):
    import json
    from songmap.instruments.sampler import install as installer, library
    from songmap.parse.errors import SongError
    sf = pytest.importorskip("soundfile")
    sample = tmp_path / "input.wav"
    sf.write(sample, np.sin(np.arange(4800)*.1)*.1, 48000)
    files = {"voice.sfz": b"<region> sample=audio/tone.wav key=60", "audio/tone.wav": sample.read_bytes(),
             "README.md": b"Test fixture, CC0 1.0"}
    source = {"repo": "fixture/library", "revision": "a"*40, "license": "CC0 1.0", "credit": "Test", "url": "https://example.com"}
    manifest = {"sources": {"fixture": source}, "voices": {"test": {"source": "fixture", "program": "voice.sfz", "title": "Test", "family": "keys", "description": "test", "range": [60, 60]}}}
    monkeypatch.setattr(library, "manifest", lambda: manifest)
    tree = {"tree": [{"path": p, "type": "blob", "sha": installer._blob(data), "size": len(data)} for p, data in files.items()]}
    def read(url):
        if "api.github.com" in url:
            return json.dumps(tree).encode()
        return files[url.split(source["revision"] + "/")[1]]
    monkeypatch.setattr(installer, "_read", read)
    root = tmp_path / "samples"
    installer.install(["fixture"], root=root, log=lambda _: None)  # a source/kit selector expands its voices
    assert installer.verify(root)["ok"]
    monkeypatch.setenv("SONGMAP_SAMPLES", str(root))
    assert np.abs(make("sampler/test").render(Note(60))).max() > 0
    (root / "_packs/fixture/audio/tone.wav").write_bytes(b"corrupted")
    assert not installer.verify(root)["ok"]
    monkeypatch.setattr(installer, "_read", lambda url: json.dumps(tree).encode() if "api.github.com" in url else b"wrong bytes")
    with pytest.raises(SongError, match="integrity"):
        installer.install(root=root, log=lambda _: None)


def test_installer_rejects_sample_path_escape(tmp_path, monkeypatch):
    from songmap.instruments.sampler.install import _within
    from songmap.parse.errors import SongError
    with pytest.raises(SongError, match="escapes"):
        _within(tmp_path, tmp_path / "../outside.wav")


def test_curated_drum_maps_kit_pitch_and_one_shot_ignores_gate(tmp_path, monkeypatch):
    from songmap.instruments.sampler import Sampler, library
    sf = pytest.importorskip("soundfile")
    sf.write(tmp_path / "tone.wav", .2*np.sin(2*np.pi*440*np.arange(24000)/48000), 48000)
    p = tmp_path / "voice.sfz"
    p.write_text("<region> sample=tone.wav key=42 loop_mode=one_shot amp_veltrack=0")
    monkeypatch.setattr(library, "manifest", lambda: {"voices": {"drum": {"family": "drum", "audition_pitch": 42}}})
    s = Sampler("drum", sfz.parse(str(p)))
    library.SAMPLES.get(str(tmp_path / "tone.wav"), 50)   # decoding a prefix must not truncate one-shot playback
    a, b = s.render(Note(60, .7, .01)), s.render(Note(72, .7, .3))
    assert len(a) > 23000 and np.array_equal(a, b) and np.max(np.abs(a)) > .1
    assert abs(a[-1]).max() < 1e-4


def test_continuous_loop_keeps_playing_during_release(tmp_path):
    from songmap.instruments.sampler import Sampler
    sf = pytest.importorskip("soundfile")
    sf.write(tmp_path / "tone.wav", .2*np.sin(2*np.pi*440*np.arange(4800)/48000), 48000)
    lengths = {}
    for mode in ("loop_sustain", "loop_continuous"):
        path = tmp_path / (mode+".sfz")
        path.write_text(f"<region> sample=tone.wav key=69 loop_mode={mode} loop_start=0 loop_end=4799 ampeg_release=.05")
        y = Sampler.from_sfz(str(path)).render(Note(69, 1, .09))
        lengths[mode] = len(y)/48000
        assert np.isfinite(y).all() and abs(y[-1]).max() < 1e-4
    assert lengths["loop_sustain"] < .11
    assert lengths["loop_continuous"] > .13


def test_installer_network_failure_is_actionable(monkeypatch):
    import urllib.error
    from songmap.instruments.sampler import install as installer
    from songmap.parse.errors import SongError
    def offline(*args, **kwargs):
        raise urllib.error.URLError("offline")
    monkeypatch.setattr(installer.urllib.request, "urlopen", offline)
    monkeypatch.setattr(installer.time, "sleep", lambda _: None)
    with pytest.raises(SongError, match="could not download") as error:
        installer._read("https://example.com/source")
    assert "verified downloads are reused" in error.value.suggestion
