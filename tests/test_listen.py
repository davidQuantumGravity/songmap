"""The automated ear (songmap listen) and the textbook Songbook that shows every song for review."""
import os
import sys

import pytest

from songmap.arrange.expand import expand
from songmap.listen import _loudness_findings, listen
from songmap.parse import lang

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEAD = 'song "L" 120 4/4 C fps=30 seed=1 tail=1\nchords C G Am F\n'


def kinds(body, qa=None):
    rep = listen(expand(lang.loads(HEAD + body, "l.sm")), qa)
    return {(f.kind, f.severity) for f in rep.findings}, rep


def test_minor_ninth_rub_on_a_strong_beat_is_a_clash():
    # bar 2 is G: C held on beat 1 sits a half step above B
    found, rep = kinds('x 4 | lead="=mf c+1 | c+1 | c+1 | a1"')
    assert ("clash", "warning") in found or ("clash", "problem") in found
    assert any("C over G" in f.message for f in rep.findings)


def test_an_appoggiatura_that_resolves_is_only_a_note():
    found, _ = kinds('x 4 | lead="=mf e+1 | c+2. b4 | c+1 | a1"')
    assert ("appoggiatura", "note") in found and not any(k == "clash" for k, _ in found)


def test_a_major_seventh_colour_is_not_a_clash():
    found, _ = kinds('x 4 | lead="=mf e+1 | f#1 | e+1 | e+1"')      # F# over G = its major 7th
    assert not any(k == "clash" for k, _ in found)


def test_crowding_repetition_and_hits():
    found, _ = kinds('x 20 | drums:{kick: "x...x...x...x..."} keys:{rel: "[R,3,5]/1", oct: 1} lead="e+1 | g+1"'
                     ' | !impact !impact@+2 !impact@+4 !impact@+6 !impact@+8')
    assert ("repetition", "warning") in found          # the same drum bar 20 times
    assert ("register", "warning") in found            # keys chords and lead in one octave
    assert ("hits", "warning") in found                # 5 impacts in 41 s


def test_loudness_findings_from_a_render():
    qa = {"sections": [{"name": "a", "loudness": -20}, {"name": "b", "loudness": -14}, {"name": "c", "loudness": -13.5}],
          "stems": {"drums": -10, "lead": -20}, "clipped_samples": 0}
    msgs = [f.message for f in _loudness_findings(qa, None)]
    assert any("only 0.5 dB above" in m for m in msgs) and any("melody (lead) is 10.0 dB under drums" in m for m in msgs)


def test_cli_listen_exit_codes(tmp_path, capsys):
    from songmap.cli import main
    good = tmp_path / "good.sm"
    good.write_text(HEAD + 'x 4 | pad:warm lead="=mf e+1 | d+1 | c+1 | c+1"\n', encoding="utf-8")
    assert main(["listen", str(good)]) == 0
    assert "automated ear" in capsys.readouterr().out


def test_the_skill_examples_pass_the_ear():
    d = os.path.join(ROOT, ".claude", "skills", "songmap-compose", "examples")
    for f in os.listdir(d):
        rep = listen(expand(lang.load(os.path.join(d, f))))
        bad = [x for x in rep.findings if x.severity != "note"]
        assert not bad, (f, [x.message for x in bad])


# ----------------------------------------------------------------------------------------------
# the Songbook
# ----------------------------------------------------------------------------------------------
@pytest.fixture
def songbook():
    sys.path.insert(0, os.path.join(ROOT, "tools", "textbook"))
    import songbook as sb
    return sb


def test_songbook_collects_every_song_and_reads_review_lines(songbook, tmp_path, monkeypatch):
    col = tmp_path / "songs" / "demo"
    col.mkdir(parents=True)
    (col / "README.md").write_text("# Demo songs\n\nTwo small songs.\n", encoding="utf-8")
    (col / "a.sm").write_text('# A test tune: should feel calm.\n# review: approved — lovely pad\n' + HEAD +
                              'x 2 | pad:warm\n', encoding="utf-8")
    (col / "b.sm").write_text('# Unreviewed.\n' + HEAD + 'x 2 | pad:warm\n', encoding="utf-8")
    (col / "broken.sm").write_text(HEAD + 'x 2 | pad:wram\n', encoding="utf-8")
    monkeypatch.setattr(songbook, "SONGS", str(tmp_path / "songs"))
    monkeypatch.setattr(songbook, "SKILL_EXAMPLES", str(tmp_path / "none"))
    cols = songbook.collections()
    assert [c["title"] for c in cols] == ["Demo songs"] and len(cols[0]["songs"]) == 3
    entries = {p: songbook.entry(p) for p in cols[0]["songs"]}
    by_name = {e["name"]: e for e in entries.values()}
    assert by_name["a"]["status"] == "approved" and by_name["a"]["review_note"] == "lovely pad"
    assert by_name["a"]["intent"] == "A test tune: should feel calm."
    assert by_name["b"]["status"] == "awaiting" and "ear" in by_name["b"]
    assert "pad:wram" not in by_name["broken"].get("error", "") and "wram" in by_name["broken"]["error"]
    frag = songbook.fragment(cols, entries, {}, {})
    secs = songbook.sections(cols)
    assert [s["id"] for s in secs] == ["about", "songs-demo"]
    for s in secs:
        assert f'<section id="{s["id"]}">' in frag
    assert frag.index("b.sm") < frag.index("a.sm")          # songs awaiting review come first
    assert "Does not load" in frag


def test_songbook_is_in_the_textbook(songbook):
    import yaml
    toc = yaml.safe_load(open(os.path.join(ROOT, "textbook", "toc.yaml"), encoding="utf-8"))
    chapters = [c for p in toc["parts"] for c in p["chapters"]]
    assert any(c.get("generated") == "songbook" for c in chapters)
    # every song in the repo is collected
    found = {os.path.normpath(p) for c in songbook.collections() for p in c["songs"]}
    for d, _, files in os.walk(os.path.join(ROOT, "songs")):
        if "renders" in d:
            continue
        for f in files:
            if f.endswith((".sm", ".sml", ".songmap.yaml")):
                assert os.path.normpath(os.path.join(d, f)) in found
