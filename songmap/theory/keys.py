"""Keys, modes, scale degrees and letter pitches. Intervals are semitones; pitch-class math goes
through theory/tuning.py so a finer grid (36edo, P10) does not touch this file."""
from __future__ import annotations

import re

from ..parse.errors import NotationError
from .tuning import OCTAVE, centered, octaves, pc_semitones, reject_microtone_prefix


LETTER = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}


MODES = {
    "major": (0, 2, 4, 5, 7, 9, 11), "ionian": (0, 2, 4, 5, 7, 9, 11),
    "minor": (0, 2, 3, 5, 7, 8, 10), "aeolian": (0, 2, 3, 5, 7, 8, 10),
    "dorian": (0, 2, 3, 5, 7, 9, 10), "phrygian": (0, 1, 3, 5, 7, 8, 10),
    "lydian": (0, 2, 4, 6, 7, 9, 11), "mixolydian": (0, 2, 4, 5, 7, 9, 10),
    "harmonic_minor": (0, 2, 3, 5, 7, 8, 11), "melodic_minor": (0, 2, 3, 5, 7, 9, 11),
}


def parse_key(key: str) -> tuple[int, tuple]:
    """'E minor' | 'Em' | 'D dorian' | 'F#' -> (tonic pitch class, scale intervals)."""
    reject_microtone_prefix(key.strip(), "key")
    m = re.fullmatch(r"\s*([A-Ga-g])([#b]?)\s*(m(?!aj)|[a-z_]+)?\s*", key)
    if not m:
        raise NotationError(f"key '{key}' not understood; write e.g. 'E minor', 'Em', 'D dorian'")
    pc = pc_semitones(LETTER[m[1].lower()] + {"#": 1, "b": -1, "": 0}[m[2]])
    mode = {"m": "minor", None: "major"}.get(m[3], m[3])
    if mode not in MODES:
        raise NotationError(f"unknown mode '{mode}' in key '{key}'; valid: {', '.join(MODES)}")
    return pc, MODES[mode]


def degree_to_midi(deg: int, key: str, octave: int = 4, alter: int = 0) -> int:
    tonic, scale = parse_key(key)
    o, i = divmod(deg, 7)
    return octaves(octave + 1) + tonic + scale[i] + octaves(o) + alter


def letter_to_midi(tok: str, octave: int = 4) -> int:
    m = re.fullmatch(r"([a-g])(#|b)?([+-]*)", tok)
    if not m:
        raise NotationError(f"bad pitch '{tok}'")
    return (octaves(octave + 1) + LETTER[m[1]] + {"#": 1, "b": -1, None: 0}[m[2]]
            + octaves(m[3].count("+") - m[3].count("-")))


def tonic_midi(key: str) -> int:
    """The key's home tonic: the tonic nearest middle C (F#3..F4).

    This is the register synth_v0 wrote its chords in (D4, E4, A3), so chord roots and
    `rel:` patterns placed relative to it reproduce the original voicings exactly.
    """
    pc, _ = parse_key(key)
    return 5 * OCTAVE + centered(pc)
