"""Keys, modes, scale degrees and letter pitches. Intervals are semitones; pitch-class math goes
through theory/tuning.py so a finer grid (36edo, P10) does not touch this file."""
from __future__ import annotations

import re

from ..parse.errors import NotationError
from .tuning import OCTAVE, centered, octaves, pc_semitones, split_updown


LETTER = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}


MODES = {
    "major": (0, 2, 4, 5, 7, 9, 11), "ionian": (0, 2, 4, 5, 7, 9, 11),
    "minor": (0, 2, 3, 5, 7, 8, 10), "aeolian": (0, 2, 3, 5, 7, 8, 10),
    "dorian": (0, 2, 3, 5, 7, 9, 10), "phrygian": (0, 1, 3, 5, 7, 8, 10),
    "lydian": (0, 2, 4, 6, 7, 9, 11), "mixolydian": (0, 2, 4, 5, 7, 9, 10),
    "harmonic_minor": (0, 2, 3, 5, 7, 8, 11), "melodic_minor": (0, 2, 3, 5, 7, 9, 11),
    "phrygian_dominant": (0, 1, 4, 5, 7, 8, 10),        # the 5th mode of harmonic minor (C in F minor)
}


def _chain(lo: int, hi: int) -> tuple:
    """Golden chain (generator phi ~ 25 sixth-steps) from index lo to hi, as sorted semitones."""
    return tuple(sorted(((25 * j) % 36) / 3 for j in range(lo, hi + 1)))


def _layer_mirror(scale: tuple) -> tuple:
    """Swap ^ and v (sixth-step layers): the silver counterpart of a golden scale."""
    out = []
    for x in scale:
        k = round(x * 3)
        base = 3 * round(k / 3)
        out.append(((base - (k - base)) % 36) / 3)
    return tuple(sorted(out))


# golden-ratio scales (docs/GOLDEN_THEORY.md): moment-of-symmetry chains of golden sixths, centred
# on the tonic, and silver13 = golden13 with ^ and v swapped (7 silver triads, 0 golden).
# Well-formed (MOS) sizes of the golden chain: 2, 3, 4, 7, 10, 13, 23, 36 (docs/GOLDEN_MATH.md).
# golden7 is the golden counterpart of the diatonic; golden13 the golden "chromatic" (13 phi ~ 9 octaves).
GOLDEN_MODES = {"golden3": _chain(-2, 0), "golden4": _chain(-2, 1), "golden7": _chain(-3, 3),
                "golden10": _chain(-4, 5), "golden13": _chain(-6, 6), "golden23": _chain(-11, 11)}
GOLDEN_MODES["silver13"] = _layer_mirror(GOLDEN_MODES["golden13"])
# The modes of a golden scale (textbook ch36), named by their chain window b|a: b chain notes below
# the tonic, a above. `golden7_51` is golden7's 5|1 mode (C vEb vE ^F# ^G ^Ab B on C), `golden10_36`
# the "35" decatonic; golden7 itself is golden7_33 and golden10 is golden10_45.
for _n in (7, 10):
    for _b in range(_n):
        GOLDEN_MODES[f"golden{_n}_{_b}{_n - 1 - _b}"] = _chain(-_b, _n - 1 - _b)
# the golden pentatonic (ch36): every other note of the decatonic, a chain of golden fifths C D vF ^G ^A
GOLDEN_MODES["golden_penta"] = tuple(sorted(((25 * j) % 36) / 3 for j in (-2, 0, 2, 4, 6)))
MODES.update(GOLDEN_MODES)


def parse_key(key: str) -> tuple[int, tuple]:
    """'E minor' | 'Em' | 'D dorian' | 'F#' -> (tonic pitch class, scale intervals)."""
    shift, rest = split_updown(key.strip())
    m = re.fullmatch(r"\s*([A-Ga-g])([#b]?)\s*(m(?!aj)|[a-z_]+\d*(?:_\d+)?)?\s*", rest)
    if not m:
        raise NotationError(f"key '{key}' not understood; write e.g. 'E minor', 'Em', 'D dorian'")
    pc = pc_semitones(LETTER[m[1].lower()] + {"#": 1, "b": -1, "": 0}[m[2]] + shift)
    mode = {"m": "minor", None: "major"}.get(m[3], m[3])
    if mode not in MODES:
        raise NotationError(f"unknown mode '{mode}' in key '{key}'; valid: {', '.join(MODES)}")
    return pc, MODES[mode]


def degree_to_midi(deg: int, key: str, octave: int = 4, alter: float = 0) -> float:
    tonic, scale = parse_key(key)
    o, i = divmod(deg, len(scale))
    return octaves(octave + 1) + tonic + scale[i] + octaves(o) + alter


def letter_to_midi(tok: str, octave: int = 4) -> float:
    shift, tok = split_updown(tok)
    m = re.fullmatch(r"([a-g])(#|b)?([+-]*)", tok)
    if not m:
        raise NotationError(f"bad pitch '{tok}'")
    out = (octaves(octave + 1) + LETTER[m[1]] + {"#": 1, "b": -1, None: 0}[m[2]]
           + octaves(m[3].count("+") - m[3].count("-")))
    return out + shift if shift else out


def tonic_midi(key: str) -> int:
    """The key's home tonic: the tonic nearest middle C (F#3..F4).

    This is the register synth_v0 wrote its chords in (D4, E4, A3), so chord roots and
    `rel:` patterns placed relative to it reproduce the original voicings exactly.
    """
    pc, _ = parse_key(key)
    return 5 * OCTAVE + centered(pc)
