# SongMap Studio: the GUI (design v2, 2026-10-22)

A local app in which songs, instruments, mixes and videos are made **both as text and visually**, and every visual
edit is written back to the same text files the language and the LLM use. It replaces the v1 plan, which predated
the language, the sampler, 36-ET, the performance stage, moods and the video renderer.

## 1. Goals

1. **One model, two views.** The `.sm` program and the visual editors are views of one song tree. Typing in the code
   pane updates every visual pane; turning a knob, drawing a note or dragging a fader rewrites the code (printed by
   `songmap fmt`, so it stays readable).
2. **Every instrument editable, every instrument buildable.** All 17 native instruments, the sampler, and new ones:
   knobs for every parameter, and a **patch editor** where an instrument is a graph of modules wired together, so its
   definition and wiring can be changed, not only its knob values.
3. **DAW basics.** Arrangement timeline, piano roll (36-ET aware), step grid, mixer (volume, pan, mute/solo, sends,
   insert effects), transport with loop and scrub, audition from an on-screen keyboard.
4. **Every output.** WAV, MP3, stems, MIDI, `cues.json`, MP4 video, PNG/SVG images (poster frame, score page, piano
   roll), QA report.
5. **Videos designed in the GUI.** What appears where, how it looks and when: layers, positions, sizes, colours,
   fonts, which parts, how notes are named, with a live frame preview.
6. **The engine stays the single source of truth.** No DSP in JavaScript. The browser plays audio the engine
   rendered.

## 2. What the GUI has to handle: a study of the engine (2026-10-22)

### 2.1 Instruments

Every instrument declares its knobs as `PARAMS` (`Param`: name, default, range, unit, knob curve, group, doc), so
**knob panels are generated, never hand-written**. The table lists what each one is internally, because the patch
editor (§4.1) has to express all of it.

| Instrument | Params (groups) | Signal chain | Velocity → timbre |
|---|---|---|---|
| `kick` | 12 (pitch, amp, tone, velocity, variation) | sine with exponential pitch sweep → t60 env; + sub sine; + band-passed noise click; → tanh drive | sweep depth, click level |
| `snare` | 11 (+ filter) | two sine modes (shell) + noise HP→LP (wires) + band-passed snap → drive | wire brightness and length |
| `clap` | 8 | 1–8 noise bursts (jittered spacing, burst envelope) → band-pass | brightness |
| `hat` | 9 | six detuned squares (metal) + noise → band-pass → high-pass → AD env | decay, brightness |
| `bass` | 16, mono | saw + square + sub sine (glide) → resonant SVF with filter env → drive → ADSR | cutoff |
| `pad` | 15 | N unison saws with slow drift, spread across stereo → SVF with LFO → ADSR | cutoff |
| `pluck` | 11 | pulse + saw → SVF with filter env → t60 env × ADSR | cutoff |
| `lead` | 16, mono | N unison saws with delayed vibrato and glide + breath noise → SVF → ADSR | cutoff |
| `string_pluck` | 9 | filtered noise burst, pick-position comb → Karplus-Strong string → body EQ peaks | excitation brightness |
| `keys` | 13 | modal piano: stiff-string partials, hammer comb, two-stage decay, two-string detune + thump noise; pitch-dependent pan | hammer hardness (spectral tilt) |
| `epiano` | 10 | 2-op FM with decaying index + 14:1 tine transient → t60 → tremolo auto-pan | FM index ("bark") |
| `organ` | 14 | nine drawbar sines + percussion + key click → rotary (Doppler + AM) | none (organs are velocity-blind) |
| `clean` | 11 | additive partials (harmonic, golden 2^m·φ^n, or odd spectrum), damping, raised-cosine envelope | rolloff |
| `riser`, `impact`, `zap`, `tick` | 3–9 | noise sweeps, sine sweeps, square chirps, sine pings | some |
| `sampler/<library>` | 6 + the SFZ program | regions by key, velocity and round robin; crossfaded layers; repitched; release samples; chokes | layer choice |

Presets (`presets/<instrument>/<name>.yaml`, 27 today incl. the stable `*/still` and `clean/*` sets) are parameter
sets on top of an instrument. **Gaps:** an instrument's *structure* is Python code, so today nothing can be rewired;
only the sampler loads its structure from data.

### 2.2 Songs, performance, mix, master, video

- **Songs:** `.sm` language (variables, `with`, form, loops, `every`, per-bar variants) or YAML; both compile to the
  same tree; `songmap fmt` prints either losslessly. Notes are mostly *generated* (styles, chord-relative figures,
  motifs with transforms), not stored note by note.
- **Performance stage** (`perform/play.py`): moods (`balanced` default, `v0`, `cinematic`, `lofi`, …) set groove,
  humanize and per-part feel (offset, strum, arch, high_loud, gate).
- **Mix today:** per part gain, pan, sends to reverb returns, sidechain from a kit piece; master `standard`, `clean`
  or `legacy`. **Gaps:** no per-part insert effects (EQ, compressor, delay, chorus, saturation, filter), no automation
  lanes, no meters.
- **Video today** (`visual/`): one fixed layout (header, letter names, grand staff, piano roll) with a theme, size,
  page length and part list. **Gaps:** no layout control, layers, colours per part, or images.
- **Exports today:** WAV 24-bit, MP3, stems (float WAV), `cues.json`, `qa.json` + `qa.png`, MP4 + poster.
  **Gap:** MIDI.

## 3. Principles

1. **Edits are operations on the song tree,** not text patches: `set part`, `set mix`, `set note clip`, `set
   instrument param`, `move section`… Each operation is validated, applied, and the file is re-printed. Comments and
   variables the user wrote by hand are preserved where the operation does not touch them (the printer keeps the
   header comment; operations rewrite only the lines they own).
2. **Generated vs. written notes.** A part played by a style or a motif is shown in the piano roll as *generated*
   (hatched). Editing it first **bakes** that part in that section into a clip of explicit notes, which then writes
   back as a `notes:` value (36-ET pitches included). Un-baking restores the style.
3. **Schema-driven UI.** Instruments, patch modules, effects and video layers all expose `PARAMS`-style schemas; the
   GUI draws knobs from schemas, so engine additions appear without GUI code.
4. **Incremental rendering.** The server keeps the last arrangement and caches rendered notes and per-part buses; an
   edit re-renders only the parts it touched. Single notes for audition render in milliseconds.

## 4. Engine foundations the GUI needs (built before or with the screens)

### 4.1 Patch instruments (rewiring)
`instruments/patch.py`: an instrument defined as a YAML graph of modules (INSTRUMENTS.md §7), compiled at load time.
- **Modules** (each with a `PARAMS` schema): `osc` (sine, saw, square/pulse, triangle, supersaw/unison, additive with
  harmonic/golden/odd spectra), `fm` (operator), `noise` (white, pink, bursts), `env` (adsr, ad, t60, raised-cosine,
  burst train), `lfo` and `drift`, `filter` (SVF lp/bp/hp with modulated cutoff, RBJ peak/shelf, one-pole), `shaper`
  (drive, fold), `ks` (Karplus-Strong with pick comb), `modal` (partial bank with inharmonicity and two-stage decay),
  `comb`, `delay`, `rotary`, `pan`/`spread`, `mix`, `vca`, `sampler` (an SFZ program as a source).
- **Wires** connect outputs to inputs and to **modulation targets** (cutoff, pitch, amplitude, pan, index).
- **Expressions** in any numeric field (`"2500 * 2**(1.5*(vel-0.7))"`) use `vel`, `pitch`, `freq`, `t`, `gate`,
  `rand` and macro names, through a safe AST evaluator (no `eval`).
- **Macros** map one knob to several parameters; macros are the instrument's knobs everywhere else.
- **Every native instrument ships as a patch template** (`patches/native/kick.yaml`, …) that renders the same sound
  (checked against the native instrument by a test), so "open kick as a patch" shows its real wiring and lets you
  change it. The native classes stay as the fast path.

### 4.2 Insert effects and the mixer model
`mix/fx.py` gains schema'd effect units: `eq` (bands), `compressor`, `drive`, `filter`, `delay` (ping-pong, synced),
`chorus`, `reverb` (as an insert or a return), `gain`, `width`. A part's `mix` entry gets `inserts: [{fx: eq, …}]`;
returns and the master get chains too. Meters (peak/LUFS per part, per section) come back with every render.

### 4.3 Clips and the note writer
`parse/clip.py`: explicit notes for a part in a section (onset, length, pitch as float MIDI, velocity, articulation),
and a writer that prints them as note-language text: sticky durations, chords, `^`/`v` sixth-step prefixes, `@vel`.
Baking a generated part produces a clip; the round trip clip → text → parse is exact (tested).

### 4.4 Views: what a video or image shows
`visual/view.py`: a **view spec** (YAML, stored with the song as `view:` or in `<song>.view.yaml`): canvas size, fps,
background (colour, gradient, image), and a list of **layers**, each with a schema: `title`, `section_banner`,
`chords`, `letters`, `staff` (grand/single, which parts, colour per part), `piano_roll` (window, 36-row or 12-row,
colour per part, golden layers tinted), `waveform`, `spectrum`, `text`, `image`, `timeline`, positioned by a
rectangle and z-order, with visibility over time (always, or per section). The current fixed layout becomes the
default view. The same spec renders MP4s, posters and stills.

### 4.5 MIDI export
`export/midi.py` (mido): one track per part, velocities, played timing, pitch bend for sixth-steps (36-ET notes as
MPE-style per-note bend or one channel per layer), drums on channel 10.

## 5. Architecture

```
 browser: React + TypeScript (Vite build, served by the Python server)
 ┌───────────────────────────────────────────────────────────────┐
 │ Code · Arrangement · Piano roll · Steps · Mixer · Rack ·        │   REST: load/save, operations, exports
 │ Instrument editor · Patch graph · Video designer · Exports · QA │◄────────────────────────────────────►
 │ WebAudio player (buffers from the server)                       │   WebSocket: render progress, audio,
 └───────────────────────────────────────────────────────────────┘   meters, check diagnostics
 python: FastAPI + uvicorn (songmap/gui/)
   project (song tree + arrangement + render cache) · operations · audition · render jobs · exports
   → the songmap engine, unchanged in kind (parse, expand, perform, instruments, mix, master, visual)
```

- **Launch:** `songmap gui [song.sm]` starts the server on 127.0.0.1:8765 and opens the browser (`.claude/launch.json`
  has the `songmap-gui` entry).
- **Audio:** the server renders and sends 16-bit or float PCM (or MP3 for long renders); the browser plays it with
  WebAudio, keeps the playhead in sync with the views, and loops a range. Audition notes are rendered on demand and
  cached by (instrument, params, pitch, velocity, gate).
- **Files:** the server reads and writes the song files in the repo (`songs/…`, `examples/…`), presets
  (`songmap/presets/`), patches (`songmap/patches/`) and views. Every write is atomic and keeps a `.bak`.

## 6. Screens

```
┌ SongMap Studio ── songs/golden/02_deceptive_light.sm ─ [▶ ■ ⟲ 1:04.2] ── LUFS −17.5 ─ [Export ▾] ─────────┐
│ FILES │ CODE (.sm, live check)            │ ARRANGEMENT: sections, parts lanes, events, cues, video thumbs│
│ songs │ song "Deceptive Light" 120 4/4 G  │ intro│verse     │pre│chorus    │post│verse_2  │…             │
│ presets│ chords …                         │ drums ▮▮▮▮ ▮▮▮▮ ▮▮ ▮▮▮▮ …                                     │
│ patches│ verse 8 | drums:pocket …         ├───────────────────────────────────────────────────────────────┤
│ views │ ✓ ok · 77 bars · 2:37            │ PIANO ROLL (36-ET rows; golden notes tinted; generated hatched)│
├───────┴──────────────────────────────────┴───────────────────────────────────────────────────────────────┤
│ MIXER: per part fader, pan, mute/solo, sends, inserts (knobs), meters · returns · master                   │
│ RACK / INSTRUMENT: knobs by group, presets A/B, keyboard + velocity pads · [Open as patch] → PATCH GRAPH     │
│ VIDEO: layers list · properties · live frame preview at the playhead · [Render MP4] [Save PNG]             │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Panes are dockable tabs. Each one is a view of the same project state; selecting a part in any pane selects it
everywhere (rack, mixer strip, piano-roll lane, code line).

| Screen | What it does | Writes back to |
|---|---|---|
| **Code** | the `.sm`/YAML source with syntax colouring, live `check` diagnostics (line + suggestion), `fmt` | the file |
| **Arrangement** | sections as blocks (drag to resize/reorder), part lanes, events and cues on a frame/bar ruler | section lines, events, cues |
| **Piano roll** | notes of one part (or all, coloured); 12- or 36-row grid; draw, move, resize, velocity lane; bake/un-bake | clips (`notes:`) |
| **Steps** | kit lanes as step grids (16/12/24 per bar), velocity per step, flam/ratchet | step strings |
| **Mixer** | faders, pan, mute/solo, sends, insert chains, returns, master; live meters | `mix`, `returns`, `master` |
| **Rack + instrument** | parts and their instruments; generated knob panels; presets (A/B, diff, save); keyboard (36-ET aware) and velocity pads | `inst` lines, presets |
| **Patch graph** | modules as nodes, wires, modulation, macros; templates incl. every native instrument | `patches/*.yaml` |
| **Feel** | mood, groove, humanize, per-part feel with a played-vs-written view | `groove`, `feel`, `mood` |
| **Video** | view layers, properties, preview at the playhead; render MP4/PNG | the view spec |
| **Exports** | WAV, MP3, stems, MIDI, cues, MP4, PNG/SVG, QA | files under `build/` or `songs/…/renders/` |
| **QA / Listen** | `qa.json` numbers, section loudness, spectrogram, `songmap listen` findings | — |

## 7. API (server)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/files` | songs, presets, patches, views in the repo |
| GET/PUT | `/api/project?path=` | load a song: source text, tree (JSON), arrangement summary, diagnostics; save text |
| POST | `/api/check` | source text → diagnostics + summary (fast, no audio) |
| POST | `/api/op` | apply an operation to the tree → new source text + tree |
| GET | `/api/catalog` | instruments (schemas), presets, styles, moods, effects, patch modules, view layers |
| POST | `/api/audition` | instrument + params + pitch/vel/gate → PCM |
| POST | `/api/render` | render the song (or a range or part solo) → job; audio + meters + QA over the WebSocket |
| GET | `/api/notes?part=&section=` | written/played notes for the piano roll (with generated flags) |
| POST | `/api/frame` | view spec + time → PNG |
| POST | `/api/export` | formats → files |
| WS | `/ws` | progress, audio ready, diagnostics |

## 8. Milestones

| | Scope | Done when |
|---|---|---|
| **S1 — Studio shell** | server, project load/save, code pane with live check, render + playback with transport, arrangement overview, exports (WAV/MP3/stems/cues/MP4/PNG) | open any song in `songs/`, edit its text, hear it, export every existing format, all from the GUI |
| **S2 — Rack and knobs** | catalog endpoint, generated knob panels for all 17 instruments + sampler, presets, keyboard audition, writes `inst` lines | every instrument audible and editable; a knob change writes the song and is heard |
| **S3 — Mixer** | insert-effect units (§4.2), mixer screen, meters | volume, pan, mute/solo, sends and inserts edit the song and are heard; meters match `qa.json` |
| **S4 — Piano roll and steps** | clips and the note writer (§4.3), piano roll (36-ET), step grid, bake/un-bake | drawing and editing notes round-trips exactly through the text |
| **S5 — Patch instruments** | patch engine (§4.1), patch graph screen, native instruments as templates | open any native instrument as a patch, rewire it, save it, use it in a song |
| **S6 — Video designer** | view spec (§4.4), video screen with live preview | change layers/positions/colours and see the frame; render the MP4 with that view |
| **S7 — Feel and MIDI** | feel screen, MIDI export (§4.5) | mood/groove edits are heard; MIDI opens in a DAW with 36-ET pitch bends |

**Testing:** API tests with FastAPI's TestClient (load/check/op/render/export); round-trip tests for every operation
(tree → text → tree identical); patch templates against native renders; UI checks in the desktop app's browser pane.
