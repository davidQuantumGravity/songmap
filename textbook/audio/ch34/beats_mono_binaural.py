"""Monaural beat, then binaural beat (HEADPHONES for the second half).

Level: the file starts with a 2 s reference tone (an organ A3 at the file's peak level). Set a comfortable, moderate
volume on it; everything after it is 12 dB lower (the build peak-normalizes the whole file).

Part 1 (8 s, speakers or headphones): 200 Hz and 206 Hz pure sines mixed into BOTH ears.
    The air (or the headphone driver) carries the sum, whose loudness rises and falls 6 times a second.
Part 2 (12 s, headphones only): 200 Hz in the LEFT ear only, 206 Hz in the RIGHT ear only.
    Neither ear receives a beating signal; any 6 Hz flutter you hear is made by the brain (a binaural beat).
"""
import numpy as np
from _lib import SR, silence, seq, tone

F_L, F_R = 200.0, 206.0      # beat rate = 6 Hz


def _sine(f, dur, amp, fade=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = amp * np.sin(2 * np.pi * f * t)
    k = int(fade * SR)
    w = 0.5 - 0.5 * np.cos(np.pi * np.arange(k) / k)          # raised-cosine fades
    x[:k] *= w
    x[-k:] *= w[::-1]
    return x


def render():
    a = 0.25
    mono = _sine(F_L, 8.0, a) + _sine(F_R, 8.0, a)
    part1 = np.stack([mono, mono], 1)                          # both tones in both ears
    part2 = np.stack([_sine(F_L, 12.0, a), _sine(F_R, 12.0, a)], 1)   # one tone per ear
    body = seq([part1, silence(1.5), part2])
    body *= 10 ** (-12 / 20) / np.abs(body).max()
    ref = tone(220.0, 2.0, "clean/organ", attack=0.3, release=0.4)
    ref /= np.abs(ref).max()
    return seq([ref, silence(1.5), body])
