"""Fifths on A3: exact 220 + 330 Hz on harmonic tones (smooth), 220 + 331 Hz on harmonic tones (beats twice a second), 220 + 331 Hz as pure sines (no clear beat)."""
from _lib import chord, sine, silence, seq


def render():
    a = chord([220.0, 330.0], 3.5, "clean/organ")
    b = chord([220.0, 331.0], 3.5, "clean/organ")
    c = sine(220.0, 3.5, 0.25, 0.05) + sine(331.0, 3.5, 0.25, 0.05)
    return seq([a, silence(0.5), b, silence(0.5), c])
