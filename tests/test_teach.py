"""The theory teacher: numerals, functions, cadences, modulation, golden chords, the ear's findings."""
from songmap.arrange.expand import expand
from songmap.gui.project import parse_text
from songmap.gui.teach import analyze, roman
from songmap.theory.harmony import Chord


def num(sym, key):
    c = Chord.parse(sym)
    return roman(c.root, c.intervals, key)


def test_numerals_and_functions():
    assert [num(s, "C")["numeral"] for s in ("C", "Dm", "Em", "F", "G7", "Am", "Bdim")] == \
        ["I", "ii", "iii", "IV", "V7", "vi", "vii°"]
    assert [num(s, "C")["function"] for s in ("C", "F", "G")] == ["tonic", "predominant", "dominant"]
    assert num("Bb", "C")["numeral"] == "bVII" and num("Bb", "C")["function"] == "borrowed"
    assert num("C", "Am")["numeral"] == "III" and num("E7", "Am")["numeral"] == "V7"
    g = num("vEbg", "G")
    assert g["function"] == "golden" and g["numeral"].startswith("↓") and g["sixth_steps"] == -1


def test_cadences_modulation_and_findings():
    song = """song "T" 100 4/4 C fps=30 seed=1 tail=1
verse 2 | keys:hold prog="Dm G7"
home 1 | keys:hold prog="C:1"
away 2 | keys:hold prog="F C" key=F
"""
    a = analyze(expand(parse_text(song, "t.sm")))
    seq = [(c["symbol"], c["numeral"], c["cadence"]) for c in a["chords"]]
    assert seq[1][1] == "V7" and "authentic" in (seq[2][2] or "")
    assert any("moves to F" in s["summary"] for s in a["sections"])
    assert all("why" in f for f in a["findings"])
    assert "rises a fourth" in a["chords"][1]["motion"]["text"]
