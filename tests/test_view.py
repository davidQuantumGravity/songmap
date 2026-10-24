"""Video views: the default reproduces the classic layout; layers, colours and new layer types render."""
import numpy as np
import pytest
from PIL import ImageChops

from songmap.arrange.expand import expand
from songmap.gui.project import parse_text
from songmap.visual import view as view_mod
from songmap.visual.draw import Renderer
from songmap.visual.score import score_of

SONG = """song "View" 100 4/4 C fps=30 seed=2 tail=1
chords C Am F G
intro 2 | keys:hold
verse 2 | keys:comp lead:{deg: "=mf 4/4 2 0 2 | 4/2 5/2"}
"""


@pytest.fixture(scope="module")
def score():
    return score_of(expand(parse_text(SONG, "v.sm")))


def test_default_view_is_the_classic_layout(score):
    for size in ((1280, 720), (1920, 1080)):
        a = Renderer(score, size, "dark", 6.0).frame(5.2)
        b = Renderer(score, view={"size": list(size), "theme": "dark", "layers": view_mod.default()["layers"]}).frame(5.2)
        assert ImageChops.difference(a, b).getbbox() is None


def test_layers_colours_and_new_types(score):
    v = {"size": "vertical", "theme": "dark", "colors": {"bg": "#102030"}, "color_by": "part",
         "part_colors": {"lead": "#ff0000"},
         "layers": [{"type": "roll", "box": [.05, .1, .9, .5]}, {"type": "sections", "box": [.05, .65, .9, .05]},
                    {"type": "text", "box": [.1, .75, .8, .1], "text": "Hello", "from": 1, "to": 3},
                    {"type": "progress", "box": [.05, .95, .9, .01]}, {"type": "staff", "box": [0, 0, 1, .5], "show": False}]}
    r = Renderer(score, view=v)
    assert (r.W, r.H) == (1080, 1920)
    im = np.asarray(r.frame(2.0))
    assert tuple(im[5, 5]) == (16, 32, 48)                          # the background colour
    caption = np.asarray(r.frame(2.0))[int(.78 * 1920):int(.82 * 1920)]
    no_caption = np.asarray(r.frame(5.0))[int(.78 * 1920):int(.82 * 1920)]
    assert not np.array_equal(caption, no_caption)                   # the caption shows only in its window
    red = np.asarray(r.frame(score.notes[-1].start + 0.01))
    assert ((red[..., 0] > 200) & (red[..., 1] < 60) & (red[..., 2] < 60)).sum() > 50   # lead notes in red


def test_resolve_explains_and_files_round_trip(tmp_path):
    for bad, msg in (({"layers": [{"type": "spiral", "box": [0, 0, 1, 1]}]}, "type 'spiral'"),
                     ({"layers": [{"type": "roll", "box": [0, 0]}]}, "box is"), ({"theme": "neon"}, "theme"),
                     ({"zoom": 2}, "unknown key")):
        with pytest.raises(ValueError, match=msg):
            view_mod.resolve(bad)
    song = tmp_path / "s.sm"
    song.write_text(SONG)
    v = view_mod.default()
    v["theme"] = "dark"
    p = view_mod.save(str(song), v)
    assert p.endswith("s.view.yaml") and view_mod.load(str(song)) == {"theme": "dark"}


def test_instrument_panels_filter_parts_and_both_render(score):
    v = {"size": [800, 400], "theme": "dark", "color_by": "part",
         "part_colors": {"keys": "#0077ff", "lead": "#ff3300"},
         "layers": [{"type": "instrument", "box": [0, 0, .5, 1], "parts": ["keys"]},
                    {"type": "instrument", "box": [.5, 0, .5, 1], "parts": ["lead"]}]}
    r = Renderer(score, view=v)
    assert {n.part for n in r.instrument_panels[0].score.notes} == {"keys"}
    assert {n.part for n in r.instrument_panels[1].score.notes} == {"lead"}
    t = next(n.start for n in score.notes if n.part == "lead") + .04
    im = np.asarray(r.frame(t))
    assert ((im[:, :400, 2] > 200) & (im[:, :400, 0] < 50)).sum() > 20
    assert ((im[:, 400:, 0] > 200) & (im[:, 400:, 2] < 50)).sum() > 20


def test_panel_windows_follow_actual_bars_and_active_mode_has_no_future_notes(score):
    from dataclasses import replace
    changed = replace(score, bars=[0., 2., 5., 6.])
    v = {"layers": [{"type": "instrument", "box": [0, 0, 1, 1], "parts": ["lead"]}]}
    p = Renderer(changed, view=v).instrument_panels[0]
    assert p.window_at(4.99) == (2., 5.)
    assert p.window_at(5.) == (5., 6.)
    assert p.window_at(8.) == (5., 6.)
    v["layers"][0]["mode"] = "active"
    active = Renderer(score, view=v).instrument_panels[0]
    assert active.visible_notes(0.) == []
    t = next(n.start for n in score.notes if n.part == "lead") + .04
    assert active.visible_notes(t)
    assert all(n.start <= t < n.end for n in active.visible_notes(t))
    assert not np.array_equal(np.asarray(active.frame(0.)), np.asarray(active.frame(t)))


def test_empty_part_selection_and_panel_validation(score):
    assert not score_of(expand(parse_text(SONG, "v.sm")), []).notes
    v = {"layers": [{"type": "instrument", "box": [.25, .25, .5, .5], "parts": []}]}
    r = Renderer(score, view=v)
    assert not r.instrument_panels[0].score.notes
    im = np.asarray(r.frame(5.))
    assert np.all(im[:180] == np.array([247, 244, 238]))  # panels never draw outside their subwindow
    for patch, msg in (({"mode": "typo"}, "mode"), ({"bars": 0}, "positive integer"),
                       ({"bars": 1.5}, "positive integer"), ({"parts": "keys"}, "list of part names")):
        with pytest.raises(ValueError, match=msg):
            view_mod.resolve({"layers": [{**v["layers"][0], **patch}]})
