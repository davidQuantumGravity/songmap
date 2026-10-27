"""Recorded ensemble coverage and continuous hybrids, tested at the audio boundary."""
from dataclasses import replace

import numpy as np
import pytest


def test_four_corners_and_bilinear_mix_preserve_sources():
    from songmap.arrange.ensemble import Ensemble
    from songmap.gui.project import parse_text
    from songmap.instruments import Note, make
    from songmap.instruments.sound import build
    ens=Ensemble(parse_text('song "Morph" 120 4/4 C\nchords C\nx 1 | bass:roots\n','test.sm'))
    # Choose existing native presets without relying on downloaded samples.
    from songmap.instruments.presets import list_presets
    refs=['bass/'+n for n in list_presets()['bass'][:4]]
    spec={k:{'use':use,'params':{}} for k,use in zip('abcd',refs)}
    note=Note(43.3,.7,.35,seed=53,rr=4)
    originals=[make(use).render(note) for use in refs]
    for (x,y),original in zip([(0,0),(1,0),(0,1),(1,1)],originals):
        np.testing.assert_array_equal(build('four',spec,ens,morph_x=x,morph_y=y).render(note),original)
    mixed=build('four',spec,ens,morph_x=.25,morph_y=.6).render(note)
    expected=np.zeros_like(mixed)
    for signal,weight in zip(originals,[.3,.1,.45,.15]):expected[:len(signal)]+=signal*weight
    np.testing.assert_allclose(mixed,expected,atol=1e-14)
    automated=replace(note,params={'morph_x':1,'morph_y':1})
    np.testing.assert_array_equal(build('four',spec,ens).render(automated),originals[3])
    with pytest.raises(ValueError,match='four sources'):
        build('bad',{k:spec[k] for k in 'abc'},ens)


def test_neutral_width_and_vibrato_are_exact_and_modulation_is_deterministic():
    from songmap.arrange.ensemble import Ensemble
    from songmap.gui.project import parse_text
    from songmap.instruments import Note,make
    from songmap.instruments.sound import build
    ens=Ensemble(parse_text('song "Tone" 120 4/4 C\nx 1 | keys:hold\n','x.sm'))
    spec={'a':{'use':'epiano','params':{}}};note=Note(64.2,.6,.9,seed=9)
    original=make('epiano').render(note)
    np.testing.assert_array_equal(build('tone',spec,ens).render(note),original)
    y=build('tone',spec,ens,tone_vibrato=.7).render(note)
    assert y.shape==original.shape and np.isfinite(y).all()
    np.testing.assert_array_equal(y[:8000],original[:8000])
    assert np.max(abs(y-original))>.001
    np.testing.assert_array_equal(y,build('tone',spec,ens,tone_vibrato=.7).render(note))
    # Stereo width removes only the side component at -1.
    inst=build('stereo',spec,ens,tone_width=-1)
    stereo=np.column_stack([np.linspace(0,.2,100),np.linspace(.1,0,100)])
    inst.layers[0].render=lambda _:stereo.copy()
    mono=inst.render(note)
    np.testing.assert_allclose(mono[:,0],stereo.mean(axis=1))
    np.testing.assert_array_equal(mono[:,0],mono[:,1])


def test_root_relative_nested_sfz_includes(tmp_path):
    from songmap.instruments.sampler.sfz import parse
    (tmp_path/'Data').mkdir()
    (tmp_path/'voice.sfz').write_text('#include "Data/group.txt"',encoding='utf-8')
    (tmp_path/'Data/group.txt').write_text('<group> seq_length=2\n#include "Data/notes.txt"',encoding='utf-8')
    (tmp_path/'Data/notes.txt').write_text('<region> sample=one.wav key=60',encoding='utf-8')
    p=parse(str(tmp_path/'voice.sfz'))
    assert len(p.regions)==1 and not p.unsupported and p.regions[0].seq_length==2


def test_library_recipes_refer_to_real_voices_and_ranges_overlap():
    from songmap.instruments.sound import library
    from songmap.instruments.sampler.library import manifest
    voices=manifest()['voices']
    assert len(library())>=14
    for recipe in library().values():
        assert recipe['title'] and recipe['description']
        rows=[voices[s['use'].removeprefix('sampler/')] for s in recipe['sources'].values()]
        assert max(r['range'][0] for r in rows)<min(r['range'][1] for r in rows)
    for n in ['violas','oboe','clarinet','bassoon','trumpet','trombone','tuba','mtg_soprano_sax','mtg_alto_sax','mtg_tenor_sax','mtg_baritone_sax']:
        assert voices[n]['range'][0]<voices[n]['range'][1]
    assert voices['mtg_baritone_sax']['source']=='mtg_sax'
    from songmap.gui.instrument_lab import voice_name
    assert voice_name('sound/trumpet_palette')=='Trumpet palette'
    assert voice_name('sound/trumpet_palette',{'trumpet_palette':{'a':{'use':'sampler/oboe'}}})=='Shaped Oboe · non-vibrato'


def test_mix_controls_only_apply_to_matching_saved_layout(tmp_path):
    from songmap.gui.music_lab import MusicLab
    from songmap.gui.tone_lab import design_change
    store=MusicLab(tmp_path)
    s=store.create('a.sm','song "Tone" 120 4/4 C\nchords C\nx 1 | bass:roots\n','bass',None,0,2,'warm')
    with pytest.raises(ValueError,match='matching source layout'):
        design_change(store,s['id'],{'base':s['pair'][0],'tone':{'morph_x':.5}})


def test_library_definition_can_be_overridden_by_the_score(monkeypatch):
    from songmap.arrange.ensemble import Ensemble
    from songmap.gui.project import parse_text
    from songmap.instruments import sound
    from songmap.parse.fmt import to_sm,to_yaml
    a={'a':{'use':'bass/sub','params':{}}}
    b={'a':{'use':'bass/rubber','params':{}}}
    monkeypatch.setattr(sound,'library',lambda:{'test':{'sources':a}})
    song=parse_text('song "Local" 120 4/4 C\nchords C\ninst bass=sound/test\nx 1 | bass:roots\n','a.sm')
    assert Ensemble(song).sound_spec('test')==a
    song.sounds={'test':b}
    for text,path in [(to_sm(song),'b.sm'),(to_yaml(song),'b.yaml')]:
        parsed=parse_text(text,path)
        assert Ensemble(parsed).sound_spec('test')==b
        assert Ensemble(parsed).instrument('bass').layers[0].p['cutoff']>0


def test_installer_and_parser_agree_on_root_relative_includes(tmp_path,monkeypatch):
    import json
    from songmap.instruments.sampler import library,install
    files={'voice.sfz':b'#include "Data/group.txt"','Data/group.txt':b'<group> seq_length=2\n#include "Data/notes.txt"',
           'Data/notes.txt':b'<region> key=60 sample=hit.wav','hit.wav':b'fixture audio'}
    src=dict(repo='test/include',revision='a'*40,license='CC0',credit='Fixture',url='https://example.com')
    voice=dict(source='fixture',program='voice.sfz',family='keys')
    monkeypatch.setattr(library,'manifest',lambda:{'sources':{'fixture':src},'voices':{'voice':voice}})
    tree={'tree':[dict(path=k,type='blob',sha=install._blob(v),size=len(v)) for k,v in files.items()]}
    monkeypatch.setattr(install,'_read',lambda url:json.dumps(tree).encode() if 'api.github' in url else files[url.split(src['revision']+'/')[1]])
    install.install(['voice'],root=tmp_path,log=lambda _:None)
    assert install.verify(tmp_path)['ok']
