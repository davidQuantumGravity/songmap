"""Maximally even (Euclidean) rhythms, each played four times on a 16th-note-like pulse grid:
E(3,8) = x..x..x.  (the tresillo), E(5,8) = x.xx.xx.  (the cinquillo),
and the 12-pulse bell pattern x.x.xx.x.x.x, whose gaps 2 2 1 2 2 2 1 are the steps of the major scale.
A soft low tone marks the start of every cycle.
"""
from _lib import tone, at, freq

PULSE = 0.18


def euclid(k, n):
    """Onsets floor(i*n/k): k onsets spread as evenly as possible over n pulses."""
    return sorted({(i * n) // k for i in range(k)})


def pattern(onsets, n, reps, t0):
    clips = []
    for r in range(reps):
        base = t0 + r * n * PULSE
        clips.append((base, tone(freq(48), 0.1, "clean/keys", vel=0.45)))
        for p in onsets:
            clips.append((base + p * PULSE, tone(freq(79), 0.07, "clean/keys", vel=0.6)))
    return clips, t0 + reps * n * PULSE


def render():
    assert euclid(3, 8) == [0, 2, 5]          # a rotation of x..x..x. (0, 3, 6)
    tres = [0, 3, 6]
    cinq = [0, 2, 3, 5, 6]                    # a rotation of euclid(5, 8) = [0, 1, 3, 4, 6]
    bell = [0, 2, 4, 5, 7, 9, 11]             # gaps 2 2 1 2 2 2 1
    clips, t = pattern(tres, 8, 4, 0.0)
    c2, t = pattern(cinq, 8, 4, t + 0.6)
    c3, t = pattern(bell, 12, 4, t + 0.6)
    return at(clips + c2 + c3)
