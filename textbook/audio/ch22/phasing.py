"""ch22: phasing, as in Reich's early works (the pattern here is written for this book). Two players repeat the
same eight-note pattern; the second plays very slightly faster and drifts ahead, one note per twelve repetitions."""
import numpy as np
from _lib import tone, at, freq

PATTERN = [64, 67, 71, 74, 72, 67, 76, 74]     # E4 G4 B4 D5 C5 G4 E5 D5
D1 = 0.15                                        # seconds per note, player 1
CYCLES = 16
D2 = D1 - D1 / (len(PATTERN) * 12)              # player 2 gains one note every 12 cycles


def pan(x, left, right):
    y = x.copy()
    y[:, 0] *= left
    y[:, 1] *= right
    return y


def render():
    notes = {m: tone(freq(m), 0.12, preset="clean/keys", vel=0.4) for m in set(PATTERN)}
    clips = []
    n = len(PATTERN) * CYCLES
    for i in range(n):
        m = PATTERN[i % len(PATTERN)]
        clips.append((i * D1, pan(notes[m], 1.0, 0.45)))
        clips.append((i * D2, pan(notes[m], 0.45, 1.0)))
    return at(clips)
