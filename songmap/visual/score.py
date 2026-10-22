"""What a song shows on screen: every sounding pitch, chord change, bar and section, in seconds.

`score_of(arrangement)` reads the expanded events (the same ones the renderer plays), so the picture is
exactly the audio: a note lights up for as long as it is held (written duration x gate), passing chords
carry the engine's names, and 36-ET pitches keep their sixth-steps.
"""
from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass, field

NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
LETTERS = "CDEFGAB"


@dataclass(frozen=True)
class Spelled:
    """A pitch as the book writes it: optional up/down (^ v), letter, sharp/flat, octave."""
    letter: str
    acc: int                 # -1 flat, 0 natural, +1 sharp
    ud: int                  # -1 down (v), 0, +1 up (^): one sixth-step
    octave: int
    layer: int               # 36-ET layer = sixth-steps mod 3 (0 = the 12-ET notes)

    @property
    def diatonic(self) -> int:
        """Staff position: 7 per octave, C4 = 28."""
        return self.octave * 7 + LETTERS.index(self.letter)

    @property
    def name(self) -> str:
        return ("^" if self.ud > 0 else "v" if self.ud < 0 else "") + self.letter + {1: "♯", -1: "♭", 0: ""}[self.acc]

    @property
    def text(self) -> str:
        return f"{self.name}{self.octave}"


def spell(pitch: float) -> Spelled:
    """MIDI pitch (float; sixth-steps are thirds of a semitone) -> spelling, as songmap.theory.passing.name36:
    a sixth-step above a 12-ET note is ^note, a sixth-step below the next one is vnote."""
    st = int(round(pitch * 3))
    q, r = divmod(st, 3)
    base, ud = (q, 0) if r == 0 else (q, 1) if r == 1 else (q + 1, -1)
    name = NAMES[base % 12]
    return Spelled(name[0], 1 if "#" in name else -1 if "b" in name else 0, ud, base // 12 - 1, r)


@dataclass(frozen=True)
class ScoreNote:
    part: str
    start: float             # seconds
    end: float
    pitch: float             # MIDI (float)
    vel: float

    @property
    def spelled(self) -> Spelled:
        return spell(self.pitch)


@dataclass(frozen=True)
class ChordMark:
    start: float
    end: float
    symbol: str

    @property
    def kind(self) -> str:
        """golden / silver / bronze / western, from the chord symbol (Cg, Cg7, Cs, CT13, vFg/C ...)."""
        head = self.symbol.split("/")[0]
        if re.search(r"g7?(\(|$)", head):
            return "golden"
        if re.search(r"T13(\(|$)", head):
            return "bronze"
        if re.search(r"[A-G#b]s(\(|$)", head):
            return "silver"
        return "western"


@dataclass
class Score:
    title: str
    seconds: float
    notes: list[ScoreNote]
    chords: list[ChordMark]
    bars: list[float]                        # bar start times (seconds), with the end of the last bar
    sections: list[tuple[str, float, float]]
    edo: int = 12
    _starts: list = field(default_factory=list, repr=False)

    def __post_init__(self):
        self.notes.sort(key=lambda n: (n.start, n.pitch))
        self._starts = [n.start for n in self.notes]
        self._longest = max((n.end - n.start for n in self.notes), default=0.0)

    def sounding(self, t: float) -> list[ScoreNote]:
        """Notes held at time t."""
        i = bisect_right(self._starts, t)
        lo = bisect_right(self._starts, t - self._longest - 1e-9)
        return [n for n in self.notes[lo:i] if n.end > t]

    def between(self, a: float, b: float) -> list[ScoreNote]:
        """Notes that overlap [a, b)."""
        i = bisect_right(self._starts, b)
        lo = bisect_right(self._starts, a - self._longest - 1e-9)
        return [n for n in self.notes[lo:i] if n.end > a]

    def chord_at(self, t: float) -> ChordMark | None:
        for c in self.chords:
            if c.start <= t < c.end:
                return c
        return None

    def section_at(self, t: float) -> str:
        for name, a, b in self.sections:
            if a <= t < b:
                return name
        return ""

    def bar_at(self, t: float) -> int:
        return max(0, bisect_right(self.bars, t) - 1)


def score_of(arr, parts: list[str] | None = None) -> Score:
    """Score of an Arrangement (songmap.arrange.expand.expand). Drums and silent padding notes are left out."""
    from ..render import held_beats
    tl, song = arr.timeline, arr.song
    notes = []
    for part, evs in arr.parts.items():
        if parts and part not in parts:
            continue
        for e in evs:
            if e.piece or not e.pitches or e.vel <= 0:
                continue
            t0 = tl.beat_to_sec(e.beat)
            t1 = tl.beat_to_sec(e.beat + held_beats(e))
            for p in e.pitches:
                notes.append(ScoreNote(part, t0, max(t1, t0 + 0.05), float(p), float(e.vel)))
    chords: list[ChordMark] = []
    for sp in arr.harmony.spans:
        if sp.chord is None:
            continue
        a, b = tl.beat_to_sec(sp.start), tl.beat_to_sec(sp.end)
        if chords and not sp.onset and chords[-1].symbol == sp.chord.symbol and abs(chords[-1].end - a) < 1e-6:
            chords[-1] = ChordMark(chords[-1].start, b, chords[-1].symbol)
        else:
            chords.append(ChordMark(a, b, sp.chord.symbol))
    nbars = int(round(tl.total_bars))
    bars = [tl.beat_to_sec(tl.bar_to_beat(k)) for k in range(nbars + 1)]
    sections = [(s.name, tl.beat_to_sec(s.start), tl.beat_to_sec(s.end)) for s in tl.sections]
    edo = 36 if "36" in str(getattr(song, "tuning", "")) or any(abs(n.pitch - round(n.pitch)) > 1e-6 for n in notes) else 12
    return Score(song.title or "", tl.seconds, notes, chords, bars, sections, edo)
