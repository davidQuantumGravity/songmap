"""Editable tone recipes and instrument-only blends, from note audio to saved scores."""
import json

import numpy as np
import pytest

from songmap.gui.project import parse_text

SCORE = '''song "Tone" 120 4/4 C seed=4 tail=.3
chords C
inst bass=bass/sub keys=epiano
verse 1 | bass:eighths keys:hold drums:half
'''


def test_sound_neutral_and_blend_endpoints_preserve_source_audio():
    from songmap.arrange.ensemble import Ensemble
    from songmap.instruments import Note, make
    from songmap.instruments.sound import build
    ens = Ensemble(parse_text(SCORE, "x.sm"))
    spec = {"a": {"use": "bass/sub", "params": {}}, "b": {"use": "bass/rubber", "params": {}}}
    note = Note(40.3, .62, .17, seed=19, rr=3)
    for amount, use in [(0, "bass/sub"), (1, "bass/rubber")]:
        y = build("test", spec, ens, blend=amount).render(note)
        original = make(use).render(note)
        np.testing.assert_array_equal(y, original)
    a, b = make("bass/sub").render(note), make("bass/rubber").render(note)
    y = build("test", spec, ens, blend=.3).render(note)
    expected = np.zeros_like(y)
    expected[:len(a)] += .7*a
    expected[:len(b)] += .3*b
    np.testing.assert_allclose(y, expected, atol=1e-14)
    shaped = build("test", spec, ens, blend=.3, tone_brightness=-.7, tone_body=.3,
                   tone_attack=.2, tone_tightness=.4, tone_grit=.2).render(note)
    assert np.isfinite(shaped).all() and np.max(np.abs(shaped-y)) > .001


def test_recipe_roundtrip_changes_only_selected_voice_and_survives_apply(tmp_path):
    from songmap.gui.music_lab import MusicLab
    from songmap.gui.tone_lab import design_change
    from songmap.parse.fmt import song_to_raw, to_yaml, to_sm
    from songmap.render import render
    folder = tmp_path / "songs"
    folder.mkdir()
    store = MusicLab(tmp_path)
    for ext, source in [("sm", SCORE), ("yaml", to_yaml(parse_text(SCORE, "a.sm")))]:
        path = f"songs/a.{ext}"
        (tmp_path/path).write_text(source)
        s = store.create(path, source, "bass", None, 0, 2, "warmer")
        s = store.add_candidate(s["id"], {"use":"bass/rubber", "params":{}}, "B", "manual")
        change, description = design_change(store, s["id"], {"pair":s["pair"],"amount":.35,"tone":{"tone_body":.3}})
        saved = store.add_candidate(s["id"], change, "Blend", "design", description)
        take = saved["candidates"][-1]
        assert (tmp_path/path).read_text() == source
        before, after = parse_text(source, path), parse_text(take["source"], path)
        old_raw, new_raw = song_to_raw(before), song_to_raw(after)
        for k in new_raw:
            if k not in {"instruments", "sounds"}:
                assert old_raw.get(k) == new_raw[k]
        np.testing.assert_array_equal(render(before).stems["keys"], render(after).stems["keys"])
        assert song_to_raw(parse_text(to_sm(after), "roundtrip.sm"))["sounds"] == after.sounds
        assert song_to_raw(parse_text(to_yaml(after), "roundtrip.yaml"))["sounds"] == after.sounds
        previews = store.preview_apply(s["id"], take["id"], [path])
        assert "sounds" in previews[0]["text"]
        receipt = store.apply(s["id"], take["id"], [path], {p["path"]:p["hash"] for p in previews})
        applied = parse_text((tmp_path/path).read_text(), path)
        np.testing.assert_array_equal(render(after).audio, render(applied).audio)
        store.restore(s["id"], receipt["id"])
        assert (tmp_path/path).read_text() == source


def test_design_validation_and_preview_do_not_record_votes_or_takes(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from songmap.gui import lab_api, project, server
    from songmap.gui.music_lab import MusicLab
    monkeypatch.setattr(project, "ROOT", str(tmp_path))
    store = MusicLab(tmp_path)
    s = store.create("songs/a.sm", SCORE, "bass", None, 0, 2, "warm")
    s = store.add_candidate(s["id"], {"use":"bass/rubber", "params":{}}, "B", "manual")
    client = TestClient(server.app)
    url = f"/api/lab/sessions/{s['id']}/design"
    original = json.dumps(store.get(s["id"]), sort_keys=True)
    for payload in [{"base":"missing","tone":{"tone_body":.5}}, {"base":s["pair"][0],"tone":{"bogus":.5}},
                    {"pair":list(reversed(s["pair"])),"amount":.3}, {"pair":s["pair"],"amount":2},
                    {"base":s["pair"][0],"tone":{"tone_body":True}}]:
        assert client.post(url, json=payload).status_code == (409 if "pair" in payload and payload["pair"] != s["pair"] else 400)
    assert json.dumps(store.get(s["id"]), sort_keys=True) == original
    preview = client.post(url+"/preview", json={"base":s["pair"][1],"tone":{"tone_brightness":-.5}})
    assert preview.status_code == 200, preview.text
    assert client.get(preview.json()["audio"]).content[:4] == b"RIFF"
    assert json.dumps(store.get(s["id"]), sort_keys=True) == original


def test_recursive_sound_definitions_are_rejected_and_cache_identity_includes_recipe():
    from songmap.arrange.ensemble import Ensemble
    from songmap.instruments.sound import build
    from songmap.parse.errors import SongError
    from songmap.render import inst_key
    song = parse_text(SCORE, "x.sm")
    song.sounds = {"bad":{"a":{"use":"sound/bad","params":{}}}}
    ens = Ensemble(song)
    with pytest.raises(SongError, match="recursive|nesting"):
        build("bad", song.sounds["bad"], ens)
    a = build("same", {"a":{"use":"bass/sub","params":{}}}, ens)
    b = build("same", {"a":{"use":"bass/rubber","params":{}}}, ens)
    assert inst_key(a) != inst_key(b)


def test_nested_blend_keeps_existing_shape_and_note_overrides():
    from songmap.arrange.ensemble import Ensemble
    from songmap.instruments import Note, make
    from songmap.instruments.sound import build
    from songmap.render import inst_key
    song = parse_text(SCORE, "x.sm")
    song.sounds = {"dark":{"a":{"use":"bass/sub","params":{}}}}
    ens = Ensemble(song)
    spec = {"a":{"use":"sound/dark","params":{"tone_brightness":-.7}},
            "b":{"use":"bass/rubber","params":{}}}
    note = Note(43.2,.7,.2,seed=9,rr=2,params={"cutoff":1200})
    a = build("dark", song.sounds["dark"], ens, tone_brightness=-.7).render(note)
    b = make("bass/rubber").render(note)
    y = build("mixed",spec,ens,blend=.4,tone_brightness=0).render(note)
    expected = np.zeros_like(y)
    expected[:len(a)] += .6*a
    expected[:len(b)] += .4*b
    np.testing.assert_allclose(y,expected,atol=1e-14)
    # A dependency edit must invalidate the render cache even with the same name.
    old = inst_key(build("mixed",spec,ens))
    song.sounds["dark"]["a"]["use"] = "bass/rubber"
    assert inst_key(build("mixed",spec,ens)) != old


def test_drum_piece_blend_keeps_other_hits_and_sample_provenance(tmp_path, monkeypatch):
    import soundfile as sf
    from songmap.gui.music_lab import MusicLab
    from songmap.gui.tone_lab import design_change
    from songmap.instruments.sampler import library
    from songmap.render import render
    t = np.arange(12000)/48000
    hit = .2*np.sin(2*np.pi*150*t)*np.exp(-t*20)
    sf.write(tmp_path/"hit.wav", np.stack([hit,hit*.6],axis=1),48000)
    program = tmp_path/"hit.sfz"
    program.write_text("<region> sample=hit.wav key=60 loop_mode=one_shot")
    real_find = library.find
    monkeypatch.setattr(library,"find",lambda name: str(program) if name=="qa_snare" else real_find(name))
    from songmap.parse.fmt import to_yaml
    song = parse_text(SCORE,"a.sm")
    song.instruments["drums"] = {"kit":{"snare":{"use":"snare/dry_rim","pan":.4,"gain_db":-2}}}
    score = to_yaml(song)
    store = MusicLab(tmp_path)
    s = store.create("a.yaml",score,"drums","snare",0,2,"warm")
    s = store.add_candidate(s["id"],{"use":"sampler/qa_snare","params":{}},"B","manual")
    a, b = [parse_text(c["source"],"a.yaml") for c in s["candidates"]]
    change, reason = design_change(store,s["id"],{"pair":s["pair"],"amount":.4,"tone":{}})
    saved = store.add_candidate(s["id"],change,"Blend","design",reason)
    mixed = parse_text(saved["candidates"][-1]["source"],"a.yaml")
    ra, rb, rm = render(a),render(b),render(mixed)
    np.testing.assert_allclose(rm.stems["drums"],.6*ra.stems["drums"]+.4*rb.stems["drums"],atol=2e-6)
    np.testing.assert_array_equal(rm.stems["bass"],ra.stems["bass"])
    assert rm.sources and any(s["program"] == str(program) for s in rm.sources)


def test_http_save_design_renders_without_picking_a_winner(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from songmap.gui import lab_api, project, server
    from songmap.gui.music_lab import MusicLab
    monkeypatch.setattr(project,"ROOT",str(tmp_path))
    class Immediate:
        def submit(self, fn, *args):
            fn(*args)
    monkeypatch.setattr(lab_api,"POOL",Immediate())
    store = MusicLab(tmp_path)
    s = store.create("a.sm",SCORE,"bass",None,0,2,"warm")
    s = store.add_candidate(s["id"],{"use":"bass/rubber","params":{}},"B","manual")
    client = TestClient(server.app)
    response = client.post(f"/api/lab/sessions/{s['id']}/design",json={"pair":s["pair"],"amount":.4,"tone":{}})
    assert response.status_code == 200, response.text
    saved = store.present(s["id"])
    assert saved["status"] == "ready", saved["error"]
    assert len(saved["candidates"]) == 3 and saved["incumbent"] == s["incumbent"] and saved["feedback"] == []
    assert saved["candidates"][-1]["design"]["amount"] == .4
    assert "Blend:" in saved["candidates"][-1]["display_name"]
    assert client.get(saved["candidates"][-1]["audio"]["focus"]).content[:4] == b"RIFF"


def test_lab_connections_close_after_the_transaction(tmp_path):
    import sqlite3
    from songmap.gui.music_lab import MusicLab
    store = MusicLab(tmp_path)
    with store.db() as connection:
        connection.execute("SELECT * FROM sessions")
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connection.execute("SELECT * FROM sessions")


def test_recipe_embeds_custom_patch_so_a_target_cannot_reinterpret_it(tmp_path):
    from songmap.gui.instrument_lab import edit_voice
    from songmap.gui.music_lab import MusicLab
    from songmap.gui.tone_lab import design_change
    from songmap.parse.fmt import to_yaml
    from songmap.render import render
    song = parse_text(SCORE,"a.sm")
    patch = {"modules":{"osc":{"type":"osc","wave":"sine"},"out":{"type":"out"}},"wires":["osc>out"]}
    song.patches = {"local":patch}
    song.instruments["bass"] = {"use":"patch/local"}
    source = to_yaml(song)
    store = MusicLab(tmp_path)
    s = store.create("a.yaml",source,"bass",None,0,2,"body")
    change, _ = design_change(store,s["id"],{"base":s["incumbent"],"tone":{"tone_body":.3}})
    a = parse_text(edit_voice(source,"a.yaml","bass",None,change),"a.yaml")
    import copy
    song.patches["local"] = copy.deepcopy(patch)
    song.patches["local"]["modules"]["osc"]["wave"] = "square"
    target = parse_text(edit_voice(to_yaml(song),"b.yaml","bass",None,change),"b.yaml")
    np.testing.assert_array_equal(render(a).stems["bass"],render(target).stems["bass"])


def test_sound_change_preserves_compact_voice_pan_and_gain():
    from songmap.gui.instrument_lab import edit_voice
    from songmap.arrange.ensemble import Ensemble
    source = SCORE.replace("bass=bass/sub","bass=bass/sub(pan=.4,gain_db=-3)")
    changed = edit_voice(source,"a.sm","bass",None,{"use":"bass/rubber","params":{}})
    voice = Ensemble(parse_text(changed,"a.sm")).voice("bass")
    assert voice.pan == .4 and voice.gain_db == -3


def test_sound_wrapper_preserves_sample_sequence_past_eight_notes(tmp_path, monkeypatch):
    import soundfile as sf
    from songmap.gui.instrument_lab import edit_voice
    from songmap.instruments.sampler import Sampler, library
    from songmap.render import render
    sf.write(tmp_path/"take.wav", .1*np.sin(np.arange(2400)*.04),48000)
    program = tmp_path/"take.sfz"
    program.write_text("<region> sample=take.wav lokey=0 hikey=127 pitch_keycenter=60 seq_length=3 seq_position=1")
    real_find, original = library.find, Sampler.render
    monkeypatch.setattr(library,"find",lambda name:str(program) if name=="qa_sequence" else real_find(name))
    seen = []
    def capture(self, note):
        if self.library=="qa_sequence":
            seen.append(note.rr)
        return original(self,note)
    monkeypatch.setattr(Sampler,"render",capture)
    source = SCORE.replace("bass=bass/sub","bass=sampler/qa_sequence").replace("verse 1", "verse 2")
    baseline = render(parse_text(source,"a.sm"))
    before = list(seen)
    seen.clear()
    changed = edit_voice(source,"a.sm","bass",None,{"use":"sound/neutral","params":{},
                         "sounds":{"neutral":{"a":{"use":"sampler/qa_sequence","params":{}}}}})
    actual = render(parse_text(changed,"a.sm"))
    assert before == seen == list(range(16))
    np.testing.assert_allclose(actual.stems["bass"],baseline.stems["bass"],atol=1e-14)
