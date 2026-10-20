"""SongMap v0.2 notation: motifs, drum step strings, chord symbols, keys (reference sketch).

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

DYN = {"ppp": 0.15, "pp": 0.25, "p": 0.37, "mp": 0.5, "mf": 0.62, "f": 0.75, "ff": 0.87, "fff": 1.0}
DYN_ORDER = list(DYN)
ACCENT = {"^": ("accent", 1.2), "!": ("marcato", 1.3)}
ART = {"'": "staccato", "_": "tenuto", "!": "marcato"}
LETTER = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}

MODES = {
    "major": (0, 2, 4, 5, 7, 9, 11), "ionian": (0, 2, 4, 5, 7, 9, 11),
    "minor": (0, 2, 3, 5, 7, 8, 10), "aeolian": (0, 2, 3, 5, 7, 8, 10),
    "dorian": (0, 2, 3, 5, 7, 9, 10), "phrygian": (0, 1, 3, 5, 7, 8, 10),
    "lydian": (0, 2, 4, 6, 7, 9, 11), "mixolydian": (0, 2, 4, 5, 7, 9, 10),
    "harmonic_minor": (0, 2, 3, 5, 7, 8, 11), "melodic_minor": (0, 2, 3, 5, 7, 9, 11),
}


class NotationError(ValueError):
    """Raised with a message written for an LLM: what, where, and how to fix it."""


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


# ----------------------------------------------------------------------------
# keys and pitches
# ----------------------------------------------------------------------------
def parse_key(key: str) -> tuple[int, tuple]:
    """'E minor' | 'Em' | 'D dorian' | 'F#' -> (tonic pitch class, scale intervals)."""
    m = re.fullmatch(r"\s*([A-Ga-g])([#b]?)\s*(m(?!aj)|[a-z_]+)?\s*", key)
    if not m:
        raise NotationError(f"key '{key}' not understood; write e.g. 'E minor', 'Em', 'D dorian'")
    pc = (LETTER[m[1].lower()] + {"#": 1, "b": -1, "": 0}[m[2]]) % 12
    mode = {"m": "minor", None: "major"}.get(m[3], m[3])
    if mode not in MODES:
        raise NotationError(f"unknown mode '{mode}' in key '{key}'; valid: {', '.join(MODES)}")
    return pc, MODES[mode]


def degree_to_midi(deg: int, key: str, octave: int = 4, alter: int = 0) -> int:
    tonic, scale = parse_key(key)
    o, i = divmod(deg, 7)
    return 12 * (octave + 1) + tonic + scale[i] + 12 * o + alter


def letter_to_midi(tok: str, octave: int = 4) -> int:
    m = re.fullmatch(r"([a-g])(#|b)?([+-]*)", tok)
    if not m:
        raise NotationError(f"bad pitch '{tok}'")
    return 12 * (octave + 1) + LETTER[m[1]] + {"#": 1, "b": -1, None: 0}[m[2]] + 12 * (m[3].count("+") - m[3].count("-"))


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


# ----------------------------------------------------------------------------
# motifs
# ----------------------------------------------------------------------------
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


def parse_motif(text: str, *, deg: bool = False, key: str = "C major", octave: int = 4,
                beats_per_bar: float = 4, name: str = "motif") -> list[Ev]:
    """Parse one motif string into events (beats relative to motif start)."""
    tok_re = _DEG_TOK if deg else _PITCH_TOK

    def pitch_of(p: str) -> int:
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
        m = tok_re.match(raw)
        if not m:
            hint = "deg tokens look like 3, -2, #4, 3/8., [0,2,4]/2" if deg else "notes look like e4, f#8., c+2~, (d16), [c,e,g]2"
            raise NotationError(f"{name}: can't read token '{raw}'. {hint}")
        if m["dur"]:
            dur = parse_duration(m["dur"])
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
                evs.append(Ev(beat - off, 0.07, (g,), vel * 0.7, "staccato", tags={"grace"}))
        pitches = tuple(pitch_of(p) for p in m["chord"].split(",")) if m["chord"] else (pitch_of(m["pitch"]),)
        evs.append(Ev(beat, dur, pitches, vel, art, "~" in marks, explicit, tags))
        beat += dur
    for i0, l0, d in ramps:   # hairpin with no closing dynamic: move one step
        if d != "done":
            idx = DYN_ORDER.index(min(DYN, key=lambda k: abs(DYN[k] - l0)))
            target = DYN[DYN_ORDER[min(max(idx + (1 if d == "<" else -1), 0), len(DYN_ORDER) - 1)]]
            _apply_ramp(evs, i0, l0, target)
    return evs


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
    return max((e.beat + e.dur for e in evs), default=0.0)


# ----------------------------------------------------------------------------
# drum step strings
# ----------------------------------------------------------------------------
STEP_VEL = {"X": 1.0, "x": 0.78, "-": 0.55, "o": 0.38}


def parse_steps(s: str, beats_per_bar: float = 4, name: str = "steps") -> tuple[list[Ev], int]:
    """'X..x..x.|X.ox.x..' -> events. Chars per bar set the grid (16 = 16ths, 12 = 8th triplets).

    X accent  x normal  - soft  o ghost  . rest  f flam  r ratchet (two quick hits)
    """
    bars = [b.replace(" ", "") for b in s.split("|")]
    evs: list[Ev] = []
    for bi, seg in enumerate(bars):
        if not seg:
            raise NotationError(f"{name}: empty bar {bi + 1} in '{s}'")
        step = beats_per_bar / len(seg)
        for i, c in enumerate(seg):
            b = bi * beats_per_bar + i * step
            if c == ".":
                continue
            if c in STEP_VEL:
                evs.append(Ev(b, step, (), STEP_VEL[c], tags={"ghost"} if c == "o" else set()))
            elif c == "f":
                evs.append(Ev(b - 0.06, step, (), 0.45, tags={"flam"}))
                evs.append(Ev(b, step, (), 0.85))
            elif c == "r":
                evs.append(Ev(b, step / 2, (), 0.6))
                evs.append(Ev(b + step / 2, step / 2, (), 0.72))
            else:
                raise NotationError(f"{name}: unknown step '{c}' in bar {bi + 1}. Use X x - o . f r")
    return evs, len(bars)


# ----------------------------------------------------------------------------
# chord symbols
# ----------------------------------------------------------------------------
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
    m = _CHORD.fullmatch(sym.strip())
    if not m:
        raise NotationError(f"chord '{sym}' not understood; qualities: {', '.join(q or 'maj' for q in QUALITY)}")
    acc = {"#": 1, "b": -1, "": 0}
    root = (LETTER[m[1].lower()] + acc[m[2]]) % 12
    bass = (LETTER[m[4].lower()] + acc[m[5]]) % 12 if m[4] else root
    return root, QUALITY[m[3] or ""], bass
