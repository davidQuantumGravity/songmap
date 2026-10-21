---
name: songmap-compose
description: Compose, score or revise music with the SongMap engine in this repo — write a .sm song map that sounds musical and alive (good chords, melodies, rhythms, instruments, dynamics, emotion) for a video or brief, place hits on exact frames, check it, render song.wav/stems/cues.json, read QA and revise. Use whenever asked to compose, score, rescore, arrange or edit a soundtrack or song here.
---

# Composing with SongMap

You write **musical decisions as text**, in a `.sm` song map. The engine does the synthesis, mixing and frame-accurate cue export. Never write DSP or edit engine code to change the music. If the engine can't do something, say so and pick the closest thing it can do.

Good scores come from **composing first and typing second**. Follow the method in §2, make it alive with §3, balance it with §4, and use the references for depth:

| Read | When |
|---|---|
| [reference/emotion.md](reference/emotion.md) | choosing key, harmony, rhythm and palette for a feeling; arcs for 1–3 minute videos |
| [reference/harmony.md](reference/harmony.md) | chords, progressions by mood, cadences, voicings (rel mode) |
| [reference/melody.md](reference/melody.md) | writing motifs and phrases, bar math, scale degrees in major and minor, developing a theme |
| [reference/rhythm.md](reference/rhythm.md) | grooves, swing, ghost notes, fills, builds, bass lines, arpeggios |
| [reference/instruments.md](reference/instruments.md) | each instrument's sound and settings, ambience and sound-design moves, arrangement |
| [reference/golden.md](reference/golden.md) | golden harmony in 36-ET inside a Western song: spelling, five techniques, rules that keep it tasteful, the rub check |
| [examples/](examples/) | three complete, rendered and balanced scores to imitate (§8) |
| [catalog.txt](catalog.txt) | every style, mod, instrument and event name (`songmap describe --compact`) |

## 1. Commands

From the repo root, activate `.venv` (`.venv/Scripts/activate` on Windows, `source .venv/bin/activate` elsewhere), or call `.venv/Scripts/python -m songmap.cli`.

| Command | What it does |
|---|---|
| `songmap check song.sm` | parse, validate, expand. Milliseconds. Prints bars, length and frames, or one error per line with a fix |
| `songmap render song.sm -o build/x` | `song.wav`, `stems/`, `cues.json`, `qa.json` (about 5–30 s) |
| `songmap describe --compact` | the catalog (what [catalog.txt](catalog.txt) holds) |
| `songmap fmt x.yaml --to sm` | convert YAML ↔ `.sm` losslessly |

## 2. The method

1. **Brief → concept.** In one sentence each, write:
   - what the viewer should *feel*, and how that changes scene by scene (the arc);
   - one musical idea that carries the piece: "a curious piano question that becomes a confident answer", "the bird's call as the motif".
2. **Choose the frame.** Pick key and mode, tempo (120 BPM for 30 fps video unless there's a reason), palette (3–5 instruments, each with a job) and a progression per section, using [emotion.md](reference/emotion.md) and [harmony.md](reference/harmony.md).
3. **Spot the picture** (§6). Turn scene starts into section boundaries, and must-land moments (reveals, counters landing, list items) into events or cues. **Budget the hits:** one big impact per 15–20 s at most, and vary the device (a new layer entering, a fill, a stop-time, a harmonic arrival).
4. **Write the material.** One motif (1–2 bars) and its answer, a groove, a bass line and a voicing ([melody.md](reference/melody.md), [rhythm.md](reference/rhythm.md)).
   - **Count every bar.**
   - **Check every held melody note against the chord under it:** a half step above or below a chord tone, on a strong beat, clashes.
5. **Arrange.** Decide who plays in each section.
   - Start sparse and add a layer per scene.
   - Keep at most 5–6 parts sounding at once (a doubling counts as one).
   - Peak once, late. Subtract for caveats.
   - Vary something every 4–8 bars, and make neighbouring sections contrast.
6. **Express** with the checklist in §3.
7. **Check → render → read the numbers** (§4). Run `check` until `ok:` with the exact frame count. Render, then compare `qa.json` with the targets in §4 and fix with `dyn=`, `mix` and arrangement.
8. **Revise by line.** Map feedback in musical terms ("pad too bright in barrier", "bigger hit at 970 M") to a section-line edit, then check and render again.

## 3. Lifelike, not robotic: the checklist

The engine plays exactly what you write: no swing, no timing humanisation and no motif transforms yet (the performance layer arrives in P3). **All of the feel has to be in the text.**

1. **Dynamic shape.** Give most sections an arc (`dyn=p<mf`, `dyn=mf>p`). A flat `dyn=mp` is fine when the sections around it move. Velocity also changes timbre (pianos brighten, filters open), so dynamics are colour, not just volume.
2. **Velocity varies inside patterns.**
   - drums: `X x - o` and `vel: [...]` lists (strong on the beat, weaker off it), plus snare ghosts (`o`);
   - melodies: `=p … < … =f` hairpins, `^` on the peak note, `(ghost)` notes.
3. **Articulation.** `'` staccato for playful or tight, `_` tenuto and `~` slurs for singing lines, a bass slide (`5/4~ R`). Marks work in deg, letter and rel notes.
4. **Phrases breathe.** End phrases on long notes or rests every 2–4 bars, written as question and answer. Leave room for other instruments and the voice-over.
5. **Something changes every 4–8 bars.** A new layer, a fill (a multi-bar lane or `bar -1:`), a register shift, a new voicing, the melody moving to another instrument, the harmonic rhythm doubling.
6. **Syncopation and anticipation.** Push a chord or bass note a 16th or a triplet early (`r/8t [3,7,9]`), and land the bass with the kick.
7. **Swing is written on the 12-step grid.** `x.xx.xx.xx.x` gives shuffled hats, and each lane has its own grid, so a swung hat can sit over a straight kick. Triplets in notes are `/8t`.
8. **Rich, moving harmony.** Use 7ths and 9ths and inversions in rel voicings (`[3,7,9]`, `[5-,R,3]`). `pad:warm` and `pad:dark` are triads only.
9. **Separate registers.** Bass below C3, chords C3–C5, melody above them.
10. **Contrast and arc.** Adjacent sections differ (texture, register, density, harmony). The peak comes once; a quiet section before it makes it land.
11. **Endings mean something.** Resolve (V–I, IV–I, Picardy) or hang on a sus chord on purpose.
12. **Silence and space.** `N.C.` chords, rests, a 2-beat `!stop:2b` before a hit, a solo instrument.

## 4. Loudness, contrast and balance

- **Start every new song with a balanced mix line**, then adjust from the stems:

  ```
  mix drums -6 | fx -6 | lead 6
  ```

  The default levels match the original Oct-13 tracks, where the drums sit about 10 dB above the melody and the lead is quiet. For a piano melody, add `| keys 0` to `2`.
- **`dyn` levels relative to `mf`**, before mastering:

  | Level | pp | p | mp | mf | f | ff |
  |---|---|---|---|---|---|---|
  | Gain | −11 dB | −6 dB | −2.6 dB | 0 | +2.3 dB | +3 to +4 dB |

  **`ff` saturates:** velocities cap at 1.0, and accented hits are already there. In a real mix a section's measured loudness moves only about **1–3 dB per `dyn` step**, because sustained notes, reverb tails and the master blunt it. For a big difference, **change the arrangement**: add parts, an octave doubling, open or 16th hats or a higher register for the peak, and **remove parts** before it. `dyn` alone won't do it.
- **The pre-peak dip** works even for short builds. On the peak's line, `!drop:1@-1(keep=[pad, keys])` silences everything but the pad and keys for the bar before it, while the riser keeps rising:

  ```
  build 2 | drums:full bass:eighths pad:warm arp:up dyn=mp<f
  peak  2 | like=build lead:theme dyn=f | !drop:1@-1(keep=[pad, arp]) !riser:1 !impact
  ```
- **The master normalises the whole song** to −14 LUFS, so only the differences between sections count.
- **`qa.json`, what to read:**

  | Field | Meaning | Target |
  |---|---|---|
  | `sections[].loudness` | LUFS per section | **peak at least 2–3 dB above every other section; a caveat or breakdown 4–6 dB or more below its neighbours; a quiet bar before the peak 6 dB or more below it** |
  | `sections[].low / mid / high` | share of energy below 250 Hz, 250 Hz–4 kHz, above 4 kHz | low above 0.85 means bass- or kick-heavy (dark, muddy); bright sections show more high |
  | `stems` | LUFS per part over the whole song (parts that play less read lower) | a featured melody within a few dB of the loudest accompaniment |
  | `return_hall` | the reverb return | — |
  | `true_peak_db`, `clipped_samples` | the master's output | −1.0 and 0 |

## 5. The `.sm` format

```
song "Title" 120 4/4 Em fps=30 seed=7 tail=3 video=Comp:3690       # tail is in seconds
inst keys(hardness=.35) gtr=string_pluck(brightness=.6)          # shape instruments
chords Em C G D /2                                               # bars per chord; loops from bar 0
theme = {deg: "=mp 0/8 2 4/4 2/2 | 4/4. 2/8 0/2", oct: 1}        # a melody kept in a variable
pocket = {kick: "X.....x...x.....", snare: "....X..o....X.o.", hat: "x-x-x-x-x-x-x-x-"}
lift = !impact !riser:2                                          # a named event list
# name   bars | parts and settings                               | events
intro      4 | keys:{rel: "[R,3,5]/2 [3,5,R+]"} dyn=pp<p
verse      8 | like=intro keys:theme bass:{rel: "R/4. R/8 r/8 5/8 R+/4", oct: -2} drums:pocket dyn=p<mf | !lift
mix drums -6 | fx -6 | keys 0 | lead 6
```

- **Parts:**

  | Form | Example |
  |---|---|
  | a style, with mods or options | `role:style+mod`, `role:style(k=v)` |
  | a variable | `role:var` |
  | a map | `role:{deg: "...", oct: 1}` |
  | chord-relative notes | `role:{rel: "...", oct: -2}` |
  | inline letter notes | `role="=p a4 c+ e+"` |
  | a drum lane | `kick="X..."` |
  | an expression | `role:pocket+{ohat: "..x."}` |
  | remove an inherited part | `-role` |

- **Settings:** `like=<section>` copies its parts and settings, including `chords`. Anything written after it on the line replaces what was inherited: a `role:` replaces that part, and `chords=` replaces the chords. Others: `dyn=`, `chords="Am:2 G:2"`, `prog=<name>`, `key=`, `tempo=<bpm>`.
- **Key.** `key=` is a section setting only (it can't go inside a part's `{...}` map). It re-keys the section's deg notes; chord names stay absolute.
- **Multi-bar patterns.** Notes in every mode (deg, letter, rel) may span several bars with `|`, and they loop to fill the section. Example: a bass that rests to re-enter after a stop, `{rel: "R/1 | r/2 R/2", oct: -2}`.
- **Events** are written **`!type[:length][@position][(options)]`**, in that order: `!zaps@+2:3(count=3)`, `!impact@cue:bird(size=xl)`.
  - Lengths are in bars (`:2`) or beats (`:2b`).
  - Positions are `@+bar:beat` (from this section, so `@-1:3` is beat 3 of the bar before), `@bar` (absolute), `@f123` or `@cue:x`.

  | Event | What it does |
  |---|---|
  | `!impact(size=s\|m\|l\|xl)` | a boom and crash starting at the position. `l` is the default; `xl` is longer and bigger |
  | `!riser:2` | a 2-bar sweep that **ends** at the position, leading into it |
  | `!zaps(count=6, every=8)` | a run of rising chirps, one per 8th note: lists, data |
  | `!stop:2b` | stop-time: every section part goes silent for 2 beats (notes starting in the span are removed); the fx keep sounding |
  | `!drop:2(keep=[pad, bass])` | every part not kept goes silent for 2 bars: breakdowns |
  | `hit crash swell fill downlifter cloud ...` | **silent for now:** written to `cues.json` only; they render from later phases |

  - **Lengths.** An impact rings about 3 s (`xl` about 4.5 s). A riser lasts exactly its bars (`:1` is 2 s at 120 BPM).
  - **Hits for list items** (n items appearing): use a small impact or a `!zaps` per item, or better, a new layer or melody note per item, and keep the big impact for the last one.

- **Loops, per-bar edits, repeats:** use definitions and `form:` ([cinematic_build.sm](examples/cinematic_build.sm), `docs/LANGUAGE.md`):
  - `for i in 1..3:`, `if i == last:`;
  - `every 4 bars: bass = eighths`, `bar -1: lead = none`;
  - `verse 8 x2`.

## 6. Time: frames, bars, positions

- **Frames per bar.** `fps × beats_per_bar × 60 / tempo`, which is 60 at 120 BPM, 4/4, 30 fps (a beat is 15 frames) and 80 at 90 BPM. The whole-frame tempos at 30 fps are 60, 72, 75, 90, 100, 120, 150 and 180. Bars count from **0**.
- **Length.** The song is all bars plus `tail` seconds. With `video=Comp:frames`, `check` compares the two: it warns when they differ by less than a bar and fails beyond. So the bars are `(frames − tail × fps) / frames_per_bar`.
  - When that isn't whole, use a fractional tail (`tail=2.5`) or a fractional last section (`end 2.5`). For example, 1,500 frames at 120 BPM with `tail=3` leaves 1,410 frames, which is 23.5 bars.
  - At 30 fps and 120 BPM:

    | tail | 1 | 2 | 3 | 4 |
    |---|---|---|---|---|
    | frames | 30 (half a bar) | 60 (1 bar) | 90 (1.5 bars) | 120 (2 bars) |

    So 2,100 frames with `tail=4` is (2100 − 120) / 60 = 33 bars.
- **Frame → position.** Divide by frames per bar, then turn the fraction into a beat: f1230 / 60 = 20.5 = bar 20, beat 3, which is `@20:3`. Use a `cue` when it isn't a whole beat (or 16th).
- **Scene starts** round to bars. **Off-grid moments** get `cue name=f1145` and `!impact@cue:name`. Cues snap to the nearest 16th, with a warning if that moves one by more than a frame.
- **Positions:**

  | Position | Meaning |
  |---|---|
  | (none) | this section's start |
  | `@+3:2` | 3 bars in, beat 2 (beats are 1-based) |
  | `@12:3` | absolute bar 12, beat 3 |
  | `@f735` | video frame 735 |
  | `@cue:x` | a named cue |
  | `@agents+8` | 8 bars into the section `agents` |

## 7. Gotchas

- **Bar sums.** Durations are sticky, and every bar must add up to the meter. Always write `|` bar lines; inline notes without them are not checked.
- **Scale degrees.**
  - Degrees run past the octave: 7 is the tonic an octave up, and −1 is the 7th below.
  - In a minor key they are natural minor (in D minor, 5 = B♭ and 6 = C). When the chord is the major V (A in D minor), the melody needs the raised 7th: `#6` (C♯).
  - Accidentals go before the degree: `#4`, `b7`.
- **Motif cycling.** `motif` plus `role:m1,m2` cycles in blocks anchored at **bar 0 of the song**, so a section starting mid-cycle begins mid-motif. Prefer melodies as inline-note variables (`theme = {deg: "...", oct: 1}`), which start with their section.
- **Pad and slash chords.** `pad:warm` and `pad:dark` voice triads, so 7ths and 9ths need a rel voicing. Slash chords (`C/E`) still put the root in the bass.
- **Part names and levels.** Parts named `keys`, `piano`, `epiano`, `organ`, `gtr` or `guitar` get their instrument and a calibrated level; any other name needs an `inst` line and a `mix` level.
- **Section names.** Avoid style, motif and keyword names (`return`, `if`, `for`, …): a section is also a variable.
- **Not available yet:** tempo ramps (`rit`), motif transforms (`m1:aug`), humanised timing and swing (the `groove` line is stored for P3), and instruments outside the catalog (strings, brass, bells, real field recordings). For ambience and nature sounds, see [instruments.md](reference/instruments.md).

## 8. Examples (complete, checked, rendered and balanced)

- [examples/hopeful_explainer.sm](examples/hopeful_explainer.sm), D major, 1:15:
  - a piano question/answer theme;
  - guitar ripples, a pocket groove with ghosts and a bass that locks to the kick;
  - the synth lead takes the tune;
  - a caveat 11 dB under its neighbours, and a plagal ending.
- [examples/cinematic_build.sm](examples/cinematic_build.sm), E minor, 1:40, a form block:
  - three rising waves driven by a loop index (dynamics and euclid hats);
  - risers into drops, per-bar fills, the lead resting in the last bar;
  - a stop-time before a held caveat with a borrowed-chord turnaround, then a bigger finale.
- [examples/lofi_late_notes.sm](examples/lofi_late_notes.sm), D dorian, 90 BPM:
  - a 12-step shuffle, rootless 9th chords with an anticipation, a bass slide;
  - a piano melody with a grace note and breathing rests;
  - a drum-less bridge.

Section loudness measured from the renders:

| Example | Sections, in order (LUFS) |
|---|---|
| hopeful explainer | intro −21.2, verse −16.5, lift −12.6, **breath −23.3**, home −12.3, outro −17.5 |
| cinematic build | intro −26.5, waves −20.5 / −18.0 / −15.6, drop −13.1, **held −22.5**, finale −11.8, coda −22.7 |
