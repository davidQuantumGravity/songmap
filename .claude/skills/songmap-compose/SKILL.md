---
name: songmap-compose
description: Compose, score or revise music with the SongMap engine in this repo — write a .sm song map that sounds musical and alive (good chords, melodies, rhythms, instruments, dynamics, emotion) for a video or brief, place hits on exact frames, check it, render song.wav/stems/cues.json, read QA and revise. Use whenever asked to compose, score, rescore, arrange or edit a soundtrack or song here.
---

# Composing with SongMap

You write **musical decisions as text**, in a `.sm` song map. The engine does the synthesis, mixing and frame-accurate cue export. Never write DSP or edit engine code to change the music. If the engine can't do something, say so and pick the closest thing it can do.

Good scores come from **composing first and typing second**. Follow the method in §2, make it alive with the checklist in §3, and use the references for depth:

| Read | When |
|---|---|
| [reference/emotion.md](reference/emotion.md) | choosing key, harmony, rhythm and palette for a feeling; arcs for 1–3 minute videos |
| [reference/harmony.md](reference/harmony.md) | chords, progressions by mood, cadences, voicings (rel mode) |
| [reference/melody.md](reference/melody.md) | writing motifs and phrases, bar math, developing a theme, counter-melodies |
| [reference/rhythm.md](reference/rhythm.md) | grooves, swing, ghost notes, fills, builds, bass lines, arpeggios |
| [reference/instruments.md](reference/instruments.md) | what each instrument sounds like, how to shape it, arrangement and balance |
| [examples/](examples/) | three complete, rendered scores to imitate (§7) |
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
   - what the music must make the viewer *feel*, and how that feeling changes scene by scene (the arc);
   - one musical idea that carries the piece: "a curious piano question that becomes a confident answer", "a pulse that grows into a choir".
2. **Choose the frame.** Pick key and mode, tempo (120 BPM for 30 fps video unless there's a reason), palette (3–5 instruments, each with a job) and a progression per section from [emotion.md](reference/emotion.md) and [harmony.md](reference/harmony.md).
3. **Spot the picture** (§5). Turn scene starts into section boundaries, and must-land moments (reveals, counters landing, list items, cuts) into events or cues.
4. **Write the material.** One motif (1–2 bars) and its answer, a groove, a bass line and a voicing ([melody.md](reference/melody.md), [rhythm.md](reference/rhythm.md)). Count every bar.
5. **Arrange.** Decide who plays in each section. Start sparse, add a layer per scene, peak once, and subtract for caveats. Vary something every 4–8 bars. Contrast neighbouring sections.
6. **Express** with the checklist in §3: dynamics arcs, accents and ghosts, articulation, breathing.
7. **Check → render → read the numbers.**
   - Run `songmap check` until `ok:` with the exact frame count.
   - Render, then read `qa.json`: per-section `loudness` should trace your arc (caveats at least 4–6 dB below their neighbours, the peak loudest), and `stems` shows part balance (a featured melody should stand out).
   - Fix with `dyn=`, `mix <part> <dB>` and arrangement changes.
8. **Revise by line.** Map feedback in musical terms ("pad too bright in barrier", "bigger hit at 970 M") to a section-line edit, then check and render again.

## 3. Lifelike, not robotic: the checklist

The engine plays exactly what you write: no swing, no timing humanisation and no motif transforms yet (the performance layer arrives in P3). **All of the feel has to be in the text.** Before rendering, go through this list.

1. **Every section has a dynamic shape.** `dyn=p<mf`, `dyn=mf>p`, or `dyn=pp` for a caveat. Never minutes at one level. Velocity also changes timbre (pianos brighten, filters open), so dynamics are colour, not just volume.
2. **Velocity varies inside patterns.**
   - drums: `X x - o` and `vel: [...]` lists (strong on the beat, weaker off it), plus snare ghosts (`o`);
   - melodies: `=p … < … =f` hairpins, `^` on the peak note, `(ghost)` notes.
3. **Articulation.** `'` staccato for playful or tight, `_` tenuto and `~` slurs for singing lines. A bass slide (`5/4~ R`) humanises a groove.
4. **Phrases breathe.** Melodies end phrases on long notes or rests every 2–4 bars, written as question and answer. Leave space for other instruments and the voice-over.
5. **Something changes every 4–8 bars.** A new layer, a fill (multi-bar lanes or `bar -1:`), a register shift, a new voicing, the melody moving to another instrument, the harmonic rhythm doubling.
6. **Syncopation and anticipation.** Push a chord or bass note a 16th or a triplet early (`r/8t [3,7,9]`), and land the bass with the kick.
7. **Swing is written on the 12-step grid.** `x.xx.xx.xx.x` gives shuffled hats, and triplets in notes are `/8t`.
8. **Rich, moving harmony.** Use 7ths and 9ths and inversions in rel voicings (`[3,7,9]`, `[5-,R,3]`) instead of root-position triads everywhere. `pad:warm` and `pad:dark` are triads only.
9. **Separate registers.** Bass below C3, chords C3–C5, melody above them. Two parts in the same job and register blur.
10. **Contrast and arc.** Adjacent sections differ (texture, register, density, harmony). The peak comes once, late. A quiet section before the biggest one makes it land.
11. **Endings mean something.** Resolve (V–I, IV–I, Picardy) for closure, or hang on a sus chord on purpose.
12. **Silence and space are allowed.** `N.C.` chords, rests, a 2-beat `!stop:2b` before a hit, a solo instrument.

## 4. The `.sm` format

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
mix keys 0
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

- **Settings:** `like=<section>` (copies its parts and settings), `dyn=`, `chords="Am:2 G:2"`, `prog=<name>`, `key=`, `tempo=<bpm>`.
- **Events:** `!impact(size=s|m|l|xl)`, `!riser:2` (ends at its position), `!zaps(count=6)`, `!stop:2b`, `!drop:2(keep=[pad])`. Position them with `@+bar:beat` (from this section), `@bar` (absolute), `@f123` or `@cue:x`.
- **Loops, per-bar edits, repeats:** use definitions and `form:` ([cinematic_build.sm](examples/cinematic_build.sm), `docs/LANGUAGE.md`):
  - `for i in 1..3:`, `if i == last:`;
  - `every 4 bars: bass = eighths`, `bar -1: lead = none`;
  - `verse 8 x2`.

## 5. Time: frames, bars, positions

- **Frames per bar.** `fps × beats_per_bar × 60 / tempo`, which is 60 at 120 BPM, 4/4, 30 fps (a beat is 15 frames) and 80 at 90 BPM. The whole-frame tempos at 30 fps are 60, 72, 75, 90, 100, 120, 150 and 180. Bars count from **0**.
- **Length.** The song is all bars plus `tail` seconds. With `video=Comp:frames`, `check` compares the two: it warns when they differ by less than a bar and fails beyond. So the bars are `(frames − tail × fps) / frames_per_bar`; adjust `tail` (it may be fractional) or give the last section a fractional length.
- **Scene starts** round to bars. **Off-grid moments** get `cue name=f1145` and `!impact@cue:name`. Cues snap to the nearest 16th, with a warning if that moves one by more than a frame.
- **Positions:**

  | Position | Meaning |
  |---|---|
  | (none) | the start of this section |
  | `@+3:2` | 3 bars in, beat 2 (beats are 1-based) |
  | `@12:3` | absolute bar 12, beat 3 |
  | `@f735` | video frame 735 |
  | `@cue:x` | a named cue |
  | `@agents+8` | 8 bars into the section `agents` |

  A riser on a section with no `@` ends at that section's start, so it plays during the section before.

## 6. Gotchas

- **Bar sums.** Durations are sticky, and every bar must add up to the meter. Always write `|` bar lines; inline notes without them are not checked.
- **Motif cycling.** `motif` plus `role:m1,m2` cycles in blocks anchored at **bar 0 of the song**, so a section starting mid-cycle begins mid-motif. Prefer melodies as inline-note variables (`theme = {deg: "...", oct: 1}`), which start with their section.
- **Pad and slash chords.** `pad:warm` and `pad:dark` voice triads, so 7ths and 9ths need a rel voicing. Slash chords (`C/E`) still put the root in the bass.
- **Levels.** The default `lead` level is low: add `mix lead 6` for a featured melody. Parts named `keys`, `piano`, `epiano`, `organ`, `gtr` or `guitar` get calibrated levels; any other name needs an `inst` line and a `mix` level.
- **Section names.** Avoid style, motif and keyword names (`return`, `if`, `for`, …): a section is also a variable, and `pad:warm` would pick up a section called `warm`.
- **Not available yet:** tempo ramps (`rit`), motif transforms (`m1:aug`), humanised timing and swing (the `groove` line is stored for P3), and instruments outside the catalog (strings, brass, bells). Use what exists.

## 7. Examples (complete, checked and rendered)

- [examples/hopeful_explainer.sm](examples/hopeful_explainer.sm), D major, 1:15:
  - a piano question/answer theme;
  - guitar ripples, a pocket groove with ghosts and a bass that locks to the kick;
  - the synth lead takes the tune;
  - an 8 dB drop for a caveat, and a plagal ending.
- [examples/cinematic_build.sm](examples/cinematic_build.sm), E minor, 1:40, a form block:
  - three rising waves driven by a loop index (dynamics and euclid hats);
  - risers into drops, per-bar fills, the lead resting in the last bar;
  - a stop-time before a held caveat with a borrowed-chord turnaround, then a bigger finale.
- [examples/lofi_late_notes.sm](examples/lofi_late_notes.sm), D dorian, 90 BPM:
  - a 12-step shuffle, rootless 9th chords with an anticipation, a bass slide;
  - a piano melody with a grace note and breathing rests;
  - a drum-less bridge, and the melody lifted in the mix.

Section loudness measured from the renders:

| Example | Sections, in order (LUFS) |
|---|---|
| hopeful explainer | intro −21.7, verse −16.8, lift −12.6, **breath −20.8**, home −12.5, outro −17.5 |
| cinematic build | intro −27.3, waves −19.8 / −17.2 / −14.9, drop −13.3, **held −19.2**, finale −12.4, coda −21.5 |
