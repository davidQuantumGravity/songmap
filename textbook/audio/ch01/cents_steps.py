"""Pairs of tones: 440 Hz, then 440 Hz raised by 100, 50, 25, 10 and 5 cents."""
from _lib import tone, silence, seq


def render():
    clips = []
    for x in (100, 50, 25, 10, 5):
        clips += [tone(440.0, 0.8, "clean/organ"), silence(0.15),
                  tone(440.0 * 2 ** (x / 1200), 0.8, "clean/organ"), silence(0.9)]
    return seq(clips)
