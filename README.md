# SongMap: compact, expressive, LLM-friendly soundtracks for videos

**Status (2026-10-20):**
- Design v0.2 is complete.
- **P0 and P1 are done.** The `songmap` package parses YAML song maps (v0.2, and v0.1 with migration), expands them against the harmony timeline with styles-as-data, renders WAV, stems and `cues.json`, and has the `check`, `render` and `migrate` commands.
- The three Oct-13 tracks are ported in `examples/v0.2_yaml/`:
  - every note matches the synth_v0 original;
  - section boundaries are frame-exact against the videos;
  - per-section loudness correlates 0.999 with the original audio.
- 114 tests pass, including the 43 moved from the sketch and golden event-list hashes. Next: P2 (QA) and P3 (performance layer).

## The idea

1. A **fixed engine** synthesizes instruments from scratch (drums, bass, synths, modal piano, Karplus-Strong guitar, FM e-piano, organ, with more planned), *performs* the notes with human dynamics and timing, mixes and masters. It is written once and improves over time.
2. Each song is a **short text file**: about 15–40 lines in the compact `.sm` form. It covers tempo, key, chords, themes, orchestration, dynamics, articulation, groove, and the video's cue points.
3. The **same file drives the video timing:** sections and hits export as a frame-accurate `cues.json`.
4. Every render emits **QA numbers**, so an LLM can check its own work without ears. A **GUI** (Studio) lets a person tune every instrument with knobs.

```
song.sm ─► parse ─► arrange (styles, motifs, harmony) ─► perform (dynamics, groove, humanize, articulation)
                                                              │
                     instruments (velocity → timbre, round-robin, physical models, sampler, plugins)
                                                              │
                     mix (buses, sidechain, sends) ─► master (contrast-preserving, −14 LUFS, −1 dBTP)
                                                              │
               song.wav · stems/ · song.mid · cues.json · qa.json/png  ──►  Remotion video / ffmpeg mux
```

## A taste of the format

```
song "The Swarm" 120 4/4 Em fps=30 mood=techno seed=7 video=WeekSwarm:3690
motif m1 deg oct=5 "=mf 0 -3 0 2 | 1/2 0"
cue big=f3005
goals     10 | drums:full+fill bass:8ths(art=staccato) arp:up pad:warm dyn=mf<f
who        2 | pad:dark -drums                                  | !stop:2b@+1:3
cumulative 3 | like=goals lead:m1:aug dyn=ff                    | !riser:2@cue:big !impact@cue:big(size=xl)
```

Melodies use LilyPond-style sticky durations plus marks:
- `^` accent, `!` marcato, `'` staccato, `_` tenuto, `~` slur or glide
- `(e8)` ghost note, `{d}e4` grace note, `@96` explicit velocity
- dynamics `=p` … `=ff`, hairpins `<` and `>`

Drums can be step strings: `"X..x..x.|X.ox.x.r"`.

## Documents

| Doc | What it covers |
|---|---|
| [ROADMAP.md](ROADMAP.md) | **The build plan.** Phases with tasks, files, how-to and done-when |
| [docs/DESIGN.md](docs/DESIGN.md) | Architecture, renderer strategy, efficiency measurements, decisions log |
| [docs/SONGMAP_SPEC.md](docs/SONGMAP_SPEC.md) | The format v0.2 (YAML form): instruments, harmony, note language, transforms, groove, sections, events, positions and cues, mix, master, QA |
| [docs/COMPACT_FORMAT.md](docs/COMPACT_FORMAT.md) | The `.sm` LLM encoding: grammar, measured savings, the LLM authoring loop, scoring rules of thumb |
| [docs/LANGUAGE.md](docs/LANGUAGE.md) | The SongMap language behind `.sm`: named sections and beats, `with`, the form block, loops, per-bar conditions, named events, functions, decisions |
| [docs/PERFORMANCE.md](docs/PERFORMANCE.md) | How annotations become played notes: velocity scale, groove templates, humanize tables, voicing, MIDI mapping |
| [docs/INSTRUMENTS.md](docs/INSTRUMENTS.md) | The instrument contract, the full suite catalog, realism recipes, sampler and plugin backends, presets, YAML patch instruments |
| [docs/ENGINE.md](docs/ENGINE.md) | Package layout, data flow, styles-as-data, timing math, contrast-preserving mastering, test strategy, what code exists now |
| [docs/GUI.md](docs/GUI.md) | SongMap Studio: auto-generated knobs, audition, presets, steps and feel, video-synced song view, patch editor, API, milestones |
| [docs/SCENE_TIMELINES.md](docs/SCENE_TIMELINES.md) | Frame-by-frame spotting of the three Oct-13 videos |
| [docs/RESCORE_PLAN.md](docs/RESCORE_PLAN.md) | Through-composed re-scores of those videos: shared motifs, per-scene treatment, production steps |

## Layout

```
Music/
├── README.md · ROADMAP.md · pyproject.toml
├── docs/                         ← the documents above
├── songmap/                      ← the engine (layout in docs/ENGINE.md §2)
│   ├── cli.py  model.py  render.py
│   ├── parse/                    ← lang (the .sm language), yaml_form (v0.2 + v0.1 migration), notes, steps, positions
│   ├── theory/                   ← keys, harmony (progressions, harmony timeline), voicing
│   ├── arrange/                  ← timeline, styles + patterns/*.yaml, expand, events, ensemble + defaults.yaml
│   ├── instruments/              ← contract, registry, presets loader, dsp/ and 16 instruments
│   ├── presets/                  ← <instrument>/<name>.yaml (the synth_v0 voices: kick/v0, pad/warm, ...)
│   ├── perform/  mix/  export/   ← performance layer (wired in P3), mixing/mastering, wav/cues/qa
├── tests/                        ← pytest; golden/ holds event-list hashes of every example
├── tools/                        ← port_check, v0_oracle (synth_v0's own notes), calibrate_v0, update_golden, demo
├── examples/
│   ├── v0.2_yaml/                ← faithful v0.2 ports of the three Oct-13 tracks (render these)
│   ├── v0.1_yaml/                ← the original v0.1 YAML ports (still load, with a deprecation warning)
│   ├── *.sm                      ← the same ports in compact form (same notes as the YAML ports)
│   └── lang/                     ← The Swarm written with definitions and a form block (.sml)
├── assets/oct13/                 ← recovered Oct-13 sources: Remotion project, synth.py, original audio (P0)
└── reference/
    └── synth_v0.py               ← the original prototype (made the Oct-13 tracks)
```

**Source assets** for the Oct-13 videos (rendered MP4s, MP3s, and the Remotion + synth source tarball) are in `C:\Users\chest\Documents\Physics\APEC\Monday Meetings\weekly_videos\`. P0 copied them into `assets/oct13/`. The MP3s are not committed; the extracted WAVs are git-ignored.

## Try it

```bash
python -m venv .venv && .venv/Scripts/pip install -e .[dev,gui]
songmap check  examples/week_oct13_swarm.sm                       # the compact form (same notes as the YAML)
songmap check  examples/v0.2_yaml/week_oct13_swarm.songmap.yaml
songmap render examples/v0.2_yaml/week_oct13_swarm.songmap.yaml -o build/swarm   # ~4 s
songmap migrate examples/v0.1_yaml/week_oct13_swarm.songmap.yaml                 # v0.1 -> v0.2 on stdout
python -m pytest -q                       # 200 tests (-m "not port" skips the 30 s render-vs-original checks)
python tools/port_check.py --stems        # notes vs synth_v0, loudness vs the original audio, per-part levels
python tools/demo.py                      # out/demo.wav + out/gallery.wav (every instrument at p, mf, ff)
```

**Running the original prototype:**

```bash
NBARS=74 python reference/synth_v0.py A
```

Use `$env:NBARS=74; python …` in PowerShell. The script's output path is hard-coded. `tools/v0_oracle.py` runs its `build()` with the instruments stubbed out to list every note it plays.
