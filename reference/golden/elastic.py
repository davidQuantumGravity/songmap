"""Elastic and ornamental strategies for joining golden and Western chords (textbook Chapter 39,
docs/GOLDEN_BLENDING.md section 17).

Every table and number of the chapter is printed here. Run:

    .venv/Scripts/python reference/golden/elastic.py           # all sections
    .venv/Scripts/python reference/golden/elastic.py 2 5       # selected sections

Conventions (as in blending.py): pitch classes are sixth-steps mod 36 (C = 0, ^C = 1, vC# = 2, C# = 3, ...);
absolute pitches are sixth-steps = MIDI * 3 (C4 = 180). A *voiced* chord is a tuple of absolute pitches, voice
order = voice identity. Golden triad G_r = {r, r+11, r+22}.

The framework (section 1). For one voice with notes x -> g -> y (an ornament g between chords X and Y), exactly one
of the three points lies between the other two when they are distinct:
    g between x and y      passing          (the ornament lies on the way)
    y between x and g      overshoot        (the voice goes past its target and comes back)
    x between g and y      escape/backswing (the voice first moves away from its target)
plus the degenerate cases g = x (hold/suspension: the voice waits), g = y (anticipation: it arrives early) and
x = y != g (neighbour). For voiced chords with the L1 metric, Y lies on a geodesic from X to G iff every voice
satisfies the one-voice condition; so a chord ornament is *uniformly* passing / overshoot / escape when all its
moving voices are, and mixed otherwise. The detour excess d(X,G) + d(G,Y) - d(X,Y) is 0 for passing, 2 d(Y,G) for an
overshoot and 2 d(X,G) for an escape: the elastic "extra travel".
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from itertools import permutations, product
from math import exp, log, pi, sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from blending import (EDO, TRI, chord, cname, fold, names, roughness, triad_label, vl, vl_moves)  # noqa: E402
from songmap.theory.passing import classify, name36  # noqa: E402

PHI = (1 + sqrt(5)) / 2
GOLD = {chord(r, "g"): r for r in range(EDO)}           # pc-set -> root
WEST = {}                                               # pc-set -> label, Western triads on layer 0
for _r in range(0, EDO, 3):
    for _q in ("", "m", "aug", "dim"):
        WEST.setdefault(chord(_r, _q), cname(_r, _q))


def H(t):
    print("\n" + "=" * 100 + f"\n{t}\n" + "=" * 100)


def gname(r):
    return name36(r) + "g"


def is_golden(pcs):
    return frozenset(p % EDO for p in pcs) in GOLD


def lab(pcs):
    """Label of a 3-note pc collection: golden / Western / metallic triad name, else the note set."""
    s = frozenset(p % EDO for p in pcs)
    if len(s) < 3:
        return "{" + names(s) + "}"
    return triad_label(s)


def kind(pcs):
    s = frozenset(p % EDO for p in pcs)
    if s in GOLD:
        return "golden"
    if s in WEST:
        return "western"
    L = lab(s)
    if L.endswith("s") or L.endswith("T13"):
        return "metallic"
    return "other"


def voice_type(x, g, y):
    """One-voice ornament type of x -> g -> y (absolute pitches)."""
    if g == x and g == y:
        return "hold"
    if x == y:
        return "neighbour"
    if g == x:
        return "suspension"         # waits, then moves
    if g == y:
        return "anticipation"       # arrives early
    if min(x, y) < g < max(x, y):
        return "passing"
    if (y - x) * (g - y) > 0:
        return "overshoot"
    return "escape"


def chord_type(X, G, Y):
    """Uniform type of a voiced ornament, or 'mixed'. Holds and degenerate voices are listed separately."""
    ts = [voice_type(x, g, y) for x, g, y in zip(X, G, Y)]
    core = {t for t in ts if t not in ("hold",)}
    if not core:
        return "hold", ts
    if len(core) == 1:
        return core.pop(), ts
    return "mixed", ts


def L1(A, B):
    return sum(abs(a - b) for a, b in zip(A, B))


def spell(p):
    """Absolute sixth-steps -> note name with octave, as the pianoroll wants (vC4 = C4 - 1 sixth-step)."""
    q, r = divmod(p, 3)                     # q = MIDI
    if r == 0:
        m, pre = q, ""
    elif r == 1:
        m, pre = q, "^"
    else:
        m, pre = q + 1, "v"
    nm = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"][m % 12]
    return f"{pre}{nm}{m // 12 - 1}"


def voicing(names_):
    """'C4 E4 G4' -> absolute sixth-steps."""
    L = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    out = []
    for tok in names_.split():
        ups = tok.count("^") - tok.count("v")
        t = tok.lstrip("^v")
        letter, rest = t[0], t[1:]
        acc = 0
        while rest and rest[0] in "#b":
            acc += 1 if rest[0] == "#" else -1
            rest = rest[1:]
        midi = 12 * (int(rest) + 1) + L[letter] + acc
        out.append(3 * midi + ups)
    return tuple(out)


def vs(v):
    return " ".join(spell(p) for p in v)


# ===================================================================================================
def s1_framework():
    H("1. The betweenness framework: one-voice ornament types (exhaustive over small motions)")
    c = Counter()
    for a in range(-6, 7):
        for b in range(-6, 7):
            c[voice_type(0, a, a + b)] += 1
    print("  x = 0, g = a, y = a + b with a, b in [-6, 6]:", dict(c))
    print("  Every (a, b) falls in exactly one class: a = 0 hold/suspension, b = 0 anticipation, a + b = 0 neighbour;")
    print("  otherwise a and b with the same sign = passing; opposite signs and |b| < |a| = overshoot; |b| > |a| = escape.")
    ok = all(voice_type(0, a, a + b) == ("passing" if a * b > 0 else "overshoot" if abs(b) < abs(a) else "escape")
             for a in range(-6, 7) for b in range(-6, 7) if a and b and a + b)
    print("  check of that rule:", ok)
    print("  Excess d(X,G) + d(G,Y) - d(X,Y) per voice: passing 0, overshoot 2|g - y|, escape 2|g - x|.")
    ok2 = True
    for a in range(-6, 7):
        for b in range(-6, 7):
            x, g, y = 0, a, a + b
            ex = abs(g - x) + abs(y - g) - abs(y - x)
            t = voice_type(x, g, y)
            want = {"passing": 0, "overshoot": 2 * abs(g - y), "escape": 2 * abs(g - x)}.get(t)
            if want is not None and ex != want:
                ok2 = False
    print("  check:", ok2)


# --------------------------------------------------------------------------- overshoot
def overshoot_table(Y, kmax=3, strict=True):
    """Y = a Western triad as (root, third, fifth) pcs. For each approach pattern s in {-1,0,+1}^3 (direction in which
    the voice arriving on root / third / fifth was moving), the golden chords G = Y + E with E_i = s_i k_i, 1 <= k_i <= kmax
    (strict: every moving voice overshoots; else a moving voice may also land, k_i = 0, as long as one overshoots)."""
    out = {}
    for s in product((-1, 0, 1), repeat=3):
        found = []
        rng = [((0,) if si == 0 else (tuple(range(0 if not strict else 1, kmax + 1)))) for si in s]
        for ks in product(*rng):
            E = tuple(si * k for si, k in zip(s, ks))
            if not any(E):
                continue
            G = tuple((y + e) % EDO for y, e in zip(Y, E))
            if is_golden(G):
                cost = sum(map(abs, E))
                dmin = vl(frozenset(G), frozenset(Y))
                found.append((cost, E, GOLD[frozenset(G)], dmin))
        out[s] = sorted(found)
    return out


def sgn(s):
    return {-1: "down", 0: "hold", 1: "up"}[s]


def s2_overshoot_tables():
    H("2. Overshoot tables: golden chords just beyond a Western target (per approach direction of root, third, fifth)")
    for nm, Y in (("C major", (0, 12, 21)), ("C minor", (0, 9, 21))):
        for strict in (True, False):
            tab = overshoot_table(Y, 3, strict)
            n_pat = sum(1 for s, f in tab.items() if f and any(s))
            print(f"\n  Target {nm}, overshoot 1-3 sixth-steps, {'every moving voice overshoots' if strict else 'moving voices may also land'}:"
                  f" {n_pat} of 26 approach patterns have a golden overshoot")
            for s, f in tab.items():
                if not f:
                    continue
                best = f[0]
                alts = ", ".join(f"{gname(r)} {E} cost {c}" for c, E, r, _ in f)
                print(f"   root {sgn(s[0]):4s} third {sgn(s[1]):4s} fifth {sgn(s[2]):4s}: {alts}"
                      + ("   [settle = smoothest]" if best[0] == best[3] else f"   [settle {best[0]} > smoothest {best[3]}]"))
    # parallel rule: all 24 major/minor triads on layer 0
    ok = True
    for r in range(0, EDO, 3):
        for q, ivs in (("", (0, 12, 21)), ("m", (0, 9, 21))):
            Y = tuple((r + i) % EDO for i in ivs)
            p = r if q == "" else (r - 1) % EDO                       # the projection pi(Y) = G_p
            for s, want_strict, want_partial in (((1, 1, 1), 2, 1), ((-1, -1, -1), -2, -1)):
                st = [GOLD[frozenset((y + e) % EDO for y, e in zip(Y, E))] for c, E, g, d in overshoot_table(Y, 3, True)[s]]
                pa = [g for c, E, g, d in overshoot_table(Y, 3, False)[s] if g not in st]
                ok &= st == [(p + want_strict) % EDO] and pa == [(p + want_partial) % EDO]
    print("\n  Parallel rule (all 24 major and minor triads): when every voice moves the same way, the only strict golden")
    print("  overshoot is pi(Y) planed two sixth-steps in the direction of motion, and the only extra partial one is pi(Y)")
    print("  planed one sixth-step:", ok)
    print("  Layer reason: overshoots of 1, 2, 3 sixth-steps in one direction sit on three different layers, so a strict")
    print("  golden overshoot uses each size once; of the 6 orders exactly one is golden.")
    # which golden chords ever occur, with min cost
    print("\n  Golden overshoot chords of C major (strict, any pattern), minimal settle cost:")
    tab = overshoot_table((0, 12, 21), 3, True)
    m = {}
    for s, f in tab.items():
        for c, E, r, d in f:
            if r not in m or c < m[r][0]:
                m[r] = (c, E, s, d)
    for r, (c, E, s, d) in sorted(m.items(), key=lambda kv: kv[1][0]):
        print(f"   {gname(r):6s} {names(chord(r, 'g')):12s} cost {c} (smoothest settle {d}) E = {E} approach {tuple(sgn(x) for x in s)}")


def s3_reflection():
    H("3. Damped oscillation: can the swing back (undershoot) also be golden?")
    # Reflection theorem: G = Y + E golden and Y - E golden?
    cnt = 0
    tot = 0
    for r in range(0, EDO, 3):
        for q in ("", "m", "aug", "dim"):
            Y = sorted(chord(r, q))
            for G in GOLD:
                for perm in permutations(sorted(G)):
                    E = [fold(g - y) for g, y in zip(perm, Y)]
                    if max(map(abs, E)) > 6:
                        continue
                    tot += 1
                    R = frozenset((y - e) % EDO for y, e in zip(Y, E))
                    if R in GOLD:
                        cnt += 1
    print(f"  Over all Western triads Y on layer 0 and golden G = Y + E with |E_i| <= 6: {tot} voice assignments;"
          f" reflection Y - E golden in {cnt}.")
    # damped sequences E1 (overshoot), E2 (undershoot, opposite sign per voice, |E2_i| <= |E1_i|)
    print("\n  Two-swing oscillations Y + E1 (golden) then Y + E2 with each moving voice reversing, |E2_i| <= |E1_i| <= 3:")
    for nm, Y in (("C", (0, 12, 21)), ("Cm", (0, 9, 21))):
        hits = []
        kinds_ = Counter()
        for E1 in product(range(-3, 4), repeat=3):
            G1 = tuple((y + e) % EDO for y, e in zip(Y, E1))
            if not is_golden(G1):
                continue
            rngs = [range(0, 1) if e == 0 else (range(-abs(e), 0) if e > 0 else range(1, abs(e) + 1)) for e in E1]
            for E2 in product(*rngs):
                G2 = tuple((y + e) % EDO for y, e in zip(Y, E2))
                k = kind(G2)
                kinds_[k] += 1
                if k == "golden":
                    hits.append((E1, E2, gname(GOLD[frozenset(G1)]), gname(GOLD[frozenset(G2)])))
                elif k in ("metallic", "western") and all(abs(b) == 1 for b in E2 if b):
                    pass
        print(f"   {nm}: undershoot kinds over all such pairs {dict(kinds_)}; golden-golden pairs: {hits}")
    # Fibonacci decay of a common amplitude (all moving voices share |E|): F_n, F_n-1, ...
    print("\n  Common-amplitude damped swings a_k = (+3, -2, +1, -1, 0) and (+2, -1, +1, 0) etc. applied to the pattern")
    print("  (hold one voice, one voice up, one down): golden only where |a_k| matches the projection or Eg pattern:")
    for nm, Y in (("C", (0, 12, 21)), ("Cm", (0, 9, 21))):
        for amps in ((5, -3, 2, -1, 1), (3, -2, 1, -1), (2, -1, 1), (1, -1)):
            for s in product((-1, 0, 1), repeat=3):
                if sorted(s) != [-1, 0, 1]:
                    continue
                row = []
                for a in amps:
                    G = tuple((y + si * a) % EDO for y, si in zip(Y, s))
                    row.append(gname(GOLD[frozenset(G)]) if is_golden(G) else lab(G))
                if any(x.endswith("g") and "{" not in x for x in row):
                    print(f"   {nm} pattern {s} amplitudes {amps}: " + " -> ".join(row))
    print("\n  Relaxed two-stage settles Y + E1 -> Y + E2 -> Y, both golden, |E2_i| <= |E1_i| per voice, at least one voice")
    print("  reversing (a true swing) -- voices may also creep monotonically or stop:")
    for nm, Y in (("C", (0, 12, 21)), ("Cm", (0, 9, 21))):
        rows = []
        for E1 in product(range(-3, 4), repeat=3):
            G1 = frozenset((y + e) % EDO for y, e in zip(Y, E1))
            if G1 not in GOLD:
                continue
            for E2 in product(*[range(-abs(e), abs(e) + 1) for e in E1]):
                G2 = frozenset((y + e) % EDO for y, e in zip(Y, E2))
                if G2 not in GOLD or G2 == G1:
                    continue
                flips = sum(1 for a, b in zip(E1, E2) if a * b < 0)
                if not flips:
                    continue
                path = sum(abs(a - b) for a, b in zip(E1, E2)) + sum(map(abs, E2))
                rows.append((path, E1, E2, gname(GOLD[G1]), gname(GOLD[G2]), flips))
        rows.sort()
        print(f"   {nm}: {len(rows)} settles")
        for path, E1, E2, a, b, fl in rows:
            print(f"     {a:6s} {E1} -> {b:6s} {E2} -> {nm}   path {path} (direct {sum(map(abs, E1))}), voices reversing {fl}")
    print("\n  Spring metaphor: amplitude ratio 1/phi per half swing <=> logarithmic decrement ln(phi) per half period.")
    d = log(PHI)
    zeta = d / sqrt(pi ** 2 + d ** 2)
    print(f"   per half period ln(phi) = {d:.4f}; damping ratio zeta = {zeta:.4f}; a pure spring with this damping overshoots")
    print(f"   a step by 1/phi = {1 / PHI:.3f} of its size (a fourth, 15 sixth-steps, by {15 / PHI:.2f} sixth-steps).")
    for frac in (1 / 3, 2 / 15, 1 / 5):
        z = -log(frac) / sqrt(pi ** 2 + log(frac) ** 2)
        print(f"   overshoot fraction {frac:.3f} <=> zeta = {z:.3f}; next swing {frac ** 2:.4f} of the step")


# --------------------------------------------------------------------------- progressions
PROGS = [
    # name, X upper voices, X bass, Y upper voices, Y bass, description
    ("I -> IV (leap up a fourth, parallel)", "C4 E4 G4", "C3", "F4 A4 C5", "F2", "all voices leap up"),
    ("I -> IV (smooth)", "C4 E4 G4", "C3", "C4 F4 A4", "F2", "common tone C"),
    ("I -> V (leap up a fifth, parallel)", "C4 E4 G4", "C3", "G4 B4 D5", "G2", ""),
    ("I -> V (leap down a fourth, parallel)", "C4 E4 G4", "C3", "G3 B3 D4", "G2", ""),
    ("V -> I (leap up a fourth, parallel)", "G3 B3 D4", "G2", "C4 E4 G4", "C3", ""),
    ("V -> I (leap down a fifth, parallel)", "G4 B4 D5", "G2", "C4 E4 G4", "C3", ""),
    ("V -> I (smooth)", "G3 B3 D4", "G2", "G3 C4 E4", "C3", ""),
    ("I -> vi (parallel down a third)", "C4 E4 G4", "C3", "A3 C4 E4", "A2", ""),
    ("vi -> I (parallel up a third)", "A3 C4 E4", "A2", "C4 E4 G4", "C3", ""),
    ("IV -> I (parallel down a fourth)", "F4 A4 C5", "F2", "C4 E4 G4", "C3", ""),
    ("I -> bVI (chromatic mediant, parallel down a major third)", "C4 E4 G4", "C3", "Ab3 C4 Eb4", "Ab2", ""),
    ("bVI -> I (parallel up a major third)", "Ab3 C4 Eb4", "Ab2", "C4 E4 G4", "C3", ""),
    ("I -> III (E major, parallel up)", "C4 E4 G4", "C3", "E4 G#4 B4", "E3", ""),
    ("III -> I (E major down to C)", "E4 G#4 B4", "E3", "C4 E4 G4", "C3", ""),
    ("I -> bIII (Eb, parallel up a minor third)", "C4 E4 G4", "C3", "Eb4 G4 Bb4", "Eb3", ""),
    ("I -> F# (tritone, parallel up)", "C4 E4 G4", "C3", "F#4 A#4 C#5", "F#2", ""),
    ("F# -> I (tritone, parallel down)", "F#4 A#4 C#5", "F#2", "C4 E4 G4", "C3", ""),
    ("I -> I (octave leap)", "C4 E4 G4", "C3", "C5 E5 G5", "C3", ""),
    ("ii -> V (parallel down a fifth)", "D4 F4 A4", "D3", "G3 B3 D4", "G2", ""),
    ("V -> vi (deceptive, parallel up a step)", "G3 B3 D4", "G2", "A3 C4 E4", "A2", ""),
    ("I -> I6 (wide spread: contrary leap)", "E4 G4 C5", "C3", "C4 G4 E5", "E3", "outer voices leap apart"),
    ("IV -> V (parallel up a step)", "F3 A3 C4", "F2", "G3 B3 D4", "G2", ""),
]


def overshoots_voiced(X, Y, kmax=3, strict=True):
    """Golden overshoot chords of a voiced progression X -> Y (upper voices)."""
    D = [y - x for x, y in zip(X, Y)]
    s = [0 if d == 0 else (1 if d > 0 else -1) for d in D]
    rng = [((0,) if si == 0 else tuple(range(0 if not strict else 1, kmax + 1))) for si in s]
    out = []
    for ks in product(*rng):
        E = tuple(si * k for si, k in zip(s, ks))
        if not any(E):
            continue
        G = tuple(y + e for y, e in zip(Y, E))
        if is_golden(G):
            out.append((sum(map(abs, E)), E, G))
    return sorted(out), D


def s4_progressions():
    H("4. Overshoot in common progressions (voiced; upper three voices; bass lands on the new root)")
    for name, xs, xb, ys, yb, _ in PROGS:
        X, Y = voicing(xs), voicing(ys)
        res, D = overshoots_voiced(X, Y, 3, True)
        resp, _ = overshoots_voiced(X, Y, 3, False)
        P4 = tuple(y + d // 3 for y, d in zip(Y, D))
        p4 = lab(P4)
        print(f"\n  {name}: {xs} -> {ys}  motion (semitones) {[d // 3 for d in D]}, total {sum(map(abs, D))} sixth-steps")
        if res:
            for c, E, G in res:
                gl = gname(GOLD[frozenset(p % EDO for p in G)])
                dm = vl(frozenset(p % EDO for p in G), frozenset(p % EDO for p in Y))
                print(f"     strict: {gl:6s} {vs(G):18s} overshoot {E} settle {c}" + ("" if c == dm else f" (smoothest {dm})"))
        else:
            print("     strict: none")
        extra = [r for r in resp if r not in res]
        if extra:
            print("     partial (some voices land): " + "; ".join(
                f"{gname(GOLD[frozenset(p % EDO for p in G)])} {vs(G)} E={E}" for c, E, G in extra[:6]))
        print(f"     uniform extrapolation P4 = Y + (Y - X)/3 = {vs(P4)} = {p4}")


def s5_extrapolation():
    H("5. Uniform extrapolation P4 = Y + d (d = (Y - X)/3): a census over all stepwise and leaping voice leadings")
    # all pairs of major/minor triads on layer 0 (X root C), all voice assignments with |motion| <= m semitones per voice
    for m in (2, 4, 7, 12):
        cnt = Counter()
        examples = defaultdict(list)
        for xq in ("", "m"):
            X = sorted(chord(0, xq))
            for yr in range(0, EDO, 3):
                for yq in ("", "m"):
                    Yset = sorted(chord(yr, yq))
                    for perm in permutations(Yset):
                        for D in product(*[[fold(y - x) + 36 * k for k in (-1, 0, 1)] for x, y in zip(X, perm)]):
                            if any(abs(d) > 3 * m for d in D) or not any(D):
                                continue
                            d = [x // 3 for x in D]
                            P1 = [x + di for x, di in zip(X, d)]
                            P2 = [x + 2 * di for x, di in zip(X, d)]
                            P4 = [x + 4 * di for x, di in zip(X, d)]
                            P5 = [x + 5 * di for x, di in zip(X, d)]
                            g1, g2, g4 = is_golden(P1), is_golden(P2), is_golden(P4)
                            cnt["P5 golden"] += is_golden(P5)
                            cnt["paths"] += 1
                            cnt["P1 golden"] += g1
                            cnt["P2 golden"] += g2
                            cnt["P4 golden"] += g4
                            cnt["P4 golden and P1 golden"] += g4 and g1
                            if g4:
                                examples[(cname(0, xq), cname(yr, yq))].append((sum(map(abs, d)), tuple(d), lab(P4), lab(P1)))
        print(f"\n  |motion| <= {m} semitones per voice (X = C or Cm, Y any major/minor on layer 0): {dict(cnt)}")
        if m == 12 and examples:
            print("   P4 golden examples (smallest total motion first):")
            allx = sorted((v[0][0], k, v[0]) for k, v in examples.items() for _ in [0])
            for _, k, v in sorted(allx)[:30]:
                print(f"     {k[0]:3s} -> {k[1]:4s} motion {v[1]} P4 = {v[2]:6s} (P1 = {v[3]})")
    print("\n  Layer rule: voice i of P4 sits on layer 4 d_i = d_i (mod 3), the same as P1: so P4 can be golden only when the")
    print("  voice leading has a held, a rising and a falling class (admissibility, Chapter 27).")
    print("\n  Theorem check (any motion size): X = Y - 3d and G = Y + d give X = 4Y - 3G (mod 36). With Y on layer 0,")
    print("  4Y_i is 0, 12 or 24, and -3G = -3g + (0, 3, 6) for a golden G on root g; so X in semitones is")
    print("  -g' + {4a, 4b + 1, 4c + 2}: three notes with three different residues mod 4. Source chords by residue pattern:")
    from songmap.theory.passing import TYPES as PT
    for q in ("", "m", "aug", "dim", "sus4", "sus2"):
        iv = [i // 3 for i in PT[q]]
        res = sorted({i % 4 for i in iv})
        cons = len(iv) == 3 and len(res) == 3 and any({(r + k) % 4 for k in range(3)} == set(res) for r in range(4))
        # brute force: does any X of this quality (root C), any layer-0 Y (any 3-note multiset of layer-0 pcs, any voice
        # assignment) give a golden P4?  Equivalent: is 4Y - 3G a voicing of X for some golden G and layer-0 Y?
        hit = 0
        if len(iv) == 3:
            Xs = frozenset((3 * i) % EDO for i in iv)
            for g in range(EDO):
                G = (g, g + 11, g + 22)
                for Y in product(range(0, EDO, 3), repeat=3):
                    for Gp in permutations(G):
                        Xc = frozenset((4 * y - 3 * gg) % EDO for y, gg in zip(Y, Gp))
                        if Xc == Xs:
                            hit += 1
        print(f"   {('C' + q) if q else 'C':6s} residues mod 4 {res}: three consecutive {cons}; golden P4 possible (brute force): {hit > 0}")
    print("  By reversal (P_-1 = X - d is P4 of the reversed path Y -> X), a uniform backswing before X is never golden")
    print("  when the target Y is major or minor either.")


def approaches_into(Y, Ylab, kmax=3):
    """For every Western major/minor triad X on layer 0 and every voice leading X -> Y (each voice moving at most an
    octave, up or down), the strict golden overshoots. Returns {golden root: [(total motion, X label, motions)]}."""
    res = defaultdict(list)
    Ys = sorted(Y)
    for xr in range(0, EDO, 3):
        for xq in ("", "m"):
            Xs = sorted(chord(xr, xq))
            for perm in permutations(Xs):                     # perm[i] is the X note that goes to Ys[i]
                opts = []
                for x, y in zip(perm, Ys):
                    f = fold(y - x)
                    o = {f}
                    if f > 0:
                        o.add(f - 36)
                    elif f < 0:
                        o.add(f + 36)
                    opts.append(sorted(o))
                for D in product(*opts):
                    s = tuple(0 if d == 0 else (1 if d > 0 else -1) for d in D)
                    for ks in product(*[((0,) if si == 0 else tuple(range(1, kmax + 1))) for si in s]):
                        E = tuple(si * k for si, k in zip(s, ks))
                        if not any(E):
                            continue
                        G = frozenset((y + e) % EDO for y, e in zip(Ys, E))
                        if G in GOLD:
                            res[GOLD[G]].append((sum(map(abs, D)) // 3 if False else sum(map(abs, D)), cname(xr, xq),
                                                 tuple(d // 3 for d in D), E))
    return res


def s6_approaches():
    H("6. Which approaches into C (and Cm) overshoot onto which golden chord (all major/minor X, all voice leadings)")
    for Ylab, Y in (("C", (0, 12, 21)), ("Cm", (0, 9, 21))):
        res = approaches_into(Y, Ylab)
        print(f"\n  Target {Ylab} (voices listed root, third, fifth of the target; motions in semitones):")
        for r, L in sorted(res.items(), key=lambda kv: min(sum(map(abs, e[3])) for e in kv[1])):
            L = sorted(set(L))
            cost = min(sum(map(abs, e[3])) for e in L)
            byx = {}
            for tm, xl, D, E in L:
                if xl not in byx or tm < byx[xl][0]:
                    byx[xl] = (tm, D, E)
            ex = ", ".join(f"{xl} {D}" for xl, (tm, D, E) in sorted(byx.items(), key=lambda kv: kv[1][0])[:8])
            print(f"   {gname(r):6s} (settle {cost}): from {len(byx)} source triads; smallest motions: {ex}")


# --------------------------------------------------------------------------- appoggiatura
def s7_appoggiatura():
    H("7. Golden appoggiatura chords: golden triads by distance to C and Cm, and their resolutions")
    for Ylab, Y in (("C", chord(0, "")), ("Cm", chord(0, "m"))):
        rows = []
        for r in range(EDO):
            d, mv, p = vl_moves(chord(r, "g"), Y)
            rows.append((d, r, mv, p))
        rows.sort()
        print(f"\n  Golden triads nearest {Ylab} (motion of each golden note, sorted by golden pitch, into {Ylab}):")
        for d, r, mv, p in rows:
            if d > 6:
                break
            g = sorted(chord(r, "g"))
            mvs = ", ".join(f"{name36(a)}->{name36(b)} {m:+d}" for a, b, m in zip(g, p, mv) if m)
            n = sum(1 for m in mv if m)
            print(f"   d = {d}: {gname(r):6s} ({mvs}); {n} voices move, largest {max(map(abs, mv))}")
        by = Counter(d for d, *_ in rows)
        print("   distribution of distances:", dict(sorted(by.items())))
    # every voice moves at most a semitone (3 sixth-steps) into C, all falling / all rising
    print("\n  Golden triads resolving into C with every voice moving by at most a semitone:")
    for r in range(EDO):
        G = sorted(chord(r, "g"))
        for perm in permutations(sorted(chord(0, ""))):
            mv = [fold(b - a) for a, b in zip(G, perm)]
            if max(map(abs, mv)) <= 3:
                tag = ("all rise" if all(m >= 0 for m in mv) else "all fall" if all(m <= 0 for m in mv) else "contrary")
                print(f"   {gname(r):6s} -> C: " + ", ".join(f"{name36(a)}->{name36(b)} {m:+d}" for a, b, m in zip(G, perm, mv))
                      + f"  total {sum(map(abs, mv))}, {tag}")
    # four-part: golden upper voices over the resolution's bass
    print("\n  Golden appoggiatura chords over the bass of the resolution (upper voices golden, close, nearest voicing):")
    for blab, bass, Yu in (("C", 0, chord(0, "")), ("G", 21, chord(21, ""))):
        rows = []
        for r in range(EDO):
            d, mv, p = vl_moves(chord(r, "g"), Yu)
            rows.append((d, r, mv, p))
        rows.sort()
        out = []
        for d, r, mv, p in rows[:8]:
            fall = all(m <= 0 for m in mv)
            rise = all(m >= 0 for m in mv)
            inb = bass in chord(r, "g")
            out.append(f"{gname(r)}/{blab} d {d}{' (falling)' if fall else ' (rising)' if rise else ''}{' [contains bass]' if inb else ''}")
        print(f"   over {blab}: " + "; ".join(out))
    print("\n  The cadential six-four C/G -> G in 36-ET (strict path, upper voices G3 C4 E4 -> G3 B3 D4):")
    X, Y = voicing("G3 C4 E4"), voicing("G3 B3 D4")
    d = [(y - x) // 3 for x, y in zip(X, Y)]
    for k in range(4):
        P = [x + k * di for x, di in zip(X, d)]
        print(f"   P{k} = {vs(P):16s} {classify(tuple([voicing('G2')[0]] + P)).name}")
    print("  (the golden six-four of Chapter 27 read backwards: the Western six-four falls through vCg/G into V)")


# --------------------------------------------------------------------------- suspensions
def s8_suspensions():
    H("8. Golden suspensions and retardations")
    # (a) Western-only suspensions are never golden
    n = 0
    for X in WEST:
        for Y in WEST:
            for held in X:
                for keep in Y:
                    S = frozenset(list(Y - {keep}) + [held])
                    n += S in GOLD
    print(f"  (a) Western preparation, Western resolution, one or more held notes: golden verticals found = {n}"
          " (all notes stay on layer 0; theorem)")
    # (b) golden double suspension: prep golden G, one voice moves to a Western note, S golden, S -> Y distance 2
    print("\n  (b) Golden double suspensions: golden preparation P, one voice moves (<= a semitone) to a note of Y while two")
    print("      golden notes are held, the vertical S is golden, and the held notes resolve by sixth-steps into Western Y:")
    rows = []
    for Ylab, Y in (("C", (0, 12, 21)), ("Cm", (0, 9, 21))):
        for pr in range(EDO):
            P = sorted(chord(pr, "g"))
            for k in range(3):                       # voice k of P moves
                for m in range(-3, 4):
                    if m == 0:
                        continue
                    new = (P[k] + m) % EDO
                    if new % 3 != 0 or new not in Y:
                        continue
                    S = frozenset([new] + [P[i] for i in range(3) if i != k])
                    if S not in GOLD:
                        continue
                    held = [P[i] for i in range(3) if i != k]
                    rest = [y for y in Y if y != new]
                    best = None
                    for pp in permutations(rest):
                        mv = [fold(b - a) for a, b in zip(held, pp)]
                        if best is None or sum(map(abs, mv)) < sum(map(abs, best[0])):
                            best = (mv, pp)
                    mv, pp = best
                    rows.append((Ylab, gname(pr), name36(P[k]), name36(new), m, gname(GOLD[S]),
                                 [(name36(a), name36(b), x) for a, b, x in zip(held, pp, mv)]))
    for Ylab, pn, a, b, m, sn, res in rows:
        print(f"   {pn:6s} -> {sn:6s} ({a}->{b} {m:+d}, others held) -> {Ylab}: "
              + ", ".join(f"{x}->{y} {z:+d} ({'retardation' if z > 0 else 'suspension'})" for x, y, z in res))
    # (c) the projection's two bends can be staggered
    print("\n  (c) Staggered resolution of a projection (one bend first, the other held): ")
    for Ylab, Y, r in (("C", (0, 12, 21), 0), ("Cm", (0, 9, 21), 35)):
        G = sorted(chord(r, "g"))
        d, mv, p = vl_moves(chord(r, "g"), frozenset(Y))
        for i in range(3):
            if mv[i] == 0:
                continue
            S = [p[j] if j != i and mv[j] else G[j] for j in range(3)]
            S = [G[j] if j == i else p[j] for j in range(3)]
            print(f"   {gname(r)} -> {lab(S):8s} ({name36(G[i])} held {'above' if mv[i] < 0 else 'below'} its target) -> {Ylab}:"
                  f" {name36(G[i])}->{name36(p[i])} {mv[i]:+d} ({'suspension' if mv[i] < 0 else 'retardation'})")
    # (d) golden upper voices held over a moving bass, resolving to the nearest Western collections
    print("\n  (d) Cg held over a new bass, then resolved by sixth-steps (each voice <= 2): the four nearest Western")
    print("      collections (C, Cm, Caug, Ab) over every bass note on layer 0 that makes a named chord:")
    from songmap.theory.passing import TYPES as PT
    targets = {"C": (0, 12, 21), "Cm": (0, 9, 21), "Caug": (0, 12, 24), "Ab": (0, 9, 24)}
    for tl, T_ in targets.items():
        out = []
        for b in range(0, EDO, 3):
            s = frozenset(list(T_) + [b])
            for t, iv in PT.items():
                if t in ("g", "g7", "s", "T13"):
                    continue
                for rr in range(0, EDO, 3):
                    if frozenset((rr + i) % EDO for i in iv) == s:
                        out.append(f"{name36(b)}: {cname(rr, '') if t == '' else name36(rr) + t}" + ("" if rr == b else f"/{name36(b)}"))
        d = vl(chord(0, "g"), frozenset(T_))
        print(f"   Cg -> {tl} (d {d}): " + "; ".join(sorted(set(out))))
    # (e) suspension chains along the golden circle
    print("\n  (e) Chains along the golden circle ending in the projection of C (each step: one voice a semitone, two held):")
    for direction, lab_ in ((-11, "falling chain (each moving voice falls a semitone)"), (11, "rising chain (each moving voice rises)")):
        seq = [0]
        r = 0
        for _ in range(4):
            r = (r + direction) % EDO      # predecessor on the walk into Cg
            seq.append(r)
        seq = seq[::-1]
        steps_ = []
        for a, b in zip(seq, seq[1:]):
            A, B = chord(a, "g"), chord(b, "g")
            out_, in_ = list(A - B)[0], list(B - A)[0]
            steps_.append(f"{name36(out_)}->{name36(in_)} {fold(in_ - out_):+d}")
        print(f"   {lab_}: " + " -> ".join(gname(x) for x in seq) + " -> C   [" + "; ".join(steps_) + "; then the projection bends]")


# --------------------------------------------------------------------------- anticipation, escape: census by type
SMOOTH = [
    ("V -> I", "G3 B3 D4", "G3 C4 E4"),
    ("IV -> I", "F3 A3 C4", "E3 G3 C4"),
    ("I -> IV", "E3 G3 C4", "F3 A3 C4"),
    ("I -> V", "G3 C4 E4", "G3 B3 D4"),
    ("ii -> V", "F3 A3 D4", "G3 B3 D4"),
    ("V -> vi", "G3 B3 D4", "A3 C4 E4"),
    ("IV -> V", "F3 A3 C4", "G3 B3 D4"),
    ("I -> vi", "G3 C4 E4", "A3 C4 E4"),
    ("bVI -> I", "Ab3 C4 Eb4", "G3 C4 E4"),
    ("I -> I (neighbour frame)", "G3 C4 E4", "G3 C4 E4"),
]


def census(X, Y, win=6):
    """All golden voicings G with every voice within win sixth-steps of its X note or its Y note; classified."""
    lo = [min(x, y) - win for x, y in zip(X, Y)]
    hi = [max(x, y) + win for x, y in zip(X, Y)]
    out = defaultdict(list)
    dxy = L1(X, Y)
    for G in product(*[range(a, b + 1) for a, b in zip(lo, hi)]):
        if not is_golden(G):
            continue
        t, ts = chord_type(X, G, Y)
        if t == "mixed":
            core = sorted(set(ts) - {"hold"})
            t = "mixed:" + "+".join(core)
        ex = L1(X, G) + L1(G, Y) - dxy
        out[t].append((ex, L1(X, G), G, ts))
    return out


def s9_census():
    H("9. Every golden chord near a progression, classified by the betweenness framework (window 6 sixth-steps)")
    for name, xs, ys in SMOOTH:
        X, Y = voicing(xs), voicing(ys)
        out = census(X, Y)
        print(f"\n  {name}: {xs} -> {ys} (d = {L1(X, Y)})")
        for t in sorted(out, key=lambda t: min(e[0] for e in out[t])):
            L = sorted(out[t])
            ex, dxg, G, ts = L[0]
            print(f"   {t:32s} {len(L):3d} chords; best excess {ex:2d}: {vs(G):18s} "
                  f"{gname(GOLD[frozenset(p % EDO for p in G)]):6s} voices {ts}")


def s10_escape_anticipation():
    H("10. Escape chords and anticipation chords (uniform types), smallest excess, for V -> I and IV -> I")
    X, P, G, Y = voicing("G3 B3 D4"), voicing("vAb3 ^B3 Eb4"), voicing("^A3 C#4 vF4"), voicing("A3 C4 E4")
    print(f"  golden cambiata V -> vAbg (passing) -> ^Ag (overshoot) -> vi: types {chord_type(X, P, Y)[1]} then "
          f"{chord_type(X, G, Y)[1]}; motion {L1(X, P)} + {L1(P, G)} + {L1(G, Y)} = {L1(X, P) + L1(P, G) + L1(G, Y)}"
          f" against {L1(X, Y)} direct")
    for name, xs, ys in SMOOTH[:2] + [SMOOTH[4]]:
        X, Y = voicing(xs), voicing(ys)
        out = census(X, Y, 9)
        for t in ("escape", "anticipation", "overshoot", "passing"):
            L = sorted(out.get(t, []))
            s = "; ".join(f"{vs(G)} = {gname(GOLD[frozenset(p % EDO for p in G)])} (excess {ex})" for ex, _, G, _ in L[:4])
            print(f"   {name:7s} {t:12s}: {len(L)} chords. {s}")
        # anticipation in the wide sense: at least one voice already on its target, all other voices passing or holding
        wide = []
        for t, L in out.items():
            for ex, dxg, G, ts in L:
                if "anticipation" in ts and set(ts) <= {"anticipation", "passing", "hold"}:
                    wide.append((ex, G, ts))
        wide.sort()
        print(f"   {name:7s} anticipation + passing (no detour): {len(wide)}. " +
              "; ".join(f"{vs(G)} = {gname(GOLD[frozenset(p % EDO for p in G)])} {ts}" for ex, G, ts in wide[:4]))


# --------------------------------------------------------------------------- neighbours
def s11_neighbours():
    H("11. Golden neighbour chords of C (C -> G -> C), upper, lower and split; double neighbours")
    C = voicing("C4 E4 G4")
    rows = []
    for G in product(*[range(c - 6, c + 7) for c in C]):
        if not is_golden(G):
            continue
        mv = [g - c for g, c in zip(G, C)]
        t = ("upper" if all(m >= 0 for m in mv) else "lower" if all(m <= 0 for m in mv) else "split")
        rows.append((sum(map(abs, mv)), t, G, mv))
    rows.sort()
    cnt = Counter(t for _, t, _, _ in rows)
    print(f"  golden voicings within a whole tone of C4 E4 G4 in every voice: {len(rows)}; by type {dict(cnt)}")
    for d, t, G, mv in rows:
        if d <= 7:
            print(f"   {t:5s} d {d}: {vs(G):16s} {gname(GOLD[frozenset(p % EDO for p in G)]):6s} motions {mv}")
    best = {}
    for d, t, G, mv in rows:
        best.setdefault(t, (d, G, mv))
    print("  nearest of each type:", {t: (d, vs(G), mv) for t, (d, G, mv) in best.items()})
    # double neighbours: C -> G1 -> G2 -> C with every moving voice going one way in G1 and the other in G2
    dn = []
    for d1, t1, G1, m1 in rows:
        for d2, t2, G2, m2 in rows:
            if all((a == 0 and b == 0) or a * b < 0 for a, b in zip(m1, m2)) and any(m1):
                dn.append((d1 + d2 + L1(G1, G2), G1, G2, m1, m2))
    dn.sort()
    print(f"  double neighbours (each voice above then below, or below then above, or held): {len(dn)}")
    for tot, G1, G2, m1, m2 in dn[:8]:
        print(f"   total motion {tot}: C -> {vs(G1)} ({gname(GOLD[frozenset(p % EDO for p in G1)])}) -> {vs(G2)} "
              f"({gname(GOLD[frozenset(p % EDO for p in G2)])}) -> C   {m1} then {m2}")
    # over a tonic pedal, golden chords containing C (the golden pedal six-four)
    print("\n  Golden chords containing C as neighbour chords over a C pedal (upper C held):")
    for r in (0, 25, 14):
        G = chord(r, "g")
        d, mv, p = vl_moves(chord(0, ""), G)
        print(f"   {gname(r)}/C: motion from C E G {mv} (d {d})")
    print("   Western pedal six-four F/C: motion (0, +3, +6) = 9; vFg/C is 2/3 of the way: the strict passing chord P2 of C -> F/C")


# --------------------------------------------------------------------------- reharmonization
ODE = [  # (letter, octave) quarter notes, Beethoven's "Ode to Joy" theme (1824, public domain); dotted: (note, beats)
    ("E", 1), ("E", 1), ("F", 1), ("G", 1), ("G", 1), ("F", 1), ("E", 1), ("D", 1),
    ("C", 1), ("C", 1), ("D", 1), ("E", 1), ("E", 1.5), ("D", 0.5), ("D", 2),
    ("E", 1), ("E", 1), ("F", 1), ("G", 1), ("G", 1), ("F", 1), ("E", 1), ("D", 1),
    ("C", 1), ("C", 1), ("D", 1), ("E", 1), ("D", 1.5), ("C", 0.5), ("C", 2),
]
PC = {"C": 0, "D": 6, "E": 12, "F": 15, "G": 21, "A": 27, "B": 33}


def golden_containing(x):
    return [r for r in range(EDO) if x % EDO in chord(r, "g")]


DIATONIC = [chord(r, q) for r, q in ((0, ""), (6, "m"), (12, "m"), (15, ""), (21, ""), (27, "m"))]


def harmonize(mel, fixed, lam=None, golden=True):
    """Dynamic programme: each melody note gets a chord containing it (or the fixed Western chord at that index) and
    the summed voice-leading distance between consecutive chords is minimized (a repeated chord costs 0).
    Candidates: the three golden triads containing the note (golden=True) and, if lam is not None, also the major and
    minor triads of C major containing it, each charged lam extra (lam = 0: pure smoothness)."""
    cands = []
    for i, x in enumerate(mel):
        if i in fixed:
            cands.append([(fixed[i], 0)])
            continue
        c = [(chord(r, "g"), 0) for r in golden_containing(x)] if golden else []
        if lam is not None:
            c += [(d, lam) for d in DIATONIC if x in d]
        cands.append(c)
    best = [{c: (pen, None) for c, pen in cands[0]}]
    for i in range(1, len(mel)):
        layer = {}
        for c, pen in cands[i]:
            layer[c] = min(((best[-1][p][0] + vl(p, c) + pen, p) for p in best[-1]), key=lambda t: t[0])
        best.append(layer)
    c = min(best[-1], key=lambda k: best[-1][k][0])
    path = [c]
    for i in range(len(mel) - 1, 0, -1):
        c = best[i][c][1]
        path.append(c)
    path = path[::-1]
    return sum(vl(a, b) for a, b in zip(path, path[1:])), path


def chordname(s):
    s = frozenset(s)
    if s in GOLD:
        return gname(GOLD[s])
    return WEST.get(s, lab(s))


def s12_reharm():
    H("12. Reharmonizing a Western melody with golden chords")
    ok = all(len(golden_containing(x)) == 3 for x in range(EDO))
    cons = all(sorted(fold(23 * r - 23 * x) for r in golden_containing(x)) == [-2, -1, 0] for x in range(EDO))
    print(f"  every pitch class lies in exactly three golden triads: {ok}; consecutive on the golden circle: {cons}")
    for x in (0, 6, 12, 15, 21, 27, 33):
        rs = golden_containing(x)
        print(f"   {name36(x):3s}: " + ", ".join(f"{gname(r)} ({'root' if r == x else 'third' if (x - r) % EDO == 11 else 'fifth'},"
                                              f" circle {fold(23 * r)})" for r in rs))
    print("  Diatonic comparison: each note of C major lies in three diatonic triads (root, third, fifth), not consecutive")
    print("  on the circle of fifths but a third apart (C: C, Am, F).")
    mel = [PC[n] for n, _ in ODE]
    # all golden; then with Western cadences: bar 4 half cadence on G (index 14 = D), final C (index 29)
    cad = {13: chord(21, ""), 14: chord(21, ""), 27: chord(21, ""), 28: chord(0, ""), 29: chord(0, "")}
    for title, fixed, lam, gold in (("all golden, no cadence constraint", {}, None, True),
                                    ("all golden, Western cadences (G in bar 4, G - C at the end)", cad, None, True),
                                    ("golden or diatonic, pure smoothness (lam = 0), Western cadences", cad, 0, True),
                                    ("golden colour: diatonic chords charged 4 (lam = 4), Western cadences", cad, 4, True),
                                    ("diatonic only, Western cadences", cad, 0, False)):
        tot, path = harmonize(mel, fixed, lam, gold)
        ng = sum(1 for c in path if c in GOLD)
        print()
        print(f"  Ode to Joy, {title}: voice-leading {tot} sixth-steps; {ng} of {len(mel)} notes golden")
        print("   " + " ".join(f"{n}:{chordname(c)}" for (n, du), c in zip(ODE, path)))
        steps_ = Counter()
        for a_, b_ in zip(path, path[1:]):
            if a_ != b_:
                k_ = ("circle step" if a_ in GOLD and b_ in GOLD and len(a_ & b_) == 2 else
                      "planing" if a_ in GOLD and b_ in GOLD and (GOLD[b_] - GOLD[a_]) % EDO in (1, 35) else "")
                steps_[(chordname(a_), chordname(b_), vl(a_, b_), k_)] += 1
        print("   changes: " + "; ".join(f"{a_}->{b_} {d}{' ' + k_ if k_ else ''} x{n}" for (a_, b_, d, k_), n in steps_.items()))
    print()
    print("  Cheapest move between golden triads containing two melody notes a given interval apart (pc voice leading):")
    for st in range(7):
        best_ = min((vl(chord(a_, "g"), chord(b_, "g")), gname(a_), gname(b_))
                    for a_ in golden_containing(0) for b_ in golden_containing(3 * st))
        print(f"   melody moves {st} semitones: {best_[0]:2d} ({best_[1]} -> {best_[2]})")


# --------------------------------------------------------------------------- further ideas
def s13_further():
    H("13. Further strategies: golden backdoor, chromatic-mediant cadence, golden pedal six-four, elastic cadence")
    from songmap.theory.passing import TYPES as PT, evaluate
    for nm, a, qa, b, qb in (("bVII -> I (backdoor)", 30, "", 0, ""), ("bVI -> I", 24, "", 0, ""), ("III -> I", 12, "", 0, ""),
                             ("bIII -> I", 9, "", 0, ""), ("iv -> I", 15, "m", 0, ""), ("bII -> I", 3, "", 0, "")):
        for nat, pref in ((False, ""), (True, "g")):
            ch, l1, l2 = evaluate(a, PT[qa], b, PT[qb], nat, pref)
            print(f"   {nm:20s} {'natural' if nat else 'strict '}: {cname(a, qa)} - {l1.name} - {l2.name} - {cname(b, qb)}"
                  f"   lines {[vs(c) for c in ch]}")
    print("\n  Distances into C of the golden chords that end these cadences:")
    for r in (34, 0, 35, 12):
        d, mv, p = vl_moves(chord(r, "g"), chord(0, ""))
        print(f"   {gname(r)} -> C: d {d}, motions {mv}")


# --------------------------------------------------------------------------- roughness of the examples
def s14_roughness():
    H("14. Roughness of the voicings used in the audio examples (Sethares model, harmonic partials 1..8; measurement;")
    print("    four notes, bass included, each counted once (no unison doublings); partials referred to C4 = 261.63 Hz)")
    ex = [
        ("overshoot_def: G (before the leap)", "G3 G4 B4 D5"),
        ("overshoot_def: partial overshoot vCg", "vC3 vC4 ^Eb4 G4"),
        ("overshoot_def: full overshoot ^Bg", "^B2 ^B3 Eb4 vG4"),
        ("overshoot_def: settle C", "C3 C4 E4 G4"),
        ("appoggiatura_def: Cg on the downbeat", "C3 C4 vE4 ^G4"),
        ("appoggiatura_def: Gg on the downbeat", "G2 G3 vB3 ^D4"),
        ("appoggiatura_def: G", "G2 G3 B3 D4"),
        ("appoggiatura_def: golden six-four vCg/G", "G2 G3 vC4 ^Eb4"),
        ("(comparison) Western cadential six-four C/G", "G2 G3 C4 E4"),
        ("suspensions_def: vEg/B (preparation)", "B2 B3 vE4 ^G4"),
        ("suspensions_def: Em/B", "B2 B3 E4 G4"),
        ("suspensions_def: C(^5), fifth still held", "C3 C4 E4 ^G4"),
        ("suspensions_def: C(v3), third still held", "C3 C4 vE4 G4"),
        ("neighbour_def: golden pedal six-four vFg/C", "C3 C4 vF4 ^Ab4"),
        ("neighbour_def: Western pedal six-four F/C", "C3 C4 F4 A4"),
    ]
    for nm, v in ex:
        a = [p - 180 for p in voicing(v)]
        print(f"   {nm:62s} {roughness(a):.3f}")


SECTIONS = [s1_framework, s2_overshoot_tables, s3_reflection, s4_progressions, s5_extrapolation, s6_approaches,
            s7_appoggiatura, s8_suspensions, s9_census, s10_escape_anticipation, s11_neighbours, s12_reharm,
            s13_further, s14_roughness]

if __name__ == "__main__":
    want = {int(a) for a in sys.argv[1:]}
    for i, f in enumerate(SECTIONS, 1):
        if not want or i in want:
            f()
