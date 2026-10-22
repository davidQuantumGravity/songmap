"""SongMap Studio: the server API, the mixer's text edits and the stem remix."""
import numpy as np
import pytest

pytest.importorskip("fastapi")

from songmap.gui import mixer
from songmap.gui.project import Project, parse_text
from songmap.render import render

SONG = """song "Remix" 120 4/4 C fps=30 seed=3 tail=1
chords C Am F G
mix keys -3 hall=.2 | bass -2  # the balance
verse 2 | keys:hold bass:sub lead:{deg: "=mf 4/4 2 0 2 | 4/2 5/2"} dyn=mf
"""


def test_set_mix_edits_one_part_and_keeps_the_rest():
    out = mixer.set_mix(SONG, "keys", gain_db=-6.5, pan=-0.25)
    line = next(ln for ln in out.splitlines() if ln.startswith("mix"))
    assert line == "mix keys -6.5 hall=.2 pan=-0.25 | bass -2  # the balance"
    back = mixer.set_mix(out, "keys", pan=0)                      # pan 0 drops the option
    assert "pan=" not in next(ln for ln in back.splitlines() if ln.startswith("mix"))


def test_set_mix_adds_a_part_and_a_line():
    out = mixer.set_mix(SONG, "lead", gain_db=4, sends={"hall": 0.3})
    assert "| lead 4 hall=0.3" in out
    bare = "\n".join(ln for ln in SONG.splitlines() if not ln.startswith("mix"))
    added = mixer.set_mix(bare, "keys", gain_db=-2).splitlines()
    assert added[2] == "mix keys -2" and added[3].startswith("verse")
    assert parse_text(mixer.set_mix(SONG, "lead", gain_db=4), "x.sm").mix["lead"]["gain_db"] == 4


def test_remix_matches_a_full_render(tmp_path):
    p = tmp_path / "remix.sm"
    p.write_text(SONG, encoding="utf-8")
    pr = Project.open(str(p))
    assert not pr.render().remixed
    text = mixer.set_mix(mixer.set_mix(SONG, "keys", gain_db=-9, pan=0.4, sends={"hall": 0.5}), "bass", gain_db=1)
    rd = pr.render(text)
    assert rd.remixed
    ref = render(parse_text(text, str(p))).audio
    assert np.abs(ref - rd.audio).max() < 1e-9
    other = pr.render(text.replace("dyn=mf", "dyn=f"))                # a note change renders in full
    assert not other.remixed
    q = pr.measure(pr.render(text, mute=("bass",)))
    assert q["stems"]["bass"] == -70.0 and q["lufs"] < 0


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from songmap.gui import project as project_mod
    from songmap.gui import server
    monkeypatch.setattr(project_mod, "ROOT", str(tmp_path))
    monkeypatch.setattr(server, "ROOT", str(tmp_path))
    monkeypatch.setattr(server, "_projects", {})
    (tmp_path / "songs").mkdir()
    (tmp_path / "songs" / "a.sm").write_text(SONG, encoding="utf-8")
    return TestClient(server.app)


def test_api_check_op_render_and_ranges(client):
    assert client.get("/api/files").json()["songs"] == ["songs/a.sm"]
    r = client.get("/api/project", params={"path": "songs/a.sm"}).json()
    assert r["check"]["ok"] and r["check"]["summary"]["parts"]
    bad = client.post("/api/check", json={"path": "songs/a.sm", "text": SONG.replace("keys:hold", "keys:holdd")}).json()
    assert not bad["ok"] and bad["diagnostics"][0]["line"] == 4
    op = client.post("/api/op", json={"path": "songs/a.sm", "text": SONG, "op": "mix",
                                      "args": {"part": "bass", "gain_db": -5}}).json()
    assert "bass -5" in op["text"] and op["check"]["ok"]
    rr = client.post("/api/render", json={"path": "songs/a.sm", "text": op["text"]}).json()
    assert rr["ok"] and rr["qa"]["stems"]
    whole = client.get(rr["audio"])
    assert whole.status_code == 200 and whole.content[:4] == b"RIFF"
    part = client.get(rr["audio"], headers={"Range": "bytes=100-199"})
    assert part.status_code == 206 and part.content == whole.content[100:200]
    assert client.get("/api/project", params={"path": "../outside.sm"}).status_code == 400
