"""A 440 Hz sine held while a second sine glides up from 440 to 660 Hz (a fifth) in 24 s: slow beats, fast beats, roughness, then two smooth tones."""
from _lib import sine, sweep


def render():
    return sine(440.0, 24.0, amp=0.22, fade=0.05) + sweep(440.0, 660.0, 24.0, amp=0.22)
