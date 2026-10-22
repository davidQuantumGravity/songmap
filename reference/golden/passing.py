"""Sub-chromatic passing chords: golden chords that appear *inside* ordinary voice leading.

Idea: in 36-ET every semitone of motion is three sixth-steps. Take the smoothest
12-ET voice leading between two chords (diatonic or chromatic), let each voice
stop at 1/3 or 2/3 of its move, and classify every intermediate chord. Some of
them are golden triads (C vE ^G) or golden sevenths (C vE ^G B): the passing
chords are not chosen ad hoc, they are *picked out* by the voice leading.

    python reference/golden/passing.py            # tables used in docs/GOLDEN_HARMONY.md §3
"""
from itertools import permutations, product

EDO = 36
NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def name36(st):
    q, r = divmod(st % EDO, 3)
    return NAMES[q] if r == 0 else ("^" + NAMES[q] if r == 1 else "v" + NAMES[(q + 1) % 12])


# chord types in 36-ET steps above the root
TYPES = {
    "g": (0, 11, 22),            # golden triad
    "g7": (0, 11, 22, 33),       # golden seventh = 1 : phi : phi^2 : phi^3 (octave-equivalent)
    "s": (0, 10, 20),            # silver triad candidate (golden minor third ^m3 stacked; see doc)
    "": (0, 12, 21), "m": (0, 9, 21), "aug": (0, 12, 24), "dim": (0, 9, 18),
    "maj7": (0, 12, 21, 33), "7": (0, 12, 21, 30), "m7": (0, 9, 21, 30), "m7b5": (0, 9, 18, 30),
}
GOLDEN = {"g", "g7", "s"}


def classify(pcs):
    s = frozenset(p % EDO for p in pcs)
    for root in sorted(s):
        for t, iv in TYPES.items():
            if frozenset((root + i) % EDO for i in iv) == s:
                return name36(root) + t, t
    return None, None


def chord(sym):
    """'C', 'Am', 'G7', 'Abmaj7' ... on the 12-ET layer -> tuple of 36-ET pitch classes."""
    alias = {"Db": "C#", "D#": "Eb", "Gb": "F#", "G#": "Ab", "A#": "Bb"}
    for t in sorted(TYPES, key=len, reverse=True):
        for i, n in enumerate(NAMES):
            if sym in (n + t, *(k + t for k, v in alias.items() if v == n)):
                return tuple((3 * i + x) % EDO for x in TYPES[t])
    raise ValueError(sym)


def smooth_vl(a, b):
    """Smoothest bijective voice leading a -> b (same size), moves in steps in [-18, 18)."""
    best = None
    for p in permutations(b):
        mv = tuple(((y - x + 18) % EDO) - 18 for x, y in zip(a, p))
        d = sum(map(abs, mv))
        if best is None or d < best[0]:
            best = (d, mv)
    return best[1]


def golden_passing(a_sym, b_sym, staggered=True):
    """Golden chords strictly between a and b along the smoothest voice leading.

    staggered=False: all voices move together (each voice at the same fraction 1/3, 2/3).
    staggered=True : voices may arrive at different times (each voice at its own 0..3 thirds).
    """
    a, b = chord(a_sym), chord(b_sym)
    mv = smooth_vl(a, b)
    found = {}
    fracs = (0, 1, 2, 3)
    combos = product(fracs, repeat=len(a)) if staggered else ((k,) * len(a) for k in (1, 2))
    for ks in combos:
        if all(k in (0, 3) for k in ks):           # only endpoints: no new chord
            continue
        pcs = tuple(x + round(m * k / 3) for x, m, k in zip(a, mv, ks))
        name, t = classify(pcs)
        if t in GOLDEN:
            found.setdefault(name, []).append(ks)
    return mv, found


def main():
    key = ["C", "Dm", "Em", "F", "G", "Am"]
    chromatic = ["Ab", "Eb", "Fm", "Cm", "E", "A", "D", "Bb", "Db", "Caug"]
    print("Triads: golden/silver chords picked out by the smoothest voice leading")
    print("(moves in sixth-steps per voice; 'sync' = all voices move together)\n")
    for a in key + ["Cm"]:
        for b in key + chromatic:
            if a == b:
                continue
            mv, staggered = golden_passing(a, b, True)
            _, sync = golden_passing(a, b, False)
            if staggered:
                tag = ", ".join(f"{n}{' (sync)' if n in sync else ''}" for n in staggered)
                print(f"  {a:>4s} -> {b:<5s} moves {str(mv):18s} {tag}")
    print("\nSevenths: golden sevenths between seventh chords")
    sev = ["Cmaj7", "Dm7", "Em7", "Fmaj7", "G7", "Am7", "Bm7b5", "Abmaj7", "Ebmaj7", "Fm7", "Cm7", "E7", "A7", "Db7"]
    for a in sev:
        for b in sev:
            if a == b:
                continue
            mv, staggered = golden_passing(a, b, True)
            g7 = {n: v for n, v in staggered.items() if n.endswith("g7")}
            if g7:
                _, sync = golden_passing(a, b, False)
                print(f"  {a:>6s} -> {b:<7s} moves {str(mv):22s} " + ", ".join(f"{n}{' (sync)' if n in sync else ''}" for n in g7))


if __name__ == "__main__":
    main()
