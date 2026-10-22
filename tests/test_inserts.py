"""Insert effects: units, the `inserts` directive, rendering, fmt round trips and the Studio's text edits."""
import numpy as np
import pytest

from songmap.arrange.expand import expand
from songmap.export.qa import lufs
from songmap.gui.mixer import set_inserts
from songmap.gui.project import parse_text
from songmap.mix.inserts import UNITS, apply_chain, make
from songmap.parse.errors import SongError
from songmap.parse.fmt import to_sm, to_yaml
from songmap.render import render

SONG = """song "Ins" 110 4/4 A fps=30 seed=2 tail=1
chords Am F C G
mix keys -3 | lead 2
verse 2 | keys:comp bass:sub lead:{deg: "=mf 4/4 2 0 2 | 4/2 5/2"}
"""


def test_every_unit_processes_stereo_and_bypasses():
    rng = np.random.default_rng(0)
    x = rng.standard_normal((24000, 2)) * 0.1
    for name in UNITS:
        y = make({"fx": name})(x, {"tempo": 120, "seed": 1})
        assert y.shape == x.shape and np.isfinite(y).all(), name
        assert np.array_equal(make({"fx": name, "on": 0})(x, {}), x), name
    drive = make({"fx": "drive", "amount": 0.9})(x, {})
    assert abs(np.sqrt(np.mean(drive ** 2)) - np.sqrt(np.mean(x ** 2))) < 1e-6      # loudness kept


def test_directive_validates_and_round_trips():
    song = parse_text(SONG.replace("mix keys", "inserts keys eq(high=-6, hp=150) chorus | master comp(ratio=2)\nmix keys"), "i.sm")
    assert song.mix["keys"]["inserts"] == [{"fx": "eq", "high": -6, "hp": 150}, {"fx": "chorus"}]
    assert song.mix["keys"]["gain_db"] == -3                       # the mix line keeps the chain
    for text, name in ((to_sm(song), "i.sm"), (to_yaml(song), "i.yaml")):
        back = parse_text(text, name)
        assert back.mix["keys"]["inserts"] == song.mix["keys"]["inserts"] and back.mix["master"] == song.mix["master"]
    for bad, msg in (("eqq(high=2)", "did you mean eq"), ("eq(hihg=2)", "did you mean high")):
        with pytest.raises(SongError, match=msg):
            parse_text(SONG.replace("mix keys", f"inserts keys {bad}\nmix keys"), "i.sm")


def test_inserts_change_the_render_and_cache_reuses_notes():
    plain = render(parse_text(SONG, "i.sm"))
    cache = {}
    dark = render(parse_text(SONG.replace("mix keys", "inserts keys eq(lp=1200, high=-12) gain(db=-6)\nmix keys"), "i.sm"),
                  note_cache=cache)
    assert lufs(dark.stems["keys"]) < lufs(plain.stems["keys"]) - 4
    assert np.allclose(dark.stems["bass"], plain.stems["bass"])
    again = render(parse_text(SONG, "i.sm"), note_cache=cache)
    assert again.stats["notes_rendered"] == 0 and np.array_equal(again.audio, plain.audio)


def test_set_inserts_edits_lines():
    a = set_inserts(SONG, "keys", [{"fx": "eq", "high": 2}, {"fx": "chorus"}])
    assert "inserts keys eq(high=2) chorus" in a
    b = set_inserts(a, "master", [{"fx": "comp", "threshold": -12}])
    assert "inserts keys eq(high=2) chorus | master comp(threshold=-12)" in b
    assert set_inserts(set_inserts(b, "keys", []), "master", []) == SONG
    assert expand(parse_text(b, "i.sm")).digest() == expand(parse_text(SONG, "i.sm")).digest()
    assert apply_chain(np.zeros((10, 2)), [], {}).shape == (10, 2)
