"""C2, C3, C4, C5 one at a time (65.41, 130.81, 261.63, 523.25 Hz), then all four together."""
from _lib import tone, chord, silence, seq, freq


def render():
    cs = [freq(m) for m in (36, 48, 60, 72)]
    return seq([seq([tone(f, 1.0, "clean/organ") for f in cs], gap=0.2), silence(0.5), chord(cs, 3.0, vel=0.45)])
