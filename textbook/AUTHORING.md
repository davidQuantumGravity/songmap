# Authoring guide: "Harmony, Rational and Golden"

Read this whole file before writing. The table of contents is canonical: `textbook/toc.yaml`.

## 1. What the book is

A self-contained textbook that builds music theory from first principles, mathematically, and develops Western harmony and the **golden tonal system** (golden-ratio harmony in 36-ET) side by side.
- **Readers:** neither a music expert nor a math expert is assumed. Both get the full treatment: every term is defined at first use, every symbol is explained, and nothing is hand-waved in the Derive layer.
- **Voice:** clear, warm, precise, unpretentious. Concrete examples in C first, then generalize. No filler, no hype.
- **Parts I–V** build Western theory; **Parts VI–VII** mirror them in the golden system.
- Western chapters contain **Golden mirror** asides that preview the golden counterpart, with a link. Golden chapters refer back to the Western idea they generalize.

## 2. Files you own

Write only your own chapters' files:
- `textbook/content/<id>.html`: the chapter body as an HTML fragment (no `<html>`, `<head>` or `<body>`; the builder adds the page, title, summary and navigation).
- `textbook/audio/<id>/<name>.songmap.yaml` or `<name>.py`: audio examples.

Do **not** edit `toc.yaml`, the builder, CSS, `_lib.py`, songmap code or other chapters. If you need something you can't express, describe it in your final report.

Validate as you go (all commands from the repo root, with the venv Python):
```bash
.venv/Scripts/python tools/textbook/build.py --check --chapters ch05
```
```bash
.venv/Scripts/python tools/textbook/build.py --test-audio --chapters ch05
```
The first checks structure and references. The second renders your chapter's audio into `build/tbtest/ch05/` and reports errors. Fix everything they report.

## 3. Page structure

- One `<section id="...">` per TOC section, **in TOC order, with exactly the ids in toc.yaml**, each starting with `<h2>` and the TOC title. You may use `<h3>` subsections.
- **Layers** inside sections. Use all three in nearly every section, in this order:
  - `<div class="layer hear">`: intuition and listening. No formulas (numbers in words are fine). An audio example belongs here whenever possible.
  - `<div class="layer understand">`: concepts, notation, worked examples, light math (fractions, logs with explanation), tables.
  - `<div class="layer derive">`: definitions, theorems, proofs or proof sketches, exact values, formulas, small code-like algorithms. Point to `ch:appD` for long proofs.

  Every chapter in Parts I–IX must use all three layers. A purely historical section may skip Derive.
- **Boxes:**
  - `<aside class="mirror">` (Western chapters: how this idea reappears in the golden system, with a link);
  - `<aside class="box math">`, `<aside class="box history">`, `<aside class="box note">`;
  - `<div class="exercise">` with `<details class="answer"><summary>Answer</summary>…</details>`. Aim for 3–6 exercises per chapter: listening tasks, calculations, small proofs.
- **Cross-references:** `<a href="ch:ch05#comma">the Pythagorean comma</a>`. These are checked.
- **Math:** KaTeX, with `$...$` inline and `$$...$$` display. Escape `<` as `&lt;` in prose and math inside HTML. Keep LaTeX simple: `\frac`, `\log_2`, `\varphi`, `\mathbb{Z}_{12}`, `\pmod{12}`, `\approx`, `\cdot`, `^{}`, `_{}`, matrices only if needed.
- **Figures:**
  - `<pianoroll edo="36" notes="G2 G3 B3 D4 ; G2 G3 ^B3 vEb4 ; G2 G3 vC4 ^Eb4 ; C3 G3 C4 E4" labels="G ; vEbT13/G ; vCg/G ; C" title="V → I, strict path"></pianoroll>`. Chords are separated by `;`, notes are names with octave (C4 = middle C), and `^`/`v` prefixes are allowed. Keep the pitch range under about two octaves.
  - `<pc-circle edo="12" marks="0 4 7" path="0 7 2 9 4 11 6 1 8 3 10 5 0" title="..."></pc-circle>`. Pitch classes are steps of the EDO (36-ET: C = 0, ^C = 1, vC# = 2, C# = 3, …).
  - Small inline `<svg>` is allowed (use `currentColor` and CSS variables, never hard-coded black or white).
  - Use HTML `<table>` freely.
- **Length:**
  - Chapters: about 3,000–5,000 words.
  - Front matter: 1,500–3,000 words.
  - Each chapter has **at least 4 audio examples** and **at least 2 figures** (pianoroll, pc-circle, table or svg).

## 4. Audio examples

`<audio-ex src="name" caption="One sentence saying what to listen for."></audio-ex>` plays `textbook/audio/<id>/name.songmap.yaml` or `name.py`. Keep examples **short (5–40 s)** and focused on one point. Captions say what to *listen for*.

### SongMap songs (anything on the 12- or 36-ET grid)

```yaml
songmap: 0.2
title: "V to I, strict path"
tempo: 72
meter: "4/4"
key: "C major"
tuning: 36edo                 # or 12edo for purely Western examples
seed: 1
tail_seconds: 2
instruments: {organ: clean/organ, low: clean/bass, bell: clean/glass}
mix: {organ: {gain_db: -6}, low: {gain_db: -4}, bell: {gain_db: -6, send: {hall: 0.3}}}
sections:
  - {name: a, bars: 4, harmony: "G:1 ~:0.5 ~:0.5 C:2", parts: {organ: hold, low: bassline}}
master: clean
```

**Harmony strings:** `Chord:bars` tokens.
- Chord symbols: C, Cm, Cdim, Caug, Csus4, C7, Cmaj7, Cm7, Cm7b5, Cdim7, C6, Cm6, C9, Cadd9.
- In 36edo also: `Cg` (golden), `Cg7`, `Cs` (silver), `CT13` (bronze), `^C`, `vEbm`, `C(v3,^5)`, `Cm(^3)`.
- `N.C.` = silence.
- Passing placeholders: `~` = System 1 (strict path); `~g`, `~g7` = System 2 (natural). Two in a row = both passing chords P1 and P2.

**Parts:**
- `hold`: four-part voice-led chords, held.
- `comp`: comping rhythm.
- `pulse`: quarter notes.
- `top`: the soprano line as a melody.
- `bassline`: the lowest voice, an octave down.
- Arpeggios: `{style: gentle8, role: arp}`, `{style: roll16, role: arp}`.
- Bass figures: `{style: roots, role: bass}`, `{style: root5, role: bass}`.
- Melody from motifs: define `motifs: {m1: {rel: "R8 3 5 R+ 5 3 R 3"}}` (chord-relative) or `{deg: "0/4 1 2 3", key: "C golden7", octave: 5}` or letter notes `"=mf c4 d e f | g2 e"`. Then use the part `melody: {motifs: [m1], oct: 1}`.

**Instruments** (stable, no wobble):
- `clean/organ` (sustained, harmonic);
- `clean/sine` (pure sine);
- `clean/keys` (struck);
- `clean/bass`;
- `clean/lead`;
- `clean/glass` (golden spectrum, bell);
- `clean/golden_pad` (golden spectrum, sustained);
- `keys/still` (modal piano), `epiano/still`, `pad/still`, `string_pluck/still`.

Always `master: clean`. For dry demonstrations omit sends; for musical examples a hall send of 0.2–0.4 is fine.

**Worked examples:** `examples/golden/etude1_passing_light.songmap.yaml`; generated examples in `examples/golden/suite/*.songmap.yaml`. Validate with `--test-audio`.

### Python examples (exact frequencies, physics demos)
```python
from _lib import SR, PHI, tone, chord, sine, sweep, silence, seq, at, freq

def render():
    # a just major third (5:4) and then a 12-ET major third, on A3 = 220 Hz
    return seq([chord([220, 275], 2.0), silence(0.4), chord([220, freq(57 + 4)], 2.0)])
```
`tone(f, dur, preset="clean/organ")`, `chord([f…], dur)`, `sine(f, dur)` (pure), `sweep(f0, f1, dur)`, `at([(t, clip), …])` to place clips in time. Use Python only when exact ratios or physics are the point: the harmonic series, beats, just intonation, exact φ, combination tones.

### Existing audio you may reference
The golden suite in `golden_audio/` (see `golden_audio/entries.json` for titles), e.g. `P01b_lullaby_in_gold.mp3`, `W1_well_tempered_golden_clavier.mp3`, `R5_exact_beating_golden_seventh.mp3`. Embed with `<audio-ref file="P01b_lullaby_in_gold.mp3" caption="..."></audio-ref>`. Use these for full-length musical illustrations, but make your own short examples for teaching points.

## 5. Notation conventions

- **Notes:** C4 = middle C = MIDI 60; A4 = 440 Hz. Prose uses ♯/♭ or #/b consistently within a chapter (prefer ♯ ♭ in prose and # b in code).
- **36-ET:** a sixth-step = 1/3 semitone = 33.33 c. `^` = up one sixth-step, `v` = down one, written as a **prefix** (^C, vE♭). Write "36-ET" in prose and `36edo` in code.
- **Chord symbols:**

  | Symbol | Notes | Steps | Exact |
  |---|---|---|---|
  | Cg | C vE ^G | 0, 11, 22 | 1 : 2/φ : 4/φ² |
  | Cg7 | C vE ^G B | 0, 11, 22, 33 | 1 : 2/φ : 4/φ² : 8/φ³ |
  | Cs (silver) | C ^E♭ vG | 0, 10, 20 | |
  | CT13 (bronze) | C ^E vA | 0, 13, 26 | |

  Slash = bass note (vCg/G). Alterations: C(v3,^5).
- **Intervals:** in cents ("366.91 c") and ratios (3/2, φ). Chord shapes in sixth-steps above the root: (0, 11, 22).
- **Roman numerals:** I ii iii IV V vi vii°, with sixth-step marks (vIg = the golden triad a sixth-step below the tonic).

## 6. Accuracy rules (the most important section)

The author cares about precision above everything. A wrong number or a wrong historical claim is worse than an omission.

1. **Compute every number** you state, or copy it from the canonical sources: `docs/GOLDEN_MATH.md`, `docs/GOLDEN_THEORY.md`, `docs/GOLDEN_HARMONY.md`, `docs/GOLDEN_PROGRESSIONS.md`, and the scripts in `reference/golden/` (`explore.py`, `classify.py`, `dictionary.py`, `passing.py`). Run Python (`.venv/Scripts/python`) to check anything new. Keep the canonical rounding (two decimals in cents).
2. **Label the status of every claim:** *theorem* (proved, or checked exhaustively), *measurement* (depends on a model: roughness, entropy, timbre, register), or *conjecture or hypothesis* (the bliss idea, EEG links). Never present a hypothesis as fact.
3. **History:** state only well-established facts. Use "c." or a range when a date is uncertain. Never invent quotations, page numbers or citations. If unsure, say less.
4. **Known pitfalls, stated correctly:**
   - **Bach did not invent equal temperament.** Zhu Zaiyu (1584) and Simon Stevin (c. 1605) computed it, and Mersenne popularized it (1636). Bach's *Well-Tempered Clavier* (Book I 1722, Book II 1742) used a well temperament across all 24 keys.
   - **Parallel fourths and fifths are early medieval *organum* (9th–10th c.), not Gregorian chant**, which is monophonic.
   - **Golden-seventh beats:** a close-voiced Cg7 on harmonic tones beats at $f_0\varphi^{-6}\times(1, 2/\varphi, 4/\varphi^2)$, the golden *triad* in rhythm. It also beats at $2f_0\varphi^{-6}$, the golden seventh against the root's octave, because $8/\varphi^3 = 2 - 2\varphi^{-6}$. No beat occurs at the golden seventh's own ratio. At 110 Hz: 6.13, 7.58, 9.37 and 12.26 Hz.
   - **The golden seventh** 8/φ³ = 1100.73 c. 36-ET renders it as 33 sixth-steps = exactly the 12-ET major seventh; the exact value is 0.73 c sharper.
   - **The golden triad is not "the least stable chord":** with harmonic timbres it is rougher than major, minor and augmented but smoother than diminished, and its instability is concentrated in the golden fifth.
5. **Canonical values:**

   | Quantity | Value |
   |---|---|
   | φ | 1.6180339887 = 833.09 c |
   | golden third 2/φ | 366.91 c (11 steps) |
   | golden fifth 4/φ² | 733.82 c (22 steps) |
   | golden seventh 8/φ³ | 1100.73 c (33 steps) |
   | golden comma φ¹³/2⁹ | 30.17 c |
   | golden apotome φ³/4 | 99.27 c |
   | golden limma 2⁷/φ¹⁰ | 69.10 c |
   | Pythagorean comma | 23.46 c |
   | limma 256/243 | 90.22 c |
   | apotome 2187/2048 | 113.69 c |
   | 36-comma φ³⁶/2²⁵ | −8.75 c |

   - **Well-formed golden scale sizes:** 2, 3, 4, 7, 10, 13, 23, 36. For fifths: 2, 3, 5, 7, 12, 17, 29, 41, 53.
   - **Scales:**
     - golden7 = C C# vE vF ^G ^A♭ B;
     - golden13 = C C# D vE♭ vE vF vF# ^F# ^G ^A♭ ^A B♭ B;
     - silver13 = C C# D ^E♭ ^E ^F vF# ^F# vG vA♭ vA B♭ B.
   - **Thirds:** silver third exact = chain distance 14 = 336.74 c; bronze third exact = chain distance 11 (inverted) = 436.01 c ≈ 9/7 (435.08 c).
   - **Averaging:** Cg = (C + Cm + Caug)/3; Cs = (C + Cm + Cdim)/3.
   - **Theorems:**
     - 288 strict golden paths, 240 with tertian endpoints, 12 types;
     - never two golden chords in a row on a strict path;
     - partner bronze (168) or silver (72);
     - quality theorem;
     - System 2: 46 pairs with two golden chords, 181 with at least one.
   - **ℤ₃₆:**
     - units 1, 5, 7, 11, 13, 17, 19, 23, 25, 29, 31, 35;
     - M11 maps {0,1,2} to {0,11,22} (the sixth-step cluster to Cg); M13 maps it to bronze (0,13,26); in ℤ₁₂, M7 maps {0,1,2} to {0,2,7};
     - the golden chain (×25) is a 36-tone row;
     - subgroup orders of ℤ₃₆: 1, 2, 3, 4, 6, 9, 12, 18, 36.
6. **Anything new you derive:** verify it with code before writing it, and mention it in your final report.

## 7. Exemplar (the style to match)

```html
<section id="comma">
<h2>The Pythagorean comma</h2>
<div class="layer hear">
<p>Stack twelve perfect fifths and you nearly return to where you started, seven octaves up, but not quite. The
twelfth fifth overshoots by a sliver: about a quarter of a semitone. Listen to the two notes one after another,
then together, and you will hear them beat.</p>
<audio-ex src="comma" caption="C after twelve pure fifths, then C after seven octaves: a quarter-semitone apart; together they beat slowly."></audio-ex>
</div>
<div class="layer understand">
<p>A pure fifth multiplies frequency by 3/2. Twelve of them multiply it by $(3/2)^{12} \approx 129.75$, while seven
octaves multiply it by $2^7 = 128$. The ratio of the two, $531441/524288 \approx 1.01364$, is the
<b>Pythagorean comma</b>, 23.46 cents.</p>
<aside class="mirror">With the golden sixth φ instead of the fifth, thirteen steps nearly make nine octaves:
$\varphi^{13} \approx 521.0$ against $2^9 = 512$. The overshoot is the <b>golden comma</b>, 30.17 cents
(<a href="ch:ch23#golden-comma">Chapter 23</a>).</aside>
</div>
<div class="layer derive">
<p><b>Definition.</b> The Pythagorean comma is $\kappa = 3^{12}/2^{19}$. In cents,
$1200\log_2\kappa = 1200\,(12\log_2 3 - 19) \approx 23.46$.</p>
</div>
</section>
```

## 8. Your final report

Report:
- files written, with word counts and the number of audio examples and figures per chapter;
- every claim you computed or derived that is not in the canonical sources;
- anything you were unsure about and left out or hedged;
- any problems the checker reported that you could not fix.

## 9. Site rendering (added 2026-10-21)

- Math is rendered at build time by KaTeX (`cd tools/textbook && npm install` once). Any TeX that KaTeX
  cannot parse is reported by `--check` as `math error in ...`: fix it, do not ignore it. Write `&lt;` or `<`
  inside math as you like; HTML entities are unescaped before rendering. Do not put `$` in prose for money.
- Section numbers (e.g. "23.1") and chapter labels are added automatically from toc.yaml: do not number
  `<h2>` headings yourself. Use `<h3>` for subsections and `<h4>` for small run-in headings.
- Each part has its own color theme; Golden mirror, Math, History, Note and Try it boxes are styled
  automatically from the classes in §3. `<blockquote>` is styled for quoted passages.
- Planned: audio examples will become videos (letter names + staff notation with the sounding notes
  highlighted), generated by SongMap's own visual renderer once it lands. Keep writing `<audio-ex>`;
  the build will upgrade them, so the source of each example must stay a SongMap song where possible.
- Note names with ups and downs (`^G`, `vE`) belong in prose or `<code>`, not in `\text{}` inside math:
  KaTeX rejects a raw `^` there. In math write `{}^{\wedge}G` or keep the name outside the formula.
- The author's favourite figure is the `<pianoroll>`: use it wherever specific notes, chords, voicings,
  scales or short progressions are discussed. It is drawn compactly (one thin row per step, sounding rows
  labelled in bold), so several per section are fine. Keep each roll to the notes under discussion.
- Passing placeholders (`~`, `~g`, `~g7`) in voiced styles play the passing engine's own four lines
  (bass + three upper voices, low to high), not an independent re-voicing; chord names are unchanged.
- SongMap pitfall: a `notes:` string shorter than its section loops, and a trailing rest does not count
  toward its length. Make the section exactly as long as the material (or pad with a silent `c16@0`).
- Roughness tables for SongMap examples must state the voicing measured and whether unison doublings
  between parts are counted once.
