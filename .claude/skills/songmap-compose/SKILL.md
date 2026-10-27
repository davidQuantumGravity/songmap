---
name: songmap-compose
description: Compose, score or revise music with the SongMap engine in this repo — write a .sm song map that sounds musical and alive (good chords, melodies, rhythms, instruments, dynamics, emotion) for a video or brief, place hits on exact frames, check it, render song.wav/stems/cues.json, read QA and revise. Use whenever asked to compose, score, rescore, arrange or edit a soundtrack or song here.
---

# Composing with SongMap

You write **musical decisions as text**, in a `.sm` song map. The engine does the synthesis, mixing and frame-accurate cue export. Never write DSP or edit engine code to change the music. If the engine can't do something, say so and pick the closest thing it can do.

Good scores come from **composing first and typing second**. Every composition or musical revision requires deliberate musical decisions, **one instrument at a time: notes first, expression second, then review in the ensemble** (§2.1). Follow the method in §2, make it alive with §3, balance it with §4, and use the references for depth:

For this user's melody revisions, golden compositions, motif auditions and listening presentations, read [listening-feedback.md](reference/listening-feedback.md). Preserve praised bass/harmony/comping, write a memorable line with breathing space, and keep unfamiliar pitches supported by calmer timbres and measured lead levels. Scale membership and technical QA do not establish that a melody sounds good. A/B auditioning is useful when it resolves a real melodic choice, not a required gate for every task.

| Read | When |
|---|---|
| [reference/emotion.md](reference/emotion.md) | choosing key, harmony, rhythm and palette for a feeling; arcs for 1–3 minute videos |
| [reference/harmony.md](reference/harmony.md) | chords, progressions by mood, cadences, voicings (rel mode) |
| [reference/melody.md](reference/melody.md) | writing motifs and phrases, bar math, scale degrees in major and minor, developing a theme |
| [reference/rhythm.md](reference/rhythm.md) | grooves, swing, ghost notes, fills, builds, bass lines, arpeggios |
| [reference/instruments.md](reference/instruments.md) | each instrument's sound and settings, ambience and sound-design moves, arrangement |
| [reference/golden.md](reference/golden.md) | golden harmony in 36-ET inside a Western song: spelling, five techniques, rules that keep it tasteful, the rub check |
| [reference/listening-feedback.md](reference/listening-feedback.md) | feedback-driven melody and balance, golden suspensions/ninths, motif A/B tests, chord-following binaural layers and compact synchronized presentation |
| [composition contexts](../../../docs/composition/README.md) | recurring units, through-composed passages, mixed layers, transitions and concise node briefs; use current `.sm` grammar, with future editor behavior clearly marked in the linked design |
| [examples/](examples/) | three complete, rendered and balanced scores to imitate (§8) |
| [catalog.txt](catalog.txt) | every style, mod, instrument and event name (`songmap describe --compact`) |

## 1. Commands

From the repo root, activate `.venv` (`.venv/Scripts/activate` on Windows, `source .venv/bin/activate` elsewhere), or call `.venv/Scripts/python -m songmap.cli`.

| Command | What it does |
|---|---|
| `songmap check song.sm` | parse, validate, expand. Milliseconds. Prints bars, length and frames, or one error per line with a fix |
| `songmap listen song.sm [--render DIR]` | **the automated ear**: melody-against-chord clashes, crowded registers, mechanical repetition, flat dynamics, too many hits, the ending. `--render DIR` also judges loudness and balance from that **existing** render's `qa.json`; it doesn't render. Every `songmap render` writes the full report to `review.json` |
| `songmap render song.sm -o DIR` | `song.wav`, `stems/`, `cues.json`, `qa.json`, `review.json` (the ear's report) and `qa.png` (spectrogram and loudness), in about 5–30 s |
| `songmap describe --compact` | the catalog (what [catalog.txt](catalog.txt) holds) |
| `songmap fmt x.yaml --to sm` | convert YAML ↔ `.sm` losslessly |

**Where songs go.** Every song lives in the repo, never in a temp folder: `songs/<collection>/<name>.sm`. Use an existing collection or make a new folder with a one-line `README.md`. Render into `songs/<collection>/renders/<name>/`, which is gitignored. Every song in `songs/` appears automatically in the textbook's **Songbook** (appendix H, built by `tools/textbook/build.py`) for the user to review, with its player, spectrogram, loudness and the ear's report.
- **Intent.** Start each file with comment lines saying what the music is for and what to listen for; the Songbook shows them.
- **Verdicts.** The user's verdict goes on a line `# review: approved — …` or `# review: rework — …`. When they give feedback in words, add or update that line.

## 2. The method

**Recorded instruments:** run `songmap samples list` before choosing `sampler/<voice>`. The curated piano, harp,
mallets, strings, winds and percussion appear in `songmap describe`; `songmap samples install` installs the free pack.
Use installed voices within their published ranges and rebalance from their rendered stems. Recordings retain natural
tuning and vibrato; keep `clean/golden_pad` and `clean/glass` when their engineered spectra are the point of a passage.
See `docs/SFZ_LIBRARY.md` and the audition/comparison page `songs/sfz_revisited/index.html`.
For bass and drums, use `docs/BASS_DRUM_PALETTE.md` and `songs/rhythm_palette/`: recorded bass techniques,
complete kit lines, individual snares/toms/cymbals, electronic presets and eight editable groove templates.
For piano, electric keys, organs and guitars, use `docs/KEYS_GUITAR_PALETTE.md` and `songs/keys_guitars/`:
recorded pianos, fixed guitar techniques and pickup channels, twelve native keyboard recipes, controlled
timbre auditions and eight authored starters. Pedals and keyswitches are fixed in these prepared programs;
do not claim connected guitar legato, slides or sampled palm mutes. Check the selected voice's actual range.
For classical and jazz ensembles, use `docs/ENSEMBLE_PALETTE.md` and `songs/ensemble_palette/`:
recorded bowing styles, woodwinds, actual brass mutes, soprano/alto/tenor/baritone saxophones,
orchestral percussion, fourteen continuous sound palettes and six authored ensemble starters.
Choose actual articulations and write breaths/bows separately for each part. Hybrid fades do
not create sampled connected legato, missing auxiliary instruments or independently recorded
players. Use sounding pitch and overlapping source ranges. For deliberate held-note phrasing,
use `expression` curves (volume, brightness/body, added pitch/vibrato, width and sound morphs).
Use `family/<instrument>` and named `technique` options or beat schedules for real recorded
articulations. Read [the feature guide](../../../docs/EXPRESSION_ARTICULATION_RESPONSE.md)
and `songs/expression_lab/` before using them. Curves use quarter-note beats, follow tempo
ramps and hold their final value; technique changes affect new notes only. Write these
during each instrument's expression pass, in ensemble context; a generic swell on every
part is not a completed expression pass. Calibration is enabled on new families and can
be adjusted with `calibration=0..1`; preserve intentional old mix levels when revising.

1. **Brief → concept.** In one sentence each, write:
   - what the viewer should *feel*, and how that changes scene by scene (the arc);
   - one musical idea that carries the piece: "a curious piano question that becomes a confident answer", "the bird's call as the motif".
2. **Choose the frame.** Pick key and mode, tempo (120 BPM for 30 fps video unless there's a reason), palette (3–5 instruments, each with a job) and a progression per section, using [emotion.md](reference/emotion.md) and [harmony.md](reference/harmony.md).
3. **Spot the picture** (§6). Turn scene starts into section boundaries, and must-land moments (reveals, counters landing, list items) into events or cues. **Budget the hits:** one big impact per 15–20 s at most, and vary the device (a new layer entering, a fill, a stop-time, a harmonic arrival).
4. **Plan the arrangement.** Decide who plays in each section and how the parts relate.
   - Start sparse and add a layer per scene.
   - Keep at most 5–6 parts sounding at once (a doubling counts as one).
   - Peak once, late. Subtract for caveats.
   - Vary something every 4–8 bars, and make neighbouring sections contrast.
5. **Compose and express each instrument in turn** (§2.1). Write its complete musical part through the song, then shape its performance before moving to the next instrument. Use [melody.md](reference/melody.md), [rhythm.md](reference/rhythm.md), and the checklist in §3.
   - **Count every bar.**
   - **Check every held melody note against the chord under it:** a half step above or below a chord tone, on a strong beat, clashes unless deliberately prepared and resolved.
6. **Review the ensemble.** Revisit earlier parts as later ones enter. Adjust notes, rests, voicings, articulation and dynamics to preserve the intended foreground, pocket, replies and section arc.
7. **Check → listen → render → read the numbers** (§4).
   - Run `check` until `ok:` with the exact frame count.
   - Run `songmap listen` and fix its problems and warnings (or decide they're intended).
   - Render, then read `review.json` (the ear with loudness) and `qa.json`, and look at `qa.png`.
   - Fix with arrangement, `dyn=` and `mix`.
8. **Revise by line.** Map feedback in musical terms ("pad too bright in barrier", "bigger hit at 970 M") to a section-line edit, then check and render again.

### 2.1 Required instrument-by-instrument writing process

For every composition or musical revision, the agent must make deliberate musical decisions as an LLM for each instrument. Choose an order appropriate to the piece; finish one instrument's note and expression passes through all its sections before starting the next, then revisit earlier parts as the ensemble develops. Proceed autonomously between instruments.

1. Establish the part's job, register, technique, entrances and silences, and its relationships to the planned and written parts.
2. Compose its pitches, voicings, rhythm, durations and rests phrase by phrase across the complete form. Work through answers, transitions, returns and ending; check harmony, voice leading, range and playability.
3. Make a separate expression pass: choose fitting note-level dynamics, phrase arcs, accents, ghosts, gates, articulations, breathing space and groove placement. Match these to the rest of the song and the chosen instrument's actual capabilities. Global dynamics and automatic humanization do not complete this pass. Use detail where it serves the phrase; a held note, a rest or an unaccented attack can be the expressive choice.
4. Review the part in the ensemble: kick/bass arrivals, foreground/accompaniment balance, replies, competing rhythms and release tails. Revisit its notes and expression when another part changes their context. Fix musical problems in the score before relying on mix changes.
5. Keep concise score comments or composing notes recording the musical decisions for that instrument. At render checkpoints, inspect its stem and the full mix; retain the distinction between technical checks and actual listening.

For drums, give each lane its own decisions and review the complete kit as one playable drummer. Leave hands free for fills and choose hat openings, pedal closures and cymbal accents intentionally. For sampled bass, respect the recorded attack technique and available articulations; slur notation alone cannot supply a missing recorded slide or hammer-on.

Templates and scripts may transcribe, expand, check and render the agent's authored decisions. A bulk loop that assigns generic patterns across instruments or changes patches over the same phrase is not a completed composition. Intentional ostinatos, sparse parts and controlled repetitions are valid; make their role and development explicit and preserve material fixed by the user's brief. Score compactness must not limit musical detail: expand phrases and section-specific writing as needed. Complete both passes for every active instrument before declaring the score finished. Automated QA does not replace this musical review.

## 3. Lifelike, not robotic: the checklist

**The performance layer plays your notes like players would.** The song's mood (§4) sets:
- timing drift (the kick stays tight, pads and keys breathe);
- velocity variation;
- rolled chords on keys and guitar;
- a phrase arch and metric accents;
- swing.

These controls provide baseline variation. They cannot supply the instrument-specific decisions in §2.1: **accents, phrasing, variation and contrast still have to be written.**

1. **Dynamic shape.** Give most sections an arc (`dyn=p<mf`, `dyn=mf>p`). A flat `dyn=mp` is fine when the sections around it move. Velocity also changes timbre (pianos brighten, filters open), so dynamics are colour, not just volume.
2. **Velocity varies inside patterns.**
   - drums: `X x - o` and `vel: [...]` lists (strong on the beat, weaker off it), plus snare ghosts (`o`);
   - melodies: `=p … < … =f` hairpins, `^` on the peak note, `(ghost)` notes.
3. **Articulation.** `'` staccato for playful or tight, `_` tenuto and `~` slurs for singing lines, a bass slide (`5/4~ R`). Marks work in deg, letter and rel notes.
4. **Phrases breathe.** End phrases on long notes or rests every 2–4 bars, written as question and answer. Leave room for other instruments and the voice-over.
5. **Something changes every 4–8 bars.** A new layer, a fill (a multi-bar lane or `bar -1:`), a register shift, a new voicing, the melody moving to another instrument, the harmonic rhythm doubling.
6. **Syncopation and anticipation.** Push a chord or bass note a 16th or a triplet early (`r/8t [3,7,9]`), and land the bass with the kick.
7. **Swing and groove.**
   - `groove swing=.56/16 tpl=laid_back` swings and pushes or lays back the whole song.
   - `feel snare offset=6` makes one player lay back; section feel (`swing=.6`) and the mood set defaults.
   - For a hard triplet shuffle, write it on the 12-step grid (`x.xx.xx.xx.x`). Each lane has its own grid, so a swung hat can sit over a straight kick. Triplets in notes are `/8t`.
8. **Rich, moving harmony.** Use 7ths and 9ths and inversions in rel voicings (`[3,7,9]`, `[5-,R,3]`). `pad:warm` and `pad:dark` are triads only.
9. **Separate registers.** Bass below C3, chords C3–C5, melody above them.
10. **Contrast and arc.** Adjacent sections differ (texture, register, density, harmony). The peak comes once; a quiet section before it makes it land.
11. **Endings mean something.** Resolve (V–I, IV–I, Picardy) or hang on a sus chord on purpose.
12. **Silence and space.** `N.C.` chords, rests, a 2-beat `!stop:2b` before a hit, a solo instrument.

## 4. Loudness, contrast and balance

- **Pick a mood** on the `song` line (`mood=cinematic`). It sets the mix, the reverb and the feel; `balanced` is the default.

  | Mood | Sound |
  |---|---|
  | `balanced` | even mix (drums under the music, the lead audible), light human feel |
  | `cinematic` | wider reverb, phrases that swell, impacts forward |
  | `documentary` | soft drums, intimate, room for a voice-over |
  | `ambient` | long reverb, pads forward, drums distant |
  | `techno` | tight and straight, drums forward |
  | `lofi` | swung 8ths laid back, soft drums, warm keys |
  | `v0` | the original Oct-13 synth sound, unperformed (the faithful ports) |

  Adjust from the stems with `mix <part> <dB>`. **`mix` sets the part's fader level; it replaces the mood's value instead of adding to it.** In `balanced` the lead's fader is +7, so `mix lead 3` makes it *quieter*. The moods' levels:

  | Part | balanced | cinematic | documentary | ambient | techno | lofi |
  |---|---|---|---|---|---|---|
  | drums | −6 | −5 | −9 | −12 | −3 | −6 |
  | lead | 7 | 6 | 5 | 4 | 6 | 5 |
  | fx | −6 | −3 | −8 | −8 | −6 | −8 |

  The other parts sit at their defaults: keys and piano −4, epiano −11, organ −19, gtr −2.5, pad 1.4, arp 2.5, bass −1.7. Moves happen from there; a piano melody usually wants `mix keys 0` to `2`.
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
- **Master mode matters.** `master standard` targets its configured loudness (usually −14 LUFS); `master clean` normalizes sample peak only, without loudness normalization or limiting. Inspect LUFS and true peak in the delivered render. Keep intentional dynamics, check that the quiet opening is usable, and preserve a common master gain across comparison tracks.
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
song "Title" 120 4/4 Em fps=30 seed=7 tail=3 mood=cinematic video=Comp:3690   # tail in seconds
inst keys(hardness=.35) gtr=string_pluck(brightness=.6)          # shape instruments
chords Em C G D /2                                               # bars per chord; loops from bar 0
theme = {deg: "=mp 0/8 2 4/4 2/2 | 4/4. 2/8 0/2", oct: 1}        # a melody kept in a variable
pocket = {kick: "X.....x...x.....", snare: "....X..o....X.o.", hat: "x-x-x-x-x-x-x-x-"}
lift = !impact !riser:2                                          # a named event list
# name   bars | parts and settings                               | events
intro      4 | keys:{rel: "[R,3,5]/2 [3,5,R+]"} dyn=pp<p
verse      8 | like=intro keys:theme bass:{rel: "R/4. R/8 r/8 5/8 R+/4", oct: -2} drums:pocket dyn=p<mf | !lift
again      8 | like=verse keys:theme:t+2 lead:theme:aug tempo="rit 120>100"     # the theme developed, slowing
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
  | a developed theme | `role:theme:aug`, `role:m1:t+2:inv`: transforms `t±n` (scale steps), `oct±n`, `inv`, `rev`, `aug`, `dim`, `frag=n`, `xN`, `thin=.5`, `canon=3@8`, chained left to right |

- **Meter.** `meter=7/8` (or `meter="7/8 2+2+3"`, `meter="13/16 3+3+3+2+2"` with accent groups) gives one section its own bars: drum lanes take that many steps per bar (14 for 16ths in 7/8), notes are checked against it, `chords="C:1"` lasts one of its bars. Swing pairs count from beat 0, so keep odd meters straight.
- **Settings:** `like=<section>` copies its parts and settings, including `chords`. Anything written after it on the line replaces what was inherited: a `role:` replaces that part, and `chords=` replaces the chords. Others: `dyn=`, `chords="Am:2 G:2"`, `prog=<name>`, `key=`, `tempo=<bpm>`, a ramp across the section `tempo="rit 120>96"` / `"accel 90>120"`, and section feel `swing=.6`.
- **Key.** `key=` is a section setting only (it can't go inside a part's `{...}` map).
  - It re-keys the section's deg notes: `key=D` is D major, `key=Dm` is D minor, and `key="D dorian"` names a mode (also lydian, mixolydian, phrygian, harmonic_minor, melodic_minor, phrygian_dominant; golden scales and modes in [golden.md](reference/golden.md)).
  - Chord names stay absolute, so write the section's `chords=` to match.
  - `pad:` styles, `arp:` and rel parts follow `chords=`.
- **Multi-bar patterns.** Notes in every mode (deg, letter, rel) may span several bars with `|`, and they loop to fill the section. Example: a bass that rests to re-enter after a stop, `{rel: "R/1 | r/2 R/2", oct: -2}`.
- **Events** are written **`!type[:length][@position][(options)]`**, in that order: `!zaps@+2:3(count=3)`, `!impact@cue:bird(size=xl)`.
  - Lengths are in bars (`:2`) or beats (`:2b`).
  - Positions are `@+bar:beat` (from this section, so `@-1:3` is beat 3 of the bar before), `@bar` (absolute), `@f123` or `@cue:x`.

  | Event | What it does |
  |---|---|
  | `!impact(size=s\|m\|l\|xl)` | a boom and crash starting at the position. `l` is the default; `xl` is longer and bigger |
  | `!riser:2` | a 2-bar sweep that **ends** at the position, leading into it |
  | `!zaps(count=6, every=8)` | a run of bright chirps rising in pitch, one per note value of `every` (8 = 8th notes, 4 = quarters, 16 = 16ths; the default count is 4): lists, data. Quiet enough for intros at `mix fx -9` |
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
- **Section names.**
  - **Reserved** (errors): `for in if elif else every def return form with and or not true false none as at bars`, and the builtins `euclid rot rev len min max`.
  - **Avoid:** style and motif names (`warm`, `dark`, `up`, `full`, `sub`, your motif names), because a section is also a variable and `pad:warm` would pick up a section called `warm`.
  - **Allowed:** directive words (`groove`, `mix`, `feel`, …) work as section names.
- **Availability:** the re-harmonising transform `to=` is not available. Recorded strings, brass, winds and other voices are available through installed `sampler/<voice>` entries; check the current catalog, sample manifest and supported ranges. Do not infer a voice name from an instrument family. For ambience and nature sounds, see [instruments.md](reference/instruments.md).
- **Tempo ramps and video.** A ramp keeps cues and frames exact, but beats no longer land on whole frames inside it, so keep ramps to endings and transitions.

## 8. Examples (complete, checked, rendered and balanced)

Each passes `songmap listen` clean (only expressive notes), with its peak at least 2 dB above every other section.
- [examples/hopeful_explainer.sm](examples/hopeful_explainer.sm), D major, 1:15, mood `balanced`:
  - a piano question/answer theme;
  - guitar ripples, a groove with ghosts and a bass that locks to the kick;
  - the build holds back its backbeat until `home`;
  - the synth lead takes the tune;
  - a caveat 9 dB under its neighbours, and a plagal ending.
- [examples/cinematic_build.sm](examples/cinematic_build.sm), E minor, 1:40, a form block, mood `balanced`:
  - three rising waves driven by a loop index (dynamics and euclid hats);
  - risers into the drops, per-bar fills, the lead resting in the last bar;
  - a stop-time before a held caveat with a borrowed-chord turnaround;
  - 16th and open hats saved for the finale;
  - a plagal close on E minor.
- [examples/lofi_late_notes.sm](examples/lofi_late_notes.sm), D dorian, 90 BPM, mood `lofi`:
  - a 12-step shuffle, rootless 9th chords with an anticipation, a bass slide;
  - a piano melody with a grace note and breathing rests;
  - a drum-less bridge, and a fuller reprise with an open pad;
  - a resolution to Dm9.

Section loudness measured from the renders:

| Example | Sections, in order (LUFS) |
|---|---|
| hopeful explainer | intro −20.3, verse −15.7, lift −13.7, **breath −22.1**, home −11.5, outro −16.5 |
| cinematic build | intro −25.5, waves −20.0 / −17.4 / −15.2, drops −13.5 / −13.7, **held −22.3**, finale −11.5, coda −21.1 |
| lo-fi | dusk −26.9, walk −15.2, tune_a −14.8, **alone −19.6**, tune_b −12.0, fade −21.4 |
