"""Stacking golden sixths: chain notes j = 0..12 (j golden sixths above C4), each folded into C4..C5.

Exact cents of note j: (j * 833.09) mod 1200. After 13 notes the octave is filled by 10 steps of
99.27 c and 3 of 69.10 c (golden13); the 14th note would land 30.17 c above C (the golden comma).
"""
from _lib import PHI, freq, seq, silence, tone

C4 = freq(60)


def render():
    notes = []
    for j in range(13):
        f = C4 * PHI ** j
        while f >= 2 * C4:
            f /= 2
        notes.append(f)
    melody = [tone(f, 0.55, "clean/keys", vel=0.55) for f in notes]
    scale = [tone(f, 0.32, "clean/keys", vel=0.5) for f in sorted(notes) + [2 * C4]]
    return seq(melody + [silence(0.8)] + scale)
