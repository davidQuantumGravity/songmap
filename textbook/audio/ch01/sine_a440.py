"""A pure 440 Hz sine (A4), then the same frequency on a harmonic organ-like tone."""
from _lib import sine, tone, silence, seq


def render():
    return seq([sine(440.0, 3.0, amp=0.35), silence(0.6), tone(440.0, 3.0, "clean/organ")])
