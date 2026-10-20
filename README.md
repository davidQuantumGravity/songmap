# SongMap: compact, expressive, LLM-friendly soundtracks for videos

**Status (2026-10-20):**
- Design v0.2 is complete.
- **Tested reference code** for the hard parts lives in `reference/sketch_v1/`: band-limited DSP, 14 velocity-sensitive instruments, the note and dynamics language, the performance layer, mixing, BS.1770 loudness and QA. It has 43 tests and a demo render.
- The `songmap` package itself is next ([ROADMAP.md](ROADMAP.md) P0–P1).

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
| [docs/PERFORMANCE.md](docs/PERFORMANCE.md) | How annotations become played notes: velocity scale, groove templates, humanize tables, voicing, MIDI mapping |
| [docs/INSTRUMENTS.md](docs/INSTRUMENTS.md) | The instrument contract, the full suite catalog, realism recipes, sampler and plugin backends, presets, YAML patch instruments |
| [docs/ENGINE.md](docs/ENGINE.md) | Package layout, data flow, styles-as-data, timing math, contrast-preserving mastering, test strategy, what code exists now |
| [docs/GUI.md](docs/GUI.md) | SongMap Studio: auto-generated knobs, audition, presets, steps and feel, video-synced song view, patch editor, API, milestones |
| [docs/SCENE_TIMELINES.md](docs/SCENE_TIMELINES.md) | Frame-by-frame spotting of the three Oct-13 videos |
| [docs/RESCORE_PLAN.md](docs/RESCORE_PLAN.md) | Through-composed re-scores of those videos: shared motifs, per-scene treatment, production steps |

## Layout

```
Music/
├── README.md · ROADMAP.md
├── docs/                         ← the documents above
├── examples/
│   ├── week_oct13_swarm.sm       ← faithful v0.2 ports of the original tracks (compact form)
│   ├── week_oct13_bench.sm
│   ├── deepdive_kapton.sm
│   └── v0.1_yaml/                ← the original v0.1 YAML ports
└── reference/
    ├── synth_v0.py               ← the original prototype (made the Oct-13 tracks)
    └── sketch_v1/                ← tested reference code for the new engine
        ├── dsp.py  instruments.py  notation.py  perform.py  mix.py
        ├── demo.py               ← end-to-end render + instrument gallery
        └── test_sketch.py
```

**Source assets** for the Oct-13 videos (rendered MP4s, MP3s, and the Remotion + synth source tarball) are in `C:\Users\chest\Documents\Physics\APEC\Monday Meetings\weekly_videos\`. ROADMAP P0 copies them into `assets/`.

## Try the sketch

```bash
cd reference/sketch_v1
pip install numpy scipy numba pytest
python -m pytest -q          # 43 tests
python demo.py               # out/demo.wav (8 bars: drums, bass, pad, guitar, piano) + out/gallery.wav
```

`out/gallery.wav` plays every instrument at p, mf and ff, so you can hear velocity change the timbre.

**Running the original prototype:**

```bash
NBARS=74 python reference/synth_v0.py A
```

Use `$env:NBARS=74; python …` in PowerShell. The script's output path is hard-coded; P1 replaces it entirely.
