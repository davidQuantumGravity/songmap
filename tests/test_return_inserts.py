"""Insert chains on the reverb returns: `inserts hall eq(...)` processes the hall's wet output."""
import numpy as np

from songmap.gui.project import Project, parse_text
from songmap.parse.fmt import to_sm, to_yaml
from songmap.render import render

SONG = """song "Returns" 120 4/4 C fps=30 seed=3 tail=1
chords C Am F G
mix keys -3 hall=.4 | bass -2
verse 2 | keys:hold bass:sub lead:{deg: "=mf 4/4 2 0 2 | 4/2 5/2"} dyn=mf
"""
CHAIN = "inserts hall eq(lp=6000, low=-4) | master comp(ratio=2)\n"


def with_chain(text=SONG, chain=CHAIN):
    return text.replace("verse 2", chain + "verse 2")


def test_directive_stores_a_return_chain():
    song = parse_text(with_chain(), "r.sm")
    assert song.mix["hall"]["inserts"] == [{"fx": "eq", "lp": 6000, "low": -4}]
    assert song.mix["master"]["inserts"] == [{"fx": "comp", "ratio": 2}]


def test_fmt_round_trips_a_return_chain():
    song = parse_text(with_chain(), "r.sm")
    for text, name in ((to_sm(song), "r.sm"), (to_yaml(song), "r.yaml")):
        back = parse_text(text, name)
        assert back.mix["hall"] == song.mix["hall"] and back.mix["master"] == song.mix["master"]


def test_render_applies_the_chain_to_the_return_only():
    plain = render(parse_text(SONG, "r.sm"))
    dark = render(parse_text(with_chain(chain="inserts hall eq(lp=2000, high=-12) gain(db=-6)\n"), "r.sm"))
    assert set(plain.stems) == set(dark.stems) and "return_hall" in plain.stems
    for k in plain.stems:
        if k != "return_hall":
            assert np.array_equal(plain.stems[k], dark.stems[k]), k
    assert np.sqrt(np.mean(dark.stems["return_hall"] ** 2)) < 0.6 * np.sqrt(np.mean(plain.stems["return_hall"] ** 2))


def test_remix_after_a_return_chain_change_matches_a_full_render(tmp_path):
    p = tmp_path / "ret.sm"
    p.write_text(SONG, encoding="utf-8")
    pr = Project.open(str(p))
    assert not pr.render().remixed
    text = with_chain()
    rd = pr.render(text)
    assert rd.remixed                                           # only the hall's chain changed
    ref = render(parse_text(text, str(p))).audio
    assert np.abs(ref - rd.audio).max() < 1e-9
    part = pr.render(with_chain(chain="inserts keys eq(high=-6)\n"))   # a part's chain renders in full
    assert not part.remixed
