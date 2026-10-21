# Golden harmony beyond passing: modulation, key maps and blending with Western harmony

This document develops ways of working with golden harmony that go beyond passing chords: key changes by the
small golden intervals, pivot chords between keys on different layers, a map of all 36-ET keys, passing keys and
bridge scales, golden modes and hybrid scales, and several blending techniques. It extends
[GOLDEN_THEORY.md](GOLDEN_THEORY.md) (classification of passing harmony), [GOLDEN_MATH.md](GOLDEN_MATH.md)
(commas, MOS scales, averaging) and textbook Chapter 32 (*Modulation in 36-ET*), whose results are cited, not repeated.

**Code.** Every table and number below is printed by [reference/golden/blending.py](../reference/golden/blending.py):
```
.venv/Scripts/python reference/golden/blending.py          # all 20 sections (section 5 runs the passing engine, a few minutes)
.venv/Scripts/python reference/golden/blending.py 2 8      # selected sections
```
Section numbers of the script are given as **[bl §n]**.

**Status labels** (AUTHORING.md §6):
- **Theorem**: proved here (proof given or sketched).
- **Exhaustive**: checked by complete enumeration in the script; a theorem about the finite system.
- **Measurement**: depends on a model (Sethares roughness with harmonic partials k = 1..8, amplitudes 0.88^(k−1), close
  position from C4 = 261.63 Hz unless stated; the model of `explore.py`). Register changes the numbers.
- **Proposal** / **Hypothesis**: compositional suggestion, or a claim about perception to be tested by listening.

**Framing** (GOLDEN_THEORY §3.0, AUTHORING §10). Physical instruments are harmonic. On them C major is the global
minimum of tension and the deepest release; arriving on a Western chord from golden harmony is always release. The
golden triad is, in the author's model and listening experience, a delicate local minimum, a metastable home. On
harmonic tones the standard models do not show that local minimum (golden 1.498, major 1.319 [bl §19]); golden-spectrum
timbres are a digital laboratory. Nothing below claims an instrument "becomes golden".

**Conventions.**
- Pitch classes are sixth-steps mod 36: C = 0, ^C = 1, vC# = 2, C# = 3, … Names are `songmap.theory.passing.name36`
  spellings (C#, Eb, ^Ab, vF#).
- The **layer** of p is p mod 3 (0 = 12-ET, 1 = ^, 2 = v).
- G_r = {r, r+11, r+22} is the golden triad on r (Cg = G_0). Western triads: M_r (major), m_r (minor).
- **Chain position** of a pitch class p: the j with 25 j ≡ p (mod 36), i.e. j ≡ 13 p, folded to [−18, 18). Write
  c(s) = 13 s folded, the chain distance of a transposition by s sixth-steps.
- **Circle position** of G_r on the golden circle (GOLDEN_THEORY §3.2): p with 11 p ≡ r, i.e. p ≡ 23 r = −13 r. So
  circle position = −(chain position of the root).
- **Voice-leading distance** d(X, Y) between pc-sets of equal size: the minimum over bijections of the summed circular
  distances, in sixth-steps (Tymoczko's L1 metric on the circle; for scales, a cyclic shift of the sorted order is optimal).
  A chord G is a **geodesic hinge** between X and Y if d(X, G) + d(G, Y) = d(X, Y): it lies on a smoothest voice leading.

---

## Summary of results

1. **The three small golden intervals are modulation units** [Exhaustive, bl §1]. Golden comma φ¹³/2⁹ (30.17 c,
   chain 13) = 1 sixth-step; golden limma 2⁷/φ¹⁰ (69.10 c, chain −10) = 2; golden apotome φ³/4 (99.27 c, chain 3) = 3.
   Every transposition s is |c(s)| chain steps away; the table of c(s) is the key to everything below.
2. **The comma pump** [Theorem + Exhaustive, bl §2]. Thirteen steps up the golden chain take C golden13 to ^C golden13;
   each step raises exactly one note by one sixth-step, in chain order (Bb, ^F#, vEb, B, ^G, vE, C, ^Ab, vF, C#, ^A,
   vF#, D). Ten steps down reach vC# golden13 (each step *lowers* one note, yet the key rises by a limma); three steps
   up reach C# golden13. Harmonically the walk is the golden circle: the tonic golden triads Cg → ^Abg → vFg → … → ^Cg are
   13 consecutive circle steps.
3. **golden13 keys form a perfect circle in voice-leading space** [Theorem for |c| ≤ 13, Exhaustive for all]:
   d(golden13 on C, golden13 on s) = |c(s)| for all 36 tonics. Neighbouring keys (a golden third or sixth apart) are
   one sixth-step apart in total motion.
4. **Lifts** [Theorem]. A sixth-step lift (modulation by a golden comma) has *no* golden chord on any smoothest voice
   leading: every chord between X and X + 1 is a subset of X ∪ (X + 1), two layers only. A third-step lift (modulation
   by a golden limma) has *exactly one* golden midpoint for every major or minor triad: C → **^Cg** → vC#,
   Am → **Ag** → vBbm (3 + 3 = 6 sixth-steps).
5. **The golden projection π** [Exhaustive + Theorem]. Every major triad M_r has exactly one nearest golden triad,
   G_r, at distance 2; every minor m_r has exactly one, G_{r−1}; each augmented triad has three; diminished ones are at
   distance 4. No Western triad is at distance 1 from a golden triad. So each golden triad has exactly three Western
   preimages at distance 2, one per layer: G_r = π(M_r) = π(m_{r+1}) = π(the augmented triad {r+11, r+23, r+35}).
6. **π turns neo-Riemannian moves into golden-home moves** [Exhaustive over 72 triads]: π∘L = one golden-circle step,
   π∘P = planing by a sixth-step, π∘R = circle step plus planing (golden root ±10).
7. **Projection pivots: keys a silver third apart share three golden pivot chords** [Exhaustive over 108 keys].
   C major and ^Eb major (+10 sixth-steps, 333 c) share Cg, Fg, Gg (I, IV, V of C = vi, ii, iii of ^Eb); C major and
   vA major (−10) share vDg, vEg, vAg (ii, iii, vi of C = IV, V, I of vA). Three is the maximum for keys on different
   layers. Each pivot is a geodesic of 2 + 2 = 4 sixth-steps with every voice monotone (C → Cg → ^Cm). This is
   pivot-chord modulation between layers, which Western harmony cannot do (the keys share no note).
8. **Western and golden keys** [Exhaustive]: F harmonic minor and vA harmonic minor each contain preimages of 4 of
   the 5 golden triads of C golden7 (F minor's i, III+, V, VI ↦ vFg, ^Abg, Cg, C#g); no Western key does better.
9. **golden13 is maximally even in 36-ET** (steps 3 and 2), and so is golden23; golden7, golden10 and the diatonic
   are not [Exhaustive]. The unique maximally even 7-note scale of 36-ET (steps 5, 6) contains three silver triads and
   nothing else tertian; a transposition of it is the centroid (Ionian + Aeolian + Locrian)/3 = C vD ^Eb F vG ^Ab ^Bb.
10. **The hybrid limit** [Exhaustive over all 1,623,160 seven-note scales containing C]: the Pareto frontier of
    (Western consonant triads, golden triads) is (7, 0), (3, 2), (2, 3), (0, 5). No 7-note Myhill (well-formed) scale
    contains both a Western consonant triad and a golden triad. The best hybrids are not inflections of C major; the
    best inflection, the **golden Ionian** C D vE F ^G A B, reaches (2, 2).
11. **Centroid scales** [Exhaustive over 286 averages of three modes]: an average of three 12-ET scales always lies on
    the 36-ET grid; (2·major + minor)/3 = C D vE F G vA vB contains no major, minor, augmented, diminished, golden,
    silver or bronze triad at all (a negative result); Cg appears only when a ♯5 mode (Lydian augmented) is in the mix.
12. **Golden planing is three-key polytonality** [Theorem]: harmonizing a C major line in parallel golden triads is the
    same as playing it simultaneously in C, vE and ^G major, three pairwise disjoint keys on three layers (21 notes).
13. **Negative results**: the golden escalator does not lift to golden7 key areas (only one golden13 key contains both
    escalator chords, sharing 2 notes with each Western key); no golden7 scale lies between C and ^C major (best
    detour 15 against 7); System 1 is undefined across layers and the engine's strict fallback finds no golden chord in
    108 cross-layer pairs; no golden triad or seventh has an interval that resolves outward to an octave by contrary
    sixth-steps (no "golden augmented sixth").

**Ranking of the techniques** (grounding × musical use), §12: projection pivots; the comma pump; the golden midpoint of
the limma lift; golden-third key cycles through projections; golden colour chords by projection; golden planing;
golden pedals; the golden Neapolitan; the F-minor ↔ golden7 bridge; hybrid scales; passing keys (weak); centroid
scales (weak); canon at the golden third (weakest).

---

## 1. Units of golden modulation

### 1.1 Comma, limma, apotome [Exhaustive, bl §1]

| Interval | Exact | Exact cents | Chain distance j | 25 j mod 36 | 36-ET |
|---|---|---|---|---|---|
| golden comma | φ¹³/2⁹ | 30.17 | 13 | 1 | 33.33 c |
| golden limma | 2⁷/φ¹⁰ | 69.10 | −10 | 2 | 66.67 c |
| golden apotome | φ³/4 | 99.27 | 3 | 3 | 100.00 c |
| chain 23 | φ²³/2¹⁶ | −38.92 | 23 | −1 | −33.33 c |
| 36-comma | φ³⁶/2²⁵ | −8.75 | 36 | 0 | 0 |

- Checks: 13·25 = 325 = 9·36 + 1; −10·25 = −250 = −7·36 + 2; 3·25 = 75 = 2·36 + 3.
- apotome − limma = comma (30.17 c); limma + comma = apotome (99.27 c); in 36-ET 2 + 1 = 3.
- **36-ET's enharmonic identification.** The golden comma (chain +13, +30.17 c) and the chain-23 interval
  (−38.92 c) are both rendered as one sixth-step (up and down respectively): 13 − (−23) = 36, and they differ by the
  36-comma, 30.17 + (−38.92) = −8.75 c. In exact golden tuning ^ written as "comma up" and v written as "chain-23 down"
  are different intervals; 36-ET makes them inverse. This is the golden analogue of 12-ET identifying B# with C.

### 1.2 Chain distance of every transposition

c(s) = 13 s mod 36, folded to [−18, 18). A transposition by s sixth-steps moves a golden scale |c(s)| chain steps.

| s | name | c(s) | s | name | c(s) | s | name | c(s) | s | name | c(s) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | C | 0 | 9 | Eb | 9 | 18 | F# | −18 | 27 | A | −9 |
| 1 | ^C | 13 | 10 | ^Eb | −14 | 19 | ^F# | −5 | 28 | ^A | 4 |
| 2 | vC# | −10 | 11 | vE | −1 | 20 | vG | 8 | 29 | vBb | 17 |
| 3 | C# | 3 | 12 | E | 12 | 21 | G | −15 | 30 | Bb | −6 |
| 4 | ^C# | 16 | 13 | ^E | −11 | 22 | ^G | −2 | 31 | ^Bb | 7 |
| 5 | vD | −7 | 14 | vF | 2 | 23 | vAb | 11 | 32 | vB | −16 |
| 6 | D | 6 | 15 | F | 15 | 24 | Ab | −12 | 33 | B | −3 |
| 7 | ^D | −17 | 16 | ^F | −8 | 25 | ^Ab | 1 | 34 | ^B | 10 |
| 8 | vEb | −4 | 17 | vF# | 5 | 26 | vA | 14 | 35 | vC | −13 |

**Reading.** Pitch-near is chain-far: ^C (33 c away) is 13 chain steps, C# (100 c) only 3, vE (a golden third) 1.

### 1.3 Chroma of each golden MOS

Moving a golden-n window by one chain step removes one note and adds another n chain steps away; the change is the
scale's chroma (large step − small step) [Exhaustive, bl §1]:

| Scale | Chain n | Change in 36-ET | Exact |
|---|---|---|---|
| golden3 | 3 | +3 | +99.27 c |
| golden4 | 4 | −8 | −267.64 c |
| golden7 | 7 | −5 | −168.37 c |
| golden10 | 10 | −2 (a limma) | −69.10 c |
| **golden13** | 13 | **+1 (a comma)** | +30.17 c |
| golden23 | 23 | −1 | −38.92 c |

So golden13 and golden23 are the scales whose key changes are single sixth-steps; golden10 changes by a limma.

---

## 2. Lifts: modulation by a golden comma or limma

### 2.1 Definition and motivation
A **lift** by s sixth-steps transposes the whole key (planing modulation, the "truck-driver" key change of pop music
shrunk below a semitone). It is the simplest key change in 36-ET: Chapter 32 calls it a *direct shift*. Lifts by 1
(comma) and 2 (limma) are the golden-sized ones.

| Lift | Target | Tonic triad d | Moves (C, E, G) | Scale d | Scale moves (C D E F G A B) |
|---|---|---|---|---|---|
| +1 | ^C major | 3 | (+1, +1, +1) | 7 | all +1 |
| +2 | vC# major | 6 | (+2, +2, +2) | 14 | all +2 |
| −1 | vC major | 3 | (−1, −1, −1) | 7 | all −1 |
| −2 | ^B major | 6 | all −2 | 14 | all −2 |
| +3 | C# major | 9 | all +3 | 15 | (0, −3, −3, 0, −3, −3, −3) |
| +4 | ^C# major | 12 | all +4 | 12 | (+1, −2, −2, +1, −2, −2, −2) |
| +5 | vD major | 15 | all +5 | 9 | (+2, −1, −1, +2, −1, −1, −1) |

[Exhaustive, bl §4.] Minor targets from C major: Cm 3, **^Cm 4** (moves +1, −2, +1), vC#m 5, vCm 6, vAm 7.

**Roughness** [Measurement]: a lift preserves every interval, so in the model only the register changes:
C 1.3189 → ^C 1.3008, Cm 1.3418 → ^Cm 1.3235, Cg 1.4980 → ^Cg 1.4810 (−0.018 each).

### 2.2 The sixth-step lift has no golden chord on the way [Theorem]
**Theorem (layer betweenness).** Let X be a pc-set on one layer and Y = X + 1. Then d(X, Y) = |X|, and every geodesic
hinge between X and Y is a subset of X ∪ Y. In particular no golden, silver or bronze triad lies on a smoothest voice
leading from X to X + 1.

*Proof.* X and Y lie on different layers, so every voice moves at least one sixth-step: d ≥ |X|, and the uniform
+1 attains it. Let G be a hinge with bijections σ: G → X, τ: G → Y. Then τσ⁻¹ is a bijection X → Y of cost
≤ Σ_g (|g − σg| + |g − τg|) = d(X, Y) = |X|. Every pair (σg, τg) costs at least 1, so each costs exactly 1 and each
triangle inequality is tight: g lies on the shortest arc between two points one sixth-step apart, so g ∈ {σg, τg}.
Hence G ⊂ X ∪ Y, which touches only two layers; golden, silver and bronze triads touch three. ∎
[Exhaustive check over all 48 major, minor, augmented and diminished triads on layer 0: 0 golden hinges, bl §6.]

Corollary for scales: no golden7 scale lies between C major and ^C major; the best golden7 detour costs 15
(^C golden7: 7 + 8, or E golden7: 8 + 7) against the direct 7 [Exhaustive, bl §9]. The cheapest golden detour for the
tonic triads is the known C → Cg → ^C, 2 + 3 = 5 against 3 (Chapter 32).

### 2.3 The limma lift has a golden midpoint [Theorem]
**Theorem (golden midpoint).** For every major triad M_r on layer 0, the lift M_r → M_r + 2 has exactly one golden
geodesic hinge, G_{r+1} (written ^Xg), and it is the exact midpoint (3 + 3). For every minor triad m_r the unique hinge
is G_r (Xg). For the downward limma lift X → X − 2 the hinges are G_{r−1} (major) and G_{r−2} (minor).

*Proof.* A major or minor triad has no semitone, so the cheapest move of each voice into X + 2 is +2 (a move of −1
would need a note a semitone lower in X); d = 6, uniquely by the uniform lift. As in 2.2, every note of a hinge lies on
the arc between x and x + 2, so G = {x_i + e_i} with e_i ∈ {0, 1, 2}. G is golden only if its notes are on three
layers, i.e. (e_i) is a permutation of (0, 1, 2), and then Σe_i = 3: the midpoint. Checking the 6 permutations: for
(0, 12, 21) only (+1, 0, +2) gives a golden triad, {1, 12, 23} = ^Cg; for (0, 9, 21) only (0, +2, +1), {0, 11, 22} = Cg. ∎
[Exhaustive for all 24 triads and both directions; lifts by ±4 and ±5 sixth-steps have 4 and 7 golden hinges for every one of the 24 triads (bl §6 checks +4, +5; the
downward lifts were checked for ch34).]

**Example (C major → vC# major, D2).**

| Voice | C | ^Cg | vC# |
|---|---|---|---|
| root | C | ^C | vC# |
| third | E | E | vE# (= vF) |
| fifth | G | vAb | vAb (= vG#) |

Each voice moves +2 in total; at the midpoint the three voices are at +1, 0, +2, one per layer. The passing engine
finds the same chord: `C:1 ~g:1 vC#:2` resolves to C – ^Cg – vC# [bl §20].

**Reading.** Modulation by a golden comma is a pure change of plane (no golden chord can mediate it without a
detour); modulation by a golden limma passes *through* gold at its exact midpoint. [Theorem.] Whether the ear hears
the limma lift with its golden midpoint as smoother than the plain lift is a hypothesis to test.

### 2.4 Demos
- **D1** sixth-step lift: `C:1 F:0.5 G7:0.5 C:1 ^C:1 ^F:0.5 ^G7:0.5 ^C:2`.
- **D2** limma lift through its golden midpoint: `C:1 F:0.5 G7:0.5 C:1 ^Cg:1 vC#:1 vF#:0.5 vG#7:0.5 vC#:2`.
- **D2b** the engine's own choice: `C:1 ~g:1 vC#:2` (→ C ^Cg vC#).

---

## 3. The comma pump: modulation along the golden chain

### 3.1 golden13 keys step by step [Exhaustive, bl §2]
golden13 on tonic t is the chain window of 13 consecutive positions centred on chain(t). Moving the tonic up a golden
sixth (one chain step) removes the window's lowest note and adds a note 13 chain steps higher: **one note rises by one
sixth-step** (the golden comma). Thirteen steps: C golden13 → ^C golden13.

| Step | Tonic | Note out → in | Move | ∩ C major | ∩ ^C major | ∩ vC# major |
|---|---|---|---|---|---|---|
| 0 | C | | | 3 | 2 | 3 |
| 1 | ^Ab | Bb → ^Bb | +1 | 3 | 2 | 3 |
| 2 | vF | ^F# → vG | +1 | 3 | 2 | 3 |
| 3 | C# | vEb → Eb | +1 | 3 | 2 | 2 |
| 4 | ^A | B → ^B | +1 | 2 | 3 | 2 |
| 5 | vF# | ^G → vAb | +1 | 2 | 2 | 3 |
| 6 | D | vE → E | +1 | 3 | 2 | 3 |
| 7 | ^Bb | C → ^C | +1 | 2 | 3 | 3 |
| 8 | vG | ^Ab → vA | +1 | 2 | 3 | 3 |
| 9 | Eb | vF → F | +1 | 3 | 3 | 2 |
| 10 | ^B | C# → ^C# | +1 | 3 | 3 | 2 |
| 11 | vAb | ^A → vBb | +1 | 3 | 2 | 3 |
| 12 | E | vF# → F# | +1 | 3 | 2 | 2 |
| 13 | ^C | D → ^D | +1 | 2 | 3 | 2 |

- The notes leave in chain order, −6 … +6 (Bb, ^F#, vEb, B, ^G, vE, C, ^Ab, vF, C#, ^A, vF#, D), and each comes back
  one sixth-step higher. After 13 steps every note has been raised once: the key has been lifted by a comma, one note at a
  time. Every step was checked to move exactly one note by exactly one sixth-step.
- **Downward (13 steps)**: C → vE → ^G → B → vEb → ^F# → Bb → vD → ^F → A → vC# → ^E → Ab → vC golden13, each step
  lowering one note by a sixth-step.
- **Limma (10 steps down)**: stopping the downward walk after 10 steps gives **vC#** golden13, which is C golden13 *raised*
  by 2 sixth-steps. Ten notes each fall one sixth-step and the scale as a whole rises by a limma: 10 lowered notes plus
  3 kept notes are the same set as all 13 notes raised by two. (Exactly: each moving note falls one golden comma,
  30.17 c, while the tonic moves 10 chain steps down, the golden limma 2⁷/φ¹⁰ = 69.10 c *up*; in 36-ET, −10 ≡ 26 = 2 · 13.)
- **Apotome (3 steps up)**: C → ^Ab → vF → C# golden13 (Bb → ^Bb, ^F# → vG, vEb → Eb).

**golden7 by comparison**: each chain step changes one note by 5 sixth-steps (the golden7 chroma); the golden7 keys
nearest C golden7 in voice-leading are vE and ^Ab (5), then ^C and vC (7, sharing no note), then vF, ^G, ^Eb and vA (10).

### 3.2 golden13 keys lie on a perfect circle [Theorem + Exhaustive]
**Theorem.** d(golden13 on 0, golden13 on s) = |c(s)| for every s.

*Proof for |c| ≤ 13.* Shifting the window by c > 0 chain steps removes chain notes k − 6 … k − 7 + c and adds k + 7 … k + 6 + c;
pair j ↔ j + 13: each pair differs by 25·13 ≡ 1 sixth-step, so d ≤ c. Conversely the two sets share exactly 13 − c notes
(Chapter 32, window overlap), so at least c notes must move, each by ≥ 1: d ≥ c. ∎ For 14 ≤ |c| ≤ 18 the equality is an
exhaustive check (bl §2: e.g. F#, |c| = 18, d = 18).

So the 36 golden13 keys, measured by total voice motion, form the 36-cycle exactly: each chain neighbour is one sixth-step
away. By contrast the 36 major keys form three circles of fifths (one per layer, 3 sixth-steps per fifth) joined by lifts of
cost 7 (only ^C and vC are that close) [Exhaustive, bl §3].

### 3.3 The comma pump in harmony: the golden circle
The tonic golden triad of each key of the upward walk is in the next key too, and the tonic triads are consecutive
golden-circle chords walked backwards [Exhaustive, bl §2]:

Cg → ^Abg → vFg → C#g → ^Ag → vF#g → Dg → ^Bbg → vGg → Ebg → ^Bg → vAbg → Eg → ^Cg

Each step keeps two notes and raises the fifth a semitone (exact golden apotome), which becomes the new root
(G_t → G_{t+25} = G_{t−11}). Since 13 · (−11) = −143 ≡ 1, thirteen circle steps lift the chord by one sixth-step. In general,
reaching G_s from G_0 along the circle takes |c(s)| steps: 13 to ^Cg, 10 to vC#g (forward), 3 to C#g (backward).

**A complete comma-pump modulation** [Proposal]: C major → Cg (projection, 2) → 13 circle steps (3 each) → ^Cg → ^C major
(projection, 2). Total motion 2 + 39 + 2 = 43 sixth-steps for a change the plain lift does in 3: its value is not economy but
continuity, a key change in which every chord shares two notes with the next and every golden13 key differs from the last by
one comma. Along the walk the golden13 keys share 2–3 notes with C major and 2–3 with ^C major; Eb golden13 (step 9) and
^B golden13 (step 10) share 3 with both.

**Demos.**
- **D3** comma pump: `C:1 Cg:0.5 ^Abg:0.5 vFg:0.5 C#g:0.5 ^Ag:0.5 vF#g:0.5 Dg:0.5 ^Bbg:0.5 vGg:0.5 Ebg:0.5 ^Bg:0.5 vAbg:0.5 Eg:0.5 ^Cg:1 ^C:2`
  (a bell melody can follow the keys `C golden13`, `^Ab golden13`, …; all 14 key strings parse to the expected sets, bl §20).
- **D4** limma pump, 10 forward circle steps: `C:1 Cg:0.5 vEg:0.5 ^Gg:0.5 Bg:0.5 vEbg:0.5 ^F#g:0.5 Bbg:0.5 vDg:0.5 ^Fg:0.5 Ag:0.5 vC#g:1 vC#:2`.
- **D5** apotome pump: `C:1 Cg:1 ^Abg:1 vFg:1 C#g:1 C#:2`.

The register rises with the backward walk (in close voicing one voice moves +3 per step, so over 13 steps the voices climb
15, 12 and 12 sixth-steps). SongMap's `hold` keeps those lines in D3: the lower voices climb 15, 12 and 12 unchanged and
only the doubled top voice drops back once.

---

## 4. A map of keys

### 4.1 Common tones and voice-leading distance from C major [Exhaustive, bl §3]
CT = common tones, d = voice-leading distance (7-note families only).

| s | Tonic | major CT/d | nat. minor CT/d | golden7 CT/d | golden13 CT | silver13 CT |
|---|---|---|---|---|---|---|
| 0 | C | 7/0 | 4/9 | 2/8 | 3 | 3 |
| 1 | ^C | 0/7 | 0/10 | 2/7 | 2 | 2 |
| 2 | vC# | 0/14 | 0/11 | 1/10 | 2 | 3 |
| 3 | C# | 2/15 | 3/12 | 2/15 | 3 | 3 |
| 4 | ^C# | 0/12 | 0/17 | 1/16 | 3 | 2 |
| 5 | vD | 0/9 | 0/10 | 1/13 | 2 | 2 |
| 6 | D | 5/6 | 6/3 | 1/12 | 3 | 3 |
| 7 | ^D | 0/13 | 0/8 | 1/13 | 2 | 2 |
| 8 | vEb | 0/16 | 0/13 | 1/16 | 3 | 2 |
| 9 | Eb | 4/9 | 2/18 | 2/15 | 3 | 3 |
| 10 | ^Eb | 0/10 | 0/13 | 1/10 | 2 | 3 |
| 11 | vE | 0/11 | 0/8 | 2/7 | 2 | 2 |
| 12 | E | 3/12 | 6/3 | 2/8 | 3 | 3 |
| 13 | ^E | 0/17 | 0/10 | 1/13 | 2 | 2 |
| 14 | vF | 0/10 | 0/17 | 1/16 | 3 | 2 |
| 15 | F | 6/3 | 3/12 | 2/11 | 3 | 3 |
| 16 | ^F | 0/8 | 0/11 | 1/10 | 2 | 3 |
| 17 | vF# | 0/13 | 0/10 | 1/11 | 2 | 3 |
| 18 | F# | 2/18 | 4/9 | 2/14 | 3 | 3 |
| 19 | ^F# | 0/13 | 0/16 | 1/19 | 3 | 2 |
| 20 | vG | 0/8 | 0/13 | 1/14 | 2 | 2 |
| 21 | G | 6/3 | 5/6 | 1/11 | 3 | 3 |
| 22 | ^G | 0/10 | 0/9 | 2/10 | 2 | 2 |
| 23 | vAb | 0/17 | 0/12 | 1/13 | 3 | 3 |
| 24 | Ab | 3/12 | 2/15 | 2/18 | 2 | 2 |
| 25 | ^Ab | 0/11 | 0/14 | 1/13 | 3 | 3 |
| 26 | vA | 0/10 | 0/7 | 2/10 | 2 | 2 |
| 27 | A | 4/9 | 7/0 | 1/11 | 3 | 3 |
| 28 | ^A | 0/16 | 0/7 | 1/14 | 2 | 2 |
| 29 | vBb | 0/13 | 0/14 | 1/19 | 3 | 2 |
| 30 | Bb | 5/6 | 2/15 | 2/14 | 3 | 3 |
| 31 | ^Bb | 0/9 | 0/12 | 1/11 | 2 | 3 |
| 32 | vB | 0/12 | 0/9 | 1/10 | 2 | 3 |
| 33 | B | 2/15 | 5/6 | 2/11 | 3 | 3 |
| 34 | ^B | 0/14 | 0/13 | 1/16 | 3 | 2 |
| 35 | vC | 0/7 | 0/16 | 1/13 | 2 | 2 |

Findings [Exhaustive]:
- **Western keys**: three circles of fifths, one per layer, with d = 3 × (number of fifths); across layers the nearest
  keys are ^C and vC major and their relatives ^A and vA minor (d = 7), then ^F, vG major (8). "Pitch-near, tone-far": ^C is
  the closest key in pitch and shares nothing.
- **golden7 vs C major**: never more than 2 common tones. The nearest golden7 keys by voice-leading are **^C golden7 and
  vE golden7** (d = 7), then C golden7 (8). From C golden7 the nearest major keys are ^Ab and vC major (7), then Ab and
  C (8).
- **Harmonic and melodic minor** behave differently: harmonic minor can share no note with golden7 (vG and ^Bb harmonic
  minor against C golden7), and golden13 and silver13 share up to 4 notes with harmonic and melodic minor keys. The bounds
  below are for major and natural minor.
- **golden13 and silver13 vs C major**: never more than 3 common tones (every golden13 key shares 2 or 3; 19 golden13 keys
  share 3: C, C#, ^C#, D, vEb, Eb, E, vF, F, F#, ^F#, G, vAb, ^Ab, A, vBb, Bb, B, ^B). *Proof for golden13*: C major in
  chain coordinates is {−15, −9, −3, 0, 6, 12, 15}, gaps 6, 6, 3, 6, 6, 3, 6 around the 36-cycle; a window of 13 consecutive
  positions (span 12) contains at most 3 of them. ∎
- **Layers**: golden7 has 3, 2, 2 notes on its tonic's and the other layers; golden13 and silver13 have 5, 4, 4.
- **golden13 vs silver13 on C**: 7 common tones, d = 12; the nearest silver13 keys to C golden13 are C (12), then B, C#,
  ^Ab, vE (13).

### 4.2 Three metrics, three maps
1. **Common tones**: Western keys on other layers are at infinite distance (0 common tones, Chapter 32).
2. **Voice-leading**: everything is connected; the lift (7) is the shortest bridge between layers.
3. **Projection pivots** (§6): C major is linked to ^Eb major and vA major by three golden pivot chords each, although
   by voice-leading they are 10 apart and by common tones infinitely far.

**Golden-third and golden-fifth relations.**

| Relation | Western (C → vE / ^G major) | golden7 | golden13 |
|---|---|---|---|
| golden third (+11, chain −1) | 0 CT, scale d 11, tonic d 7, 2 shared projections | 6 CT, d 5 | 12 CT, d 1 |
| golden fifth (+22, chain −2) | 0 CT, scale d 10, tonic d 8 | 5 CT, d 10 | 11 CT, d 2 |

A suggested picture for the textbook figure [Proposal]: three concentric 12-cycles of Western keys (the layers),
crossed by the golden13 36-cycle as a helix that visits layer 0, then ^, then v, every step, returning to the 12-ET layer
every third step a semitone higher (C, C#, D, … are golden13 keys 3 chain steps apart, d = 3).

---

## 5. Pivots and hinges across layers

### 5.1 What cannot work, and what can [Theorem, Chapter 32]
- Western keys on different layers share no note (cosets of 3ℤ₃₆), so no Western pivot chord.
- A golden (or silver, or bronze) triad has one note on each layer, so it shares at most one note with any Western key.
- System 1 (strict) is **undefined** across layers: a displacement not divisible by 3 cannot split into three equal parts.
  The engine's strict fallback (move as early as evenly possible) found no golden chord in any of the 108 pairs
  (the six consonant triads of C major to the six of ^C, vC# and ^Eb major, three keys × 36 pairs) [Exhaustive, bl §5].

### 5.2 Golden geodesic hinges between diatonic triads [Exhaustive, bl §6]
All 7 × 7 pairs of diatonic triads (including diminished) from C major to the target key:

| Target | Pairs with an exact golden hinge | With a golden hinge of excess ≤ 2 |
|---|---|---|
| ^C major | 34/49 | 48/49 |
| vC# major | 46/49 | 48/49 |
| C# major | 43/49 | 49/49 |
| vC major | 34/49 | 48/49 |

Shortest examples with an exact hinge:
- To ^C major: **Am → ^C** (d 7; hinges ^Cg, vAg), Dm → ^F (vDg, ^Fg), Em → ^G (vEg, ^Gg), C → ^G (d 8; Cg, vCg),
  F → ^C (vFg, Fg). The tonic-to-tonic lift itself has none (§2.2), but **vi → ^I** does: the submediant is the door.
- To vC# major (d 6, one hinge each): C → vC# (^Cg), Dm → vEbm (Dg), Em → vFm (Eg), F → vF# (^Fg), G → vAb (^Gg),
  Am → vBbm (Ag), F → vFm (vFg).
- To C# major: C → Ab (Cg), Am → Fm (vFg), Dm → Bbm (vBbg) … (these are the same-layer quality-theorem pairs).

### 5.3 The passing engine across layers (System 2, `~g`) [Exhaustive, bl §5]
Six consonant diatonic triads of C major to six of the target (36 pairs), four-part engine, natural paths:

| Target | ≥ 1 exact golden passing chord | Two different golden chords | Golden incl. over a pedal |
|---|---|---|---|
| ^C major | 6 | 5 | 13 |
| vC# major | 19 | 10 | 21 |
| ^Eb major (= ^C minor) | 21 | 12 | 29 |

Representative engine paths (motion = total sixth-steps in four voices):
- **F – vFg – ^Eg – ^Em** (11): two golden chords from IV of C to iii of ^C (**D9**).
- Dm – ^C#g – C#g – ^C (17), Am – ^Abg – Abg – ^G (17): golden escalator shapes across a layer.
- C – ^Cg – vC# (8), F – ^Fg – vF# (8), G – ^Gg – vAb (8): the limma-lift midpoints (§2.3).
- **C – Cg – ^Cm, F – Fg – ^Fm, G – Gg – ^Gm** (5 each): exactly the projection pivots of §6, found independently by the
  engine as its smoothest golden paths into ^Eb major. Am – vAg – ^Ab and Em – vEg – ^Eb (7) leave through a projection
  (vAg = π(Am)) and arrive by a 3-sixth-step move.

So the natural engine already implements cross-layer golden modulation; it needs only a target in the other key.

---

## 6. The golden projection and projection pivots

### 6.1 Definition and theorem
**Definition.** The **golden projection** π(X) of a Western triad X is the golden triad nearest to it in voice-leading.

**Theorem (projection).** [Exhaustive over 144 triads, with the lower bound proved]
| Western triad | Nearest golden triad(s) | Distance |
|---|---|---|
| major M_r | G_r (unique) | 2 |
| minor m_r | G_{r−1} (unique) | 2 |
| augmented {r, r+12, r+24} | G_{r+1}, G_{r+13}, G_{r+25} | 2 |
| diminished d_r | G_{r−2} (unique) | 4 |

*Lower bound.* A golden triad has one note per layer and a Western triad all three on one, so at least two voices change
layer: distance ≥ 2, and no Western triad is at distance 1 (exhaustively: 0 such pairs). ∎

**Preimages.** The Western triads at distance 2 from Cg are exactly C (keeps C), ^Cm (keeps ^G) and vEaug = {vE, vAb, vC}
(keeps vE), one per layer (Chapter 31's table). So G_r = π(M_r) = π(m_{r+1}) = π({r+11, r+23, r+35}).

**Projections of C major's triads** [bl §7]:

| Triad | π | Notes | Motion (sorted pcs of the triad) | Common tone |
|---|---|---|---|---|
| C | Cg | C vE ^G | E −1, G +1 | C |
| Dm | vDg | vD ^F A | D −1, F +1 | A |
| Em | vEg | vE ^G B | E −1, G +1 | B |
| F | Fg | F vA ^C | C +1, A −1 | F |
| G | Gg | G vB ^D | D +1, B −1 | G |
| Am | vAg | vA ^C E | C +1, A −1 | E |

A major triad keeps its root and bends third down, fifth up (Cg = C(v3, ^5)). A minor triad keeps its fifth, bends the
root down and the third up.

### 6.2 Neo-Riemannian moves through π [Exhaustive over all 72 triads]
| Move | From major: golden root change | From minor | Golden-home operation |
|---|---|---|---|
| L (leading-tone exchange) | +11 | −11 | one golden-circle step |
| P (parallel) | −1 | +1 | planing by a sixth-step |
| R (relative) | −10 | +10 | circle step and planing |

(π commutes with transposition, so the check reduces to C and Cm; the script checks all 72.) The golden circle is the image
of the leading-tone exchange: C → Em projects to Cg → vEg, and F → Am to Fg → vAg. This explains Chapter 31's
observation that the circle step *is* the L gesture.

### 6.3 Projection pivots: the silver-third key relation [Exhaustive over 108 keys, bl §8]
Let π(K) be the set of projections of the six consonant triads of a key. For a major key on t,
π(K) = t + D with **D = {0, 5, 11, 15, 21, 26}** (majors on 0, 15, 21 keep their roots; minors on 6, 12, 27 project to 5, 11, 26).
Two keys share |π(K) ∩ π(K')| = #{(a, b) ∈ D²: b − a ≡ t' − t} golden projections. From C major:

| Key | Shift | Shared | Pivot chords (C major triad / other key's triad) |
|---|---|---|---|
| F major, G major (and D minor, E minor) | ±15 | 4 | common triads (same layer) |
| **^Eb major (= ^C minor)** | **+10** | **3** | **Cg (C / ^Cm), Fg (F / ^Fm), Gg (G / ^Gm)** |
| **vA major (= vF# minor)** | **−10** | **3** | **vDg (Dm / vD), vEg (Em / vE), vAg (Am / vA)** |
| vE major | +11 | 2 | vEg (Em / vE), vAg (Am / vA) |
| ^Ab major | −11 | 2 | Cg (C / ^Cm), Fg (F / ^Fm) |
| vD major | +5 | 2 | vDg (Dm / vD), vAg (Am / vA) |
| ^Bb major | −5 | 2 | Cg (C / ^Cm), Gg (G / ^Gm) |
| D major, Bb major | ±6 | 2 | same layer |

Distribution over the 36 major keys: 0 shared: 21; 1: 4; 2: 6; 3: 2; 4: 2; 6: 1 (itself). Over the 36 harmonic minor keys
the maximum is 3 (E and A harmonic minor, same layer); across layers 2 (^C, ^G harmonic minor). Counting only the true
degree triads (i, iv, V, VI; `key_triads` in blending.py also picks up non-tertian pitch-class subsets of harmonic minor,
which inflates the low counts) the distribution is 0: 19, 1: 12, 2: 3, 3: 2; the maxima are unchanged.

**Theorem (silver-third pivots).** Keys on different layers share at most three golden projections, and exactly three
when their tonics are ±10 sixth-steps apart (a silver third, 333.33 c): the pairs are I/vi, IV/ii, V/iii (to ^Eb) and
ii/IV, iii/V, vi/I (to vA). Each shared projection G_r joins a major triad M_r of one key with the minor triad m_{r+1} of the
other, and M_r → G_r → m_{r+1} is a geodesic: d(M_r, m_{r+1}) = 4 = 2 + 2, every voice monotone
(C → Cg → ^Cm: C 0, +1; E −1, −1; G +1, 0). [Exhaustive; the geodesic property is a 3-voice check made for all r by
transposition.]

**Why this is new.** Chapter 32 found C → Cg → ^Cm (cost 4) as the most efficient golden route from C major to another
layer. The projection theorem shows it is one of *three* such pivots between C major and ^Eb major (= ^C minor), names the
key relation (the silver third), and gives its mirror (vA major). Western pivot-chord modulation needs a chord diatonic in both keys. Between layers there is none, but
here are three golden chords, each *the* golden image of a diatonic chord in both keys. The golden chord plays the
pivot's double role exactly: in C it is "golden IV", in ^Eb it is "golden ii".

**Reinterpretation** (the golden analogue of enharmonic reinterpretation) [Theorem]: one golden triad has three Western
meanings, one per layer: Cg is golden I of C major, golden i of ^C minor (golden vi of ^Eb major), and the golden image of
the augmented triad vE vAb vC (III+ of vC# harmonic minor). The ear cannot tell from the golden chord alone which one is
meant; the continuation decides, as with a German sixth and a dominant seventh.

### 6.4 Worked modulations [Proposal; harmony verified by SongMap]
- **D6** C major → ^Eb major via Fg (IV = ii): `C:1 Am:1 F:1 Fg:1 ^Fm:1 ^Bb7:1 ^Eb:2`. After the pivot, a
  ii–V7–I in the new key confirms it.
- **D8** via Gg (V = iii): `C:1 Dm:1 G:1 Gg:1 ^Gm:1 ^Ab:1 ^Bb7:1 ^Eb:1`.
- **D7** C major → vA major via vAg (vi = I): `C:1 F:1 G:1 Am:1 vAg:1 vA:1 vE7:1 vA:2`. Am → vAg → vA is a golden
  "Picardy" a sixth-step down: A −1, C +1 then +1, E 0 then −1.

### 6.5 Golden keys and Western keys [Exhaustive, bl §8]
Projecting major, minor and augmented triads (an augmented triad projects to three golden triads), the Western keys whose
triads project onto the most golden triads of C golden7 (Cg, C#g, vEg, vFg, ^Abg) are (over all 144 major, natural,
harmonic and melodic minor keys the coverage distribution is 0: 50, 1: 62, 2: 25, 3: 5, 4: 2; without augmented triads
the maximum is 3):

| Western key | Covered | Preimages |
|---|---|---|
| **F harmonic minor** | 4 of 5 | Cg ← C (V), C#g ← Db (VI), vFg ← Fm (i), ^Abg ← Ab+ (III+) |
| **vA harmonic minor** | 4 of 5 | Cg ← vC+ (III+; the same set as vE+), vEg ← vE (V), vFg ← vF (VI), ^Abg ← vAm (i) |
| ^C, ^C# harmonic minor; ^C# melodic minor; F, vA melodic minor | 3 | |
| C major | 2 | Cg ← C, vEg ← Em |

No Western key covers all five. So the natural Western partner of C golden7 is F harmonic minor (whose dominant is C):
**D20** `Fm:1 Db:1 Abaug:1 C:1 Cg:1 C#g:1 vFg:1 ^Abg:1 Cg:1 C:1 Fm:2` (key F minor) walks from F minor into C golden7
through the projections of its own V, VI, i and III+, and back. Status: chord facts exhaustive; any functional reading is
hypothesis.

---

## 7. Passing keys and bridge scales

### 7.1 The golden escalator as key areas: a negative result [Exhaustive, bl §10]
The engine's natural path C – vC#g – ^C#g – D (and F – vF#g – ^F#g – G) puts two golden chords on the chromatic root.
Raising them to key areas fails by every metric:
- vC# golden7 (vC# vD ^E ^F Ab A vC) shares 1 note with C major (A) and 1 with D major (A); ^C# golden7 shares F and F#
  respectively; the two golden7 keys share nothing (chain distance 10, d = 14). Direct C major → D major: 5 common tones, d = 6.
- No golden7, golden10 or silver13 key contains both escalator chords; exactly one golden13 key does (**vB golden13** for
  C → D, **vE golden13** for F → G), because the two chords are 10 circle steps apart (circle positions 10 and −16), the full
  span of golden13's 11 golden triads. It shares only 2 notes with each Western key.
- The degree-by-degree scale averages (2·C + D)/3 = ^C D E ^F G A B and (C + 2·D)/3 = vC# D E vF# G A B contain only G and Em.

**Reading.** The escalator is a voice-leading phenomenon (two lines rising through the layers), not a key phenomenon: its
golden chords belong to no common golden diatonic. Use it as passing harmony (**D21**), not as passing keys.

### 7.2 Bridge scales between Western keys [Exhaustive, bl §9]
Best golden scales by shared notes with both keys (a + b), and for 7-note scales the voice-leading detour d(K₁,S) + d(S,K₂):

| K₁ → K₂ | d(K₁,K₂) | golden7 | golden13 (3 + 3) | silver13 (3 + 3) |
|---|---|---|---|---|
| C → ^C major | 7 | ^C or E (2 + 2, detour 15) | ^C#, Eb, F, ^F#, Bb, ^B | C#, ^Eb, ^F, vF#, F#, ^Bb, vB, B |
| C → vC# major | 14 | vC# or E (detour 18) | C, D, vEb, … | vC#, E, vF#, … |
| C → C# major | 15 | C or F (2 + 2, detour 19) | C, C#, D, … | C, C#, D, … |
| C → ^C minor | 10 | **vE (2 + 2, detour 14 = 7 + 7)** | C#, ^C#, vEb, … | D, ^Eb, E, … |

No golden7, golden13 or silver13 scale shares more than 3 notes with a major or natural minor key (§4.1), so a golden bridge key is never a common-tone bridge in
the Western sense; golden13 keys sharing 3 + 3 are the best available. golden10 has no 3 + 3 bridge between C and ^C.

### 7.3 Interstitial scales (one note at a time from C major to ^C major) [Exhaustive, bl §9]
Raising a subset of C major's notes by a sixth-step gives 126 two-layer interstitial scales. They contain no golden triad
(§2.2). The raising order that keeps the most consonant triads at every stage (maximin over all 5040 orders) is
**D, F, A, C, E, G, B**, keeping at least 3:

| After raising | Scale | Consonant triads |
|---|---|---|
| D | C ^D E F G A B | C, F, Em, Am |
| F | C ^D E ^F G A B | C, Em, Am |
| A | C ^D E ^F G ^A B | C, ^Dm, Em |
| C | ^C ^D E ^F G ^A B | ^F, ^Dm, Em |
| E | ^C ^D ^E ^F G ^A B | ^F, ^Dm, ^Am |
| G | ^C ^D ^E ^F ^G ^A B | ^C, ^F, ^Dm, ^Am |

The order lifts the ii triad first, then I, then the leading tone. [Proposal] A Western "comma pump" in seven stages, with
Western triads on two layers sounding side by side.

### 7.4 How long must a passing key last? [Proposal]
No measurement exists yet. A testable criterion:
1. **Content**: the passing key must sound the notes that distinguish it from both neighbours (for a golden13 key one
   comma-shifted note per chain step, so a passing golden13 key needs only one new note, while a golden7 key needs a note 5
   sixth-steps away from its predecessor).
2. **Anchor**: its tonic golden triad on a strong beat, approached by a circle step (the dominant-like vEg → Cg of
   Chapter 31 is itself a hypothesis).
3. **Duration**: a working figure of at least two chord changes or about 2–4 s, by analogy with Western tonicization; to be
   replaced by data.
4. **Test**: probe-tone ratings (Krumhansl and Kessler's method, 1982) after sequences in which the passing key lasts 1, 2, 4
   and 8 beats, with probes from the old key, the passing key and the new key.

---

## 8. Modes and scales

### 8.1 Modes of golden7 [Exhaustive, bl §11]
Brightness = sum of the mode's degrees in sixth-steps when transposed to C; consecutive modes differ in exactly one degree,
by the chroma (5 sixth-steps for golden7). The textbook proposes naming a golden7 mode b|a by the number of chain notes
below and above its tonic: the mode on chain position j is (3+j)|(3−j); the tonic golden triad is present iff b ≥ 2,
the golden seventh iff b ≥ 3 (ch36; a proposal).

| Mode on | Chain | Steps (sixth-steps) | As a mode on C | Tonic golden triad | Tonic golden seventh | Brightness |
|---|---|---|---|---|---|---|
| C# | +3 | 8 3 8 3 8 3 3 | C vEb vE ^F# ^G Bb B | yes | yes | 123 |
| vF | +2 | 8 3 8 3 3 8 3 | C vEb vE ^F# ^G ^Ab B | yes | yes | 118 |
| ^Ab | +1 | 8 3 3 8 3 8 3 | C vEb vE vF ^G ^Ab B | yes | yes | 113 |
| C | 0 | 3 8 3 8 3 8 3 | C C# vE vF ^G ^Ab B | yes | yes | 108 |
| vE | −1 | 3 8 3 8 3 3 8 | C C# vE vF ^G ^Ab ^A | yes | no | 103 |
| ^G | −2 | 3 8 3 3 8 3 8 | C C# vE vF vF# ^Ab ^A | no | no | 98 |
| B | −3 | 3 3 8 3 8 3 8 | C C# D vF vF# ^Ab ^A | no | no | 93 |

Like the diatonic modes (Lydian brightest, Locrian without a perfect fifth), the golden7 modes are totally ordered by
brightness, and the two darkest lack a tonic golden triad. Every mode contains all 5 golden triads of the parent scale.
The book has not named these modes; a natural naming is by chain position (golden7 +3 … −3).

### 8.2 Modes of golden13 [Exhaustive, bl §11]
13 modes, steps 3 and 2 (ten 3s, three 2s). The brightest is the mode on Bb (chain −6), the darkest on D (chain +6);
here *lower* chain positions are brighter because golden13's chroma is +1 (golden7's is −5). Tonic golden triad in 11
modes (all except the modes on ^F# and Bb, chain −5 and −6); tonic golden seventh in 10 (also not vEb, chain −4).

### 8.3 Evenness: golden13 is the maximally even 13-note scale [Exhaustive, bl §11]
**Theorem (chroma criterion, ch36).** A well-formed scale in n-EDO is maximally even iff its large and small steps differ
by one step of the EDO. This is why golden13 (3, 2) and golden23 are maximally even and golden2/3/4/7/10 and the 36-ET
diatonic are not. Chain spans of the triad types (golden-chain links between their notes): major and minor 21,
augmented 24, diminished 18, silver 22, bronze 22.

| Scale | Step sizes (count) | MOS | Myhill | Maximally even in 36-ET |
|---|---|---|---|---|
| C major (in 36-ET) | 3 (×2), 6 (×5) | yes | yes | no |
| golden7 | 3 (×4), 8 (×3) | yes | yes | no |
| golden10 | 3 (×7), 5 (×3) | yes | yes | no |
| **golden13** | 2 (×3), 3 (×10) | yes | yes | **yes** |
| golden23 | 1 (×10), 2 (×13) | yes | yes | yes |
| silver13 | 1, 2, 3, 4 | no | no | no |

Maximal evenness (Clough–Douthett) is tested as: every generic interval has one size or two consecutive sizes. The
13-note maximally even set ⌊36k/13⌋ = C vC# vD vEb vE ^E ^F ^F# ^G Ab A Bb B *is* golden13 (transposed; it is the D mode of
golden13 on C). So golden13 is the golden counterpart of the 12-ET diatonic in a sense golden7 is not: in its own tuning it is
both well-formed and maximally even. [Exhaustive.] The 7-note maximally even set of 36-ET (steps 5 and 6) contains three
silver triads and no other tertian triad (§8.6).

### 8.4 Golden inflections of C major [Exhaustive over 3⁷ = 2187 scales, bl §12]
Move each degree of C major by −1, 0 or +1 sixth-step. 419 inflections contain a golden triad; at most 3 do.
Pareto frontier of (W = consonant Western triads, G = golden triads):

| (W, G) | Example (fewest inflected notes) | Triads |
|---|---|---|
| (6, 0) | C D E F G A B | C, F, G, Dm, Em, Am |
| (3, 1) | C vD E ^F G A B | C, Em, Am, vDg |
| (3, 1) | C ^D E F G A vB | C, F, Am, Gg |
| **(2, 2)** | **C D vE F ^G A B** (golden Ionian) | F, Dm, **Cg, vEg** |
| (2, 2) | ^C D E F G vA B | G, Em, Fg, vAg |
| (0, 3) | C vD vE ^F ^G A B | Cg, vDg, vEg |
| (0, 3) | ^C ^D E F G vA vB | Fg, Gg, vAg |

The **golden Ionian** inflects only E and G, exactly the two notes the tonic needs to become golden; it keeps the
subdominant side (F, Dm, and Bdim) Western and gains vEg, the circle neighbour of Cg. It is not Myhill and not MOS.
Only 7 inflections have Myhill's property (C major, its two lifts, and four silver scales such as C D E ^F ^G vA vB with
5 silver triads); none contains a golden triad.

### 8.5 Centroid scales [Exhaustive over 286 averages, bl §13]
**Theorem.** The degree-by-degree average of three 12-ET scales always lies on the 36-ET grid (a sum of three multiples
of 3, divided by 3). An average of two lies on the 36 grid only where every degree differs by an even number of semitones,
and then it is on 12-ET: (Ionian + Aeolian)/2 has its third at 10.5 sixth-steps. ∎

Averages of three of 11 modes on C (the 7 diatonic modes, harmonic and melodic minor, Lydian augmented, harmonic major):
225 distinct scales, 44 with a golden triad, 16 with Cg.

| Centroid | Scale | Triads (all 7 types) | Myhill |
|---|---|---|---|
| (2·Ionian + Aeolian)/3 | C D vE F G vA vB | **none** | no |
| (Ionian + 2·Aeolian)/3 | C D ^Eb F G ^Ab ^Bb | none | no |
| (Ionian + Aeolian + Lydian aug.)/3 | C D vE ^F ^G vA vB | Cg, Ds, ^Fs, ^Gs, vBs | no |
| (Ionian + harm. minor + Lydian aug.)/3 | C D vE ^F ^G vA B | Cg, vEg, Ds, ^Fs | no |
| (harm. minor + Lydian aug. + harm. major)/3 | C D vE ^F ^G ^Ab B | Cg, vEg, ^Abg | no |
| **(Ionian + Aeolian + Locrian)/3** | C vD ^Eb F vG ^Ab ^Bb | **Cs, vDs, ^Bbs** | **yes (maximally even)** |
| (2·Ionian + Lydian)/3 | C D E ^F G A B | C, G, Em, Am | no |

Findings:
- The author's proposed (2·major + minor)/3 gives the tonic chord C vE G = C(v3), which is none of the named types; the
  scale has no tertian triad of any of the seven types. [Negative result.]
- Cg ⊂ centroid requires a mode with a ♯5 (here only Lydian augmented): the fifth averages to 22 only from (21, 21, 24) or (18, 24, 24) (Locrian + 2 × Lydian augmented, giving
  C vD vE vF# ^G vA vB, the same scale as Phrygian + Lydian + Lydian augmented). So 21 mode triples contain Cg (16 distinct
  scales), and every one includes Lydian augmented.
- The **silver tonic** arises from (Ionian + Aeolian + Locrian)/3, the scale version of Cs = (C + Cm + Cdim)/3; that
  centroid is the maximally even 7-note scale of 36-ET, and its three triads are all silver.

### 8.6 The hybrid limit [Exhaustive over all 1,623,160 seven-note scales containing C, bl §14]
- Maxima: W ≤ 7, G ≤ 5; with G ≥ 1, W ≤ 3; with W ≥ 1, G ≤ 3.
- **Pareto frontier**: (7, 0) [14 scales containing C], (3, 2) [56], (2, 3) [28], (0, 5) [7 = golden7's rotations].
- Examples at the frontier:
  - (3, 2): **C ^C D E F vA A**: F, Dm, Am, Fg, vAg. Adding the two notes vA, ^C to the pentachord C D E F A gives the
    projections of F and Am (an L-pair, so circle neighbours sharing vA and ^C). The six notes C ^C E F vA A reach
    (3, 2) with any of D, G, C# or Ab as the seventh note (Dm, C, A or Fm as the third Western triad).
  - (2, 3): C ^C ^C# E F vA A: F, Am, ^C#g, Fg, vAg.
  - (0, 5): golden7 (on C#: C C# D vF vF# ^Ab ^A as a set containing C).
- 672 scales have W ≥ 2 and G ≥ 2; 56 have W ≥ 3 and G ≥ 2.
- **Well-formedness**: 70 Myhill scales contain C; 7 contain a Western consonant triad, 7 a golden triad, **none both**.
  The 7-note MOS scales of 36-ET by generator: 3 (100 c), 5 (166.67 c: 3 silver triads), 10 (333.33 c, the silver third:
  5 silver triads), 11 (golden7: 5 golden), 15 (diatonic: 3 major, 3 minor), 4 and 16 (augmented triads only), 1, 2, 17
  (none); generator 8 also gives two step sizes (augmented triads only) but, being inside a 9-note cycle, is not Myhill.
- **Maximal evenness**: the 7 maximally even 7-note scales containing C (one transposition class) have W = G = 0 and 3 silver
  triads.

**Theorem (no well-formed hybrid).** No 7-note well-formed scale of 36-ET contains both a Western consonant triad and a
golden triad. [Exhaustive.] A hybrid scale is necessarily irregular: hybrids are colour collections, not new diatonics.

### 8.8 The golden decatonic (golden10) and its splits [Exhaustive + Theorem, ch36]
- **Splitting golden7's large step.** golden7 on C has steps 3 8 3 8 3 8 3 (sixth-steps). Splitting every 8 as 5 + 3
  gives "53" = 3 5 3 3 5 3 3 5 3 3, as 3 + 5 gives "35" = 3 3 5 3 3 5 3 3 5 3. Cyclically both read 5 3 3 5 3 3 5 3 3 3:
  they are modes of one scale, **golden10**. 35 on C is the chain window [−3, 6], 53 on C is [−6, 3] (= 35 on B), and
  SongMap's `C golden10` (−4..5) is a third mode of it.
- **All 27 splits** (each large step split 35, 53 or 44 independently): 18 rotation classes; exactly 4 are well-formed,
  all golden10. *Theorem*: a split is golden10 iff every 53 comes below every 35 (chain contiguity). The other four
  3/5 splits have 5–6 golden triads; none of the 19 splits using a 44 is well-formed or inside golden13; 7 splits contain a
  Western triad (F#, Bm, ^D, vEbm); none of the 27 is maximally even.
- **The 44 scale** (3 4 4 3 4 4 3 4 4 3): steps 3 and 4, not generated by any single interval, not Myhill (generic
  thirds of 6, 7 and 8 sixth-steps), symmetric about C. Its new notes ^D F# vBb form ^Dg; 6 golden triads, 4 golden
  sevenths; 10 distinct modes, brightness 168 down to 156 with three ties; the tonic golden triad in 6 modes, the seventh
  in 4. In exact tuning the midpoints of golden7's large steps (233.09, 600.00, 966.91 c) are not golden intervals.
- **golden10 content.** 10 modes, each lowering one note of the next by a golden limma (brightness 171 … 153); exact
  steps 99.27 c and 32/φ⁷ = 168.37 c; 8 golden triads, 7 golden sevenths, 6 golden ninths, no Western, silver or bronze
  triad. The golden third spans 3 scale steps, so golden chords are degrees 1-4-7. Interval counts (sixth-steps: pairs):
  3: 7, 5: 3, 6: 4, 8: 6, 9: 1, 11: 9, 14: 8, 16: 2, 17: 5.
- **Double pentatonic** [Theorem]: alternate notes of golden10 have equal chain parity, so 35 on C = the golden
  pentatonic C D vF ^G ^A plus the same pentatonic a golden third higher (C# vE vF# ^Ab B). These are the only two
  well-formed 5-subsets of the 252. The golden pentatonic (chain of golden fifths; well-formed at 2, 3, 5, 8, 13 notes in
  exact tuning) has steps 267.64 c × 3 and 198.54 c × 2: the Western pentatonic's proportions reversed.
- **The decatonic is the golden pentatonic by chroma** [Theorem + computation]: the chroma of an n-note well-formed scale
  spans n chain links, so the limma (5 fifths; 10 golden sixths) is the chroma of the pentatonic and of golden10. By
  chroma: apotome — diatonic (7) / golden3 (3); limma — pentatonic (5) / golden10 (10); comma — chromatic (12) /
  golden13 (13). The comma scale is the union of the other two (12 = 7 + 5 white + black keys; 13 = 3 + 10), and a key
  change by a limma keeps one part and moves the other: golden13 on C -> vC# keeps vEbg (Bb ^F# vEb) and moves exactly the
  35 decatonic on C; down to ^B it keeps Dg and moves the 53 decatonic. The proportions are reversed (10 + 3 against
  5 + 7) because the golden apotome lies 3 chain links away, the Pythagorean 7 (ch36 §pentatonic-mirror).
- **Distances.** From Cg to the golden triad k chain steps away (k = 0 … 18): 0, 3, 6, …, 18, 15, 12, 9, 6, 5, 4, 3, 6, …, 18.

### 8.7 Demos
- **D12** golden Ionian: `F:1 Dm:1 Cg:1 vEg:1 Dm:1 Cg:2` (melody in letters on C D vE F ^G A B).
- **D13** the (3, 2) hybrid C ^C D E F vA A: `F:1 Dm:1 Fg:1 vAg:1 Am:1 Fg:1 F:2`.

---

## 9. Golden modal mixture by projection (colour chords)

**Definition.** In a Western key, replace a diatonic triad X by its projection π(X) as a colour chord, on a strong beat
or held, rather than as a passing chord. It is the golden analogue of borrowing iv or ♭VI: the chord keeps one note of X
and bends the other two by a sixth-step each (§6.1).

**Facts** [Theorem]:
- Distance 2 from the original triad, one common tone; π(I) = Cg, π(ii) = vDg, π(iii) = vEg, π(IV) = Fg, π(V) = Gg,
  π(vi) = vAg.
- The six projections of a key are the golden roots t + {0, 5, 11, 15, 21, 26}; they pair into golden-circle neighbours
  along L: (Cg, vEg), (Fg, vAg), (Gg, vBg = π(Bm), not diatonic). So I–iii and IV–vi colour pairs are circle steps.
- Each colour chord is also a pivot into the silver-third keys (§6.3): the same Fg is golden IV in C and golden ii in ^Eb.

**Roughness** [Measurement]: every golden triad is the same shape, so in this model its roughness is fixed up to register:
Cg 1.498 at C4 against C 1.319 and Cm 1.342. Root by root in close position the golden version is rougher than the
diatonic triad on every degree except vii (Bdim 1.201, Bg 1.120) [bl §15]. These are same-root values. For the colour
chords themselves (the projections π(X)) the rise is 0.179–0.200 on I–vi: C 1.319 → Cg 1.498, Dm 1.238 → vDg 1.417,
Em 1.149 → vEg 1.333, F 1.090 → Fg 1.284, G 1.020 → Gg 1.220, Am 0.977 → vAg 1.175; and Bdim 1.201 → ^Bbg 1.135
(its nearest golden triad) is smoother [Measurement, computed for ch38].

**Demo D11**: `C:1 Fg:1 G7:1 C:1 Am:1 vAg:1 Dm:1 Gg:1 C:2` (I – golden IV – V7 – I – vi – golden vi – ii – golden V – I).

---

## 10. Further techniques

### 10.1 Golden planing is three-key polytonality [Theorem, bl §15]
Harmonize every note x of a C major line with the golden triad {x, x + 11, x + 22} (melody in the root): Cg, Dg, Eg, Fg,
Gg, Ag, Bg for C … B. The second voice is the line in **vE major**, the third in **^G major**. The three keys lie on three
layers (0, 2, 1), share no note pairwise and together use 21 pitch classes. With the melody on top (as the fifth) the
chords are vFg, vGg, vAg, vBbg, vCg, vDg, vEg. **D14** `Cg:0.5 Dg:0.5 Eg:0.5 Fg:0.5 Gg:0.5 Ag:0.5 Bg:0.5 Cg:0.5 C:2`.
Roughness is constant up to register [Measurement]. Its Western ancestor is parallel organum and Debussy's planing; its
difference is that the three lines are in three keys that cannot share a note.

### 10.2 Golden pedals and drones [Theorem + Measurement, bl §16]
- **Each pitch class lies in exactly three golden triads, consecutive on the golden circle**: C ∈ Cg, ^Abg, vFg (circle
  positions 0, −1, −2), since x ∈ G_r iff r ∈ {x, x − 11, x − 22}. So a C pedal sustains under a three-chord walk of the
  circle: **D15** `C:1 Cg/C:1 ^Abg/C:1 vFg/C:1 ^Abg/C:1 Cg/C:1 C:2`.
- Measured roughness with a C3 pedal under close triads from C4 (harmonic tones): C 1.956, F/C 1.859, Am/C 1.489,
  Ab/C 1.605, Fm/C 1.901; Cg 2.292, ^Abg/C 1.733, vFg/C 2.145; vEg (no C) 2.312. (^Abg/C measuring below C/C is a
  register effect: it is voiced from ^Ab4, higher than the others; compare chords only at equal register.)
- Western triads of C major over a Cg drone (C3 vE3 ^G3) are rougher than over a C major drone in every case (by 0.18 to
  1.00 in the model): C 7.130 vs 6.141, G 5.783 vs 4.908, Am 5.594 vs 5.155 … So a golden drone colours a Western progression
  at a measurable cost on harmonic instruments; on the digital golden spectrum (laboratory) the order reverses: Western triads measure smoother over the Cg drone,
  by 0.55 (Em) to 1.36 (F) (measured for ch37).

### 10.3 Approach chords: the golden Neapolitan and leading-tone chord [Theorem, bl §17]
- **No Western chord resolves into a golden triad by semitone or whole-tone motion**: such motion keeps each voice on its
  layer, and a golden triad needs three. Any Western → golden move bends at least two voices by sixth-steps (minimum 2).
- Of the 26 chords that resolve into Cg with every voice moving by a semitone or holding, exactly 6 are golden and none is
  Western: vEg (B → C), ^Abg (^Ab → ^G), ^Gg (B → C and vEb → vE), vFg (two voices fall), **C#g** (all three fall: the
  **golden Neapolitan**, each voice an exact golden apotome) and **Bg** (all three rise: a golden "leading-tone triad").
  blending.py §17 prints vEg → Cg as the "golden leading-tone chord" (one voice, B → C, as the Western leading tone);
  the two names mean different things: vEg moves only the leading tone, Bg moves every voice up.
  The other 20 are not tertian.
- **No golden augmented sixth**: the intervals of golden triads and sevenths are 3, 11, 14, 22, 25, 33 sixth-steps; none
  is 34 or 2, so none expands to an octave (or contracts to a unison) by contrary sixth-steps. The same holds for equal
  contrary steps of a third-step or a semitone (intervals 4, 32, 6, 30: none occurs). [Negative result.] With unequal
  steps the golden seventh does reach an octave (C falls one sixth-step to vC while B rises two to vC); that is a
  different, asymmetric resolution, not an augmented-sixth analogue.
- **D16** (key C golden7): `Cg:1 C#g:1 Cg:1 vEg:1 Cg:1 C:2` (golden Neapolitan, leading-tone exchange, release to C).

### 10.4 Sequences [Exhaustive + Proposal, bl §18]
- **Golden giant steps.** Coltrane's major-third cycle C → Ab → E → C consists of same-quality pairs a major third apart,
  so by the quality theorem each move has exactly one strict golden passing chord on the upper root: C – Cg – Ab – Abg –
  E – Eg – C. The three golden chords sit 12 circle positions apart (0, 12, −12): the golden circle divided in three, as the
  octave is. **D17** `C:1 ~:1 Ab:1 ~:1 E:1 ~:1 C:2`.
- **Golden-third key cycle.** Keys a golden third apart, C → vE → ^G → B → vEb → ^F# → Bb …: three steps make 33 ≡ −3, a
  semitone down on the same layer; 36 steps visit all 36 major keys. Each step can be taken through two projections,
  C → Cg → vEg → vE, costing 2 + 3 + 2 = 7, which equals the direct tonic distance (moves C −4, E −1, G +2): the golden route
  is a **geodesic**, every voice monotone (Cg, vEg and Eg are geodesic hinges of C → vE, Eg at cost 4 + 3; bl §18). Likewise C → Cg → ^Abg → ^Ab.
  **D18** `C:1 Cg:1 vEg:1 vE:1 vEg:1 ^Gg:1 ^G:1 ^Gg:1 Bg:1 B:2`.
- **Hinges by transposition.** Of the 35 transpositions of a major tonic, only the two sixth-step lifts (±1) have no
  golden geodesic hinge [Exhaustive, computed for ch37].
- **Layer-prism sequence.** A ii–V–I repeated a sixth-step higher each time divides the semitone into three:
  **D19** `Dm7:0.5 G7:0.5 C:1 ^Dm7:0.5 ^G7:0.5 ^C:1 vEbm7:0.5 vAb7:0.5 vC#:1 Ebm7:0.5 Ab7:0.5 C#:2`.

### 10.5 Canon at the golden third [Theorem; weak]
A follower 11 sixth-steps above a stepwise C major leader, one note behind, sounds the interval 11 − (leader's step):
17, 14, 11, 8 or 5 sixth-steps for steps of −6, −3, 0, +3, +6. Only repeated notes give golden thirds; the canon mostly
yields non-golden intervals. Ranked last.

---

## 11. Audio demos (all parsed and expanded by SongMap, bl §20)

| Id | Technique | Key | Harmony |
|---|---|---|---|
| D1 | sixth-step lift | C major | `C:1 F:0.5 G7:0.5 C:1 ^C:1 ^F:0.5 ^G7:0.5 ^C:2` |
| D2 | limma lift through its golden midpoint | C major | `C:1 F:0.5 G7:0.5 C:1 ^Cg:1 vC#:1 vF#:0.5 vG#7:0.5 vC#:2` |
| D2b | the same, engine-chosen | C major | `C:1 ~g:1 vC#:2` → C ^Cg vC# |
| D3 | comma pump (13 circle steps) | C major | `C:1 Cg:0.5 ^Abg:0.5 vFg:0.5 C#g:0.5 ^Ag:0.5 vF#g:0.5 Dg:0.5 ^Bbg:0.5 vGg:0.5 Ebg:0.5 ^Bg:0.5 vAbg:0.5 Eg:0.5 ^Cg:1 ^C:2` |
| D4 | limma pump (10 circle steps) | C major | `C:1 Cg:0.5 vEg:0.5 ^Gg:0.5 Bg:0.5 vEbg:0.5 ^F#g:0.5 Bbg:0.5 vDg:0.5 ^Fg:0.5 Ag:0.5 vC#g:1 vC#:2` |
| D5 | apotome pump (3 circle steps) | C major | `C:1 Cg:1 ^Abg:1 vFg:1 C#g:1 C#:2` |
| D6 | projection pivot to ^Eb (IV = ii) | C major | `C:1 Am:1 F:1 Fg:1 ^Fm:1 ^Bb7:1 ^Eb:2` |
| D7 | projection pivot to vA (vi = I) | C major | `C:1 F:1 G:1 Am:1 vAg:1 vA:1 vE7:1 vA:2` |
| D8 | projection pivot to ^Eb (V = iii) | C major | `C:1 Dm:1 G:1 Gg:1 ^Gm:1 ^Ab:1 ^Bb7:1 ^Eb:1` |
| D9 | two golden chords across layers | C major | `F:1 ~g:0.5 ~g:0.5 ^Em:2` → F vFg ^Eg ^Em |
| D10 | hinge vi → ^I | C major | `Am:1 ~g:1 ^C:2` → Am vAg/A ^C |
| D11 | golden colour chords | C major | `C:1 Fg:1 G7:1 C:1 Am:1 vAg:1 Dm:1 Gg:1 C:2` |
| D12 | golden Ionian | C major | `F:1 Dm:1 Cg:1 vEg:1 Dm:1 Cg:2` |
| D13 | (3, 2) hybrid | C major | `F:1 Dm:1 Fg:1 vAg:1 Am:1 Fg:1 F:2` |
| D14 | golden planing | C major | `Cg:0.5 Dg:0.5 Eg:0.5 Fg:0.5 Gg:0.5 Ag:0.5 Bg:0.5 Cg:0.5 C:2` |
| D15 | golden pedal | C major | `C:1 Cg/C:1 ^Abg/C:1 vFg/C:1 ^Abg/C:1 Cg/C:1 C:2` |
| D16 | golden Neapolitan | C golden7 | `Cg:1 C#g:1 Cg:1 vEg:1 Cg:1 C:2` |
| D17 | golden giant steps | C major | `C:1 ~:1 Ab:1 ~:1 E:1 ~:1 C:2` → C Cg Ab Abg E Eg C |
| D18 | golden-third key cycle | C major | `C:1 Cg:1 vEg:1 vE:1 vEg:1 ^Gg:1 ^G:1 ^Gg:1 Bg:1 B:2` |
| D19 | layer-prism sequence | C major | `Dm7:0.5 G7:0.5 C:1 ^Dm7:0.5 ^G7:0.5 ^C:1 vEbm7:0.5 vAb7:0.5 vC#:1 Ebm7:0.5 Ab7:0.5 C#:2` |
| D20 | F harmonic minor ↔ C golden7 | F minor | `Fm:1 Db:1 Abaug:1 C:1 Cg:1 C#g:1 vFg:1 ^Abg:1 Cg:1 C:1 Fm:2` |
| D21 | escalator as passing harmony | C major | `C:1 G7:1 C:1 ~g:0.5 ~g:0.5 D:1 A7:1 D:2` → … vC#g ^C#g D … |

The test harness in bl §20 uses `tuning: 36edo`, parts `organ: hold` and `low: bassline`, and prints the resolved chord
symbols. For textbook use, add instruments and melodies following AUTHORING §4; keep golden-home sections on
`clean/golden_pad` or `clean/glass` only as the laboratory.

---

## 12. Ranking

| Rank | Technique | Grounding | Why it matters |
|---|---|---|---|
| 1 | Projection pivots (silver-third keys) | exhaustive + geodesic theorem | real pivot-chord modulation between layers; three pivots per key pair; cost 4, monotone |
| 2 | Comma pump / golden circle as key engine | theorem (d = chain distance) | smoothest possible long modulation; one note, one sixth-step per step |
| 3 | Golden midpoint of the limma lift | theorem | a two-chord key change through gold; the comma lift cannot do it |
| 4 | Golden-third key cycle via projections; golden giant steps | exhaustive (geodesic) + quality theorem | sequences with golden chords exactly on the smoothest paths |
| 5 | Golden colour chords by projection | theorem | modal mixture with one common tone and two sixth-step bends |
| 6 | Golden planing (three-key polytonality) | theorem | a simple, striking texture with a clean explanation |
| 7 | Golden pedals | theorem + measurement | three circle chords over every pedal note |
| 8 | Golden Neapolitan / leading-tone triads | theorem; function is hypothesis | approach chords inside golden keys |
| 9 | F harmonic minor ↔ C golden7 | exhaustive | the best Western partner of a golden key |
| 10 | Hybrid scales (golden Ionian, (3, 2) hybrids) | exhaustive | colour collections; not well-formed |
| 11 | Passing keys (escalator as keys) | exhaustive (negative) | the escalator is voice leading, not keys |
| 12 | Centroid scales | exhaustive (mostly negative) | the silver centroid is maximally even; the golden ones are irregular |
| 13 | Canon at the golden third | theorem (negative) | rarely produces golden intervals |

---

## 13. Proposed chapter outline: Part "Golden harmony beyond passing"

Placement: a new Part after Part VII (after Chapter 33). Because chapter numbers come from the ids (`chNN`), inserting
four chapters means renumbering the current ch34–ch39 to ch38–ch43; alternatively the ids ch40–ch43 can be used with the
Part placed at the end of the numbered chapters. Ids below assume insertion as ch34–ch37.

**Chapter 34. Modulation by golden intervals** (`ch34`)
| id | title |
|---|---|
| `units` | The comma, the limma and the apotome as key changes |
| `lifts` | Lifting a key: sixth-steps and third-steps |
| `midpoint` | The golden midpoint of the limma lift |
| `comma-pump` | The comma pump: thirteen steps to ^C |
| `golden-circle-keys` | The golden circle as a modulation engine |
| `key-map` | A map of the 36-ET keys |

**Chapter 35. Golden pivot chords** (`ch35`)
| id | title |
|---|---|
| `projection` | The golden projection of a triad |
| `plr` | Neo-Riemannian moves through the golden lens |
| `silver-third-keys` | Keys a silver third apart |
| `hinges` | Golden hinges and the passing engine across layers |
| `reinterpretation` | One golden chord, three meanings |
| `golden-western-keys` | Between golden keys and Western keys |

**Chapter 36. Golden modes and hybrid scales** (`ch36`)
| id | title |
|---|---|
| `golden-modes` | The modes of golden7 and golden13 |
| `evenness` | Maximal evenness: golden13 as the golden diatonic of 36-ET |
| `inflections` | Golden inflections of the major scale |
| `centroid-scales` | Centroid scales |
| `hybrid-limit` | The hybrid limit |
| `colour-chords` | Golden colour chords |

**Chapter 37. Blending techniques** (`ch37`)
| id | title |
|---|---|
| `golden-planing` | Golden planing and three-key polytonality |
| `pedals-drones` | Golden pedals, Western drones |
| `approach` | Approach chords: the golden Neapolitan |
| `sequences` | Golden sequences: giant steps and the golden-third cycle |
| `passing-keys` | Bridge scales and passing keys |

---

## 14. Open questions

1. **Perception of the two lifts.** Does the limma lift with its golden midpoint (C – ^Cg – vC#) sound smoother or more
   "inevitable" than the plain comma lift (C – ^C)? Hypothesis to test.
2. **Projection pivots by ear.** Is Fg heard as golden IV of C or golden ii of ^Eb, and how quickly does the continuation
   decide? A probe-tone study (§7.4) could measure it.
3. **Function of the comma pump.** Does a 13-step circle walk register as a modulation by a sixth-step, or as a drift? What
   pacing (Fibonacci bar lengths, GOLDEN_THEORY §3.4) makes the arrival on ^C feel like a cadence?
4. **Silver projections.** Every Western triad has a nearest silver triad too (silver also has one note per layer). Do
   silver projections give their own pivot relation between keys, and how does it combine with the golden one? The
   generator-10 MOS C D E ^F ^G vA vB with 5 silver triads, an inflection of C major, looks like the silver counterpart of
   golden7 (GOLDEN_THEORY §6, question 1).
5. **Golden-key pivots with sevenths.** Extend π to seventh chords (Cmaj7 → Cg7 is distance 2): do seventh-chord keys
   give more than three shared projections?
6. **Exact tuning.** In exact golden tuning (`golden_exact`, planned) 13 chain steps land exactly one golden comma higher,
   30.17 c, which is 3.16 c below 36-ET's ^C; each of the 13 per-note moves is an exact golden comma. Is the 3.16 c gap
   between a golden-exact arrival and a 36-ET ^C major audible, for example against a sustained reference?
7. **Hybrid scales with 13 notes.** The 7-note hybrid limit is (3, 2) / (2, 3). What is the limit for 13-note scales
   (C(35, 12) ≈ 8.3 × 10⁸ subsets; needs a smarter search)?
8. **Passing-key duration.** The criterion of §7.4 is a proposal; it needs listening data.
9. **Naming.** Names for the golden7 modes (chain positions +3 … −3; the textbook proposes b|a, §8.1), for the golden Ionian, and for "projection" (the
   book already uses *shadow* for vCg → C, GOLDEN_THEORY §4.1, a different relation: the shadow is a sixth-step *below* the
   root, the projection keeps the root of a major triad).

---

## 15. Elastic and ornamental strategies

Textbook Chapter 39 (*Elastic harmony: strategies from tradition*). Every number is printed by
[reference/golden/elastic.py](../reference/golden/elastic.py) (`.venv/Scripts/python reference/golden/elastic.py`,
sections **[el §n]**). Voiced chords are tuples of absolute sixth-steps (MIDI × 3); distances are L1 with the voice
assignment fixed unless stated (pc-set distances use `blending.vl`).

### 15.1 The betweenness framework [Theorem, el §1]
For one voice x → g → y (all distinct) exactly one point lies between the other two: g (**passing**), y
(**overshoot**: the voice goes past its target and returns) or x (**escape**: it first moves away). Degenerate cases:
g = x (suspension), g = y (anticipation), x = y (neighbour). For voiced chords, the detour excess is
d(X,G) + d(G,Y) − d(X,Y) = Σ (0 for passing voices, 2|g−y| for overshooting, 2|g−x| for escaping ones). Chapter 12's
(a, b) table of non-chord tones is this classification. A chord is *uniform* when all moving voices share one type.

### 15.2 Overshoot and settle [Exhaustive + Theorem, el §2–§6]
**Definition.** For X → Y, G = Y + E with each moving voice continuing past its target by |E_i| ∈ {1, 2, 3} in its own
direction and held voices fixed (*full*); *partial* if some moving voices land (E_i = 0) and at least one overshoots.
Equivalently Y lies on a geodesic from X to G; excess = 2 d(G, Y). (Which overshoot order is golden in the parallel
rule is an exhaustive check; the three-stage settles (4 into C: three with amplitudes 2, 1, 1 and one with 2, 2, 1;
4 into C minor: Bg–^Gg–^Bg, vEg–^Gg–vCg, Eg–^Cg–vCg at 2, 1, 1 and Bg–vAbg–^Bg at 2, 2, 1) were enumerated
separately for ch39 and are not printed by elastic.py.)

- **Overshoot table of C major** (26 approach patterns of root/third/fifth): 8 patterns have a full golden overshoot
  (9 with partial), and the settle is always the smoothest voice leading back. Cg (0, −1, +1; root held, third from
  above, fifth from below), vCg (−1, −2, 0), ^Cg (+1, 0, +2), Eg (−2, 0, +2), vEg / A♭g / vA♭g (down, down, up),
  ^Eg (−1, +1, +3), ^Bg (−2, −3, −1; all from above), vC♯g (+2, +1, +3; all from below). C minor: also 8 / 9.
- **Parallel rule** [Theorem, all 24 major/minor triads]: when all voices move one way, the only full golden overshoot is
  π(Y) planed **two** sixth-steps in the direction of motion, and the only additional partial one is π(Y) planed **one**
  (C rising: vC♯g, ^Cg; falling: ^Bg, vCg; Cm rising ^Cg, Cg; falling Bg, ^Bg), independent of the leap size. Proof:
  overshoots of 1, 2, 3 one way sit on three layers, so a full golden overshoot uses each once; of the six orders
  (2, 1, 3) is golden, (1, 2, 3) bronze (A♭T13), (3, 1, 2) silver (C♯s), three are not tertian.
- **Double duty.** vCg (partial overshoot of every falling leap into C) is the strict passing chord of the smooth V → I;
  ^Bg (full overshoot from above) is the last chord of the natural path B♭ – vBg – ^Bg – C.
- **Cg as overshoot** needs converging voices; sources among the 24 triads: C (voice exchange), F (A → E, F → G), Fm, Cm,
  A♭, Am.
- **No proportional overshoot** [Theorem]: P₄ = Y + d (the uniform path stretched one step, d = (Y − X)/3) is never
  golden if X is major, minor or augmented, for any layer-0 Y and any motion size. Proof: X ≡ 4Y − 3G (mod 36), so in
  semitones X ≡ −g + {4a, 4b + 1, 4c + 2} (mod 12): three different residues mod 4, while major, minor and augmented
  triads repeat a residue. Diminished, sus2 and sus4 sources do admit golden P₄ (brute force). By reversal the uniform
  backswing X − d before a major/minor Y is never golden. Census: 0 golden P₄ in 2,616 voice leadings (each voice up to an
  octave). Golden overshoot is necessarily uneven.
- **No golden mirror** [Theorem]: if Y lies on one layer and Y + E is golden, Y − E is not (0 of 1,320 assignments).
  Proof: σ_i + τ_i constant mod 6 forces τ = 2 − σ, then 2Y_i is constant mod 36. Hence no undershoot of a golden
  overshoot (every voice reversing, smaller amplitude) is golden: 45 candidates for C and 45 for Cm, none tertian.
- **Relaxed damped settles** [Exhaustive, |E| ≤ 3]: 11 two-stage settles Y + E₁ → Y + E₂ → Y into C (11 into Cm), both
  golden, each with exactly one voice reversing, e.g. ^Bg → Cg → C (fifth vG → ^G → G; path 8 against 6). Four
  three-stage settles into C have a voice swinging twice; three of them with amplitudes 2, 1, 1 (vA♭g → ^Bg → Cg → C,
  A♭g → ^Eg → Cg → C, vC♯g → ^Eg → ^Cg → C).
- **Spring metaphor** [computation]: decay 1/φ per half swing ⇔ ζ = ln φ / √(π² + ln² φ) = 0.1514, whose first overshoot
  of a fourth would be 9.27 sixth-steps; the musical 2 sixth-steps on a fourth (0.133) corresponds to ζ = 0.540, next
  swing 1.8 % of the step.

### 15.3 Golden appoggiatura chords [Exhaustive, el §7]
- Distances of the 36 golden triads to C: 2 (Cg), 3 (vCg, ^Cg), 4 (Eg), 5 (vEg, ^Eg, ^A♭g), 6 (six chords), then 7, 8, 9
  (six), 12 (six), 15 (six), 18 (three). Cm has the same distribution (vCg at 2).
- Ten golden triads resolve into C with every voice moving ≤ a semitone; ^Cg and vC♯g fall in every moving voice, vCg
  and ^Bg rise: the overshoot chords of 17.2.
- **The cadential six-four in 36-ET**: C/G – vCg/G – vE♭T13/G – G (strict path of the upper voices G3 C4 E4 → G3 B3 D4) is
  the golden authentic cadence reversed; vCg/G serves both I⁶₄ → V (falling, cost 6) and V → I (rising).
- Roughness [Measurement, four notes incl. bass, el §14]: Cg 2.292 / C 1.956 (C3 C4 …); Gg 2.903 / G 2.604 (G2 G3 …);
  vCg/G 2.965 / C/G 2.640.

### 15.4 Suspensions [Theorem + Exhaustive, el §8]
- Suspensions using only layer-0 notes are never golden. A golden vertical made of held golden notes and moved Western
  notes has exactly two held notes and one moved; preparation and suspension are golden-circle neighbours.
- **Golden double suspensions into C** (preparation → suspension → C): vEg → Cg (retardation + suspension), vA♭g → Eg
  (suspension + retardation), C♯g → vFg (two suspensions; the golden minor plagal vFg/C → C), Fg → vAg (two suspensions),
  A♭g → vCg (two retardations), vBg → Gg (two retardations). Six into Cm, cheapest A♭g → vCg → Cm.
- When the suspension chord is π(Y), the resolution is always one suspension and one retardation (projection bends).
- Staggered: Cg → C(^5) → C, Cg → C(v3) → C; roughness C(^5) 2.262, C(v3) 2.003 (C3 C4 …): the golden fifth carries
  most of the roughness [Measurement].
- Cg over a moving bass resolves to C (2), Cm (3), Caug (3), A♭ (4): with bass A → Am7, B → Cmaj7/B, B♭ → C7/B♭; A♭ →
  A♭maj7, A → Am7♭5; F → Fm7, G → A♭maj7/G.
- Chains: ^Ag → C♯g → vFg → ^A♭g → Cg → C (falling semitones in turn) and vE♭g → Bg → ^Gg → vEg → Cg → C (rising).

### 15.5 Anticipation and escape chords [Exhaustive within a whole tone per voice, el §9–§10]
- Smooth V → I, IV → I, I → IV, I → V: the only golden chord on a geodesic is the strict passing chord; no uniform
  overshoot, escape or anticipation chord exists; all others are mixed with excess ≥ 2 (V → I: 36 mixed chords in ten
  classes).
- V → vi and IV → V (all voices one way): anticipation + passing chords with excess 0 (Cg = ^G3 C4 vE4 in V → vi;
  Dg = vF♯3 ^A3 D4 in IV → V); uniform escape (^F♯g, ^Eg) and overshoot (^Ag, vA♭g) chords with excess 12.
- Golden cambiata [Proposal]: V → vA♭g (passing) → ^Ag (overshoot) → vi, motion 6 + 15 + 6 = 27 against 15.

### 15.6 Neighbour chords [Exhaustive, el §11]
- 28 golden voicings within a whole tone of C4 E4 G4: 10 upper, 10 lower, 8 split; nearest Cg (split, 2), vCg (lower, 3),
  ^Cg (upper, 3).
- Golden pedal six-four: vFg/C = C vF ^A♭ is P₂ of C → F/C (motions 0, 2, 4 against 0, 3, 6). Roughness with pedal 2.360
  against F/C 2.022 [Measurement].
- 98 golden double neighbours; the cheapest C – ^Bg – vC♯g – C (total 24) is the pair of full overshoots.

### 15.7 Reharmonization [Theorem + Exhaustive, el §12]
- Each pitch class x lies in exactly three golden triads G_x, G_{x−11}, G_{x−22}, at consecutive circle positions
  23x, 23x − 1, 23x − 2.
- Cheapest move between golden harmonizations of two melody notes s semitones apart, s = 0 … 6: 0, 3, 12, 5, 3, 3, 12
  (semitone = circle step; major third and fourth = planing; whole step and tritone expensive).
- Ode to Joy (30 notes, cadences G in bar 4 and G – C at the end), total pc voice-leading: diatonic only 162; golden or
  diatonic, smoothest 162 with 13 golden notes (vAg → Fg is the circle-step image of Am → F, π∘L); diatonic charged 4:
  180 with 20 golden (the audio example); golden only 210 (25 golden + 5 fixed); golden only without cadences 204.

### 15.8 Further strategies [path facts exhaustive by the engine, use Proposal; el §13]
- **Golden backdoor**: Fm – B♭ – vBg – ^Bg – C (natural path; ^Bg → C rises in every voice, 2 + 3 + 1).
- **Golden chromatic-mediant cadence**: A♭ – Cg/A♭ – C (strict A♭ – {C ^E♭ vA♭} – Cg/A♭ – C) and E – Eg – C (strict
  E – Eg – ^GT13/E – C): the golden passing chord of each mediant pair is a projection.
- **Golden pedal six-four**: C – vFg/C – C (17.6).
- **Cadential palindrome**: C/G – vCg/G – vE♭T13/G – G – vE♭T13/G – vCg/G – C.

### 15.9 Audio (textbook/audio/ch39, all expanded by SongMap with explicit voicings)
`overshoot_def`, `elastic_phrase`, `damped_settle`, `appoggiatura_def`, `suspensions_def`, `anticipation_escape`,
`neighbour_def`, `reharm_ode`, `cadences_extra`.

### 15.10 Open questions
1. Does the ear prefer the partial overshoot (settle 3) or the full one (settle 6) after a leap, and does the preference
   depend on the leap size, as gap-fill would suggest?
2. Is a one-beat overshoot heard as an ornament of the arrival or as a chord of its own? What duration ratio (the
   C. P. E. Bach half-value rule is a starting point) makes it an appoggiatura?
3. The relaxed damped settles let only one voice swing. With overshoots up to a whole tone (|E| ≤ 6) do two-voice swings
   appear, and are they audible as damping?
4. Golden reharmonization favours semitone, major-third and fourth melodic steps. Which melodies (chromatic, pentatonic,
   golden7) does it suit best, measured by the cost table?
5. Extend overshoot to seventh chords (G7 → C, Cmaj7 targets) and to golden sevenths as overshoot chords.

---

## 16. Golden melody across scales

Textbook Chapter 40 (*Golden melody across scales*). Every number is printed by
[reference/golden/melody.py](../reference/golden/melody.py) (`.venv/Scripts/python reference/golden/melody.py`, sections
**[me §n]**; §7 expands all 17 SongMap examples of `textbook/audio/ch40` and checks every melody and harmony note against
the scale claimed for its bars: 0 notes outside). Scales are on C: golden pentatonic A = C D vF ^G ^A (chain −2, 0, 2, 4,
6), pentatonic B = C# vE vF# ^Ab B (its complement in 35), golden7 = [−3, 3], 35 = [−3, 6], 53 = [−6, 3], golden10
(SongMap) = [−4, 5], golden13 = [−6, 6].

### 16.1 The palette [Theorem + Exhaustive, me §1]
- **The n − k rule** [Theorem]: in a window of n consecutive chain notes the interval of chain distance k occurs exactly
  n − k times (in the golden pentatonic, a window of golden fifths, chain distance 2m occurs 5 − m times). So the interval
  content of every golden scale is read off one table:

| k | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 36-ET ic | 11 | 14 | 3 | 8 | 17 | 6 | 5 | 16 | 9 | 2 | 13 | 12 | 1 | 15 |
| exact (c) | 366.91 | 466.18 | 99.27 | 267.64 | 565.45 | 198.54 | 168.37 | 535.28 | 297.81 | 69.10 | 436.01 | 397.08 | 30.17 | 496.35 |

- **Western-sized intervals** follow: a whole tone (k = 6, 198.54 c) needs n ≥ 7 (golden7 has 1, the decatonic 4,
  golden13 7); a minor third (k = 9, 297.81 c) n ≥ 10 (decatonic 1, golden13 4); a major third (k = 12, 397.08 c) n = 13
  (golden13 1, B♭–D); the first near-fourth (k = 15, 496.35 c, 1.69 c below 4/3) lies outside every golden scale up to 13
  notes. **No golden scale of up to 13 notes contains a fourth or fifth**; the nearest is the golden fifth (733.82 c,
  31.86 c wide of 3/2) and its inversion the golden fourth (466.18 c).
- **Character table** (36-ET steps; semitone pairs = steps of 3 sixth-steps, exact 99.27 c in chain scales):

| Scale | Steps | Semitone pairs | Golden 3rds/5ths (pairs) | Golden triads | Golden 7ths | Western triads |
|---|---|---|---|---|---|---|
| golden3 | 11 11 14 | 0 | 2 / 1 | 1 | 0 | 0 |
| golden4 | 11 11 3 11 | 1 (^G–^A♭) | 3 / 2 | 2 | 1 | 0 |
| golden pentatonic | 6 8 8 6 8 | 0 | 0 / 4 | 0 | 0 | 0 |
| golden7 | 3 8 3 8 3 8 3 | 4 | 6 / 5 | 5 | 4 | 0 |
| decatonic (35, 53) | 3 and 5 | 7 | 9 / 8 | 8 | 7 | 0 |
| golden13 | 3 and 2 | 10 | 12 / 11 | 11 | 10 | 0 |
| silver13 | 1, 2, 3, 4 | 10 | 2 / 4 | 0 (7 silver, 7 bronze) | 0 | 0 |
| golden Ionian C D vE F ^G A B | 3–7 (five sizes) | 1 (B–C) | 3 / 2 | 2 | 1 | F, Dm (+ B dim) |
| (3,2) hybrid C ^C D E F vA A | 1–11 (six sizes) | 1 | 3 / 2 | 2 | 1 | F, Dm, Am |
| decatonic 44 | 3 and 4 | 4 | 8 / 6 | 6 | 4 | 0 (4 fourths, 3 tritones) |

- **Leaning pairs**: golden7 B–C, C–C♯, vE–vF, ^G–^A♭ (three layer clusters {B C C♯}, {vE vF}, {^G ^A♭}); 35 adds C♯–D,
  vF–vF♯, ^A♭–^A (clusters {B C C♯ D}, {vE vF vF♯}, {^G ^A♭ ^A}); every golden scale from golden7 up has both B and C♯
  around C, and from golden7 up a semitone step keeps the layer while every other step changes it (the golden pentatonic is the exception: its whole tone C–D also keeps the layer). The hybrids contain sixth-step "steps" (C–^C, vA–A, 33.33 c), inflections rather than steps.

### 16.2 The golden pentatonic [Theorem + Exhaustive, me §2]
- Steps 267.64 c × 3 and 198.54 c × 2 (36-ET 8 and 6), **chroma = the golden limma** (69.10 c, chain span 10, as for
  golden10). Anhemitonic, and without golden thirds or sixths: its intervals are golden fifths/fourths (4 pairs), 267.64
  (3), whole tones (2) and 535.28 c (1). Generic intervals: seconds 6/8, thirds 14/16, fourths 20/22, fifths 28/30.
- **Five modes** on C (b|a = golden-fifth-chain notes below|above the tonic; each lowers one note of the previous by a
  limma): 4|0 C vE♭ ^F ^G B♭ (brightness 76), 3|1 C vE♭ vF ^G B♭ (74), 2|2 C vE♭ vF ^G ^A (72, symmetric about C),
  **1|3 C D vF ^G ^A** (70, pentatonic A, symmetric about vF), 0|4 C D vF vG ^A (68, no golden fifth on C).
- **No golden triad** (a golden triad spans chain r, r − 1, r − 2, both parities). Each of the four golden fifths implies
  exactly one golden triad: C–^G → Cg, vF–C → vFg, ^A–vF → ^Ag, D–^A → Dg, and every missing third (vE, ^A♭, C♯, vF♯)
  lies in pentatonic B. Consecutive chords Cg – vFg – ^Ag – Dg share exactly the melody's common tone (C, vF, ^A): the
  **common-tone chain**. Western mirror: C D E G A contains the triads C and Am.
- Transposition: pentatonic A and T_s(A) share 0 notes if c(s) is odd and 5 − |c(s)|/2 if even (a golden fifth keeps 4, a
  golden third 0). A and B are disjoint and A ∪ B = 35. Golden pentatonics inside: golden7 0, 35 2, 53 2, golden13 5
  (the only other MOS 5-subset of golden13 is the cluster B♭ B C C♯ D). A golden pentatonic shares at most 2 notes with
  any Western major, minor (natural, harmonic, melodic) or pentatonic scale on any of the 36 tonics.

### 16.3 golden7 and the decatonic [Theorem + Exhaustive, me §3]
- Degree chords: golden7 on 1-3-5 gives 5 golden triads (not on ^G, B); the decatonic on 1-4-7 gives 8 (not on ^G:
  ^G B D, or on B: B D vF♯; both contain the one minor third B–D). Proof: a decatonic step is chain +3 (small) or −7
  (large); three steps make the golden third (chain −1) iff they contain exactly one large step, which 9 of the 10
  three-step windows do.
- **Inversion**: x → −x maps golden7 and golden13 to themselves and **exchanges 35 and 53** (D, vF♯, ^A ↔ B♭, ^F♯,
  vE♭); 35 is self-inverse only about the axis 1.5 sixth-steps (x → 3 − x, C ↔ C♯), pentatonic A about vF (x → 28 − x).
  Inversion maps golden triads to golden triads (Cg ↔ vFg, C♯g ↔ vEg, ^A♭g fixed), so a golden7 phrase and its exact
  mirror can be harmonized by mirrored progressions.
- Real chain sequences: T25 keeps n − 1 notes (golden7: B → ^A, −5; 35: B → ^B♭, −2; golden13: B♭ → ^B♭, +1); T11 (up a
  golden third): golden7 C♯ → vE♭ (+5), 35 D → vE♭ (+2), golden13 D → vD (−1). A motif built on a golden triad and the
  scale note above its root stays in 35 under T25 for roots Cg, ^A♭g, vFg, C♯g; at ^Ag it must bend (tonal sequence).
- Approaches to C (golden triad holding the approach note; VL to Cg): B (+3): vEg 3 in golden7 and 35; in 53 also ^Gg
  (6) and Bg (9, all voices rise); C♯ (−3): C♯g 9 (all fall); vE (−11) and ^G (+14): Cg itself.
- Western (12-ET) cells live inside the layer clusters only: of C major's three-note cells within a fourth, exactly the
  chromatic ones (semitone + whole tone) fit in 35 (e.g. B C D and the turn D C B C); do-re-mi does not (no major third).

### 16.4 Common-tone subsets [Theorem + Exhaustive, me §4]
- Inclusions on C: golden3 ⊂ golden4 ⊂ golden7 ⊂ 35, 53, golden10 ⊂ golden13; pentatonic A ⊂ 35 ⊂ golden13;
  **35 ∩ 53 = golden7, 35 ∪ 53 = golden13**; golden13 − 35 = vE♭g, golden13 − 53 = Dg.
- **Theorem (window overlap)**: for n ≤ 18, golden-n on C and on s share max(0, n − |c(s)|) notes (the two windows then
  span at most 36 chain positions; it fails for larger n, e.g. n = 30, c = 10 gives 24, not 20; checked for n = 3, 4, 7,
  10, 13, all 36 s). 53 shares at most 3 notes with major, natural, harmonic and melodic minor keys and 2 with pentatonics. Chain step (vE, ^A♭): n − 1; golden fifth: n − 2; apotome (C♯, B): n − 3; limma (vC♯, ^B): golden13 keeps 3 = a
  golden triad (vE♭g resp. Dg), every smaller scale 0; **sixth-step (^C, vC): 0 for every golden scale**.
- A golden triad lies in n − 2 keys of golden-n: Cg in 2 golden4, 5 golden7 (C, vE, ^G, ^A♭, B), 8 decatonic and 11
  golden13 keys; no Western scale holds two of its notes.
- Golden ∩ Western on C: golden7 ∩ C major = {C, B}; 35 ∩ C major = golden13 ∩ C major = {B, C, D}; 53 ∩ C major = {C, B};
  pentatonic A ∩ C major = {C, D}; with C natural minor: golden7 {C}, 35 {C, D}, 53 {C, B♭}, golden13 {C, D, B♭}.
  Maxima over all 36 tonics: golden pentatonic 2 and golden7 2 (every family); 35: 3 with major, natural, harmonic and
  melodic minor (2 with pentatonics); golden13: 3 with major and natural minor, **4 with harmonic and melodic minor, for one
  key each** (B harmonic and B melodic minor: B C♯ D A♯).
- Ranking of pivot cells (size, then content): chain-step neighbours (n − 1 notes, n − 3 golden triads) ≫ a whole
  golden triad (limma between golden13 keys) ≫ a golden fifth or third ≫ the semitone pair B–C (golden7 vs C major) ≫ a
  single note.

### 16.5 Changing scales [Exhaustive, me §5]
- **Chroma of one chain step** (the note that changes, exact): pentatonic (generator a golden fifth) −69.10 (limma);
  golden3 +99.27 (apotome); golden4 −267.64; **golden7 −168.37 (5 sixth-steps, not an apotome)**; golden10 −69.10 (limma);
  golden13 +30.17 (comma); golden23 −38.92. The apotome belongs to golden3, as the Pythagorean apotome belongs to the diatonic. The growing golden chain
  reaches its first semitone at 4 notes; the chain of fifths at 6 (F to E).
- Walks up the chain: golden7 C → ^A♭ (B → ^A) → vF (^G → vF♯) → C♯ (vE → D) → ^A (C → ^B♭) → vF♯ → D → ^B♭ (0 notes
  left after 7 steps); 35 C → ^A♭ (B → ^B♭) → vF (^G → vG) → …; golden-third key cycle (one chain step down): golden7
  C♯ → vE♭ (+5) etc., 35 D → vE♭ (+2), golden13 D → vD (−1).
- **The growing scale** C, vE, ^G, ^A♭, B, vF, C♯, ^A, vF♯, D, vE♭, ^F♯, B♭ (chain order around the tonic triad): two step
  sizes exactly at n = 2, 3, 4, 7, 10, 13, three sizes in between (36-ET and exact golden tuning agree); golden triads
  0, 1, 2, …, 11 (= n − 2). Western mirror with pure fifths: two sizes at 2, 3, 5, 7, 12.
- **Alternation**: 35 → 53 on C raises three notes by a limma (D vF♯ ^A → vE♭ ^F♯ B♭), keeps golden7; Western mirror C
  major → C minor lowers three by a semitone (E A B → E♭ A♭ B♭), keeps 4. Pentatonic A ↔ B: disjoint, union 35.
- **Limma key change**: golden13 C → vC♯ keeps vE♭g, the leaving ten notes are exactly 35 on C and each arriving note
  lies one sixth-step below a leaving one; C → ^B keeps Dg, the leaving notes are 53 on C, each arriving note one
  sixth-step above.

### 16.6 Crossing worlds [Exhaustive + Theorem, me §6]
- C golden7 shares two notes with 13 of the 36 major keys: C and G ({C, B}), C♯ and A♭ ({C, C♯}), D, E, F♯, A, B
  ({C♯, B}), ^E♭ and ^A♭ ({^G, ^A♭}), vF and vC ({vE, vF}). {B, C} lies in only two major keys (C, G) but in 4 golden7, 7
  decatonic and 10 golden13 keys.
- B lies in G, Em, E, B, Bm, G♯m and in vEg, ^Gg, Bg; C lies in C, F, A♭, Cm, Fm, Am and in Cg, vFg, ^A♭g. The shared
  cadence B → C is harmonized G → C (Western), vEg → Cg (golden7: π(iii) → π(I)) or Bg → Cg (53; all voices rise).
- **Projection inflection** [Theorem, me §6]: bending a C major melody by the projection of the chord under it, (C major
  − X) ∪ π(X), gives under Cg (and vEg) the golden Ionian C D vE F ^G A B, under Fg (and vAg) ^C D E F G vA B, under Gg
  C ^D E F G A vB, under vDg C vD E ^F G A B: the two inflections at the (2, 2) point of §8.4's frontier plus the two
  two-note inflections at (3, 1) (the frontier holds 3 / 6 / 2 / 2 scales at (6,0) / (3,1) / (2,2) / (0,3)).

### 16.7 Audio (textbook/audio/ch40; all expanded and note-checked by me §7)
`palette`, `pentatonic_chain`, `pentatonic_mirror`, `golden7_tendency`, `golden7_mirror`, `decatonic_sequence`,
`decatonic_alternation`, `pivot_subset`, `chain_walk`, `growing_scale`, `limma_pivot`, `cross_inflection`, `cross_hinge`,
`worked_pentatonic`, `worked_golden7`, `worked_decatonic`, `worked_crossing` (14–37 s each, plus a 3 s tail).

### 16.8 Open questions
1. Does a golden-pentatonic melody, which has no semitone and no golden third, sound "golden" at all without its harmony,
   or does the ear hear it as a slightly stretched Western pentatonic? A listening test with and without the chords.
2. Tendency: are B → C and C♯ → C heard as equally strong closes in golden7, and does the parallel Bg → Cg (53) close
   more strongly than vEg → Cg? (Chapter 31's question about golden function, asked melodically.)
3. How long must a melody dwell on a common subset for the ear to accept the new key underneath (§7.4's criterion, for
   melodic pivots)?
4. The growing scale passes through three-size stages (5, 6, 8, 9, 11, 12 notes). Are these heard as unstable, as the MOS
   stages are heard as resting points? A probe-tone design would test it.
5. Which Western tunes survive projection inflection best (melodies on chord tones bend most; stepwise ones least)?
