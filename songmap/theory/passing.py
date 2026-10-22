"""Sub-chromatic passing harmony in 36edo (docs/GOLDEN_THEORY.md).

Between two chords X -> Y, four-part lines (bass + three upper chord tones) move in sixth-steps:

    strict   every line moves uniformly: a half step 1+1+1 sixth-steps, a whole step 2+2+2
             (the unique path; at most one golden chord per transition, theorem 2.2)
    natural  half steps stay 1+1+1; other moves split into monotone parts of <= a semitone
             (allows two different golden chords in a row, e.g. F - vF#g - ^F#g - G)

`passing_chords(X, Y, tokens)` fills progression placeholders:
    ~      the strict path's passing chord(s), whatever they are
    ~g     golden triad or golden seventh preferred (natural path)
    ~g7    golden seventh preferred
A run of two placeholders asks for both passing chords P1, P2 of one path.
Chords are songmap Chord objects; everything inside works in integer sixth-steps.
"""
from __future__ import annotations

import hashlib
import os
import pickle
from dataclasses import dataclass
from functools import lru_cache
from itertools import permutations, product

EDO = 36
NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
TYPES = {"g": (0, 11, 22), "g7": (0, 11, 22, 33), "s": (0, 10, 20), "T13": (0, 13, 26),
         "": (0, 12, 21), "m": (0, 9, 21), "dim": (0, 9, 18), "aug": (0, 12, 24),
         "sus4": (0, 15, 21), "sus2": (0, 6, 21), "7": (0, 12, 21, 30), "maj7": (0, 12, 21, 33),
         "m7": (0, 9, 21, 30), "m7b5": (0, 9, 18, 30), "dim7": (0, 9, 18, 27), "mmaj7": (0, 9, 21, 33),
         "6": (0, 12, 21, 27), "m6": (0, 9, 21, 27)}
GOLDEN_T = ("g", "g7")
DEG = {6: "2", 9: "3", 10: "3", 11: "3", 12: "3", 13: "3", 15: "4", 18: "5", 20: "5", 21: "5", 22: "5", 24: "5",
       26: "5", 27: "6", 30: "7", 33: "7"}
BASS_LO, BASS_HI = 3 * 40, 3 * 55        # E2 .. G3 (sixth-steps = MIDI * 3)
UP_LO = 3 * 55                           # upper voices start in [G3, G4)


def name36(st: int) -> str:
    q, r = divmod(st % EDO, 3)
    return NAMES[q] if r == 0 else ("^" + NAMES[q] if r == 1 else "v" + NAMES[(q + 1) % 12])


def near(a: int, b: int) -> int:
    return ((b - a + 18) % EDO) - 18


def steps(x: float) -> int:
    return int(round(x * 3))


@dataclass(frozen=True)
class Label:
    name: str          # chord symbol in songmap notation (parseable for g, g7, s, T13 and Western types)
    kind: str          # golden | golden_pedal | equal_third | western | planing | altered
    root: int          # sixth-steps
    ivs: tuple         # sixth-steps above the root (sorted)
    bass: int


def classify(voices: tuple) -> Label:
    """voices[0] = bass, absolute sixth-steps."""
    bass = voices[0] % EDO
    s = frozenset(v % EDO for v in voices)
    up = frozenset(v % EDO for v in voices[1:])
    for t, iv in TYPES.items():
        for r in sorted(s):
            if frozenset((r + i) % EDO for i in iv) == s:
                kind = ("golden" if t in GOLDEN_T else "equal_third" if t in ("s", "T13")
                        else "western" if r % 3 == 0 else "planing")
                return Label(name36(r) + t + ("" if r == bass else "/" + name36(bass)), kind, r, iv, bass)
    for t in GOLDEN_T:
        for r in sorted(up):
            if frozenset((r + i) % EDO for i in TYPES[t]) == up:
                return Label(f"{name36(r)}{t}/{name36(bass)}", "golden_pedal", r, TYPES[t], bass)
    # nearest Western/golden chord with micro-alterations (root exact)
    best = None
    for t, iv in TYPES.items():
        if t in ("s", "T13"):
            continue
        for r in sorted(s):
            devs, ok = {}, True
            for p in s:
                d, i = min((abs(((p - (r + i)) % EDO + 18) % EDO - 18), i) for i in iv)
                dd = ((p - (r + i)) % EDO + 18) % EDO - 18
                if d > 2 or i in devs:
                    ok = False
                    break
                devs[i] = dd
            if not ok or any(i not in devs and i not in (18, 21, 22, 24) for i in iv):
                continue
            cost = sum(abs(x) for x in devs.values()) - (0.3 if t in GOLDEN_T else 0)
            if best is None or cost < best[0]:
                best = (cost, r, t, devs)
    if best:
        _, r, t, devs = best
        alt = ",".join(("^" * d if d > 0 else "v" * -d) + DEG.get(i, "?") for i, d in sorted(devs.items()) if d)
        ivs = tuple(sorted((i + devs.get(i, 0)) for i in TYPES[t] if i in devs))
        return Label(f"{name36(r)}{t}({alt})" + ("" if r == bass else "/" + name36(bass)), "altered", r, ivs, bass)
    root = bass
    return Label("{" + " ".join(name36(p) for p in sorted(s)) + "}", "altered", root,
                 tuple(sorted((p - root) % EDO for p in s)), bass)


def _upper_options(root: int, ivs: tuple):
    pc = [(root + i) % EDO for i in ivs]
    if len(ivs) >= 4:
        return [(pc[1:4], 0.0), ([pc[1], pc[3], pc[0]], 0.5)]
    if len(ivs) == 3:
        return [(pc, 0.0), ([pc[0], pc[0], pc[1]], 1.0)]
    return [((pc + pc)[:3], 1.0)]


def _schedules(D: int, natural: bool):
    if D == 0:
        return [(0, 0, 0)]
    if abs(D) > 6:                       # a leap: hold, then move on the arrival chord
        return [(0, 0, D)]
    if not natural:
        if D % 3 == 0:
            u = D // 3
            return [(u, u, u)]
        # off-grid displacement (e.g. a sixth-step): move as early as evenly possible
        sg = 1 if D > 0 else -1
        a = abs(D)
        return [tuple(sg * (a // 3 + (1 if k < a % 3 else 0)) for k in range(3))]
    if abs(D) == 3:
        u = D // 3
        return [(u, u, u)]
    sg = 1 if D > 0 else -1
    return [(sg * a, sg * b, sg * (abs(D) - a - b)) for a in range(4) for b in range(4) if 0 <= abs(D) - a - b <= 3]


def _starts(root: int, ivs: tuple):
    bass = BASS_LO + (root - BASS_LO) % EDO
    return [((bass, *[UP_LO + (p - UP_LO) % EDO for p in u]), pen) for u, pen in _upper_options(root, ivs)]


def evaluate(xr: int, xivs: tuple, yr: int, yivs: tuple, natural: bool = True, prefer: str = "g",
             start: tuple | None = None, seventh: int | None = None):
    """Best four-part path X -> P1 -> P2 -> Y. Roots/intervals in sixth-steps.
    prefer: 'g' (golden triad or seventh), 'g7' (golden seventh) or '' (none: strict path as is).
    Returns (chords[4] as tuples of absolute sixth-steps B,T,A,S ; Label P1 ; Label P2)."""
    best = None
    for X0, xpen in ([(start, 0.0)] if start else _starts(xr, xivs)):
        rd = near(X0[0], yr)
        if abs(rd) > 6:
            alt = rd - EDO if rd > 0 else rd + EDO
            if not BASS_LO <= X0[0] + rd <= BASS_HI and BASS_LO <= X0[0] + alt <= BASS_HI:
                rd = alt
        systems = []
        for yu, ypen in _upper_options(yr, yivs):
            for perm in set(permutations(yu)):
                systems.append(([near(x, y) for x, y in zip(X0[1:], perm)], xpen + ypen))
        step = [sy for sy in systems if all(abs(d) <= 6 for d in sy[0])]
        if step:
            systems = step
        else:
            m = min(sum(map(abs, sy[0])) for sy in systems)
            systems = [sy for sy in systems if sum(map(abs, sy[0])) == m]
        bass_scheds = _schedules(rd, natural) if abs(rd) <= 6 else [(0, 0, rd)]
        for D, pen in systems:
            for bsch in bass_scheds:
                for sch in product(*[_schedules(d, natural) for d in D]):
                    pos = list(X0)
                    chords = [tuple(pos)]
                    for st in range(3):
                        pos = [pos[0] + bsch[st]] + [pos[1 + i] + sch[i][st] for i in range(3)]
                        chords.append(tuple(pos))
                    l1, l2 = classify(chords[1]), classify(chords[2])
                    motion = sum(abs(d) for d in D) / 3 + pen
                    uneven = sum(max(x) - min(x) for x in sch)
                    want = ("golden", "golden_pedal") if prefer else ()
                    golden = (l1.kind in want) + (l2.kind in want)
                    exact = (l1.kind == "golden") + (l2.kind == "golden")
                    sev = 0
                    if prefer == "g7":
                        sev = (l1.name.split("/")[0].endswith("g7")) + (l2.name.split("/")[0].endswith("g7"))
                    distinct = frozenset(c % EDO for c in chords[1]) != frozenset(c % EDO for c in chords[2])
                    par = sum(1 for i in range(1, 4)
                              if chords[3][i] - chords[0][i] == chords[3][0] - chords[0][0] != 0
                              and (chords[0][i] - chords[0][0]) % EDO in (0, 21))
                    sev_up = 0 if seventh is None else sum(
                        1 for i in range(1, 4) if chords[0][i] % EDO == seventh and chords[3][i] > chords[0][i])
                    key = (-sev, -golden, -exact, -int(distinct), par, motion + 0.5 * sev_up, uneven)
                    if best is None or key < best[0]:
                        best = (key, chords, l1, l2)
    _, chords, l1, l2 = best
    return chords, l1, l2


# evaluate() is a pure, exhaustive search that takes seconds per chord pair, so results are cached in
# memory and on disk (keyed by a hash of this file, so any change to the engine starts a fresh cache).
# The Studio re-checks a song on every edit, which made this matter.
_DISK: dict | None = None
_DISK_PATH = os.path.join(os.path.expanduser("~"), ".cache", "songmap",
                          "passing-" + hashlib.sha1(open(__file__, "rb").read()).hexdigest()[:12] + ".pkl")


def _disk() -> dict:
    global _DISK
    if _DISK is None:
        try:
            with open(_DISK_PATH, "rb") as f:
                _DISK = pickle.load(f)
        except (OSError, EOFError, pickle.UnpicklingError, AttributeError):
            _DISK = {}
    return _DISK


def _disk_put(key, value) -> None:
    d = _disk()
    d[key] = value
    try:
        os.makedirs(os.path.dirname(_DISK_PATH), exist_ok=True)
        tmp = _DISK_PATH + f".{os.getpid()}.tmp"
        with open(tmp, "wb") as f:
            pickle.dump(d, f)
        os.replace(tmp, _DISK_PATH)
    except OSError:
        pass                                   # a read-only home: memory cache only


@lru_cache(maxsize=8192)
def _cached(xr, xivs, yr, yivs, natural, prefer, start=None):
    key = (xr, xivs, yr, yivs, natural, prefer, start)
    hit = _disk().get(key)
    if hit is None:
        hit = evaluate(xr, xivs, yr, yivs, natural, prefer, start=start)
        _disk_put(key, hit)
    return hit


def label_chord(lab: Label):
    """A Label as a songmap Chord (root and intervals back in semitones)."""
    from .harmony import Chord
    return Chord(lab.name, lab.root / 3, tuple(i / 3 for i in lab.ivs), lab.bass / 3)


def passing_chords(X, Y, tokens: list[str]) -> list:
    """Chords for placeholder tokens between Chords X and Y (see module docstring)."""
    return passing_path(X, Y, tokens)[0]


def _midi_lines(ch: tuple) -> tuple:
    return tuple(p / 3 for p in ch)


def passing_path(X, Y, tokens: list[str], start: tuple | None = None):
    """(passing Chords, voicings) for placeholders between X and Y. The voicings (MIDI, bass first) are
    the engine's four lines: one each for X, the passing chord(s) and Y. With `start` (X's voicing, as
    fixed by an earlier path that arrived on X) the path continues from there, but only if that gives
    the same passing chords as the canonical path; otherwise the canonical path is used, so a chord's
    name never depends on its neighbours' history."""
    for t in tokens:
        if t.split("@")[0] not in ("~", "~g", "~g7"):
            from ..parse.errors import NotationError
            raise NotationError(f"passing placeholder '{t}' not understood; use ~, ~g or ~g7 (two in a row = P1 P2)")
    if len(tokens) > 2:
        from ..parse.errors import NotationError
        raise NotationError("at most two passing placeholders between two chords (P1 P2)")
    base = tokens[0].split("@")[0]
    prefer = {"~": "", "~g": "g", "~g7": "g7"}[base]
    natural = prefer != ""
    xr, xivs = steps(X.root), tuple(steps(i) for i in X.intervals)
    yr, yivs = steps(Y.root), tuple(steps(i) for i in Y.intervals)
    chords, l1, l2 = _cached(xr, xivs, yr, yivs, natural, prefer)
    if start is not None:
        s = tuple(int(round(p * 3)) for p in start)
        if len(s) == 4:
            c2, m1, m2 = _cached(xr, xivs, yr, yivs, natural, prefer, s)
            if (m1.name, m2.name) == (l1.name, l2.name):
                chords = c2
    if len(tokens) == 2:
        picked = [(l1, chords[1]), (l2, chords[2])]
    else:
        pos = tokens[0].split("@")[1] if "@" in tokens[0] else None
        if pos == "1/3":
            picked = [(l1, chords[1])]
        elif pos == "2/3":
            picked = [(l2, chords[2])]
        else:
            rank = {"golden": 0, "golden_pedal": 1, "equal_third": 2, "planing": 3, "western": 3, "altered": 4}
            picked = [min([(l1, chords[1]), (l2, chords[2])], key=lambda lc: rank[lc[0].kind])]
    from dataclasses import replace
    # order the upper lines low to high by their place in X, keeping each line's identity along the path
    order = [0] + sorted(range(1, 4), key=lambda i: chords[0][i])
    chords = [tuple(c[i] for i in order) for c in chords]
    picked = [(lab, tuple(ch[i] for i in order)) for lab, ch in picked]
    out = [replace(label_chord(lab), lines=_midi_lines(ch)) for lab, ch in picked]
    return out, [_midi_lines(chords[0])] + [_midi_lines(ch) for _, ch in picked] + [_midi_lines(chords[3])]
