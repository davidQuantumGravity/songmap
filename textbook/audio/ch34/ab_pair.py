"""A blind A/B pair for the listening protocol: one variable changed (timbre), everything else matched.

Both excerpts: the golden triad in exact close voicing 1 : 2/phi : 4/phi^2 on 220 Hz, 14 s, the same
envelope, no reverb. They differ only in the spectrum of the clean additive tone:
harmonic partials (1, 2, 3, ...) in one, golden partials (2^m * phi^n) in the other.
Each excerpt is scaled to the same integrated loudness (ITU-R BS.1770, -23 LUFS) before the file is
peak-normalized as a whole, so loudness cannot give the answer away.
The order (which is A and which is B) is given in the chapter's exercise answer.
"""
import numpy as np
from _lib import PHI, chord, silence, seq
from songmap.export.qa import lufs

SHAPE = [1, 2 / PHI, 4 / PHI ** 2]


def excerpt(spectrum):
    x = chord([220.0 * r for r in SHAPE], 14.0, "clean/organ", partials=10, rolloff=1.3,
              spectrum=spectrum, attack=1.5, release=1.5)
    return x * 10 ** ((-23.0 - lufs(x)) / 20)


def render():
    a = excerpt(1)      # A: golden spectrum
    b = excerpt(0)      # B: harmonic spectrum
    return seq([a, silence(3.0), b])
