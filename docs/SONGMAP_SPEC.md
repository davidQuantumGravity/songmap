# SongMap format, v0.2 (YAML form)

A song map is one text file that fully describes a soundtrack: tempo, harmony, themes, orchestration, *how* every part is played (dynamics, articulation, groove), mix intent, and the sync points of the video it scores. The engine expands it into notes, renders audio, and exports MIDI plus a frame-accurate cue sheet.

There are two equivalent spellings:
- **YAML form** (this document): explicit and easy to diff. Use it for hand edits, the GUI's save format, and anything unusual.
- **Compact form** ([COMPACT_FORMAT.md](COMPACT_FORMAT.md)): one line per section, about 2–3× fewer tokens. Use it when an LLM writes or revises a song.

Both parse to the same internal tree, and a lossless converter between them (`songmap fmt`) is planned; today the CLI has `check`, `render` and `migrate`.

**Changes from v0.1:** durations are now sticky; dynamics, articulation, groove, humanize and automation are new; positions can be bar:beat or video frames; there are `instruments`, `mix` and `master` blocks; sections inherit from earlier ones; motifs have transforms; drums can use step strings; video sync is first-class. v0.1 files still load with a deprecation warning. The only semantic change is sticky durations, and `songmap migrate` rewrites old files for you.

---

## 1. Top level

```yaml
songmap: 0.2
title: Week of Oct 13 — The Swarm
tempo: 120              # BPM; per-section overrides allowed (see §9)
meter: 4/4
key: E minor            # 'E minor' | 'Em' | 'D dorian' | 'F# major' ...
fps: 30                 # cue export; warns unless 60*fps/tempo is an integer
seed: 7                 # every random choice (humanize, round-robin) derives from this
tail_seconds: 3
video:                  # optional: the composition this score is locked to
  composition: WeekSwarm
  frames: 3690          # render length check: error if bars*frames_per_bar+tail != frames ± 1 bar

instruments: {...}      # §2 the ensemble
groove: {...}           # §5 default feel for all parts
harmony: {...}          # §3
motifs: {...}           # §4
sections: [...]         # §6
events: [...]           # §8
mix: {...}              # §10
master: {...}           # §10
qa: {...}               # §11
expression: {...}       # beat curves inside held notes; see the guide below
techniques: {...}       # named recorded techniques on subsequent notes
```

Continuous curves use the same mapping in YAML and `.sm`:

```yaml
expression:
  verse:
    violin:
      volume: [[0, 0.25], [4, 1], [8, 0.3]]
techniques:
  verse:
    violin: [[0, sustain], [4, pizzicato]]
```

The part uses `family/violin` for these recorded techniques. Curves use quarter-note
beats from section start, including at tempo ramps; endpoints must cover the section.
See [the implemented controls, inheritance and calibration](EXPRESSION_ARTICULATION_RESPONSE.md).

## 2. Instruments (the ensemble)

Each **part** is a named role that plays one instrument. The parts `drums`, `bass`, `pad`, `arp`, `lead` and `fx` exist by default and map to sensible instruments. Declare more parts freely (`cello`, `piano`, `brass`, `choir`, `gtr`).

```yaml
instruments:
  drums: {kit: {kick: kick/punchy, snare: snare/tight, hat: hat/808, ohat: hat/808_open, clap: clap}}
  bass:  {use: bass/acid_sub, cutoff: 650, glide: 0.04}    # preset + param overrides
  pad:   {use: pad/warm_analog, voices: 7}
  arp:   pluck/glass
  lead:  {use: lead/supersaw, vib_depth: 18}
  keys:  {use: keys/felt_piano, hardness: 0.35}             # extra part
  gtr:   {use: string_pluck/nylon, layer: [string_pluck/steel]}   # layering = round-robin across sources
  fx:    {riser: riser, impact: impact/cinematic, zap: zap, tick: tick}
```

- `use:` is `instrument/preset`. Presets live in `presets/<instrument>/<name>.yaml` and are written by the GUI ([GUI.md](GUI.md)).
- Any key besides `use`/`layer`/`kit` is a parameter override, validated against the instrument's schema ([INSTRUMENTS.md](INSTRUMENTS.md)). Unknown names are errors with suggestions.
- `sampler/<library>` and `plugin/<name>` are also valid instrument names; see INSTRUMENTS.md §5.

## 3. Harmony

```yaml
harmony:
  default: [Em, C, G, D]          # loops for the whole song
  chord_bars: 2                   # bars per chord in the list above
  progressions:                   # named, reusable; sections pick one
    verse:  "Em:2 C:2 G:2 D:2"    # chord:bars (beats with a decimal, e.g. D:0.5)
    lift:   "C:1 D:1 Em:2 | Am7:1 Bsus4:0.5 B7:0.5 Em:2"
    pedal:  "Em Em/D Cmaj7/E Em"  # bare = 1 bar each
  voicing: {range: [e3, b4], voices: 4, lead: smooth}    # default pad/keys voicing (§7)
```

Chord symbols: root (`A`–`G`, `#`/`b`) + quality (`m`, `dim`, `aug`, `5`, `sus2`, `sus4`, `6`, `m6`, `7`, `maj7`, `m7`, `m7b5`, `dim7`, `add9`, `madd9`, `9`, `maj9`, `m9`) + optional `/bass`. `N.C.` means no chord.

## 4. Motifs (melodies) and the note language

```yaml
motifs:
  theme:   "=mf e4^ d8' c' e4_ g | a2~ g4 (e8) r"         # letter mode, base octave 4
  answer:  {deg: "=p < 0 -3 0 2 | 1/2 0 =f", octave: 5}   # scale-degree mode
  riff:    {notes: "e8 e e+ e d e g e", octave: 2}
  chordal: "[e,g,b]2 [d,f#,a]"                            # chords inside melodies
```

| Token | Meaning |
|---|---|
| `c d e f g a b` + `#`/`b` + `+`/`-` | Pitch. `+`/`-` shift octaves relative to the motif's `octave` (default 4, so `c` is middle C) |
| `0 1 -3 #4 b7` | Scale degree in `deg:` mode (0 = tonic of the song key or the motif's `key:`) |
| `R 3 5 7 9 b7 #11` + `+`/`-` | Chord-relative tones in `rel:` mode (R = root of the chord sounding at that moment). This is how bass, arp and comping styles follow the harmony: `bass: {rel: "R8 R R+' R r R 5~ R+"}` |
| `1 2 4 8 16 32`, dots, `t` | Duration (whole … 32nd), dotted, triplet. **Sticky:** omit it to repeat the previous duration. In deg mode it goes after a slash: `3/8.` |
| `r` | Rest |
| `[c,e,g]` / `[0,2,4]` | Chord |
| `=ppp … =fff` | Dynamic level for following notes (the `=` stops `f` the note being read as `=f` forte) |
| `<`, `>` | Crescendo / diminuendo to the next dynamic mark (or one step if none follows) |
| `^` | Accent (louder, slightly harder attack) |
| `!` | Marcato (strong accent, shortened) |
| `'` | Staccato (gate 45%) |
| `_` | Tenuto (full length, slight weight) |
| `~` | Slur into the next note: legato overlap, or **glide** on mono instruments |
| `@0..127` | Explicit velocity; overrides every dynamics layer |
| `(e8)` | Ghost note (≈45% velocity) |
| `{d}e4`, `{c,d}e4` | Grace note(s) just before the main note |
| `\|` | Bar line. **Checked:** a bar with the wrong number of beats is an error that names the bar |

**Transforms** can be used anywhere a motif name is accepted, chained with `:`:

| Transform | Effect |
|---|---|
| `theme:t+2` | Transpose 2 scale degrees (deg motifs) or semitones (letter motifs) |
| `theme:oct-1` | Down an octave |
| `theme:inv` | Melodic inversion around the first note |
| `theme:rev` | Retrograde |
| `theme:aug` / `theme:dim` | Durations ×2 / ÷2 |
| `theme:dyn=p` | Replace the written dynamics |
| `theme:frag=2` | First 2 bars only; `frag=-1` = last bar |
| `theme:x2` | Repeat twice |
| `theme:thin=0.25` | Keep only the strongest 25% of notes by metric position (density control: 25/50/75/100%) |
| `theme:canon=4@8` | 4 staggered copies, each entering a 16th later (`@8` = 8th) |
| `theme:to=Am` | Re-harmonize: re-fit degrees to another chord/key (keeps contour) |

Example: `lead: [theme, answer, theme:t+2, answer:inv:dyn=f]`.

## 5. Groove, feel and humanize

Set the defaults once at the top and override per section or per part.

```yaml
groove:
  swing: 0.54          # 0.5 straight · 0.58 light · 0.66 triplet shuffle
  swing_grid: 16       # swing 8ths or 16ths
  template: straight   # straight | push | laid_back | mpc | dilla | <user-defined>
  humanize: {time_ms: 4, drift_ms: 3, vel: 0.04}
  metric: 0.5          # downbeat emphasis strength
parts_feel:            # per-part defaults (players have personalities)
  snare: {offset_ms: +6}          # lays back: heavier backbeat
  bass:  {offset_ms: -3, gate: 0.85}
  keys:  {high_loud: 0.4, arch: 0.5, time_ms: 7}
```

Full semantics are in [PERFORMANCE.md](PERFORMANCE.md). Everything is seeded, so renders are bit-for-bit reproducible.

## 6. Sections

```yaml
sections:
  - name: terminal
    bars: 4
    dyn: pp<mp                         # the section's dynamic arc (scales every part)
    parts: {arp: dark, fx: ticks, bass: sub}

  - name: swarm_in
    bars: 2
    like: terminal                     # inherit parts, then apply changes
    add: {drums: four_floor, bass: eighths}
    drop: [fx]

  - name: goals
    bars: 10
    dyn: mf
    harmony: verse                     # named progression
    feel: {template: push}             # section-level groove override
    parts:
      drums: {style: full, fills: every 2, crash: phrase}
      bass:  {style: eighths, art: staccato, dyn: mf}
      arp:   {style: up, octaves: 2, auto: {cutoff: "1500>4000 exp"}}
      pad:   {style: warm, voicing: {range: [e3, e5], style: drop2}}
      keys:  {notes: "=p [e,b]1 | [c,g] | [g,d+] | [d,a]", art: tenuto}
```

**Part value forms** (from shortest to most detailed):
1. `style`: `bass: eighths`
2. style with modifiers: `drums: full+fill+hats16`
3. a motif list (melodic parts): `lead: [theme, answer]`, cycled once per chord block or per motif length
4. a dict: `{style | motif | notes | steps, dyn, art, oct, transpose, feel, voicing, auto, mute, gain_db}`

**Drum step strings** can replace styles for any kit piece:

```yaml
      drums:
        kick:  "X.....x...x.....|X.....x...x...x."
        snare: "....X..o....X...|....X..o....X.oo"
        hat:   "x-x-x-x-x-x-x-x-|x-x-x-x-x-x-x-r-"
```

`X` accent · `x` normal · `-` soft · `o` ghost · `.` rest · `f` flam · `r` ratchet (two quick hits). The number of characters per bar sets the grid (16 = 16ths, 12 = 8th-note triplets, 24 = 16th triplets). Patterns loop to fill the section.

**Per-bar variants:** `vary:` gives a part different material for some bars of its section. `bars` are offsets from the section start, as in `name+3`. In those bars the variant's notes replace the part's, and a note belongs to the bar it starts in. A part with `mute: true` and `vary:` plays only in its variants' bars. The SongMap language writes these for per-bar edits (`every 4 bars: bass = eighths`, `bar -1: lead = [answer]`; [LANGUAGE.md §7](LANGUAGE.md)).

```yaml
      bass: {style: sub, vary: [{bars: [3, 7], part: eighths}]}
      lead: {motifs: [theme], vary: [{bars: [7], part: [answer]}, {bars: [2], part: {mute: true}}]}
```

**Inheritance:** `like:` copies another section's `parts`, `harmony`, `feel` and `dyn`; `add:` merges parts in and `drop:` removes them. This is how a chorus repeat costs one line.

## 7. Voicing and orchestration helpers

```yaml
voicing:
  range: [e3, b4]      # lowest and highest note for chord parts
  voices: 4
  style: close         # close | open | drop2 | spread | shell (3-7 only) | quartal
  lead: smooth         # smooth = minimal motion between chords (voice leading); free = re-voice each time
  top: theme           # optional: force the top voice to follow a motif (melody harmonization)
```

Orchestration shortcuts:
- `double: {part: lead, with: keys, oct: -1, dyn: -6dB}` doubles a line in another instrument.
- `split: {part: keys, at: c4}` sends notes below c4 to the left hand (`keys_lh`) and the rest to the right hand.
- `range_check: true` (default) errors when an instrument plays outside its playable range (see INSTRUMENTS.md).

## 8. Events and positions

**Positions** are used by events, automation breakpoints and `qa` rules:

| Position | Meaning |
|---|---|
| `56` | Absolute bar 56, counted from 0, at the downbeat |
| `56:3` | Bar 56, beat 3 (beats are 1-based, like a DAW) |
| `56:3.5` | Bar 56, the "and" of beat 3 |
| `agents` | Start of section `agents` |
| `agents+8`, `agents+8:2` | 8 bars into `agents` (on beat 2) |
| `agents-1` | One bar before `agents` starts |
| `f3960` | Video frame 3960. Snapped to the nearest 16th unless `snap: none` |
| `cue:net_force` | A named cue defined in `cues:` (below) |

```yaml
cues:                     # named sync points from the video (written by hand or by `songmap cues-from-video`)
  clean:      f1680
  net_force:  f2915
  big_number: f3960

events:
  - {at: swarm_in, type: impact}
  - {at: goals, type: riser, bars: 1}             # risers END at `at`
  - {at: cue:big_number, type: impact, size: xl}
  - {at: cue:big_number, type: riser, bars: 2}
  - {at: f1575, type: hit, sound: stab, dyn: ff}  # orchestral stab on the NEGATIVE stamp
  - {at: "agents+15:3", type: stop, beats: 2}     # stop-time: everything except fx is silent for 2 beats
  - {at: so_what, type: drop, bars: 2, keep: [pad]}
  - {at: 2, type: zaps, count: 6, every: 4}       # `every` = note value: one zap per quarter note
  - {at: thruster-1, type: fill, style: snare_roll}
  - {at: summary, type: swell, part: strings, bars: 2, dyn: p<ff}
```

Event types: `impact`, `riser`, `downlifter`, `hit` (stab, with `sound:`), `zaps`, `ticks`, `stop`, `drop` (mute parts), `fill`, `swell`, `crash`, `reverse` (reversed cymbal into `at`), `tape_stop`, `filter_sweep`, and `cloud`: `n` short notes scattered between `at` and `to`, drawn from a scale, with density following a curve, e.g. `{at: f1085, to: f1145, type: cloud, n: 135, part: blips, scale: minor_pent, density: "exp"}`. Use it to make a counter audible. Every event is also written to `cues.json`.

## 9. Tempo, meter, key and scale changes

```yaml
sections:
  - {name: outro, bars: 4, tempo: rit 120>96}       # ritardando across the section
  - {name: ballad, bars: 8, tempo: 90}
  - {name: odd, bars: 8, meter: "7/8 2+2+3"}         # its own meter; groups (eighths) accent the group starts
  - {name: modal, bars: 4, key: "D dorian", tempo: "accel 90>120"}
```

A section `meter` changes the length of its own bars: step strings have that many steps per bar (14 sixteenths in
7/8), bar lines in notes are checked against it, `chords "X:1"` lasts one of its bars, and positions and event
lengths count bars across meters as written (`@-1` is the bar before, in the meter it has).

Tempo is quarter-note BPM, independent of the denominator. Ramps are linear in beats, integrated exactly
to seconds. Meter, tempo and key overrides affect their section only; an omitted or `null` value uses the
song default independently of previous sections. `like:` copies parts, harmony, feel and dynamics, so
write conductor values explicitly when needed on a repeated section.

`key` encodes tonic and scale/mode together, e.g. `C`, `F# minor`, `D dorian` or `C golden7`. Scale-degree
notes and named degree motifs without their own key follow the section key. A motif's explicit `key`
pins it. Letter pitches and chord symbols remain as written; changing the key does not transpose them.
Tuning stays song-wide and must accommodate any microtonal scale. Changes occur at section boundaries;
shorter sections provide additional change points, while a tempo ramp runs within a section.

An optional top-level `conductor` mapping overrides named section instances after section/form expansion:

```yaml
conductor:
  verse_2: {tempo: 108, meter: "7/8 2+2+3", key: "D dorian"}
  outro: {tempo: "rit 108>72", key: null} # null clears the section override
```

Targets must identify existing unique section names; fields are limited to `tempo`, `meter` and `key`.
The canonical formatter resolves these values into section fields. Studio uses this map to edit one expanded
instance while keeping the original structured `.sm` program. See [GUI.md](GUI.md) for the Conductor editor.

Changing tempo breaks whole-frame beats. The engine still exports exact frame numbers in `cues.json`, but it warns when `60*fps/tempo` is not an integer. (Whole-frame tempos at 30 fps: 60, 72, 75, 90, 100, 120, 150, 180.)

## 10. Mix and master

```yaml
mix:
  drums: {gain_db: 0, bus_comp: {threshold_db: -16, ratio: 3}, send: {room: 0.2}}
  bass:  {gain_db: -2, sidechain: {from: kick, depth: 0.5, release: 0.15}}
  pad:   {gain_db: -6, pan: 0, width: 1.2, send: {hall: 0.35}, sidechain: {from: kick, depth: 0.35}}
  lead:  {gain_db: -4, send: {hall: 0.25, delay: 0.2}, eq: [{peak: 3000, gain: 2, q: 1}]}
  keys:  {gain_db: -5, pan: 0.1, send: {hall: 0.3}}
returns:
  hall:  {type: reverb, seconds: 2.4, predelay: 0.02, damping: 0.6}
  room:  {type: reverb, seconds: 0.8}
  delay: {type: pingpong, note: 8., feedback: 0.35}
master:
  target_lufs: -14
  ceiling_db: -1          # true peak
  glue: gentle            # none | gentle | punchy
  preserve_contrast: 4    # dB of section-to-section loudness range to protect (see DESIGN §6)
```

## 11. QA rules

```yaml
qa:
  target_lufs: [-15, -13]
  true_peak_max_db: -1
  contrast:                      # A quieter than B by at least N dB
    - [who, agents, 6]
    - [so_what, output, 6]
  never_silent: [goals, agents, output]
  max_low_ratio: 0.6             # share of energy below 250 Hz in any section
  hits_audible: true             # every impact/hit is >= 3 dB above the surrounding 2 beats (onset check)
```

`songmap render` exits non-zero and prints the failing rule, numbers and section when a rule fails.

## 12. Tuning and microtones

`tuning: 12edo` is the default. `tuning: 36edo` adds sixth-step inflections:
- `^` and `v` **prefixes** on notes, degrees, chord roots and keys (`^c4`, `v3`, `^F#m`);
- golden chords `Cg` and `Cg7`;
- alteration lists `C(v3,^5)`;
- the golden scales `golden3`, `golden4`, `golden7`, `golden10`, `golden13`, `golden23` and the layer mirror `silver13`.

Full design in [GOLDEN_HARMONY.md](GOLDEN_HARMONY.md). Accent `^` stays a suffix, so `^c4^` is a C-up quarter note, accented.

## 12a. A binaural layer (headphones)

`binaural:` adds exact pure-tone pairs, one frequency in each ear ([songmap/mix/binaural.py](../songmap/mix/binaural.py);
the textbook's Chapters 41 and 48). Each carrier `f` is split into `f - d/2` (left) and `f + d/2` (right); carrier `i`
has difference `d = f / 2^octaves` by default. A shared octave reduction preserves the carrier-frequency ratios
through chord changes and does not depend on the carrier's list position.

```yaml
binaural:
  carriers: [A3, "A3*phi", "A4*phi^-1"]   # note names in the song's tuning, MIDI numbers, "220hz", "A3*phi^k"
  beat: octave                             # default mode; each difference derives from its own note
  octaves: 5                               # default divisor 32: A3=220 Hz -> 6.875 Hz
  level_db: -12                            # integrated loudness relative to the music (LU)
  fade: 8                                  # s, in at the start and out at the end
  glide: 6                                 # s: carriers crossfade and beats glide at section starts
  breathe: 2                               # optional swell, one cycle per 2 bars; breath_db: 3 its depth
  carve: true                              # the music gives up a band of +-(widest beat/2 + 3 Hz) at each carrier
sections:
  - {name: deep, bars: 21, binaural: {carriers: [A3, "A3*phi"], gain_db: -2}}
```

In octave mode, omit an independent `ladder` and numeric section `beat` overrides; they would break the frequency
relationship. `octaves` is one positive integer shared throughout the song. Increase it if the derived differences
exceed the engine's 45 Hz limit. For explicitly requested fixed-Hz experiments, set a numeric song-level `beat`
instead (for example `beat: 10`, with optional `ladder: golden`, `same` or a list). Only that legacy mode accepts
independent section ramps such as `beat: "10>6.18"`; a ramp's end value then carries over. The legacy golden ladder
is an independent difference pattern and does not imply octave reduction of the notes.

Other unset section values carry over. The layer is a dry stem (`binaural`: its tones minus the
music it carves); `songmap check` prints its plan, and `songmap listen` flags a carrier a sixth-step from a chord tone
(a problem) or a half step (a pedal point, a note). MP3s of songs with a layer are coded without joint stereo.

## 13. Outputs

| File | Contents |
|---|---|
| `song.wav` | Mastered stereo mix, 48 kHz / 24-bit |
| `stems/<part>.wav` | One per part, plus the reverb returns, pre-master (for re-mixing in a DAW) |
| `song.mid` | All parts with velocities, articulation-adjusted lengths, CC11 (expression) and pitch-bend for glides; drums on channel 10 |
| `cues.json` | Sections, events, named cues, beat grid, all in frames + seconds |
| `qa.json`, `qa.png` | Loudness, peaks, section contrast, band balance, spectrogram with section lines |
| `render.log` | Expanded event counts per part/section, warnings |
