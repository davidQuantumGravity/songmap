"""`songmap describe`: the catalog is complete (built from the registries) and the compact one stays small."""
import os

import pytest

from songmap.arrange.events import EVENT_TYPES
from songmap.arrange.styles import catalog as style_catalog
from songmap.describe import catalog
from songmap.instruments import REGISTRY


def test_compact_catalog_names_everything_and_stays_small():
    c = catalog(compact=True)
    for role, names in style_catalog().items():
        assert f"{role}:" in c and all(n in c for n in names)
    assert all(n in c for n in REGISTRY) and all(t in c for t in EVENT_TYPES)
    assert "+hats16" in c and "8ths" in c and "STICKY" in c
    assert len(c) < 6000                     # grammar, synthesis presets and the expanded sample voice names


def test_full_catalog_has_descriptions_and_params():
    f = catalog(compact=False)
    assert "four-on-the-floor" in f and "cutoff=" in f and len(f) > len(catalog(compact=True))


def test_skill_bundles_the_current_catalog():
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, ".claude", "skills", "songmap-compose", "catalog.txt")
    with open(path, encoding="utf-8") as f:
        assert f.read() == catalog(compact=True), \
            "regenerate it: songmap describe --compact -o .claude/skills/songmap-compose/catalog.txt"


SKILL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".claude", "skills", "songmap-compose")
SNIPPET_HEAD = 'song "Snippet" 120 4/4 Am fps=30 seed=1 tail=1\nchords Am F C G\n'


def _blocks(path, tag=""):
    import re
    with open(path, encoding="utf-8") as f:
        return re.findall(r"```" + tag + r"\n(.*?)```", f.read(), re.S)


def test_skill_song_blocks_expand():
    from songmap.arrange.expand import expand
    from songmap.parse import lang
    blocks = [b for b in _blocks(os.path.join(SKILL, "SKILL.md")) if b.startswith("song ")]
    assert blocks
    for b in blocks:
        assert expand(lang.loads(b, "SKILL.md")).timeline.total_bars > 0


@pytest.mark.parametrize("name", ["emotion", "harmony", "melody", "rhythm", "instruments"])
def test_reference_snippets_expand(name):
    """Every ```sm block in the references is real: it compiles and expands under a small song header."""
    from songmap.arrange.expand import expand
    from songmap.parse import lang
    path = os.path.join(SKILL, "reference", f"{name}.md")
    for b in _blocks(path, "sm"):
        expand(lang.loads(b if b.startswith("song ") else SNIPPET_HEAD + b, f"{name}.md"))


@pytest.mark.parametrize("name", ["hopeful_explainer", "cinematic_build", "lofi_late_notes"])
def test_skill_examples_check_cleanly(name):
    from songmap.arrange.expand import expand
    from songmap.parse import lang
    song = lang.load(os.path.join(SKILL, "examples", f"{name}.sm"))
    arr = expand(song)
    arr.ensemble.check(song.parts())
    assert arr.timeline.total_bars >= 30 and not arr.warnings
    roles = {p for s in song.sections for p in s.parts}
    assert len(roles) >= 4                                        # a real arrangement, not a loop
    assert len({s.dyn for s in song.sections}) >= 4               # every section has its own dynamic shape


def test_cli_describe(capsys):
    from songmap.cli import main
    assert main(["describe", "--compact"]) == 0
    assert capsys.readouterr().out == catalog(compact=True)
