"""Golden melody across scales: the melodic resources of every golden scale, common-tone subsets between scales,
melodic modulation (chain walks, growing scales, alternation) and melodies that cross between golden and Western keys.
Every table of textbook Chapter 40 and of docs/GOLDEN_BLENDING.md section 16 is printed by this script.

    .venv/Scripts/python reference/golden/melody.py          # all sections
    .venv/Scripts/python reference/golden/melody.py 1 4      # selected sections

Sections:  1 the palette (steps, intervals, chords, tendency tones of every scale)
           2 the golden pentatonic (modes, golden fifths and the chords they imply, Western comparison)
           3 golden7 and the decatonic (generic intervals, degree chords, inversion, sequences, cadences, Western cells)
           4 common-tone subsets (nested scales, golden keys against golden keys, golden against Western, pivot cells)
           5 changing scales (chroma of a chain step, chain walks, the growing scale, alternation, key cycles)
           6 crossing worlds (shared notes, harmonizations of the shared notes, golden inflection by projection)
           7 the chapter's audio: every SongMap example expanded and every note checked against its claimed scale

Conventions as in blending.py: pitch classes are sixth-steps mod 36 (C = 0, ^C = 1, vC# = 2, C# = 3, ...); chain
position j of a pitch class p satisfies 25 j = p (mod 36). Exact cents of a chain interval of j links are
1200 * frac(j log2 phi). Status labels: every count is an exhaustive computation over the finite sets named.
"""
from __future__ import annotations

import sys
from collections import Counter
from itertools import combinations
from math import floor, log2, sqrt
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
import blending as bl  # noqa: E402
from songmap.theory.passing import name36  # noqa: E402

PHI = (1 + sqrt(5)) / 2
G = log2(PHI)
EDO = 36
fold, cd, vl, T = bl.fold, bl.cd, bl.vl, bl.T


def H(t):
    print("\n" + "=" * 100 + f"\n{t}\n" + "=" * 100)


def nm(s):
    return " ".join(name36(x) for x in sorted(s))


def nm_from(s, tonic=0):
    """Names in ascending order starting from the tonic."""
    return " ".join(name36(x) for x in sorted(s, key=lambda x: (x - tonic) % EDO))


def chain_pos(p):
    return fold(13 * p)


def exact_chain_cents(j):
    """Exact pitch-class cents of chain position j above the reference."""
    return 1200 * ((j * G) % 1)


def win(lo, hi):
    return frozenset((25 * j) % EDO for j in range(lo, hi + 1))


def chain_set(js):
    return frozenset((25 * j) % EDO for j in js)


# --------------------------------------------------------------------------- the scales (on C)
PENT_A = chain_set([-2, 0, 2, 4, 6])            # C D vF ^G ^A  (ch36: golden pentatonic "A")
PENT_B = chain_set([-3, -1, 1, 3, 5])           # C# vE vF# ^Ab B (a golden third higher)
CHAIN_SCALES = {                                # name -> chain positions (exact tuning defined)
    "golden pentatonic (C D vF ^G ^A)": [-2, 0, 2, 4, 6],
    "golden3": list(range(-2, 1)),
    "golden4": list(range(-2, 2)),
    "golden7": list(range(-3, 4)),
    "decatonic 35": list(range(-3, 7)),
    "decatonic 53": list(range(-6, 4)),
    "golden10 (SongMap)": list(range(-4, 6)),
    "golden13": list(range(-6, 7)),
}
OTHER_SCALES = {                                # 36-ET only
    "silver13": bl.S13,
    "golden Ionian": frozenset((0, 6, 11, 15, 22, 27, 33)),
    "hybrid (3,2) C ^C D E F vA A": frozenset((0, 1, 6, 12, 15, 26, 27)),
    "hybrid (2,3) C ^C ^C# E F vA A": frozenset((0, 1, 4, 12, 15, 26, 27)),
    "decatonic 44": frozenset((0, 3, 7, 11, 14, 18, 22, 25, 29, 33)),
    "C major pentatonic (Western)": frozenset((0, 6, 12, 21, 27)),
    "C major (Western)": bl.MAJOR,
}
SCALES = {k: chain_set(v) for k, v in CHAIN_SCALES.items()}
SCALES.update(OTHER_SCALES)
D35, D53, G7, G13, G10 = (SCALES["decatonic 35"], SCALES["decatonic 53"], SCALES["golden7"], SCALES["golden13"],
                          SCALES["golden10 (SongMap)"])
G3, G4 = SCALES["golden3"], SCALES["golden4"]

WESTERN = {"major": bl.MAJOR, "nat.minor": bl.NMINOR, "harm.minor": bl.HMINOR, "mel.minor": bl.MMINOR,
           "maj.pent": frozenset((0, 6, 12, 21, 27)), "min.pent": frozenset((0, 9, 15, 21, 30))}

IC_NAME = {1: "sixth-step", 2: "third-step (limma)", 3: "semitone", 4: "", 5: "wide step 5", 6: "whole tone",
           7: "", 8: "small minor third", 9: "minor third", 10: "silver third", 11: "golden third / golden sixth",
           12: "major third", 13: "bronze third", 14: "golden fourth / golden fifth", 15: "fourth / fifth",
           16: "wide fourth", 17: "near-tritone", 18: "tritone"}

TRI4 = {"g7": (0, 11, 22, 33)}


def golden_triads(S):
    return [r for r in range(EDO) if bl.chord(r, "g") <= S]


def golden_sevenths(S):
    return [r for r in range(EDO) if frozenset((r + i) % EDO for i in (0, 11, 22, 33)) <= S]


def tri_list(S, q):
    return [name36(r) + q for r in range(EDO) if bl.chord(r, q) <= S]


def icv(S):
    c = Counter(min((b - a) % EDO, (a - b) % EDO) for a, b in combinations(sorted(S), 2))
    return {k: c.get(k, 0) for k in range(1, 19)}


def steps_list(S, tonic=0):
    a = sorted(S, key=lambda x: (x - tonic) % EDO)
    return [(a[(i + 1) % len(a)] - a[i]) % EDO for i in range(len(a))]


# ===================================================================================================
def s1_palette():
    H("1. The palette: melodic resources of every golden scale on C")
    for name, S in SCALES.items():
        js = CHAIN_SCALES.get(name)
        print(f"\n--- {name}: {nm_from(S)}  ({len(S)} notes)")
        st = steps_list(S)
        print(f"    steps (sixth-steps, from C): {' '.join(map(str, st))};  sizes {sorted(set(st))};"
              f"  largest {max(st)} ({max(st) * 100 / 3:.2f} c 36-ET), smallest {min(st)} ({min(st) * 100 / 3:.2f} c)")
        if js:
            ex = sorted(exact_chain_cents(j) for j in js)
            exs = [((ex[(i + 1) % len(ex)] - ex[i]) % 1200) for i in range(len(ex))]
            print(f"    exact steps (c, from C): {' '.join(f'{x:.2f}' for x in exs)}")
            print(f"    exact step sizes: {sorted({round(x, 2) for x in exs})}")
        v = icv(S)
        print("    interval classes (sixth-steps: pairs): " + ", ".join(f"{k}: {n}" for k, n in v.items() if n))
        west = {k: v[k] for k in (3, 6, 9, 12, 15, 18)}
        print(f"    12-ET-sized interval classes: semitone {west[3]}, whole tone {west[6]}, minor 3rd {west[9]},"
              f" major 3rd {west[12]}, 4th/5th {west[15]}, tritone {west[18]};  golden fifth/fourth (14) {v[14]},"
              f" golden third/sixth (11) {v[11]}")
        gt = golden_triads(S)
        print(f"    golden triads ({len(gt)}): {' '.join(name36(r) + 'g' for r in gt)}")
        gs = golden_sevenths(S)
        print(f"    golden sevenths ({len(gs)}): {' '.join(name36(r) + 'g7' for r in gs)}")
        oth = {q: tri_list(S, q) for q in ("", "m", "aug", "dim", "s", "T13")}
        print("    other triads: " + "; ".join(f"{q or 'maj'}: {' '.join(v)}" for q, v in oth.items() if v) or "none")
        semis = [(a, (a + 3) % EDO) for a in sorted(S) if (a + 3) % EDO in S]
        print(f"    semitone steps (3 sixth-steps; leaning pairs): {', '.join(f'{name36(a)}-{name36(b)}' for a, b in semis)}")
        print(f"    leading tones of C: below (B) {'yes' if 33 in S else 'no'}, above (C#) {'yes' if 3 in S else 'no'};"
              f"  tonic Cg {'yes' if bl.chord(0, 'g') <= S else 'no'}; fifth above C: 21 {'yes' if 21 in S else 'no'},"
              f" golden fifth ^G {'yes' if 22 in S else 'no'}")
        layers = [sorted(x for x in S if x % 3 == L) for L in (0, 1, 2)]
        print("    layer clusters: " + " | ".join(nm(L) for L in layers))
    H("1a. Intervals by chain distance k: in a window of n chain notes the interval k occurs n - k times")
    print(f"{'k':>3s} {'36-ET (ic)':>10s} {'exact pc (c)':>12s} {'inverted':>9s}  nearest Western / note")
    notes = {6: "whole tone (9/8 = 203.91)", 9: "minor third (12-ET 300)", 12: "major third (12-ET 400, 5/4 = 386.31)",
             15: "fourth (4/3 = 498.04)", 1: "golden sixth / golden third", 2: "golden fifth / golden fourth",
             3: "golden apotome (semitone)", 10: "golden limma", 13: "golden comma"}
    for k in range(1, 19):
        ic = min((25 * k) % EDO, (-25 * k) % EDO)
        ex = exact_chain_cents(k)
        print(f"{k:3d} {ic:10d} {ex:12.2f} {1200 - ex:9.2f}  {notes.get(k, '')}")
    for name, js in CHAIN_SCALES.items():
        S = chain_set(js)
        span = max(js) - min(js)
        step = 2 if "pentatonic" in name else 1
        pred = Counter()
        for k in range(step, span + 1, step):
            pred[min((25 * k) % EDO, (-25 * k) % EDO)] += len(js) - k // step
        ok = all(icv(S)[ic] == pred.get(ic, 0) for ic in range(1, 19))
        print(f"    check n - k rule for {name}: {ok}")
    H("1b. Character table (compact)")
    print(f"{'scale':38s} {'n':>2s} {'steps':>8s} {'semi':>4s} {'gold3rds':>8s} {'gold5ths':>8s} {'g-triads':>8s}"
          f" {'g7':>3s} {'Western triads':>14s}")
    for name, S in SCALES.items():
        v = icv(S)
        w = sum(len(tri_list(S, q)) for q in ("", "m"))
        print(f"{name:38s} {len(S):2d} {str(sorted(set(steps_list(S)))):>8s} {v[3]:4d} {v[11]:8d} {v[14]:8d}"
              f" {len(golden_triads(S)):8d} {len(golden_sevenths(S)):3d} {w:14d}")


# ===================================================================================================
def pent_modes():
    """The five modes of the golden pentatonic on C: windows of five chain notes of one parity containing 0."""
    out = []
    for q0 in range(-4, 1):
        js = [2 * q for q in range(q0, q0 + 5)]
        S = chain_set(js)
        b = sum(1 for j in js if j < 0)
        out.append((f"{b}|{4 - b}", js, S))
    return out


def s2_pentatonic():
    H("2. The golden pentatonic: modes, intervals, implied chords, Western comparison")
    print("Exact steps: chain distances 4 (inverted) and 6:", f"{1200 * (3 - 4 * G):.2f}", f"{1200 * (6 * G - 4):.2f}",
          "; chroma (large - small) =", f"{1200 * (3 - 4 * G) - 1200 * (6 * G - 4):.2f} c (= golden limma 69.10)")
    print("\nModes on C (b|a = golden-fifth-chain notes below|above the tonic in chain order):")
    for name, js, S in sorted(pent_modes(), key=lambda m: -sum(m[2])):
        st = steps_list(S)
        ex = sorted(exact_chain_cents(j) for j in js)
        print(f"  {name}: {nm_from(S):22s} steps {' '.join(map(str, st)):12s} brightness {sum(S):3d}  chain {js}"
              f"  exact {' '.join(f'{x:.2f}' for x in ex)}  golden fifth on C: {'yes' if 22 in S else 'no'},"
              f" golden fourth (C-vF): {'yes' if 14 in S else 'no'}")
    print("\nGeneric intervals of the golden pentatonic (sizes in sixth-steps):", bl.generic_sizes(PENT_A))
    print("Generic intervals of the Western major pentatonic C D E G A:", bl.generic_sizes(WESTERN["maj.pent"]))
    print("Semitones in the golden pentatonic:", icv(PENT_A)[3], "(anhemitonic);  icv:",
          {k: n for k, n in icv(PENT_A).items() if n})
    print("Western major pentatonic icv:", {k: n for k, n in icv(WESTERN['maj.pent']).items() if n})
    print("Golden triads inside the golden pentatonic:", golden_triads(PENT_A), "(none: a golden triad spans chain"
          " positions r, r-1, r-2 of both parities)")
    print("\nGolden fifths of pentatonic A and the unique golden triad each implies (third from pentatonic B):")
    for a in sorted(PENT_A):
        b = (a + 22) % EDO
        if b in PENT_A:
            r = a
            third = (a + 11) % EDO
            print(f"  {name36(a)}-{name36(b)}: {name36(r)}g, missing third {name36(third)} in pentatonic B: {third in PENT_B}")
    print("Each note of pentatonic A as the THIRD of a golden triad whose root and fifth lie in B:")
    for x in sorted(PENT_A):
        r = (x - 11) % EDO
        print(f"  {name36(x)} = third of {name36(r)}g = {nm(bl.chord(r, 'g'))}; root, fifth in B:"
              f" {r in PENT_B and (r + 22) % EDO in PENT_B}")
    print("\nGolden triads containing two notes of pentatonic A:",
          [name36(r) + "g" for r in range(EDO) if len(bl.chord(r, "g") & PENT_A) >= 2])
    print("Golden triads containing >= 1 note of A:",
          len([r for r in range(EDO) if bl.chord(r, "g") & PENT_A]))
    print("\nWestern pentatonic C D E G A contains triads:", tri_list(WESTERN["maj.pent"], ""), tri_list(WESTERN["maj.pent"], "m"))
    print("\nTranspositions of pentatonic A: common tones by chain shift c (T_s with c(s) = c):")
    for c in range(-10, 11):
        s = (25 * c) % EDO
        print(f"  c={c:3d} ({name36(s):4s}): {len(PENT_A & T(PENT_A, s))}", end="")
        if c % 5 == 4:
            print()
    print()
    print("Pentatonic A and B: disjoint", not (PENT_A & PENT_B), "; union = 35:", (PENT_A | PENT_B) == D35)
    # golden pentatonics inside other scales
    pents = {T(PENT_A, s) for s in range(EDO)}
    for nmx, S in (("golden7", G7), ("decatonic 35", D35), ("decatonic 53", D53), ("golden13", G13),
                   ("silver13", bl.S13), ("C major", bl.MAJOR)):
        inside = [P for P in pents if P <= S]
        print(f"  golden pentatonics inside {nmx}: {len(inside)}: " + "; ".join(nm_from(P, min(P)) for P in inside))
    # all well-formed 5-subsets of golden13
    wf = [frozenset(c) for c in combinations(sorted(G13), 5) if bl.is_mos(frozenset(c))]
    print(f"  MOS 5-note subsets of golden13: {len(wf)}: the golden pentatonics plus "
          + "; ".join(nm(P) for P in wf if P not in pents) + " (a semitone cluster)")
    # max common tones of the golden pentatonic with Western scales
    for fam, W in WESTERN.items():
        best = max(len(PENT_A & T(W, t)) for t in range(EDO))
        arg = [name36(t) for t in range(EDO) if len(PENT_A & T(W, t)) == best]
        print(f"  pentatonic A vs {fam}: max common {best} on {' '.join(arg)}; with C {fam}: {nm(PENT_A & W)}")


# ===================================================================================================
def degree_chords(S, span):
    """Chords on scale degrees k, k+span, k+2*span (and +3*span) of S sorted from C."""
    a = sorted(S)
    n = len(a)
    out = []
    for k in range(n):
        tri = frozenset(a[(k + i * span) % n] for i in range(3))
        sev = frozenset(a[(k + i * span) % n] for i in range(4))
        out.append((a[k], tri, sev))
    return out


def s3_seven_ten():
    H("3. golden7 and the decatonic: generic intervals, degree chords, inversion, sequences, cadences")
    for nmx, S in (("golden7", G7), ("decatonic 35", D35), ("decatonic 53", D53), ("golden13", G13)):
        print(f"\n--- {nmx}: {nm_from(S)}")
        a = sorted(S)
        n = len(a)
        for k in range(1, n):
            c = Counter((a[(i + k) % n] - a[i]) % EDO for i in range(n))
            print(f"    generic {k}: " + ", ".join(f"{s} ({s * 100 / 3:.2f} c) x{m}" for s, m in sorted(c.items())))
    print("\nDecatonic 35: degree chords on degrees 1-4-7(-10) (skip two notes):")
    for root, tri, sev in degree_chords(D35, 3):
        lab = bl.triad_label(tri)
        g7 = frozenset((root + i) % EDO for i in (0, 11, 22, 33)) == sev
        print(f"    on {name36(root):4s}: {nm_from(tri, root):16s} -> {lab:10s} seventh golden: {g7}")
    print("golden7: degree chords on degrees 1-3-5 (skip one):")
    for root, tri, sev in degree_chords(G7, 2):
        print(f"    on {name36(root):4s}: {nm_from(tri, root):16s} -> {bl.triad_label(tri)}")
    # inversion
    print("\nInversion about C (x -> -x):")
    for nmx, S in (("golden pentatonic A", PENT_A), ("golden7", G7), ("35", D35), ("53", D53), ("golden13", G13)):
        inv = frozenset((-x) % EDO for x in S)
        same = [k for k, V in (("pentA", PENT_A), ("golden7", G7), ("35", D35), ("53", D53), ("golden13", G13)) if V == inv]
        print(f"    {nmx}: inverted = {nm(inv)}  equals {same}")
    print("Inversion axes x -> a - x that map each scale to itself:")
    for nmx, S in (("golden pentatonic A", PENT_A), ("golden7", G7), ("35", D35), ("53", D53), ("golden13", G13)):
        ax = [a for a in range(EDO) if frozenset((a - x) % EDO for x in S) == S]
        print(f"    {nmx}: a = {ax}  (axis at a/2 sixth-steps: " + ", ".join(f"{a / 2:g}" for a in ax) + ")")
    # sequences: real transposition by one chain step
    print("\nReal transposition by one chain step (T25, up a golden sixth; T11 = down a chain step, up a golden third):")
    for nmx, S in (("golden pentatonic A (T22 = golden fifth)", PENT_A), ("golden7", G7), ("35", D35), ("golden13", G13)):
        for t in ((22, 14) if "pent" in nmx else (25, 11)):
            S2 = T(S, t)
            out, inn = S - S2, S2 - S
            print(f"    {nmx} T{t}: common {len(S & S2)}, out {nm(out)}, in {nm(inn)}, change "
                  f"{[fold(i - o) for o in out for i in inn]}")
    # cadential cells into C
    print("\nApproaches to C in each scale (melodic interval into C; golden triads holding the approach note; VL to Cg):")
    for nmx, S in (("golden7", G7), ("35", D35), ("53", D53)):
        print(f"  {nmx}:")
        for x in sorted(S, key=lambda x: cd(x, 0)):
            if x == 0:
                continue
            chords = [r for r in golden_triads(S) if x in bl.chord(r, "g")]
            desc = ", ".join(f"{name36(r)}g (VL {vl(bl.chord(r, 'g'), bl.chord(0, 'g'))})" for r in chords)
            print(f"    {name36(x):4s} -> C ({fold(-x):+d}): {desc}")
    # Western cells inside the decatonic
    print("\nWestern (12-ET) melodic cells: layer clusters (all mutual intervals multiples of 3):")
    for nmx, S in (("golden7", G7), ("35", D35), ("53", D53), ("golden13", G13), ("pentatonic A", PENT_A)):
        cl = [sorted(x for x in S if x % 3 == L) for L in (0, 1, 2)]
        print(f"    {nmx}: " + " | ".join(nm_from(c, c[0]) if c else "-" for c in cl))
    # three-note Western cells (12-ET pitch sets of C major type) embeddable in 35
    print("Three-note cells of C major (any three notes within a fourth, transposed anywhere) that fit in 35:")
    cells = set()
    M = sorted(bl.MAJOR)
    for c3 in combinations(M + [m + 36 for m in M], 3):
        if c3[2] - c3[0] <= 15:
            cells.add(tuple(x - c3[0] for x in c3))
    fit = [c for c in sorted(cells) if any(all((t + x) % EDO in D35 for x in c) for t in range(EDO))]
    print("    ", [tuple(x // 3 for x in c) for c in fit], "(semitones)")
    print("    and not:", [tuple(x // 3 for x in c) for c in sorted(cells) if c not in fit])


# ===================================================================================================
def common_tones_table(scales):
    names = list(scales)
    print(f"{'':28s}" + "".join(f"{n[:9]:>10s}" for n in names))
    for a in names:
        print(f"{a[:28]:28s}" + "".join(f"{len(scales[a] & scales[b]):10d}" for b in names))


def s4_common():
    H("4. Common-tone subsets")
    nest = {"golden3": G3, "golden4": G4, "golden7": G7, "pentatonic A": PENT_A, "pentatonic B": PENT_B,
            "35": D35, "53": D53, "golden10": G10, "golden13": G13, "silver13": bl.S13}
    print("Inclusions among the golden scales on C:")
    for a, A in nest.items():
        sup = [b for b, B in nest.items() if a != b and A <= B]
        print(f"    {a:14s} inside: {', '.join(sup) or '-'}")
    print("\nCommon tones between scales on C:")
    common_tones_table(nest)
    print("\n35 n 53 =", nm(D35 & D53), "= golden7:", (D35 & D53) == G7, ";  35 u 53 = golden13:", (D35 | D53) == G13)
    print("35 -> 53 on C, the notes that differ:", nm(D35 - D53), "->", nm(D53 - D35),
          [fold(b - a) for a, b in zip(sorted(D35 - D53), sorted(D53 - D35))])
    print("golden13 minus 35 =", nm(G13 - D35), " (a golden triad:", bl.triad_label(G13 - D35), ")")
    print("golden13 minus 53 =", nm(G13 - D53), " (", bl.triad_label(G13 - D53), ")")
    print("golden13 minus golden7 =", nm(G13 - G7))
    # windows: common tones = n - |c|
    print("\nTheorem check: a chain window of n notes and its transposition by s share max(0, n - |c(s)|) notes:")
    for n_, S in ((3, G3), (4, G4), (7, G7), (10, D35), (13, G13)):
        ok = all(len(S & T(S, s)) == max(0, n_ - abs(fold(13 * s))) for s in range(EDO))
        print(f"    n = {n_}: {ok}")
    okp = all(len(PENT_A & T(PENT_A, s)) == (0 if fold(13 * s) % 2 else max(0, 5 - abs(fold(13 * s)) // 2))
              for s in range(EDO))
    print(f"    golden pentatonic: 0 if c odd, max(0, 5 - |c|/2) if c even: {okp}")
    print("\ngolden13 on C against golden13 on named neighbours (common tones, kept notes):")
    rel = [("chain step up (^Ab)", 25), ("chain step down = golden third (vE)", 11), ("golden fifth (^G)", 22),
           ("golden fifth below (vF)", 14), ("apotome up (C#)", 3), ("apotome down (B)", 33), ("limma up (vC#)", 2),
           ("limma down (^B)", 34), ("sixth-step up (^C)", 1), ("sixth-step down (vC)", 35), ("whole tone (D)", 6),
           ("12-ET fifth (G)", 21), ("12-ET major third (E)", 12)]
    for lab, s in rel:
        for nmx, S in (("golden13", G13), ("golden7", G7), ("35", D35), ("pentA", PENT_A)):
            k = S & T(S, s)
            print(f"    {lab:36s} {nmx:9s} c={fold(13 * s):4d}: {len(k):2d}  {nm(k) if len(k) <= 4 else ''}"
                  f"{'  triad ' + bl.triad_label(k) if len(k) == 3 else ''}")
    # golden scales vs Western scales
    print("\nGolden scales on C against Western scales on C (common notes):")
    for nmx, S in (("pentatonic A", PENT_A), ("pentatonic B", PENT_B), ("golden7", G7), ("35", D35), ("53", D53),
                   ("golden10", G10), ("golden13", G13), ("silver13", bl.S13)):
        print(f"    {nmx:13s} " + "; ".join(f"{fam}: {nm(S & W) or '-'}" for fam, W in WESTERN.items()))
    print("\nMaximum common notes with any Western scale of each family on any of the 36 tonics:")
    for nmx, S in (("pentatonic A", PENT_A), ("golden7", G7), ("35", D35), ("golden13", G13), ("silver13", bl.S13)):
        row = []
        for fam, W in WESTERN.items():
            vals = {t: len(S & T(W, t)) for t in range(EDO)}
            mx = max(vals.values())
            arg = [name36(t) for t, v in vals.items() if v == mx]
            row.append(f"{fam} {mx} ({' '.join(arg[:6])}{' ...' if len(arg) > 6 else ''})")
        print(f"    {nmx:13s} " + "; ".join(row))
    print("\nThe 4-note intersections of golden13 on C with harmonic / melodic minor keys:")
    for fam in ("harm.minor", "mel.minor"):
        for t in range(EDO):
            k = G13 & T(WESTERN[fam], t)
            if len(k) >= 4:
                print(f"    {name36(t)} {fam}: {nm(k)}")
    # pivot cells
    print("\nPivot cells: the common subset of each pair, ranked by size, then by content")
    pairs = []
    allsc = {"golden7 C": G7, "35 C": D35, "53 C": D53, "golden13 C": G13, "pentA C": PENT_A, "pentB C": PENT_B}
    for t, tn in ((25, "^Ab"), (11, "vE"), (22, "^G"), (14, "vF"), (3, "C#"), (2, "vC#"), (1, "^C")):
        for base in ("golden7", "35", "golden13", "pentA"):
            allsc[f"{base} {tn}"] = T(allsc[f"{base} C"], t)
    W = {"C major": bl.MAJOR, "C minor": bl.NMINOR, "C harm.minor": bl.HMINOR, "A minor": T(bl.NMINOR, 27),
         "G major": T(bl.MAJOR, 21), "F major": T(bl.MAJOR, 15)}
    names_ = list(allsc)
    for i, a in enumerate(names_):
        for b in names_[i + 1:]:
            pairs.append((a, b, allsc[a] & allsc[b]))
        for w, WS in W.items():
            pairs.append((a, w, allsc[a] & WS))

    def content(k):
        g = len(golden_triads(k))
        return (len(k), g, icv(k)[11] + icv(k)[14], icv(k)[3])
    seen = set()
    shown = Counter()
    for a, b, k in sorted(pairs, key=lambda p: content(p[2]), reverse=True):
        if shown[len(k)] >= 6:
            continue
        if not k or len(k) > 12:
            continue
        key = (a.split()[0], b.split()[0], len(k))
        if key in seen:
            continue
        seen.add(key)
        shown[len(k)] += 1
        if len(k) <= 9:
            print(f"    {a:13s} & {b:13s}: {len(k):2d}  {nm(k):40s} golden triads {len(golden_triads(k))},"
                  f" golden 3rds/5ths {icv(k)[11]}/{icv(k)[14]}, semitones {icv(k)[3]}")
    # a golden triad as pivot: how many keys of each scale contain Cg
    print("\nKeys (tonics) of each scale type that contain Cg (the golden triad as a pivot cell):")
    for nmx, S in (("golden4", G4), ("golden7", G7), ("decatonic (any mode, as sets)", D35), ("golden13", G13),
                   ("silver13", bl.S13)):
        ks = [t for t in range(EDO) if bl.chord(0, "g") <= T(S, t)]
        print(f"    {nmx}: {len(ks)}: {' '.join(name36(t) for t in ks)}")
    ks = [(fam, name36(t)) for fam, Wf in WESTERN.items() for t in range(EDO) if len(bl.chord(0, 'g') & T(Wf, t)) >= 2]
    print("    Western scales holding two notes of Cg:", len(ks), ks[:12])


# ===================================================================================================
def s5_changing():
    H("5. Changing scales")
    print("Chroma: one step of the generator moves one note (window of chain positions):")
    gens = [("golden pentatonic (gen. golden fifth)", [-2, 0, 2, 4, 6], 2), ("golden3", list(range(-2, 1)), 1),
            ("golden4", list(range(-2, 2)), 1), ("golden7", list(range(-3, 4)), 1), ("golden10", list(range(-3, 7)), 1),
            ("golden13", list(range(-6, 7)), 1), ("golden23", list(range(-11, 12)), 1)]
    for nmx, js, g in gens:
        S, S2 = chain_set(js), chain_set([j + g for j in js])
        out, inn = list(S - S2), list(S2 - S)
        o, i = out[0], inn[0]
        span = (max(js) + g) - min(js)
        ex = 1200 * ((span * G + 0.5) % 1 - 0.5)
        print(f"    {nmx:38s} one step up the chain: {name36(o)} -> {name36(i)}  {fold(i - o):+d} sixth-steps,"
              f" exact {ex:+.2f} c (chain span {span})")
    # walks
    print("\nWalks up the chain from C (each step: note out -> note in, change):")
    for nmx, js, g, n in (("golden7", list(range(-3, 4)), 1, 7), ("35", list(range(-3, 7)), 1, 10),
                          ("pentatonic A", [-2, 0, 2, 4, 6], 2, 5)):
        cur = js
        line = []
        for k in range(n):
            nxt = [j + g for j in cur]
            o = (set(chain_set(cur)) - set(chain_set(nxt))).pop()
            i = (set(chain_set(nxt)) - set(chain_set(cur))).pop()
            ton = (25 * g * (k + 1)) % EDO
            line.append(f"{name36(ton)}: {name36(o)}->{name36(i)}")
            cur = nxt
        print(f"    {nmx}: " + ";  ".join(line))
        print(f"      common with C after the walk: {len(chain_set(js) & chain_set(cur))}")
    print("    golden13 (comma pump): see GOLDEN_BLENDING section 3.1 (13 steps, each +1)")
    # walks down = golden-third key cycle
    print("\nThe golden-third key cycle (each key a golden third = one chain step DOWN):")
    for nmx, js in (("golden7", list(range(-3, 4))), ("35", list(range(-3, 7))), ("golden13", list(range(-6, 7)))):
        cur = js
        line = []
        for k in range(6):
            nxt = [j - 1 for j in cur]
            o = (set(chain_set(cur)) - set(chain_set(nxt))).pop()
            i = (set(chain_set(nxt)) - set(chain_set(cur))).pop()
            line.append(f"{name36((11 * (k + 1)) % EDO)}: {name36(o)}->{name36(i)} ({fold(i - o):+d})")
            cur = nxt
        print(f"    {nmx}: " + ";  ".join(line))
    print("    3 golden thirds = 33 = -3: B, a 12-ET semitone below C; 36 steps visit all 36 keys")
    # growing scale
    print("\nThe growing scale: chain windows around the tonic triad, one note at a time:")
    order = [0, -1, -2, 1, -3, 2, 3, 4, 5, 6, -4, -5, -6]
    cur = []
    for j in order:
        cur.append(j)
        S = chain_set(cur)
        if len(S) < 2:
            continue
        st = steps_list(S)
        exs = sorted(exact_chain_cents(x) for x in cur)
        exst = sorted({round((exs[(i + 1) % len(exs)] - exs[i]) % 1200, 2) for i in range(len(exs))})
        tag = "MOS" if len(set(st)) == 2 else f"{len(set(st))} sizes"
        print(f"    +{name36((25 * j) % EDO):4s} n={len(S):2d} [{min(cur)},{max(cur)}] {nm_from(S):50s} steps {sorted(set(st))}"
              f" exact {exst} {tag}  golden triads {len(golden_triads(S))}")
    print("  well-formed windows of every size n = 2..13 (some placement):",
          [n for n in range(2, 14) if len(set(steps_list(win(0, n - 1)))) == 2])
    print("  in exact golden tuning, windows with two step sizes:",
          [n for n in range(2, 14) if len(_exact_steps([j * G for j in range(n)])) == 2])
    print("  Western mirror (exact Pythagorean fifths): windows with two step sizes:",
          [n for n in range(2, 13) if len(_exact_steps([j * log2(1.5) for j in range(n)])) == 2])
    # alternation 35 <-> 53, pentatonics
    print("\nAlternation on one tonic:")
    print(f"    35 -> 53: {nm(D35 - D53)} -> {nm(D53 - D35)} (each +2 = a golden limma); common {len(D35 & D53)} = golden7")
    MA, MI = bl.MAJOR, bl.NMINOR
    print(f"    Western mirror C major -> C minor: {nm(MA - MI)} -> {nm(MI - MA)} (each -3 = a semitone); common {len(MA & MI)}")
    print(f"    pentatonic A <-> B: common {len(PENT_A & PENT_B)}, union = 35: {(PENT_A | PENT_B) == D35}")
    print("    Western mirror: C major pentatonic and its golden-third-like partner? C D E G A vs the black keys:",
          len(WESTERN["maj.pent"] & T(WESTERN["maj.pent"], 18)), "common with F# pentatonic; union with C major = 12 notes")
    # limma key change of golden13
    print("\nLimma key change golden13 C -> vC# (up) and C -> ^B (down):")
    for s in (2, 34):
        S2 = T(G13, s)
        keep = G13 & S2
        print(f"    to {name36(s)}: kept {nm(keep)} = {bl.triad_label(keep)}; leaving {nm(G13 - S2)} (= 35? {(G13 - S2) == D35},"
              f" = 53? {(G13 - S2) == D53}); arriving {nm(S2 - G13)}")
        print(f"      moves of the leaving notes to the arriving ones: "
              f"{sorted(Counter(min((fold(b - a) for b in S2 - G13), key=abs) for a in G13 - S2).items())}")
    # Western mirror of growing: 2 3 5 7 12
    print("\nWestern unfolding (chain of pure fifths F C G D ..., exact cents of the step sizes):")
    for n in range(2, 13):
        st = _exact_steps([j * log2(1.5) for j in range(-1, n - 1)])
        print(f"    n={n:2d} steps {st}{'  (two sizes)' if len(st) == 2 else ''}")


def _exact_steps(octs):
    """Distinct step sizes (cents, 2 decimals) of the pitch classes given in octaves."""
    a = sorted(1200 * (x % 1) for x in octs)
    n = len(a)
    return sorted({round((a[(i + 1) % n] - a[i]) % 1200, 2) for i in range(n)})


# ===================================================================================================
def proj_major(r):
    return bl.chord(r, "g")


def s6_crossing():
    H("6. Crossing worlds")
    print("Western major keys (36 tonics) sharing notes with C golden7, C 35, C pentatonic A:")
    for nmx, S in (("golden7", G7), ("35", D35), ("53", D53), ("pentatonic A", PENT_A), ("golden13", G13)):
        rows = []
        for t in range(EDO):
            k = S & T(bl.MAJOR, t)
            if len(k) >= 2:
                rows.append(f"{name36(t)} ({nm(k)})")
        print(f"    {nmx}: {len(rows)} keys share >= 2: " + ", ".join(rows))
    print("\nTriads containing B and C (harmonizing the shared cadence B-C):")
    for x in (33, 0):
        w = [bl.cname(r, q) for q in ("", "m") for r in range(0, EDO, 3) if x in bl.chord(r, q)]
        g = [name36(r) + "g" for r in range(EDO) if x in bl.chord(r, "g")]
        print(f"    {name36(x)}: Western {w}; golden {g}")
    print("Projection pi of C major's triads and the melody notes they bend:")
    for r, q in ((0, ""), (6, "m"), (12, "m"), (15, ""), (21, ""), (27, "m")):
        X = bl.chord(r, q)
        P = bl.projection(r, q) if hasattr(bl, "projection") else None
        Pg = [g for g in range(EDO) if vl(X, bl.chord(g, "g")) == 2]
        for g in Pg:
            Y = bl.chord(g, "g")
            d, mv, p = bl.vl_moves(X, Y)
            bends = [f"{name36(a)}->{name36(b)}" for a, b in zip(sorted(X), p) if a != b]
            print(f"    {bl.cname(r, q):4s} -> {name36(g)}g: keeps {nm(X & Y)}, bends {', '.join(bends)}")
    # golden inflection of a melody: allowed set per chord
    print("\nThe 'inflected scale' under each colour chord (C major with the projection's bends):")
    for r, q in ((0, ""), (15, ""), (21, ""), (27, "m"), (12, "m"), (6, "m")):
        X = bl.chord(r, q)
        g = [g for g in range(EDO) if vl(X, bl.chord(g, "g")) == 2][0]
        Y = bl.chord(g, "g")
        S = (bl.MAJOR - X) | Y
        print(f"    under {name36(g)}g (pi of {bl.cname(r, q)}): {nm_from(S)}  golden triads {[name36(x) + 'g' for x in golden_triads(S)]}"
              f"  Western triads {tri_list(S, '') + tri_list(S, 'm')}")
    # which golden7 keys contain both C and B and the golden scales containing {B, C, D}
    print("\nGolden keys that contain the shared cell {B, C}:")
    for nmx, S in (("golden7", G7), ("decatonic", D35), ("golden13", G13), ("pentatonic", PENT_A)):
        ks = [name36(t) for t in range(EDO) if {0, 33} <= T(S, t)]
        print(f"    {nmx}: {ks}")
    print("Golden keys that contain {B, C, D} (golden13 n C major):")
    for nmx, S in (("decatonic", D35), ("golden13", G13)):
        ks = [name36(t) for t in range(EDO) if {0, 33, 6} <= T(S, t)]
        print(f"    {nmx}: {ks}")
    # Western keys containing {B, C}
    print("Western major keys containing {B, C}:", [name36(t) for t in range(EDO) if {0, 33} <= T(bl.MAJOR, t)])
    print("Western major keys containing {B, C, D}:", [name36(t) for t in range(EDO) if {0, 33, 6} <= T(bl.MAJOR, t)])


# ===================================================================================================
# 7. the chapter's audio: claims per bar range -> (melody scale, harmony scale); None = not claimed
MAJ, MPENT, GION = bl.MAJOR, WESTERN["maj.pent"], OTHER_SCALES["golden Ionian"]


def inflected(r):
    """C major with the major triad on r replaced by its golden projection G_r (E->vE, G->^G under Cg, ...)."""
    return (MAJ - bl.chord(r, "")) | bl.chord(r, "g")


G13_vCs = T(G13, 2)
G7_vE = T(G7, 11)
AUDIO_CLAIMS = {   # file: [(first bar, last bar, label, melody set, harmony set)]
    "palette": [(1, 2, "golden3", G3, G3), (3, 4, "golden4", G4, G4), (5, 6, "pentatonic A", PENT_A, D35),
                (7, 8, "golden7", G7, G7), (9, 10, "35", D35, D35), (11, 12, "golden13", G13, G13),
                (13, 13, "C major", MAJ, MAJ)],
    "pentatonic_chain": [(1, 7, "pentatonic A (harmony in 35)", PENT_A, D35), (8, 8, "C major", MAJ, MAJ)],
    "pentatonic_mirror": [(1, 4, "Western major pentatonic", MPENT, MAJ), (5, 8, "pentatonic A", PENT_A, D35),
                          (9, 9, "C major", MAJ, MAJ)],
    "golden7_tendency": [(1, 4, "golden7", G7, G7), (5, 5, "golden7 melody, Cg -> C", G7, None)],
    "golden7_mirror": [(1, 5, "golden7", G7, G7), (6, 6, "C major", MAJ, MAJ)],
    "decatonic_sequence": [(1, 8, "35", D35, D35), (9, 9, "C major", MAJ, MAJ)],
    "decatonic_alternation": [(1, 4, "35 (harmony golden7)", D35, G7), (5, 8, "53 (harmony golden7)", D53, G7),
                              (9, 9, "C major", MAJ, MAJ)],
    "pivot_subset": [(1, 2, "C golden7 n vE golden7 / harmony C golden7", G7 & G7_vE, G7),
                     (3, 4, "C golden7 n vE golden7 / harmony vE golden7", G7 & G7_vE, G7_vE),
                     (5, 5, "common notes / C golden7", G7 & G7_vE, G7), (6, 6, "C major", MAJ, MAJ)],
    "chain_walk": [(1, 1, "C golden7", G7, G7), (2, 2, "^Ab golden7", T(G7, 25), T(G7, 25)),
                   (3, 3, "vF golden7", T(G7, 14), T(G7, 14)), (4, 4, "C# golden7", T(G7, 3), T(G7, 3)),
                   (5, 5, "vF golden7", T(G7, 14), T(G7, 14)), (6, 6, "^Ab golden7", T(G7, 25), T(G7, 25)),
                   (7, 7, "C golden7", G7, G7), (8, 8, "C, Cg -> C", G7, None)],
    "growing_scale": [(1, 2, "golden3", G3, G3), (3, 3, "golden4", G4, G4), (4, 5, "golden7", G7, G7),
                      (6, 7, "35", D35, D35), (8, 10, "golden13", G13, G13), (11, 11, "C major", MAJ, MAJ)],
    "limma_pivot": [(1, 2, "C golden13", G13, G13), (3, 3, "pivot vEbg", G13 & G13_vCs, G13 & G13_vCs),
                    (4, 5, "vC# golden13", G13_vCs, G13_vCs), (6, 6, "pivot vEbg", G13 & G13_vCs, G13 & G13_vCs),
                    (7, 8, "C golden13", G13, G13), (9, 9, "C major", MAJ, MAJ)],
    "cross_inflection": [(1, 4, "C major", MAJ, MAJ), (5, 5, "C major bent by pi(C)", inflected(0), inflected(0)),
                         (6, 6, "bent by pi(F)", inflected(15), inflected(15)),
                         (7, 7, "bent by pi(G)", inflected(21), inflected(21)),
                         (8, 8, "bent by pi(C)", inflected(0), inflected(0)), (9, 9, "C major", MAJ, MAJ)],
    "cross_hinge": [(1, 2, "C major", MAJ, MAJ), (3, 4, "golden7", G7, G7), (5, 6, "C major", MAJ, MAJ),
                    (7, 8, "golden7", G7, G7), (9, 9, "C major", MAJ, MAJ)],
    "worked_pentatonic": [(1, 12, "pentatonic A (harmony in 35)", PENT_A, D35), (13, 13, "C major", MAJ, MAJ)],
    "worked_golden7": [(1, 8, "golden7", G7, G7), (9, 9, "C major", MAJ, MAJ)],
    "worked_decatonic": [(1, 8, "35", D35, D35), (9, 12, "53", D53, D53), (13, 13, "C major", MAJ, MAJ)],
    "worked_crossing": [(1, 4, "C major", MAJ, MAJ), (5, 8, "golden7", G7, G7), (9, 12, "35", D35, D35),
                        (13, 15, "golden Ionian", GION, GION), (16, 16, "golden Ionian, Cg -> C", GION, None)],
}


def s7_audio():
    H("7. Audio check: every note of every SongMap example of Chapter 40 against its claimed scale")
    from songmap.arrange.expand import expand
    from songmap.parse import yaml_form
    adir = ROOT / "textbook" / "audio" / "ch40"
    files = sorted(p.name.replace(".songmap.yaml", "") for p in adir.glob("*.songmap.yaml"))
    print("files:", len(files), "claims:", len(AUDIO_CLAIMS), "unclaimed:", [f for f in files if f not in AUDIO_CLAIMS])
    total_bad = 0
    for f in files:
        song = yaml_form.load(str(adir / f"{f}.songmap.yaml"))
        arr = expand(song)
        bars = sum(s.bars for s in song.sections) if hasattr(song, "sections") else None
        tempo = getattr(song, "tempo", None)
        claims = AUDIO_CLAIMS.get(f, [])
        bad = []
        mel_roles = [r for r in arr.parts if r not in ("pad", "low")]
        print(f"\n--- {f}: {bars} bars at {tempo} bpm = {bars * 240 / tempo:.1f} s (+ tail); melody parts {mel_roles}")
        for b0, b1, lab, mset, hset in claims:
            mel = []
            for r in mel_roles:
                for e in arr.parts[r]:
                    bar = int(e.beat // 4) + 1
                    if b0 <= bar <= b1:
                        for p in e.pitches:
                            st = round(p * 3)
                            mel.append(st)
                            if st % EDO not in mset:
                                bad.append((f, bar, r, name36(st)))
            har = []
            for r in ("pad", "low"):
                for e in arr.parts.get(r, []):
                    bar = int(e.beat // 4) + 1
                    if b0 <= bar <= b1:
                        har += [round(p * 3) % EDO for p in e.pitches]
                        if hset is not None:
                            bad += [(f, bar, r, name36(round(p * 3))) for p in e.pitches if round(p * 3) % EDO not in hset]
            print(f"    bars {b0:2d}-{b1:2d} {lab:46s} melody {nm(frozenset(m % EDO for m in mel)):42s}"
                  f" harmony {nm(frozenset(har))}")
        # the melody spelled bar by bar
        for r in mel_roles:
            line, cur = [], 0
            for e in sorted(arr.parts[r], key=lambda e: e.beat):
                bar = int(e.beat // 4) + 1
                if bar != cur:
                    line.append("|")
                    cur = bar
                line.append(" ".join(name36(round(p * 3)) + str(round(p * 3) // 36 - 1) for p in e.pitches))
            print(f"    {r}: " + " ".join(line[1:]))
        if f.startswith("worked_") or f in ("pentatonic_chain", "golden7_mirror", "decatonic_sequence"):
            pads = sorted(arr.parts["pad"], key=lambda e: e.beat)
            for r in mel_roles:
                rows, cur = [], None
                for e in sorted(arr.parts[r], key=lambda e: e.beat):
                    pad = [p for p in pads if p.beat <= e.beat + 1e-9][-1]
                    pcs = frozenset(round(p * 3) % EDO for p in pad.pitches)
                    lab = bl.triad_label(pcs)
                    x = round(e.pitches[0] * 3) % EDO
                    role = "nct"
                    if pcs in bl.ALL_TRIADS:
                        root, q = bl.ALL_TRIADS[pcs][0]
                        role = {0: "R"}.get((x - root) % EDO) or ("3" if (x - root) % EDO in (9, 11, 12) else
                                                                  "5" if (x - root) % EDO in (21, 22) else "nct")
                    if lab != cur:
                        rows.append(f"[{lab}]")
                        cur = lab
                    rows.append(f"{name36(x)}:{role}")
                print(f"    annotated {r}: " + " ".join(rows))
        total_bad += len(bad)
        for b in bad:
            print("    NOT IN CLAIMED SCALE:", b)
    print(f"\nTotal notes outside their claimed scale: {total_bad}")
    # pivot_subset: the harmony really changes key
    print("pivot_subset: C#g in vE golden7?", bl.chord(3, "g") <= G7_vE, "; ^Gg in C golden7?", bl.chord(22, "g") <= G7)
    print("limma_pivot: Bbg, vC#g in C golden13?", bl.chord(30, "g") <= G13, bl.chord(2, "g") <= G13,
          "; Bg in vC# golden13?", bl.chord(33, "g") <= G13_vCs)


SECTIONS = [s1_palette, s2_pentatonic, s3_seven_ten, s4_common, s5_changing, s6_crossing, s7_audio]

if __name__ == "__main__":
    want = {int(a) for a in sys.argv[1:]}
    for i, f in enumerate(SECTIONS, 1):
        if not want or i in want:
            f()
