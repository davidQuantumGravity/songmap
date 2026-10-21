"""Rigorous classification of golden passing paths (and their inversion, golden homes).

Model
-----
* Pitch classes are Z_36 (sixth-steps). Layer(p) = p mod 3. 12-ET = layer 0 ("rational").
* A chord with v voices is a vector X in Z_36^v (voices = lines; order = voice identity).
* A *uniform sub-chromatic path* X -> Y with per-voice displacement d (in semitones,
  |d_i| <= 2, i.e. stepwise) is  P_k = X + k*d (sixth-steps), k = 0..3, Y = X + 3d.
  Half steps advance one sixth-step per chord, whole steps two. P_1, P_2 are the passing chords.
* Home/passing principle: X, Y are Western chords (layer 0); a passing chord is golden if
  its pitch-class set is a golden triad {r, r+11, r+22} or golden seventh {r, r+11, r+22, r+33}.

Results printed here (and copied into docs/GOLDEN_THEORY.md):
  A. Layer theorem, the four-path theorem, and the complete list of triad paths.
  B. "Never two in a row": no uniform path has both passing chords golden.
  C. The partner chord: the other passing chord is always an equal-third triad T_n = {0, n, 2n}.
  D. Golden sevenths: the complete list of 4-voice paths.
  E. Diatonic restriction: which pairs in C major (+ common chromatic chords) have golden passing chords.
  F. Relaxed (monotone, non-uniform) paths: diatonic - golden - golden - diatonic forms.
  G. Inversion: golden homes, the golden circle, and rational chords as passing between golden homes.

    python reference/golden/classify.py
"""
from collections import Counter, defaultdict
from itertools import permutations, product

EDO = 36
NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
ROMAN = ["I", "bII", "II", "bIII", "III", "IV", "#IV", "V", "bVI", "VI", "bVII", "VII"]


def name36(st):
    q, r = divmod(st % EDO, 3)
    return NAMES[q] if r == 0 else ("^" + NAMES[q] if r == 1 else "v" + NAMES[(q + 1) % 12])


def roman36(st):
    q, r = divmod(st % EDO, 3)
    return ROMAN[q] if r == 0 else ("^" + ROMAN[q] if r == 1 else "v" + ROMAN[(q + 1) % 12])


WEST = {"": (0, 12, 21), "m": (0, 9, 21), "aug": (0, 12, 24), "dim": (0, 9, 18),
        "sus4": (0, 15, 21), "sus2": (0, 6, 21)}
WEST7 = {"7": (0, 12, 21, 30), "maj7": (0, 12, 21, 33), "m7": (0, 9, 21, 30), "m7b5": (0, 9, 18, 30),
         "dim7": (0, 9, 18, 27), "mmaj7": (0, 9, 21, 33), "6": (0, 12, 21, 27), "m6": (0, 9, 21, 27),
         "augmaj7": (0, 12, 24, 33), "7sus4": (0, 15, 21, 30)}
GOLD = (0, 11, 22)
GOLD7 = (0, 11, 22, 33)


def pcset(v):
    return frozenset(x % EDO for x in v)


def is_type(s, iv):
    return [r for r in s if pcset(r + i for i in iv) == s]


def west_name(s):
    for t, iv in {**WEST, **WEST7}.items():
        r = is_type(s, iv)
        if r:
            return name36(r[0]) + t
    return None


def golden_root(s, seventh=False):
    r = is_type(s, GOLD7 if seventh else GOLD)
    return r[0] if r else None


def equal_third(s):
    """T_n = {r, r+n, r+2n} (3 distinct pcs): return n in 1..17 (the smaller stacked third), else None."""
    if len(s) != 3:
        return None
    a = sorted(s)
    gaps = [(a[1] - a[0]), (a[2] - a[1]), (a[0] + EDO - a[2])]
    for i in range(3):
        if gaps[i] == gaps[(i + 1) % 3]:
            return gaps[i]
    return None


TNAME = {9: "dim", 10: "silver", 11: "golden", 12: "aug", 13: "T13", 8: "T8", 14: "T14"}


def label(s):
    w = west_name(s)
    if w:
        return w
    g = golden_root(s)
    if g is not None:
        return name36(g) + "g"
    g7 = golden_root(s, True)
    if g7 is not None:
        return name36(g7) + "g7"
    n = equal_third(s)
    if n:
        r = [x for x in s if (x + n) % EDO in s and (x + 2 * n) % EDO in s][0]
        return f"{name36(r)}{TNAME.get(n, f'T{n}')}"
    return "{" + " ".join(name36(x) for x in sorted(s)) + "}"


def H(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


STEP_D = range(-2, 3)


def triad_paths():
    """All uniform stepwise paths (3 voices) whose P1 or P2 is a golden triad, X, Y Western triads."""
    out = []
    for r in range(EDO):
        G = tuple((r + i) % EDO for i in GOLD)
        for k in (1, 2):
            for d in product(STEP_D, repeat=3):
                X = tuple((g - k * di) % EDO for g, di in zip(G, d))
                Y = tuple((g + (3 - k) * di) % EDO for g, di in zip(G, d))
                if any(x % 3 for x in X):
                    continue
                sx, sy = pcset(X), pcset(Y)
                if len(sx) < 3 or len(sy) < 3:
                    continue
                other = tuple((x + (3 - k if k == 2 else 2) * 0) for x in X)  # placeholder
                P = [tuple((x + j * di) % EDO for x, di in zip(X, d)) for j in (1, 2)]
                out.append(dict(r=r, k=k, d=d, X=X, Y=Y, P=P, wx=west_name(sx), wy=west_name(sy)))
    return out


def main():
    H("A. Layer theorem and the four-path theorem (triads, uniform paths)")
    print("Layers of a golden triad {r, r+11, r+22}: r, r+2, r+1 (mod 3) -> exactly one note per layer.")
    print("Hence P_k = X + k d is golden only if d contains one voice of each class")
    print("  hold (d = 0), rising class (d = +1 or -2), falling class (d = -1 or +2).")
    paths = triad_paths()
    both_west = [p for p in paths if p["wx"] and p["wy"]]
    per_triad = Counter((p["r"], p["k"]) for p in paths)
    print(f"Uniform stepwise paths (3 voices) with a golden P_k and layer-0 endpoints: {len(paths)}"
          f" = 36 golden triads x 2 positions x {len(paths) // 72} displacement vectors")
    print(f"  of which both endpoints are Western triads: {len(both_west)}")
    # canonical classes up to semitone transposition (r mod 3 = layer of the golden root), k = 1
    print("\nComplete list up to transposition (golden chord at 1/3 from X; the reverse path has it at 2/3):")
    seen = set()
    for p in sorted(paths, key=lambda p: (p["r"] % 3, p["k"], p["d"])):
        if p["k"] != 1 or p["r"] not in (0, 1, 2):
            continue
        key = (p["r"], p["d"])
        if key in seen:
            continue
        seen.add(key)
        sx, sy = pcset(p["X"]), pcset(p["Y"])
        partner = label(pcset(p["P"][1]))
        print(f"  root layer {p['r']}: d={str(p['d']):12s}  {label(sx):8s} -> {label(pcset(p['P'][0])):6s} -> {partner:9s} -> {label(sy)}")

    H("B. Never two golden chords in a row (uniform paths)")
    twice = [p for p in paths if golden_root(pcset(p["P"][0])) is not None and golden_root(pcset(p["P"][1])) is not None]
    print(f"paths with BOTH passing chords golden: {len(twice)}")

    H("C. The partner chord is always an equal-third triad T_n")
    partners = Counter()
    for p in both_west:
        other = p["P"][1] if p["k"] == 1 else p["P"][0]
        n = equal_third(pcset(other))
        partners[TNAME.get(n, f"T{n}") if n else label(pcset(other))] += 1
    print("partner of the golden chord, over all Western-to-Western paths:", dict(partners))
    print("Equal-third line T_n = {0, n, 2n}: n = 9 dim, 10 silver, 11 golden, 12 aug, 13 T13.")
    print("Caug -> Cg -> Cs -> Cdim is ONE uniform path (root holds; third -1, fifth -2 sixth-steps per chord).")

    H("D. Golden sevenths (4 voices, uniform paths)")
    p7 = []
    for r in range(EDO):
        G = tuple((r + i) % EDO for i in GOLD7)
        for k in (1, 2):
            for d in product(STEP_D, repeat=4):
                X = tuple((g - k * di) % EDO for g, di in zip(G, d))
                Y = tuple((g + (3 - k) * di) % EDO for g, di in zip(G, d))
                if any(x % 3 for x in X) or len(pcset(X)) < 3 or len(pcset(Y)) < 3:
                    continue
                wx, wy = west_name(pcset(X)), west_name(pcset(Y))
                if wx and wy:
                    p7.append(dict(r=r, k=k, d=d, X=X, Y=Y, wx=wx, wy=wy,
                                   other=tuple((x + (3 - k) * di) % EDO for x, di in zip(G, d)) if k == 1 else None))
    print(f"Western -> golden seventh -> ... -> Western paths: {len(p7)}")
    seen = set()
    for p in sorted(p7, key=lambda p: (p["r"] % 3, p["d"])):
        if p["k"] != 1 or p["r"] not in (0, 1, 2) or (p["r"], p["d"]) in seen:
            continue
        seen.add((p["r"], p["d"]))
        P2 = tuple((x + 2 * di) % EDO for x, di in zip(p["X"], p["d"]))
        print(f"  root layer {p['r']}: d={str(p['d']):16s} {p['wx']:8s} -> {name36(p['r'])}g7 -> {label(pcset(P2)):14s} -> {p['wy']}")

    H("E. Diatonic restriction: C major + common chromatic chords")
    key = {"I": "C", "ii": "Dm", "iii": "Em", "IV": "F", "V": "G", "vi": "Am", "vii°": "Bdim",
           "i": "Cm", "iv": "Fm", "bIII": "Eb", "bVI": "Ab", "bVII": "Bb", "bII": "C#", "II": "D", "III": "E",
           "VI": "A", "V+": "Gaug", "I+": "Caug", "vii°/V": "F#dim"}
    inv = {v: k for k, v in key.items()}
    table = defaultdict(set)
    def kname(S):
        for k_, v_ in key.items():
            for i, n in sorted(enumerate(NAMES), key=lambda t: -len(t[1])):
                if v_.startswith(n) and v_[len(n):] in WEST and pcset(3 * i + x for x in WEST[v_[len(n):]]) == S:
                    return k_
        return None

    for p in both_west:
        a, b = kname(pcset(p["X"])), kname(pcset(p["Y"]))
        if a and b:
            g = name36(p["r"]) + "g"
            pos = "1/3" if p["k"] == 1 else "2/3"
            table[(a, b)].add(f"{g}@{pos}")
    for (a, b), gs in sorted(table.items(), key=lambda kv: (list(key).index(kv[0][0]), list(key).index(kv[0][1]))):
        print(f"  {a:>6s} -> {b:<6s} ({key[a]} -> {key[b]}): {', '.join(sorted(gs))}")
    print(f"ordered pairs with a uniform golden passing chord: {len(table)}")

    H("F. Relaxed paths: diatonic - golden - golden - diatonic (monotone voices, <= 1 semitone per chord)")
    # each voice: 3 increments, monotone, each in 0..3 sixth-steps (or 0..-3), summing to 3*d
    def schedules(total):
        sgn = 1 if total >= 0 else -1
        for a, b in product(range(0, 4), repeat=2):
            c = abs(total) - a - b
            if 0 <= c <= 3:
                yield (sgn * a, sgn * b, sgn * c)
    found = defaultdict(list)

    def voiced(nm):
        for i, n in sorted(enumerate(NAMES), key=lambda t: -len(t[1])):
            if nm.startswith(n) and nm[len(n):] in WEST:
                return tuple((3 * i + x) % EDO for x in WEST[nm[len(n):]])
        raise KeyError(nm)

    for a, A in key.items():
        for b, B in key.items():
            if a == b:
                continue
            sa, sb = voiced(A), voiced(B)
            for perm in permutations(sb):
                d = [(((y - x + 18) % EDO) - 18) for x, y in zip(sa, perm)]
                if any(abs(x) > 6 for x in d):        # stepwise: at most a whole step per voice
                    continue
                for sch in product(*[list(schedules(x)) for x in d]):
                    P1 = tuple((x + s_[0]) % EDO for x, s_ in zip(sa, sch))
                    P2 = tuple((x + s_[0] + s_[1]) % EDO for x, s_ in zip(sa, sch))
                    g1, g2 = golden_root(pcset(P1)), golden_root(pcset(P2))
                    if g1 is not None and g2 is not None:
                        found[(a, b)].append((sum(map(abs, d)), name36(g1) + "g", name36(g2) + "g", sch))
    for (a, b), lst in sorted(found.items(), key=lambda kv: (list(key).index(kv[0][0]), list(key).index(kv[0][1]))):
        lst.sort()
        best = sorted({(x[1], x[2]) for x in lst if x[0] == lst[0][0]})
        print(f"  {a:>6s} -> {b:<6s}: " + "; ".join(f"{g1} - {g2}" for g1, g2 in best[:4]))
    print(f"pairs admitting diatonic-golden-golden-diatonic: {len(found)}")

    H("G. Inversion: golden homes")
    # golden circle: Cg -> vEg (C -> B, one voice down a semitone) etc.
    G = lambda r: pcset(r + i for i in GOLD)
    print("Golden circle: G_r and G_{r+11} share two notes; the third moves one semitone (3 sixth-steps).")
    circ = [0]
    while len(circ) < 36:
        circ.append((circ[-1] + 11) % EDO)
    print("  " + " -> ".join(name36(r) + "g" for r in circ[:13]) + " -> ...  (period 36: visits all 36 golden triads)")
    print("  Union of two neighbours = a golden seventh: Cg + vEg =", " ".join(name36(x) for x in sorted(G(0) | G(11))),
          "=", label(G(0) | G(11)))
    # rational chords as passing between golden homes (uniform paths)
    inv_paths = []
    for r in range(EDO):
        G0 = tuple((r + i) % EDO for i in GOLD)
        for dd in product(range(-2, 3), repeat=3):
            G1 = tuple((x + 3 * d) % EDO for x, d in zip(G0, dd))
            if golden_root(pcset(G1)) is None or pcset(G1) == pcset(G0):
                continue
            Ps = [pcset((x + k * d) % EDO for x, d in zip(G0, dd)) for k in (1, 2)]
            w = [west_name(P) for P in Ps]
            if any(w):
                inv_paths.append((r, dd, name36(r) + "g", [label(P) for P in Ps], label(pcset(G1))))
    print(f"\nUniform paths golden -> ... -> golden with a Western passing chord: {len(inv_paths)}")
    seen = set()
    for r, dd, g0, ps, g1 in inv_paths:
        if r in (0, 1, 2) and (r, dd) not in seen:
            seen.add((r, dd))
            print(f"  {g0:6s} -> {ps[0]:9s} -> {ps[1]:9s} -> {g1:6s}   d={dd}")


if __name__ == "__main__":
    main()
