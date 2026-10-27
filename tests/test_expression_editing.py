import numpy as np
import pytest


SCORE='''# Preserve this authored score.
song "Editor" 120 4/4 C mood=v0 tail=.2
inst lead=clean/sine bass=clean/bass
chords C
a 2 | lead:{deg: "0/1~ | 0/1_"} bass:roots
'''


def test_unsaved_curve_edit_preserves_score_and_other_parts(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from songmap.gui import project,server
    from songmap.gui.project import parse_text
    from songmap.render import render
    monkeypatch.setattr(project,'ROOT',str(tmp_path));monkeypatch.setattr(server,'ROOT',str(tmp_path));monkeypatch.setattr(server,'_projects',{})
    path=tmp_path/'a.sm';path.write_text(SCORE,encoding='utf-8');c=TestClient(server.app)
    result=c.post('/api/op',json={'path':'a.sm','text':SCORE,'op':'expression','args':{'index':0,'part':'lead','control':'volume','points':[[0,.2],[4,1],[8,.2]]}})
    assert result.status_code==200,result.text
    data=result.json();assert data['check']['ok'];assert data['text'].startswith(SCORE.rstrip())
    assert path.read_text(encoding='utf-8')==SCORE
    old=render(parse_text(SCORE,'a.sm'));new=render(parse_text(data['text'],'a.sm'))
    np.testing.assert_array_equal(old.stems['bass'],new.stems['bass'])
    assert not np.array_equal(old.stems['lead'],new.stems['lead'])
    bad=c.post('/api/op',json={'path':'a.sm','text':SCORE,'op':'expression','args':{'index':0,'part':'lead','control':'morph_x','points':[[0,0],[8,1]]}})
    assert bad.status_code==400


def test_riff_expression_is_scoped_and_can_change_without_new_notes(tmp_path):
    from songmap.gui.music_lab import MusicLab
    store=MusicLab(tmp_path);s=store.create('a.sm',SCORE,'lead',None,0,2,'Shape the held note',scope='riff')
    changed=SCORE+'set expression={a: {lead: {volume: [[0,.2],[8,1]]}}}\n'
    result=store.add_candidate(s['id'],{'source':changed},'Swell','manual')
    assert len(result['candidates'])==2
    with pytest.raises(ValueError,match='selected part'):
        store.add_candidate(s['id'],{'source':SCORE+'set expression={a: {bass: {volume: [[0,.2],[8,1]]}}}\n'},'Wrong part','manual')


def test_morph_moves_inside_a_held_note():
    from songmap.gui.project import parse_text
    from songmap.render import render
    spec='set sounds.pair={a: {use: "clean/sine"}, b: {use: "clean/glass"}}\n'
    base=SCORE.replace('lead=clean/sine','lead=sound/pair(blend=0)')+spec
    a=render(parse_text(base,'a.sm')).stems['lead']
    b=render(parse_text(base.replace('blend=0','blend=1'),'b.sm')).stems['lead']
    moving=base+'set expression={a: {lead: {blend: [[0,0],[8,1]]}}}\n'
    y=render(parse_text(moving,'c.sm')).stems['lead']
    t=np.clip(np.arange(len(y))/48000/4,0,1)
    np.testing.assert_allclose(y,a*(1-t[:,None])+b*t[:,None],atol=1e-12)


def test_future_blend_lane_keeps_the_original_balance_before_it_starts():
    from songmap.gui.project import parse_text
    from songmap.render import render
    base=SCORE.replace('lead=clean/sine','lead=sound/pair(blend=.2)')+'b 1 | lead:{deg: "0/1_"}\n'
    base+='set sounds.pair={a: {use: "clean/sine"}, b: {use: "clean/glass"}}\n'
    old=render(parse_text(base,'a.sm')).stems['lead']
    new=render(parse_text(base+'set expression={b: {lead: {blend: [[0,1],[4,0]]}}}\n','b.sm')).stems['lead']
    np.testing.assert_array_equal(old[:90000],new[:90000])


def test_ai_lab_marks_continuous_expression_changes_on_the_selected_part(tmp_path):
    from songmap.gui.music_lab import MusicLab
    from songmap.gui.lab_score import comparison_score
    store=MusicLab(tmp_path);s=store.create('a.sm',SCORE,'lead',None,0,2,'Swell',scope='riff')
    store.add_candidate(s['id'],{'source':SCORE+'set expression={a: {lead: {volume: [[0,.2],[8,1]]}}}\n'},'Swell','manual')
    changes=comparison_score(store,s['id'])['changes']
    assert changes['lead']==['notes / expression']
    assert changes['bass']==[]
