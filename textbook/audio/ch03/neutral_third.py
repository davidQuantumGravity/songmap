"""Thirds above C4 on harmonic tones: just minor third 6/5 (315.64 c), a neutral third (350 c), just major third 5/4 (386.31 c)."""
from _lib import chord, silence, seq, freq


def render():
    c4 = freq(60)
    return seq([chord([c4, c4 * r], 2.8, "clean/organ") for r in (6 / 5, 2 ** (350 / 1200), 5 / 4)], gap=0.5)
