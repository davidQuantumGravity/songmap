"""ch33: golden spectralism. (1) A golden-spectrum tone on C3 (partials 2^m phi^n: 1, phi, 2,
phi^2, 2phi, 4, phi^3, 2phi^2, 4phi, phi^4). (2) The same ten partials entering one by one as
pure sines, an 'unfolded' spectrum. (3) The ten partial frequencies orchestrated as a chord of
harmonic-spectrum organ tones. (4) The same chord on golden-spectrum organ tones."""
import numpy as np
from _lib import PHI, SR, at, sine, silence, seq, tone

F0 = 130.81                                   # C3
PARTS = sorted({2 ** m * PHI ** n for m in range(8) for n in range(8)})[:10]


def spectral_chord(spectrum, dur):
    clips = [(0.0, tone(F0 * p, dur, "clean/organ", vel=0.55 * (k + 1) ** -0.35, spectrum=spectrum))
             for k, p in enumerate(PARTS)]
    return at(clips)


def render():
    one = tone(F0, 3.0, "clean/organ", vel=0.7, spectrum=1, partials=10)
    end = 9.0
    unfold = at([(0.7 * k, sine(F0 * p, end - 0.7 * k, amp=0.25 * (k + 1) ** -0.6, fade=0.3))
                 for k, p in enumerate(PARTS)])
    return seq([one, silence(0.6), unfold, silence(0.6), spectral_chord(0, 4.0), silence(0.6),
                spectral_chord(1, 4.0)])
