"""Styles (patterns/*.yaml) expand exactly like synth_v0's parts."""
import pytest

from songmap.arrange.expand import expand
from songmap.arrange.styles import catalog, get_style


def _song(make_song, parts, bars=8, key="E minor", chords=("Em", "C", "G", "D"), before=0):
    secs = ([{"name": "pre", "bars": before}] if before else []) + [{"name": "s", "bars": bars, "parts": parts}]
    return make_song({"key": key, "harmony": {"default": list(chords), "chord_bars": 2}, "sections": secs})


def _at(arr, part, piece=None):
    return [(e.beat, e.pitches) for e in arr.parts.get(part, []) if piece is None or e.piece == piece]


@pytest.mark.parametrize("role, name", [(r, n) for r, ns in catalog().items() for n in ns])
def test_every_style_expands(make_song, role, name):
    st = get_style(role, name)
    mods = "+".join([name] + list(st.get("mods") or {}))
    arr = expand(_song(make_song, {role: mods}))
    assert arr.parts[role]


def test_drum_patterns(make_song):
    arr = expand(_song(make_song, {"drums": "full"}, bars=1))
    assert [b for b, _ in _at(arr, "drums", "kick")] == [0, 1, 2, 3]
    assert [b for b, _ in _at(arr, "drums", "snare")] == [1, 3] == [b for b, _ in _at(arr, "drums", "clap")]
    hats = [e for e in arr.parts["drums"] if e.piece == "hat"]
    assert [e.beat for e in hats] == [i / 2 for i in range(8)]
    assert hats[1].vel > hats[0].vel                                   # off-beats louder, like synth_v0
    half = expand(_song(make_song, {"drums": "half"}, bars=1))
    assert [b for b, _ in _at(half, "drums", "kick")] == [0, 2.5]


def test_fill_on_the_last_bar_of_each_8_counted_from_the_song_start(make_song):
    arr = expand(_song(make_song, {"drums": "full+fill"}, bars=8, before=4))   # bars 4..11
    fills = [e for e in arr.parts["drums"] if e.piece == "fill"]
    assert [e.beat for e in fills] == [7 * 4 + 2 + i / 4 for i in range(8)]   # bar 7 only
    assert [e.vel for e in fills] == sorted(e.vel for e in fills)


def test_open_and_hats16_mods(make_song):
    arr = expand(_song(make_song, {"drums": "full+open+hats16"}, bars=1))
    assert [b for b, _ in _at(arr, "drums", "ohat")] == [0.5, 1.5, 2.5, 3.5]
    assert [b for b, _ in _at(arr, "drums", "hat")] == [0, 1, 2, 3]
    assert len(_at(arr, "drums", "hat16")) == 16


def test_bass_octave_bounce_on_chord_roots(make_song):
    arr = expand(_song(make_song, {"bass": "eighths"}, bars=4))
    roots = [p[0] for _, p in _at(arr, "bass")]
    assert roots[:8] == [40, 52] * 4 and roots[16:24] == [36, 48] * 4    # Em then C, two octaves down + bounce
    sub = expand(_song(make_song, {"bass": "sub"}, bars=2))
    assert _at(sub, "bass") == [(0, (40,)), (4, (40,))]


def test_pad_holds_each_chord_and_lets_a_chord_ring_into_the_next_section(make_song):
    arr = expand(_song(make_song, {"pad": "warm"}, bars=4))
    assert _at(arr, "pad") == [(0, (76, 79, 83)), (8, (72, 76, 79))]
    assert {e.dur for e in arr.parts["pad"]} == {8}
    odd = expand(_song(make_song, {"pad": "warm"}, bars=3, before=1))     # starts mid-chord at bar 1
    assert _at(odd, "pad") == [(8, (72, 76, 79))]                          # synth_v0: only at chord changes
    dark = expand(_song(make_song, {"pad": "dark"}, bars=2))
    assert dict(dark.parts["pad"][0].patch)["cutoff"] == 810


def test_arp_order_wraps_up_octaves_and_brightens_over_8_bars(make_song):
    arr = expand(_song(make_song, {"arp": "up"}, bars=8))
    first = [p[0] for _, p in _at(arr, "arp")[:8]]
    assert first == [76, 79, 83, 88, 83, 79, 91, 83]          # order 0 1 2 3 2 1 4 2 over E G B
    cut = [e.params["cutoff"] for e in arr.parts["arp"][::16]]
    assert cut == [2500 + 3000 * b / 8 for b in range(8)]
    own = expand(_song(make_song, {"arp": {"style": "dark", "order": [0, 2, 1, 3]}}, bars=1))
    assert [p[0] for _, p in _at(own, "arp")[:4]] == [76, 83, 79, 88]


def test_ticks_are_seeded(make_song):
    a = expand(_song(make_song, {"fx": "ticks"}, bars=4))
    b = expand(_song(make_song, {"fx": "ticks"}, bars=4))
    assert a.digest() == b.digest()
    beats = [e.beat for e in a.parts["fx"]]
    assert all(q in beats for q in range(16)) and len(beats) > 16
