"""Publication boundaries for the sampled textbook edition."""
import hashlib
import importlib
from pathlib import Path
import sys

import pytest
import yaml

TOOLS = Path(__file__).resolve().parents[1] / "tools/textbook"


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(TOOLS))
    return tuple(importlib.import_module(n) for n in ("audio_editions", "refresh_audio", "songbook"))


@pytest.mark.parametrize("mapping", ["{keys: clean/keys}", "\n  keys: clean/keys"])
def test_edit_preserves_written_music_and_comments(modules, mapping):
    _, refresh, _ = modules
    text = ("# listening intent\ntitle: Example\ninstruments: " + mapping +
            "\n# keep the phrase\nsections:\n  - {name: phrase, bars: 2, parts: {keys: comp}}\nmaster: clean\n")
    result = refresh.replace_mapping(text, "instruments", {"keys": "sampler/grand_piano"})
    before, after = yaml.safe_load(text), yaml.safe_load(result)
    assert after["instruments"] == {"keys": "sampler/grand_piano"}
    assert after["sections"] == before["sections"] and after["master"] == before["master"]
    assert "# listening intent" in result and "# keep the phrase" in result


def test_notation_reuse_requires_cached_preimage_and_identical_timing(modules, tmp_path, monkeypatch):
    editions, _, _ = modules
    monkeypatch.setattr(editions, "ROOT", tmp_path)
    source = tmp_path / "textbook/audio/ch01/example.songmap.yaml"
    source.parent.mkdir(parents=True)
    original = ("songmap: 0.2\ntitle: Example\ntempo: 120\nmeter: 4/4\nkey: C\n"
                "instruments: {keys: clean/keys}\nsections:\n"
                "  - {name: a, bars: 1, harmony: 'C:1', parts: {keys: hold}}\nmaster: clean\n")
    source.write_text(original)
    backup = tmp_path / "build/textbook_originals/textbook/audio/ch01/example.songmap.yaml"
    backup.parent.mkdir(parents=True)
    backup.write_text(original)
    old_cache = hashlib.sha1(backup.read_bytes()).hexdigest() + "|old-renderer"
    source.write_text(original.replace("clean/keys", "sampler/grand_piano"))
    assert editions.reusable_notation(source, old_cache)
    assert not editions.reusable_notation(source, "unrelated-video")
    source.write_text(original.replace("tempo: 120", "tempo: 90"))
    assert not editions.reusable_notation(source, old_cache)
    source.write_text(original)
    from songmap.visual.view import path_for
    Path(path_for(str(source))).write_text("theme: dark\n")
    assert not editions.reusable_notation(source, old_cache)


def test_songbook_renders_shared_edition_once(modules, monkeypatch):
    _, _, book = modules
    monkeypatch.setattr(book, "engine_hash", lambda: "engine")
    calls = []
    def job(args):
        calls.append(args)
        return args[0]["path"], "rendered", None
    monkeypatch.setattr(book, "_render_job", job)
    result = book.render_all([{"name": "song", "hash": "same", "path": "original"},
                              {"name": "song", "hash": "same", "path": "sampled"}], jobs=1)
    assert len(calls) == 1
    assert result == {"original": "rendered", "sampled": "rendered"}


def test_songbook_render_failure_blocks_publication(modules, monkeypatch):
    _, _, book = modules
    monkeypatch.setattr(book, "collections", lambda: [{"songs": ["broken"]}])
    monkeypatch.setattr(book, "entry", lambda _: {"rel": "broken", "error": "failed"})
    monkeypatch.setattr(book, "render_all", lambda *args: {})
    with pytest.raises(RuntimeError, match="not ready to publish"):
        book.chapter(render=True)


def test_overlapping_builds_publish_a_complete_cache_without_shared_work_files(modules, tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    import songmap.render as renderer
    _, _, book = modules
    monkeypatch.setattr(book, "CACHE", str(tmp_path / "cache"))
    source = tmp_path / "demo.sm"
    source.write_text('song "Demo" 120 4/4 C\nphrase 1 | keys:comp\n')
    monkeypatch.setattr(renderer, "render", lambda song: object())
    barrier, work_dirs = Barrier(2), []
    def outputs(result, folder, **kwargs):
        work_dirs.append(folder)
        barrier.wait(timeout=10)
        for name in ("song.wav", "song.mp3", "qa.json", "review.json", "qa.png", "render.log"):
            Path(folder, name).write_bytes(b"complete")
    monkeypatch.setattr(renderer, "write_outputs", outputs)
    entry = {"name": "demo", "hash": "same", "path": str(source)}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: book.render_cached(entry, "engine"), range(2)))
    assert len(set(work_dirs)) == 2 and results[0] == results[1]
    assert Path(results[0], "song.mp3").read_bytes() == b"complete"
    assert Path(results[0], "render.log").read_bytes() == b"complete"
    assert not Path(results[0], "song.wav").exists()


def test_audio_cache_ignores_gui_and_video_but_tracks_sound_sources(modules, tmp_path, monkeypatch):
    editions, _, _ = modules
    monkeypatch.setattr(editions, "ROOT", tmp_path)
    sound = tmp_path / "songmap/instruments/tone.py"
    screen = tmp_path / "songmap/visual/video.py"
    for p in (sound, screen):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("original")
    editions.audio_engine_hash.cache_clear()
    try:
        first = editions.audio_engine_hash()
        screen.write_text("new layout")
        editions.audio_engine_hash.cache_clear()
        assert editions.audio_engine_hash() == first
        sound.write_text("new waveform")
        editions.audio_engine_hash.cache_clear()
        assert editions.audio_engine_hash() != first
    finally:
        editions.audio_engine_hash.cache_clear()


def test_published_urls_track_finished_audio_bytes(modules, tmp_path):
    editions, _, _ = modules
    media = tmp_path / "audio/example.mp3"
    page = tmp_path / "chapters/example.html"
    media.parent.mkdir()
    page.parent.mkdir()
    media.write_bytes(b"old recording")
    page.write_text('<audio src="../audio/example.mp3?v=planned"></audio>')
    editions.stamp_media_urls(tmp_path)
    first = page.read_text()
    assert hashlib.sha256(media.read_bytes()).hexdigest()[:12] in first
    media.write_bytes(b"new recording")
    editions.stamp_media_urls(tmp_path)
    assert page.read_text() != first
    assert hashlib.sha256(media.read_bytes()).hexdigest()[:12] in page.read_text()
