# Roadmap

Each phase lists **tasks** (with the files they create), **how to do them**, and **done when**. Phases 1–4 are the critical path to re-scoring the videos. The GUI (Phase 7) can start once Phase 1's instrument contract exists. Effort is in working sessions.

```
P0 setup ─► P1 core engine ─► P2 QA ─► P3 performance ─► P4 sound & master ─┬─► R1 rescore Swarm
                 │                                                          ├─► P5 instrument suite ─► R2 Bench, R3 Deep Dive
                 └─► P7 GUI (G1–G3 can run in parallel from here)            └─► P6 compact + LLM tooling ─► P8 video helpers ─► P9 variety
```

**Status (2026-10-20):**
- Design docs are v0.2.
- **P0 and P1 are done.**
  - The sketch now lives in the `songmap/` package, and its 43 tests run from `tests/`.
  - The engine parses, expands, renders and exports the three Oct-13 ports (`examples/v0.2_yaml/`).
  - Those ports match synth_v0 note for note, with frame-exact sections and per-section loudness r = 0.999 against the original audio.
  - 114 tests pass.
- **P1 notes for later phases:**
  - The performance layer (`songmap/perform/`) is moved but not wired in yet (P3).
  - `drop`/`stop` currently remove the notes that start inside the span; P4 adds mute masks.
  - Motif transforms and the event types other than impact/riser/zaps/drop/stop are validated and exported to `cues.json`, and render from P3/P4.
  - Pitch is float MIDI end to end, and all pitch-class math goes through `songmap/theory/tuning.py` (`steps_per_octave`, 12 for now).
  - `^`/`v` prefixes are reserved for P10's sixth-step accidentals: the parsers reject them with a message that says so.

---

## P0: Project setup (≈0.5 session)

**Tasks**
1. `git init`, a `.gitignore` (`build/`, `out/`, `*.wav` except `tests/golden/*.wav`, `__pycache__/`, `.venv/`, `node_modules/`), and a first commit of the docs and sketch.
2. `pyproject.toml`:
   - Package `songmap`, Python ≥ 3.12.
   - Deps: `numpy scipy numba pyyaml mido matplotlib`.
   - Extras: `gui = [fastapi, uvicorn]`, `plugin = [dawdreamer]`, `sampler = [soundfile]`, `dev = [pytest]`.
   - Console script `songmap = songmap.cli:main`.
3. `python -m venv .venv`, then `pip install -e .[dev,gui]`.
4. Recover assets:
   - Extract `weekly_video_source.tar.gz` into `assets/oct13/` (on Windows: `tar --force-local -xzf …`).
   - Copy the two MP3s there.
   - Extract the v2 Bench and Deep Dive audio: `ffmpeg -i <mp4> -vn -c:a pcm_s16le assets/oct13/<name>.wav`.
5. `.claude/launch.json` with a `songmap-gui` entry (port 8765) for later.

**Done when:** `pytest` runs the moved sketch tests from `tests/` and passes; `songmap --help` prints.

## P1: Core engine and parser, porting synth_v0 (≈2 sessions)

**Tasks**
1. **Move the sketch into the package** (layout in [docs/ENGINE.md §2](docs/ENGINE.md)):
   - `dsp.py` → `songmap/instruments/dsp/`
   - `instruments.py` → `songmap/instruments/` (split per family)
   - `notation.py` → `songmap/parse/notes.py` + `steps.py`
   - `mix.py` → `songmap/mix/` + `songmap/export/qa.py`
   - Keep the tests green after each move.
2. **Port the remaining `synth_v0` sounds** as instruments: `zap`, `tick`, the `dark`/`warm` pad styles, the `dark`/`up` arp brightness behaviour. Make them presets (`pad/warm`, `pad/dark`, `pluck/dark`) where they are only parameter differences.
3. **`model.py`:** dataclasses for Song, Section, PartSpec, Motif, EventSpec, Cue, MixSpec, MasterSpec, QARules.
4. **`parse/yaml_form.py`:** YAML → Song, with v0.1 migration. Durations become explicit, because v0.1 meant "quarter by default" while v0.2 is sticky; `songmap migrate` writes the result.
5. **`parse/positions.py`:** `56`, `56:3.5`, `name`, `name+8:2`, `name-1`, `f3960` (snap to 16th, report the frame error), `cue:x`.
6. **`theory/harmony.py`:** progressions (`Em:2 C:1 …`, `default` + `chord_bars`), the harmony timeline `chord_at(beat)`.
7. **`arrange/patterns/*.yaml` + `styles.py`:**
   - Drums: `four_floor`, `full`, `half`, `half_kick`, and the mods `fill`, `hats16`, `open`.
   - Bass: `sub`, `eighths`.
   - Pad: `warm`, `dark`.
   - Arp: `up`, `dark`.
   - Fx: `ticks`.
   - Exactly reproduce the synth_v0 behaviour, including the bass octave bounce and the arp sequence per song.
   - Implement the `rel:` chord-relative note mode in `parse/notes.py`.
8. **`arrange/expand.py`:** sections × parts → written `Ev` lists, with lead motif lists cycled per 2-bar chord block like synth_v0. **`arrange/events.py`:** impact, riser (ends at `at`), zaps.
9. **`arrange/timeline.py`:** a constant-tempo map (beats ↔ seconds ↔ frames).
10. **`render.py`:**
    - Place notes via instruments into per-part buses.
    - Sidechain from kick times.
    - Reverb sends.
    - The v0 master: normalize + tanh, kept as `master: legacy` for the port check.
11. **Exporters:** `song.wav` (24-bit), `stems/*.wav`, `cues.json` (format in [docs/DESIGN.md §4](docs/DESIGN.md)).
12. **CLI:** `songmap check`, `songmap render`, `songmap migrate`.
13. **Port check:** convert `examples/v0.1_yaml/*.yaml` (or the `.sm` ports, if P6's compact parser lands first) and render all three.

**Done when:**
- The three Oct-13 songs render from song maps with section boundaries frame-exact against [docs/SCENE_TIMELINES.md](docs/SCENE_TIMELINES.md).
- Per-section loudness correlates ≥ 0.9 with the original audio (assets from P0).
- `cues.json` validates.
- Golden event-list hashes are committed.

## P2: QA without ears (≈1 session)

**Tasks**
1. `export/qa.py`:
   - Integrated LUFS, true peak, clipping (from the sketch).
   - Per-section and **per-stem** loudness; band balance per section.
   - `contrast_pre`/`contrast_post` per adjacent section pair.
   - `hits_audible`: onset energy in a ±30 ms window at each event vs. the median of the surrounding 2 beats, ≥ +3 dB.
   - Silence detection.
2. `qa.png`: spectrogram (matplotlib, log frequency) with section lines, event ticks, and per-section loudness bars.
3. `qa:` rules in the song: evaluate, print failing rules with numbers, exit code 2 on failure.
4. `songmap why <section>`: per-part note counts per bar, velocity min/median/max, chord list, active events.
5. Add `tests/test_loudness.py` with EBU 3341 cases 1–5 and EBU 3342 (loudness range) synthetic signals.

**Done when:** a deliberately bad song (kick +10 dB, a silent section, a break louder than the drop) fails with three precise messages, and the fixed song passes.

## P3: Performance layer (≈2 sessions)

**Tasks**
1. Move `perform.py` into `songmap/perform/`. Wire it into `expand → render` for every part, seeded via `crc32(song.seed, section, part, bar)`.
2. **Notation:**
   - Motif transforms (`t±n`, `oct±n`, `inv`, `rev`, `aug`, `dim`, `frag`, `dyn=`, `x2`, `thin=`, `canon=`, `to=`) in `theory/transforms.py`, each with a unit test.
   - Grace notes and chords inside motifs (the sketch has them; add tests).
3. **Section `dyn` shapes, part `art`/`gate`/`dyn`, groove/feel/humanize blocks, `parts_feel`** (spec §5–6).
4. **Step strings for drums** (`kick: "X..."`) as an alternative to styles; flams and ratchets; **choke groups** (closed hat cuts open hat).
5. **Mono voice allocation:** a slurred note passes `glide_from`, and the previous note's gate extends to the next onset (no gap).
6. **Voicing:** `voice_lead` (sketch) plus `drop2`, `shell`, `spread`, `quartal`, `top:` harmonization; `range_check`.
7. **Automation lanes:** `auto:` ramps and breakpoints sampled per note into `Note.params`.
8. **Events:** `hit`, `stop`, `drop`, `fill`, `swell`, `crash`, `reverse`, `cloud`.
9. **MIDI export** (`export/midi.py`, mido): velocities, post-articulation lengths, CC11 per section shape, pitch bend for glides, drums on channel 10 with the GM map.

**Done when:**
- The Swarm port renders with humanize and section dynamics, and QA shows ≥ 4 dB build contrast between `goals` and `agents` before mastering.
- The MIDI opens in a DAW (Cakewalk) with visible velocity variation.
- Swing 0.58 is audible and measurable (off-step onsets ~ +0.08 beat).

## P4: Sound quality, mix and master (≈1–2 sessions)

**Tasks**
1. **Instruments:**
   - Click detector test (HF energy in the first and last 64 samples).
   - Speed test (< 50 ms per second of audio).
   - **Release-stage handling:** every instrument honors gate → release.
2. **`mix/fx.py`:**
   - Reverb IR (sketch) with sizes `room`, `plate`, `hall`, `cathedral`.
   - Ping-pong and tempo-synced delay (`note: 8.`).
   - Chorus.
   - RBJ EQ bands.
   - Compressor (sketch).
   - Saturation.
   - `tape_stop` and `filter_sweep` bus effects.
3. **`mix/bus.py`:** routing from the `mix:` block (gain, pan, width, sends, sidechain `from:` any part, per-part EQ); returns; **mute masks** from `stop`/`drop` events with 5 ms ramps.
4. **`mix/master.py`:**
   - Glue presets.
   - **`preserve_contrast`:** measure sections pre-master, ride gain to restore contrast, as specified in [docs/ENGINE.md §6](docs/ENGINE.md).
   - True-peak limiter with 4× oversampling (the sketch only trims overs).
   - Target LUFS.
5. **Mood presets** (`presets/moods/*.yaml`): techno, cinematic, documentary, ambient. Each bundles instruments, presets, groove, mix and master.

**Done when:**
- The demo-style mix keeps ≥ 80% of its pre-master section contrast after mastering (the sketch kept 25%).
- True peak ≤ −1.0 dBTP with no trim needed.
- All instrument contract tests pass.

## R1: Re-score The Swarm (≈1 session), after P4

Follow [docs/RESCORE_PLAN.md §3 and §6](docs/RESCORE_PLAN.md).
1. Add the needed instruments first, or use the stand-ins: `bell` (modal) and `strings` (ensemble).
2. Write `examples/rescore/the_swarm.sm`.
3. Check, render, and pass QA (contrast rules, `hits_audible`).
4. Mux into an MP4 with ffmpeg.
5. Hand it to the user for listening notes, and iterate.

**Done when:** the user approves `Week_Oct13_The_Swarm_v3.mp4`.

## P5: Instrument suite (≈3–4 sessions, can be split per family)

Work through the catalog in [docs/INSTRUMENTS.md §3](docs/INSTRUMENTS.md), each item following its §8 checklist (tests + 2–4 presets + catalog row):
1. **Percussion:** `tom`, `cymbal` (ride/crash/china), `shaker`/`tambourine` (PhISEM), `rim`/`clave`/`cowbell`, `brushes`, `timpani`/`taiko`/`cinematic_drum`.
2. **Mallets and bells:** `marimba`, `vibes`, `glockenspiel`, `bell`/`tubular`, `celesta`, `kalimba` (modal bank with the listed ratios).
3. **Bass:** `bass808`, `acid` (303 accent and slide semantics), `ebass`, `upright`.
4. **Keys:** sustain pedal + sympathetic resonance for `keys`; `clav`, `harpsichord`.
5. **Bowed strings:**
   - Option A (source + body formant + bow noise + vibrato wander) and option B (friction waveguide, numba). A/B them blind on a cello line and keep the winner.
   - Then `strings` ensemble (N players, articulations: sustain, tremolo, pizz, spiccato).
6. **Brass and winds:** `brass` (the dynamics→brightness law, lip blat, scoop), `braam`, `flute`, `clarinet`.
7. **Voice:** `choir` (formant vowels, N singers).
8. **Synths:** `fm` (4-op), `wavetable`, `reese`, `string_machine`. **FX:** `downlifter`, `whoosh`, `reverse_cymbal`, `sub_drop`, `stab` (layered orchestral hit).
9. **Sampler backend** (`instruments/sampler/`, the SFZ subset in [INSTRUMENTS.md §5.1](docs/INSTRUMENTS.md)). ✅ engine, tests and per-render `LICENSES.md` (2026-10-21); still to do: evaluate VSCO-2 CE and Salamander by ear.
10. **Plugin backend** (`instruments/plugin.py`, DawDreamer): Surge XT + Dexed first.
11. **Patch instruments** (`instruments/patch.py`): the YAML module graph and safe expression evaluator of [INSTRUMENTS.md §7](docs/INSTRUMENTS.md), with templates.

**Done when:**
- Every instrument is in `describe()` with presets.
- `demo.py`'s gallery covers all of them.
- The bowed A/B decision is recorded in DESIGN §7.

## R2 / R3: Re-score Bench and Deep Dive (≈1–2 sessions each), after P5 items 1, 2, 5, 6

Same procedure as R1, using [docs/RESCORE_PLAN.md §4–5](docs/RESCORE_PLAN.md). Deliver `*_v3.mp4` and copy the final WAVs into the Remotion project's `public/`.

## P6: Compact format and LLM tooling (≈1–2 sessions)

**Tasks**
1. `parse/compact.py`: the grammar in [docs/COMPACT_FORMAT.md](docs/COMPACT_FORMAT.md), with errors carrying `file:line section:` + suggestion.
2. `parse/fmt.py`: Song → YAML and Song → compact. **Round-trip tests** on all examples (parse → print → parse is identical).
3. `songmap describe [--compact]`: the catalog from the registry, patterns folder, presets, events, transforms and note-language cheat sheet. Check it stays under ~500 tokens.
4. `songmap fmt --to yaml|compact`.
5. **Claude Code skill** `.claude/skills/songmap-compose/SKILL.md`:
   - Contents: the authoring loop (describe → spot → write → check → render → read QA → revise), the rules of thumb, and RESCORE_PLAN's shared devices.
   - Bundle `describe --compact` output as a reference file.
6. Measure: token counts of the three ports and the three re-scores; record them in DESIGN §5.

**Done when:** an LLM given only the skill and a scene timeline writes a song that passes `check` on the first or second try.

## P7: SongMap Studio GUI (≈4–6 sessions; G1–G3 can start after P1)

Milestones G1–G6 exactly as in [docs/GUI.md §6](docs/GUI.md):
1. **G1:** knobs and audition (FastAPI server, schema-driven knob panels, velocity pads, keyboard, waveform, render cache).
2. **G2:** presets (A/B, diff, morph, randomize, Copy as songmap).
3. **G3:** step grid and feel panel with loop swap.
4. **G4:** song view synced to the video, timeline, mixer, QA panel.
5. **G5:** patch editor (form first, then node graph) for arbitrary instruments.
6. **G6:** plugin and sampler panels.

**How to verify:** run `songmap gui`, open it in the desktop app's browser pane, and exercise each milestone's "done when" from GUI.md. API tests run under pytest with FastAPI's TestClient.

## P8: Video integration (≈1 session)

1. `songmap cues-from-video <VideoX.tsx>`: statically scan for `Slam`/`Counter`/`Flash`/`Tag` `at=` values, honouring `<Sequence from=…>` offsets (VideoA's +840!), and counter `dur` for landing frames. Emit `cue` lines with comments.
2. Remotion helper `remotion/songmap.ts`: `loadCues()`, `cue(name).frame`, `section(name).start/end`, `bar(n)`, `beat(n)`. Port one video to it as the example.
3. `songmap mux video.mp4 song.wav -o out.mp4` (the ffmpeg wrapper).
4. Bring-your-own-track: `songmap cues-from-audio track.wav` (librosa beat and onset) → `cues.json` + suggested sections.

**Done when:** changing a section length in the `.sm` moves the matching scene in the re-rendered video with no TSX edits.

## P9: Variety (ongoing)

- **Pattern library:** breakbeat, half-time, shuffle, trap, brushes jazz, 6/8, cinematic ostinati, walking bass, Alberti and ballad comping, string ostinati.
- **Groove extraction from reference loops** (onset timing → template).
- KTH performance rules (duration contrast, final ritardando, phrase punctuation, leap articulation, harmonic charge).
- Tempo maps with `rit`/`accel`, plus frame-safety warnings.
- Mood presets for new video types (explainer, promo, calm walkthrough).
