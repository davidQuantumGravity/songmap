"""`songmap describe`: the catalog is complete (built from the registries) and the compact one stays small."""
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
    assert len(c) < 2000                     # ~500 tokens at ~3.5 chars per token


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


def test_skill_example_checks():
    import os
    import re
    from songmap.arrange.expand import expand
    from songmap.parse import lang
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, ".claude", "skills", "songmap-compose", "SKILL.md"), encoding="utf-8") as f:
        blocks = [b for b in re.findall(r"```\n(.*?)```", f.read(), re.S) if b.startswith("song ")]
    assert blocks
    for b in blocks:
        assert expand(lang.loads(b, "SKILL.md")).timeline.frames == 1350


def test_cli_describe(capsys):
    from songmap.cli import main
    assert main(["describe", "--compact"]) == 0
    assert capsys.readouterr().out == catalog(compact=True)
