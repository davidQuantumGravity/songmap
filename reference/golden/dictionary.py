"""Golden progression dictionary (diatonic = home, golden = passing).

Four-part writing (SATB):
  * upper three voices = the three distinct chord tones of each chord (for sevenths:
    3rd, 5th, 7th), joined by the smoothest stepwise lines (each line moves <= a whole step);
  * the bass sounds the root. If the roots are a step apart the bass is a line like the
    others; otherwise it holds through the passing chords and moves on the arrival
    (like a dominant pedal under a cadential six-four).

Passing paths X -> P1 -> P2 -> Y (all quantities in 36-ET sixth-steps):
  strict      every line moves uniformly: half step = 1+1+1, whole step = 2+2+2 (unique path)
  natural     half steps stay 1+1+1; a whole step may split unevenly (1+2+3, 3+3+0, ...);
              every line still moves monotonically and never more than a semitone per chord
Forms:  D-G-D  (one golden passing chord)   D-G-G-D  (two different golden passing chords)

    python reference/golden/dictionary.py   ->  docs/GOLDEN_PROGRESSIONS.md, docs/golden_progressions.json
"""
from __future__ import annotations

import json
import os
from itertools import permutations, product

EDO = 36
NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
ROMAN = ["I", "bII", "II", "bIII", "III", "IV", "#IV", "V", "bVI", "VI", "bVII", "VII"]
HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.normpath(os.path.join(HERE, "..", "..", "docs"))

TYPES = {"g": (0, 11, 22), "g7": (0, 11, 22, 33), "silver": (0, 10, 20), "T13": (0, 13, 26),
         "": (0, 12, 21), "m": (0, 9, 21), "dim": (0, 9, 18), "aug": (0, 12, 24),
         "sus4": (0, 15, 21), "sus2": (0, 6, 21), "7": (0, 12, 21, 30), "maj7": (0, 12, 21, 33),
         "m7": (0, 9, 21, 30), "m7b5": (0, 9, 18, 30), "dim7": (0, 9, 18, 27), "mmaj7": (0, 9, 21, 33),
         "6": (0, 12, 21, 27), "m6": (0, 9, 21, 27)}
GOLDEN_T = {"g", "g7"}
DEG = {0: "1", 6: "2", 9: "3", 10: "3", 11: "3", 12: "3", 13: "3", 15: "4", 18: "5", 20: "5", 21: "5",
       22: "5", 24: "5", 26: "5", 27: "6", 30: "7", 33: "7"}


def name36(st):
    q, r = divmod(st % EDO, 3)
    return NAMES[q] if r == 0 else ("^" + NAMES[q] if r == 1 else "v" + NAMES[(q + 1) % 12])


def roman36(st):
    q, r = divmod(st % EDO, 3)
    return ROMAN[q] if r == 0 else ("^" + ROMAN[q] if r == 1 else "v" + ROMAN[(q + 1) % 12])


def note36(st):
    q, r = divmod(st, 3)
    if r == 2:
        q += 1
    return f"{name36(st)}{q // 12 - 1}"


def pcset(v):
    return frozenset(x % EDO for x in v)


# ---------------------------------------------------------------------------
# classification
# ---------------------------------------------------------------------------
def classify(voices):
    """voices[0] = bass. Returns (name, roman, kind) with kind in
    golden | golden_pedal | equal_third | western | altered."""
    bass = voices[0] % EDO
    s = pcset(voices)
    up = pcset(voices[1:])

    def sl(r):
        return ("", "") if r == bass else ("/" + name36(bass), "/" + roman36(bass))

    for t, iv in TYPES.items():
        for r in s:
            if pcset(r + i for i in iv) == s:
                kind = "golden" if t in GOLDEN_T else "equal_third" if t in ("silver", "T13") else                     ("western" if r % 3 == 0 else "planing")
                a, b = sl(r)
                return name36(r) + t + a, roman36(r) + t + b, kind
    for t in GOLDEN_T:
        for r in up:
            if pcset(r + i for i in TYPES[t]) == up:
                return f"{name36(r)}{t}/{name36(bass)}", f"{roman36(r)}{t}/{roman36(bass)}", "golden_pedal"
    best = None                                     # nearest micro-altered chord, root exact
    for t, iv in TYPES.items():
        if t in ("silver", "T13"):
            continue
        for r in s:
            devs, ok = {}, True
            for p in s:
                cand = [(abs(((p - (r + i)) % EDO + 18) % EDO - 18), i, ((p - (r + i)) % EDO + 18) % EDO - 18) for i in iv]
                c = min(cand)
                if c[0] > 2 or c[1] in devs:
                    ok = False
                    break
                devs[c[1]] = c[2]
            if not ok or any(i not in devs and i not in (18, 21, 22, 24) for i in iv):
                continue
            cost = sum(abs(d) for d in devs.values()) - (0.3 if t in GOLDEN_T else 0)
            if best is None or cost < best[0]:
                best = (cost, r, t, devs)
    if best:
        _, r, t, devs = best
        alt = ",".join(("^" * d if d > 0 else "v" * -d) + DEG[i] for i, d in sorted(devs.items()) if d)
        a, b = sl(r)
        return f"{name36(r)}{t}({alt}){a}", f"{roman36(r)}{t}({alt}){b}", "altered"
    return "{" + " ".join(name36(p) for p in sorted(s)) + "}", "?", "altered"


RANK = {"golden": 0, "golden_pedal": 1, "equal_third": 2, "western": 3, "altered": 4}

# ---------------------------------------------------------------------------
# chords in C major (+ common chromatic), as (root semitone, quality)
# ---------------------------------------------------------------------------
CHORDS = {
    "I": (0, ""), "ii": (2, "m"), "iii": (4, "m"), "IV": (5, ""), "V": (7, ""), "vi": (9, "m"), "vii°": (11, "dim"),
    "Imaj7": (0, "maj7"), "ii7": (2, "m7"), "iii7": (4, "m7"), "IVmaj7": (5, "maj7"), "V7": (7, "7"),
    "vi7": (9, "m7"), "viiø7": (11, "m7b5"),
    "i": (0, "m"), "iv": (5, "m"), "bIII": (3, ""), "bVI": (8, ""), "bVII": (10, ""), "bII": (1, ""),
    "II": (2, ""), "III": (4, ""), "VI": (9, ""), "V7/V": (2, "7"), "V7/vi": (4, "7"), "V7/IV": (0, "7"),
    "iiø7": (2, "m7b5"), "bVImaj7": (8, "maj7"), "I+": (0, "aug"), "vii°7": (11, "dim7"),
}


def cname(k):
    r, q = CHORDS[k]
    return NAMES[r] + q


def upper_options(k):
    """Candidate upper-voice pitch-class sets with a small penalty:
    triads: complete (0) or incomplete with doubled root (1); sevenths: 3-5-7 (0) or 3-7-root (0.5)."""
    r, q = CHORDS[k]
    iv = TYPES[q]
    pc = [(3 * r + i) % EDO for i in iv]
    if len(iv) == 4:
        return 3 * r, [(pc[1:], 0.0), ([pc[1], pc[3], pc[0]], 0.5)]
    return 3 * r, [(pc, 0.0), ([pc[0], pc[0], pc[1]], 1.0)]


def schedules(D, natural):
    if D == 0:
        return [(0, 0, 0)]
    if abs(D) > 6:                       # a leap: hold, then move on the arrival chord
        return [(0, 0, D)]
    u = D // 3
    if not natural or abs(D) == 3:
        return [(u, u, u)]
    sg = 1 if D > 0 else -1
    out = []
    for a, b in product(range(4), repeat=2):
        c = abs(D) - a - b
        if 0 <= c <= 3:
            out.append((sg * a, sg * b, sg * c))
    return out


BASS_LO, BASS_HI = 3 * 40, 3 * 55        # E2 .. G3
UP_LO = 3 * 55                           # upper voices start in [G3, G4)


def placed_starts(k):
    root, opts = upper_options(k)
    bass = BASS_LO + (root - BASS_LO) % EDO
    return [((bass, *[UP_LO + (p - UP_LO) % EDO for p in u]), pen) for u, pen in opts]


def near(a, b):
    return ((b - a + 18) % EDO) - 18


SEVENTHS = ("7", "maj7", "m7", "m7b5", "dim7")


def evaluate(xk, yk, natural, start=None):
    """Best X -> P1 -> P2 -> Y path. start = fixed absolute X chord (bass, v1, v2, v3)."""
    starts = [(start, 0.0)] if start else placed_starts(xk)
    yroot, yopts = upper_options(yk)
    best = None
    for X0, xpen in starts:
        rd = near(X0[0], yroot)
        if abs(rd) > 6:                                   # bass leap: keep the bass in range
            alt = rd - EDO if rd > 0 else rd + EDO
            if not BASS_LO <= X0[0] + rd <= BASS_HI and BASS_LO <= X0[0] + alt <= BASS_HI:
                rd = alt
        systems = []
        for yu, ypen in yopts:
            for perm in set(permutations(yu)):
                systems.append(([near(x, y) for x, y in zip(X0[1:], perm)], xpen + ypen))
        step = [sy for sy in systems if all(abs(d) <= 6 for d in sy[0])]
        if step:
            systems = step
        else:
            m = min(sum(map(abs, sy[0])) for sy in systems)
            systems = [sy for sy in systems if sum(map(abs, sy[0])) == m]
        bass_scheds = schedules(rd, natural) if abs(rd) <= 6 else [(0, 0, rd)]
        sev = (3 * CHORDS[xk][0] + TYPES[CHORDS[xk][1]][3]) % EDO if CHORDS[xk][1] in SEVENTHS else None
        for D, pen in systems:
            for bsch in bass_scheds:
                for sch in product(*[schedules(d, natural) for d in D]):
                    pos = list(X0)
                    chords = [tuple(pos)]
                    for st in range(3):
                        pos = [pos[0] + bsch[st]] + [pos[1 + i] + sch[i][st] for i in range(3)]
                        chords.append(tuple(pos))
                    l1, l2 = classify(chords[1]), classify(chords[2])
                    motion = sum(abs(d) for d in D) / 3 + pen
                    uneven = sum(max(x) - min(x) for x in sch)
                    golden = (l1[2] in ("golden", "golden_pedal")) + (l2[2] in ("golden", "golden_pedal"))
                    exact = (l1[2] == "golden") + (l2[2] == "golden")
                    distinct = pcset(chords[1]) != pcset(chords[2])
                    par = sum(1 for i in range(1, 4)
                              if chords[3][i] - chords[0][i] == chords[3][0] - chords[0][0] != 0
                              and (chords[0][i] - chords[0][0]) % EDO in (0, 21))
                    sev_up = 0 if sev is None else sum(
                        1 for i in range(1, 4) if chords[0][i] % EDO == sev and chords[3][i] > chords[0][i])
                    key = (-golden, -exact, -int(distinct), par, motion + 0.5 * sev_up, uneven)
                    if best is None or key < best[0]:
                        best = (key, chords, l1, l2)
    _, chords, l1, l2 = best
    if start is None:
        idx = [0] + sorted(range(1, 4), key=lambda i: chords[0][i])      # T < A < S by starting pitch
        chords = [tuple(c[i] for i in idx) for c in chords]
    return dict(chords=chords, l1=l1, l2=l2)


def lines(ch):
    """Four text lines S A T B for a list of 36-ET chords."""
    out = []
    for v, lab in ((3, "S"), (2, "A"), (1, "T"), (0, "B")):
        out.append(f"{lab}: " + "  ".join(f"{note36(c[v]):6s}" for c in ch))
    return out


def stars(r):
    return "★" * ((r["l1"][2] == "golden") + (r["l2"][2] == "golden")) + "☆" * ((r["l1"][2] == "golden_pedal") + (r["l2"][2] == "golden_pedal"))


COMMON = [("V", "I"), ("V7", "I"), ("IV", "I"), ("I", "IV"), ("I", "V"), ("ii", "V"), ("ii7", "V7"), ("IV", "V"),
          ("V", "vi"), ("V7", "vi"), ("I", "vi"), ("vi", "IV"), ("vi", "ii"), ("ii", "vi"), ("iii", "vi"),
          ("I", "ii"), ("IV", "ii"), ("vii°", "I"), ("V7", "Imaj7"), ("I", "bVI"), ("bVI", "I"), ("bVII", "I"),
          ("iv", "I"), ("IV", "iv"), ("V7/V", "V7"), ("bII", "I"), ("V7/vi", "vi"), ("IVmaj7", "V7"),
          ("iii7", "vi7"), ("vi7", "ii7"), ("Imaj7", "IVmaj7"), ("I", "iii"), ("iii", "IV")]

PROGRESSIONS = {
    "Authentic cadence V–I": ["V", "I"],
    "Full cadence I–IV–V–I": ["I", "IV", "V", "I"],
    "Jazz ii–V–I": ["ii7", "V7", "Imaj7"],
    "Pop axis I–V–vi–IV": ["I", "V", "vi", "IV"],
    "Doo-wop I–vi–IV–V": ["I", "vi", "IV", "V"],
    "Sensitive vi–IV–I–V": ["vi", "IV", "I", "V"],
    "Circle of fifths iii–vi–ii–V–I": ["iii7", "vi7", "ii7", "V7", "Imaj7"],
    "Royal road IVmaj7–V7–iii7–vi": ["IVmaj7", "V7", "iii7", "vi"],
    "Mixolydian I–bVII–IV–I": ["I", "bVII", "IV", "I"],
    "Minor plagal I–IV–iv–I": ["I", "IV", "iv", "I"],
    "Chromatic mediant I–bVI–I": ["I", "bVI", "I"],
    "Pachelbel": ["I", "V", "vi", "iii", "IV", "I", "IV", "V"],
    # new progressions built from the theory (GOLDEN_THEORY.md Part III)
    "Golden cadence ii–V–I": ["ii", "V", "I"],
    "Golden jazz cadence ii7–V–Imaj7": ["ii7", "V", "Imaj7"],
    "Golden staircase I–ii–iii–IV–V–vi": ["I", "ii", "iii", "IV", "V", "vi"],
    "Golden major-third cycle I–III–bVI–I": ["I", "III", "bVI", "I"],
    "Golden Andalusian vi–V–IV–III": ["vi", "V", "IV", "III"],
    "Golden plagal-authentic I–IV–I–V–I": ["I", "IV", "I", "V", "I"],
    "Golden mediant return I–bVI–IV–I": ["I", "bVI", "IV", "I"],
}


def progression(ks, natural):
    """Voice-led chain: each transition starts from the previous arrival chord, unless
    re-voicing that diatonic chord (marked 'revoice') gives more exact golden passing chords."""
    def exact(r):
        return (r["l1"][2] == "golden") + (r["l2"][2] == "golden")

    first = evaluate(ks[0], ks[1], natural)
    seq, labels = list(first["chords"]), [first["l1"], first["l2"], None]
    for a, b in zip(ks[1:], ks[2:]):
        cont = evaluate(a, b, natural, start=seq[-1])
        fresh = evaluate(a, b, natural)
        if exact(fresh) > exact(cont):
            # keep the bass register continuous; the upper voices re-voice on the repeated chord
            seq.append(fresh["chords"][0])
            labels.append("revoice")
            r = fresh
        else:
            r = cont
        seq += r["chords"][1:]
        labels += [r["l1"], r["l2"], None]
    return seq, labels


def main():
    keys = list(CHORDS)
    strict = {(a, b): evaluate(a, b, False) for a in keys for b in keys if a != b}
    natural = {(a, b): evaluate(a, b, True) for a in keys for b in keys if a != b}

    L = ["# Golden progression dictionary", "",
         "Generated by `python reference/golden/dictionary.py` (do not edit by hand). Theory, proofs and context: "
         "[GOLDEN_THEORY.md](GOLDEN_THEORY.md).", "",
         "**Principle:** diatonic = home, golden = passing. Key of C major.",
         "",
         "**Voicing.**",
         "- Four voices (SATB).",
         "- The upper voices are the three chord tones (for sevenths: 3rd, 5th, 7th), joined by the smoothest stepwise lines.",
         "- The bass sounds the root. It moves by step like the other voices when the roots are a step apart. Otherwise it holds through the passing chords and moves on the arrival, like a dominant pedal under a cadential six-four.",
         "",
         "**Two kinds of path.**",
         "- **Strict path:** every half step is split into 1 + 1 + 1 sixth-steps and every whole step into 2 + 2 + 2, so the path between a fixed voicing pair is *unique*.",
         "- **Natural path:** half steps stay 1 + 1 + 1, but a whole step may split unevenly (for example 1 + 2 + 3). Every voice still moves in one direction and never more than a semitone per chord.",
         "",
         "**Names.**",
         "- `^` = up one sixth-step (+33 c), `v` = down one.",
         "- `g` = golden triad, `g7` = golden seventh.",
         "- `silver` = {0, 10, 20}; `T13` = {0, 13, 26} (equal-third triads).",
         "- `Xg/Y` = golden chord over pedal Y.",
         "- An off-grid ordinary chord such as `vF#` is *planing*: a Western chord shifted onto another layer.",
         "- Parenthesised alterations name the micro-altered tones.",
         "",
         "**Rating.** ★ = an exact golden passing chord; ☆ = golden over a pedal.", ""]

    for title, (a, b) in (("V → I", ("V", "I")), ("V7 → I", ("V7", "I"))):
        r, n = strict[(a, b)], natural[(a, b)]
        L += [f"## Worked example: {title}", "", "Strict (unique) path:", "", "```",
              *lines(r["chords"]), "```", "",
              f"- P1 = **{r['l1'][0]}** ({r['l1'][1]}): {r['l1'][2]}",
              f"- P2 = **{r['l2'][0]}** ({r['l2'][1]}): {r['l2'][2]}", ""]
        if (n["l1"][0], n["l2"][0]) != (r["l1"][0], r["l2"][0]):
            L += ["Natural path:", "", "```", *lines(n["chords"]), "```", "",
                  f"- P1 = **{n['l1'][0]}**, P2 = **{n['l2'][0]}**", ""]

    L += ["## The common transitions", "",
          "| Transition | Chords | Strict P1 · P2 | ★ | Natural P1 · P2 | ★ |", "|---|---|---|---|---|---|"]
    for a, b in COMMON:
        r, n = strict[(a, b)], natural[(a, b)]
        L.append(f"| {a} → {b} | {cname(a)} → {cname(b)} | {r['l1'][0]} · {r['l2'][0]} | {stars(r)} | "
                 f"{n['l1'][0]} · {n['l2'][0]} | {stars(n)} |")
    L += ["", "Voice lines (natural path):", ""]
    for a, b in COMMON:
        n = natural[(a, b)]
        L += [f"<details><summary>{a} → {b}: {cname(a)} – {n['l1'][0]} – {n['l2'][0]} – {cname(b)}</summary>", "",
              "```", *lines(n["chords"]), "```", "</details>", ""]

    # 3- and 4-chord forms
    def gg(r):
        return r["l1"][2] == "golden" and r["l2"][2] == "golden" and r["l1"][0].split("/")[0] != r["l2"][0].split("/")[0]

    four = {k: v for k, v in natural.items() if gg(v)}
    three = {}
    for k in strict:
        for src in (strict[k], natural[k]):
            for lab in (src["l1"], src["l2"]):
                if lab[2] == "golden":
                    three.setdefault(k, lab)
                    break
            if k in three:
                break
    L += ["## Four-chord forms: diatonic – golden – golden – diatonic", "",
          f"{len(four)} ordered pairs have two *different* exact golden passing chords on a natural path.", "",
          "| Form | Chords |", "|---|---|"]
    for (a, b), v in sorted(four.items(), key=lambda kv: (keys.index(kv[0][0]), keys.index(kv[0][1]))):
        L.append(f"| {a} – {v['l1'][1]} – {v['l2'][1]} – {b} | {cname(a)} – {v['l1'][0]} – {v['l2'][0]} – {cname(b)} |")
    L += ["", "## Three-chord forms: diatonic – golden – diatonic", "",
          f"{len(three)} ordered pairs have at least one exact golden passing chord. Use it alone: X – G – Y.", "",
          "| Form | Chords |", "|---|---|"]
    for (a, b), lab in sorted(three.items(), key=lambda kv: (keys.index(kv[0][0]), keys.index(kv[0][1]))):
        L.append(f"| {a} – {lab[1]} – {b} | {cname(a)} – {lab[0]} – {cname(b)} |")

    L += ["", "## Golden versions of common progressions (natural paths)", ""]
    pj = {}
    for title, ks in PROGRESSIONS.items():
        seq, labs = progression(ks, True)
        rom, nm = [ks[0]], [cname(ks[0])]
        it = iter(ks[1:])
        for lab in labs:
            if lab == "revoice":
                rom.append("(re-voice)")
                nm.append("(re-voice)")
                continue
            if lab is None:
                k = next(it)
                rom.append(k)
                nm.append(cname(k))
            else:
                rom.append(lab[1])
                nm.append(lab[0])
        ng = sum(1 for l in labs if isinstance(l, tuple) and l[2] == "golden")
        L += [f"### {title}", "", f"`{' – '.join(rom)}`", "", f"{' – '.join(nm)}  ({ng} exact golden passing chords)",
              "", "```", *lines(seq), "```", ""]
        pj[title] = {"roman": rom, "chords": nm, "steps36": [list(c) for c in seq]}

    L += ["## Full dictionary", "",
          f"All {len(strict)} ordered pairs over {len(keys)} chords (C major: diatonic triads and sevenths, plus "
          "i, iv, bIII, bVI, bVII, bII, II, III, VI, V7/V, V7/vi, V7/IV, iiø7, bVImaj7, I+, vii°7).", "",
          "| Transition | Chords | Strict P1 · P2 | ★ | Natural P1 · P2 | ★ |", "|---|---|---|---|---|---|"]
    for (a, b) in strict:
        r, n = strict[(a, b)], natural[(a, b)]
        L.append(f"| {a} → {b} | {cname(a)} → {cname(b)} | {r['l1'][0]} · {r['l2'][0]} | {stars(r)} | "
                 f"{n['l1'][0]} · {n['l2'][0]} | {stars(n)} |")

    def census(d):
        c = {}
        for v in d.values():
            for l in (v["l1"], v["l2"]):
                c[l[2]] = c.get(l[2], 0) + 1
        return c

    L += ["", f"Passing-chord census: strict {census(strict)}; natural {census(natural)}", ""]
    with open(os.path.join(DOCS, "GOLDEN_PROGRESSIONS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    data = {f"{a}>{b}": {"from": cname(a), "to": cname(b),
                         "strict": {"chords": [list(c) for c in strict[(a, b)]["chords"]],
                                    "p1": strict[(a, b)]["l1"], "p2": strict[(a, b)]["l2"]},
                         "natural": {"chords": [list(c) for c in natural[(a, b)]["chords"]],
                                     "p1": natural[(a, b)]["l1"], "p2": natural[(a, b)]["l2"]}}
            for (a, b) in strict}
    with open(os.path.join(DOCS, "golden_progressions.json"), "w", encoding="utf-8") as f:
        json.dump({"edo": 36, "key": "C major", "unit": "36-ET step (MIDI*3)", "voices": "B T A S",
                   "pairs": data, "progressions": pj}, f, indent=1)
    print("strict census", census(strict))
    print("natural census", census(natural))
    print("four-chord forms", len(four), " three-chord forms", len(three))
    for a, b in COMMON[:12]:
        r, n = strict[(a, b)], natural[(a, b)]
        print(f"  {a:>5s}->{b:<5s} strict {r['l1'][0]:16s} {r['l2'][0]:16s} | natural {n['l1'][0]:14s} {n['l2'][0]}")


if __name__ == "__main__":
    main()
