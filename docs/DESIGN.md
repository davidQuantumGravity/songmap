# SongMap: design overview

## 1. Goals

1. **Token-efficient authoring.**
   - A full soundtrack is a short text file: about 0.7–1k characters for a loop-style score, 2–4k for a through-composed one.
   - The LLM writes only musical decisions, never DSP.
2. **Real, human-sounding music.**
   - Instruments respond to velocity with timbre.
   - A performance layer adds dynamics, articulation, groove and phrasing.
   - The mix and master protect the drama.
3. **Music and picture are one document.** Sections, events and cues are addressable by bar:beat *or* video frame, and export as a frame-accurate cue sheet.
4. **Quality compounds.** Better instruments, presets and mastering land in the engine, and every song benefits.
5. **Verifiable without ears.** Every render emits objective QA (loudness, contrast between sections, band balance, audible hits). The LLM reads it and iterates.
6. **Tunable by ear.** A GUI with auto-generated knobs for every instrument, presets, groove tuning and a video-synced song view, all round-tripping to the same text files.
7. **Editable elsewhere.** Stems and expressive MIDI for a DAW.

**Non-goals (for now):** real-time performance; competing with sample-library orchestral mockups for exposed solo passages (the sampler backend covers those).

## 2. Layers

```
  .sm / .yaml song map ──── written by the LLM or a person; edited by the GUI
        │
  ┌─────▼─────────────────────────────────────────────────────────────────────┐
  │ SONG LAYER        parse · resolve (defaults, presets, inheritance, cues)   │ SONGMAP_SPEC.md
  │                   harmony timeline · styles (data) · motifs + transforms   │ COMPACT_FORMAT.md
  ├───────────────────────────────────────────────────────────────────────────┤
  │ PERFORMANCE LAYER dynamics arcs · metric accent · phrasing · groove ·      │ PERFORMANCE.md
  │                   humanize (drift + jitter) · articulation → gate · voicing│
  ├───────────────────────────────────────────────────────────────────────────┤
  │ INSTRUMENT LAYER  Param schema · velocity → timbre · round-robin ·         │ INSTRUMENTS.md
  │                   native synthesis / physical models · sampler · plugins · │
  │                   YAML patch instruments                                   │
  ├───────────────────────────────────────────────────────────────────────────┤
  │ MIX / MASTER      buses · sidechain · sends/returns · glue ·               │ ENGINE.md §6
  │                   contrast-preserving loudness · true-peak limit           │
  ├───────────────────────────────────────────────────────────────────────────┤
  │ EXPORT            song.wav · stems · song.mid · cues.json · qa.json/png    │ ENGINE.md
  └───────────────────────────────────────────────────────────────────────────┘
        │                                  │
   Studio GUI (GUI.md)               Remotion video (cues.json → scene timing)
```

Working, tested reference code for the hard parts of every layer is in `reference/sketch_v1/` ([ENGINE.md §1](ENGINE.md)).

## 3. Renderer strategy (revised)

The first design recommended MIDI → FluidSynth + SoundFonts. That has been **demoted**: it is the "MIDI sound" this project wants to avoid unless the libraries are excellent, and it gives up control over velocity-to-timbre, articulation and glide.

| Backend | Role | Why |
|---|---|---|
| **Native synthesis** (numpy + numba): subtractive, FM, additive, Karplus-Strong, modal, waveguide, formant | **Primary** for drums, bass, synths, keys, plucked strings, mallets, bells and FX; starting point for bowed, brass, wind and voice | Full control of expression; deterministic; no assets or licenses; matches the "from scratch" spirit |
| **Sampler** (SFZ subset) | Exposed acoustic solos (piano, cello, horn), when synthesis falls short | Real recordings with velocity layers and round-robin; still driven by our performance layer |
| **Plugin host** (DawDreamer + VST3: Surge XT, Dexed, Pianoteq…) | Optional pro-grade synths and pianos | Best-in-class sound; plugin params get GUI knobs |
| **Bring-your-own track** (beat and onset detection → cues) | When a licensed track is preferred | Still gets frame-accurate cues and QA |

All four sit behind the same `Instrument` contract, so a song swaps backends by changing one `inst` line.

## 4. Video integration

- **Positions:** `f####` (frame), `cue:name`, `section+bars:beat`, all resolved to absolute beats. Frames snap to the 16th grid, with a warning if the snap moves a cue by more than 1 frame.
- **`cues.json`:** sections, events, cues and the beat grid in frames and seconds. A Remotion helper (`cue('net_force').frame`, `bar(n)`, `beat(n)`) replaces hard-coded frame numbers like those in `VideoA/B/C.tsx`.
- **Audio-only re-mix:** `ffmpeg … -c:v copy` swaps a new score into an existing MP4 in seconds ([RESCORE_PLAN.md §6](RESCORE_PLAN.md)).
- **Spotting:** [SCENE_TIMELINES.md](SCENE_TIMELINES.md) shows the target. Phase 8's `cues-from-video` extracts Slam, Counter-landing and flash frames from the TSX source automatically.
- **Whole-frame tempos:** at 30 fps, use 60/72/75/90/100/120/150/180 BPM. The Oct-13 videos are cut on the 120 BPM grid, so calm music uses half-time feel there.

## 5. Efficiency (measured)

| Item | Prototype | SongMap v0.2 |
|---|---|---|
| Engine | 14.8k chars of Python regenerated or patched per session | Written once; not part of per-song output |
| One loop-style song | ≈1.7k chars of Python | **0.7–1.0k chars** compact (`examples/*.sm`), 2× smaller than v0.1 YAML |
| One through-composed score | n/a | ≈2–4k chars (the size goes into musical decisions: cues, transforms, dynamics) |
| LLM context needed | The whole synth script | `songmap describe --compact`, about 400 tokens |
| Video timing | Hand-copied frame numbers in TSX | Generated `cues.json` |
| A revision | Edit synth + every downstream frame | Replace one section line |
| Render time | ≈10 s per track | Sketch: ~4× real time single-threaded; target < 20 s for 2 min |

## 6. QA without ears

- **Measured on every render:**
  - Integrated LUFS (BS.1770-4, validated against EBU 3341 case 1), true peak (4× oversampled), clipped samples.
  - Per-section loudness, before and after the master (contrast preservation).
  - Per-section band balance (low <250 Hz, mid, high >4 kHz).
  - **Per-stem loudness.** This caught a kick 10 dB too hot and a melody 10 dB too low in the sketch demo.
  - Silence, and `hits_audible` (onset energy at each event vs. the surrounding 2 beats).
  - Spectrogram PNG with section lines.
- **`qa:` rules** in the song (contrast pairs, LUFS range, max low ratio, never-silent sections) make `render` fail loudly.
- **`songmap why <section>`** summarizes what was generated (notes per part per bar, velocity ranges, chords), so an LLM can reason about the arrangement it can't hear.

## 7. Decisions log

| Date | Decision |
|---|---|
| 2026-10-19 | Song map as a YAML file; one engine; cues for video (v0.1) |
| 2026-10-20 | Native synthesis is primary; the FluidSynth path is dropped; sampler and plugins optional |
| 2026-10-20 | Performance is a separate layer between notes and instruments |
| 2026-10-20 | Durations are sticky; dynamics use the `=` prefix (`=f` vs the note `f`) |
| 2026-10-20 | The compact `.sm` form is the LLM default; YAML for GUI saves and diffs; lossless conversion |
| 2026-10-20 | Styles are data (patterns/*.yaml); instruments declare a `PARAMS` schema that drives the GUI, validation and LLM context |
| 2026-10-20 | 48 kHz internal rate (video delivery); numba for per-sample kernels; stable seeds via crc32 |
| 2026-10-20 | GUI = FastAPI + React/TS front-end over the same engine (no JS DSP) |
| 2026-10-20 | (P1) Chord register: a chord's root sits nearest the key's home tonic, and the tonic sits nearest middle C. This reproduces every synth_v0 voicing |
| 2026-10-20 | (P1) The default progression and motif blocks loop from beat 0, not from each section, and a chord that crosses a section boundary is not re-struck. This is what synth_v0 did |
| 2026-10-20 | (P1) v0.1 songs migrate to `master: legacy` (synth_v0's normalize + tanh), because that master is what rendered them |
| 2026-10-20 | (P1) The default ensemble is the synth_v0 port. Its levels are calibrated against synth_v0's own voices and stems (`tools/calibrate_v0.py`, `port_check.py --stems`) |
| 2026-10-21 | The SongMap language *is* the `.sm` grammar (`.sml` is an alias): section lines are its flat subset, and definitions, `with`, `form:`, loops, conditions, named events and functions are opt-in. It compiles to the v0.2 raw mapping, so YAML and `.sm` share one validator and one engine. *One format to learn, and flat files stay line-addressable* |
| 2026-10-21 | (Language) The n-th instance of a section is `<name>_n`, counted only among that section's instances; `as` pins a name. *Inserting other sections never renames an instance, so cues and seeds stay put* |
| 2026-10-21 | (Language) `every N bars` counts the instance's bars; `every N song bars`, and `every` at the top of the form, count song bars. *Phrases are section-relative, and song-wide rules say so explicitly* |
| 2026-10-21 | (Language) `+` concatenates strings, `&` overlays them, and `+` layers beats. *Python for text, "play both" for drums* |
| 2026-10-21 | (Language) Values, not references: `b = a with {...}` copies `a` at that line. *A line's meaning depends only on the lines above it, like YAML `like:`* |
| 2026-10-21 | (Language) Per-bar edits on any part compile to part variants (`vary:`, a per-bar mask in expand), not sub-sections. *Sections, cue names, seeds and dynamic arcs stay whole, and songs without variants are untouched* |
| 2026-10-21 | (Language) Events are values: `lift = !impact !riser:2`, placed with `!lift`, relative to where they are placed. *Hit-and-riser groups are the most repeated thing in the Oct-13 scores* |
| 2026-10-21 | (Language) Layering step strings of different lengths uses their common grid. *The drum voices ignore note length, so only the written step length changes, and one string per lane stays printable* |

## 8. Open questions

- **Sample sources:** which (if any) sample libraries to ship for exposed solos, and their licensing for company-internal videos.
- **Bowed and brass synthesis:** how far physical models (waveguide or friction) go before sampling wins. Prototype both on a cello line in Phase 5 and A/B them blind.
- **Picture edits:** whether to nudge the visuals to the grid (receipt stamps, BUILD/CHARGE/TEST) or keep the off-grid cadences as syncopation.
- **Tempo changes against video:** `rit` at end cards, given that cues need exact frames.
- **A Claude Code skill** (`songmap-compose`) bundling the authoring loop, the catalog and the rules of thumb, so any session can score a video.
