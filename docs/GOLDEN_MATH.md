# The mathematics and history of golden harmony

The math behind the golden Pythagorean system: commas, limmas and apotomes, well-formed scales, the averaging principle, the metallic triads, and where all of it sits in the history of tuning. Companion to [GOLDEN_THEORY.md](GOLDEN_THEORY.md) (classification and new progressions) and [GOLDEN_HARMONY.md](GOLDEN_HARMONY.md) (notation and engine).

Every number here is reproduced by `reference/golden/explore.py`, `classify.py` and `passing.py`. ("c" = cents, 1200 per octave; a sixth-step = 33.33 c.)

---

## 1. Two generators, one method

A **Pythagorean-type scale** is made by stacking one interval, the *generator*, and folding the results back into one octave. Pythagoras used the fifth 3/2; the golden Pythagorean scale uses φ = (1+√5)/2, a sixth of 833.09 c.

| | Pythagorean | Golden Pythagorean |
|---|---|---|
| Generator | fifth 3/2 = 701.96 c | golden sixth φ = 833.09 c |
| Generator as a fraction of an octave | log₂(3/2) = 0.58496… | log₂φ = 0.69424… |
| Continued fraction | [0; 1, 1, 2, 2, 3, 1, 5, …] | [0; 1, 2, 3, 1, 2, 3, 2, …] |
| Best "n generators ≈ m octaves" | 12 fifths ≈ 7 octaves | **13 golden sixths ≈ 9 octaves** |
| Comma (the overshoot) | (3/2)¹²/2⁷ = **23.46 c** (Pythagorean comma) | φ¹³/2⁹ = **30.17 c** (golden comma) |
| Equal temperament that removes the comma | 12-ET (fifth = 7/12 octave) | 13-ET (golden sixth = 9/13 octave = 830.77 c, 2.3 c flat) |
| Next comma | 53 fifths ≈ 31 octaves (3.6 c) | 36 golden sixths ≈ 25 octaves: φ³⁶/2²⁵ = **−8.75 c** |
| Unifying temperament | — | **36-ET** removes the 36-comma: golden sixth = 25 steps, within 0.24 c; it also contains 12-ET exactly |

**Why 36:** 36-ET is to the golden chain what 12-ET is to the fifths. It removes a golden comma, here the 36-chain one, so the golden circle closes after 36 steps. On top of that it contains Western 12-ET exactly. No other small tuning does both.

## 2. Limma, apotome, comma

In Pythagorean tuning the chromatic scale has **two different semitones**:
- **limma** (Greek *leimma*, "remnant") = 256/243 = **90.22 c**: the diatonic semitone, as in E–F;
- **apotome** (Greek *apotomē*, "a cutting-off") = 2187/2048 = **113.69 c**: the chromatic semitone, as in F–F#.

A whole tone 9/8 (203.91 c) = limma + apotome. **Apotome − limma = the Pythagorean comma** (23.46 c). The two sizes exist because 12 fifths overshoot 7 octaves; equal temperament makes them equal by spreading the comma out.

The golden Pythagorean 13-note scale has the same structure:
- **golden apotome** = φ³/4 = **99.27 c**, three golden sixths minus two octaves (the larger step, which 36-ET renders as 3 sixth-steps = 100 c);
- **golden limma** = 2⁷/φ¹⁰ = **69.10 c**, seven octaves minus ten golden sixths (the smaller step, which 36-ET renders as 2 sixth-steps = 67 c);
- **golden apotome − golden limma = the golden comma** (30.17 c), exactly as in the Pythagorean case.

The golden13 scale has 10 apotomes and 3 limmas (10 × 99.27 + 3 × 69.10 = 1200).

## 3. Well-formed scales (moments of symmetry)

Stack the generator *n* times. The **three-gap theorem** says the resulting scale has at most three step sizes. It has exactly two, making it a *well-formed* or *moment-of-symmetry* (MOS) scale, exactly when *n* is a denominator on the generator's path through the **Stern–Brocot tree**.

| | Path (fraction of an octave) | Well-formed sizes |
|---|---|---|
| Fifth | 1/2, 2/3, 3/5, 4/7, 7/12, 10/17, 17/29, 24/41, 31/53 | 2, 3, **5** (pentatonic), **7** (diatonic), **12** (chromatic), 17, 29, 41, 53 |
| Golden sixth | 1/2, 2/3, 3/4, 5/7, 7/10, 9/13, 16/23, 25/36 | 2, 3, **4**, **7**, **10**, **13**, **23**, **36** |

**Nested step sizes.** Each MOS splits the larger step of the previous one:

| Scale | Pythagorean steps | Golden steps |
|---|---|---|
| Diatonic / golden7 | tone 203.9 c (= apotome + limma) and limma 90.2 c | 267.6 c (= 2 apotomes + limma) and golden apotome 99.27 c |
| golden10 | — | 168.4 c (= apotome + limma) and 99.27 c |
| Chromatic / golden13 | apotome and limma | golden apotome 99.27 c and golden limma 69.10 c |

### Your question: is "7 notes" related to 2⁷, and is there a natural 9-note golden scale?
- **The 7 in 2⁷** is the *numerator* of 7/12: twelve fifths are seven octaves, because a fifth is 7 of the 12 chromatic steps. **The 7 notes of the diatonic** are a *denominator*: 4/7, the step before 7/12 on the Stern–Brocot path (a fifth is 4 of the 7 diatonic steps). The two 7s coincide because 7/12 = (3+4)/(5+7), the mediant of 3/5 and 4/7. They are arithmetically linked, but neither causes the other. The same coincidence would make a 24-note scale from 24/41, and that isn't well-formed.
- **The 9 in 2⁹** means the golden sixth spans 9 of the 13 golden-chromatic steps, the exact counterpart of "the fifth spans 7 semitones". But **9 is not a well-formed size of the golden chain**: nine golden sixths give three step sizes (99.3, 168.4 and 267.6 c). The parents of 9/13 are 2/3 and 7/10, so golden13's well-formed sub-scales are **golden10** and, before it, **golden7** and golden4.
- **The natural golden "diatonic" is golden7.** It has 7 notes like the diatonic, and two step sizes:

  **C C# vE vF ^G ^A♭ B** (steps 3, 8, 3, 8, 3, 8, 3 sixth-steps)

  Its chord vocabulary stays entirely inside the golden system:
  - five golden triads: Cg, C#g, vEg, vFg, ^A♭g;
  - four golden sevenths: Cg7, C#g7, vFg7, ^A♭g7. The tonic golden seventh Cg7 = C vE ^G B is in the scale.

  Natural golden progressions move between these chords, for example by golden-circle steps (neighbours share two notes). See "Golden Diatonic" in the audio suite.

## 4. Interval content: where the familiar intervals hide in the golden chain

Every interval of a golden scale is some number of golden sixths, folded into the octave.

| Chain distance | Exact | 36-ET | Meaning |
|---|---|---|---|
| 1 | 833.1 c | 25 | **golden sixth** (inverts to the **golden third** 366.9 c) |
| 2 | 466.2 c | 14 | inverts to the **golden fifth** 733.8 c |
| 3 | 99.3 c | 3 | **golden apotome** (semitone) |
| 9 | 297.8 c | 9 | **minor third**, 2 c from 12-ET |
| 11 | 764.0 c | 23 | inverts to the **bronze third** 436.0 c ≈ 9/7 (435.1 c) |
| 12 | 397.1 c | 12 | **major third**, 3 c from 12-ET |
| 13 | 30.2 c | 1 | **golden comma** |
| 14 | 863.3 c | 26 | inverts to the **silver third** 336.7 c ≈ 17/14 (336.1 c) |

Consequences for the scales:
- **golden13** (chain distances up to 12) contains golden thirds (12 of them), minor thirds (4), bronze thirds (2) and one major third. It contains **no silver third**: that needs chain distance 14.
- **Silver first appears in golden23 and in full 36-ET.** It *is* a golden-chain interval (exactly 336.7 c), just a distant one, and 36-ET renders it as 10 sixth-steps.

## 5. The averaging principle (barycentric harmony)

**Definition.** On a common root, write each triad as (third, fifth) in sixth-steps:

| Triad | (third, fifth) |
|---|---|
| major | (12, 21) |
| minor | (9, 21) |
| augmented | (12, 24) |
| diminished | (9, 18) |

**The principle:** a new chord can be formed as the **average of Western chords**, voice by voice. With three chords the averages land exactly on the 36-ET grid.

All 16 averages of three triads on C (the 20 multisets of three qualities give 16 chords; four are reached twice):

| (third, fifth) | Chord | Average of |
|---|---|---|
| (9, 18) | C E♭ F# | dim + dim + dim (diminished) |
| (9, 19) | C E♭ ^F# | min + dim + dim |
| (9, 20) | C E♭ vG | min + min + dim |
| (9, 21) | C E♭ G | min + min + min (minor) |
| (10, 19) | C ^E♭ ^F# | maj + dim + dim |
| (10, 20) | **C ^E♭ vG (silver)** | **maj + min + dim**, or aug + dim + dim |
| (10, 21) | C ^E♭ G | maj + min + min (the Picardy step), or min + aug + dim |
| (10, 22) | C ^E♭ ^G | min + min + aug |
| (11, 20) | C vE vG | maj + maj + dim |
| (11, 21) | C vE G | maj + maj + min, or maj + aug + dim |
| (11, 22) | **C vE ^G (golden)** | **maj + min + aug**, or aug + aug + dim |
| (11, 23) | C vE vA♭ | min + aug + aug |
| (12, 21) | C E G | maj + maj + maj (major) |
| (12, 22) | C E ^G | maj + maj + aug |
| (12, 23) | C E vA♭ | maj + aug + aug |
| (12, 24) | C E A♭ | aug + aug + aug (augmented) |

- **Your own description, made exact:** the golden third is "2/3 major, 1/3 minor", i.e. (12+12+9)/3 = 11. The golden fifth is "2/3 perfect, 1/3 augmented", i.e. (21+21+24)/3 = 22. The silver third is 2/3 minor and 1/3 major, (9+9+12)/3 = 10; the silver fifth is 2/3 perfect and 1/3 diminished, (21+21+18)/3 = 20.
- **Golden and silver are the centroids** of the bright triple (major, minor, augmented) and the dark triple (major, minor, diminished). No other three Western triads average to these two chords except augmented+augmented+diminished (for golden) and augmented+diminished+diminished (for silver).
- **Passing chords are averages too.** On a uniform path, P₁ = (2X + Y)/3 and P₂ = (X + 2Y)/3 voice by voice. Golden passing chords are the averages that land on the golden chain. For example Cg = (2·C + A♭/C)/3 on the move C → A♭.
- **Universality:** *every* 36-ET chord is an average of three 12-ET chords, because any sixth-step pitch is a sum of three semitone pitches divided by 3. The principle's musical content is in averaging *related* chords: same root, neighbouring qualities, chords adjacent in a progression.
- **Connection to chord geometry:** in Tymoczko's chord spaces, voice-leading distance is a straight line and the augmented triad (the most even triad) sits at the center. Averaging is moving along those lines, and golden and silver are near-central points. That is why they connect efficiently to many chords and make good passing chords.

## 6. The metallic triads: the equal-third line

Stack two equal thirds of *n* sixth-steps, T_n = {0, n, 2n}:

| n | Third | Name | Notes on C | Remarks |
|---|---|---|---|---|
| 8 | 267 c | T8 | C vE♭ ^F | silver reflected through diminished |
| 9 | 300 c | diminished | C E♭ F# | Western |
| 10 | 333 c (exact chain: 336.7 c) | **silver** | C ^E♭ vG | average of maj + min + dim |
| 11 | 367 c (exact 366.9 c) | **golden** | C vE ^G | average of maj + min + aug; stacked 2/φ |
| 12 | 400 c | augmented | C E A♭ | Western; the center of chord space |
| 13 | 433 c (exact chain: 436.0 c) | **bronze** | C ^E vA | golden reflected through augmented (2·aug − golden); third ≈ 9/7 |

- These are evenly spaced points on **one straight line**. One uniform path runs Caug → Cg → Cs → Cdim (the root holds; the third falls one sixth-step and the fifth two per chord).
- **Bronze is golden's partner:** on every strict path between two major triads (or two minor triads) a third or fifth apart, the passing chord that isn't golden is bronze (or silver, between augmented and diminished). Example: V → I = G – vE♭ bronze – vCg – C.
- **Naming.** "Silver" is fixed by the averaging principle (the dark-side centroid). "Bronze" names T13, continuing the metallic-means sequence golden (1), silver (2), bronze (3). The metallic-mean numbers themselves (1+√2, (3+√13)/2) are *not* these chords' ratios; the names follow the ordering, not the numbers.

**Which stacked thirds cycle through all 36 notes?**

| Third | Notes before it repeats |
|---|---|
| minor (9) | 4 (a diminished seventh) |
| silver (10) | 18 |
| **golden (11)** | **36** |
| major (12) | 3 |
| **bronze (13)** | **36** |

Only golden and bronze thirds walk through every note, because only 11 and 13 share no factor with 36. That is why the golden circle exists. Silver doesn't need to cycle: it is defined by averaging, not generated by stacking.

## 7. Two systems of passing harmony

- **System 1 (strict, the unique path).** A half step splits into 1 + 1 + 1 sixth-steps and a whole step into 2 + 2 + 2.
  - At most one golden chord per transition (theorem).
  - Golden chords occur exactly between same-quality triads a third or fifth apart (the quality theorem), and the partner is bronze or silver.
  - SongMap: `~` placeholders.
- **System 2 (natural).** Half steps still split evenly, but whole steps may split unevenly into monotone parts of at most a semitone.
  - Two different golden chords can follow each other: 46 pairs get two, 181 get at least one.
  - Roots a whole step apart get two golden chords on the chromatic root between (the golden escalator).
  - SongMap: `~g` placeholders.

**Why uneven splits are natural:** Pythagorean tuning already splits the whole tone unevenly (limma + apotome), and golden13 splits its steps into golden apotome + golden limma. System 2 lets voice leading use the same unevenness.

## 8. History (brief)

**Pythagorean tuning and its successors**
- **Origins.** The fifth-generated scale is attributed to Pythagoras (6th c. BCE) by later writers. Philolaus (5th c. BCE) and Plato's *Timaeus* (c. 360 BCE) describe its ratios, including the tone 9/8 and the limma 256/243. Boethius (*De institutione musica*, early 6th c. CE) carried this theory into medieval Europe, together with the terms limma, apotome and comma.
- **The comma problem** drove the history of temperament:
  - meantone tunings in the Renaissance (described by Zarlino in the 16th century);
  - equal temperament computed by Zhu Zaiyu (1584) and Simon Stevin (c. 1605), and popularized by Mersenne (1636);
  - the *well* temperaments of Werckmeister (1691) and others.
- **Bach's *Well-Tempered Clavier*** (Book I 1722, Book II 1742) demonstrated music in all 24 major and minor keys under such a temperament. It is the model for this project's *Well-Tempered Golden Clavier*: 72 major and minor keys plus 36 golden13 and 36 silver13 scales, at a much faster harmonic rhythm.

**36-ET and microtonal notation**
- **Busoni**, in *Sketch of a New Esthetic of Music* (1907), proposed dividing the whole tone into thirds and combining two such series, which amounts to sixth-tones, i.e. 36-ET.
- **Alois Hába** composed in quarter-, third- and sixth-tones in the 1920s–30s.
- **Notation:** the `^`/`v` accidentals follow Kite Giedraitis' "ups and downs" notation for equal divisions of the octave.

**The golden ratio**
- **Mathematics:**
  - Euclid's *Elements* (Book VI) defines division in "extreme and mean ratio".
  - Fibonacci's *Liber Abaci* (1202) gives the sequence whose ratios approach φ.
  - Pacioli's *De divina proportione* (1509, illustrated by Leonardo) popularized it.
  - The name "golden section" comes from the 19th century.
- **In music:**
  - φ has been used mostly for *form and proportion*: Ernő Lendvai's analyses of Bartók, and Roy Howat's of Debussy (*Debussy in Proportion*, 1983).
  - It has also been used for *tuning*: the "golden meantone" associated with Thorvald Kornerup, and Heinz Bohlen's 833-cent scale built on the φ interval.
  - This project's distinct contributions are the golden *Pythagorean* chord system, the averaging principle and the passing-chord classification.

**Mathematics used here**
- **Continued fractions and best approximations.** Hurwitz's theorem (1891) makes φ the hardest number to approximate by fractions; its continued fraction is all 1s.
- **The Stern–Brocot tree** (Stern 1858, Brocot 1861).
- **The three-gap theorem** (conjectured by Steinhaus; proved in the late 1950s by Sós, Świerczkowski and Surányi).
- **Erv Wilson's moment-of-symmetry scales** (1970s).
- **KAM theory** (Kolmogorov 1954, Arnold 1963, Moser 1962). The golden-mean torus is the most robust quasi-periodic motion (Greene, 1979).

**Hearing and the brain**
- **Consonance as roughness:** Plomp & Levelt (1965), extended to arbitrary timbres by Sethares (*Tuning, Timbre, Spectrum, Scale*, 1998), the basis for golden-spectrum timbres.
- **Harmonic entropy:** Paul Erlich (1990s).
- **Chord geometry:** Dmitri Tymoczko, "The Geometry of Musical Chords" (*Science*, 2006) and *A Geometry of Music* (2011).
- **The golden-mean EEG hypothesis:** Pletzer, Kerschbaum & Klimesch (2010, *Brain Research*) and Roopun et al. (2008, *Frontiers in Neuroscience*). It suggests that golden ratios between brain rhythms avoid unwanted synchronization.
- **Binaural beats:** a 2019 meta-analysis (Garcia-Argibay, Santed & Reales) found small effects on anxiety, memory and attention. These are hypotheses for this project's listening experiments, not claims.
