"""Clips: explicit notes for one part in one section, and the writer that prints them as note-language text.

The piano roll edits clips; baking a generated part (a style, motifs, chord-relative figures) makes one.
`write_notes` is the inverse of `parse_motif` for letter mode: onsets and lengths on a 1/12-beat grid
(16ths and triplets), pitches as floats (36-EDO sixth-steps as ^/v), every velocity written (@NN) so section
dynamics don't apply twice. Notes that overlap without being a chord go in `&` layers.

    clip = [ClipNote(beat=0, dur=1, pitches=(60.0,), vel=.62), ...]
    write_notes(clip, bars=4, beats_per_bar=4)   ->   "c4@79 e g c+ | ..."
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

GRID = 12                                   # steps per beat: 16ths (3) and 8th/16th triplets (4, 2)
NAMES = ["c", "c#", "d", "eb", "e", "f", "f#", "g", "ab", "a", "bb", "b"]
ART_MARK = {"staccato": "'", "tenuto": "_", "marcato": "!", "accent": "^"}


def _durations() -> dict[Fraction, str]:
    """Every duration token, in beats (a quarter note is one beat), simplest spelling first."""
    out: dict[Fraction, str] = {}
    for base in (1, 2, 4, 8, 16, 32, 64):
        b = Fraction(4, base)
        for dots in ("", ".", ".."):
            total, add = b, b
            for _ in dots:
                add /= 2
                total += add
            for trip in ("", "t"):
                v = total * (Fraction(2, 3) if trip else 1)
                if (v * GRID).denominator == 1 and v not in out:
                    out[v] = f"{base}{dots}{trip}"
    for base in (1, 2, 4, 8, 16):                    # longer than a dotted whole: whole notes times N (1*2)
        for k in range(2, 65):
            v = Fraction(4, base) * k
            if v not in out and v <= 256:
                out[v] = f"{base}*{k}"
    return out


DURS = _durations()
DUR_DESC = sorted(DURS, reverse=True)


@dataclass
class ClipNote:
    beat: float                       # onset, beats from the clip's start
    dur: float                        # written length, beats
    pitches: tuple = ()
    vel: float = 0.62
    art: str = "normal"
    slur: bool = False
    tags: frozenset = field(default_factory=frozenset)


def q(x: float) -> Fraction:
    return Fraction(round(x * GRID), GRID)


def spell(p: float) -> str:
    """60 -> c, 61.3333 -> ^c#, 71.6667 -> vc+ (C5 a sixth-step down), 48 -> c-."""
    k = round(p)
    off = round((p - k) * 3)
    octave = k // 12 - 1
    name = NAMES[k % 12]
    shift = octave - 4
    return ("^" if off > 0 else "v" if off < 0 else "") + name + ("+" * shift if shift > 0 else "-" * -shift)


def fit(d: Fraction, room: Fraction | None = None) -> Fraction:
    """The written duration nearest d that fits in `room` (a note can't run into the next one in its layer)."""
    cands = [v for v in DUR_DESC if room is None or v <= room]
    if not cands:
        return DUR_DESC[-1]
    return min(cands, key=lambda v: (abs(v - d), -v))


def _rests(gap: Fraction, pos: Fraction, bar: Fraction, barlines: bool) -> list[tuple[Fraction, Fraction]]:
    """Split a silence into rest durations (and bar boundaries when bar lines are written)."""
    out = []
    while gap > 0:
        limit = gap
        if barlines:
            to_bar = bar - (pos % bar)
            limit = min(gap, to_bar)
        v = next(v for v in DUR_DESC if v <= limit)
        out.append((pos, v))
        pos += v
        gap -= v
    return out


def _layers(notes: list[ClipNote]) -> list[list[tuple]]:
    """Group notes into chords (same onset, length, velocity, articulation) and pack them into layers
    in which no chord overlaps the next."""
    groups: dict[tuple, list] = {}
    for n in notes:
        if not n.pitches or "grace" in n.tags:
            continue
        k = (q(n.beat), max(q(n.dur), Fraction(1, GRID)), round(n.vel * 127), n.art, n.slur)
        groups.setdefault(k, []).extend(n.pitches)
    chords = sorted(((b, d, v, a, s, tuple(sorted(set(ps)))) for (b, d, v, a, s), ps in groups.items()),
                    key=lambda c: (c[0], -c[1], c[5]))
    layers: list[list[tuple]] = []
    for c in chords:
        for lay in layers:
            last = lay[-1]
            if last[0] + fit(last[1]) <= c[0]:              # overlapping notes keep their length: next layer
                lay.append(c)
                break
        else:
            layers.append([c])
    return layers


def write_notes(notes: list[ClipNote], *, bars: float, beats_per_bar: float = 4) -> str:
    """Note-language text for a clip of `bars` bars (rests pad it to the full length, so it doesn't loop
    early). Bar lines are written in a layer whose notes don't cross them."""
    bar = Fraction(beats_per_bar).limit_denominator(GRID)
    total = q(bars * float(bar))
    layers = _layers(notes) or [[]]
    # grace notes are written before the note they lead into: {d,e}f4
    graces: dict[tuple, list] = {}
    onsets = sorted({(c[0], li, ci) for li, lay in enumerate(layers) for ci, c in enumerate(lay)})
    for g in sorted((n for n in notes if "grace" in n.tags and n.pitches), key=lambda n: n.beat):
        nxt = next((o for o in onsets if float(o[0]) >= g.beat - 1e-6), None)
        if nxt is not None and float(nxt[0]) - g.beat < 0.5:
            graces.setdefault((nxt[1], nxt[2]), []).extend(g.pitches)
    texts = []
    for li, lay in enumerate(layers):
        # a note may ring past the clip's end (it belongs to the bar it starts in), not into the next note
        lens = [fit(c[1], (lay[i + 1][0] - c[0]) if i + 1 < len(lay) else None) for i, c in enumerate(lay)]
        barlines = all((c[0] // bar) == ((c[0] + L - Fraction(1, 10 * GRID)) // bar) or c[0] + L > total
                       for c, L in zip(lay, lens))
        toks, pos, cur = [], Fraction(0), None

        def bar_mark(p):
            if barlines and p > 0 and p % bar == 0 and p < total:
                toks.append("|")

        def emit(tok_core: str, L: Fraction, tail: str = ""):
            nonlocal cur
            d = "" if L == cur else DURS[L]
            cur = L
            toks.append(tok_core + d + tail)

        for ci, (c, L) in enumerate(zip(lay, lens)):
            onset, _, vel, art, slur, pitches = c
            for p, v in _rests(onset - pos, pos, bar, barlines):
                bar_mark(p)
                emit("r", v)
            pos = max(pos, onset)
            bar_mark(pos)
            core = spell(pitches[0]) if len(pitches) == 1 else "[" + ",".join(spell(p) for p in pitches) + "]"
            g = graces.get((li, ci))
            if g:
                core = "{" + ",".join(spell(p) for p in g) + "}" + core
            emit(core, L, ART_MARK.get(art, "") + ("~" if slur else "") + f"@{min(127, max(0, vel))}")
            pos += L
        for p, v in _rests(total - pos, pos, bar, barlines):
            bar_mark(p)
            emit("r", v)
        texts.append(" ".join(toks))
    return " & ".join(t for t in texts if t) or "r1"


def clip_of(events, start: float, end: float) -> list[ClipNote]:
    """The expanded events (arrange.expand.XEv) of one part between two beats, as a clip."""
    return [ClipNote(e.beat - start, e.dur, tuple(float(p) for p in e.pitches), float(e.vel), e.art, e.slur,
                     frozenset(e.tags)) for e in events if start - 1e-9 <= e.beat < end - 1e-9 and e.pitches]
