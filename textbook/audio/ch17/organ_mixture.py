"""Pipes that fuse. A short melody (C4 D4 E4 G4 E4 D4 C4) on a soft "8-foot" tone alone; then with
"4-foot" (octave, x2) and "2 2/3-foot" (twelfth, x3) ranks playing the same melody in exact parallel
octaves and twelfths: one brighter tone. Then the same three lines with the upper two entering
0.12 s late on every note: the fusion breaks and you hear parallel lines.
"""
from _lib import tone, at, freq

MEL = [60, 62, 64, 67, 64, 62, 60]
STEP = 0.5


def line(mult, t0, lag=0.0, vel=0.55):
    pipe = dict(partials=3, rolloff=1.8)
    return [(t0 + i * STEP + lag, tone(freq(m) * mult, STEP * 0.9, "clean/organ", vel=vel, **pipe))
            for i, m in enumerate(MEL)]


def render():
    clips = line(1, 0.0)
    t1 = len(MEL) * STEP + 1.0
    clips += line(1, t1) + line(2, t1, vel=0.42) + line(3, t1, vel=0.38)
    t2 = t1 + len(MEL) * STEP + 1.0
    clips += line(1, t2) + line(2, t2, lag=0.12, vel=0.42) + line(3, t2, lag=0.12, vel=0.38)
    return at(clips)
