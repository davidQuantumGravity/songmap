"""Chord symbols, progressions and the harmony timeline (`chord_at(beat)`)."""
from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass, field, replace

from ..parse.errors import NotationError
from .keys import LETTER
from .tuning import SIXTH, centered, pc_semitones


QUALITY = {
    "": (0, 4, 7), "m": (0, 3, 7), "dim": (0, 3, 6), "aug": (0, 4, 8), "5": (0, 7),
    "sus2": (0, 2, 7), "sus4": (0, 5, 7), "6": (0, 4, 7, 9), "m6": (0, 3, 7, 9),
    "7": (0, 4, 7, 10), "maj7": (0, 4, 7, 11), "mmaj7": (0, 3, 7, 11), "m7": (0, 3, 7, 10), "m7b5": (0, 3, 6, 10),
    "dim7": (0, 3, 6, 9), "add9": (0, 4, 7, 14), "madd9": (0, 3, 7, 14),
    "9": (0, 4, 7, 10, 14), "maj9": (0, 4, 7, 11, 14), "m9": (0, 3, 7, 10, 14),
    # 36edo golden family (docs/GOLDEN_THEORY.md): stacked golden thirds 2/phi ~ 11 sixth-steps
    "g": (0, 11 / 3, 22 / 3), "g7": (0, 11 / 3, 22 / 3, 11),
    "s": (0, 10 / 3, 20 / 3),            # silver: stacked golden minor thirds (0-10-20)
    "T13": (0, 13 / 3, 26 / 3),          # golden's partner on the equal-third line
}
DEGREE_INDEX = {3: 1, 5: 2, 7: 3, 9: 4}


_QUAL = "|".join(sorted((re.escape(q) for q in QUALITY if q), key=len, reverse=True))
_CHORD = re.compile(r"([\^v]*)([A-G])([#b]?)(" + _QUAL + r")?(?:\(([^)]*)\))?(?:/([\^v]*)([A-G])([#b]?))?")
_ACC = {"#": 1, "b": -1, "": 0}


def _ud(prefix: str) -> float:
    n = prefix.count("^") - prefix.count("v")
    return n * SIXTH if n else 0


def parse_chord(sym: str) -> tuple[float, tuple, float]:
    """'F#m7/C#' -> (root pc, intervals, bass pc). 36edo: '^C', 'vEbm', 'Cg', 'Cg7', 'C(v3,^5)', 'Cs'."""
    m = _CHORD.fullmatch(sym.strip())
    if not m:
        raise NotationError(f"chord '{sym}' not understood; qualities: {', '.join(q or 'maj' for q in QUALITY)}; "
                            "sixth-step roots take ^/v prefixes (^C, vEb); alterations go in parentheses: C(v3,^5)")
    root = pc_semitones(LETTER[m[2].lower()] + _ACC[m[3]] + _ud(m[1]))
    ivs = list(QUALITY[m[4] or ""])
    if m[5]:
        for item in m[5].split(","):
            a = re.fullmatch(r"\s*([\^v]+)(\d+)\s*", item)
            if not a or int(a[2]) not in DEGREE_INDEX or DEGREE_INDEX[int(a[2])] >= len(ivs):
                raise NotationError(f"chord '{sym}': alteration '{item}' not understood; write e.g. v3, ^5, vv5, ^7 "
                                    "for a chord tone the chord has")
            ivs[DEGREE_INDEX[int(a[2])]] += _ud(a[1])
    bass = pc_semitones(LETTER[m[7].lower()] + _ACC[m[8]] + _ud(m[6])) if m[7] else root
    return root, tuple(ivs), bass


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
    # The passing engine's four-part voicing (absolute MIDI, bass first) for a chord on a golden passing
    # path, and the run it belongs to. Voiced styles play these lines instead of re-voicing the chord.
    lines: tuple | None = field(default=None, compare=False)
    run: int | None = field(default=None, compare=False)

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
        if sym.startswith("~"):
            out.append((Passing(sym), nbars * bpb))
            continue
        out.append((None if sym in NO_CHORD else Chord.parse(sym), nbars * bpb))
    if not out:
        raise NotationError("progression is empty")
    if any(isinstance(c, Passing) for c, _ in out):
        out = resolve_passing(out)
    return out


@dataclass(frozen=True)
class Passing:
    """`~g`, `~g7`, `~`, `~g@1/3`: a golden passing chord derived from its neighbours (36edo)."""
    token: str


def resolve_passing(prog: list) -> list:
    """Replace runs of placeholders between two chords by the golden chords the voice leading picks out
    (docs/GOLDEN_THEORY.md). Progressions loop, so a run at either end uses the cyclic neighbour."""
    from .passing import passing_path
    chords = [c for c, _ in prog]
    n = len(chords)
    out = list(prog)
    lines = {}                       # index -> voicing already fixed by an earlier run (its arrival)
    i, run = 0, 0
    while i < n:
        if not isinstance(chords[i], Passing):
            i += 1
            continue
        j = i
        while j < n and isinstance(chords[j], Passing):
            j += 1
        prev = next((chords[(i - k) % n] for k in range(1, n + 1) if isinstance(chords[(i - k) % n], Chord)), None)
        nxt = next((chords[(j + k) % n] for k in range(0, n) if isinstance(chords[(j + k) % n], Chord)), None)
        if prev is None or nxt is None:
            raise NotationError("progression: a passing placeholder (~g) needs real chords around it")
        toks = [chords[k].token for k in range(i, j)]
        ip, inx = (i - 1) % n, j % n
        got, path = passing_path(prev, nxt, toks, start=lines.get(ip))
        run += 1
        for k, ch in zip(range(i, j), got):
            out[k] = (ch, prog[k][1])
        # the run's endpoints get the path's voicings too, so the lines are continuous X -> P -> Y
        if isinstance(chords[ip], Chord) and ip not in lines:
            lines[ip] = path[0]
            out[ip] = (replace(out[ip][0], lines=path[0], run=run), prog[ip][1])
        if isinstance(chords[inx], Chord) and inx not in lines:
            lines[inx] = path[-1]
            out[inx] = (replace(out[inx][0], lines=path[-1], run=run), prog[inx][1])
        for k, ch in zip(range(i, j), got):
            out[k] = (replace(ch, run=run), prog[k][1])
        i = j
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
