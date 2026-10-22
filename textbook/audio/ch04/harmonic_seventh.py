"""C3 E3 G3 with a seventh on top: the harmonic seventh 4:5:6:7 (Bb 31.17 c low), then the 12-ET dominant seventh C E G Bb."""
from _lib import chord, silence, seq, freq


def render():
    c3 = freq(48)
    return seq([chord([c3 * r for r in (1, 5 / 4, 3 / 2, 7 / 4)], 3.5, "clean/organ"), silence(0.6),
                chord([freq(m) for m in (48, 52, 55, 58)], 3.5, "clean/organ")])
