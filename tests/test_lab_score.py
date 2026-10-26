"""Actual-note display, source windows and timing maps for the listening UI."""
import pytest

from songmap.gui.lab_score import comparison_score, pitch_label, saved_structure
from songmap.gui.music_lab import MusicLab

SCORE = '''song "View" 120 4/4 C tuning=36edo seed=4 tail=.4 mood=v0
inst melody=lead bass=bass/sub
first 1 | melody:{notes: "^c1"} bass:{notes: "c-1"}
second 1 | melody:{notes: "g1"} bass:{notes: "c-1"}
'''


@pytest.fixture
def setup(tmp_path):
    (tmp_path / "songs").mkdir()
    (tmp_path / "songs/a.sm").write_text(SCORE)
    lab = MusicLab(tmp_path)
    s = lab.create("songs/a.sm", SCORE, "", None, 0, 2, "Compare melodies", "snippet",
                   {"path":"songs/a.sm", "start":2})
    return lab, s


def test_labels_preserve_sixth_step_pitch():
    assert pitch_label(60 + 1/3) == "^C4"
    assert pitch_label(64 - 1/3) == "vE4"
    assert pitch_label(60) == "C4"


def test_each_take_uses_its_own_saved_window_and_marks_changed_parts(setup):
    lab, s = setup
    data = comparison_score(lab, s["id"])
    assert data["changes"]["melody"] == ["notes / expression"]
    assert data["changes"]["bass"] == []
    a, b = data["takes"]
    assert a["bars"][0]["index"] == 0 and b["bars"][0]["index"] == 1
    assert b["bars"][0]["start"] == 0
    assert a["parts"][0]["notes"][0]["label"] == "^C4"
    assert a["parts"][0]["notes"][0]["micro"]
    assert b["parts"][0]["notes"][0]["label"] == "G4"
    assert a["parts"][0]["notes"][0]["hz"] == pytest.approx(440*2**((60+1/3-69)/12))
    (lab.root / "songs/a.sm").write_text("invalid newer source")
    assert comparison_score(lab, s["id"])["takes"] == data["takes"]


def test_cached_take_metadata_is_not_mutated_by_comparison(setup):
    lab, s = setup
    one = comparison_score(lab, s["id"], [s["pair"][0]])
    assert all(not p["changes"] for p in one["takes"][0]["parts"])
    assert comparison_score(lab, s["id"])["changes"]["melody"]
    with pytest.raises(ValueError, match="saved take"):
        comparison_score(lab, s["id"], ["missing"])


def test_voice_change_is_distinct_from_written_notes(setup):
    lab, _ = setup
    s=lab.create("songs/a.sm", SCORE, "melody", None, 0, 2, "Rounder")
    s=lab.add_candidate(s["id"], {"use":"epiano","params":{}}, "Keys", "manual")
    assert comparison_score(lab,s["id"])["changes"]["melody"] == ["instrument"]


def test_mixed_meter_and_section_tempo_use_real_bar_boundaries(tmp_path):
    path=tmp_path / "a.sm"
    path.write_text('''song "Meters" 120 4/4 C
a 1 | melody:{notes:"c1"}
b 2 | melody:{notes:"d2."} meter=3/4 tempo=60
''')
    data=saved_structure(tmp_path,"a.sm")
    assert [(b["start"],b["end"]) for b in data["bars"]] == [(0,2),(2,5),(5,8)]
    assert data["sections"][1]["first_bar"] == 1


def test_score_endpoints_are_read_only_and_reject_unknown_take(setup,monkeypatch):
    from fastapi.testclient import TestClient
    from songmap.gui import project, server
    lab,s=setup
    monkeypatch.setattr(project,"ROOT",str(lab.root))
    client=TestClient(server.app)
    assert client.get("/api/lab/source",params={"path":"songs/a.sm"}).json()["bars"]
    response=client.get(f"/api/lab/sessions/{s['id']}/score")
    assert response.status_code==200 and len(response.json()["takes"])==2
    assert client.get(f"/api/lab/sessions/{s['id']}/score?candidates=bad").status_code==400
    assert client.get("/api/lab/source?path=../outside.sm").status_code==400
    assert not lab.get(s["id"])["feedback"] and not lab.get(s["id"])["applied"]


def test_display_uses_the_performance_stage_and_held_notes_across_window(tmp_path):
    from songmap.gui.lab_score import take_score
    source=SCORE.replace('inst melody=lead bass=bass/sub','inst melody=lead bass=bass/sub\nfeel melody offset=100 gate=.5')
    view=take_score(str(tmp_path/'a.sm'),source,0,2)
    note=next(p for p in view["parts"] if p["part"]=="melody")["notes"][0]
    assert note["start"]==pytest.approx(.1)
    assert note["end"]==pytest.approx(1.0)
    view=take_score(str(tmp_path/'a.sm'),SCORE,1,1)
    note=next(p for p in view["parts"] if p["part"]=="melody")["notes"][0]
    assert note["start"]==-1 and note["end"]==pytest.approx(.8)


def test_shared_master_change_is_not_labelled_unchanged(setup):
    lab,_=setup
    s=lab.create("songs/a.sm",SCORE,"",None,0,2,"Change production","arrangement")
    lab.add_candidate(s["id"],{"source":SCORE+'master clean ceiling=-4\n'},"Quieter master","manual")
    changes=comparison_score(lab,s["id"])["changes"]
    assert changes=={"bass":["mix"],"melody":["mix"]}


def test_same_phrase_at_distant_origins_does_not_gain_a_false_change(tmp_path):
    source='''song "Shifted" 80 4/4 C mood=v0 tail=1
inst bass=bass/sub
groove hum=0,0,0 metric=0
feel bass gate=.91
phrase={notes:"r1 | r1 | r1 | r1 | r1 | r1 | r1 | c--2. r4"}
a 8 | bass:phrase
reset 1 |
b 8 | bass:phrase
'''
    (tmp_path/'a.sm').write_text(source)
    lab=MusicLab(tmp_path)
    s=lab.create('a.sm',source,'',None,0,24,'Same phrase','snippet',{'path':'a.sm','start':27})
    assert comparison_score(lab,s['id'])['changes']['bass']==[]


def test_develop_branches_the_immutable_favorite_and_keeps_its_offset(setup,monkeypatch):
    from fastapi.testclient import TestClient
    from songmap.gui import project,server
    lab,s=setup
    monkeypatch.setattr(project,"ROOT",str(lab.root))
    s["prior_choice"]={"provenance":"human conversation","text":"More motion"}
    lab.put(s)
    lab.feedback(s["id"],{"event_id":"pick","pair":s["pair"],"choice":"b","text":"Keep the rhythm",
                            "tags":["Better groove"],"audition_range":[.5,1.5]})
    (lab.root/"songs/a.sm").write_text("newer disk changes must not replace the snapshot")
    client=TestClient(server.app)
    r=client.post(f"/api/lab/sessions/{s['id']}/develop",json={"candidate":s["pair"][1],"scope":"riff","part":"melody","brief":"Develop the answer"})
    assert r.status_code==200,r.text
    branch=r.json()
    assert branch["start"]==2 and branch["base_source"]==SCORE
    assert branch["origin_candidate"]==s["pair"][1] and branch["origin_session"]==s["id"]
    assert not branch["feedback"] and branch["inherited_feedback"][0]["tags"]==["Better groove"]
    context=lab.context(branch["id"])
    assert context["prior_choice"]["text"]=="More motion"
    assert context["prior_feedback"][0]["audition_range"]==[.5,1.5]
    assert client.post(f"/api/lab/sessions/{s['id']}/develop",json={"candidate":"missing"}).status_code==400
