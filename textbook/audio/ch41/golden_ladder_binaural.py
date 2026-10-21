"""A golden beat ladder, binaural (HEADPHONES).

Level: the file starts with a 2 s reference tone (an organ A3 at the file's peak level). Set a comfortable, moderate
volume on it; everything after it is 12 dB lower (the build peak-normalizes the whole file).

Three pure sines in exact golden-chain ratios 1 : phi : phi^2 on 220 Hz (220, 355.97, 575.97 Hz).
Each voice is split between the ears with a mirrored detune: left f - d/2, right f + d/2.
The detunes form a golden ladder: d = 10, 10/phi = 6.18 and 10/phi^2 = 3.82 Hz.
The voices enter one at a time (lowest first) so each binaural rate can be heard alone, then together.
This is a sound design taken from the bliss hypothesis (GOLDEN_THEORY 3.4), not a tested stimulus.
"""
import numpy as np
from _lib import SR, PHI, silence, seq, tone

F0 = 220.0
VOICES = [(F0, 10.0), (F0 * PHI, 10.0 / PHI), (F0 * PHI ** 2, 10.0 / PHI ** 2)]
ENTRY = [0.0, 6.0, 12.0]
DUR = 26.0


def render():
    n = int(DUR * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for (f, d), t0 in zip(VOICES, ENTRY):
        on = np.clip((t - t0) / 2.0, 0, 1)                      # 2 s raised-cosine entry
        env = (0.5 - 0.5 * np.cos(np.pi * on)) * np.clip((DUR - t) / 2.0, 0, 1) ** 2
        amp = 0.18 * (f / F0) ** -0.5                           # gently softer upper voices
        out[:, 0] += amp * env * np.sin(2 * np.pi * (f - d / 2) * t)
        out[:, 1] += amp * env * np.sin(2 * np.pi * (f + d / 2) * t)
    out *= 10 ** (-12 / 20) / np.abs(out).max()
    ref = tone(220.0, 2.0, "clean/organ", attack=0.3, release=0.4)
    ref /= np.abs(ref).max()
    return seq([ref, silence(1.5), out])
