"""The pitch grid. Every pitch-class calculation goes through here.

Pitch is a float MIDI number in semitones end to end (69 = A440, 60.333 = C4 up a sixth-step).
The tuning only says how finely the octave is divided: 12 steps (12edo, the default) or 36
(36edo, ROADMAP P10, where a step is 1/3 semitone). Chord intervals and scales are written in
semitones (floats allowed), so they mean the same in any tuning. Membership tests ("is this
pitch class in the chord?") compare grid steps, never raw floats.

36edo notation (docs/GOLDEN_HARMONY.md): `^` and `v` as PREFIXES on notes, degrees, chord-relative
tones, chord roots and keys are sixth-step accidentals (`^c4`, `v3`, `^F#m`), +-1/3 semitone each.
An accent `^` stays a suffix after the duration (`c4^`). The parsers always accept the prefixes;
a song whose pitches leave the 12-step grid must declare `tuning: 36edo` (checked in expand()).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

OCTAVE = 12          # semitones per octave: the MIDI unit, fixed whatever the tuning (int keeps 12edo math exact)
FIFTH = 7            # perfect fifth in semitones (voicing drops it first)


@dataclass(frozen=True)
class Tuning:
    steps_per_octave: int = 12

    @property
    def step(self) -> float:
        """Semitones per grid step (1 in 12edo, 1/3 in 36edo)."""
        return OCTAVE / self.steps_per_octave

    def pc(self, pitch: float) -> int:
        """Pitch class as a grid-step index in [0, steps_per_octave)."""
        return int(round(pitch / self.step)) % self.steps_per_octave

    def grid(self, lo: float, hi: float) -> list[float]:
        """Every grid pitch in [lo, hi] (ints in 12edo)."""
        k0, k1 = math.ceil(lo / self.step - 1e-9), math.floor(hi / self.step + 1e-9)
        return [k * self.step if self.steps_per_octave != 12 else k for k in range(k0, k1 + 1)]

    @property
    def name(self) -> str:
        return f"{self.steps_per_octave}edo"


DEFAULT = Tuning(12)
EDO36 = Tuning(36)
SUPPORTED = {"12edo": DEFAULT, "36edo": EDO36}


def pc_semitones(x: float) -> float:
    """Pitch class in semitones, [0, 12)."""
    return x % OCTAVE


def centered(x: float) -> float:
    """Interval folded into [-6, +6) semitones (nearest octave placement)."""
    return (x + OCTAVE // 2) % OCTAVE - OCTAVE // 2


def octaves(n: float) -> float:
    return OCTAVE * n


def parse_tuning(name) -> Tuning:
    key = str(name).strip().lower().replace("-", "").replace("tet", "edo").replace("et", "edo")
    if key in SUPPORTED:
        return SUPPORTED[key]
    raise ValueError(f"tuning '{name}' is not available; valid: " + " ".join(SUPPORTED))


SIXTH = OCTAVE / 36      # one sixth-step in semitones


def split_updown(token: str) -> tuple[float, str]:
    """'^^c4' -> (+2/3, 'c4'); 'vEb' -> (-1/3, 'Eb'). Prefixes only; a suffix '^' is an accent."""
    n = 0
    i = 0
    while i < len(token) and token[i] in "^v" and i + 1 < len(token) and (token[i + 1] in "^v" or token[i + 1].isalnum()
                                                                         or token[i + 1] in "#b-[R"):
        if token[i] == "v" and not (token[i + 1] in "^v" or token[i + 1].upper() in "ABCDEFGR" or token[i + 1].isdigit()
                                    or token[i + 1] in "#b-["):
            break
        n += 1 if token[i] == "^" else -1
        i += 1
    return (n * SIXTH if n else 0), token[i:]


def on_grid(pitch: float, tuning: "Tuning" = DEFAULT) -> bool:
    k = pitch / tuning.step
    return abs(k - round(k)) < 1e-6


def reject_microtone_prefix(token: str, what: str) -> None:
    """Kept for callers that must stay on the 12 grid; the note/chord/key parsers accept prefixes."""
    from ..parse.errors import NotationError
    t = token.lstrip("({")
    if t[:1] in ("^", "v") and len(t) > 1 and (t[1].isalnum() or t[1] in "#b-[R"):
        raise NotationError(f"{what}: '{token}' uses a sixth-step accidental; this needs tuning: 36edo")
