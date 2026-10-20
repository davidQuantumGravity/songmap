# SongMap Studio: GUI plan

A local app for **designing sounds with knobs**, auditioning them by velocity and pitch, tuning groove and feel, building arbitrary instruments, and scoring against the actual video. It is a front-end to the same engine the CLI uses: **no DSP is duplicated in JavaScript**.

## 1. Goals

1. **Every instrument gets knobs automatically.** That covers the kick, snare, clap, hats, bass, pad, pluck, lead, keys, strings, patch instruments and plugins. Knobs are generated from the instrument's `PARAMS` schema (`Instrument.schema()` is already JSON-ready and tested). Adding an instrument in Python makes it appear in the GUI with no GUI code.
2. **Instant audition.** Changing a knob re-renders and replays the sound within about 50 ms for single hits. Loops update at the next loop boundary.
3. **Presets** (`presets/<instrument>/<name>.yaml`), with A/B compare, diff, randomize and morph.
4. **Arbitrary instruments** through a patch editor that writes the YAML module graphs of [INSTRUMENTS.md §7](INSTRUMENTS.md).
5. **Feel and groove tuning** for the performance layer ([PERFORMANCE.md](PERFORMANCE.md)).
6. **Song view synced to the video:** sections, cues and events over the rendered MP4, with QA readouts.
7. **Everything round-trips to text.** "Copy as songmap" puts the current settings on the clipboard as a compact `inst`/`kit`/`feel` line or YAML, so the LLM and the GUI edit the same files.

## 2. Architecture

```
 browser (Vite + React + TypeScript)           Python (FastAPI + uvicorn, already installed)
 ┌───────────────────────────────┐   HTTP     ┌─────────────────────────────────────────┐
 │ Rack · Editor · Keyboard · Pads│◄────────► │ /api/instruments  (schemas)             │
 │ Presets · Steps · Feel · Song  │  JSON     │ /api/presets/...  (YAML files on disk)  │
 │ Patch editor (node graph)      │           │ /api/render/note|pattern|song           │
 │ WebAudio playback, Web MIDI in │◄─ WS ───► │ /ws  live param changes → PCM back      │
 └───────────────────────────────┘ float32   │   songmap engine (instruments, perform, │
                                    PCM        │   mix) — the same code as the CLI      │
                                               └─────────────────────────────────────────┘
```

**Why this stack:**
- Python stays the single source of DSP truth.
- React matches the Remotion video stack.
- A browser UI runs in the desktop app's browser pane or any browser.
- FastAPI, uvicorn and node/npm are already on this machine.

**Audio path:**
- **One-shot:** the server renders a note into a float32 stereo buffer and sends it as a binary WebSocket frame with a JSON header. The browser builds an `AudioBuffer` and plays it.
- **Renders are cached** by `hash(instrument, params, pitch, vel, gate, seed)`, so dragging a knob back to a previous value is instant.
- **Rate limiting:** while a knob is dragged, requests are coalesced to at most one in flight plus the latest pending one (about 20–30 renders per second).
- **Loop audition** (a 1–4 bar pattern or section): the server renders the loop; the browser plays it with `loop=true`. On a parameter change the server re-renders in a background task and the browser swaps buffers at the next loop start with a 5 ms crossfade.
- **Budget:** the sketch renders 23 s of a full 6-part mix in about 5.7 s on this machine, including first-run numba compilation. A single drum hit or 1 s note takes a few ms. Keep any instrument above 20 ms per second of audio off the live path (render it in the background).
- **MIDI keyboard:** the Web MIDI API sends note-ons to `/ws`, the server renders the note and returns it. Latency is about 20–60 ms: fine for auditioning, not for performing. Real-time play is a non-goal for v1.

## 3. Screens

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ SongMap Studio   [song: week_oct13_swarm.sm ▾]  [Render ▶]  LUFS -14.1  TP -1.0  ✓QA  │
├───────────────┬──────────────────────────────────────────────────────────────────────┤
│ RACK          │ KICK · preset kick/punchy  [A|B] [Save] [Save as] [Rand ±10%] [Init]  │
│ ▸ drums       │ ┌─ pitch ───────────┐ ┌─ amp ──────┐ ┌─ click ────────┐ ┌─ tone ──┐  │
│   kick  ●     │ │ (tune) (sweep)    │ │ (decay)    │ │ (click)(tone)  │ │ (drive) │  │
│   snare       │ │  50Hz   34st      │ │  0.38s     │ │  0.55  4.2k    │ │  2.2x   │  │
│   clap        │ │ (sweep_time)      │ │ (sub)      │ └────────────────┘ └─────────┘  │
│   hat / ohat  │ └───────────────────┘ └────────────┘ ┌─ velocity ─────┐ ┌─ var ───┐  │
│ ▸ bass        │  [waveform + spectrum of last hit]   │(vel_sweep)(vel_│ │ (rr)    │  │
│ ▸ pad         │  [pitch-env / amp-env curves drawn]  │ click)(curve)  │ └─────────┘  │
│ ▸ keys        │                                      └────────────────┘              │
│ + instrument  │ VELOCITY PADS  ░▒▓█ (click height = velocity)   [p] [mf] [ff] [sweep] │
│ + patch       │ KEYBOARD  |█|█||█|█|█||█|█||   oct [-][+]   MIDI in: ● Arturia        │
├───────────────┴──────────────────────────────────────────────────────────────────────┤
│ STEPS  kick  X . . . . . x . . . x . . . . .  │ swing 0.56/16  tpl mpc  hum 4/3/.04  [▶] │
│        snare . . . . X . . o . . . . X . o o  │ feel snare +6ms           [Copy songmap] │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Rack
The parts of the loaded song, or a scratch rack. Each entry shows its instrument, preset, mute/solo, and a level meter. **+ instrument** picks from the registry, including samplers and plugins. **+ patch** opens the patch editor.

### 3.2 Instrument editor (auto-generated)
- One **panel per `Param.group`** (pitch, amp, filter, tone, velocity, variation…), knobs in schema order.
- **Knob behaviour:**
  - Vertical drag; Shift for fine adjustment; mouse wheel; double-click resets to the default; Ctrl/Cmd-click types a value.
  - `log` params use exponential mapping, and units are formatted (Hz/kHz, ms/s, st, oct, dB).
  - The tooltip shows `Param.doc` and the range.
  - A small **velocity ring** shows the param's `vel_*` modulation amount.
  - A lock icon excludes the param from randomize.
- **Visualizers:**
  - Waveform and spectrum of the last render.
  - Envelope curves drawn from params (ADSR, pitch sweep, filter env), computed server-side by rendering control curves through the same functions.
- **Velocity strip:** auditions p / mf / ff, and **sweep** plays 8 hits from vel 0.2 to 1.0. That is the fastest way to hear velocity-to-timbre mapping.

### 3.3 Presets
- Browser by instrument and tag, with a text search over descriptions.
- **A/B:** two slots per instrument, toggled instantly. **Diff** lists the params that differ.
- **Morph:** a slider interpolating A→B (log-aware).
- **Randomize ±N%:** respects locks and stays within ranges. **Mutate** applies small random steps, for exploring nearby sounds.
- Saving writes YAML with a description, tags and a `base:` reference, ready to commit to the repo.

### 3.4 Steps and Feel
- **Step grid** per kit piece. Clicking cycles `. o - x X`; right-click sets `f` (flam) or `r` (ratchet). Per-bar resolution is 16, 12 or 24, and patterns can be up to 4 bars. It writes step strings.
- **Feel controls:** swing, grid, template, groove amount, humanize (time, drift, vel), per-part offset ms, metric, high_loud, arch, gate. A **played-offset view** draws each note's actual time and velocity against the grid.
- **Loop playback** of the pattern with the current kit and feel.

### 3.5 Song view (scoring against the picture)
- Load a `.sm`/`.yaml` song and its video (the Remotion-rendered MP4, or a Remotion preview URL).
- **Timeline:** sections as colored blocks, cues as frame-exact markers, events as glyphs (impact, riser span, hits). A frame ruler and a bar:beat ruler sit above.
- **Video player synced to the audio:** scrubbing either one moves both. Selecting an event jumps to its frame. Markers can be dragged; on release they snap to the 16th grid and update the song file.
- **Mixer strip** per part: gain, pan, sends, sidechain depth, mute/solo. Changes write the `mix` line.
- **QA panel:** LUFS, true peak, section contrast table, band balance per section, spectrogram with section lines. Failing `qa:` rules turn red.
- **Render ▶** renders the full song (background, progress over WS) and loads the new audio when done.

### 3.6 Patch editor (arbitrary instruments)
- **v1 (form-based):** a list of modules, each row with a type dropdown and its params as knobs, plus an inputs selector. Expression fields accept `vel`, `pitch`, `t` and macros, validated live.
- **v2 (node graph):** drag-and-drop modules and wires, using litegraph.js or Rete.js. Each node shows its knobs and a mini scope, and validation rejects feedback between modules.
- A **macro builder** lets you pick params and ranges for each macro knob. Macros appear as the instrument's knobs everywhere else.
- **Templates:** "subtractive mono", "FM bell", "KS pluck", "modal mallet", "formant voice", "noise percussion".
- **Export as Python:** generates an `Instrument` subclass skeleton from the patch, for promoting a patch into a first-class, faster engine instrument.

### 3.7 Copy as songmap
Every panel has **Copy as songmap**:
- `inst bass=bass/acid_sub(cutoff=640,res=2.1)`
- `kit kick=kick/punchy(decay=.35)`
- `feel snare offset=6`
- a step-string line
- or the YAML equivalent

This is how a sound tuned by ear gets back into an LLM-authored song.

## 4. API

| Method | Path | Body / response |
|---|---|---|
| GET | `/api/instruments` | `[schema]`: name, family, mono, params |
| GET | `/api/presets?instrument=kick` | List with descriptions and tags |
| GET/PUT/DELETE | `/api/presets/{inst}/{name}` | Preset YAML ↔ JSON (DELETE moves it to `presets/.trash/`) |
| POST | `/api/render/note` | `{instrument, params, pitch, vel, gate, seed}` → binary PCM |
| POST | `/api/render/pattern` | `{kit/parts, steps/motifs, feel, bars, tempo}` → binary PCM |
| POST | `/api/render/song` | `{path}` → job id; progress and result over WS |
| GET | `/api/song?path=` | Parsed song tree + `cues.json` + last `qa.json` |
| PUT | `/api/song` | Apply an edit (section line, cue, mix) and write the file |
| POST | `/api/patch/validate` | Patch YAML → errors or the compiled schema |
| WS | `/ws` | `{type: param, inst, name, value}` → re-render; `{type: midi, note, vel}` → render note; server pushes `audio`, `progress`, `qa` |

## 5. File layout

```
songmap/gui/
  server.py            # FastAPI app, routes, WS, render cache, background jobs
  cache.py             # LRU of rendered buffers keyed by stable hash
  web/                 # Vite + React + TS app
    src/components/Knob.tsx, KnobPanel.tsx, VelocityPads.tsx, Keyboard.tsx,
                   StepGrid.tsx, Scope.tsx, Spectrum.tsx, EnvelopeView.tsx,
                   PresetBar.tsx, Timeline.tsx, VideoSync.tsx, Mixer.tsx, QAPanel.tsx,
                   PatchEditor.tsx
    src/audio.ts       # WebAudio playback, loop swap with crossfade, Web MIDI
    src/api.ts
  static/              # built web app, served by FastAPI
```

Launch with `songmap gui [song.sm]`, which starts uvicorn on 127.0.0.1:8765 and opens the browser. Add a `.claude/launch.json` entry so Claude Code can open it in the browser pane for verification.

## 6. Milestones

| Milestone | Scope | Done when |
|---|---|---|
| **G1 — Knobs & audition** | Server with `/api/instruments` and `/api/render/note`; Knob component; auto-generated editor; velocity pads; keyboard; waveform view; render cache | Every registered instrument is editable; a knob change is heard in ≤ 100 ms for drums; the schema of a newly added instrument appears without GUI changes |
| **G2 — Presets** | Save/load/A-B/diff/randomize/morph; tags; Copy as songmap | Presets round-trip YAML↔GUI byte-stable; a song referencing `kick/punchy` renders the same sound as the GUI |
| **G3 — Steps & Feel** | Step grid, loop playback with background re-render and swap, feel panel, played-offset view | 4-bar loop edits swap at the loop boundary without clicks; the step strings written match the spec grammar |
| **G4 — Song & video** | Song view, timeline, video sync, mixer, QA panel, full render jobs | Scrubbing the video and the audio together stays in sync within 1 frame; dragging a cue updates the `.sm` file |
| **G5 — Patch editor** | Form editor, then node graph; macros; templates; export-as-Python | A user builds an FM bell from a template, saves it, and uses it in a song without writing Python |
| **G6 — Plugins & samplers** | Plugin parameter panels (DawDreamer), sampler zone viewer | A Surge XT preset and an SFZ piano are playable and savable like native instruments |

**Testing:**
- API tests run under pytest with FastAPI's TestClient: schema endpoint, deterministic render hashes, preset round-trip.
- UI checks run in the desktop app's browser pane: knob drag, A/B, loop swap, video sync.
- The audio path is exercised by asserting rendered PCM equals the engine's offline render for the same inputs.
