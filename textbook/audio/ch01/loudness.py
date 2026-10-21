"""A 440 Hz sine at five levels, each 6 dB (half the amplitude) below the one before."""
from _lib import sine, silence, seq


def render():
    clips = []
    for k in range(5):
        clips += [sine(440.0, 1.3, amp=0.4 * 10 ** (-6 * k / 20), fade=0.03), silence(0.35)]
    return seq(clips)
