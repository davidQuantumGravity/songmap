# Performance: turning written notes into played notes

The gap between "MIDI" and "music" is mostly here. Instruments decide what a velocity *sounds* like ([INSTRUMENTS.md](INSTRUMENTS.md)); this layer decides **when** each note happens, **how hard**, and **how long**. Reference code is in [reference/sketch_v1/perform.py](../reference/sketch_v1/perform.py) (`perform()`, `Feel`, `GROOVES`, `voice_lead()`). Annotations are parsed by [notation.py](../reference/sketch_v1/notation.py).

## 1. Pipeline

For each part in each section, `perform()` applies these steps in order. Each step is optional and seeded.

| # | Layer | Input | Effect |
|---|---|---|---|
| 1 | **Written dynamics** | `=mf`, `<`, `>`, `^`, `!`, `(ghost)`, `@NN` in motifs; `X x - o` in step strings | Base velocity per note. Hairpins interpolate by onset time, keeping accents relative to the ramp |
| 2 | **Section shape** | `dyn: mp<f`, `p<ff>mp` | Multiplies each note by `level(position)/level(mf)` across the section, even when a 2-bar pattern loops (`section_start`, `section_beats`) |
| 3 | **Metric accent** | `metric` (0–1) | Downbeat ×1.08, mid-bar ×1.04, beats ×1.0, 8th off-beats ×0.95, 16ths ×0.91 (scaled by `metric`) |
| 4 | **Melodic shaping** | `high_loud`, `arch` | KTH rules: higher notes louder (`(pitch−mean)/24` per unit), and a crescendo-decrescendo over each phrase |
| 5 | **Groove** | `swing`, `swing_grid`, `template`, `groove_amt` | Moves off-steps later (swing) and applies a 16-step template of timing and velocity offsets (`push`, `laid_back`, `mpc`, `dilla`, or user-defined) |
| 6 | **Feel offset** | `offset_ms` per part | The snare lays back +6 ms, the bass pushes −3 ms: players have personalities |
| 7 | **Humanize** | `time_ms`, `drift_ms`, `vel_sd` | White jitter **plus slow drift** (a smoothed random walk): humans wander gradually, they don't jitter randomly per note |
| 8 | **Articulation → gate** | `'` `_` `!` `^` `~`, part `art:`, `gate` | gate = written length × {normal 0.9, staccato 0.45, staccatissimo 0.25, tenuto 1.0, marcato 0.7, accent 0.85, legato 1.04} × part gate |
| 9 | **Legato / glide** | `~` slur | Mono instruments receive `glide_from`, so they glide instead of re-attacking. Poly instruments overlap (legato 1.04) |

The output is a list of `Played(time_seconds, Note(pitch, vel, gate, seed, glide_from))`. Velocities are clipped to 0.02–1.0. Explicit `@NN` velocities skip layers 2–4.

## 2. Velocity scale

| Mark | Velocity | MIDI |
|---|---|---|
| `=ppp` | 0.15 | 19 |
| `=pp` | 0.25 | 32 |
| `=p` | 0.37 | 47 |
| `=mp` | 0.50 | 64 |
| `=mf` | 0.62 | 79 (default) |
| `=f` | 0.75 | 95 |
| `=ff` | 0.87 | 110 |
| `=fff` | 1.00 | 127 |
| `^` accent | ×1.2 + 0.04 | |
| `!` marcato | ×1.3 + 0.04, gate 0.7 | |
| `(x)` ghost | ×0.45 | |
| Step `X` / `x` / `-` / `o` | 1.0 / 0.78 / 0.55 / 0.38 | |

Instruments turn velocity into loudness with `vel ** vel_curve`, so dynamics stay perceptually even. With `vel_curve` = 1.5, mf→f is about +2.5 dB and p→ff is about +11 dB. They also turn it into **brightness and attack**, which is what listeners actually hear as "louder playing".

## 3. Groove and swing

- `swing` is the fraction of the pair spent on the first note: 0.5 is straight, 0.54–0.58 is a subtle modern swing, 0.62 a lazy shuffle, 0.66 a triplet shuffle. `swing_grid` picks 8ths or 16ths. Only notes exactly on the off-step move.
- **Templates** are lists of `(timing offset as a fraction of a 16th, velocity factor)` per 16th step:
  - `push`: urgent, ahead of the beat.
  - `laid_back`: relaxed, behind the beat.
  - `mpc`: a ~58% 16th swing with off-beat velocity dips.
  - `dilla`: uneven and drunk, but repeating every 2 beats.
  - Users add templates in `grooves/*.yaml`, or extract one from audio in Phase 9 (onset-detect a reference loop and average the timing deviations per step).
- **Defaults by mood:**
  - techno: straight, metric 0.3, snare +0 ms.
  - house: swing 0.54/16.
  - hip-hop: `mpc` + snare +8 ms.
  - cinematic and documentary: straight, humanize 6/4 ms, arch 0.5.
  - jazz: swing 0.62/8, ride `laid_back`.

## 4. Humanize amounts (starting points)

| Part | time_ms | drift_ms | vel_sd | Notes |
|---|---|---|---|---|
| Kick (electronic) | 0–1 | 0 | 0.02 | Leave tight: it's the clock |
| Snare / clap | 3 | 2 | 0.04 | `offset_ms` +4…+10 for weight |
| Hats | 4 | 3 | 0.06 | Plus a groove template; vary `o`/`-`/`x` in steps |
| Bass | 3 | 2 | 0.03 | `gate` 0.8–0.9 for bounce |
| Pads | 10 | 0 | 0.02 | Also randomize chord-tone onset (strum) by 0–30 ms |
| Piano / keys | 6–8 | 5 | 0.03 | `high_loud` 0.4, `arch` 0.5. **Melody leads by 10–20 ms** (melody lead is a known pianist trait) |
| Strings / brass | 12 | 8 | 0.03 | Swells via `dyn`, not velocity; slow attacks |
| Guitar strums | — | — | — | Chord notes 8–25 ms apart, down-strums low→high, up-strums high→low and softer |

## 5. Voicing and voice leading

`voice_lead(prev, root, intervals, lo, hi, voices)` searches every playable voicing (all chord tones present, the 5th droppable, no unisons, gaps of at most an octave, span of at most 2 octaves). It picks the one with **least total motion** from the previous chord, plus taste penalties: prefer doubling the root, and avoid a 9th or 2nd as the lowest voice. Tested on Am→F→C→G-type progressions, it keeps common tones and moves the other voices by step.

Planned voicing styles (`voicing.style`):
- `drop2`: drop the second-highest voice an octave (piano and guitar comping).
- `shell`: 3rd and 7th only.
- `quartal`: stacked 4ths, a modern or cinematic sound.
- `spread`: the root low, the rest an octave or more up (strings).
- `top: <motif>`: force the top voice onto a melody (harmonization).

## 6. Expression over time (automation)

`expression` lanes now change volume, brightness/body, added vibrato, pitch, width and
sound-source balance **inside held notes**. Points use quarter-note beats and follow tempo
ramps; terminal values hold until another lane changes them. Studio's **Instruments →
Expression** tab edits these curves and schedules real named `family/` techniques.
See [the syntax, ranges and response-calibration method](EXPRESSION_ARTICULATION_RESPONSE.md).
The legacy `auto:` field is parsed, but its formerly described general parameter ramps
are not implemented; use the explicit `expression` controls for working continuous lanes.

## 7. MIDI export mapping

- Velocity: `round(vel*127)`.
- Note length: the post-articulation gate.
- Glides: pitch-bend ramps (±2 semitone default range; wider glides use legato re-triggers and set `CC65` portamento).
- Section dynamics: written into velocities and also as **CC11** (expression) on sustained parts.
- Groove and humanize are baked into note times. An optional `--quantized` export keeps the grid and writes the offsets into a sidecar `groove.json`, for DAW users who want to re-groove.

## 8. Rules worth adding later (KTH Director Musices set)

- Duration contrast: short notes a little shorter, long notes a little longer.
- Final ritardando: the last 1–2 bars slow along a square-root curve (needs a tempo map).
- Phrase punctuation: micro-pauses at phrase ends.
- Leap articulation: a small gap before a big leap.
- Harmonic charge: chords far from the tonic slightly louder and longer.
- Melodic charge: non-chord tones emphasized.

Each is one function over the `Played` list, gated by a `Feel` field defaulting to 0.

## 9. Tuning by ear

Every number above is a starting point. The GUI's **Feel panel** ([GUI.md](GUI.md) §4) loops a section, shows the note grid with played offsets, and exposes these fields as knobs. "Copy as songmap" puts the result back into the song file.
