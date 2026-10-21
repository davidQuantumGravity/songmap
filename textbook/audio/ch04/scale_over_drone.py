"""A C major scale over a C3 drone: first in just intonation (1, 9/8, 5/4, 4/3, 3/2, 5/3, 15/8, 2), then in 12-ET."""
from _lib import tone, at, freq


def scale_over(ratios):
    c3, c4 = freq(48), freq(60)
    clips = [(0.0, tone(c3, 9.0, "clean/organ", vel=0.45)), (0.0, tone(c3 * 1.5, 9.0, "clean/organ", vel=0.35))]
    for i, r in enumerate(ratios):
        clips.append((0.6 + i * 1.0, tone(c4 * r, 0.9, "clean/organ", vel=0.55)))
    return at(clips)


def render():
    just = [1, 9 / 8, 5 / 4, 4 / 3, 3 / 2, 5 / 3, 15 / 8, 2]
    et = [2 ** (s / 12) for s in (0, 2, 4, 5, 7, 9, 11, 12)]
    a, b = scale_over(just), scale_over(et)
    return at([(0.0, a), (len(a) / 48000 + 0.8, b)])
