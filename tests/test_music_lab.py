"""Musical A/B scope, independent source windows, persistence and explicit writes."""
import json
import wave

import numpy as np
import pytest

from songmap.gui.music_lab import MusicLab

SCORE = '''song "Musical Lab" 120 4/4 C seed=4 tail=.3
inst melody=lead keys=epiano
chords C
first 1 | melody:{notes: "c1"} keys:hold
second 1 | melody:{notes: "g1"} keys:hold
mix melody -2 | keys -35
master clean ceiling=-2
'''


@pytest.fixture
def lab(tmp_path):
    (tmp_path / "songs").mkdir()
    (tmp_path / "songs/a.sm").write_text(SCORE)
    (tmp_path / "songs/b.sm").write_text(SCORE.replace('"c1"', '"e1"'))
    return MusicLab(tmp_path)


def create(lab, scope="riff", **kw):
    return lab.create("songs/a.sm", SCORE, "melody", None, 0, 2, "more forward motion", scope, **kw)


def test_riff_preserves_backing_and_persists_human_decision(lab):
    s = create(lab)
    s = lab.add_candidate(s["id"], {"source": SCORE.replace('"c1"', '"c2 e4 g4"')}, "Forward", "manual")
    vote = {"event_id": "human-1", "pair": s["pair"], "choice": "b", "text": "This moves", "mode": "context"}
    lab.feedback(s["id"], vote)
    lab.feedback(s["id"], vote)
    view = MusicLab(lab.root).present(s["id"])
    assert len(view["feedback"]) == 1 and view["feedback"][0]["scope"] == "riff"
    assert view["feedback"][0]["selected_take"] == 2
    assert view["incumbent"] == s["pair"][1]
    assert lab.context(s["id"])["source"].find('c2 e4 g4') > 0
    assert lab.listing()["sessions"][0]["scope"] == "riff"
    assert (lab.root / "songs/a.sm").read_text() == SCORE


@pytest.mark.parametrize("changed", [SCORE.replace("keys:hold", 'keys:{notes: "r1"}'),
    SCORE.replace("melody=lead", "melody=epiano"), SCORE.replace("chords C", "chords Am"),
    SCORE.replace('seed=4', 'seed=5'), SCORE.replace('120 4/4', '100 4/4')])
def test_riff_rejects_backing_voice_harmony_and_timing_edits(lab, changed):
    s = create(lab)
    with pytest.raises(ValueError):
        lab.add_candidate(s["id"], {"source": changed}, "Wrong scope", "manual")
    assert len(lab.get(s["id"])["candidates"]) == 1


def test_arrangement_allows_orchestration_but_keeps_timing(lab):
    s = create(lab, "arrangement")
    s = lab.add_candidate(s["id"], {"source": SCORE.replace("melody=lead", "melody=epiano").replace("keys:hold", 'keys:{notes: "r1"}')}, "Sparse", "manual")
    assert lab.present(s["id"])["audition"]["can_solo"] is False
    with pytest.raises(ValueError, match="timing"):
        lab.add_candidate(s["id"], {"source": SCORE.replace("first 1", "first 2")}, "Longer", "manual")
    with pytest.raises(ValueError, match="no musical change"):
        lab.add_candidate(s["id"], {"source": SCORE + "# comment only\n"}, "No edit", "manual")


def test_musical_apply_preview_conflict_and_undo(lab):
    s = create(lab)
    changed = SCORE.replace('"c1"', '"e1"')
    s = lab.add_candidate(s["id"], {"source": changed}, "New riff", "manual")
    cid, sid = s["pair"][1], s["id"]
    with pytest.raises(ValueError, match="original score"):
        lab.preview_apply(sid, cid, ["songs/b.sm"])
    preview = lab.preview_apply(sid, cid, [s["path"]])
    expected = {p["path"]: p["hash"] for p in preview}
    with pytest.raises(ValueError, match="changed"):
        lab.apply(sid, cid, [s["path"]], {s["path"]: "stale"})
    receipt = lab.apply(sid, cid, [s["path"]], expected)
    assert (lab.root / s["path"]).read_text() == changed
    lab.restore(sid, receipt["id"])
    assert (lab.root / s["path"]).read_text() == SCORE
    (lab.root / s["path"]).write_text(SCORE + "# newer\n")
    with pytest.raises(ValueError, match="changed"):
        lab.preview_apply(sid, cid, [s["path"]])


def test_saved_excerpts_render_their_own_offsets_and_keep_snapshots(lab):
    s = create(lab, "snippet", comparison={"path": "songs/a.sm", "start": 2, "label": "Higher riff"})
    sid = s["id"]
    lab.render_pair(sid)
    view = lab.present(sid)
    assert [c["excerpt"]["start"] for c in view["candidates"]] == [0, 2]
    assert all(c["audio"]["context"] for c in view["candidates"])
    peaks = []
    for c in view["candidates"]:
        with wave.open(str(lab.audio_path(sid, c["id"], "context"))) as w:
            assert w.getnframes() == 96000 and w.getframerate() == 48000
        # The isolated asset is the full mix for snippet mode.
        with wave.open(str(lab.audio_path(sid, c["id"], "solo"))) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, 2).mean(axis=1)
        segment = x[24000:72000] * np.hanning(48000)
        peaks.append(np.argmax(np.abs(np.fft.rfft(segment))))
    assert abs(peaks[0] - peaks[1]) > 80
    original = lab.audio_path(sid, s["pair"][0], "context").read_bytes()
    (lab.root / "songs/a.sm").write_text("broken after snapshot")
    lab.render_pair(sid)
    assert lab.audio_path(sid, s["pair"][0], "context").read_bytes() == original
    assert lab.present(sid)["candidates"][0]["source"] == SCORE
    with pytest.raises(ValueError, match="listening only"):
        lab.preview_apply(sid, s["pair"][1], ["songs/a.sm"])


@pytest.mark.parametrize("comparison", [{"path": "songs/a.sm", "start": -1},
    {"path": "songs/a.sm", "start": 4}, {"path": "../outside.sm", "start": 0},
    {"path": "songs/a.sm", "start": "bad"}, {"path": "songs/a.sm", "start": None},
    {"path": "songs/a.sm", "start": "NaN"}, {"path": "songs/a.sm", "start": 0}])
def test_invalid_excerpt_does_not_leave_a_partial_session(lab, comparison):
    with pytest.raises(ValueError):
        create(lab, "snippet", comparison=comparison)
    assert not lab.listing()["sessions"]


def test_api_routes_musical_jobs_and_rejects_snippet_generation(lab, monkeypatch):
    from fastapi.testclient import TestClient
    from songmap.gui import lab_api, project, server
    monkeypatch.setattr(project, "ROOT", str(lab.root))
    monkeypatch.setattr(server, "ROOT", str(lab.root))
    class Immediate:
        def submit(self, fn, *args): fn(*args)
    monkeypatch.setattr(lab_api, "POOL", Immediate())
    seen = []
    def propose(store, sid, token):
        seen.append(store.context(sid))
        return {"source": SCORE.replace('"c1"', '"c2 e4 g4"')}, "Forward", "Rhythmic motion"
    monkeypatch.setattr(lab_api, "propose", propose)
    client = TestClient(server.app)
    s = client.post("/api/lab/sessions", json={"scope":"riff","path":"songs/a.sm","part":"melody","seconds":2}).json()
    assert client.post(f"/api/lab/sessions/{s['id']}/generate", json={}).status_code == 200
    view = client.get(f"/api/lab/sessions/{s['id']}").json()
    assert view["status"] == "ready" and len(view["pair"]) == 2 and seen[0]["scope"] == "riff"
    assert client.get(view["candidates"][1]["audio"]["context"]).content[:4] == b"RIFF"
    s = client.post("/api/lab/sessions", json={"scope":"snippet","path":"songs/a.sm","seconds":2,
                                            "comparison":{"path":"songs/b.sm","start":0}}).json()
    assert client.post(f"/api/lab/sessions/{s['id']}/generate", json={}).status_code == 400
    assert client.post(f"/api/lab/sessions/{s['id']}/render", json={}).status_code == 200
    assert client.get(f"/api/lab/sessions/{s['id']}").json()["status"] == "ready"


def test_musical_provider_requests_a_complete_score_with_scope_and_feedback(lab, monkeypatch):
    from songmap.gui import lab_api, rack
    (lab.root / "docs").mkdir()
    (lab.root / "docs/COMPACT_FORMAT.md").write_text('Notes: c4 d8 r4; chords: [c,e,g]2')
    s = create(lab)
    lab.feedback(s["id"], {"event_id":"direction", "pair":s["pair"], "choice":"comment",
                           "text":"Keep the backing; add forward motion"})
    monkeypatch.setattr(rack, "catalog", lambda: {"samplers":[],"instruments":{},"presets":{}})
    monkeypatch.setattr(lab_api.shutil, "which", lambda _: "codex.exe")
    captured = {}
    class Process:
        returncode = 0
        def __init__(self, command, **kwargs):
            captured["command"] = command
            self.out = command[command.index("--output-last-message") + 1]
            captured["schema"] = json.loads(__import__('pathlib').Path(command[command.index("--output-schema") + 1]).read_text())
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def communicate(self, prompt, timeout):
            captured["prompt"] = prompt
            __import__('pathlib').Path(self.out).write_text(json.dumps({"label":"Forward","reason":"Rhythmic answer",
                "source":SCORE.replace('"c1"', '"c2 e4 g4"')}))
            return "", ""
    monkeypatch.setattr(lab_api.subprocess, "Popen", Process)
    change, label, reason = lab_api.propose(lab, s["id"], "adapter-test")
    assert captured["schema"]["required"] == ["label", "reason", "source"]
    assert "Keep the backing; add forward motion" in captured["prompt"]
    assert "ONLY the selected part" in captured["prompt"] and "LANGUAGE REFERENCE" in captured["prompt"]
    assert "--sandbox" in captured["command"] and "read-only" in captured["command"]
    lab.add_candidate(s["id"], change, label, "codex", reason)
    assert len(lab.get(s["id"])["pair"]) == 2
