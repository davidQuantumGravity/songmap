"""Library data integrity, database boundary, exact pitches and playable exports."""
import io
import sqlite3
import wave

import numpy as np
import pytest

from songmap.gui.harmony_library import (
    HarmonyLibrary, KINDS, TONICS, pitch_name, realization, render_preview, seed_catalog, transpose,
)
from songmap.gui.project import parse_text
from songmap.arrange.expand import expand
from songmap.theory.harmony import Chord
from songmap.theory.keys import parse_key
from songmap.theory.tuning import EDO36


@pytest.fixture(scope="module")
def catalog():
    return seed_catalog()


def test_curated_catalog_complete_distinct_and_linked(catalog):
    assert len(catalog["progressions"]) == 100
    assert len(catalog["chords"]) == 30
    assert len(catalog["transitions"]) >= 150
    patterns = [(tuple(p["symbols"]), tuple(p["bars"]), p["mode"]) for p in catalog["progressions"]]
    assert len(set(patterns)) == 100
    source_ids = {s["id"] for s in catalog["sources"]}
    ids = {kind: {e["id"] for e in catalog[kind]} for kind in KINDS}
    for kind in KINDS:
        assert len(ids[kind]) == len(catalog[kind])
        assert len({e["description"] for e in catalog[kind]}) == len(catalog[kind])
        for e in catalog[kind]:
            assert len(e["summary"]) > 35 and e["summary"].endswith(".")
            assert len(e["description"].split()) >= 35
            assert set(e["source_ids"]) <= source_ids
            assert e["source_ids"]
            for k in KINDS:
                assert set(e.get(k[:-1] + "_ids", [])) <= ids[k]
            for symbol in e["symbols"]:
                Chord.parse(symbol)


def test_directed_adjacency_has_real_context_and_no_held_duplicates(catalog):
    transitions = {e["id"]: e for e in catalog["transitions"]}
    for p in catalog["progressions"]:
        for link in p["transition_links"]:
            t = transitions[link["id"]]
            i = link["position"]
            assert t["symbols"] == [p["symbols"][i], p["symbols"][(i + 1) % len(p["symbols"])]]
            assert t["symbols"][0] != t["symbols"][1]
            assert t["mode"] == p["mode"]
            assert p["id"] in t["progression_ids"]
            assert not link["loop_closure"] or p["loop"]
    forward = next(t for t in transitions.values() if t["symbols"] == ["Cmaj7", "Cg7"])
    reverse = next(t for t in transitions.values() if t["symbols"] == ["Cg7", "Cmaj7"])
    assert forward["id"] != reverse["id"]
    assert forward["common_tones"] == ["C", "B"]
    assert forward["catalog_uses"] == 0  # project extension, no invented song usage


def test_sqlite_persists_searches_filters_and_relations(tmp_path, catalog):
    library = HarmonyLibrary(tmp_path)
    assert library.metadata()["counts"]["progressions"] == 100
    assert [e["id"] for e in library.search("progressions", q="Andalusian")] == ["p037"]
    assert library.search("chords", q="golden ninth")[0]["id"] == "golden-nine"
    minor = library.search("progressions", family="Minor-key songs", mode="minor")
    assert len(minor) == 12 and all(e["mode"] == "minor" for e in minor)
    assert library.search("chords", q="' OR 1=1 --") == []
    assert not library.search("progressions", q="utterly-unknown")
    with pytest.raises(ValueError):
        library.search("../../files")
    with pytest.raises(KeyError):
        library.get("chords", "absent")
    reopened = HarmonyLibrary(tmp_path)
    assert reopened.get("progressions", "p001") == library.get("progressions", "p001")
    assert len(reopened.export()["transitions"]) == len(catalog["transitions"])
    with sqlite3.connect(library.path) as db:
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("SELECT COUNT(*) FROM links").fetchone()[0] > 700


def test_all_records_export_scores_that_really_expand(catalog):
    for kind in KINDS:
        for entry in catalog[kind]:
            plan = realization(entry)
            arr = expand(parse_text(plan["score"], "library.sm"))
            assert arr is not None
            assert len(plan["events"]) == len(entry["symbols"])
            assert plan["seconds"] > 0


def test_transposition_all_tonics_preserves_chord_and_slash_bass(catalog):
    for tonic in TONICS:
        shift = parse_key(tonic)[0]
        for entry in catalog["chords"]:
            original = Chord.parse(entry["symbols"][0])
            transposed = Chord.parse(transpose(entry["symbols"][0], tonic))
            assert transposed.intervals == original.intervals
            assert EDO36.pc(transposed.root) == EDO36.pc(original.root + shift)
            assert EDO36.pc(transposed.bass) == EDO36.pc(original.bass + shift)
        c = Chord.parse(transpose("Cm/B", tonic))
        assert EDO36.pc(c.bass) == EDO36.pc(11 + shift)
    assert transpose("C/E", "D") == "D/F#"
    assert pitch_name(60 + 2/3, True) == "vDb4"
    assert transpose("^Cg", "D") == "^Dg"


def test_preview_plays_all_actual_chord_tones_and_requested_bass(catalog):
    for pid in ("p006", "p043", "p052", "p069", "p088"):
        e = next(p for p in catalog["progressions"] if p["id"] == pid)
        for tonic in ("C", "Eb", "F#", "A"):
            plan = realization(e, tonic)
            for event in plan["events"]:
                chord = Chord.parse(event["symbol"])
                actual = {EDO36.pc(p) for p in event["pitches"]}
                assert {EDO36.pc(chord.root + i) for i in chord.intervals} <= actual
                assert EDO36.pc(event["pitches"][0]) == EDO36.pc(chord.bass)
                assert event["pitches"][0] < min(event["pitches"][1:])
    golden = realization(next(c for c in catalog["chords"] if c["id"] == "golden-nine"), "D")
    assert "tuning=36edo" in golden["score"]
    assert any(abs(p - round(p)) > .1 for p in golden["events"][0]["pitches"])


def test_quiet_finite_stereo_preview(catalog):
    e = next(c for c in catalog["chords"] if c["id"] == "golden-nine")
    plan = realization(e, "D", 160)
    audio = render_preview(plan)
    assert audio.shape[1] == 2 and np.isfinite(audio).all()
    assert .01 < np.max(np.abs(audio)) <= .55 + 1e-9
    assert len(audio) == pytest.approx((plan["seconds"] + 2.5) * 48000, abs=1)
    assert np.max(np.abs(audio[-1])) < 1e-10


def test_http_library_without_project_never_writes_scores(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from songmap.gui import project
    from songmap.gui.server import app
    monkeypatch.setattr(project, "ROOT", str(tmp_path))
    client = TestClient(app)
    assert client.get("/api/harmony/meta").json()["counts"]["progressions"] == 100
    results = client.get("/api/harmony/progressions?q=Andalusian").json()["items"]
    assert [e["id"] for e in results] == ["p037"]
    detail = client.get("/api/harmony/progressions/p006?tonic=D").json()
    assert detail["realization"]["events"][1]["symbol"] == "A/Db"
    assert client.get("/api/harmony/chords/missing").status_code == 404
    assert client.get("/api/harmony/nonsense").status_code == 400
    assert client.get("/api/harmony/chords/major?tonic=bad").status_code == 400
    assert client.get("/api/harmony/chords/major?bpm=0").status_code == 422
    export = client.get("/api/harmony/export")
    assert "attachment" in export.headers["content-disposition"]
    assert len(export.json()["progressions"]) == 100
    wav = client.get("/api/harmony/chords/golden-triad/audio?tonic=F&bpm=160")
    assert wav.status_code == 200 and wav.headers["content-type"] == "audio/wav"
    with wave.open(io.BytesIO(wav.content)) as f:
        assert f.getnchannels() == 2 and f.getframerate() == 48000
    assert list(tmp_path.rglob("*.sm")) == []
