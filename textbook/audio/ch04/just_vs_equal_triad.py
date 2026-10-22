"""The C major triad tuned 4:5:6 (just), then in 12-ET."""
from _lib import chord, silence, seq, freq


def render():
    c4 = freq(60)
    return seq([chord([c4, c4 * 5 / 4, c4 * 3 / 2], 3.5, "clean/organ"), silence(0.6),
                chord([freq(60), freq(64), freq(67)], 3.5, "clean/organ")])
