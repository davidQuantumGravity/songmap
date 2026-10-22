"""Golden harmony beyond passing chords: modulation, key maps, bridges, modes, hybrid scales and
blending techniques. Every table in docs/GOLDEN_BLENDING.md is printed by this script.

    .venv/Scripts/python reference/golden/blending.py            # everything (section 5 takes a few minutes)
    .venv/Scripts/python reference/golden/blending.py 3 7       # only sections 3 and 7

Sections:  1 comma/limma/apotome, chain distance c(s)   2 the comma pump (golden13 walks), d = |c| theorem
           3 map of keys (CT and VL)                    4 lifts by sixth-steps and third-steps
           5 passing engine across layers (slow)        6 golden geodesic hinges; lift midpoints
           7 the golden projection, PLR through it      8 projection pivots between keys; golden7 <-> Western
           9 bridge scales, interstitial scales         10 the golden escalator as keys (negative)
          11 modes of golden7/golden13, evenness        12 golden inflections of C major (3^7)
          13 centroid scales (averages of 3 modes)      14 all 7-note scales: hybrid frontier, Myhill, ME
          15 golden planing = polytonality              16 pedals and drones (roughness)
          17 approach chords, golden Neapolitan         18 sequences (giant steps, golden-third keys)
          19 roughness of the chords used               20 SongMap sketches D1..D21 (parse + expand)

Conventions: pitch classes are sixth-steps mod 36 (C = 0, ^C = 1, vC# = 2, C# = 3, ...); the layer of p
is p mod 3. Names come from songmap.theory.passing.name36. Voice-leading distance between two chords or
scales of equal size is the minimum, over bijections, of the summed circular distances (sixth-steps).
Roughness is the Sethares model of reference/golden/explore.py (harmonic partials 1..8, amplitudes
0.88^(k-1), k = 1..8, close position from C4 = 261.63 Hz unless stated); it is a measurement in a model.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from functools import lru_cache
from itertools import combinations, permutations, product
from math import log2, sqrt
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from songmap.theory.passing import classify, evaluate, name36  # noqa: E402

PHI = (1 + sqrt(5)) / 2
EDO = 36
GEN = 25                                   # golden sixth phi in sixth-steps
INV25 = 13                                 # 25 * 13 = 325 = 9*36 + 1: chain position of pitch p is 13 p


def cents(r):
    return 1200 * log2(r)


def H(t):
    print("\n" + "=" * 100 + f"\n{t}\n" + "=" * 100)


def fold(x, n=EDO):
    """Representative of x mod n in [-n/2, n/2)."""
    return (x + n // 2) % n - n // 2


def cd(a, b):
    """Circular distance in Z36."""
    return abs(fold(b - a))


def names(s):
    return " ".join(name36(x) for x in sorted(s))


def chain_pos(p):
    """Golden-chain position j of pitch class p (25 j = p mod 36), folded to [-18, 18)."""
    return fold(INV25 * p)


# --------------------------------------------------------------------------- chords
TRI = {"": (0, 12, 21), "m": (0, 9, 21), "aug": (0, 12, 24), "dim": (0, 9, 18),
       "g": (0, 11, 22), "s": (0, 10, 20), "T13": (0, 13, 26)}
CONSONANT = ("", "m")
METALLIC = ("g", "s", "T13")


def chord(r, q):
    return frozenset((r + i) % EDO for i in TRI[q])


def cname(r, q):
    return name36(r) + q


ALL_TRIADS = {}                          # frozenset -> list of (root, quality)
for _q in TRI:
    for _r in range(EDO):
        ALL_TRIADS.setdefault(chord(_r, _q), []).append((_r, _q))


def triad_label(s):
    s = frozenset(s)
    if s in ALL_TRIADS:
        r, q = ALL_TRIADS[s][0]
        return cname(r, q)
    return "{" + names(s) + "}"


def vl(a, b):
    """Minimal voice-leading distance between two pc-sets of equal size (sum of circular distances)."""
    a, b = sorted(a), sorted(b)
    n = len(a)
    assert n == len(b)
    if n <= 7:
        return min(sum(cd(x, y) for x, y in zip(a, p)) for p in permutations(b))
    # on the circle an optimal matching of equal-size sets is a cyclic shift of the sorted order
    return min(sum(cd(a[i], b[(i + k) % n]) for i in range(n)) for k in range(n))


def vl_moves(a, b):
    """(distance, moves) for 3-note chords: moves[i] = signed motion of a's sorted note i."""
    a = sorted(a)
    best = None
    for p in permutations(sorted(b)):
        mv = [fold(y - x) for x, y in zip(a, p)]
        d = sum(map(abs, mv))
        if best is None or d < best[0]:
            best = (d, mv, p)
    return best


def triads_in(S, quals=TRI):
    S = frozenset(S)
    return [(r, q) for q in quals for r in range(EDO) if chord(r, q) <= S]


def triad_census(S):
    c = Counter(q for _, q in triads_in(S))
    return {q: c.get(q, 0) for q in TRI}


# --------------------------------------------------------------------------- scales
def T(S, t):
    return frozenset((x + t) % EDO for x in S)


MAJOR = frozenset((0, 6, 12, 15, 21, 27, 33))
NMINOR = frozenset((0, 6, 9, 15, 21, 24, 30))
HMINOR = frozenset((0, 6, 9, 15, 21, 24, 33))
MMINOR = frozenset((0, 6, 9, 15, 21, 27, 33))


def chain_window(lo, hi):
    return frozenset((GEN * j) % EDO for j in range(lo, hi + 1))


def layer_mirror(S):
    return frozenset((3 * round(x / 3) * 2 - x) % EDO for x in S)


G7 = chain_window(-3, 3)
G10 = chain_window(-4, 5)
G13 = chain_window(-6, 6)
G23 = chain_window(-11, 11)
S13 = layer_mirror(G13)
FAMILIES = {"major": MAJOR, "minor": NMINOR, "hminor": HMINOR, "golden7": G7, "golden13": G13, "silver13": S13}

# The 7-note modes on C used for centroid scales (sixth-steps)
MODES7 = {
    "ionian": (0, 6, 12, 15, 21, 27, 33), "dorian": (0, 6, 9, 15, 21, 27, 30),
    "phrygian": (0, 3, 9, 15, 21, 24, 30), "lydian": (0, 6, 12, 18, 21, 27, 33),
    "mixolydian": (0, 6, 12, 15, 21, 27, 30), "aeolian": (0, 6, 9, 15, 21, 24, 30),
    "locrian": (0, 3, 9, 15, 18, 24, 30), "harm.minor": (0, 6, 9, 15, 21, 24, 33),
    "mel.minor": (0, 6, 9, 15, 21, 27, 33), "lyd.aug": (0, 6, 12, 18, 24, 27, 33),
    "harm.major": (0, 6, 12, 15, 21, 24, 33),
}


def steps_of(S):
    a = sorted(S)
    return [(a[(i + 1) % len(a)] - a[i]) % EDO for i in range(len(a))]


def generic_sizes(S):
    """For each generic interval k = 1..n-1, the set of specific sizes (sixth-steps)."""
    a = sorted(S)
    n = len(a)
    return {k: sorted({(a[(i + k) % n] - a[i]) % EDO for i in range(n)}) for k in range(1, n)}


def myhill(S):
    """Myhill's property: every generic interval comes in exactly two specific sizes."""
    return all(len(v) == 2 for v in generic_sizes(S).values())


def is_mos(S):
    """Generated by one interval (some unit-free g), and has exactly two step sizes."""
    n = len(S)
    if len(set(steps_of(S))) != 2:
        return False
    for g in range(1, EDO):
        for x0 in S:
            if frozenset((x0 + g * j) % EDO for j in range(n)) == frozenset(S):
                return True
    return False


def max_even(S):
    """Clough-Douthett: maximally even = every generic interval has one size or two consecutive sizes."""
    return all(len(v) == 1 or (len(v) == 2 and v[1] - v[0] == 1) for v in generic_sizes(S).values())


# --------------------------------------------------------------------------- roughness (explore.py model)
def _diss(fr, am):
    d = 0.0
    for i in range(len(fr)):
        for j in range(i + 1, len(fr)):
            f1, f2 = sorted((fr[i], fr[j]))
            s = 0.24 / (0.0207 * f1 + 18.96)
            d += min(am[i], am[j]) * (np.exp(-3.5 * s * (f2 - f1)) - np.exp(-5.75 * s * (f2 - f1)))
    return d


def roughness(steps_abs, f0=261.63, spectrum="harmonic"):
    """steps_abs: absolute sixth-steps above f0 (a voicing). Harmonic partials 1..8, amps 0.88^(k-1), k = 1..8."""
    if spectrum == "harmonic":
        parts = list(range(1, 9))
    else:
        parts = sorted({2 ** m * PHI ** n for m in range(4) for n in range(4) if 2 ** m * PHI ** n < 9})
    amps = [0.88 ** i for i in range(len(parts))]
    fr, am = [], []
    for c in steps_abs:
        for p, a in zip(parts, amps):
            fr.append(f0 * 2 ** (c / 36) * p)
            am.append(a)
    return _diss(fr, am)


def close(S, root):
    """Close position of pc-set S above `root` (the lowest note), as absolute sixth-steps from C4."""
    r = root % EDO
    return sorted(r + (x - r) % EDO for x in S)


# ===================================================================================================
def s1_units():
    H("1. The three small golden intervals as modulation units (exact and 36-ET)")
    rows = [("golden comma  phi^13/2^9", PHI ** 13 / 2 ** 9, 13),
            ("golden limma  2^7/phi^10", 2 ** 7 / PHI ** 10, -10),
            ("golden apotome phi^3/4", PHI ** 3 / 4, 3),
            ("chain 23: phi^23/2^16", PHI ** 23 / 2 ** 16, 23),
            ("36-comma phi^36/2^25", PHI ** 36 / 2 ** 25, 36)]
    print(f"  {'interval':28s} {'exact c':>9s} {'chain j':>8s} {'25 j mod 36':>12s} {'36-ET c':>8s}")
    for n, r, j in rows:
        st = fold(GEN * j)
        print(f"  {n:28s} {cents(r):9.2f} {j:8d} {st:12d} {st * 1200 / 36:8.2f}")
    print("  check: 13*25 = 325 = 9*36 + 1;  -10*25 = -250 = -7*36 + 2;  3*25 = 75 = 2*36 + 3")
    print("  apotome - limma = comma:", round(cents(PHI ** 3 / 4) - cents(2 ** 7 / PHI ** 10), 2), "c;",
          " limma + comma = ", round(cents(2 ** 7 / PHI ** 10) + cents(PHI ** 13 / 2 ** 9), 2), "c (36-ET: 2 + 1 = 3)")
    print("\n  Chain distance of every transposition s (sixth-steps): c(s) = 13 s mod 36, folded to [-18, 18)")
    print("   s  name  c(s) | s  name  c(s) | s  name  c(s) | s  name  c(s)")
    for i in range(9):
        print("  " + " | ".join(f"{s:2d} {name36(s):>4s} {chain_pos(s):4d}" for s in (i, i + 9, i + 18, i + 27)))
    print("\n  Chroma of each golden MOS (chain distance n between the note that leaves and the note that enters):")
    for n in (3, 4, 7, 10, 13, 23):
        ex = (n * cents(PHI)) % 1200
        ex = ex - 1200 if ex > 600 else ex
        print(f"   golden{n:<3d} chain {n:2d} -> {fold(GEN * n):+3d} sixth-steps (exact {ex:+8.2f} c)")


def golden13_walk(start_t, nsteps, direction):
    """Walk golden13 keys along the chain from tonic start_t: direction +1 = tonic up a golden sixth."""
    k = chain_pos(start_t)
    S = chain_window(k - 6, k + 6)
    out = []
    for i in range(nsteps):
        k2 = k + direction
        S2 = chain_window(k2 - 6, k2 + 6)
        (o,), (n,) = tuple(S - S2), tuple(S2 - S)
        out.append((i + 1, (GEN * k2) % EDO, o, n, fold(n - o), S2))
        k, S = k2, S2
    return out


def s2_comma_pump():
    H("2. The comma pump: golden13 keys along the chain (each step changes one note by one sixth-step)")
    C_MAJ, UC_MAJ, VCS_MAJ = MAJOR, T(MAJOR, 1), T(MAJOR, 2)
    for title, t0, n, dirn, target in [("C golden13 -> ^C golden13: 13 steps up the chain (modulation by a golden comma)", 0, 13, +1, 1),
                                       ("C golden13 -> vC golden13: 13 steps down the chain", 0, 13, -1, 35),
                                       ("C golden13 -> vC# golden13: 10 steps down the chain (modulation by a golden limma)", 0, 10, -1, 2),
                                       ("C golden13 -> C# golden13: 3 steps up (modulation by a golden apotome)", 0, 3, +1, 3)]:
        print(f"\n  {title}")
        print(f"   {'step':>4s} {'tonic':>6s}  {'out':>4s} -> {'in':4s} {'move':>4s}  |S n Cmaj| |S n ^Cmaj| |S n vC#maj|")
        S = G13
        print(f"   {0:4d} {name36(t0):>6s}  {'':4s}    {'':4s} {'':4s}  {len(S & C_MAJ):10d} {len(S & UC_MAJ):11d} {len(S & VCS_MAJ):12d}")
        walk = golden13_walk(t0, n, dirn)
        for i, t, o, nn, mv, S in walk:
            print(f"   {i:4d} {name36(t):>6s}  {name36(o):>4s} -> {name36(nn):4s} {mv:+4d}  {len(S & C_MAJ):10d} "
                  f"{len(S & UC_MAJ):11d} {len(S & VCS_MAJ):12d}")
        assert walk[-1][1] == target and walk[-1][5] == T(G13, target)
        assert all(abs(w[4]) == 1 for w in walk)
        print(f"   end = golden13 on {name36(target)} (verified); every step moves exactly one note by one sixth-step")
    # the tonic golden triads of the walk are consecutive golden-circle chords
    tonics = [0] + [w[1] for w in golden13_walk(0, 13, +1)]
    steps_ = [fold(b - a) for a, b in zip(tonics, tonics[1:])]
    print("\n  Tonic golden triads of the 13-step walk: " + " ".join(name36(t) + "g" for t in tonics))
    print(f"   root steps {set(steps_)} (= -11: one golden-circle step each; the fifth rises a semitone and becomes"
          f" the root); 13 x (-11) = {13 * -11} = {fold(13 * -11)} mod 36")
    for t in tonics:
        assert chord(t, "g") <= T(G13, t)
    # theorem: VL distance between golden13 keys = |chain distance| for |c| <= 13
    print("\n  Voice-leading distance between C golden13 and its 36 transpositions vs chain distance |c(s)|:")
    rows = []
    for s in range(EDO):
        rows.append((s, abs(chain_pos(s)), vl(G13, T(G13, s)), len(G13 & T(G13, s))))
    ok = all(d == c for s, c, d, _ in rows if c <= 13)
    print("   s:name |c| VL CT  ...")
    for i in range(0, 36, 6):
        print("   " + "  ".join(f"{name36(s):>4s} {c:2d} {d:2d} {ct:2d}" for s, c, d, ct in rows[i:i + 6]))
    print(f"   VL = |c| for every |c| <= 13: {ok};  for |c| > 13 VL = "
          + ", ".join(f"{name36(s)}:{d}" for s, c, d, _ in rows if c > 13))
    # golden7 comparison
    print("\n  golden7 by comparison: each chain step changes one note by 5 sixth-steps (the golden7 chroma).")
    rows7 = [(s, abs(chain_pos(s)), vl(G7, T(G7, s)), len(G7 & T(G7, s))) for s in range(EDO)]
    near7 = sorted(rows7, key=lambda r: (r[2], r[1]))[:10]
    print("   nearest golden7 keys to C golden7 by VL: " + ", ".join(f"{name36(s)} (VL {d}, |c| {c}, CT {ct})" for s, c, d, ct in near7))


def s3_key_map():
    H("3. A map of keys: common tones (CT) and voice-leading distance (VL) from C in each family")
    fam = [("major", MAJOR), ("minor", NMINOR), ("golden7", G7), ("golden13", G13), ("silver13", S13)]
    print("  Reference: C major. Columns: target family on tonic s.  CT / VL (VL only for equal sizes).")
    hdr = "   s  name | " + " | ".join(f"{n:>9s}" for n, _ in fam)
    print(hdr)
    for s in range(EDO):
        cells = []
        for n, F in fam:
            S = T(F, s)
            ct = len(MAJOR & S)
            cells.append(f"{ct:2d}/{vl(MAJOR, S):3d}" if len(S) == 7 else f"{ct:2d}/  -")
        print(f"  {s:3d} {name36(s):>5s} | " + " | ".join(f"{c:>9s}" for c in cells))
    print("\n  Nearest keys to C major by VL (7-note families):")
    allk = [(vl(MAJOR, T(F, s)), len(MAJOR & T(F, s)), f"{name36(s)} {n}") for n, F in fam for s in range(EDO)
            if len(F) == 7 and not (n == "major" and s == 0)]
    for d, ct, k in sorted(allk)[:16]:
        print(f"   {k:16s} VL {d:3d}  CT {ct}")
    print("\n  Nearest golden7 keys to C major, and nearest major keys to C golden7:")
    g = sorted((vl(MAJOR, T(G7, s)), name36(s)) for s in range(EDO))[:6]
    print("   from C major:", ", ".join(f"{n} golden7 ({d})" for d, n in g))
    g = sorted((vl(G7, T(MAJOR, s)), name36(s)) for s in range(EDO))[:6]
    print("   from C golden7:", ", ".join(f"{n} major ({d})" for d, n in g))
    print("\n  Max common tones of C major with any golden13 / silver13 / golden7 key:",
          max(len(MAJOR & T(G13, s)) for s in range(EDO)), max(len(MAJOR & T(S13, s)) for s in range(EDO)),
          max(len(MAJOR & T(G7, s)) for s in range(EDO)))
    print("   golden13 keys sharing 3 notes with C major:",
          ", ".join(f"{name36(s)} ({names(MAJOR & T(G13, s))})" for s in range(EDO) if len(MAJOR & T(G13, s)) == 3))
    # layer split of golden scales
    print("\n  Notes per layer (tonic layer first): golden7", [len([x for x in G7 if x % 3 == l]) for l in (0, 1, 2)],
          " golden13", [len([x for x in G13 if x % 3 == l]) for l in (0, 1, 2)],
          " silver13", [len([x for x in S13 if x % 3 == l]) for l in (0, 1, 2)])
    print("\n  13-note families: nearest silver13 keys to C golden13 by VL (and CT):")
    r13 = sorted((vl(G13, T(S13, s)), len(G13 & T(S13, s)), name36(s)) for s in range(EDO))[:5]
    print("   " + ", ".join(f"{n} silver13 (VL {d}, CT {c})" for d, c, n in r13))
    print("\n  Major-key VL by transposition (the 'pitch-near, tone-far' profile):")
    print("   " + "  ".join(f"{name36(s)}:{vl(MAJOR, T(MAJOR, s))}" for s in range(0, 19)))


def s4_lifts():
    H("4. Direct lifts: sixth-step and third-step key changes (planing modulation)")
    I = chord(0, "")
    print(f"  {'shift':>5s} {'target':>8s} {'tonic VL':>8s} {'moves':>14s} {'scale VL':>8s} {'scale moves (C D E F G A B)':>40s}")
    for s in (1, 2, -1, -2, 3, 4, 5):
        Y = chord(s, "")
        d, mv, _ = vl_moves(I, Y)
        sc = sorted(MAJOR)
        tgt = T(MAJOR, s)
        # optimal scale matching via cyclic shifts with explicit moves
        b = sorted(tgt)
        cand = []
        for k in range(7):
            mvv = [fold(b[(i + k) % 7] - sc[i]) for i in range(7)]
            cand.append((sum(map(abs, mvv)), mvv))
        dd, mvv = min(cand)
        print(f"  {s:+5d} {name36(s) + ' maj':>8s} {d:8d} {str(mv):>14s} {dd:8d} {str(mvv):>40s}")
    print("\n  Theorem check: any minimal voice leading from X (one layer) to X + 1 moves each voice by +1, so")
    print("  every intermediate set uses only layers 0 and 1 and contains no golden/silver/bronze triad.")
    # minor-key targets
    print("\n  Tonic-to-tonic distances from C major to minor keys nearby:")
    for s in (0, 1, 2, 35, 34, 10, 26):
        d, mv, _ = vl_moves(I, chord(s, "m"))
        print(f"   C -> {cname(s, 'm'):6s} VL {d}  moves {mv}")
    print("\n  Roughness is a function of the intervals and (weakly) of register; planing by a sixth-step changes it by:")
    for q in ("", "m", "g"):
        r0 = roughness(close(chord(0, q), 0))
        r1 = roughness(close(chord(1, q), 1))
        print(f"   {cname(0, q):4s} {r0:.4f}  ->  {cname(1, q):5s} {r1:.4f}   (delta {r1 - r0:+.4f})")


# --------------------------------------------------------------------------- the passing engine across layers
def diatonic_triads(S):
    S = frozenset(S)
    return sorted([(r, q) for q in ("", "m", "dim", "aug") for r in sorted(S) if chord(r, q) <= S],
                  key=lambda rq: sorted(S).index(rq[0]))


def s5_engine():
    H("5. Pivot and passing paths across layers via the passing engine (strict ~ and natural ~g)")
    targets = [("^C major", T(MAJOR, 1)), ("vC# major", T(MAJOR, 2)), ("^Eb major (= ^C minor)", T(MAJOR, 10))]
    X = key_triads(MAJOR)                        # the six consonant triads (slow: about a minute per target)
    for tname, K in targets:
        Y = key_triads(K)
        tot = Counter()
        golden_list = Counter()
        ex = []
        for (xr, xq), (yr, yq) in product(X, Y):
            for natural, pref in ((False, ""), (True, "g")):
                ch, l1, l2 = evaluate(xr, TRI[xq], yr, TRI[yq], natural, pref)
                kinds = (l1.kind, l2.kind)
                g = sum(k == "golden" for k in kinds)
                if g == 2 and l1.name.split("/")[0] == l2.name.split("/")[0]:
                    g = 1                                   # one golden chord held over P1 and P2
                gp = sum(k == "golden_pedal" for k in kinds)
                tag = "nat" if natural else "str"
                tot[(tag, "pairs")] += 1
                tot[(tag, ">=1 golden")] += g >= 1
                tot[(tag, "2 golden")] += g == 2
                tot[(tag, "golden or pedal")] += (g + gp) >= 1
                for l in (l1, l2):
                    if l.kind == "golden":
                        golden_list[(tag, l.name.split("/")[0])] += 1
                if natural and g >= 1:
                    motion = sum(cd(a, b) for a, b in zip(ch[0], ch[3]))
                    ex.append((-g, motion, f"{cname(xr, xq)} - {l1.name} - {l2.name} - {cname(yr, yq)}"))
        print(f"\n  C major diatonic triads -> {tname} diatonic triads ({len(X)} x {len(Y)} pairs)")
        for tag in ("str", "nat"):
            print(f"   {tag}: pairs {tot[(tag, 'pairs')]}, >=1 exact golden {tot[(tag, '>=1 golden')]}, two different golden "
                  f"{tot[(tag, '2 golden')]}, golden incl. over-pedal {tot[(tag, 'golden or pedal')]}")
            gl = sorted(((n, c) for (t, n), c in golden_list.items() if t == tag), key=lambda x: -x[1])
            if gl:
                print("        golden chords used:", ", ".join(f"{n} x{c}" for n, c in gl))
        for _, m, s in sorted(ex)[:24]:
            print(f"     natural, motion {m:2d}: {s}")


def geodesic_hinges(X, Y, slack=0):
    """Golden triads G with d(X,G) + d(G,Y) <= d(X,Y) + slack."""
    dxy = vl(X, Y)
    out = []
    for r in range(EDO):
        G = chord(r, "g")
        s = vl(X, G) + vl(G, Y)
        if s <= dxy + slack:
            out.append((s - dxy, r))
    return dxy, out


def s6_hinges():
    H("6. Golden hinges: golden triads on (or near) a minimal voice leading between keys' triads")
    for tname, s in [("^C major", 1), ("vC# major", 2), ("C# major", 3), ("vC major", 35)]:
        K = T(MAJOR, s)
        X, Y = diatonic_triads(MAJOR), diatonic_triads(K)
        n0 = n2 = 0
        hingecount = Counter()
        rows = []
        for (xr, xq), (yr, yq) in product(X, Y):
            A, B = chord(xr, xq), chord(yr, yq)
            dxy, hs = geodesic_hinges(A, B, slack=2)
            ex0 = [r for e, r in hs if e == 0]
            n0 += bool(ex0)
            n2 += bool(hs)
            for r in ex0:
                hingecount[name36(r) + "g"] += 1
            if ex0 and xq in CONSONANT and yq in CONSONANT:
                rows.append((dxy, f"{cname(xr, xq)} -> {cname(yr, yq)}: d = {dxy}, exact hinges " +
                             ", ".join(name36(r) + "g" for r in ex0)))
        print(f"\n  C major -> {tname}: pairs with an exact golden hinge {n0}/{len(X) * len(Y)}; "
              f"with a hinge of excess <= 2: {n2}")
        if hingecount:
            print("   hinge chords:", ", ".join(f"{k} x{v}" for k, v in hingecount.most_common()))
        for _, r in sorted(rows)[:10]:
            print("    ", r)
    print("\n  Lifts of a single triad X -> X + s (all 24 major/minor triads on layer 0; exact geodesic golden hinges):")
    for sh in (1, 2, 4, 5, -1, -2):
        res = Counter()
        for q in ("", "m"):
            for r in range(0, EDO, 3):
                A = chord(r, q)
                dxy, hs = geodesic_hinges(A, T(A, sh), 0)
                res[(q, dxy, tuple(sorted(fold(g - r) for _, g in hs)))] += 1
        print(f"   s = {sh:+d}: " + "; ".join(f"{'major' if q == '' else 'minor'} d={d} hinge roots at offset {offs} ({n})"
                                        for (q, d, offs), n in sorted(res.items())))
    print("\n  Theorem check (layer betweenness): for X on layer 0 and Y = X + 1, no golden triad lies on a geodesic.")
    bad = 0
    for q in ("", "m", "dim", "aug"):
        for r in range(0, EDO, 3):
            A = chord(r, q)
            B = T(A, 1)
            _, hs = geodesic_hinges(A, B, 0)
            bad += len(hs)
    print("   golden geodesic hinges between X and X+1 over all 12-ET triads:", bad)


# --------------------------------------------------------------------------- the golden projection
def projection(r, q):
    """Golden triads at minimal distance from a Western triad."""
    A = chord(r, q)
    ds = [(vl(A, chord(g, "g")), g) for g in range(EDO)]
    m = min(d for d, _ in ds)
    return m, [g for d, g in ds if d == m]


def proj1(r, q):
    m, gs = projection(r, q)
    assert len(gs) == 1
    return gs[0]


def key_triads(S, quals=("", "m")):
    return [(r, q) for (r, q) in diatonic_triads(S) if q in quals]


def s7_projection():
    H("7. The golden projection: every major/minor/augmented triad has one nearest golden triad")
    res = Counter()
    for q in ("", "m", "aug", "dim"):
        for r in range(EDO):
            m, gs = projection(r, q)
            res[(q, m, tuple(fold(g - r) for g in gs))] += 1
    for (q, m, offs), c in sorted(res.items()):
        print(f"   {('maj' if q == '' else q):4s} distance {m}  golden roots at offset {offs} from the root  ({c} roots)")
    print("\n  Preimage: Western triads at distance 2 from Cg (all layers):",
          ", ".join(cname(r, q) for q in ("", "m", "aug", "dim") for r in range(EDO) if vl(chord(r, q), chord(0, "g")) == 2))
    print("  Distance 1 from any golden triad: impossible (counted:",
          sum(1 for q in ("", "m", "aug", "dim") for r in range(EDO) for g in range(EDO)
              if vl(chord(r, q), chord(g, "g")) == 1), ")")
    # projection of neo-Riemannian moves
    def P(r, q):
        return (r, "m" if q == "" else "")

    def L(r, q):
        return ((r + 12) % EDO, "m") if q == "" else ((r + 24) % EDO, "")

    def R(r, q):
        return ((r + 27) % EDO, "m") if q == "" else ((r + 9) % EDO, "")

    print("\n  Neo-Riemannian moves seen through the projection pi (golden root change, all 72 triads):")
    for nm, f in (("P", P), ("L", L), ("R", R)):
        c = Counter()
        for q in ("", "m"):
            for r in range(EDO):
                a, b = proj1(r, q), proj1(*f(r, q))
                c[(q, fold(b - a))] += 1
        print(f"   {nm}: " + ", ".join(f"from {'major' if q == '' else 'minor'}: golden root {d:+d} ({n})"
                                    for (q, d), n in sorted(c.items())))
    print("   (+-11 = one golden-circle step, +-1 = planing by a sixth-step, -10/+10 = circle step + planing)")
    # projections of the C major diatonic triads
    print("\n  Projections of the C major diatonic triads:")
    for r, q in key_triads(MAJOR, ("", "m")):
        g = proj1(r, q)
        print(f"   {cname(r, q):4s} -> {name36(g)}g = {names(chord(g, 'g'))}   moves {vl_moves(chord(r, q), chord(g, 'g'))[1]}")


def proj_set(S, quals=("", "m")):
    """Golden projections of the key's triads of the given qualities (an augmented triad has three)."""
    return frozenset(g for r, q in key_triads(S, quals) for g in projection(r, q)[1])


def s8_projection_pivots():
    H("8. Projection pivots: keys that share golden projections (golden pivot chords in the Western sense)")
    fams = [("major", MAJOR), ("minor", NMINOR), ("hminor", HMINOR)]
    base = proj_set(MAJOR)
    print("  C major projections:", ", ".join(name36(g) + "g" for g in sorted(base)))
    print("  Western keys (consonant triads, all 36 tonics) sharing >= 2 projections with C major:")
    for n, F in fams:
        for s in range(EDO):
            K = T(F, s)
            ps = proj_set(K, ("", "m"))
            sh = base & ps
            if len(sh) >= 2 and not (n == "major" and s == 0) and not (n == "minor" and s == 27):
                pairs = []
                for g in sorted(sh):
                    a = [cname(r, q) for r, q in key_triads(MAJOR) if proj1(r, q) == g]
                    b = [cname(r, q) for r, q in key_triads(K) if proj1(r, q) == g]
                    pairs.append(f"{name36(g)}g ({'/'.join(a)} | {'/'.join(b)})")
                print(f"   {name36(s)} {n:6s} (shift {fold(s):+3d}): {len(sh)} shared: " + "; ".join(pairs))
    print("\n  Distribution over all 108 keys (36 major, 36 natural minor, 36 harmonic minor) of #shared projections:")
    for n, F in fams:
        c = Counter(len(base & proj_set(T(F, s), ('', 'm'))) for s in range(EDO))
        print(f"   {n:7s} {dict(sorted(c.items()))}")
    # golden7 keys vs Western keys, including augmented triads (harmonic minor's III+)
    print("\n  Golden7 keys and Western keys: golden7 triads that are projections of the Western key's triads")
    print("  (major, minor and augmented triads projected; best Western partner of C golden7):")
    g7tri = frozenset(r for r, q in triads_in(G7, ("g",)))
    rows = []
    for n, F in fams + [("mminor", MMINOR)]:
        for s in range(EDO):
            K = T(F, s)
            ps = proj_set(K, ("", "m", "aug"))
            sh = g7tri & ps
            rows.append((len(sh), n, s, sh))
    for k, n, s, sh in sorted(rows, key=lambda x: -x[0])[:8]:
        K = T(dict(fams + [("mminor", MMINOR)])[n], s)
        det = []
        for g in sorted(sh):
            b = [cname(r, q) for r, q in key_triads(K, ("", "m", "aug")) if g in projection(r, q)[1]]
            det.append(f"{name36(g)}g<-{'/'.join(b)}")
        print(f"   {name36(s)} {n:7s}: {k} of 5: " + ", ".join(det))


def s9_bridges():
    H("9. Bridge scales between two Western keys (golden7, golden10, golden13, silver13, and centroid 7-sets)")
    pairs = [("C major", MAJOR, "^C major", T(MAJOR, 1)), ("C major", MAJOR, "vC# major", T(MAJOR, 2)),
             ("C major", MAJOR, "C# major", T(MAJOR, 3)), ("C major", MAJOR, "D major", T(MAJOR, 6)),
             ("C major", MAJOR, "^C minor", T(NMINOR, 1))]
    fams = [("golden7", G7), ("golden10", G10), ("golden13", G13), ("silver13", S13)]
    for n1, K1, n2, K2 in pairs:
        print(f"\n  {n1} -> {n2}: d(K1,K2) = {vl(K1, K2)}, common tones {len(K1 & K2)}")
        for fn, F in fams:
            scored = []
            for s in range(EDO):
                S = T(F, s)
                a, b = len(S & K1), len(S & K2)
                v = (vl(K1, S) + vl(S, K2)) if len(S) == 7 else None
                scored.append((min(a, b), a + b, -(v or 0), s, a, b, v))
            top = sorted(scored, key=lambda x: (-x[0], -x[1], -x[2]))[:3]
            print(f"   {fn:8s} best by shared notes: " + "; ".join(
                f"{name36(s)} ({a}+{b}" + (f", VL {v}" if v is not None else "") + ")" for _, _, _, s, a, b, v in top))
            if len(F) == 7:
                bv = sorted(scored, key=lambda x: x[6])[:3]
                print(f"   {'':8s} best by VL sum   : " + "; ".join(f"{name36(s)} (VL {v}: {vl(K1, T(F, s))}+{vl(T(F, s), K2)})"
                                                            for _, _, _, s, a, b, v in bv))
    # interstitial scales: raise a subset of C major by one sixth-step
    print("\n  Interstitial scales between C major and ^C major (raise a subset A of notes by a sixth-step):")
    deg = sorted(MAJOR)
    best = []
    for m in range(1, 7):
        for A in combinations(range(7), m):
            S = frozenset((deg[i] + (1 if i in A else 0)) % EDO for i in range(7))
            cen = triad_census(S)
            best.append((cen[""] + cen["m"], m, A, S, cen))
    for m in range(1, 7):
        cands = sorted([b for b in best if b[1] == m], key=lambda b: -b[0])
        top = cands[0]
        print(f"   {m} raised: max consonant triads {top[0]}: e.g. {names(top[3])}  ->  "
              + ", ".join(triad_label(chord(r, q)) for r, q in triads_in(top[3], ('', 'm'))))
    # best monotone order (maximize the minimum number of consonant triads over the 6 interstitial stages)
    cons = {frozenset(b[2]): b[0] for b in best}
    cons[frozenset()] = cons[frozenset(range(7))] = 6

    @lru_cache(None)
    def bestpath(A):
        if len(A) == 7:
            return (99, ())
        out = None
        for i in range(7):
            if i not in A:
                B = A | frozenset([i])
                v, p = bestpath(B)
                val = (min(v, cons[B]) if len(B) < 7 else v, (i,) + p)
                if out is None or val[0] > out[0]:
                    out = val
        return out

    v, p = bestpath(frozenset())
    print(f"   best raising order (max-min consonant triads = {v}): " + " ".join(name36(deg[i]) for i in p))
    A = set()
    for i in p[:-1]:
        A.add(i)
        S = frozenset((deg[j] + (1 if j in A else 0)) % EDO for j in range(7))
        print(f"     after {name36(deg[i]):>2s}: {names(S):34s} " + ", ".join(triad_label(chord(r, q)) for r, q in triads_in(S, ('', 'm'))))


def s10_escalator_keys():
    H("10. Passing keys: the golden escalator elevated to key areas (C major -> D major, F -> G)")
    for a, b in ((0, 6), (15, 21)):
        for nat, pref in ((True, "g"),):
            ch, l1, l2 = evaluate(a, TRI[""], b, TRI[""], nat, pref)
            print(f"  engine (natural): {name36(a)} - {l1.name} - {l2.name} - {name36(b)}")
    K1, K2 = MAJOR, T(MAJOR, 6)
    print("\n  Candidate passing keys between C major and D major (tonics vC#, ^C#; golden7 and golden13):")
    for t in (2, 4):
        for fn, F in (("golden7", G7), ("golden13", G13)):
            S = T(F, t)
            print(f"   {name36(t)} {fn:8s}: {names(S)}")
            print(f"       shares with C major {len(S & K1)} ({names(S & K1)}), with D major {len(S & K2)} ({names(S & K2)})"
                  + (f", VL {vl(K1, S)} / {vl(S, K2)}" if len(S) == 7 else ""))
    for a, b, g1, g2 in ((0, 6, 2, 4), (15, 21, 17, 19)):
        for fn, F in (("golden7", G7), ("golden10", G10), ("golden13", G13), ("silver13", S13)):
            hits = [s for s in range(EDO) if chord(g1, "g") <= T(F, s) and chord(g2, "g") <= T(F, s)]
            print(f"   {fn:8s} keys containing both {name36(g1)}g and {name36(g2)}g: "
                  + (", ".join(f"{name36(s)} (shares {len(T(F, s) & MAJOR)} with C major, "
                               f"{len(T(F, s) & T(MAJOR, b if a == 0 else 21))} with {name36(b if a == 0 else 21)} major)"
                               for s in hits) or "none"))
        print(f"   circle positions of {name36(g1)}g, {name36(g2)}g: {fold(23 * g1)}, {fold(23 * g2)}")
    S1, S2 = T(G7, 2), T(G7, 4)
    print(f"   vC# golden7 vs ^C# golden7: common {len(S1 & S2)}, VL {vl(S1, S2)}, chain distance {abs(chain_pos(2))}")
    print(f"   direct C major -> D major: common {len(K1 & K2)}, VL {vl(K1, K2)}")
    # scale-level escalator: averages
    for w in (1, 2):
        avg = frozenset(((3 - w) * x + w * y) // 3 for x, y in zip(sorted(K1), sorted(K2)))
        print(f"   scale average ({3 - w}*C major + {w}*D major)/3 degree by degree: {names(avg)}  triads: "
              + ", ".join(triad_label(chord(r, q)) for r, q in triads_in(avg, TRI)))


def s11_modes():
    H("11. Modes: rotations of golden7 and golden13 (step patterns, chain position, tonic chords)")
    for fn, F, m in (("golden7", G7, 3), ("golden13", G13, 6)):
        print(f"\n  {fn} on C, modes by tonic, brightest first (brightness = sum of the C-mode's degrees in sixth-steps;"
              f" consecutive modes differ in exactly one degree, by the chroma):")
        rows = []
        for t in sorted(F):
            S = T(F, -t)                       # mode on t, transposed to C
            j = chain_pos(t)
            st = steps_of(S)
            gtr = sorted(fold(r) for r, q in triads_in(S, ("g",)))
            tonic = chord(0, "g") <= S
            sev = frozenset((0, 11, 22, 33)) <= S
            rows.append((j, t, st, gtr, tonic, sev, S))
        rows.sort(key=lambda r: -sum(r[6]))
        for a_, b_ in zip(rows, rows[1:]):
            assert all(x >= y for x, y in zip(sorted(a_[6]), sorted(b_[6])))
            assert sum(x != y for x, y in zip(sorted(a_[6]), sorted(b_[6]))) == 1
        for j, t, st, gtr, tonic, sev, S in rows:
            print(f"   brightness {sum(S):4d} chain {j:+3d} on {name36(t):>3s}: steps {' '.join(map(str, st)):28s} tonic golden triad {'yes' if tonic else 'no ':3s}"
                  f"  tonic g7 {'yes' if sev else 'no '}  golden triads {len(gtr)}  as C-mode: {names(S)}")
    print("\n  Step-size structure and evenness checks:")
    for fn, S in (("C major (in 36)", MAJOR), ("golden7", G7), ("golden10", G10), ("golden13", G13), ("golden23", G23),
                  ("silver13", S13)):
        print(f"   {fn:16s} steps {sorted(Counter(steps_of(S)).items())}  MOS {is_mos(S)}  Myhill {myhill(S)}  "
              f"maximally even {max_even(S)}")
    me13 = frozenset((36 * k) // 13 for k in range(13))
    print("   ME13 = floor(36k/13):", names(me13), " = a transposition of golden13:",
          any(T(G13, s) == me13 for s in range(EDO)))
    me7 = frozenset((36 * k) // 7 for k in range(7))
    print("   ME7  = floor(36k/7): ", names(me7), " triads:", triad_census(me7))


def inflections():
    deg = sorted(MAJOR)
    out = []
    for mv in product((-1, 0, 1), repeat=7):
        S = frozenset((d + m) % EDO for d, m in zip(deg, mv))
        out.append((mv, S, triad_census(S)))
    return out


def s12_inflections():
    H("12. Golden inflections of C major: every degree moved by -1, 0 or +1 sixth-step (3^7 = 2187 scales)")
    inf = inflections()
    with_g = [x for x in inf if x[2]["g"] > 0]
    print(f"  scales with >= 1 golden triad: {len(with_g)};  max golden triads: {max(x[2]['g'] for x in inf)}")
    front = defaultdict(list)
    for mv, S, c in inf:
        front[(c[""] + c["m"], c["g"])].append((sum(map(abs, mv)), mv, S, c))
    pareto = [k for k in front if not any(k2 != k and k2[0] >= k[0] and k2[1] >= k[1] for k2 in front)]
    print("  Pareto frontier (consonant Western triads W, golden triads G):")
    for W, G in sorted(pareto):
        cand = sorted(front[(W, G)])[:3]
        for cost, mv, S, c in cand:
            tri = ", ".join(triad_label(chord(r, q)) for r, q in triads_in(S, ("", "m", "g")))
            print(f"   W={W} G={G}  moves {mv}  ({cost} inflected)  {names(S):34s} {tri}")
    print("\n  Named examples:")
    for nm, mv in [("golden Ionian (E->vE, G->^G)", (0, 0, -1, 0, 1, 0, 0)),
                   ("golden Ionian + vA", (0, 0, -1, 0, 1, -1, 0)),
                   ("E->vE, G->^G, B->vB? no: A->vA, B->vB", (0, 0, -1, 0, 1, -1, -1))]:
        S = frozenset((d + m) % EDO for d, m in zip(sorted(MAJOR), mv))
        c = triad_census(S)
        print(f"   {nm:40s} {names(S):34s} census {c}  Myhill {myhill(S)}  MOS {is_mos(S)}  "
              + ", ".join(triad_label(chord(r, q)) for r, q in triads_in(S, ("", "m", "g", "s", "T13"))))
    ms = [x for x in inf if myhill(x[1])]
    print(f"\n  inflections with Myhill's property: {len(ms)}: " + "; ".join(f"{names(S)} {c}" for _, S, c in ms[:6]))


def s13_centroids():
    H("13. Centroid scales: degree-by-degree averages of three modes on C (always on the 36-ET grid)")
    nm = list(MODES7)
    rows = []
    for a, b, c in [(i, j, k) for i in range(len(nm)) for j in range(i, len(nm)) for k in range(j, len(nm))]:
        A, B, Cc = MODES7[nm[a]], MODES7[nm[b]], MODES7[nm[c]]
        avg = tuple((x + y + z) // 3 for x, y, z in zip(A, B, Cc))
        assert all((x + y + z) % 3 == 0 for x, y, z in zip(A, B, Cc))
        S = frozenset(avg)
        cen = triad_census(S)
        rows.append(((nm[a], nm[b], nm[c]), avg, S, cen))
    print(f"  {len(rows)} multisets of 3 from {len(nm)} modes; grid check passed (sum of three 12-ET pitches is divisible by 3).")
    distinct = {r[2] for r in rows}
    print(f"  distinct centroid scales: {len(distinct)}; containing a golden triad: "
          f"{len({r[2] for r in rows if r[3]['g']})}; the tonic golden triad Cg: {len({r[2] for r in rows if chord(0, 'g') <= r[2]})}")
    print("\n  Named centroids:")
    named = [("ionian", "ionian", "aeolian"), ("ionian", "aeolian", "aeolian"), ("ionian", "aeolian", "lyd.aug"),
             ("ionian", "ionian", "lydian"), ("ionian", "lydian", "lyd.aug"), ("ionian", "aeolian", "locrian"),
             ("ionian", "dorian", "lyd.aug"), ("ionian", "harm.minor", "lyd.aug"), ("ionian", "mixolydian", "lydian"),
             ("ionian", "ionian", "lyd.aug")]
    for key in named:
        r = next(x for x in rows if x[0] == tuple(sorted(key, key=nm.index)))
        tri = ", ".join(triad_label(chord(rr, q)) for rr, q in triads_in(r[2], TRI))
        print(f"   ({' + '.join(key)})/3 = {names(r[1]):36s} steps {steps_of(r[2])}  Myhill {myhill(r[2])}  [{tri}]")
    print("\n  Centroids containing Cg, with their full triad content:")
    seen = set()
    for key, avg, S, cen in rows:
        if chord(0, "g") <= S and S not in seen:
            seen.add(S)
            tri = ", ".join(triad_label(chord(rr, q)) for rr, q in triads_in(S, TRI))
            print(f"   {'+'.join(key):34s} {names(S):34s} [{tri}]")
    print("\n  Two-mode averages: (X + Y)/2 is on the 36 grid only where every degree differs by an even number of")
    print("  semitones, and then it is on 12-ET: e.g. (ionian + aeolian)/2 third =",
          (12 + 9) / 2, "sixth-steps (off the 36 grid).")


def s14_exhaustive_hybrids():
    H("14. All 7-note scales of 36-ET containing C: Western consonant triads (W) vs golden triads (G)")
    masks = {}
    for q in TRI:
        masks[q] = [sum(1 << x for x in chord(r, q)) for r in range(EDO)]
    combos = np.fromiter((sum(1 << x for x in (0,) + c) for c in combinations(range(1, EDO), 6)), dtype=np.uint64)
    print(f"  {len(combos)} scales (C plus 6 of the other 35 notes)")
    cnt = {}
    for q in TRI:
        tot = np.zeros(len(combos), dtype=np.int16)
        for m in masks[q]:
            mm = np.uint64(m)
            tot += ((combos & mm) == mm)
        cnt[q] = tot
    W = cnt[""] + cnt["m"]
    G = cnt["g"]
    print(f"  max W = {W.max()}, max G = {G.max()}, max W with G >= 1 = {W[G >= 1].max()}, max G with W >= 1 = {G[W >= 1].max()}")
    tab = Counter(zip(W.tolist(), G.tolist()))
    pareto = [k for k in tab if not any(k2 != k and k2[0] >= k[0] and k2[1] >= k[1] for k2 in tab)]
    print("  Pareto frontier (W, G): count of scales (up to rotation counting C fixed):")
    for k in sorted(pareto):
        idx = np.nonzero((W == k[0]) & (G == k[1]))[0]
        exs = []
        for i in idx[:400]:
            S = frozenset(x for x in range(EDO) if int(combos[i]) >> x & 1)
            exs.append(S)
        # one representative per transposition class
        classes = {}
        for S in exs:
            key = min(tuple(sorted(T(S, -t))) for t in S)
            classes.setdefault(key, S)
        print(f"   W={k[0]} G={k[1]}: {tab[k]} scales; e.g.")
        for key in list(classes)[:3]:
            S = frozenset(key)
            print(f"      {names(S):36s} Myhill {myhill(S)} MOS {is_mos(S)} [" +
                  ", ".join(triad_label(chord(r, q)) for r, q in triads_in(S, ('', 'm', 'g'))) + "]")
    # Myhill's property, vectorized over all 1.6M scales
    arr = np.array([(0,) + c for c in combinations(range(1, EDO), 6)], dtype=np.int16)
    my = np.ones(len(arr), dtype=bool)
    me = np.ones(len(arr), dtype=bool)
    for k in range(1, 7):
        d = (np.roll(arr, -k, axis=1) - arr) % EDO
        d.sort(axis=1)
        nd = 1 + (np.diff(d, axis=1) != 0).sum(axis=1)
        my &= nd == 2
        me &= (nd == 1) | ((nd == 2) & (d[:, -1] - d[:, 0] == 1))
    print(f"  Myhill scales: {int(my.sum())} (containing C); with W >= 1: {int((my & (W >= 1)).sum())}, with G >= 1: "
          f"{int((my & (G >= 1)).sum())}, with both: {int((my & (W >= 1) & (G >= 1)).sum())}")
    print(f"  maximally even 7-note scales containing C: {int(me.sum())}; their W, G:",
          sorted(set(zip(W[me].tolist(), G[me].tolist()))), "silver triads:", sorted(set(cnt['s'][me].tolist())))
    # scales with both W >= 2 and G >= 2
    both = (W >= 2) & (G >= 2)
    print(f"  scales with W >= 2 and G >= 2: {int(both.sum())};  W >= 3 and G >= 2: {int(((W >= 3) & (G >= 2)).sum())}")
    # all 7-note MOS / Myhill scales of 36-ET and their triads
    print("\n  All 7-note well-formed (MOS) scales of 36-ET, one per generator, chain centred on C:")
    seen = set()
    for g in range(1, 18):
        S = frozenset((g * j) % EDO for j in range(-3, 4))
        if len(S) == 7 and len(set(steps_of(S))) == 2:
            key = min(tuple(sorted(T(S, -t))) for t in S)
            if key in seen:
                continue
            seen.add(key)
            c = triad_census(S)
            print(f"   generator {g:2d} ({g * 100 / 3:6.1f} c): {names(S):34s} steps {sorted(set(steps_of(S)))}  "
                  f"Myhill {myhill(S)}  triads {dict((k, v) for k, v in c.items() if v)}")


def s15_polytonal():
    H("15. Golden planing = three-key polytonality (keys a golden third apart, one per layer)")
    K = [MAJOR, T(MAJOR, 11), T(MAJOR, 22)]
    print("  keys:", ", ".join(f"{name36(t)} major" for t in (0, 11, 22)), " pairwise common tones:",
          [len(K[i] & K[j]) for i, j in ((0, 1), (0, 2), (1, 2))], " union size:", len(K[0] | K[1] | K[2]))
    print("  parallel golden triads on the C major scale (melody in the root):")
    print("   " + "  ".join(f"{name36(x)}g={names(chord(x, 'g'))}" for x in sorted(MAJOR)))
    print("  each is {x, x+11, x+22}: x in C major, x+11 in vE major, x+22 in ^G major (layer theorem)")
    print("\n  Melody in the top voice instead (x = fifth): roots x-22 =", ", ".join(name36(x - 22) + "g" for x in sorted(MAJOR)))
    # canon at the golden third: dyads produced by a stepwise C-major melody against itself delayed one note
    print("\n  Two-voice canon at the golden third (follower = leader + 11, delayed by one note), stepwise leader:")
    for st in (-6, -3, 0, 3, 6):
        print(f"   leader moves {st:+d} -> vertical interval {11 - st:+d} = {(11 - st) * 100 / 3:.1f} c")
    print("\n  Roughness of parallel golden triads vs the diatonic triads they harmonize (close position on each degree):")
    for x in sorted(MAJOR):
        wt = [(r, q) for r, q in key_triads(MAJOR, ("", "m", "dim")) if r == x][0]
        print(f"   {cname(*wt):5s} {roughness(close(chord(*wt), x)):.3f}   {name36(x)}g {roughness(close(chord(x, 'g'), x)):.3f}")


def s16_pedals():
    H("16. Pedals and drones: golden chords over a Western pedal, Western chords over a golden drone")
    print("  Golden triads containing C:", ", ".join(f"{name36(r)}g (circle position {fold(23 * r)})"
                                                    for r in range(EDO) if 0 in chord(r, "g")))
    print("  (23 = 11^-1 mod 36; three consecutive golden-circle chords share each note)")
    print("\n  Roughness with a pedal C3 (absolute -36) under close triads from C4 (harmonic tones):")
    rows = []
    for nm, (r, q) in [("C", (0, "")), ("F/C", (15, "")), ("Am/C", (27, "m")), ("Cg", (0, "g")), ("^Abg/C", (25, "g")),
                       ("vFg/C", (14, "g")), ("vEg (no C)", (11, "g")), ("Fm/C", (15, "m")), ("Ab/C", (24, ""))]:
        v = close(chord(r, q), r)
        v = [x if x >= 0 else x + 36 for x in v]
        rows.append((nm, roughness(v), roughness([-36] + v)))
    for nm, a, b in rows:
        print(f"   {nm:12s} triad {a:.3f}   with C3 pedal {b:.3f}")
    print("\n  Western triads of C major over a Cg drone (drone C3 vE3 ^G3, triad close from C4) vs over a C major drone:")
    dr_g = [-36, -25, -14]
    dr_w = [-36, -24, -15]
    for r, q in key_triads(MAJOR, ("", "m", "dim")):
        v = close(chord(r, q), r)
        print(f"   {cname(r, q):5s} over Cg drone {roughness(dr_g + v):.3f}   over C drone {roughness(dr_w + v):.3f}"
              f"   common tones with Cg {len(chord(r, q) & chord(0, 'g'))}")


def s17_applied():
    H("17. Approach chords: semitone neighbours of Cg (applied chords), and the golden Neapolitan")
    G = (0, 11, 22)
    rows = Counter()
    lst = []
    for mv in product((-3, 0, 3), repeat=3):
        if mv == (0, 0, 0):
            continue
        S = frozenset((g - m) % EDO for g, m in zip(G, mv))        # the chord that moves by mv into Cg
        if len(S) < 3:
            continue
        lab = triad_label(S)
        kind = ("golden" if lab.endswith("g") and "{" not in lab else
                "metallic" if any(lab.endswith(t) for t in ("s", "T13")) and "{" not in lab else
                "western" if "{" not in lab else "other")
        rows[kind] += 1
        lst.append((sum(map(abs, mv)), mv, lab, kind))
    print("  chords X that resolve to Cg with every voice moving by a semitone or holding (26 motion vectors):", dict(rows))
    for d, mv, lab, kind in sorted(lst):
        if kind != "other":
            print(f"   {lab:8s} motion into Cg {mv}  ({kind})")
    print("  Theorem: none is Western (semitone motion keeps each voice on its layer; Cg touches three layers).")
    print("\n  Golden Neapolitan C#g -> Cg: every voice falls a semitone (exact golden apotome 99.27 c each).")
    print("  Golden leading-tone chord vEg -> Cg: B rises to C, vE and ^G hold.")
    # golden seventh resolutions: maj7 -> octave
    print("\n  Intervals in golden triads / sevenths:", sorted({(b - a) % EDO for a in (0, 11, 22, 33) for b in (0, 11, 22, 33) if a != b}),
          " (no 34 or 2: no 'golden augmented sixth' that expands to an octave by contrary sixth-steps)")


def s18_sequences():
    H("18. Sequences: golden giant steps, the golden-third key cycle, the layer-prism sequence")
    print("  Major-third cycle with strict golden passing chords (quality theorem):")
    for a, b in ((0, 24), (24, 12), (12, 0)):
        ch, l1, l2 = evaluate(a, TRI[""], b, TRI[""], False, "")
        g = [l.name for l in (l1, l2) if l.kind in ("golden", "golden_pedal")]
        print(f"   {name36(a)} -> {name36(b)}: strict path {l1.name}, {l2.name};  golden: {g}")
    print("  golden roots on the golden circle (position p with 11 p = r):", [(name36(r), fold(23 * r)) for r in (0, 24, 12)])
    print("\n  Key cycle by golden thirds (tonic + 11 each step):")
    t = 0
    seq = []
    for i in range(7):
        seq.append(name36(t))
        t = (t + 11) % EDO
    print("   " + " -> ".join(seq), "  (three steps = 33 = down a semitone, back on the same layer)")
    d = vl_moves(chord(0, ""), chord(11, ""))
    print(f"   tonic triads C -> vE major: VL {d[0]}, moves {d[1]};  C -> Cg -> vEg -> vE: "
          f"{vl(chord(0, ''), chord(0, 'g'))} + {vl(chord(0, 'g'), chord(11, 'g'))} + {vl(chord(11, 'g'), chord(11, ''))}")
    for s_ in (11, 25):
        dxy, hs = geodesic_hinges(chord(0, ""), chord(s_, ""), 0)
        print(f"   geodesic golden hinges C -> {name36(s_)} major (d = {dxy}): " + ", ".join(name36(r) + "g" for _, r in hs))
    print("\n  Layer-prism sequence: a cadence on C, ^C, vC#, C# (each tonic one sixth-step higher; 3 steps = a semitone)")


SKETCHES = [
    # (id, technique, key, harmony): every string is parsed and expanded by SongMap in section 20
    ("D1", "sixth-step lift (planing modulation)", "C major", "C:1 F:0.5 G7:0.5 C:1 ^C:1 ^F:0.5 ^G7:0.5 ^C:2"),
    ("D2", "third-step lift through its golden midpoint", "C major", "C:1 F:0.5 G7:0.5 C:1 ^Cg:1 vC#:1 vF#:0.5 vG#7:0.5 vC#:2"),
    ("D2b", "third-step lift, engine-chosen midpoint", "C major", "C:1 ~g:1 vC#:2"),
    ("D3", "comma pump: 13 golden-circle steps from Cg to ^Cg", "C major",
     "C:1 Cg:0.5 ^Abg:0.5 vFg:0.5 C#g:0.5 ^Ag:0.5 vF#g:0.5 Dg:0.5 ^Bbg:0.5 vGg:0.5 Ebg:0.5 ^Bg:0.5 vAbg:0.5 Eg:0.5 ^Cg:1 ^C:2"),
    ("D4", "limma pump: 10 forward circle steps from Cg to vC#g", "C major",
     "C:1 Cg:0.5 vEg:0.5 ^Gg:0.5 Bg:0.5 vEbg:0.5 ^F#g:0.5 Bbg:0.5 vDg:0.5 ^Fg:0.5 Ag:0.5 vC#g:1 vC#:2"),
    ("D5", "apotome pump: 3 backward circle steps from Cg to C#g", "C major", "C:1 Cg:1 ^Abg:1 vFg:1 C#g:1 C#:2"),
    ("D6", "projection pivot C major -> ^Eb major (IV = ii via Fg)", "C major", "C:1 Am:1 F:1 Fg:1 ^Fm:1 ^Bb7:1 ^Eb:2"),
    ("D7", "projection pivot C major -> vA major (vi = I via vAg)", "C major", "C:1 F:1 G:1 Am:1 vAg:1 vA:1 vE7:1 vA:2"),
    ("D8", "projection pivot C major -> ^Eb major (V = iii via Gg)", "C major", "C:1 Dm:1 G:1 Gg:1 ^Gm:1 ^Ab:1 ^Bb7:1 ^Eb:1"),
    ("D9", "two golden chords across layers (natural engine)", "C major", "F:1 ~g:0.5 ~g:0.5 ^Em:2"),
    ("D10", "golden hinge vi -> ^I", "C major", "Am:1 ~g:1 ^C:2"),
    ("D11", "golden modal mixture by projection (colour chords)", "C major", "C:1 Fg:1 G7:1 C:1 Am:1 vAg:1 Dm:1 Gg:1 C:2"),
    ("D12", "golden Ionian C D vE F ^G A B", "C major", "F:1 Dm:1 Cg:1 vEg:1 Dm:1 Cg:2"),
    ("D13", "hybrid (W, G) = (3, 2): C ^C D E F vA A", "C major", "F:1 Dm:1 Fg:1 vAg:1 Am:1 Fg:1 F:2"),
    ("D14", "golden planing = three-key polytonality", "C major", "Cg:0.5 Dg:0.5 Eg:0.5 Fg:0.5 Gg:0.5 Ag:0.5 Bg:0.5 Cg:0.5 C:2"),
    ("D15", "golden pedal on C (three circle chords share C)", "C major", "C:1 Cg/C:1 ^Abg/C:1 vFg/C:1 ^Abg/C:1 Cg/C:1 C:2"),
    ("D16", "golden Neapolitan and leading-tone chord", "C golden7", "Cg:1 C#g:1 Cg:1 vEg:1 Cg:1 C:2"),
    ("D17", "golden giant steps (major-third cycle, strict passing)", "C major", "C:1 ~:1 Ab:1 ~:1 E:1 ~:1 C:2"),
    ("D18", "golden-third key cycle through projections", "C major",
     "C:1 Cg:1 vEg:1 vE:1 vEg:1 ^Gg:1 ^G:1 ^Gg:1 Bg:1 B:2"),
    ("D19", "layer-prism sequence (ii-V-I rising by sixth-steps)", "C major",
     "Dm7:0.5 G7:0.5 C:1 ^Dm7:0.5 ^G7:0.5 ^C:1 vEbm7:0.5 vAb7:0.5 vC#:1 Ebm7:0.5 Ab7:0.5 C#:2"),
    ("D20", "F harmonic minor <-> C golden7 by shared projections", "F minor",
     "Fm:1 Db:1 Abaug:1 C:1 Cg:1 C#g:1 vFg:1 ^Abg:1 Cg:1 C:1 Fm:2"),
    ("D21", "golden escalator as passing keys", "C major", "C:1 G7:1 C:1 ~g:0.5 ~g:0.5 D:1 A7:1 D:2"),
]


def s19_roughness():
    H("19. Roughness of the chords used (Sethares model; close position, root C4; measurement)")
    rows = [("C major", (0, 12, 21)), ("C minor", (0, 9, 21)), ("C aug", (0, 12, 24)), ("C dim", (0, 9, 18)),
            ("Cg golden", (0, 11, 22)), ("Cs silver", (0, 10, 20)), ("CT13 bronze", (0, 13, 26)),
            ("C(v3) = C vE G", (0, 11, 21)), ("C(^3) = C ^E G", (0, 13, 21)), ("C(^5) = C E ^G", (0, 12, 22)),
            ("Cmaj7", (0, 12, 21, 33)), ("Cg7", (0, 11, 22, 33))]
    print(f"  {'chord':18s} {'harmonic':>9s} {'golden spectrum':>16s}")
    for n, v in rows:
        print(f"  {n:18s} {roughness(list(v)):9.3f} {roughness(list(v), spectrum='golden'):16.3f}")
    print("  (all golden triads are transpositions of one shape: in this model their roughness differs only by register)")
    print("\n  Register check, Cg on each 12-ET root of the octave from C4 (harmonic):",
          " ".join(f"{name36(r)}:{roughness([r, r + 11, r + 22]):.2f}" for r in range(0, 36, 3)))


def s20_sketches():
    H("20. Audio sketches: parsed and expanded by SongMap (resolved chord symbols)")
    from songmap.arrange.expand import expand
    from songmap.parse import yaml_form
    tpl = ("songmap: 0.2\ntitle: \"t\"\ntempo: 72\nmeter: \"4/4\"\nkey: \"{key}\"\ntuning: 36edo\nseed: 1\n"
           "tail_seconds: 1\ninstruments: {{organ: clean/organ, low: clean/bass}}\nsections:\n"
           "  - {{name: a, bars: {bars:g}, harmony: \"{h}\", parts: {{organ: hold, low: bassline}}}}\nmaster: clean\n")
    from songmap.theory.keys import parse_key
    walk = [0] + [w[1] for w in golden13_walk(0, 13, +1)]
    for t in walk:
        pc, sc = parse_key(name36(t) + " golden13")
        assert frozenset(round((pc + x) * 3) % EDO for x in sc) == T(G13, t)
    print("  keys 'X golden13' parse to the expected sets for every tonic of the comma pump:",
          ", ".join(name36(t) for t in walk))
    for sid, name, key, h in SKETCHES:
        bars = sum(float(t.rsplit(":", 1)[1]) for t in h.split())
        try:
            song = yaml_form.from_raw(yaml_form.load_raw_text(tpl.format(key=key, bars=bars, h=h)))
            arr = expand(song)
            syms = " ".join(s.chord.symbol if s.chord else "N.C." for s in arr.harmony.spans)
            print(f"  OK  {sid:4s} {name}  [key: {key}]\n      {h}\n      -> {syms}"
                  + (f"   warnings: {arr.warnings}" if arr.warnings else ""))
        except Exception as e:  # noqa: BLE001
            print(f"  ERR {sid:4s} {name}\n      {h}\n      -> {type(e).__name__}: {e}")


SECTIONS = [s1_units, s2_comma_pump, s3_key_map, s4_lifts, s5_engine, s6_hinges, s7_projection, s8_projection_pivots,
            s9_bridges, s10_escalator_keys, s11_modes, s12_inflections, s13_centroids, s14_exhaustive_hybrids,
            s15_polytonal, s16_pedals, s17_applied, s18_sequences, s19_roughness, s20_sketches]

if __name__ == "__main__":
    want = {int(a) for a in sys.argv[1:]}
    for i, f in enumerate(SECTIONS, 1):
        if not want or i in want:
            f()
