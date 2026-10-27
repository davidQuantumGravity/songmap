"""Continuous curves must affect one held note, including through tempo ramps."""
import numpy as np
import pytest

from songmap.gui.project import parse_text
from songmap.render import render

SCORE='''song "Held" 120 4/4 C seed=3 tail=.2 mood=v0
inst voice=clean/sine
hold 2 | voice:{deg: "0/1~ | 0/1_"}
mix voice -10
'''


def test_continuous_volume_changes_inside_one_note_and_neutral_is_exact():
    original=render(parse_text(SCORE,'x.sm')).stems['voice']
    score=SCORE+'set expression={hold: {voice: {volume: [[0,1],[4,0],[8,0]]}}}\n'
    result=render(parse_text(score,'x.sm')).stems['voice']
    assert np.max(abs(result[48000:70000])) < np.max(abs(original[48000:70000]))*.6
    assert np.max(abs(result[100000:150000]))<1e-8
    neutral=render(parse_text(SCORE+'set expression={hold: {voice: {volume: 1}}}\n','x.sm')).stems['voice']
    np.testing.assert_array_equal(original,neutral)


def test_expression_roundtrip_validation_and_cache():
    from songmap.parse.fmt import to_sm,to_yaml
    score=SCORE+'set expression={hold: {voice: {pitch_cents: [[0,0],[8,50]]}}}\n'
    song=parse_text(score,'x.sm')
    for text,path in [(to_sm(song),'y.sm'),(to_yaml(song),'y.yaml')]:
        assert parse_text(text,path).expression==song.expression
    cache={};a=render(parse_text(SCORE,'x.sm'),note_cache=cache)
    b=render(song,note_cache=cache)
    assert not np.array_equal(a.stems['voice'],b.stems['voice'])
    for lane in ['[[0,0],[0,1]]','[[0,0],[9,1]]','[[0,0],[8,true]]']:
        with pytest.raises(ValueError):render(parse_text(SCORE+f'set expression={{hold: {{voice: {{volume: {lane}}}}}}}\n','bad.sm'))


def test_curve_follows_beats_during_tempo_ramp():
    from songmap.expression import Expression
    from songmap.arrange.expand import expand
    song=parse_text(SCORE.replace('hold 2 |','hold 2 | tempo="rit 120>60" ')+
                    'set expression={hold: {voice: {volume: [[0,0],[8,1]]}}}\n','ramp.sm')
    arr=expand(song);control=Expression(arr)
    times=np.array([arr.timeline.beat_to_sec(b) for b in [0,2,4,6,8]])
    np.testing.assert_allclose(control.values('voice','volume',times),[0,.25,.5,.75,1],atol=1e-8)


def test_expression_cache_identity_includes_tempo_shape():
    from songmap.expression import Expression
    from songmap.arrange.expand import expand
    lane='set expression={hold: {voice: {volume: [[0,0],[8,1]]}}}\n'
    a=Expression(expand(parse_text(SCORE.replace('hold 2 |','hold 2 | tempo="accel 80>160" ')+lane,'a.sm')))
    b=Expression(expand(parse_text(SCORE.replace('hold 2 |','hold 2 | tempo="rit 160>80" ')+lane,'b.sm')))
    assert a.fingerprint!=b.fingerprint


def test_downward_bend_retains_a_silent_buffer_end():
    from songmap.expression import apply
    from songmap.instruments import Note
    class Lane:
        def samples(self,n):return np.full(n,-200)
    source=np.ones(4800);source[-150:]=np.linspace(1,0,150)
    moved=apply(source,Note(curves={'pitch_cents':Lane()}))
    assert abs(moved[-1])<1e-12
    assert moved[2000]>.99
