"""Chapter video sidecars affect both the rendered view and its media cache identity."""
import importlib.util
from pathlib import Path


def test_textbook_media_hash_tracks_view_changes(tmp_path):
    source = Path(__file__).resolve().parents[1] / "tools/textbook/build.py"
    spec = importlib.util.spec_from_file_location("textbook_build", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    song = tmp_path / "example.songmap.yaml"
    song.write_text("title: Example\n")
    original = module.file_hash(str(song))
    view = tmp_path / "example.songmap.view.yaml"
    view.write_text("theme: dark\n")
    dark = module.file_hash(str(song))
    assert dark != original
    view.write_text("theme: light\n")
    assert module.file_hash(str(song)) not in (original, dark)
