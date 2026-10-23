"""Instrument fixes: no clicks at a note's end, rr varies every instrument that declares it, the open hat is
choked by the next hat hit, velocity changes the timbre of the fx, and every knob is described."""
import numpy as np
import pytest

from songmap.arrange.expand import expand
from songmap.gui.project import parse_text
from songmap.instruments import REGISTRY, Note, Sampler, make
from songmap.render import declick, render


def _mono(y):
    return y if y.ndim == 1 else y.mean(1)


@pytest.mark.parametrize("name, kw", [("impact", {"decay": 0.5}), ("impact", {}), ("tick", {"t60": 0.5, "length": 0.05}),
                                      ("zap", {"t60": 4, "length": 0.2}), ("riser", {}), ("zap", {})])
def test_fx_end_in_silence(name, kw):
    y = _mono(make(name, **kw).render(Note(60, 0.9, 1.0, seed=1)))
    assert abs(y[-1]) <= 1e-3 * np.abs(y).max()


def test_declick_fades_only_notes_that_end_loud():
    loud = np.sin(np.linspace(0, 200, 48000))
    assert abs(declick(loud)[-1]) < 1e-6 and np.array_equal(declick(loud)[:-200], loud[:-200])
    quiet = loud * np.exp(-np.linspace(0, 14, 48000))           # already decayed to about -120 dB
    assert declick(quiet) is quiet


@pytest.mark.parametrize("name", [c.name for c in REGISTRY.values() if any(q.name == "rr" for q in c.PARAMS)])
def test_rr_changes_every_instrument_that_has_it(name):
    a = make(name, rr=0).render(Note(60, 0.7, 0.4, seed=3))
    b = make(name, rr=1).render(Note(60, 0.7, 0.4, seed=3))
    assert not np.allclose(a, b), f"{name}: rr does nothing"


def test_open_hat_is_choked_by_the_next_hat():
    song = """song "H" 120 4/4 C fps=30 seed=1 tail=1
kit ohat=hat/v0_open(decay=1) hat=hat/v0
verse 1 | drums:{ohat: "x...............", hat: "....x..........."}
"""
    r = render(parse_text(song, "h.sm"))
    tl = r.arrangement.timeline
    cut = int(round(tl.beat_to_sec(1.0) * 48000))
    drums = _mono(r.stems["drums"])
    after = np.abs(drums[cut + int(0.2 * 48000):cut + int(0.6 * 48000)]).max()
    loose = song.replace("hat/v0_open(decay=1)", "hat/v0_open(decay=1, choke=0)")
    r2 = render(parse_text(loose, "h.sm"))
    after2 = np.abs(_mono(r2.stems["drums"])[cut + int(0.2 * 48000):cut + int(0.6 * 48000)]).max()
    assert after < 0.3 * after2                                 # the open hat stops when the closed one plays
    assert make("hat/v0").choke(Note())[1] == 0                  # closed hats are never cut


@pytest.mark.parametrize("name", ["riser", "impact"])
def test_velocity_brightens_the_fx(name):
    inst = make(name)

    def centroid(v):
        y = _mono(inst.render(Note(60, v, 1.0, seed=2)))
        s = np.abs(np.fft.rfft(y))
        return (s * np.fft.rfftfreq(len(y), 1 / 48000)).sum() / s.sum()
    assert centroid(1.0) > centroid(0.25) * 1.05


def test_every_knob_is_described():
    empty = [(c.name, q.name) for c in [*REGISTRY.values(), Sampler] for q in c.PARAMS if not q.doc.strip()]
    assert empty == []
    assert expand(parse_text('song "x" 100 4/4 C\nverse 1 | keys:hold\n', "x.sm"))
