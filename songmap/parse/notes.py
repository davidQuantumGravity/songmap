"""SongMap v0.2 note language: motifs (letter, deg and rel modes), durations, dynamics.

Motif grammar (whitespace-separated tokens; `|` bar lines are checked against the meter):

    dynamic   =ppp =pp =p =mp =mf =f =ff =fff   sets the level for following notes
              (the `=` keeps `f` the note apart from `=f` forte)
    hairpin   <  >                         ramp from the current level to the next dynamic
    note      c d e f g a b, then # or b, then octave shifts + / -     (c = C4 unless octave: set)
    degree    0 1 -3 #4 b7                 in `deg:` motifs, degrees of the key (0 = tonic)
    chord     [c,e,g]  [0,2,4]             simultaneous notes
    rest      r
    duration  1 2 4 8 16 32, dots `.`, triplet `t`   e.g. 4.  8t  16
              STICKY: a note without a duration repeats the previous one (LilyPond rule)
              in deg mode durations follow a slash: 3/8, 0/4.
    marks     ^ accent   ! marcato   ' staccato   _ tenuto   ~ slur into next (glide on mono)
    velocity  @0..127 explicit, overrides dynamics
    ghost     (e8)  parenthesized note = ghost (very soft)
    grace     {d}e4  quick grace note(s) just before the main note

Examples
    "=mf e4^ d8' c' e4_ g | a2~ g4 (e8) r"
    deg: "=p < 0 -3 0 2 | 1/2 0 =f"
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..theory.keys import LETTER, MODES, degree_to_midi, letter_to_midi, parse_key
from ..theory.tuning import DEFAULT as TUNING_12, OCTAVE, Tuning, octaves, reject_microtone_prefix
from .errors import NotationError


DYN = {"ppp": 0.15, "pp": 0.25, "p": 0.37, "mp": 0.5, "mf": 0.62, "f": 0.75, "ff": 0.87, "fff": 1.0}


DYN_ORDER = list(DYN)


ACCENT = {"^": ("accent", 1.2), "!": ("marcato", 1.3)}


ART = {"'": "staccato", "_": "tenuto", "!": "marcato"}


@dataclass
class Ev:
    beat: float                  # onset, in beats from the start of the motif/pattern
    dur: float                   # written duration in beats
    pitches: tuple = ()          # MIDI numbers; empty for unpitched (drum) hits
    vel: float = 0.62
    art: str = "normal"          # normal | staccato | tenuto | marcato | accent
    slur: bool = False           # tie/glide into the next note
    explicit_vel: bool = False   # @NN given: later dynamics layers leave it alone
    tags: set = field(default_factory=set)   # ghost, grace, flam, ...
    rel: tuple = ()              # rel mode: ((degree, octave shift), ...), resolved against the chord at expand time


class EvList(list):
    """Parsed events plus their written length in beats (trailing rests count)."""

    def __init__(self, items=(), length: float | None = None):
        super().__init__(items)
        self.length = max((e.beat + e.dur for e in self), default=0.0) if length is None else length


def parse_duration(d: str, beat_unit: int = 4) -> float:
    """'4' -> 1 beat, '8.' -> 0.75, '8t' -> 1/3, in beats of `beat_unit` notes."""
    m = re.fullmatch(r"(1|2|4|8|16|32|64)(\.*)(t?)", d)
    if not m:
        raise NotationError(f"bad duration '{d}'; use 1 2 4 8 16 32 with optional dots or t")
    base = beat_unit / int(m[1])
    total, add = base, base
    for _ in m[2]:
        add /= 2
        total += add
    return total * (2 / 3 if m[3] else 1)


_PITCH_TOK = re.compile(r"""^
    (?P<open>\()?
    (?:\{(?P<grace>[^}]+)\})?
    (?:(?P<rest>r)|\[(?P<chord>[^\]]+)\]|(?P<pitch>[a-g](?:\#|b)?[+-]*))
    (?P<dur>(?:1|2|4|8|16|32|64)\.*t?)?
    (?P<marks>[\^!'_~]*)
    (?:@(?P<vel>\d{1,3}))?
    (?P<close>\))?
$""", re.X)


_DEG_TOK = re.compile(r"""^
    (?P<open>\()?
    (?:\{(?P<grace>[^}]+)\})?
    (?:(?P<rest>r)|\[(?P<chord>[^\]]+)\]|(?P<pitch>[\#b]?-?\d+))
    (?:/(?P<dur>(?:1|2|4|8|16|32|64)\.*t?))?
    (?P<marks>[\^!'_~]*)
    (?:@(?P<vel>\d{1,3}))?
    (?P<close>\))?
$""", re.X)


# rel mode: chord tones relative to the chord sounding at that moment. `R` = root; numbers are
# chord degrees (3 = the chord's own third, 7 = its seventh, b7/#11 = altered). Durations go
# straight after `R` or an octave mark (`R8`, `5+8`), else after a slash (`5/8`).
_DUR = r"(?:1|2|4|8|16|32|64)\.*t?"
_REL_TOK = re.compile(rf"""^
    (?P<open>\()?
    (?:\{{(?P<grace>[^}}]+)\}})?
    (?:(?P<rest>r)|\[(?P<chord>[^\]]+)\]|(?P<pitch>R[+-]*|[\#b]?\d{{1,2}}[+-]*))
    (?:/(?P<dur>{_DUR})|(?P<dur2>{_DUR}))?
    (?P<marks>[\^!'_~]*)
    (?:@(?P<vel>\d{{1,3}}))?
    (?P<close>\))?
$""", re.X)

_REL_NATURAL = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}
_REL_CLASS = {2: (2, 1), 3: (3, 4), 4: (5,), 5: (7, 6, 8), 6: (9,), 7: (10, 11, 9)}   # chord intervals that count as that degree


def rel_degree(tok: str) -> tuple[int, int]:
    """'b7' -> (7, -1), 'R' -> (1, 0), '#11' -> (11, +1)."""
    if tok == "R":
        return 1, 0
    alter = {"#": 1, "b": -1}.get(tok[0], 0)
    n = int(tok.lstrip("#b"))
    if not 1 <= n <= 13:
        raise NotationError(f"rel degree '{tok}' out of range; use R, 3, 5, 7, 9, b7, #11, 13 "
                            "(durations after a number need a slash: 5/8)")
    return n, alter


def rel_to_midi(tok: str, octs: int, intervals: tuple, root_midi: float, tuning: Tuning = TUNING_12) -> float:
    """Resolve one rel token against a chord: its own 3rd/5th/7th when it has one, else diatonic."""
    n, alter = rel_degree(tok)
    compound = OCTAVE if n > 7 else 0
    base = n - 7 if n > 7 else n
    if base == 1:
        semis = 0
    elif alter:
        semis = _REL_NATURAL[base] + alter
    else:
        have = {tuning.pc(i) for i in intervals}
        semis = next((c for c in _REL_CLASS[base] if tuning.pc(c) in have), None)
        if semis is not None:     # the chord's own tone, exactly as the chord spells it
            semis = next(i % OCTAVE for i in intervals if tuning.pc(i) == tuning.pc(semis))
        if semis is None:
            semis = 10 if base == 7 and tuning.pc(3) in have else _REL_NATURAL[base]
    return root_midi + semis + compound + octaves(octs)


def parse_motif(text: str, *, deg: bool = False, rel: bool = False, key: str = "C major", octave: int = 4,
                beats_per_bar: float = 4, name: str = "motif") -> list[Ev]:
    """Parse one motif string into events (beats relative to motif start).

    rel=True: chord-relative tokens; events carry `rel` instead of `pitches` until expansion.
    """
    tok_re = _REL_TOK if rel else _DEG_TOK if deg else _PITCH_TOK

    def pitch_of(p: str):
        if rel:
            m = re.fullmatch(r"(R|[#b]?\d{1,2})([+-]*)", p.strip())
            if not m:
                raise NotationError(f"{name}: bad rel tone '{p}'; use R, 3, 5, b7, 9 with + or - for octaves")
            rel_degree(m[1])
            return m[1], m[2].count("+") - m[2].count("-")
        if deg:
            alter = {"#": 1, "b": -1}.get(p[0], 0)
            return degree_to_midi(int(p.lstrip("#b")), key, octave, alter)
        return letter_to_midi(p, octave)

    evs: list[Ev] = []
    beat, dur, level = 0.0, 1.0, DYN["mf"]
    bar_start, bar_no = 0.0, 1
    ramps: list[tuple[int, float, str]] = []   # (event index, level at start, direction)
    for raw in text.split():
        if raw == "|":
            if abs((beat - bar_start) - beats_per_bar) > 1e-6:
                raise NotationError(
                    f"{name}: bar {bar_no} has {beat - bar_start:g} beats, expected {beats_per_bar:g}. "
                    f"Check durations before bar line {bar_no} (durations are sticky).")
            bar_start, bar_no = beat, bar_no + 1
            continue
        if raw in DYN and raw != "f":
            raise NotationError(f"{name}: write dynamics with '=', e.g. '={raw}'")
        if raw.startswith("=") and raw[1:] in DYN:
            level = DYN[raw[1:]]
            if ramps and ramps[-1][2] != "done":
                i0, l0, _ = ramps[-1]
                ramps[-1] = (i0, l0, "done")
                _apply_ramp(evs, i0, l0, level)
            continue
        if raw in ("<", ">"):
            ramps.append((len(evs), level, raw))
            continue
        reject_microtone_prefix(raw, name)
        m = tok_re.match(raw)
        if not m:
            hint = ("rel tokens look like R8, R+, 5/8, b7, [R,3,5]1" if rel else
                    "deg tokens look like 3, -2, #4, 3/8., [0,2,4]/2" if deg else
                    "notes look like e4, f#8., c+2~, (d16), [c,e,g]2")
            raise NotationError(f"{name}: can't read token '{raw}'. {hint}")
        d = m["dur"] or (m["dur2"] if rel else None)
        if rel and m["dur2"] and m["pitch"] and m["pitch"][-1].isdigit():
            raise NotationError(f"{name}: '{raw}' is ambiguous; put a slash before the duration, e.g. "
                                f"{m['pitch']}/{m['dur2']}")
        if d:
            dur = parse_duration(d)
        marks = m["marks"] or ""
        vel = level
        art = "normal"
        for c in marks:
            if c in ACCENT:
                vel = min(1.0, vel * ACCENT[c][1] + 0.04)
                art = ACCENT[c][0] if art == "normal" else art
            if c in ART:
                art = ART[c]
        explicit = m["vel"] is not None
        if explicit:
            vel = int(m["vel"]) / 127
        tags = set()
        if m["open"] and m["close"]:
            vel *= 0.45
            tags.add("ghost")
        if m["rest"]:
            beat += dur
            continue
        if m["grace"]:
            gp = [pitch_of(g) for g in m["grace"].split(",")]
            for k, g in enumerate(gp):
                off = 0.08 * (len(gp) - k)
                evs.append(Ev(beat - off, 0.07, () if rel else (g,), vel * 0.7, "staccato", tags={"grace"},
                              rel=(g,) if rel else ()))
        pitches = tuple(pitch_of(p) for p in m["chord"].split(",")) if m["chord"] else (pitch_of(m["pitch"]),)
        if rel:
            evs.append(Ev(beat, dur, (), vel, art, "~" in marks, explicit, tags, rel=pitches))
        else:
            evs.append(Ev(beat, dur, pitches, vel, art, "~" in marks, explicit, tags))
        beat += dur
    for i0, l0, d in ramps:   # hairpin with no closing dynamic: move one step
        if d != "done":
            idx = DYN_ORDER.index(min(DYN, key=lambda k: abs(DYN[k] - l0)))
            target = DYN[DYN_ORDER[min(max(idx + (1 if d == "<" else -1), 0), len(DYN_ORDER) - 1)]]
            _apply_ramp(evs, i0, l0, target)
    return EvList(evs, length=max(beat, max((e.beat + e.dur for e in evs), default=0.0)))


def _apply_ramp(evs: list[Ev], i0: int, l0: float, l1: float):
    seg = [e for e in evs[i0:] if not e.explicit_vel]
    if not seg:
        return
    b0, b1 = seg[0].beat, seg[-1].beat + seg[-1].dur
    for e in seg:
        x = (e.beat - b0) / max(b1 - b0, 1e-9)
        base = l0 + (l1 - l0) * x
        ratio = e.vel / l0 if l0 else 1.0     # keep accents/ghosts relative to the ramp
        e.vel = min(1.0, base * ratio)


def motif_length(evs: list[Ev]) -> float:
    """Written length: an EvList knows it (trailing rests included); otherwise the last note's end."""
    if isinstance(evs, EvList):
        return evs.length
    return max((e.beat + e.dur for e in evs), default=0.0)
