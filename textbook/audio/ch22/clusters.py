"""ch22: clusters. (1) A chromatic cluster C4..B4 built up one semitone at a time and held, in the spirit of
Ligeti's sustained clusters; (2) struck clusters in the manner of Cowell: all white keys C3..C5 with the forearm,
then all black keys in the same span."""
import numpy as np
from _lib import tone, chord, silence, seq, at, freq


def render():
    # 1. accumulate: one new semitone every 0.9 s, all held until 14 s, soft organ
    clips = []
    for k in range(12):
        t0 = 0.9 * k
        clips.append((t0, tone(freq(60 + k), 14.0 - t0, preset="clean/organ", vel=0.22)))
    build = at(clips)
    # 2. struck clusters on a piano-like preset
    white = [m for m in range(48, 73) if m % 12 in (0, 2, 4, 5, 7, 9, 11)]
    black = [m for m in range(48, 73) if m % 12 in (1, 3, 6, 8, 10)]
    w = chord([freq(m) for m in white], 2.5, preset="clean/keys", vel=0.35)
    b = chord([freq(m) for m in black], 2.5, preset="clean/keys", vel=0.35)
    return seq([build, silence(0.6), w, silence(0.4), b])
