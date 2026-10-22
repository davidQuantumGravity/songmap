"""A golden-spectrum A3, then its own partials split between the ears (HEADPHONES for the second half).

Level: the file starts with a 2 s reference tone (an organ A3 at the file's peak level). Set a comfortable, moderate
volume on it; everything after it is 12 dB lower (the build peak-normalizes the whole file).

First, 6 s of one note: A3 on the golden pad (partials at 2^m * phi^n times 220 Hz: 220, 355.97, 440, 575.97 Hz, ...).
Then the hidden layer of "Deep Water" alone: three pure-tone pairs on the pad's first, second and fourth partials,
A3, A3*phi and A3*phi^2, each split with a mirrored detune (left f - d/2, right f + d/2) of 6.18, 3.82 and 2.36 Hz,
the golden ladder one rung below ch41's. Last, both together, as in the song: the pad gives up those three bands
(carving), and the pairs take their place.
"""
import numpy as np
from _lib import SR, silence, seq, tone

from songmap.arrange.expand import expand
from songmap.mix.binaural import carve, plan, render_layer
from songmap.parse import lang

DUR = 12.0
SONG = """song "golden A3" 44 4/4 A fps=30 seed=1 tail=0 tuning=36edo
binaural A3 A3*phi A3*phi^2 beat=6.18 level=-3 fade=2
x 2 | pad:warm
"""


def pairs():
    s = lang.loads(SONG, "golden_a3.sm")
    tl = expand(s).timeline
    return plan(s, tl), tl                  # the last section's state holds to the end of the clip


def render():
    n = int(DUR * SR)
    pad = tone(220.0, DUR - 1.0, "clean/golden_pad", vel=0.6, release=1.0)[:n]
    pad = np.pad(pad, ((0, n - len(pad)), (0, 0)))
    p, tl = pairs()
    alone = render_layer(p, tl, n, pad, SR)
    both = pad - carve(p, pad, SR) + alone
    body = seq([pad[: int(6 * SR)], silence(1.0), alone, silence(1.0), both])
    body *= 10 ** (-12 / 20) / np.abs(body).max()
    ref = tone(220.0, 2.0, "clean/organ", attack=0.3, release=0.4)
    ref /= np.abs(ref).max()
    return seq([ref, silence(1.5), body])

