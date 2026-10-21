"""An exponential sine sweep from 55 Hz (A1) to 1760 Hz (A6): five octaves in 15 seconds, one octave every 3 s."""
from _lib import sweep


def render():
    return sweep(55.0, 1760.0, 15.0, amp=0.3)
