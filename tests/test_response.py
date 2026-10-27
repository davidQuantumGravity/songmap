import numpy as np


def test_measured_gain_is_opt_in_and_preserves_dynamic_ratios(monkeypatch):
    from songmap.instruments import make,Note
    from songmap.instruments import response
    monkeypatch.setattr(response,'profiles',lambda:{'clean/sine':{'gain_db':-6}})
    raw=make('clean/sine');cal=make('clean/sine',calibration=1)
    for vel in [.3,.6,.9]:
        note=Note(60.3,vel,.2)
        np.testing.assert_allclose(cal.render(note),raw.render(note)*10**(-6/20),atol=1e-14)
    np.testing.assert_array_equal(make('clean/sine',calibration=0).render(Note()),make('clean/sine').render(Note()))


def test_calibration_profile_changes_invalidate_note_cache(monkeypatch):
    from songmap.instruments import make,response
    from songmap.render import inst_key
    p={'clean/sine':{'gain_db':-3}}
    monkeypatch.setattr(response,'profiles',lambda:p)
    a=inst_key(make('clean/sine',calibration=1));p['clean/sine']['gain_db']=-8
    assert a!=inst_key(make('clean/sine',calibration=1))
