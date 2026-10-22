"""Mood presets (`moods/*.yaml`): a song's `mood:` picks one, `balanced` when it names none.

A mood layers over the default ensemble (`defaults.yaml`) and under the song's own blocks:

    defaults.yaml  <  mood: instruments, mix, returns, groove, parts_feel  <  the song's blocks

`v0` is the synth_v0 sound exactly, with the performance layer off: the faithful Oct-13 ports
use it. Every other mood turns the performance layer on with its own groove and part feel.
"""
from __future__ import annotations

import os
from functools import lru_cache

import yaml

from ..parse.errors import SongError, did_you_mean

MOOD_DIR = os.path.join(os.path.dirname(__file__), "moods")
DEFAULT = "balanced"
KEYS = ("mood", "description", "perform", "instruments", "mix", "returns", "groove", "parts_feel")


@lru_cache(maxsize=None)
def load_moods() -> dict[str, dict]:
    out = {}
    for f in sorted(os.listdir(MOOD_DIR)):
        if f.endswith(".yaml"):
            with open(os.path.join(MOOD_DIR, f), encoding="utf-8") as fh:
                d = yaml.safe_load(fh) or {}
            bad = [k for k in d if k not in KEYS]
            if bad:
                raise SongError(f"mood {f}: unknown key '{bad[0]}'", suggestion=did_you_mean(bad[0], KEYS))
            out[d.get("mood", f[:-5])] = d
    return out


def get_mood(name: str | None, file: str | None = None) -> dict:
    moods = load_moods()
    key = name or DEFAULT
    if key not in moods:
        raise SongError(f"unknown mood '{key}'", file=file, suggestion=did_you_mean(key, moods))
    return moods[key]


def catalog() -> dict[str, str]:
    return {name: m.get("description", "") for name, m in load_moods().items()}
