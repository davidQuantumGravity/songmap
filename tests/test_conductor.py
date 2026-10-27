"""Section-aware musical metadata, lossless editing, and GUI timeline contracts."""
import math

import pytest

from songmap.arrange.expand import expand
from songmap.gui.project import Project, parse_text, summarize
from songmap.parse.errors import SongError

SCORE = '''song "Conductor" 120 4/4 C seed=7 tail=.2
chords C
motif phrase deg "0/4 2 4 6"
intro 2 | lead:[phrase] bass:sub
odd 2 | lead:{deg: "0/8 1 2 3 4 5 6"} meter="7/8 2+2+3" tempo=90 key="D dorian"
outro 2 | lead:{deg: "0/4 1 2 3 4"} meter=5/4 tempo=accel90>120 key="E phrygian"
'''


def test_summary_has_actual_meter_bar_times_and_section_metadata(tmp_path):
    arr = expand(parse_text(SCORE,"a.sm"))
    s = summarize(arr)
    assert s["bar_times"] == [round(arr.timeline.beat_to_sec(arr.timeline.bar_to_beat(b)),4) for b in range(7)]
    assert s["sections"][1]["meter"] == "7/8 2+2+3"
    assert s["sections"][1]["scale"] == "dorian"
    assert s["sections"][1]["tonic"] == "D"
    assert s["sections"][2]["tempo_start"] == 90 and s["sections"][2]["tempo_end"] == 120
    assert s["sections"][0]["tempo_override"] is None
    assert s["sections"][1]["tempo_override"] == 90
    assert s["sections"][2]["end_beat"]-s["sections"][2]["start_beat"] == 10


def test_unpinned_degree_motifs_follow_section_tonic_and_mode():
    score = '''song "Modulation" 120 4/4 C
motif phrase deg "0/4 2 4 6"
motif fixed deg key="C major" "0/4 2 4 6"
a 1 | lead:[phrase] keys:[fixed]
b 1 | lead:[phrase] keys:[fixed] key="D dorian"
c 1 | lead:[phrase] keys:[fixed] key="C minor"
'''
    arr = expand(parse_text(score,"a.sm"))
    pitches = lambda role, section:[e.pitches[0] for e in arr.parts[role] if e.section==section]
    assert pitches("lead","a") == [60,64,67,71]
    assert pitches("lead","b") == [62,65,69,72]
    assert pitches("lead","c") == [60,63,67,70]
    assert pitches("keys","b") == pitches("keys","a") == [60,64,67,71]


def test_piano_roll_and_step_grid_use_section_meter():
    from songmap.gui.clips import section_clip, section_hits
    arr = expand(parse_text(SCORE.replace('odd 2 |','odd 2 | drums:half '),"a.sm"))
    assert section_clip(arr,1,"lead")["beats_per_bar"] == 3.5
    assert section_hits(arr,1,"drums",SCORE)["beats_per_bar"] == 3.5


def test_conductor_edits_preserve_notes_and_other_metadata_in_sm_and_yaml():
    from songmap.gui.conductor import edit
    from songmap.parse.fmt import song_to_raw, to_yaml
    original = parse_text(SCORE,"a.sm")
    for path, source in [("a.sm",SCORE),("a.yaml",to_yaml(original))]:
        new = edit(source,path,index=1,values={"tempo":"rit 110>80","key":"F# minor","meter":"7/8 3+2+2"})
        song = parse_text(new,path)
        before, after = song_to_raw(original),song_to_raw(song)
        assert before["instruments"] == after["instruments"] if "instruments" in before else "instruments" not in after
        assert [s["parts"] for s in before["sections"]] == [s["parts"] for s in after["sections"]]
        assert before["sections"][0] == after["sections"][0]
        assert song.sections[1].tempo == "rit 110>80" and song.sections[1].key=="F# minor"
        assert song.sections[1].meter == (7,8,(3,2,2))
        reset = parse_text(edit(new,path,index=1,values={"tempo":None,"meter":None,"key":None}),path)
        assert reset.sections[1].tempo is None and reset.sections[1].meter is None and reset.sections[1].key is None


def test_structured_program_edits_only_the_requested_instance():
    from songmap.gui.conductor import edit
    source = '''song "Form" 120 4/4 C
verse = {lead: {deg: "0/1"}}
form:
  verse 1
  verse 1
'''
    song = parse_text(source,"form.sm")
    changed = edit(source,"form.sm",index=1,values={"tempo":83,"key":"Eb lydian"})
    assert source.rstrip() in changed
    back = parse_text(changed,"form.sm")
    assert back.sections[0].tempo is None and back.sections[1].tempo==83
    assert back.sections[1].key=="Eb lydian"
    reset = edit(changed,"form.sm",index=1,values={"tempo":None,"meter":None,"key":None})
    assert parse_text(reset,"form.sm").sections[1].tempo is None
    assert "verse = {lead:" in reset


def test_song_defaults_preserve_section_overrides_and_comments():
    from songmap.gui.conductor import edit
    source = SCORE.replace('odd 2 |','odd 2 |').replace('tempo=90 key="D dorian"','tempo=90 key="D dorian" # keep the key')
    text = edit(source,"a.sm",index=None,values={"tempo":103,"meter":"3/4","key":"F# minor"})
    back = parse_text(text,"a.sm")
    assert back.tempo == 103 and back.meter == (3,4) and back.key == "F# minor"
    assert back.sections[1].tempo == 90 and back.sections[1].key == "D dorian"
    edited = edit(source,"a.sm",index=1,values={"tempo":104,"key":"G lydian"})
    assert '# keep the key' in edited and 'lead:{deg: "0/8 1 2 3 4 5 6"}' in edited


@pytest.mark.parametrize("section",['verse 2 | lead:{\n  deg: "0/1"\n}\n',
                                    'verse 2 | lead:{deg: "0/1"}:\n  bar -1: lead = {deg: "2/1"}\n'])
def test_multiline_sections_and_variant_blocks_keep_their_program(section):
    from songmap.gui.conductor import edit
    source = 'song "Multiline" 120 4/4 C\n'+section
    changed = edit(source,"a.sm",index=0,values={"tempo":93,"key":"D dorian"})
    assert source.rstrip() in changed
    assert parse_text(changed,"a.sm").sections[0].tempo == 93


def test_conductor_encoding_round_trips_through_formatters():
    from songmap.gui.conductor import edit
    from songmap.parse.fmt import song_to_raw,to_sm,to_yaml
    source = SCORE + 'set conductor={outro: {tempo: "rit 120>80", key: "G mixolydian"}}\n'
    song = parse_text(source,"a.sm")
    for path, text in [("a.sm",to_sm(song)),("a.yaml",to_yaml(song))]:
        assert song_to_raw(parse_text(text,path))==song_to_raw(song)
    yaml_source = to_yaml(song)+'conductor:\n  outro: {tempo: 77}\n'
    edited = parse_text(edit(yaml_source,"a.yaml",index=2,values={"tempo":None}),"a.yaml")
    assert edited.sections[2].tempo is None


@pytest.mark.parametrize("source",[SCORE+'set conductor={absent: {tempo: 90}}\n',
                                 SCORE+'set conductor={intro: {tempo: 0}}\n',
                                 SCORE+'set conductor={intro: {key: "C nonsense"}}\n'])
def test_invalid_encoded_conductor_is_a_song_error(source):
    with pytest.raises(SongError):
        parse_text(source,"a.sm")


@pytest.mark.parametrize("values",[{"tempo":0},{"tempo":float("inf")},{"tempo":"rit 80>120"},
                                  {"key":"C invalid"},{"meter":"7/8 2+2"},{"scale":"unknown"}])
def test_invalid_edits_are_rejected_without_a_partial_result(values):
    from songmap.gui.conductor import edit
    with pytest.raises((ValueError,SongError)):
        edit(SCORE,"a.sm",index=1,values=values)


def test_api_conductor_op_is_unsaved_and_validated(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from songmap.gui import project,server
    monkeypatch.setattr(project,"ROOT",str(tmp_path));monkeypatch.setattr(server,"ROOT",str(tmp_path))
    monkeypatch.setattr(server,"_projects",{})
    (tmp_path/"a.sm").write_text(SCORE)
    client = TestClient(server.app)
    request={"path":"a.sm","text":SCORE,"op":"conductor","args":{"index":1,"values":{"tempo":100,"key":"G mixolydian"}}}
    r=client.post("/api/op",json=request)
    assert r.status_code==200,r.text
    assert r.json()["check"]["ok"] and r.json()["check"]["summary"]["sections"][1]["scale"]=="mixolydian"
    assert (tmp_path/"a.sm").read_text()==SCORE
    request["args"]["values"]={"meter":"5/9"}
    assert client.post("/api/op",json=request).status_code==400
