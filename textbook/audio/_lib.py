"""Helpers for textbook audio examples written in Python (exact frequencies, physics demos).

An example file textbook/audio/<chapter>/<name>.py defines `render() -> np.ndarray` of shape (n, 2)
at 48 kHz. The build peak-normalizes it to -1 dBFS and encodes MP3. Use SongMap songs
(<name>.songmap.yaml) for anything on the 12- or 36-ET grid; use Python only when you need
exact ratios (just intervals, the harmonic series, exact phi), pure sines, or sweeps.

    from _lib import SR, tone, chord, silence, seq, sine, sweep, stereo

    def render():
        return seq([chord([220, 275, 330], 2.0), silence(0.4), chord([220, 277.18, 329.63], 2.0)])
"""
from __future__ import annotations

import numpy as np

from songmap.instruments import Note, make

SR = 48000
PHI = (1 + 5 ** 0.5) / 2
_CACHE: dict = {}


def midi(freq: float) -> float:
    return 69 + 12 * np.log2(freq / 440.0)


def freq(midi_note: float) -> float:
    return 440.0 * 2 ** ((midi_note - 69) / 12)


def inst(preset: str = "clean/organ", **params):
    key = (preset, tuple(sorted(params.items())))
    if key not in _CACHE:
        _CACHE[key] = make(preset, **params)
    return _CACHE[key]


def stereo(x: np.ndarray) -> np.ndarray:
    return x if x.ndim == 2 else np.stack([x, x], 1)


def tone(f: float, dur: float, preset: str = "clean/organ", vel: float = 0.6, **params) -> np.ndarray:
    """One note at an exact frequency (Hz), held for `dur` seconds (plus the preset's release)."""
    return stereo(inst(preset, **params).render(Note(midi(f), vel, dur)))


def chord(freqs, dur: float, preset: str = "clean/organ", vel: float = 0.5, **params) -> np.ndarray:
    parts = [tone(f, dur, preset, vel, **params) for f in freqs]
    n = max(len(p) for p in parts)
    out = np.zeros((n, 2))
    for p in parts:
        out[: len(p)] += p
    return out


def sine(f: float, dur: float, amp: float = 0.3, fade: float = 0.02) -> np.ndarray:
    """A pure sine with raised-cosine fades (for beats and difference-tone demos)."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = amp * np.sin(2 * np.pi * f * t)
    k = max(1, int(fade * SR))
    w = 0.5 - 0.5 * np.cos(np.pi * np.arange(k) / k)
    x[:k] *= w
    x[-k:] *= w[::-1]
    return stereo(x)


def sweep(f0: float, f1: float, dur: float, amp: float = 0.25) -> np.ndarray:
    """Exponential (log-frequency) sine sweep."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    k = np.log(f1 / f0) / dur
    ph = 2 * np.pi * f0 * (np.exp(k * t) - 1) / k
    x = amp * np.sin(ph)
    f = int(0.02 * SR)
    x[:f] *= np.linspace(0, 1, f)
    x[-f:] *= np.linspace(1, 0, f)
    return stereo(x)


def silence(dur: float) -> np.ndarray:
    return np.zeros((int(dur * SR), 2))


def seq(parts, gap: float = 0.0) -> np.ndarray:
    """Concatenate clips (each may ring past its nominal end; tails are overlapped into the next gap)."""
    out = []
    for p in parts:
        out.append(stereo(p))
        if gap:
            out.append(silence(gap))
    return np.concatenate(out) if out else silence(0.1)


def at(clips) -> np.ndarray:
    """Mix clips placed at times: [(seconds, clip), ...]."""
    end = max(int(t * SR) + len(c) for t, c in clips)
    out = np.zeros((end, 2))
    for t, c in clips:
        i = int(t * SR)
        out[i:i + len(c)] += stereo(c)
    return out
