"""Chord symbols, progressions and the harmony timeline (`chord_at(beat)`)."""
from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass

from ..parse.errors import NotationError
from .keys import LETTER
from .tuning import centered, pc_semitones, reject_microtone_prefix


QUALITY = {
    "": (0, 4, 7), "m": (0, 3, 7), "dim": (0, 3, 6), "aug": (0, 4, 8), "5": (0, 7),
    "sus2": (0, 2, 7), "sus4": (0, 5, 7), "6": (0, 4, 7, 9), "m6": (0, 3, 7, 9),
    "7": (0, 4, 7, 10), "maj7": (0, 4, 7, 11), "m7": (0, 3, 7, 10), "m7b5": (0, 3, 6, 10),
    "dim7": (0, 3, 6, 9), "add9": (0, 4, 7, 14), "madd9": (0, 3, 7, 14),
    "9": (0, 4, 7, 10, 14), "maj9": (0, 4, 7, 11, 14), "m9": (0, 3, 7, 10, 14),
}


_CHORD = re.compile(r"([A-G])([#b]?)(" + "|".join(sorted((q for q in QUALITY if q), key=len, reverse=True)) + r")?(?:/([A-G])([#b]?))?")


def parse_chord(sym: str) -> tuple[int, tuple, int]:
    """'F#m7/C#' -> (root pc, intervals, bass pc)."""
    reject_microtone_prefix(sym.strip(), "chord")
    m = _CHORD.fullmatch(sym.strip())
    if not m:
        raise NotationError(f"chord '{sym}' not understood; qualities: {', '.join(q or 'maj' for q in QUALITY)}")
    acc = {"#": 1, "b": -1, "": 0}
    root = pc_semitones(LETTER[m[1].lower()] + acc[m[2]])
    bass = pc_semitones(LETTER[m[4].lower()] + acc[m[5]]) if m[4] else root
    return root, QUALITY[m[3] or ""], bass


# ----------------------------------------------------------------------------
# chords in context: register, progressions, the harmony timeline
# ----------------------------------------------------------------------------
NO_CHORD = ("N.C.", "NC", "N.C")


@dataclass(frozen=True)
class Chord:
    symbol: str
    root: int            # pitch class in semitones (float once microtones exist)
    intervals: tuple
    bass: int            # pitch class (slash chords)

    @classmethod
    def parse(cls, sym: str) -> "Chord":
        root, ivs, bass = parse_chord(sym)
        return cls(sym.strip(), root, ivs, bass)

    def home_root(self, tonic: int) -> int:
        """Root MIDI note nearest the key's home tonic (within -6..+5 semitones)."""
        return tonic + centered(self.root - tonic)

    def tones(self, tonic: int) -> tuple:
        """Root-position close voicing on the home root."""
        r = self.home_root(tonic)
        return tuple(r + i for i in self.intervals)


def parse_progression(text, bpb: float = 4, chord_bars: float = 1.0) -> list[tuple["Chord | None", float]]:
    """'Em:2 C:1 | Am7:1 B7:0.5' (chord:bars; bare = `chord_bars`) or a list of symbols -> [(Chord, beats)]."""
    toks = text if isinstance(text, (list, tuple)) else str(text).replace("|", " ").split()
    out = []
    for tok in toks:
        tok = str(tok)
        sym, _, bars = tok.partition(":")
        try:
            nbars = float(bars) if bars else float(chord_bars)
        except ValueError:
            raise NotationError(f"progression: bad length in '{tok}'; write chord:bars, e.g. Em:2 or D:0.5")
        if nbars <= 0:
            raise NotationError(f"progression: '{tok}' has no length")
        out.append((None if sym in NO_CHORD else Chord.parse(sym), nbars * bpb))
    if not out:
        raise NotationError("progression is empty")
    return out


@dataclass(frozen=True)
class Span:
    start: float         # beats
    end: float
    chord: "Chord | None"
    onset: bool          # True where the harmony actually changes


class HarmonyTimeline:
    """Which chord sounds at any beat. The song's default progression loops from beat 0 (as in
    synth_v0); a section with its own progression replaces that section's span."""

    def __init__(self, spans: list[Span], tonic: int):
        self.spans = spans
        self.tonic = tonic
        self._starts = [s.start for s in spans]

    def span_at(self, beat: float) -> Span | None:
        i = bisect_right(self._starts, beat + 1e-9) - 1
        return self.spans[i] if 0 <= i < len(self.spans) and beat < self.spans[i].end - 1e-9 else None

    def chord_at(self, beat: float) -> "Chord | None":
        s = self.span_at(beat)
        return s.chord if s else None

    def changes(self, start: float, end: float) -> list[Span]:
        """Spans whose harmonic onset lies in [start, end)."""
        return [s for s in self.spans if s.onset and start - 1e-9 <= s.start < end - 1e-9]

    def symbols(self, start: float, end: float) -> list[str]:
        return [s.chord.symbol if s.chord else "N.C." for s in self.spans
                if s.end > start + 1e-9 and s.start < end - 1e-9]


def build_harmony(default: list, section_progs: list[tuple[float, float, list | None]], total: float,
                  tonic: int) -> HarmonyTimeline:
    """default: [(Chord, beats)] looping from beat 0. section_progs: [(start, end, [(Chord, beats)] or None)].

    A chord that runs across a section boundary stays one span (no new onset), so a pad that
    retriggers on chord changes behaves exactly like synth_v0's `bar % 2 == 0` rule.
    """
    pieces: list[tuple[float, float, "Chord | None", tuple]] = []    # (start, end, chord, instance id)
    for s0, s1, prog in section_progs:
        if prog is None and not default:
            pieces.append((s0, s1, None, ("nc", s0)))
        elif prog is None:
            cycle = sum(b for _, b in default)
            k = int(s0 // cycle)
            t = k * cycle
            while t < s1 - 1e-9:
                for i, (ch, b) in enumerate(default):
                    if t + b > s0 + 1e-9 and t < s1 - 1e-9:
                        pieces.append((max(t, s0), min(t + b, s1), ch, ("default", k, i)))
                    t += b
                k += 1
        else:
            t, i = s0, 0
            while t < s1 - 1e-9:
                ch, b = prog[i % len(prog)]
                pieces.append((t, min(t + b, s1), ch, ("section", s0, i)))
                t += b
                i += 1
    pieces.sort(key=lambda p: p[0])
    spans: list[Span] = []
    for j, (a, z, ch, inst) in enumerate(pieces):
        if j and pieces[j - 1][3] == inst:      # one chord split by a section boundary: keep one span
            prev = spans.pop()
            spans.append(Span(prev.start, z, ch, prev.onset))
        else:
            spans.append(Span(a, z, ch, True))
    if spans and spans[-1].end < total - 1e-9:
        spans.append(Span(spans[-1].end, total, None, True))
    return HarmonyTimeline(spans, tonic)
