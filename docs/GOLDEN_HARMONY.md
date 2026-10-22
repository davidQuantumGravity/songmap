# Golden harmony: a sub-chromatic music theory in 36-ET

**Goal:** give music new colors. Golden-ratio intervals and chords are woven *into* standard Western harmony:
- as **sub-chromatic passing chords** between diatonic chords and inside chromatic motion;
- as sustained colors of their own;
- and, through their self-similar overtone structure and controlled beating, as a tool for **inducing a blissful state, in the spirit of binaural beats**.

Every number here is reproduced by [reference/golden/explore.py](../reference/golden/explore.py) (intervals, scales, stability, combination tones, beat spectra) and [reference/golden/passing.py](../reference/golden/passing.py) (passing-chord tables).

**The rigorous classification**, both directions (golden passing in a diatonic home, and golden homes with drones), plus the generalized theory and new progressions, is in **[GOLDEN_THEORY.md](GOLDEN_THEORY.md)**. The generated dictionary of all 870 chord pairs, with SATB voice lines, is in **[GOLDEN_PROGRESSIONS.md](GOLDEN_PROGRESSIONS.md)**.

---

## 0. The vision (author's principles)

1. **The golden Pythagorean scale.** Generate the scale from 2 and φ = (1+√5)/2 instead of 2 and 3/2.
2. **Golden intervals.**
   - φ is a sixth (833 c).
   - Inverted and octave-reduced, it gives the **golden third** (2/φ, 367 c): about 2/3 major and 1/3 minor.
   - Two golden thirds give the **golden fifth** (4/φ², 734 c): about 2/3 perfect and 1/3 augmented.
3. **Golden chords are chain chords.**
   - **1 : φ : φ²** is octave-equivalent to the **golden major triad**.
   - **1 : φ : φ² : φ³** is the **golden (major) seventh chord**.
   - The golden seventh is the chord of φ³.
4. **Sub-chromatic passing harmony.**
   - Golden chords are the least stable chords: built on the most irrational number, they have the most irrational overtone relations.
   - That makes them ideal **passing chords** between diatonic chords, or *inside* chromatic motion, where they divide a semitone into thirds.
   - Expanding the voice leading between two chords picks out unique golden chords in a well-defined way.
5. **A family of micro-altered chords.**
   - The **silver triad** uses the **golden minor third** (about 2/3 minor and 1/3 major).
   - The fifth can be explored at various levels of micro-augmentation or micro-diminution, and the 7th degree at various levels too.
   - **First explorations focus on the golden major triad and the golden major seventh.**
6. **Purpose.** The original idea is to induce a state of bliss, similar to binaural beats. Golden harmony is a new palette of colors for humanity.

The rest of this document makes that vision precise, measurable, writable and renderable.

---

## 1. The system (verified)

### 1.1 Golden intervals and why 36-ET hosts them

| Interval | Exact ratio | Exact cents | 36-ET steps | 36-ET cents | Error | Reading |
|---|---|---|---|---|---|---|
| golden sixth | φ | 833.09 | 25 | 833.33 | +0.24 | ^m6 |
| golden third | 2/φ | 366.91 | 11 | 366.67 | −0.24 | vM3 (2/3 major, 1/3 minor) |
| golden fifth | 4/φ² | 733.82 | 22 | 733.33 | −0.49 | ^P5 (2/3 perfect, 1/3 augmented) |
| golden seventh | 8/φ³ | 1100.73 | 33 | 1100.00 | −0.73 | in 36-ET, exactly the 12-ET major seventh; the exact golden seventh is 0.73 c sharper |
| golden minor third | (see §1.6) | ≈333 | 10 | 333.33 | — | ^m3 (2/3 minor, 1/3 major) |

- **36-ET** divides the octave into 36 *sixth-steps* of 33.33 c (1/3 semitone). It **contains 12-ET exactly**, plus two copies shifted by ±1/3 semitone: the **three layers** (0 = standard, `^` = up one sixth-step, `v` = down one).
- **Why 36:** log₂φ has the continued fraction [0; 1, 2, 3, 1, 2, …], whose convergents are 1/1, 2/3, 7/10, 9/13 and **25/36**.
- **The identity behind the layers:** **φ³/4 ≈ 2^(1/12)**, off by 0.73 c. Three golden sixths make two octaves plus a semitone, so the golden chain cycles through the three layers, advancing by a semitone on each return.
- **Algebra worth knowing:** φ² = φ + 1, φ³ = 2φ + 1, and φⁿ − φⁿ⁻¹ = φⁿ⁻². Every golden chord lives in the number field ℚ(√5).

### 1.2 The golden chain, its scales, and the three layers
- Chain note *j* (j golden sixths above the start) sits on layer *j* mod 3.
- The chain closes into well-formed two-step-size scales at **2, 3, 4, 7, 10, 13, 23 and 36 notes** (Stern–Brocot denominators of log₂φ); the most useful are:

| Scale | Notes (centred on C) | Steps (sixth-steps) |
|---|---|---|
| golden3 = the golden triad | C vE ^G | 11 11 14 |
| golden10 | C C# vEb vE vF vF# ^G ^Ab ^A B | 3 5 3 3 3 5 3 3 5 3 |
| golden13 | C C# D vEb vE vF vF# ^F# ^G ^Ab ^A Bb B | 3 3 2 3 3 3 2 3 3 3 2 3 3 |

- golden13 has 10 semitone steps and 3 steps of 2/3 semitone (exactly 99.27 c and 69.10 c). It reads as a chromatic scale with three "seams" where the melody slips into another layer.
- It has **36 distinct transpositions**: the 36 unique 13-note scales.
- Centred on C it contains 11 golden triads.

### 1.3 The golden major triad and golden seventh as chain chords
- **Chain form.** **1 : φ : φ²** has the pitch classes {0, 466, 833} c, which is the golden triad **C vE ^G in second inversion**. The chain's top (φ²) is the chord's root, φ is its third (^G · φ = vE), and 1 is its fifth: bottom to top, fifth, third, root. Equivalently, the triad is three consecutive chain notes, read downward from the root.
- **Close form.** **Cg = C vE ^G** (36-ET steps 0, 11, 22): two stacked golden thirds.
- **Golden seventh: 1 : 2/φ : 4/φ² : 8/φ³** (three stacked golden thirds; octave-equivalent to the chain chord 1 : φ : φ² : φ³) = **Cg7 = C vE ^G B** (0, 11, 22, 33).
  - The 7th sits at 8/φ³ = 1100.73 c, which 36-ET renders as 33 sixth-steps, exactly the 12-ET major seventh (1100 c). The exact golden seventh is 0.73 c sharper. Note 8/φ³ = 2 − 2φ⁻⁶: it sits exactly 2φ⁻⁶ below the octave.
  - So Cg7 is **Cmaj7 with the inner voices bent by one sixth-step each** (v3, ^5).
  - This is the chord of φ³: the root is the chain note three golden sixths above the 7th.
- **It sits between the Western triads.** In 36-ET, Cg is *exactly* the centroid of C major (0, 12, 21), C minor (0, 9, 21) and C augmented (0, 12, 24). It is 2 sixth-steps from C, and 3 from Cm and Caug.
- **Symmetry.** Like the diminished and augmented triads, it is built from equal stacked intervals (11 + 11, closed by 14) and is mirror-symmetric (it is its own inversion).

### 1.4 Stability
- **Roughness** (Sethares beating model), chord on C4:

| Chord | Harmonic overtones | Golden overtones 2^m·φ^n |
|---|---|---|
| sus4 | 1.23 | 2.99 |
| major | 1.32 | 3.17 |
| minor | 1.34 | 3.26 |
| augmented | 1.45 | 3.14 |
| **golden** | **1.50** | **2.08 (smoothest)** |
| diminished | 1.67 | 3.19 |

- **Harmonic entropy** (how ambiguous a dyad is as a ratio; percentile across the octave):

| Interval | Percentile |
|---|---|
| P5 | 4% |
| M3 | 18% |
| golden third | 27% |
| m3 | 34% |
| golden sixth | 65% |
| **golden fifth** | **69%** |

- **Reading:**
  1. With harmonic timbres the golden triad is **unstable**: rougher than major, minor and augmented, with its tension concentrated in the **golden fifth**, one of the most ambiguous intervals there is. It is a good passing chord, as the vision says. (Diminished is rougher still: the golden triad is rougher than every common Western triad except diminished.)
  2. With **golden-spectrum timbres** the golden triad becomes the **smoothest** chord and major and minor become rough. Timbre decides which world is at rest: a second new color, and a tool for the bliss texture (§4).

### 1.5 Self-similar combination tones (why golden chords can "glow")
- The ear makes **combination tones**, the strongest being f₂ − f₁ and 2f₁ − f₂.
- For the chain voicing **1 : φ : φ² : φ³ tuned exactly**, φⁿ − φⁿ⁻¹ = φⁿ⁻² means **every combination tone lands exactly on a golden-chain pitch**. There are 6 distinct tones, all chain pitches, with 0 Hz error. The chord's by-products *are* the chord: a self-similar cascade with no foreign pitches.
- **In 36-ET** the same voicing misses by at most **0.2 Hz** (at a 110 Hz root): very slow, breathing beats.
- **In close voicing** (C vE ^G B, exact) the misses reach **3.5 Hz** at a 110 Hz root, and scale linearly with register (≈7 Hz at 220 Hz). That is a *monaural* beat in the delta-to-theta range, produced inside the ear by the chord itself.
- **The beat rates of close voicings are golden too.**
  - Cg beats at f₀·φ⁻⁶ × {1, 2/φ, 2}.
  - Cg (close) beats at 6.13 and 7.58 Hz = f₀·φ⁻⁶ × (1, 2/φ), plus 12.26 Hz = 2 × 6.13 Hz from a doubled harmonic pair (root harmonic 6 against fifth harmonic 4).
  - The golden seventh Cg7 (1 : 2/φ : 4/φ² : 8/φ³) beats at 6.13, 7.58 and 9.37 Hz = f₀·φ⁻⁶ × (1, 2/φ, 4/φ²): the golden *triad* in rhythm.
  - Cg7 also beats at 12.26 Hz, the golden seventh against the root's octave, because **8/φ³ = 2 − 2φ⁻⁶**.
  - A beat at the golden seventh's own ratio (11.58 Hz) does not occur.
  - For a golden chord on f₀ = 110 Hz (A2) the rates are 6.13, 7.58, 9.37 and 12.26 Hz.
- These three knobs (**voicing** chain vs close, **tuning** exact vs 36-ET, **register**) let us design the beat rates a golden chord produces. This is the technical bridge to the bliss goal (§4).

### 1.6 The silver triad and the micro-altered family
- **Golden minor third** = ^m3 = 10 sixth-steps (333.33 c): 2/3 minor, 1/3 major.
- **Silver triad** = root + golden minor third + a fifth. The fifth is the author's choice. The natural candidates:

| Candidate | Steps | Character |
|---|---|---|
| **vP5** | 0, 10, 20 | Equal stacked golden minor thirds (mirror of golden's construction); **exact centroid of minor, major and diminished**, just as golden is of major, minor and augmented |
| **P5** | 0, 10, 21 | A "brightened minor" with a pure fifth |
| **^P5** | 0, 10, 22 | Shares the golden fifth |

- **Exact definition: open.** The ^m3 isn't a short golden-chain interval. The nearest exact candidates are the 22-step chain interval (328 c) and the silver-ratio third (1+√2)/2 (326 c). Alternatively the silver triad can stay a 36-ET object.
- **The wider family:**
  - fifths at v, ^, vv, ^^ (micro-diminished to micro-augmented);
  - 7ths at m7 (30), ^m7 (31), vM7 (32), M7 (33), ^M7 (34);
  - golden-third and golden-minor-third combinations.
- The notation (§5.3) can write all of these as alteration lists. **Scope for now: golden major and golden major seventh only.** Silver and the rest come after the first études.

---

## 2. Sub-chromatic passing chords (the voice-leading expansion)

### 2.1 Method
1. Take two chords X → Y (diatonic, or chromatic such as ♭VI, III, iv, ♭II) and their **smoothest 12-ET voice leading**.
2. In 36-ET every semitone of motion is 3 sixth-steps. **Expand** the motion by letting each voice stop at 1/3 or 2/3 of its move.
3. Classify every intermediate chord. The **golden** ones are the passing chords the voice leading *picks out*. They are not chosen by taste: they fall out of the motion.
4. **Synchronous** (all voices at the same fraction) gives the purest passing chord. **Staggered** (voices arriving at different times) gives more options and is natural for sustained, legato textures.

### 2.2 What it finds (triads, synchronous; C major unless noted)

| Progression | Smoothest moves (sixth-steps per voice) | Golden chord picked out |
|---|---|---|
| I → IV (C → F) | C 0, E +3, G +6 | **vFg** (vF ^Ab C) at 2/3 |
| IV → I (F → C) | reverse | vFg |
| I → V (C → G) | C −3, E −6, G 0 | **vCg** (vC ^Eb G) at 1/3 |
| V → I (G → C) | reverse | vCg |
| ii → vi (Dm → Am) | | **Ag** |
| iii → vi (Em → Am) | | **Eg** |
| vi → ii, vi → iii | | Ag, Eg |
| I → ♭VI (C → Ab) | C 0, E −3, G +3 | **Cg** at 1/3 (the central example: contrary semitones split in thirds) |
| I → III (C → E) | | **Eg** |
| I → VI (C → A) | | **^Cg** |
| I → ♭III (C → Eb) | | **^Ebg** |
| IV → ♭II (F → Db), V → ♭III (G → Eb) | | Fg, Gg |
| i → iv (Cm → Fm), i → III (Cm → Em) | | Cg, vCg |
| V → III (G → E), IV → II (F → D) | | ^Gg, ^Fg |

- Precisely (the quality theorem, [GOLDEN_THEORY.md §2.4](GOLDEN_THEORY.md)): a strict golden passing chord exists **exactly** when both chords have the same quality (major–major or minor–minor) and their roots are a third or a fifth apart. It is then unique.
  - In a major key: I–IV, I–V, ii–vi, iii–vi, plus all chromatic mediants.
  - Stepwise and mixed-quality pairs need natural paths (§2.3 and GOLDEN_THEORY §2.6).
- Parallel chromatic motion (C → Db, G → Ab, Em → Fm: every voice +1 semitone) yields several staggered golden and silver chords. These are the "inside the chromatic slide" colors.

### 2.3 Golden sevenths (staggered)
Chromatic seventh-chord motions pass through golden sevenths:

| Motion | Golden seventh |
|---|---|
| G7 → Abmaj7 (deceptive) | **^Gg7** |
| Fmaj7 → E7 (Phrygian or Andalusian cadence) | **^Eg7** |
| Em7 → Fm7 (parallel) | **Eg7** |
| Cm7 → E7, Cm7 → Db7 | **Cg7** |
| Bm7b5 → Cm7 | **Bg7** |
| Am7 → Db7 | **Ag7** |

Golden sevenths appear only when the voices arrive at different times: a natural fit for legato strings, pads and piano with pedal.

### 2.4 Rules that follow
1. **A golden chord is defined by its neighbors.** Writing "golden passing chord here" is enough. The engine derives which one from the voice leading (§5.4).
2. **Placement:** between the two chords, on a weak beat or as a short duration (an eighth to a half note at moderate tempo). At 2/3 position it leans toward the destination, at 1/3 toward the origin.
3. **Voicing:** keep the smoothest voice leading (the passing chord exists only on that path). Sustain or glide the moving voices so the sub-chromatic motion is audible.
4. **Preferred progressions to start with:** I→♭VI→I via Cg; I→IV via vFg; V→I via vCg; G7→Abmaj7 via ^Gg7; Fmaj7→E7 via ^Eg7.

---

## 3. Golden colors as destinations (not only passing)

Passing is the main use. The golden major and golden major seventh can also be **held** as colors:
- **On harmonic timbres:** a held golden chord is suspense, unreality, "the impossible". Use it briefly and resolve (Cg → C, or Cg → Ab).
- **On golden-spectrum timbres:** a held golden chord is luminous and stable, an "otherworldly consonance". This is the bliss texture's home.
- **Cmaj7 ↔ Cg7:** bend only the inner voices. A shimmering, breathing seventh (the core sound of the first études).

---

## 4. Bliss: beats, binaural and self-similar sound

The original aim is a blissful state, akin to binaural beats. The engine can't claim effects on the brain. Evidence for binaural-beat entrainment and mood effects is mixed: a 2019 meta-analysis reports a medium pooled effect on memory, attention, anxiety and pain (g = 0.45), while a 2023 systematic review of EEG entrainment (Ingendoh, Posny & Heine) found 5 of 14 studies consistent with entrainment and 8 contradicting it. What the engine *can* do is **design and measure the beating precisely**, so listening experiments are repeatable.

| Mechanism | What creates it | Engine control |
|---|---|---|
| **Self-similar combination tones** | Chain voicing in exact tuning: by-products are chord tones (§1.5) | `voicing: chain`, `tuning: golden_exact` |
| **Monaural beats** | Near-coincident partials and combination tones in close voicings; rate grows with register | `beats:` target band, e.g. `beats: {target_hz: [4, 8], via: register}`. The engine picks the octave and voicing that place the dominant beats in band |
| **Binaural beats** (headphones) | The same tone at f in the left ear and f + Δ in the right; the brain perceives Δ | Per-part `binaural: {beat_hz: 6, voices: [root, fifth]}`. Golden chord voices get mirrored L/R detunes, with Δ optionally swept over time (e.g. 10 → 6 Hz) |
| **Isochronic pulse** | Slow amplitude modulation | `pulse: {hz: 6, depth: 0.15}` on pads |
| **Golden breathing** | Very slow beats from 36-ET vs exact differences (≈0.2 Hz) | `tuning: 36edo` with chain voicing: a ~5-second "breath" |

**Analysis tools:**
- A **beat spectrum** per chord: every partial pair and combination tone within 15 Hz of another, with its rate and strength.
- A **beat-rate curve** over the song in `qa.json` and `qa.png`.
- QA rules such as `beats_in_band: {section: bliss, band: [4, 8], min_share: 0.6}`.

**Safety and claims:**
- Moderate levels.
- No strong infrasound.
- Binaural content marked "headphones".
- Videos and notes describe the music, never promise effects.

---

## 5. Notation in SongMap

### 5.1 Tuning
```yaml
tuning: 36edo           # unifying tuning: Western exact, golden within 0.75 c
# tuning: golden_exact  # chain-related notes at exact phi ratios (self-similar combination tones)
```
✅ **Implemented** (`songmap/theory/tuning.py`). `tuning: 36edo` is accepted.
- A 12edo song whose chords or notes leave the 12-step grid is an error that names the fix.
- 12-ET songs render bit-identically to before (the golden hash tests pass).

### 5.2 Ups and downs
✅ **Implemented.** `^` raises and `v` lowers by one sixth-step, written as a **prefix**: in letter, `deg:` and `rel:` motifs, chords inside motifs, grace notes, chord roots and keys. The accent `^` stays a suffix.

| Where | Examples |
|---|---|
| Notes | `^c4`, `ve8`, `^^g`, `^c4^` (C-up quarter, accented) |
| Degrees | `^3`, `v5/8.`, `vb7` |
| Chord-relative tones | `v3`, `^5` |
| Chord roots | `^C`, `vEb`, `^F#m7` |
| Keys | `key: ^D minor`, `key: vE golden13` |

### 5.3 Chord symbols

| Symbol | Notes | Status |
|---|---|---|
| `Cg` | C vE ^G | ✅ **first focus** |
| `Cg7` | C vE ^G B | ✅ **first focus** |
| `Cs` | C ^Eb vG | ✅ silver (0-10-20), the average of major, minor and diminished |
| `CT13` | C ^E vA | ✅ **bronze** (0-13-26), golden's passing partner |
| `C(v3,^5)` | | general alteration lists: any chord tone bent by sixth-steps, so the whole micro-altered family is writable: `C(^5)`, `C(v3,^^5)`, `Cmaj7(v3,^5,^7)`. `Cg` = `C(v3,^5)` |
| `Cg@chain` | 1 : φ : φ² | chain voicing (likewise `Cg7@chain` = 1 : φ : φ² : φ³) |

### 5.4 Passing-chord placeholders (the voice-leading expansion, written compactly)
```
# YAML: harmony: {progressions: {walk: "..."}} or a section's harmony: "..."
"G:1 ~:0.5 ~:0.5 C:2"          # System 1 (strict): both passing chords of the unique path (vEbT13/G, vCg/G)
"C:1.5 ~:0.5 F:2"              # System 1, one placeholder: the strict path's better passing chord (vFg/C)
"F:1 ~g:0.5 ~g:0.5 G:2"        # System 2 (natural): two golden chords (vF#g, ^F#g)
"G7:1.5 ~g7:0.5 Abmaj7:2"      # prefer a golden seventh
"C:1 ~g@1/3:0.5 Ab:1.5"        # force the 1/3 position
```
- ✅ **Implemented** in `songmap/theory/passing.py`. The engine computes the four-part voice leading, expands it in sixth-steps, and inserts the chord(s).
  - `~` = System 1 (strict).
  - `~g` / `~g7` = System 2 (natural, golden preferred).
  - Runs of two placeholders ask for P1 and P2. Progressions loop, so a placeholder can bridge back to the start.
- ✅ The `voiced` styles (`hold`, `comp`, `pulse`, `top`, `bassline`) play the passing engine's own four lines for every passing run (bass + three upper voices, one octave shift per run), and voice-lead all other chords in the song's tuning. `top` turns the soprano into a melody.
- Planned (not implemented): an error listing the nearest options when no golden chord exists, and a `songmap theory pass X Y` command that prints the analysis. Today `songmap check` shows the resolved chords.

### 5.5 Example (first-focus étude)
```
song "Golden Étude No. 1 — passing light" 72 4/4 C tuning=36edo seed=36 fps=30
inst keys=keys/felt_piano strings=strings/legato bell=bell/golden_spectrum
feel keys time=8 arch=.5
prog walk  "C:1.5 ~g:0.5 F:1.5 ~g:0.5 | G7:1.5 ~g7:0.5 Abmaj7:2 | Fmaj7:1.5 ~g7:0.5 E7:2 | Am:1.5 ~g:0.5 C:2"
prog shine "Cmaj7:2 Cg7:2 | Cmaj7:2 Cg7@chain:2"
a  8 | keys:block(voicing=smooth) strings:sustain prog=walk dyn=p<mf
b  4 | bell:sustain strings:sustain(dyn=pp) prog=shine -keys | !swell@+2(part=strings,dyn=pp<p)
```

---

## 6. Infrastructure

| # | Component | Status / details |
|---|---|---|
| 1 | **Tuning layer** | ✅ `Tuning(36)`, `tuning: 36edo`, ups/downs parsing (`split_updown`), grid check. *Still to add:* `GoldenExact` (exact φ cents) |
| 2 | **Parser** | ✅ `^`/`v` everywhere; `g`, `g7`, `s`, `T13` qualities; alteration lists `C(v3,^5)`; `~`, `~g`, `~g7` placeholders; scales golden3/4/7/10/13/23 and silver13. *Still to add:* `@chain` voicing |
| 3 | **Passing-chord engine** `theory/passing.py` | ✅ Systems 1 and 2, four-part (bass + three upper voices), classification (golden, golden-over-pedal, silver or bronze, planing, micro-altered) |
| 4 | **Golden theory catalog** `theory/golden.py` | Chain, MOS scales, 36 transpositions, golden triads in a scale, centroid, `deform()` |
| 5 | **Consonance and beat analysis** `analysis/` | Roughness and harmonic entropy on the instruments' real rendered spectra; **beat spectrum** and **combination-tone map**; tension curve and beat-rate curve in `qa.json`/`qa.png`; QA rules `golden_resolves`, `tension_profile`, `beats_in_band` |
| 6 | **Bliss rendering** | `binaural:` per-part L/R detune (swept Δ), `pulse:` isochronic AM, `beats:` register/voicing auto-placement, chain voicing |
| 7 | **Clean and golden-spectrum instruments** | ✅ `clean` additive instrument (exact partials, Schroeder phases, raised-cosine envelopes; `spectrum` harmonic / golden / odd) with presets `clean/sine`, `organ`, `keys`, `bass`, `lead`, `glass` (golden spectrum), `golden_pad`. Still presets for `keys`, `epiano`, `pad`, `string_pluck`. `master: clean` (peak normalization only); `songmap render --mp3` |
| 8 | **Export** | Three-layer MIDI (one channel per layer with a fixed bend), MPE for glides and staggered passing, Scala `.scl`/`.kbm`, optional MTS |
| 9 | **GUI** | 3-row layer keyboard; chord explorer (per-voice sixth-step sliders; live roughness, entropy and **beat-rate** meters); **passing-chord finder** (pick X and Y, hear the expansion); headphones mode for binaural A/B |

---

## 7. Composition guide (first focus: golden major and golden major seventh)
1. **Start from a Western progression** and insert `~g` / `~g7` passing chords between chords whose voice leading picks one out (§2.2–2.3). Two or three per phrase is plenty.
2. **Hear the sub-chromatic motion.** Sustain or legato the moving voices (strings, pads, felt piano with pedal). The ear should follow a semitone being divided in three.
3. **Shine moments:** alternate Cmaj7 ↔ Cg7 (inner voices only) over a pedal. Use chain voicing 1 : φ : φ² : φ³ for the luminous, self-similar version.
4. **Timbre decides rest vs tension.** Golden chords on bells or golden-spectrum pads can be held; on strings or piano they pass.
5. **Bliss sections:** golden-spectrum pad + chain voicing + exact tuning. Place beats at 4–8 Hz via register, add an optional binaural layer (headphones), slow tempo or no pulse, long reverb.
6. **Later explorations:** the silver triad, micro-altered fifths and 7ths, golden13 melodies running through the layer seams, and modulation between the three 12-ET layers through golden pivots.

---

## 8. Plan (ROADMAP P10)

| Phase | Scope | Done when |
|---|---|---|
| **G0: Theory spec** | ✅ Vision captured (§0). Still open: names, silver fifth, exact vs 36-ET defaults (§9) | §9 answered |
| **G1: 36-ET core ✅** | `Tuning(36)`, `GoldenExact`, ups/downs parsing, `g`/`g7`, alteration lists, `@chain` | §5.5 parses; FFT-measured pitches within 1 c |
| **G2: Passing engine ✅** | `theory/passing.py`, `~`/`~g`/`~g7` (a `songmap theory pass` command is planned) | §2.2–2.3 tables reproduce from the CLI |
| **G3: First études ✅ (first pass)**: `golden_audio/index.html`, 15 technique portfolios | 3–4 short pieces on golden major and golden maj7 only: (1) passing light (§5.5); (2) Cmaj7 ↔ Cg7 shimmer; (3) a chromatic slide with staggered golden sevenths; (4) a bliss drone with chain voicing | The author approves by ear |
| **G4: Analysis and bliss tools** | Beat spectrum, combination-tone map, curves in QA; `binaural`/`pulse`/`beats` | Étude 4's measured beat rates land in the requested band |
| **G5: Golden timbres** | `spectrum:` param + presets | §1.4's roughness ordering reproduces from rendered audio |
| **G6: Export and GUI** | Layer MIDI, Scala, MPE; GUI explorer and passing finder | Études open in a DAW; the GUI passing finder plays §2.4's progressions |
| **G7: The family** | Silver triad, micro-altered fifths and 7ths, golden13 melody, layer modulation | Defined with the author; one étude each |

---

## 9. Questions for the author
1. **Silver triad fifth:** vP5 (equal stacked thirds, the centroid of minor/major/diminished), P5, or ^P5? Should its third be exactly 10 sixth-steps, or an exact irrational ratio (and which)?
2. **Exact or 36-ET by default:** exact φ makes the chain voicing's combination tones coincide perfectly; 36-ET gives slow "breathing" beats. Which is the default "golden"?
3. **The voice-leading expansion:** §2.1 is our reading of "well-defined ways to expand melodies of voice leading". Is it yours, or do you weight or select differently (for example only synchronous, only the 1/3 point, or melodic voices first)?
4. **Names:** Cg / Cg7 / Cs, "golden major", "golden major seventh", "silver". Any preferred symbols?
5. **Bliss targets:** which beat bands (delta, theta, alpha), and is headphone-only binaural content acceptable for the first études?
