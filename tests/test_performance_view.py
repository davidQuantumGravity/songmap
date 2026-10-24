"""Readable per-instrument notes retain microtones, octaves, gates and filtering."""
import numpy as np
import pytest

from songmap.visual.draw import Renderer
from songmap.visual.performance import PerformancePanel, chord_names
from songmap.visual.score import Score, ScoreNote
from songmap.visual.view import resolve


def score():
    return Score('Notes',4,[ScoreNote('keys',0,2,60,.6),ScoreNote('keys',0,2,60+1/3,.6),
        ScoreNote('keys',0,2,60+2/3,.6),ScoreNote('keys',0,2,72,.6),
        ScoreNote('bass',0,2,36,.6),ScoreNote('keys',2.5,3,67,.6)],[],[0,1,3,4],[('a',0,4)],36)


def panel(parts=None,**opts):
    layer={'type':'instrument','style':'performance','box':[0,0,1,1],'parts':parts or ['keys'],**opts}
    return Renderer(score(),view={'size':[900,300],'theme':'dark','layers':[layer]}).instrument_panels[0]


def test_each_pitch_retains_its_name_octave_and_gate():
    p=panel()
    assert isinstance(p,PerformancePanel)
    assert p.note_names(.2)==['C4','^C4','vC♯4','C5']
    assert p.note_names(1.5)==['C4','^C4','vC♯4','C5']  # held across a bar
    assert p.note_names(2)==[]  # exclusive gate end, no future G4
    assert p.note_names(2.5)==['G4']
    assert panel(['bass']).note_names(.2)==['C2']
    assert len(chord_names('Cg7'))==4
    assert chord_names('Cg7')==('C','vE','^G','B')


def test_chips_and_pitch_cells_show_every_distinct_sixth_step():
    p=panel();chips,font,_=p.chip_layout(.2)
    assert len(chips)==4
    for note,(x0,y0,x1,y1) in chips:
        assert 0<=x0<x1<=p.W and 0<=y0<y1<p.H
    p.frame(.2)
    cells=dict(p.pitch_cells())
    assert cells[180]!=cells[181]!=cells[182]
    notes=p.active_notes(.2)
    assert len({p.note_x(n,p.window_at(.2)) for n in notes[:3]})==3
    # A different instrument cannot appear merely because it shares an onset.
    assert all(n.part=='keys' for n,_ in chips)


def test_dense_chord_wraps_without_dropping_notes_and_layout_options_work():
    sc=score()
    sc.notes=[ScoreNote('keys',0,2,48+i/3,.6) for i in range(20)]
    sc.__post_init__()
    v={'size':[900,340],'theme':'dark','layers':[{'type':'instrument','style':'performance',
       'parts':['keys'],'box':[0,0,1,1]}]}
    r=Renderer(sc,view=v);p=r.instrument_panels[0]
    chips,font,_=p.chip_layout(.1)
    assert len(chips)==20 and len({box[1] for _,box in chips})>1
    assert all(box[3]<p.H for _,box in chips)
    assert np.asarray(r.frame(.1)).shape==(340,900,3)
    baseline=np.asarray(r.frame(.3))
    v['layers'][0].update(note_chips=False,pitch_strip=False,glow=False)
    changed=np.asarray(Renderer(sc,view=v).frame(.3))
    assert not np.array_equal(baseline,changed)


def test_active_only_and_small_clipped_panels_are_safe():
    p=panel(mode='active')
    assert p.visible_notes(2)==[] and p.visible_notes(2.6)
    v={'size':[600,300],'layers':[{'type':'instrument','style':'performance','parts':['keys'],
                                  'box':[.5,.5,.1,.1]}]}
    im=np.asarray(Renderer(score(),view=v).frame(.1))
    resting=np.asarray(Renderer(score(),view=v).frame(2.1))
    assert np.array_equal(im[:150],resting[:150])
    assert np.array_equal(im[:,:300],resting[:,:300])
    assert im.shape==(300,600,3)


@pytest.mark.parametrize('patch',[{'style':'glitter'},{'note_chips':'yes'},{'pitch_strip':3},{'glow':None}])
def test_invalid_performance_options_are_explained(patch):
    with pytest.raises(ValueError,match='instrument'):
        resolve({'layers':[{'type':'instrument','box':[0,0,1,1],**patch}]})
