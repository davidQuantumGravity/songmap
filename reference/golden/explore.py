"""Golden-ratio harmony in 36-ET: reproducible numbers behind docs/GOLDEN_HARMONY.md.

    python reference/golden/explore.py

Sections:
  1. interval approximations (exact golden vs 36-ET)
  2. why 36: continued fraction of log2(phi), the identity phi^3 ~ 4 * 2^(1/12)
  3. the golden chain, its MOS scales (2, 3, 4, 7, 10, 13, 23, 36 notes; scales printed as chains j = 0..n-1, not centred on C) and the three 12-ET layers
  4. the golden triad as the centroid of major / minor / augmented
  5. voice-leading resolutions of the golden triad (in sixth-steps)
  6. stability: Sethares roughness (harmonic vs golden spectra) and harmonic entropy
"""
from itertools import permutations
from math import gcd, log2, sqrt

import numpy as np

PHI = (1 + sqrt(5)) / 2
EDO = 36
STEP = 1200 / EDO            # 33.333 cents = a sixth-tone (1/3 semitone)
GEN = 25                     # golden sixth in 36-ET steps
NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def cents(r):
    return 1200 * log2(r)


def name36(st: int) -> str:
    """Ups-and-downs name: ^ = up one sixth-tone, v = down one sixth-tone."""
    q, r = divmod(st % EDO, 3)
    return NAMES[q] if r == 0 else ("^" + NAMES[q] if r == 1 else "v" + NAMES[(q + 1) % 12])


def section(t):
    print(f"\n== {t} " + "=" * (70 - len(t)))


def main():
    section("1. golden intervals: exact vs 36-ET")
    rows = [("golden sixth  phi", PHI, 25), ("golden third  2/phi", 2 / PHI, 11),
            ("golden fifth  4/phi^2", 4 / PHI ** 2, 22), ("golden seventh 8/phi^3", 8 / PHI ** 3, 33)]
    for n, r, s in rows:
        print(f"  {n:24s} {cents(r):8.3f} c   36-ET {s:2d} steps = {s * STEP:8.3f} c   error {s * STEP - cents(r):+.2f} c")

    section("2. why 36-ET")
    x, a = log2(PHI), []
    y = x
    for _ in range(7):
        a.append(int(y))
        y = 1 / (y - int(y))
    h, k = [0, 1], [1, 0]
    for ai in a:
        h.append(ai * h[-1] + h[-2])
        k.append(ai * k[-1] + k[-2])
    print("  log2(phi) =", a, "...  convergents:", list(zip(h[2:], k[2:])))
    print("  -> MOS scale sizes of the golden chain: 2, 3, 4, 7, 10, 13, 23, 36 (36 = where phi is ~exact: 25/36)")
    print(f"  phi^3 / 4 = {PHI ** 3 / 4:.5f}  vs  2^(1/12) = {2 ** (1 / 12):.5f}"
          f"  ({cents(PHI ** 3 / 4):.2f} c): three golden sixths = two octaves + ~one semitone")

    section("3. golden chain, MOS scales, three 12-ET layers")
    for size in (3, 10, 13):
        ch = sorted((GEN * j) % EDO for j in range(size))
        steps = [(ch[(i + 1) % size] - ch[i]) % EDO for i in range(size)]
        print(f"  golden{size:<2d}: {' '.join(name36(s) for s in ch)}")
        print(f"            steps {steps}  layers {[s % 3 for s in ch]}")
    ch13 = [(GEN * j) % EDO for j in range(13)]
    n_t = len({tuple(sorted((s + t) % EDO for s in ch13)) for t in range(EDO)})
    print(f"  distinct transpositions of golden13 in 36-ET: {n_t}")
    ex = sorted((j * cents(PHI)) % 1200 for j in range(13))
    print("  exact golden13 step sizes:", sorted({round((ex[(i + 1) % 13] - ex[i]) % 1200, 2) for i in range(13)}), "cents")
    print("  layer of chain note j = j mod 3 (since 25 = 1 mod 3); same-layer neighbours j, j+3 differ by a semitone")

    section("4. the golden triad")
    maj, mnr, aug = (0, 12, 21), (0, 9, 21), (0, 12, 24)
    cen = tuple(sum(v) / 3 for v in zip(maj, mnr, aug))
    print(f"  centroid of C, Cm, Caug (36-ET steps) = {cen}  ->  C vE ^G = (0, 11, 22)")
    print("  intervals 11 + 11 + 14: equal stacked thirds, mirror-symmetric (like dim and aug triads)")
    print("  golden seventh (0, 11, 22, 33) =", " ".join(name36(s) for s in (0, 11, 22, 33)), "= Cmaj7 with v3 and ^5")

    section("5. resolutions of Cg (voice-leading distance in sixth-steps)")
    Q = {"": (0, 12, 21), "m": (0, 9, 21), "aug": (0, 12, 24), "dim": (0, 9, 18), "sus4": (0, 15, 21), "sus2": (0, 6, 21)}

    def vl(a, b):
        best = None
        for p in permutations(b):
            mv = [((y - x + 18) % EDO) - 18 for x, y in zip(a, p)]
            d = sum(map(abs, mv))
            if best is None or d < best[0]:
                best = (d, mv)
        return best

    g = (0, 11, 22)
    res = sorted((vl(g, tuple((r + i) % EDO for i in iv)) + (NAMES[r // 3] + q,))
                 for r in range(0, EDO, 3) for q, iv in Q.items())
    for d, mv, n in res[:8]:
        print(f"  Cg -> {n:6s} distance {d}  moves (C, vE, ^G) = {mv}")

    section("6. stability")

    def diss(fr, am):
        d = 0.0
        for i in range(len(fr)):
            for j in range(i + 1, len(fr)):
                f1, f2 = sorted((fr[i], fr[j]))
                s = 0.24 / (0.0207 * f1 + 18.96)
                d += min(am[i], am[j]) * (np.exp(-3.5 * s * (f2 - f1)) - np.exp(-5.75 * s * (f2 - f1)))
        return d

    def chord_diss(cs, parts, amps, f0=261.63):
        fr, am = [], []
        for c in cs:
            for p, a in zip(parts, amps):
                fr.append(f0 * 2 ** (c / 1200) * p)
                am.append(a)
        return diss(fr, am)

    harm = list(range(1, 9))
    gold = sorted({2 ** m * PHI ** n for m in range(4) for n in range(4) if 2 ** m * PHI ** n < 9})
    chords = {"major": [0, 400, 700], "minor": [0, 300, 700], "sus4": [0, 500, 700], "aug": [0, 400, 800],
              "dim": [0, 300, 600], "golden": [0, cents(2 / PHI), cents(4 / PHI ** 2)],
              "maj7": [0, 400, 700, 1100], "golden7": [0, cents(2 / PHI), cents(4 / PHI ** 2), cents(8 / PHI ** 3)]}
    print("  Sethares roughness (lower = smoother). Harmonic spectrum = partials 1..8;")
    print("  golden spectrum = partials 2^m * phi^n:", [round(p, 3) for p in gold])
    print(f"  {'chord':9s} {'harmonic':>9s} {'golden':>8s}")
    for n, cs in chords.items():
        print(f"  {n:9s} {chord_diss(cs, harm, [0.88 ** i for i in range(8)]):9.3f}"
              f" {chord_diss(cs, gold, [0.88 ** i for i in range(len(gold))]):8.3f}")

    R, W = [], []
    for d in range(1, 120):
        for n in range(d, 4 * d + 1):
            if gcd(n, d) == 1 and n * d <= 12000:
                R.append(cents(n / d))
                W.append(1 / sqrt(n * d))
    R, W = np.array(R), np.array(W)

    def he(c, s=17):
        p = W * np.exp(-(c - R) ** 2 / (2 * s * s))
        p /= p.sum()
        p = p[p > 1e-15]
        return float(-(p * np.log(p)).sum())

    H = np.array([he(c) for c in range(1201)])
    print("\n  Harmonic entropy of dyads (Erlich model, s = 17 c; percentile over 0-1200 c, higher = more ambiguous)")
    for n, c in [("P5", 700), ("M3", 400), ("m3", 300), ("golden third", cents(2 / PHI)), ("neutral third", 350),
                 ("golden fifth", cents(4 / PHI ** 2)), ("golden sixth", cents(PHI)), ("m6", 800), ("M6", 900)]:
        print(f"  {n:14s} {c:7.1f} c   HE {he(c):.3f}   percentile {100 * (H < he(c)).mean():3.0f}%")


def combination_tones(f0=110.0):
    section("7. combination tones of the chain voicing 1 : phi : phi^2 : phi^3")
    for label, ratios in [("exact phi", [PHI ** k for k in range(4)]),
                          ("36-ET (25-step chain)", [2 ** (25 * k / 36) for k in range(4)]),
                          ("close voicing C vE ^G B (exact)", [1, 2 / PHI, 4 / PHI ** 2, 8 / PHI ** 3])]:
        fr = [f0 * r for r in ratios]
        pairs = [(a, b) for i, a in enumerate(fr) for b in fr[i + 1:]]          # a < b
        # the two combination tones the ear actually produces: f2 - f1 and 2 f1 - f2
        tones = sorted({b - a for a, b in pairs} | {2 * a - b for a, b in pairs if 2 * a > b})
        # nearest golden-chain frequency f0 * 2^m * phi^n, and the beat it makes against it
        chain = [f0 * 2 ** m * PHI ** n for m in range(-3, 4) for n in range(-4, 5)]
        worst = max(min(abs(t - c) for c in chain) for t in tones)
        print(f"  {label:32s} {len(tones):2d} combination tones (f2-f1, 2f1-f2); worst miss vs a chain pitch {worst:6.3f} Hz")
    print("  exact phi powers: f(phi^n) - f(phi^(n-1)) = f(phi^(n-2)), so the combination tones are")
    print("  chord/chain tones (a self-similar cascade). 36-ET detunes them into slow beats (< 1 Hz at 110 Hz).")


def beat_spectrum(f0=110.0, partials=6):
    section("8. beat spectrum: the beats of a golden chord form a golden chord")

    def beats(ratios):
        F = [(f0 * r * n, i) for i, r in enumerate(ratios) for n in range(1, partials + 1)]
        out = set()
        for a in range(len(F)):
            for b in range(a + 1, len(F)):
                if F[a][1] != F[b][1]:
                    d = abs(F[a][0] - F[b][0])
                    if 0.05 < d < 15:
                        out.add(round(d, 3))
        return sorted(out)

    for name, r in [("Cg close (exact)", [1, 2 / PHI, 4 / PHI ** 2]),
                    ("Cg7 close (exact)", [1, 2 / PHI, 4 / PHI ** 2, 8 / PHI ** 3]),
                    ("chain 1:phi:phi^2", [1, PHI, PHI ** 2]),
                    ("C major 12-ET", [1, 2 ** (4 / 12), 2 ** (7 / 12)]),
                    ("C major just 4:5:6", [1, 1.25, 1.5])]:
        b = beats(r)
        rel = " ".join(f"{x / b[0]:.3f}" for x in b) if b else "-"
        print(f"  {name:20s} beats <15 Hz at f0={f0:g}: {b}   relative: {rel}")
    print("  The base beat is f0 * (13 - 8 phi) = f0 * phi^-6 (Fibonacci approximant 13/8 of phi).")
    print("  Cg : f0 phi^-6 x (1, 2/phi), plus 2 f0 phi^-6 from a doubled harmonic pair (root h6 vs fifth h4)")
    print("  Cg7 (1 : 2/phi : 4/phi^2 : 8/phi^3): f0 phi^-6 x (1, 2/phi, 4/phi^2) = the golden TRIAD in rhythm,")
    print("       plus 2 f0 phi^-6 = the golden seventh against the root's octave, since 8/phi^3 = 2 - 2 phi^-6.")
    print("       No beat occurs at the golden seventh's own ratio (8/phi^3 x f0 phi^-6 = 11.58 Hz at 110 Hz).")
    print("  With 8 partials the Cg7 beats below 15 Hz (at 110 Hz) are still exactly these four rates.")
    print("  Beat rates scale linearly with f0, so register tunes the beat ladder (f0 = 55 Hz halves them).")


if __name__ == "__main__":
    main()
    combination_tones()
    beat_spectrum()
