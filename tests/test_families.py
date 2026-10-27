import numpy as np
import pytest


def test_named_technique_selects_recording_without_changing_notes(monkeypatch):
    from songmap.instruments import family,make,Note
    monkeypatch.setattr(family,'library',lambda:{'test':{'title':'Test','default':'sustain','automatic':{'staccato':'short'},'techniques':{'sustain':'clean/sine','short':'clean/glass'}}})
    inst=make('family/test',calibration=0)
    note=Note(60.3,.6,.4,technique='short')
    np.testing.assert_array_equal(inst.render(note),make('clean/glass').render(note))
    assert inst.select(None,'staccato')=='short'
    assert inst.select(None,'legato')=='sustain'
    with pytest.raises(ValueError,match='technique'):inst.select('missing')


def test_phrase_techniques_roundtrip_and_preserve_other_parts(monkeypatch):
    from songmap.instruments import family
    from songmap.gui.project import parse_text
    from songmap.parse.fmt import to_sm,to_yaml
    from songmap.render import render
    monkeypatch.setattr(family,'library',lambda:{'test':{'title':'Test','default':'sustain','automatic':{'staccato':'short'},'techniques':{'sustain':'clean/sine','short':'clean/glass'}}})
    score='''song "Techniques" 120 4/4 C seed=4 mood=v0 tail=.2
inst lead=family/test(calibration=0) keys=epiano
chords C
a 1 | lead:{deg: "0/2 2/2", technique: sustain} keys:hold
b 1 | lead:{deg: "0/2 2/2", technique: short} keys:hold
'''
    song=parse_text(score,'x.sm');result=render(song)
    for text,path in [(to_sm(song),'y.sm'),(to_yaml(song),'y.yaml')]:
        np.testing.assert_array_equal(render(parse_text(text,path)).audio,result.audio)
    other=render(parse_text(score.replace('technique: short','technique: sustain'),'x.sm'))
    np.testing.assert_array_equal(result.stems['keys'],other.stems['keys'])
    assert not np.array_equal(result.stems['lead'],other.stems['lead'])


def test_technique_schedule_validates_beats_and_names(monkeypatch):
    from songmap.instruments import family
    from songmap.gui.project import parse_text
    from songmap.arrange.expand import expand
    monkeypatch.setattr(family,'library',lambda:{'test':{'default':'sustain','techniques':{'sustain':'clean/sine'}}})
    score='''song "Schedule" 120 4/4 C
inst voice=family/test
a 1 | voice:{deg: "0/4 2/4 4/4 0/4"}
'''
    for lane in ['[[-.5,"sustain"]]','[[true,"sustain"]]','[[4,"sustain"]]','[[0,"missing"]]','[[0,1]]','[[1,"sustain"],[0,"auto"]]']:
        with pytest.raises(ValueError):expand(parse_text(score+f'set techniques={{a: {{voice: {lane}}}}}\n','bad.sm'))
    assert all(e.technique=='sustain' for e in expand(parse_text(score+'set techniques={a: {voice: [[0,"sustain"]]}}\n','ok.sm')).parts['voice'])


def test_family_score_validates_without_audio_and_render_still_requires_it(tmp_path,monkeypatch):
    from songmap.arrange.expand import expand
    from songmap.gui.project import parse_text
    from songmap.instruments.sampler import library
    from songmap.render import render
    monkeypatch.setattr(library,'roots',lambda:[str(tmp_path)])
    text='''song "Uninstalled family" 120 4/4 C
inst voice=family/violin
a 1 | voice:{deg: "0/4 2/4 4/4 0/4", technique: pizzicato}
'''
    assert expand(parse_text(text,'test.sm')).parts['voice']
    with pytest.raises(ValueError,match='recorded range'):
        expand(parse_text(text.replace('"0/4 2/4 4/4 0/4"','"0/4 2/4 4/4 0/4", oct: -4'),'range.sm'))
    with pytest.raises(ValueError,match='unknown technique'):
        expand(parse_text(text.replace('technique: pizzicato','technique: absent'),'unknown.sm'))
    with pytest.raises(ValueError,match='not installed'):
        render(parse_text(text,'render.sm'))
