# Engine: package layout, data flow, and the code that exists today

## 1. Status of the code

The sketch (`reference/sketch_v1/`) was moved into the package in P1, definition by definition, and its 43 tests into `tests/`. `tools/demo.py` still renders the same `demo.wav`, bit for bit.

| Piece | Where now | Tested |
|---|---|---|
| Band-limited oscillators, SVF with per-sample cutoff, envelopes, EQ, drive, Karplus-Strong, modal bank, ping-pong delay | `songmap/instruments/dsp/` (core, osc, env, filters, physical, fx) | ✅ aliasing, KS pitch at 4 notes, SVF sweep |
| `Param`/`Note`/`Instrument` contract, registry, `describe()`, presets, 16 instruments (+ `zap`, `tick` from synth_v0) | `songmap/instruments/` (base, presets, drums/ bass/ synth/ strings/ keys/ fx/) | ✅ every instrument renders; velocity→timbre for 9; schema is JSON; bad param name → suggestion |
| Note language (letter, deg and chord-relative `rel:` modes), step strings, keys, chord symbols | `songmap/parse/notes.py`, `steps.py`, `songmap/theory/keys.py`, `harmony.py` | ✅ sticky durations, marks, ghosts, hairpins, deg and rel modes, bar-check error text |
| Positions, tempo map, progressions + harmony timeline | `songmap/parse/positions.py`, `songmap/arrange/timeline.py`, `songmap/theory/harmony.py` | ✅ all position forms, frame snapping, synth_v0 chord registers |
| YAML parser with v0.1 migration; styles as data; expansion; events; ensemble defaults | `songmap/parse/yaml_form.py`, `songmap/arrange/` | ✅ inheritance, errors with line + suggestion, every style, golden hashes |
| Performance pipeline, groove templates, voice leading | `songmap/perform/`, `songmap/theory/voicing.py` | ✅ seeded, crescendo shaping, swing, smooth C→F (wired into render in P3) |
| Buses, reverb IR, compressor, sidechain, limiter, BS.1770 LUFS, true peak, master + synth_v0's legacy master, QA | `songmap/mix/`, `songmap/export/qa.py` | ✅ EBU 3341 case 1 (−23.0 LUFS), limiter ceiling, master hits −14 |
| Render, 24-bit WAV, stems, `cues.json` (+ validator), CLI | `songmap/render.py`, `songmap/export/`, `songmap/cli.py` | ✅ deterministic renders, cues validation, CLI |
| Original prototype | [reference/synth_v0.py](../reference/synth_v0.py) | the port check runs it as an oracle (`tools/v0_oracle.py`) |

Run `python -m pytest -q` (114 tests) and `python tools/port_check.py --stems`.

**Lessons from building the sketch** (now design rules):
- Seeds must come from a **stable hash** (`zlib.crc32` of names). Python's `hash()` is randomized per process, and an early demo was not reproducible because of it.
- The mastering chain **flattened the section crescendo**: 1.6 dB of build-to-peak contrast before the master, 0.4 dB after (glue compressor plus re-normalization). `master()` needs a `preserve_contrast` mode (§6).
- A sample-peak limiter lets inter-sample peaks through (−0.62 dBTP against a −1 target). `master()` now trims, and Phase 4 adds an oversampled true-peak limiter.
- The first balance pass had the kick 10 dB too hot and the melody 10 dB too low. **QA caught both**, without anyone listening. Per-stem loudness belongs in `qa.json`.
- The motif bar-checker caught a wrong example in the test suite immediately. Keep the checks strict.

## 2. Package layout (target)

```
songmap/
  __init__.py
  cli.py                  # songmap check | render | describe | fmt | migrate | why | gui | cues-from-video
  model.py                # dataclasses: Song, Section, PartSpec, Motif, EventSpec, Cue, MixSpec, QARules
  parse/
    yaml_form.py          # YAML -> Song (schema-validated, v0.1 migration)
    compact.py            # .sm -> Song (line grammar, COMPACT_FORMAT.md)
    notes.py              # motif / rel / deg language (from sketch notation.py)
    steps.py              # drum step strings
    positions.py          # "agents+8:3", "f3960", "cue:x" -> absolute beats
    errors.py             # SongError(file, line, section, message, suggestion)
    fmt.py                # Song -> YAML / compact (round-trip)
  theory/
    harmony.py            # chord symbols, progressions, harmony timeline (chord at beat)
    keys.py               # modes, degree mapping, re-harmonize transform
    voicing.py            # voicings(), voice_lead(), drop2/shell/quartal/spread, top-voice harmonization
    transforms.py         # t+n, inv, rev, aug, dim, frag, dyn=, to=
  arrange/
    timeline.py           # tempo map: beats <-> seconds <-> frames (handles rit/accel)
    patterns/             # DATA: styles as YAML (see §4)
    styles.py             # load + expand styles against the harmony timeline
    expand.py             # Song -> {part: [Ev...]} with section context
    events.py             # impact/riser/hit/stop/drop/... -> fx notes + mute masks
  perform/
    pipeline.py           # perform() (from sketch)
    grooves.py            # templates + user grooves/*.yaml
    rules.py              # KTH-style rules (duration contrast, final rit, ...)
  instruments/
    base.py               # Param, Note, Instrument, registry, describe()
    dsp/                  # osc, filters, env, noise, physical models, fx kernels (numba)
    drums/ bass/ keys/ mallets/ strings/ brass/ winds/ voice/ synth/ fx/
    sampler.py            # SFZ subset
    plugin.py             # DawDreamer host (optional extra)
    patch.py              # YAML module-graph instruments + safe expression evaluator
  presets/                # <instrument>/<name>.yaml
  mix/
    bus.py                # buses, sends, returns, sidechain routing, mute masks
    fx.py                 # reverb, delay, chorus, eq, compressor, saturation
    master.py             # glue, preserve_contrast, true-peak limiter, loudness
  export/
    wav.py                # 24-bit WAV, stems
    midi.py               # velocities, CC11, pitch-bend glides, drum map (mido)
    cues.py               # cues.json
    qa.py                 # qa.json + qa.png (matplotlib spectrogram + section lines)
  render.py               # orchestrates: parse -> expand -> perform -> render notes -> mix -> master -> export
  gui/                    # see GUI.md
tests/
  test_notes.py test_steps.py test_positions.py test_compact_roundtrip.py
  test_instruments.py (renders, velocity timbre, pitch, clicks, speed)
  test_perform.py test_voicing.py test_mix.py test_loudness.py
  golden/                 # event-list hashes + metric snapshots for examples/*.sm
pyproject.toml            # deps: numpy scipy numba pyyaml mido matplotlib; extras: gui=[fastapi uvicorn], plugin=[dawdreamer], sampler=[soundfile]
```

## 3. Data flow

```
.sm / .yaml
   │ parse (compact.py | yaml_form.py)            errors carry file:line + suggestion
   ▼
Song (model.py)
   │ resolve: defaults, mood preset, like=/add/drop inheritance, presets, cues → positions
   ▼
Timeline (tempo map, harmony timeline, section spans in beats/seconds/frames)
   │ expand: for each section × part → written Ev list
   │   style (patterns/*.yaml, chord-relative) | motif list (+transforms) | inline notes | steps
   │ events → fx notes, mute masks (stop/drop), automation breakpoints
   ▼
{part: [Ev]}  ──perform()──►  {part: [Played(time, Note)]}      (seeded per song/section/part)
   │ render notes: per part, voice allocation (mono glide, choke groups), cache identical notes
   │   parallel across parts (ProcessPoolExecutor; numba kernels are nogil)
   ▼
stems (n×2 float64 per part) → mix (gain, pan, sidechain from kick Played times, sends→returns)
   → master (glue, contrast-preserving gain, true-peak limit, LUFS target)
   ▼
song.wav · stems/ · song.mid · cues.json · qa.json/png · render.log
```

## 4. Styles are data (the pattern library)

Adding a groove or bass figure means adding YAML, not Python. Styles use the step grammar and the chord-relative `rel:` note language.

```yaml
# songmap/arrange/patterns/drums/full.yaml
style: full
role: drums
bars: 1
steps: {kick: "X.......X.......", snare: "....X.......X...", hat: "x-x-x-x-x-x-x-x-"}
mods:
  fill:   {every: 8, last_bar: {snare: "....X...xxxxXXXX"}}     # `+fill`
  hats16: {add: {hat16: "xoxoxoxoxoxoxoxo"}}                   # `+hats16`
  open:   {add: {ohat: "..x...x...x...x."}}
  ghosts: {add: {snare: ".o.....o..o....o"}}

# patterns/bass/eighths.yaml
style: eighths
role: bass
rel: "R8 R+ R R+ R R+ R R+"      # octave bounce on chord roots, like synth_v0
art: normal
gate: 0.9

# patterns/arp/up.yaml
style: up
role: arp
grid: 16
order: [0, 1, 2, 3, 2, 1, 4, 2]     # indices into the current chord voicing (wrapping up octaves)
brightness_ramp: {over: 8, cutoff: "2500>5500"}   # synth_v0's 8-bar brightening, now declarative

# patterns/pad/pulse8.yaml
style: pulse8
role: pad
rhythm: "x.x.x.x.x.x.x.x."            # retriggered chord on 8ths
voicing: {style: close, lead: smooth}
```

Styles are matched by name per role. Unknown names list the valid ones. `songmap describe` reads this folder, so the catalog is always current.

## 5. Timing math

- Beats → seconds: integrate the tempo map. For constant tempo, `t = beat * 60 / bpm`. For `rit a>b` across a section, tempo varies linearly with beat, so `t = ∫ 60/bpm(b) db` (closed form with a log).
- Seconds → frames: `round(t * fps)`. `cues.json` stores both. At 120 BPM / 30 fps, a beat is exactly 15 frames.
- `f####` positions convert to beats through the inverse map, snapped to the nearest 16th unless `snap: none`. The check warns when the snap moves a cue by more than 1 frame.
- Every position resolves to **absolute beats** internally, so sections, events and cues share one coordinate system.

## 6. Mastering that keeps the drama

1. Run the glue compressor **slowly** (attack 30 ms, release 200 ms, ratio 2, knee 8 dB) or skip it (`glue: none`).
2. Measure each section's loudness *before* mastering (`pre[s]`).
3. Normalize the whole song to target, then limit.
4. Re-measure (`post[s]`). If any adjacent-section contrast shrank by more than `preserve_contrast` dB, apply a slow section-level gain ride (±2 dB max, 1-bar ramps) that restores the pre-master contrast, then re-limit.
5. Use a true-peak limiter at 4× oversampling (`resample_poly`), with a 5 ms lookahead, ceiling −1 dBTP.

`qa.json` reports `contrast_pre` and `contrast_post` per adjacent section pair, so the LLM can see whether the master ate the dynamics.

## 7. Performance budget

| Item | Target |
|---|---|
| `songmap check` | < 200 ms for a 5-minute song |
| Render of a 2-minute song, 6–8 parts | < 20 s (sketch rate: ~4× real time, single-threaded, includes JIT warm-up) |
| Single note for the GUI | < 10 ms for drums, plucks and bass; < 50 ms for modal piano and big pads |

**Tactics:**
- numba `cache=True` (compile once per machine).
- Cache identical notes, since drum hits repeat with the same seed per round-robin slot.
- Render parts in parallel.
- Cap modal partials by Nyquist and by amplitude.
- Pre-render long reverbs with FFT convolution.

## 8. Testing strategy

- **Unit:** notation, positions, compact↔YAML round-trip, voicing, groove math, loudness against EBU 3341/3342 cases, limiter ceiling.
- **Instrument contract:** parametrized over the registry, covering finite output, velocity→timbre, pitch accuracy, click-free edges, speed.
- **Golden:**
  - For each `examples/*.sm`, hash the expanded event list (exact) and snapshot `qa.json` metrics with tolerances.
  - A refactor that changes notes fails loudly. An intentional change updates the golden files in the same commit.
- **Port check (Phase 1):** render the v0.2 ports of the three Oct-13 songs and compare against the originals:
  - Section boundaries exact to the frame.
  - Per-section loudness correlation ≥ 0.9 with the original audio, decoded via ffmpeg.
  - Sources in `weekly_videos/` (see README): `track_B_swarm.mp3` for The Swarm; the audio tracks of `Week_Oct13_Bench_Fields_Thruster_v2.mp4` and `DeepDive_Inside_the_56_Movies.mp4` for the other two. `track_A_bench.mp3` is the older 60-bar cut, not the 74-bar v2.
