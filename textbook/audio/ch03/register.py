"""The same 12-ET minor third as two pure sines, low (C2-Eb2, 65.4 and 77.8 Hz) and then high (C5-Eb5, 523.3 and 622.3 Hz)."""
from _lib import sine, silence, seq, freq


def render():
    lo = sine(freq(36), 3.0, 0.3, 0.05) + sine(freq(39), 3.0, 0.3, 0.05)
    hi = sine(freq(72), 3.0, 0.3, 0.05) + sine(freq(75), 3.0, 0.3, 0.05)
    return seq([lo, silence(0.7), hi])
