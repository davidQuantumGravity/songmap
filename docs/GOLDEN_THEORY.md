# A theory of golden harmony: rational homes, irrational passages

This document classifies golden passing harmony rigorously, inverts it (golden homes and drones), and generalizes both into one theory with new chord progressions.

**Companion documents:**
- [GOLDEN_HARMONY.md](GOLDEN_HARMONY.md): the vision, notation and engine plan.
- [GOLDEN_PROGRESSIONS.md](GOLDEN_PROGRESSIONS.md): the generated dictionary of all 870 chord pairs, with SATB voice lines.

**Code** (every claim here is reproduced by these):
- [reference/golden/classify.py](../reference/golden/classify.py): theorems and exhaustive enumeration.
- [reference/golden/dictionary.py](../reference/golden/dictionary.py): four-part realizations.
- [reference/golden/explore.py](../reference/golden/explore.py): acoustics.

**Names used throughout:**
- **golden** = stacked golden thirds (0-11-22 sixth-steps);
- **silver** = stacked golden minor thirds (0-10-20), the average of major, minor and diminished;
- **bronze** = the T13 chord (0-13-26), golden reflected through augmented, golden's constant passing partner.

Chord symbols: `Cg`, `Cs`, `CT13`. The full mathematics and history (commas, limma and apotome, well-formed scales, the averaging principle) are in [GOLDEN_MATH.md](GOLDEN_MATH.md).

## 0. The averaging principle (the founding idea)

A golden or silver chord is an **average of Western chords**, voice by voice, and lands exactly on the 36-ET grid:
- **Cg = (C + Cm + Caug)/3:** third (12+9+12)/3 = 11, fifth (21+21+24)/3 = 22.
- **Cs = (C + Cm + Cdim)/3:** third 10, fifth 20.

The author's description ("the golden third is 2/3 major, 1/3 minor; the golden fifth 2/3 perfect, 1/3 augmented") is exactly this average. Passing chords are averages of their neighbours: P₁ = (2X + Y)/3, P₂ = (X + 2Y)/3. All 16 three-chord averages are tabulated in GOLDEN_MATH §5.

**The theory runs in two systems, simplest first:**
- **System 1 (strict):** the unique uniform path. At most one golden chord per transition. SongMap `~`.
- **System 2 (natural):** whole steps may split unevenly. Two golden chords can follow each other. SongMap `~g`.

## Summary of results

1. **Layer theorem.** A golden triad (stacked golden thirds, 1 : 2/φ : 4/φ²) has exactly one note on each of the three 12-ET layers of 36-ET. Western chords live on one layer.
2. **Four-path theorem.** Every golden triad is the passing chord of exactly 4 stepwise uniform paths. Up to transposition, there are **12 path types**: the complete classification.
3. **Quality theorem.** Strict golden passing chords join only triads of the *same quality* (major–major or minor–minor) whose roots are a **third or a fifth** apart. Each such pair has exactly **one**.
   - In a major key that means **I–IV, I–V, ii–vi and iii–vi**, plus every chromatic mediant (I–♭VI, I–III, I–VI, I–♭III).
4. **Root rules.** The golden chord's root is fixed by the pair: the upper root for major pairs and the lower root for minor pairs, shifted by 0, ^ or v (or vv) depending on the interval.
5. **Never twice; partner theorem.** A uniform path never has two golden passing chords. The other passing chord is always an *equal-third* triad: **bronze** (T13, two stacked thirds of 13 sixth-steps, third ≈ 9/7), or **silver** (only between augmented and diminished).
6. **Equal-third line.** Diminished (9) – silver (10) – golden (11) – augmented (12) – bronze (13) are evenly spaced points on one straight line of chord space, and one uniform path runs along it: Caug → Cg → Cs → Cdim.
7. **Natural paths.** If whole steps may split unevenly (half steps stay 1 + 1 + 1), golden passing extends to stepwise progressions:
   - Roots a whole step apart get **two golden chords on the chromatic root between them** (IV → v#IVg → ^#IVg → V).
   - 46 chord pairs take a diatonic–golden–golden–diatonic form; 181 take diatonic–golden–diatonic.
8. **Half-step theorem.** Chords a half step apart in parallel motion can never pass through golden. Their passing chords are *planing* (Western chords shifted onto another layer).
9. **Asymmetry theorem.** No uniform path goes golden → Western → golden. When golden harmony is home, it moves by its own operations: the **golden circle** of 36 triads, layer **planing**, and golden-seventh **breathing**. Western chords only *visit*.
10. **Acoustics decide which world is home.**
    - With harmonic timbres, golden chords are tense (passing).
    - With golden-spectrum timbres they are the smoothest chords (home).
    - The exact chain voicing 1 : φ : φ² : φ³ makes combination tones that land exactly on its own chain.
    - In close voicing the golden seventh beats at f₀·φ⁻⁶ × (1, 2/φ, 4/φ²), the golden triad in rhythm, plus 2f₀·φ⁻⁶, because the golden seventh sits exactly 2φ⁻⁶ below the octave (8/φ³ = 2 − 2φ⁻⁶).

---

## 1. Foundations

### 1.1 Chords as vectors in Z₃₆
- Pitch classes are sixth-steps mod 36.
- Every pitch class p has a **layer** λ(p) = p mod 3: layer 0 is 12-ET, layer 1 is `^` (+33 c), layer 2 is `v` (−33 c).
- A chord in *v* voices is a vector X ∈ Z₃₆^v; voice order is voice identity.
- **Rational (Western) chords** are *single-layer*: every interval is a multiple of 100 c. A Western chord moved onto another layer is still rational; it is the same chord, off the grid.
- **Golden chords** are built from stacked golden thirds (2/φ ≈ 366.9 c = 11 sixth-steps):
  - triad G_r = {r, r+11, r+22} ≈ 1 : 2/φ : 4/φ²;
  - seventh G7_r = {r, r+11, r+22, r+33} ≈ 1 : 2/φ : 4/φ² : 8/φ³.
  - Octave-equivalently, these are the chain chords 1 : φ : φ² and 1 : φ : φ² : φ³.

### 1.2 The layer theorem
λ(r + 11) = λ(r) + 2 and λ(r + 22) = λ(r) + 1 (mod 3), so **a golden triad has one note on each layer**. A golden seventh has two notes on its root's layer (root and seventh, 33 = 3·11 ≡ 0) and one on each of the others.

**Irrationality degree:** the number of layers a chord touches. Western chords have degree 1; golden triads have the maximum, 3.

### 1.3 Uniform sub-chromatic paths
- Given voice displacements d ∈ {−2, …, 2}^v (in semitones, so each voice moves stepwise), the **uniform path** is P_k = X + k·d (in sixth-steps), for k = 0, 1, 2, 3, ending at Y = X + 3d.
- Every half step is split 1 + 1 + 1 and every whole step 2 + 2 + 2: the author's rule, and it is unique once the voicing is fixed.
- **Barycentric reading:** P_k = ((3 − k)·X + k·Y) / 3. Every sub-chromatic passing chord is a weighted mean of its two neighbours.
- Since X is on layer 0, voice i of P_k sits on layer k·dᵢ mod 3. Each voice belongs to one of three **motion classes**:

| Class | Motions | Layer of P₁ |
|---|---|---|
| hold | d = 0 | 0 |
| rising | d = +1 or −2 | 1 |
| falling | d = −1 or +2 | 2 |

---

## 2. Part I: diatonic home, golden passing (complete classification)

### 2.1 Admissibility and the four-path theorem
- **Admissibility:** P_k can be golden only if the voice leading contains one voice of each class (hold, rising, falling). This follows from the layer theorem.
- **Four-path theorem:**
  - Fix a golden triad and a position k. The hold voice must have d = 0, and each other voice has exactly two stepwise choices of its class. That gives exactly **4** paths with layer-0 endpoints.
  - Over all 36 golden triads and both positions that is **288 ordered paths**. 240 have Western endpoints (one of the 12 types ends on a sus4, C♯dim → Esus4); the rest end on a non-tertian set such as {C, F, F#}.
  - Up to semitone transposition and reversal there are **12 types**.

| Root layer | Motion (root, third, fifth) | X | P₁ | P₂ | Y |
|---|---|---|---|---|---|
| 0 | (0, −1, −2) | Caug | **Cg** | C silver | Cdim |
| 0 | (0, −1, +1) | C | **Cg** | ^E♭ T13 | A♭ |
| 0 | (0, +2, +1) | Cm | **Cg** | vA♭ T13 | Fm |
| 0 | (0, +2, −2) | A♭ | **Cg** | {C ^E vG} | {C F F#} |
| 1 | (−2, 0, −1) | C#m | **^Cg** | ^G T13 | Em |
| 1 | (−2, 0, +2) | C#dim | **^Cg** | vC T13 | Esus4 |
| 1 | (+1, 0, −1) | Caug | **^Cg** | vC# silver | C#dim |
| 1 | (+1, 0, +2) | C | **^Cg** | E T13 | A |
| 2 | (−1, −2, 0) | C# | **vC#g** | vE T13 | A♭ |
| 2 | (−1, +1, 0) | C#m | **vC#g** | A♭ T13 | Fm |
| 2 | (+2, −2, 0) | Fm | **vC#g** | {^C# vE A♭} | {D E♭ A♭} |
| 2 | (+2, +1, 0) | Caug | **vC#g** | ^C# silver | Ddim |

(Each type holds for all 12 semitone transpositions; reversing a path moves the golden chord to position 2/3.)

### 2.2 Never twice, and the partner theorem
- **Never twice:** no uniform path has both passing chords golden. This was checked exhaustively; it also follows because P₂ − P₁ = d shifts the two moving voices off the golden interval pattern.
- **Partner theorem:** on every Western-to-Western path, the passing chord that isn't golden is an **equal-third triad** T_n = {0, n, 2n}: bronze (T13) in 168 paths, and silver (T10) in 72 paths.
- **Silver appears only between augmented and diminished triads.**

### 2.3 The equal-third line
- Chords T_n = (0, n, 2n) for n = 9 (diminished), 10 (**silver**), 11 (**golden**), 12 (augmented) and 13 (**bronze**, T13) lie on one straight line of voice-leading space.
- **Caug → Cg → Cs → Cdim is a single uniform path**: the root holds, the third falls one sixth-step per chord, the fifth two.
- **Centroids:**
  - Cg = (C + Cm + Caug)/3.
  - Cs (silver, the 0-10-20 form) = (C + Cm + Cdim)/3.
- Golden is the balance point of the "bright" triads, silver of the "dark" ones.

### 2.4 Quality theorem and root rules (every key)
**Quality theorem:**
- Strict golden passing chords exist between major or minor triads **only when both have the same quality** and their roots are a **m3, M3, P4/P5 or m6/M6** apart.
- They never exist for seconds, the tritone, or mixed quality. Each qualifying pair has exactly one.
- **Equivalent form (neo-Riemannian):** these are exactly the pairs two P/L/R moves apart (from C: A♭ = PL, E♭ = PR, E = LP, G = LR, A = RP, F = RL). Checked exhaustively: 144 ordered pairs, each with exactly one golden chord, all at P/L/R distance 2.

**Major pairs.** The golden chord sits on the *upper root*, the root lying a third or a fourth above the other. It is shifted by the interval and lies nearer that chord.

| Relation | Shift | Example |
|---|---|---|
| major third | 0 | C ↔ E: **Eg** · C ↔ A♭: **Cg** |
| minor third | ^ | C ↔ E♭: **^E♭g** · C ↔ A: **^Cg** |
| fourth/fifth | v | C ↔ F: **vFg** · C ↔ G: **vCg** |

**Minor pairs.** The golden chord sits on the *lower root* and lies nearer that chord.

| Relation | Shift | Example |
|---|---|---|
| fourth/fifth | 0 | Cm ↔ Fm: **Cg** · Dm ↔ Am: **Ag** |
| major third | v | Cm ↔ Em: **vCg** |
| minor third | vv | Cm ↔ E♭m: **^Bg** (= vvC) |

**In a major key** the diatonic pairs are exactly the four fifth-relations whose voice leading crosses one of the scale's two half steps (E–F, B–C):

| Pair | Golden passing chord |
|---|---|
| I ↔ IV | **vFg** (vF ^A♭ C) |
| I ↔ V | **vCg** (vC ^E♭ G) |
| ii ↔ vi | **Ag** (A vC# ^E) |
| iii ↔ vi | **Eg** (E vG# ^B) |

All the Romantic **chromatic mediants** qualify, so golden harmony is native to Schubert-to-film-score mediant harmony. The 68 ordered pairs in C major plus common chromatic chords are listed in `classify.py` §E and in the dictionary.

### 2.5 Golden sevenths
Strict paths reach a golden seventh between Western chords in only **4 types** (up to transposition and reversal; 96 paths):
- **m7 ↔ maj7 a semitone lower**: C#m7 → ^Cg7 → ^G T13 → Cmaj7, and C#m7 → vC#g7 → A♭ T13 → C#maj7.
- **augmented ↔ diminished seventh**: Caug → ^Cg7 → … → C#dim7.

Golden sevenths become common on **natural paths**, as parallel or chromatic seventh motion:
- ii7 – IIg7 – ♭IIIg7 – iii7
- iii7 – ♭IIIg7 – IIg7 – ii7
- G7 → A♭maj7 via ^Gg7, and Fmaj7 → E7 via ^Eg7 (staggered voices)

### 2.6 Natural paths (two golden chords in a row)
**Rule:** half steps stay 1 + 1 + 1. A whole step may split unevenly into monotone parts of at most a semitone (for example 1 + 2 + 3 or 3 + 3 + 0).

**Census** (870 ordered pairs, SATB):

| Path type | Exact golden passing chords | Golden over a pedal | Pairs with two different golden chords | Pairs with at least one |
|---|---|---|---|---|
| Strict | 32 | 122 | — | — |
| Natural | 227 | 299 | 46 | 181 |

**Whole-step root rule:** when roots move by a whole step, the two golden chords sit on the **chromatic root between**, crossing layers.

| Progression | Path |
|---|---|
| IV → V | F – **vF#g – ^F#g** – G |
| V → vi | G – **vA♭g – A♭g** – Am |
| I → ii | C – **vC#g – C#g** – Dm |
| ii → iii | Dm – **^Dg – E♭g** – Em |
| ♭VII → I | B♭ – **vBg – ^Bg** – C |

**Half-step theorem:** parallel half-step motion (iii → IV, vii° → I in parallel) puts every voice in one class, so the passing chords are *planing* (^Em, vF …), never golden. Revoicing does not help: an exhaustive check (every voice assignment, every voice moving up to three semitones either way, any monotone split into parts of at most a semitone) finds no golden passing chord between major or minor triads whose roots are a half step apart (the result is the same for moves of up to two or up to three semitones, with or without doublings). Golden color there needs an intermediate chord.

### 2.7 Four-part realizations (worked)
**V → I (strict, unique):**
```
S: D4   vEb4  ^Eb4  E4        P1 = vEb T13 / G  (bronze partner)
A: B3   ^B3   vC4   C4        P2 = vCg / G      golden, over the dominant pedal
T: G3   G3    G3    G3
B: G2   G2    G2    C3
```
This is the **golden cadential six-four**:
- The golden triad sits a sixth-step below the tonic, over the dominant bass. The fifth of vCg *is* that bass, G.
- The leading tone rises B → ^B → vC → C, and the second degree rises D → vE♭ → ^E♭ → E.
- **V7 → I (natural):** G7 – G g7(^^3,^5) – vCg/G – C. The seventh F rises through F# to G, as Bach often lets an inner-voice seventh rise.

Further four-part realizations:
- **I–IV–V–I:** C – vA♭T13/C – **vFg/C** – F – **vF#g – ^F#g** – G – vE♭T13/G – **vCg/G** – C. Four golden passing chords, all voices stepwise.
- **ii–V–I:** Dm – **Dg – vGg/D** – G – vE♭T13/G – **vCg/G** – C.

---

## 3. Part II: golden home and rational release (the inversion)

### 3.0 What "golden home" means (the author's framing)
- **Western consonance is the global minimum of tension.** Physical instruments (strings, winds, voices) have
  (nearly) harmonic spectra, so on any real instrument a Western triad, C major above all, is the deepest rest.
  Arriving on a Western chord from golden harmony is the ultimate release, never a "rough visit".
- **The golden triad as a local minimum** is the author's model of how golden harmony *feels*: a metastable
  resting place, unstable relative to C major yet somewhere one can dwell and return to, and whose effect on
  the overtones over extended listening is the motivation for this whole project (a personal experience and a
  hypothesis, Part VIII). **Measured** on harmonic tones, the standard models do *not* show a local minimum:
  in the (third, fifth) plane, Sethares roughness and triad harmonic entropy both fall steadily from the exact
  golden triad toward the just major triad (golden 1.498, C major 1.319; the lowest value within 5 c of golden
  is 0.007 lower, within 30 c 0.197 lower; the only grid minima nearby are just major 386/702 c and 386/772 c).
  The "local minimum" is therefore a musical and psychological claim to test, not a property of these models.
- **The timbre flip is a laboratory, not a claim about instruments.** Golden spectra (partials 2^m·φ^n) exist
  only digitally. On them the exact golden triad *is* a strict local minimum of roughness (every triad within
  5–30 c is rougher, by 0.11–0.46) and lies below major (2.08 vs 3.17). The flip is an exercise: immerse in golden
  harmony on its own terms, to ground oneself in it and study it, then carry what was learned back to real,
  harmonic instruments, where C major is home and golden is the delicate local rest.

### 3.1 Asymmetry theorem
**No uniform path golden → Western → golden exists** (exhaustive). Rational chords are not natural *passing* chords between golden homes.

Golden homes therefore move by their own operations:

| Operation | Effect |
|---|---|
| **Circle step** | G_r → G_{r+11} (or G_{r−11}): two common tones; one voice moves a semitone, staying on its layer. Exact tuning: 99.27 c = φ³/4 |
| **Planing** | G_r → G_{r±1}: every voice glides one sixth-step (33 c); the whole chord changes layer color |
| **Breathing** | G_r ↔ G7_r ↔ G_{r+11}: add the chain neighbour (Cg + B = Cg7), then drop the root (= vEg) |
| **Visit** | G → W → G, a release to the nearest rational chord and back: Cg ↔ C (2 sixth-steps), Cm (3), Caug (3), A♭ (4) |

### 3.2 The golden circle
Cg → vEg → ^Gg → Bg → vE♭g → ^F#g → B♭g → vDg → ^Fg → Ag → vC#g → ^Eg → A♭g → …

- Period 36: it visits **all 36 golden triads**, like the circle of fifths visits all 12 keys.
- Each step moves **one voice down a semitone** (the other direction moves one voice up).
- Any two neighbours form a golden seventh (Cg ∪ vEg = Cg7).
- **In chain voicing** the circle is a *sliding window* over φ powers: {φ⁰, φ¹, φ²} → {φ¹, φ², φ³} → …. Each step replaces φʲ by φʲ⁺³ = φʲ · 4 · (φ³/4): two octaves and a 99.27 c semitone.

### 3.3 Acoustics: why golden can be home
| Fact | Detail |
|---|---|
| **Timbre flips consonance** | Roughness (Sethares). Harmonic overtones: major 1.32, golden 1.50. Golden-spectrum overtones 2^m·φ^n (0 ≤ m, n ≤ 3, below 9: 11 partials; adding φ⁴ gives golden 2.40, major 3.53, minor 3.62): golden **2.08** vs major 3.17, minor 3.26. On this digital timbre (the laboratory, §3.0) the golden triad is the smoothest chord measured |
| **Self-similar combination tones** | φⁿ − φⁿ⁻¹ = φⁿ⁻², so the exact chain voicing 1 : φ : φ² : φ³ makes **every** f₂−f₁ and 2f₁−f₂ combination tone land on a golden-chain pitch (0 Hz error) |
| **Fibonacci tuning** | Exact φ powers on f₀ = 55 Hz are ≈ 55, 89, 144, 233, 377, 610 Hz: the **Fibonacci numbers**, off by about 0.01 Hz. With integer Fibonacci frequencies, combination tones are again Fibonacci numbers (Fₙ₊₁ − Fₙ = Fₙ₋₁), but the drone becomes periodic (1 s period). Exact φ is truly quasi-periodic. The two differ by beats of 0.008 Hz (89, 144), 0.016 Hz (233), 0.024 Hz (377) and 0.041 Hz (610): a "breath" of about 25–120 s |
| **Beat spectrum of close voicings** | Lowest beats of exact close voicings on harmonic tones. **Cg:** f₀·φ⁻⁶ × (1, 2/φ), plus 2f₀·φ⁻⁶ from a doubled harmonic pair. **Cg7 (1 : 2/φ : 4/φ² : 8/φ³):** f₀·φ⁻⁶ × (1, 2/φ, 4/φ²), the golden *triad* in rhythm, plus 2f₀·φ⁻⁶, the golden seventh against the root's octave, since 8/φ³ = 2 − 2φ⁻⁶. No beat occurs at the golden seventh's own ratio. The base rate f₀(13 − 8φ) = f₀·φ⁻⁶ comes from the Fibonacci approximant 13/8 ≈ φ. With root f₀ = 110 Hz (A2) the rates are 6.13, 7.58, 9.37 and 12.26 Hz; register sets the band (f₀ = 10·φ⁶ ≈ 179 Hz puts the base beat at 10 Hz) |
| **Quasi-periodicity** | Tones in φ ratios never realign into a common period. φ is the number hardest to approximate by fractions (all-ones continued fraction), so in dynamical systems a φ frequency ratio is the most robust against mode-locking (golden-mean tori are the last to break in KAM theory; the golden rotation number is the last to lock in the circle map). A golden drone is maximally resistant to settling into a periodic pulse |

### 3.4 Bliss hypothesis
**The hypothesis (from the author's principle):**
- **Rational harmony** invites *locking*: periodic, synchronizing resonance. Taken to the extreme, hypersynchrony is the signature of a seizure.
- **Irrational harmony** offers *coherence without locking*: structured, self-similar, never periodic.
- The idea is that a coherent, non-periodic resonance invites a calm, open state rather than entrainment.

**Supporting threads (to be stated carefully):**
- Pletzer, Kerschbaum & Klimesch (2010, *Brain Research*), "When frequencies never synchronize: the golden mean and the resting EEG": argues that EEG frequency bands relate by ≈ φ, because golden ratios minimize spurious cross-frequency synchronization.
- Roopun et al. (2008, *Frontiers in Neuroscience*) observed ratios near φ between cortical rhythm bands.
- Binaural-beat research is mixed: a 2019 meta-analysis (Garcia-Argibay et al., 22 studies) found a medium pooled effect (g = 0.45) on memory, attention, anxiety and pain, while EEG-entrainment studies are inconsistent.

**Status:** these are hypotheses to test by listening, not effects to claim. The music and videos describe sounds, never promise states of mind.

**Design principles that follow:**
1. **Golden at every scale.** Pitches in φ ratios (chain voicing). Beats in φ ratios (close-voicing beat spectrum, or a deliberate **golden beat ladder**: binaural detunes of B, B/φ, B/φ² … e.g. 10, 6.18 and 3.82 Hz). Section lengths in Fibonacci bars (8, 13, 21).
2. **No rational lock.** Avoid steady rational pulses (drums, strict meter) in bliss sections. Let golden beats and slow golden-circle changes provide the motion.
3. **Golden timbres** for the home chords: golden-spectrum pads and bells, where golden chords are acoustically smooth.
4. **Safety.**
   - Moderate levels; no strong infrasound (the Fibonacci 21 and 34 Hz combination tones are fine at low level).
   - Binaural layers are headphone-only and optional.
   - Pair the music with calm visuals, never flashing ones.

### 3.5 Drone recipes
| Name | Recipe |
|---|---|
| **Golden drone I** (chain) | f₀ = 55 Hz chain 55·φ^{0..3} (exact) on a golden-spectrum pad; window slides one chain step every 13 or 21 s (the golden circle); 4 s crossfades |
| **Golden drone II** (beating) | Close-voiced Cg7 on harmonic-spectrum strings at f₀ ≈ 110 Hz (beats 6.1–12.3 Hz, theta to alpha); slow breathing Cg ↔ Cg7 ↔ vEg |
| **Golden drone III** (binaural ladder) | Chain drone + headphone layer with per-voice L/R detunes 10, 6.18, 3.82 Hz; every 21 bars the ladder shifts down by φ |
| **Visitation** | Within a golden home, a brief rational chord (C major, 3–5 s) then return. On harmonic timbres the Western chord is the release and the return to Cg re-enters the delicate local rest; on the digital golden timbre (the laboratory) the roles flip |

---

## 4. Part III: a general theory of golden harmony

### 4.1 Principles
1. **Two worlds.** Rational chords (one layer) and irrational chords (all three layers, the golden family). 36-ET contains both exactly or to within a cent.
2. **Bridges are barycenters.** A golden passing chord is a 2/3 : 1/3 mean of two same-quality triads a third or a fifth apart (§2.4). A golden triad is also the centroid of major, minor and augmented. Golden chords are *averages of Western harmony that land on the golden chain*.
3. **Timbre assigns home.** The grammar of §2 (rational home) and §3 (golden home) is the same mathematics viewed from opposite sides. The instrument's spectrum decides which side is acoustically stable.
4. **Function is positional.** The same golden chord can be:

| Function | Meaning | Example |
|---|---|---|
| **Passage** | Between two homes | C – vFg – F |
| **Shadow** | A golden chord a sixth-step below (v) a diatonic root, leading up into it | vCg → C, the "sub-chromatic leading chord" |
| **Pivot** | One golden chord on paths in two worlds. **Cg** lies on C ↔ A♭ (major world) *and* Cm ↔ Fm (minor world) | Golden modal mixture: C – Cg – Cm |
| **Home** | Sustained on golden timbres | — |

5. **Classical constraints carry over.**
   - Passing chords on weak beats.
   - Common tones hold.
   - Sevenths resolve down, or rise only in inner voices.
   - No parallel fifths or octaves at the arrival.
   - A bass pedal under passing chords (the golden six-four).
   - Leading tones rise *through* the golden layers.

### 4.1b Golden scales for natural progressions
- The golden chain's well-formed sizes are 2, 3, 4, 7, 10, 13, 23 and 36 (GOLDEN_MATH §3).
- **golden7 = C C# vE vF ^G ^A♭ B** is the golden counterpart of the diatonic.
  - It contains five golden triads (Cg, C#g, vEg, vFg, ^A♭g) and four golden sevenths, including the tonic Cg7.
  - Progressions that stay inside golden7 (or golden10, golden13) are the natural "diatonic" progressions of the golden system. Neighbouring chords on the golden circle share two notes.
- There is no well-formed 9-note golden scale, even though 13 golden sixths ≈ 9 octaves. The "9" counts how many golden-chromatic steps the golden sixth spans, just as the "7" in 12 fifths ≈ 7 octaves counts the fifth's semitones.

### 4.2 Classical progressions with golden passing (new, tradition-respecting)
Voice lines for each are in [GOLDEN_PROGRESSIONS.md](GOLDEN_PROGRESSIONS.md) under the same names.

| Name | Progression | Notes |
|---|---|---|
| **Golden authentic cadence** | V – vIg/V – I | G – vCg/G – C (3-chord); or G – vE♭T13/G – vCg/G – C (4-chord) |
| **Golden full cadence** | I – vIVg – IV – v#IVg – ^#IVg – V – vIg – I | 4 golden passing chords, all stepwise |
| **Golden ii–V–I** | ii – IIg – vVg/II – V – vIg/V – I | Dm – Dg – vGg/D – G – vCg/G – C |
| **Golden jazz cadence** | ii7 – IIg7 – vVg/II – V – … – Imaj7 | The golden seventh on the supertonic |
| **Golden deceptive cadence** | V – v♭VIg – ♭VIg – vi | G – vA♭g – A♭g – Am. The golden chords sit on ♭VI and foreshadow it |
| **Golden staircase** | I – v♭IIg – ♭IIg – ii – ^IIg – ♭IIIg – iii – IV – v#IVg – ^#IVg – V – v♭VIg – ♭VIg – vi | 8 golden chords; each diatonic step is approached through two golden chromatic chords |
| **Golden Andalusian** | vi – ♭VIg – v♭VIg – V – ^#IVg – v#IVg – IV – (planing) – III | Am – A♭g – vA♭g – G – ^F#g – vF#g – F – vF – ^E – E. The last step is the half-step theorem in action: sub-chromatic planing into the Phrygian cadence |
| **Golden modal mixture** | I – Ig – i | C – Cg – Cm; the golden centroid pivots major to minor |
| **Golden Picardy** | i – I(^m3) – Ig – I | Cm – C(^m3) – Cg – C. The third climbs 9 → 10 → 11 → 12 sixth-steps; the fifth touches the golden fifth as an upper neighbour |
| **Golden mediant neighbour** | I – Ig – ♭VI – Ig – I | C – Cg – A♭ – Cg – C; Cg sits 1/3 of the way from C to A♭ (2/3 from A♭ back to C) |
| **Golden plagal amen** | IV – vIVg/IV – I | F – vFg/F – C, a golden chord over the subdominant pedal |

### 4.3 Golden-home progressions (stable irrationality, for bliss)
| Name | Motion | Voicing / timbre |
|---|---|---|
| **Golden circle walk** | Cg – vEg – ^Gg – Bg – vE♭g – … (one voice down a semitone each step; 13 or 21 s per chord) | Chain voicing, exact φ, golden-spectrum pad |
| **Golden breathing** | Cg – Cg7 – vEg – vEg7 – ^Gg … (add the next chain tone, then release the oldest) | The window grows to 4 and shrinks to 3: a breath |
| **Layer prism** | Cg – ^Cg – vC#g – C#g (planing by sixth-steps: the same shape in three layer colors) | Slow glides (3–5 s portamento) |
| **Rational visitation** | Cg – C – Cg … Cg – A♭ – Cg … Cg – Cm – Cg | On harmonic timbres each Western chord is a moment of full release; on a golden-spectrum pad (laboratory) the roles flip |
| **Fibonacci ascent** | Drone on 55·φ^k, adding one chain tone every Fibonacci number of bars (1, 1, 2, 3, 5, 8, 13) until the golden seventh is complete | Golden-spectrum bells and pad |
| **Golden beat cadence** | Close-voiced Cg7 at f₀ = 179 Hz (beats from 10 Hz), descending the golden circle until f₀·φ⁻⁶ is near 6 Hz | Harmonic strings; beats cross alpha → theta |

### 4.4 Composition workflow
1. Write a Western progression, or pick one from the dictionary.
2. Insert golden passing chords where §2.4 or §2.6 guarantees them, using `~g` placeholders in SongMap ([GOLDEN_HARMONY.md §5.4](GOLDEN_HARMONY.md)).
3. Choose the world per section by timbre: harmonic for rational home, golden spectrum for golden home.
4. For bliss sections, use §4.3 with chain voicing and the beat recipes. Avoid strict rational pulse.
5. Verify with the analysis tools: tension curve, beat spectrum, roughness.

---

## 5. Listening examples

Rendered by `python reference/golden/render_examples.py` into `reference/golden/out/`.
- Examples 1–6 use 36-ET, felt piano + soft pad; golden passing chords are short and diatonic chords long.
- Examples 7–8 use exact φ ratios.

| File | What to listen for |
|---|---|
| `01_golden_authentic_cadence.wav` | V – vE♭T13/G – **vCg/G** – I: the leading tone and 2nd degree rising through sixth-steps; the golden six-four |
| `02_golden_full_cadence.wav` | I–IV–V–I with 4 golden passing chords, incl. the IV → vF#g → ^F#g → V "escalator" |
| `03_golden_ii_V_I.wav` | Dm – Dg – vGg/D – G – … – vCg/G – C |
| `04_golden_staircase.wav` | The diatonic ladder I → vi, each step approached through golden chromatic chords |
| `05_golden_andalusian.wav` | Golden chords on ♭VI and #IV, ending in sub-chromatic planing into E |
| `06_golden_pop_axis.wav` | I–V–vi–IV with the golden deceptive motion V – vA♭g – A♭g – vi |
| `07_golden_circle_drone.wav` | Golden home: an exact-φ chain window (55·φʲ, octave-folded) on a golden-spectrum pad, walking the golden circle, 13 s per chord |
| `08_beating_golden_seventh.wav` | Golden home with beats: close-voiced golden triad → golden seventh → next golden triad with root f₀ = 110 Hz (A2) on a harmonic pad. Beats at 6.13, 7.58 and 9.37 Hz (the golden triad in rhythm) and 12.26 Hz (the golden seventh against the octave) |

## 6. Questions: resolved and open

**Resolved by the author (2026-10-20):**
- The averaging principle is a founding principle (§0).
- T13 is named **bronze**.
- Silver = 0-10-20, the dark-side average (major + minor + diminished).
- Both passing systems are explored, System 1 first, then System 2.
- Listening: musical demos of 45 s to 2 min per technique, each paired with simple definition clips (see `golden_audio/index.html`).

**Findings from those questions** (GOLDEN_MATH.md):
- Silver isn't in golden13. It is a golden-chain interval only at distance 14 (exactly 336.7 c), so it first appears in golden23 and 36-ET.
- The golden comma is φ¹³/2⁹ = 30.17 c, with golden apotome φ³/4 = 99.27 c and golden limma 2⁷/φ¹⁰ = 69.10 c.
- There is no well-formed 9-note scale; golden7 is the natural sub-scale.

**Still open:**
1. Should silver triads (and silver13, the layer-mirrored golden13) get their own passing rules? Silver passes only between augmented and diminished under System 1.
2. Which golden7 progressions feel functional (tonic, predominant, dominant analogues)? Proposal: rank by golden-circle distance from Cg.
3. Listening protocol details for the drones (§3.4).
