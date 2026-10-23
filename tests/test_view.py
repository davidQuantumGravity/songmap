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
