"""Checks at the new sample/renderer boundary, independent of downloaded libraries."""
import hashlib
import io
import zipfile

import numpy as np
import pytest

from songmap.instruments import Note
from songmap.instruments.sampler import Sampler, sfz


def test_velocity_curve_keeps_soft_recordings_at_their_recorded_level(tmp_path):
    p = tmp_path / "bass.sfz"
    p.write_text("<global> amp_velcurve_40=1\n<region> key=36 hivel=40 sample=soft.wav")
    s = Sampler("test", sfz.parse(str(p)))
    r = s.program.regions[0]
    assert not s.warnings
    assert s._gain(r, Note(36, 40/127), 1) == pytest.approx(1)
    assert s._gain(r, Note(36, 20/127), 1) == pytest.approx(.5)
    assert s._gain(r, Note(36, 1), 1) == pytest.approx(1)


def test_sfz_panning_and_avl_aliases(tmp_path):
    p = tmp_path / "kit.sfz"
    p.write_text("<group> key=42 lochan=1 hichan=16 pan=-100 offby=1 off_mode=fast group=1\n"
                 "<region> sample=hat.wav loop_mode=one_shot")
    s = Sampler("test", sfz.parse(str(p)))
    r = s.program.regions[0]
    assert not s.warnings and s.choke(Note(42)) == (1, 1)
    y = s._pan(np.ones((100, 1)), r.pan)
    assert y.shape == (100, 2) and np.max(abs(y[:, 1])) < 1e-10
    assert np.max(abs(y[:, 0])) > .9


def test_archive_is_pinned_and_never_extracts_traversal(tmp_path, monkeypatch):
    from songmap.instruments.sampler import install
    from songmap.parse.errors import SongError
    def archive(name):
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            z.writestr(name, b"test bytes")
        return b.getvalue()
    data = archive("kit/tone.wav")
    monkeypatch.setattr(install, "_read", lambda _: data)
    source = {"archive": "https://example.com/kit.zip", "sha256": "0" * 64}
    with pytest.raises(SongError, match="integrity"):
        install._archive(source, tmp_path / "pack", tmp_path, {"files": {}})
    assert not (tmp_path / "pack").exists()
    data = archive("../escaped.wav")
    source["sha256"] = hashlib.sha256(data).hexdigest()
    with pytest.raises(SongError, match="escapes"):
        install._archive(source, tmp_path / "pack", tmp_path, {"files": {}})
    assert not (tmp_path / "escaped.wav").exists()


def test_verified_archive_repairs_corrupted_local_audio(tmp_path, monkeypatch):
    from songmap.instruments.sampler import install
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("kit/tone.wav", b"original")
    data = b.getvalue()
    monkeypatch.setattr(install, "_read", lambda _: data)
    source = {"archive": "https://example.com/kit.zip", "sha256": hashlib.sha256(data).hexdigest()}
    receipt = {"files": {}}
    install._archive(source, tmp_path / "pack", tmp_path, receipt)
    target = tmp_path / "pack/kit/tone.wav"
    target.write_bytes(b"wrong")
    monkeypatch.setattr(install, "_read", lambda _: pytest.fail("verified ZIP should be reused"))
    install._archive(source, tmp_path / "pack", tmp_path, receipt)
    assert target.read_bytes() == b"original"
    assert receipt["files"]["pack/kit/tone.wav"]["archive_sha256"] == source["sha256"]


def test_shared_kit_programs_have_distinct_studio_cache_keys(tmp_path, monkeypatch):
    from songmap.instruments.sampler import library
    from songmap.render import inst_key
    monkeypatch.setattr(library, "manifest", lambda: {"voices": {
        "kick": {"family": "drum", "audition_pitch": 36},
        "hat": {"family": "drum", "audition_pitch": 42}}})
    p = sfz.Program(str(tmp_path / "kit.sfz"), [])
    a, b = Sampler("kick", p), Sampler("hat", p)
    monkeypatch.setattr(library, "license_entry", lambda *args: {"program": p.path})
    assert inst_key(a) != inst_key(b)


def test_sampler_take_counter_does_not_restart_at_eight(make_song, monkeypatch):
    from songmap.arrange.ensemble import Ensemble
    from songmap.render import render
    from songmap.instruments import make
    inst = make("bass/sub")
    inst.program = object()       # renderer contract for a sampled voice
    counters = []
    original = inst.render
    def observed(note):
        counters.append(note.rr)
        return original(note)
    inst.render = observed
    monkeypatch.setattr(Ensemble, "instrument", lambda *args: inst)
    song = make_song({"mood": "v0", "harmony": {"default": ["C"]},
                      "sections": [{"name": "a", "bars": 2, "parts": {"bass": "eighths"}}]})
    render(song)
    assert counters == list(range(16))


def test_studio_auditions_apply_the_same_hat_chokes_as_song_renders(tmp_path, monkeypatch, make_song):
    sf = pytest.importorskip("soundfile")
    from songmap.gui.rack import audition
    from songmap.instruments.sampler import library
    monkeypatch.setattr(library, "roots", lambda: [str(tmp_path)])
    sf.write(tmp_path / "hat.wav", np.ones(24000) * .2, 48000)
    (tmp_path / "test.sfz").write_text("<region> sample=hat.wav key=42 loop_mode=one_shot group=1 off_by=1 amp_veltrack=0")
    song = make_song({"instruments": {"drums": {"kit": {"hat": "sampler/test"}}},
                      "sections": [{"name": "a", "bars": 1, "parts": {}}]})
    y = audition(song, "drums", [{"t": 0, "pitch": 42}, {"t": .1, "pitch": 42}], piece="hat")
    assert np.max(abs(y[9600:14400])) == pytest.approx(.2, abs=1e-4)  # no overlapping first hit
