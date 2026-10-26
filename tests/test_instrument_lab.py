"""Instrument reach, persistent listening feedback, and safe musical edits."""
import json

import pytest

from songmap.gui.project import parse_text

SCORE = '''song "Lab" 120 4/4 C seed=4 tail=.3
chords C
inst bass=bass/sub keys=epiano
verse 1 | bass:eighths keys:hold drums:half
'''


def test_inventory_counts_played_voices_and_reports_bad_sources(tmp_path):
    from songmap.gui.instrument_lab import inventory
    (tmp_path / "songs").mkdir()
    (tmp_path / "songs/a.sm").write_text(SCORE)
    (tmp_path / "songs/b.sm").write_text(SCORE.replace('"Lab"', '"Other"'))
    (tmp_path / "songs/broken.sm").write_text("not a song")
    report = inventory(tmp_path)
    bass = next(v for v in report["instruments"] if v["use"] == "bass/sub")
    assert bass["source_count"] == 2 and bass["notes"] > 0
    assert {o["path"] for o in bass["occurrences"]} == {"songs/a.sm", "songs/b.sm"}
    assert any(v["piece"] == "kick" for v in report["occurrences"])
    assert len(report["errors"]) == 1


def test_inventory_reuses_snapshot_and_refreshes_live_feedback(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from songmap.gui import lab_api, project, server
    from songmap.gui.instrument_lab import Lab
    monkeypatch.setattr(project, "ROOT", str(tmp_path))
    (tmp_path / "songs").mkdir()
    (tmp_path / "songs/a.sm").write_text(SCORE)
    scans = []
    real_scan = lab_api.inventory
    def counted(root):
        scans.append(root)
        return real_scan(root)
    monkeypatch.setattr(lab_api, "inventory", counted)
    client = TestClient(server.app)
    first = client.get("/api/lab/inventory").json()
    assert not first["cached"] and len(scans) == 1
    store = Lab(tmp_path)
    session = store.create("songs/a.sm", SCORE, "bass", None, 0, 2, "warmer")
    store.assess("bass/sub", 3, "Needs work")
    (tmp_path / "songs/b.sm").write_text(SCORE)
    saved = client.get("/api/lab/inventory").json()
    assert saved["cached"] and len(scans) == 1
    assert saved["scanned_at"] == first["scanned_at"] and len(saved["sources"]) == 1
    assert saved["sessions"][0]["id"] == session["id"]
    assert saved["assessments"]["bass/sub"]["need"] == 3
    fresh = client.get("/api/lab/inventory?refresh=true").json()
    assert not fresh["cached"] and len(scans) == 2 and len(fresh["sources"]) == 2
    assert fresh["scanned_at"] >= saved["scanned_at"]
    assert "songs/b.sm" in client.get("/api/lab/inventory.csv").text
    # A missing export is rebuilt even when the JSON snapshot exists.
    (store.home / "instrument-usage.csv").unlink()
    assert "songs/b.sm" in client.get("/api/lab/inventory.csv").text
    assert len(scans) == 3
    # An incomplete or corrupt snapshot cannot strand the library.
    for contents in ('{"sources": []}', 'broken json'):
        (store.home / "inventory.json").write_text(contents)
        assert not client.get("/api/lab/inventory").json()["cached"]


def test_slow_inventory_does_not_block_saved_comparisons(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    from fastapi.testclient import TestClient
    from songmap.gui import lab_api, project, server
    from songmap.gui.instrument_lab import Lab, inventory
    monkeypatch.setattr(project, "ROOT", str(tmp_path))
    store = Lab(tmp_path)
    saved = store.create("songs/a.sm", SCORE, "bass", None, 0, 2, "warmer")
    scanning, release = threading.Event(), threading.Event()
    def slow(root):
        scanning.set()
        assert release.wait(5)
        return inventory(root)
    monkeypatch.setattr(lab_api, "inventory", slow)
    client = TestClient(server.app)
    with ThreadPoolExecutor() as pool:
        future = pool.submit(client.get, "/api/lab/inventory?refresh=true")
        try:
            assert scanning.wait(2)
            assert client.get("/api/lab/sessions").json()["sessions"][0]["id"] == saved["id"]
            assert client.get(f"/api/lab/sessions/{saved['id']}").json()["id"] == saved["id"]
        finally:
            release.set()
        assert future.result().status_code == 200


def test_voice_edit_preserves_music_in_sm_and_yaml():
    from songmap.gui.instrument_lab import edit_voice
    from songmap.parse.fmt import song_to_raw, to_yaml
    for path, source in [("a.sm", SCORE), ("a.yaml", to_yaml(parse_text(SCORE, "a.sm")))]:
        new = edit_voice(source, path, "bass", None, {"use": "bass/sub", "params": {"cutoff": 750}})
        before, after = parse_text(source, path), parse_text(new, path)
        assert after.instruments["bass"]["cutoff"] == 750
        before.instruments = after.instruments
        assert song_to_raw(before) == song_to_raw(after)
    with pytest.raises(ValueError):
        edit_voice(SCORE, "a.sm", "bass", None, {"use": "bass/sub", "params": {"made_up_knob": 1}})


def test_store_feedback_is_durable_idempotent_and_scope_checked(tmp_path):
    from songmap.gui.instrument_lab import Lab
    lab = Lab(tmp_path)
    s = lab.create("songs/a.sm", SCORE, "bass", None, 0, 2, "Less plastic")
    b = lab.add_candidate(s["id"], {"use": "bass/sub", "params": {"cutoff": 750}}, "Rounder", "manual")
    pair = b["pair"]
    vote = {"event_id": "test-vote", "pair": pair, "choice": "b", "text": "Better attack, less sub please"}
    lab.feedback(s["id"], vote)
    again = Lab(tmp_path).feedback(s["id"], vote)
    assert len(again["feedback"]) == 1 and again["incumbent"] == pair[1]
    assert "less sub" in json.dumps(Lab(tmp_path).context(s["id"]))
    with pytest.raises(ValueError, match="same sound|no instrument change"):
        lab.add_candidate(s["id"], {"use":"bass/sub", "params":{"cutoff":750}}, "No change", "manual")
    with pytest.raises(ValueError):
        lab.feedback(s["id"], {**vote, "event_id": "wrong", "pair": ["missing", pair[1]]})


def test_apply_is_explicit_and_detects_disk_changes(tmp_path):
    from songmap.gui.instrument_lab import Lab
    p = tmp_path / "songs/a.sm"
    p.parent.mkdir()
    p.write_text(SCORE)
    lab = Lab(tmp_path)
    s = lab.create("songs/a.sm", SCORE, "bass", None, 0, 2, "warmer")
    s = lab.add_candidate(s["id"], {"use": "bass/sub", "params": {"cutoff": 750}}, "warm", "manual")
    assert p.read_text() == SCORE
    p.write_text(SCORE + "# a concurrent edit\n")
    with pytest.raises(ValueError, match="changed"):
        lab.apply(s["id"], s["pair"][1], ["songs/a.sm"])
    assert "concurrent edit" in p.read_text()


def test_style_overrides_cannot_disguise_an_ineffective_knob_change(tmp_path):
    from songmap.gui.instrument_lab import Lab
    score = SCORE.replace("bass:eighths", "bass:sub")
    lab = Lab(tmp_path)
    s = lab.create("songs/a.sm", score, "bass", None, 0, 2, "clearer")
    assert "cutoff" in json.dumps(lab.context(s["id"])["style_and_note_overrides"])
    with pytest.raises(ValueError, match="overrides mask"):
        lab.add_candidate(s["id"], {"use":"bass/sub", "params":{"cutoff":750}}, "Ineffective", "manual")
    result = lab.add_candidate(s["id"], {"use":"bass/sub", "params":{"drive":2}}, "More edge", "manual")
    assert len(result["pair"]) == 2


def test_batch_apply_keeps_unrelated_overrides_and_can_be_undone(tmp_path):
    from songmap.gui.instrument_lab import Lab
    folder = tmp_path / "songs"
    folder.mkdir()
    a = SCORE.replace("bass=bass/sub", "bass=bass/sub(res=.2)")
    b = SCORE.replace("bass=bass/sub", "bass=bass/sub(res=.6)")
    (folder / "a.sm").write_text(a)
    (folder / "b.sm").write_text(b)
    lab = Lab(tmp_path)
    s = lab.create("songs/a.sm", a, "bass", None, 0, 2, "warmer")
    s = lab.add_candidate(s["id"], {"use": "bass/sub", "params": {"cutoff": 750}}, "warm", "manual")
    paths = ["songs/a.sm", "songs/b.sm"]
    preview = lab.preview_apply(s["id"], s["pair"][1], paths)
    receipt = lab.apply(s["id"], s["pair"][1], paths, {p["path"]: p["hash"] for p in preview})
    assert parse_text((folder / "b.sm").read_text(), "b.sm").instruments["bass"]["res"] == .6
    assert parse_text((folder / "b.sm").read_text(), "b.sm").instruments["bass"]["cutoff"] == 750
    lab.restore(s["id"], receipt["id"])
    assert (folder / "a.sm").read_text() == a and (folder / "b.sm").read_text() == b


def test_prefix_preview_preserves_original_note_timing_and_stems():
    import numpy as np
    from songmap.render import render
    song = parse_text(SCORE, "x.sm")
    full, clip = render(song), render(song, preview_end=1.2)
    assert len(clip.audio) == round(1.2 * 48000)
    for part in full.stems:
        assert np.max(np.abs(full.stems[part][:len(clip.stems[part])] - clip.stems[part])) < 1e-9


def test_http_round_trip_and_real_worker_feedback_context(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from songmap.gui import lab_api, project, server
    from songmap.gui.instrument_lab import Lab
    monkeypatch.setattr(project, "ROOT", str(tmp_path))
    monkeypatch.setattr(server, "ROOT", str(tmp_path))
    monkeypatch.setattr(server, "_projects", {})
    (tmp_path / "songs").mkdir()
    (tmp_path / "songs/a.sm").write_text(SCORE)
    seen = []
    def propose(store, sid, token):
        seen.append(store.context(sid))
        return {"use": "bass/sub", "params": {"cutoff": 750 + 100 * len(seen)}}, "Feedback revision", "Based on the comment"
    monkeypatch.setattr(lab_api, "propose", propose)
    class Immediate:
        def submit(self, fn, *args):
            fn(*args)
    monkeypatch.setattr(lab_api, "POOL", Immediate())
    client = TestClient(server.app)
    r = client.get("/api/lab/inventory").json()
    assert r["instruments"] and not r["errors"]
    assert client.post("/api/lab/sessions", json={"path":"../bad.sm", "part":"bass"}).status_code == 400
    s = client.post("/api/lab/sessions", json={"path":"songs/a.sm", "part":"bass", "seconds":2}).json()
    sid = s["id"]
    client.post(f"/api/lab/sessions/{sid}/generate")
    s = client.get(f"/api/lab/sessions/{sid}").json()
    assert s["status"] == "ready", s
    original = client.get(s["candidates"][0]["audio"]["solo"]).content
    assert original[:4] == b"RIFF"
    assert client.get(f"/api/lab/audio/{sid}/missing/solo").status_code == 400
    assert client.post(f"/api/lab/sessions/{sid}/feedback", json={"event_id":"vote1", "pair":s["pair"], "choice":"b", "text":"Less sub, keep this attack"}).status_code == 200
    client.post(f"/api/lab/sessions/{sid}/generate")
    new = client.get(f"/api/lab/sessions/{sid}").json()
    assert new["pair"][0] == s["pair"][1] and "Less sub" in json.dumps(seen[-1])
    assert client.get(s["candidates"][0]["audio"]["solo"]).content == original
    body = {"candidate":new["pair"][1], "paths":["songs/a.sm"]}
    preview = client.post(f"/api/lab/sessions/{sid}/preview", json=body).json()
    receipt = client.post(f"/api/lab/sessions/{sid}/apply", json={**body,"expected":{p["path"]:p["hash"] for p in preview["files"]}}).json()
    assert receipt["files"]
    assert client.post(f"/api/lab/sessions/{sid}/undo", json={"receipt":receipt["id"]}).status_code == 200
    assert (tmp_path / "songs/a.sm").read_text() == SCORE
    assert len(Lab(tmp_path).get(sid)["feedback"]) == 1


def test_generation_saves_the_unsent_comment_and_records_its_base(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from songmap.gui import lab_api, project, server
    from songmap.gui.instrument_lab import Lab
    monkeypatch.setattr(project, "ROOT", str(tmp_path))
    monkeypatch.setattr(server, "ROOT", str(tmp_path))
    (tmp_path / "songs").mkdir()
    (tmp_path / "songs/a.sm").write_text(SCORE)
    lab = Lab(tmp_path)
    s = lab.create("songs/a.sm", SCORE, "bass", None, 0, 2, "warmer")
    s = lab.add_candidate(s["id"], {"use":"bass/sub", "params":{"cutoff":750}}, "Rounder", "manual")
    lab.feedback(s["id"], {"event_id":"pick", "pair":s["pair"], "choice":"b", "text":"Good attack", "mode":"solo"})
    queued = []
    class Queue:
        def submit(self, *args): queued.append(args)
    monkeypatch.setattr(lab_api, "POOL", Queue())
    client = TestClient(server.app)
    draft = {"event_id":"unsent", "pair":s["pair"], "text":"Keep the attack but shorten the tail", "mode":"solo"}
    response = client.post(f"/api/lab/sessions/{s['id']}/generate", json={"feedback":draft})
    assert response.status_code == 200
    saved = lab.get(s["id"])
    assert saved["feedback"][-1]["text"] == draft["text"]
    assert saved["generation"]["base_candidate"] == s["pair"][1]
    assert "unsent" in saved["generation"]["feedback_events"]
    assert len(queued) == 1
    again = client.post(f"/api/lab/sessions/{s['id']}/generate", json={"feedback":draft})
    assert again.status_code == 200 and len(queued) == 1
    assert len(lab.get(s["id"])["feedback"]) == 2


def test_presented_takes_use_score_facts_and_resolve_historical_votes(tmp_path):
    from songmap.gui.instrument_lab import Lab
    lab = Lab(tmp_path)
    s = lab.create("songs/a.sm", SCORE, "bass", None, 0, 2, "warmer")
    s = lab.add_candidate(s["id"], {"use":"bass/sub", "params":{"cutoff":750}}, "Misleading model nickname", "manual")
    lab.feedback(s["id"], {"event_id":"pick", "pair":s["pair"], "choice":"b", "text":"Better", "mode":"context"})
    s = lab.add_candidate(s["id"], {"use":"bass/sub", "params":{"cutoff":850}}, "Another nickname", "manual")
    view = lab.present(s["id"])
    assert [c["take"] for c in view["candidates"]] == [1,2,3]
    assert "epiano" in json.dumps(view["audition"]["accompaniment"])
    assert view["audition"]["target"]["part"] == "bass"
    assert view["feedback"][0]["selected_take"] == 2
    assert view["candidates"][1]["display_name"] != "Misleading model nickname"
    assert "cutoff" in json.dumps(view["candidates"][2]["changes"])


def test_focused_preview_is_audible_without_rewriting_original_audio(tmp_path):
    import wave
    import numpy as np
    from songmap.gui.instrument_lab import Lab
    lab = Lab(tmp_path)
    s = lab.create("songs/a.sm", SCORE, "bass", None, 0, 2, "warmer")
    s = lab.add_candidate(s["id"], {"use":"bass/sub", "params":{"cutoff":750}}, "Rounder", "manual")
    lab.render_pair(s["id"])
    c = lab.get(s["id"])["candidates"][0]
    path = lab.audio_path(s["id"], c["id"], "solo")
    original = path.read_bytes()
    # Reproduce a quiet legacy asset like the reported bass audition.
    with wave.open(str(path)) as w:
        values = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float)/32768
        params = w.getparams()
    with wave.open(str(path), "wb") as w:
        w.setparams(params); w.writeframes((values*.01*32767).astype("<i2").tobytes())
    quiet = path.read_bytes()
    stored = lab.get(s["id"])
    stored["candidates"][0]["audio"].pop("focus", None)
    lab.put(stored)
    view = lab.present(s["id"])
    focused = lab.audio_path(s["id"],c["id"],"focus")
    assert focused.exists() and path.read_bytes() == quiet and quiet != original
    with wave.open(str(focused)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float)/32768
    assert np.max(np.abs(x)) <= .971 and np.sqrt(np.mean(x*x)) > np.sqrt(np.mean((values*.01)**2))*2
    assert view["candidates"][0]["preview_gain_db"] > 0


def test_render_assets_survive_a_later_candidate(tmp_path):
    from songmap.gui.instrument_lab import Lab
    lab = Lab(tmp_path)
    s = lab.create("songs/a.sm", SCORE, "bass", None, 0, 2, "warmer")
    s = lab.add_candidate(s["id"], {"use": "bass/sub", "params": {"cutoff": 750}}, "warm", "manual")
    lab.render_pair(s["id"])
    s = lab.get(s["id"])
    for candidate in s["candidates"]:
        assert lab.audio_path(s["id"], candidate["id"], "solo").read_bytes()[:4] == b"RIFF"
        assert candidate["audio"]["context"] and candidate["loudness"]["solo"] < 0
    first = lab.audio_path(s["id"], s["pair"][0], "solo").read_bytes()
    assert first != lab.audio_path(s["id"], s["pair"][1], "solo").read_bytes()
    lab.add_candidate(s["id"], {"use": "bass/sub", "params": {"cutoff": 950}}, "clear", "manual")
    assert lab.audio_path(s["id"], s["pair"][0], "solo").read_bytes() == first
