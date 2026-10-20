"""Buses: sum placed notes into stereo buffers."""
from __future__ import annotations

import numpy as np

from ..instruments.dsp import SR, n_samples, pan_mono


class Bus:
    def __init__(self, seconds: float, name: str = "bus"):
        self.name = name
        self.x = np.zeros((n_samples(seconds), 2))

    def add(self, t: float, sig: np.ndarray, gain: float = 1.0, pan: float = 0.0):
        i = int(round(t * SR))
        if i >= len(self.x):
            return
        s = pan_mono(sig, pan) if sig.ndim == 1 else sig * np.array([1 - max(pan, 0), 1 + min(pan, 0)])
        s = s[: len(self.x) - i] * gain
        self.x[i:i + len(s)] += s
