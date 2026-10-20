"""WAV writing: 24-bit PCM for the song, 32-bit float for stems (pre-master, may exceed 0 dBFS)."""
from __future__ import annotations

import os
import wave

import numpy as np
from scipy.io import wavfile

from ..instruments.dsp import SR, as_stereo


def write_wav24(path: str, x: np.ndarray, sr: int = SR) -> None:
    x = as_stereo(np.asarray(x, float))
    q = np.ascontiguousarray(np.clip(np.round(x * 8388607.0), -8388608, 8388607).astype("<i4"))
    b = q.view(np.uint8).reshape(-1, 4)[:, :3].tobytes()      # little-endian: drop the high byte
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(3)
        w.setframerate(sr)
        w.writeframes(b)


def write_float(path: str, x: np.ndarray, sr: int = SR) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    wavfile.write(path, sr, as_stereo(np.asarray(x, float)).astype(np.float32))


def read_wav(path: str) -> tuple[int, np.ndarray]:
    """Any PCM/float WAV -> (sr, float array in [-1, 1], shape (n, ch))."""
    with wave.open(path, "rb") as w:
        if w.getsampwidth() == 3:
            sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
            raw = np.frombuffer(w.readframes(n), np.uint8).reshape(-1, 3)
            q = (raw[:, 0].astype(np.int32) | (raw[:, 1].astype(np.int32) << 8) | (raw[:, 2].astype(np.int32) << 16))
            q = np.where(q >= 1 << 23, q - (1 << 24), q)
            return sr, (q / 8388608.0).reshape(-1, ch)
    sr, x = wavfile.read(path)
    if x.dtype.kind == "i":
        x = x / float(np.iinfo(x.dtype).max + 1)
    return sr, x.reshape(len(x), -1).astype(float)
