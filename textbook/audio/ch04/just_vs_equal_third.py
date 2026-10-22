"""C4 with a just major third 5/4 (327.03 Hz, 386.31 c), then with the 12-ET third (329.63 Hz, 400 c), which beats about 10 times a second."""
from _lib import chord, silence, seq, freq


def render():
    c4 = freq(60)
    return seq([chord([c4, c4 * 5 / 4], 3.5, "clean/organ"), silence(0.6), chord([c4, freq(64)], 3.5, "clean/organ")])
