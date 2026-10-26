# Instruments: the suite, the model, and how to make them sound real

Working code for 14 instruments is in [reference/sketch_v1/instruments.py](../reference/sketch_v1/instruments.py), on top of [dsp.py](../reference/sketch_v1/dsp.py). It is tested by `test_sketch.py`, which includes a check that velocity changes timbre and not just level. `demo.py` renders `out/gallery.wav`: every instrument at p, mf and ff.

## 1. What makes an instrument sound real (in order of payoff)

1. **Velocity changes timbre.** Hard hits are brighter, have sharper attacks, more noise or click, more pitch sweep, and often longer decay. Soft hits are darker and shorter. Every instrument maps velocity to at least two non-level parameters, and the test suite enforces it (spectral centroid must rise with velocity).
2. **No two hits are identical (round-robin).** The `rr` param jitters decay, pitch (a few cents), noise seed and timing of internal components per note, using the note's seed. Samplers use real round-robin layers.
3. **Performance.** Timing feel, dynamics, articulation and phrasing are handled by [PERFORMANCE.md](PERFORMANCE.md), not by the instrument. They matter as much as the sound.
4. **Physics where it counts.**
   - Strings and plucks: Karplus-Strong or waveguide, so the tone darkens as it decays.
   - Pianos, mallets and bells: modal synthesis with inharmonic partials and two-stage decay.
   - Drums: pitch envelopes plus filtered noise.
   - Each of these gets the natural *evolution* of the sound for free.
5. **The incidental noises.** Hammer thump, key click, bow noise, breath, fret squeak, release and damper noise, pedal resonance. They are small in level but large in realism.
6. **Space.** A stereo early-reflection room on drums and a hall send on sustained parts. Instruments are panned and spread like a stage (`pan_mono`, the pitch-dependent spread in `Keys`).
7. **Band-limited oscillators.** PolyBLEP saw and square (`dsp.saw`, `dsp.square`) remove the "fizzy" aliasing of `synth_v0`. The test shows at least 4× less alias energy at 3.5 kHz.

## 2. The instrument contract

```python
@register
class Snare(Instrument):
    name, family = "snare", "drum"          # family: drum | bass | keys | synth | string | bowed | brass | wind | voice | fx
    mono = False                            # mono instruments glide on slurs (`~`)
    PARAMS = (                              # the ONLY place knobs are defined
        Param("tone", 185, 120, 320, "Hz", "log", "pitch", "shell fundamental"),
        Param("vel_bright", 1.5, 0, 4, "oct", "lin", "velocity", "ghost notes darker"),
        ...)
    def render(self, note: Note) -> np.ndarray: ...   # mono (n,) or stereo (n, 2), starts at note-on
    def tail(self, note) -> float: ...                # seconds after the gate (for buffer sizing)
```

`Note` carries `pitch` (fractional MIDI number), `vel` (0–1), `gate` (seconds held, already adjusted for articulation), `seed`, `glide_from`, and `params` (an automation snapshot for this note).

From the single `PARAMS` schema you get:
- **GUI knobs:** each param's group becomes a panel, `curve='log'` gives an exponential knob, and the unit is shown ([GUI.md](GUI.md)).
- **Validation:** unknown names fail with "did you mean …?", and values are clamped to range.
- **LLM context:** `describe()` prints one ~40-token line per instrument.
- **Automation:** any param can be an automation lane, e.g. `auto: {cutoff: "800>3000 exp"}`.
- **MIDI CC mapping** when the GUI is played from a keyboard.

**Conventions:**
- Frequency-type velocity amounts are in **octaves per unit velocity** around a reference of 0.7 (`vel_oct`).
- Level follows `vel ** vel_curve`.
- `rr` (0–1) scales all per-hit randomness.
- Frequency and time params use `log` knob curves.

## 3. Catalog

Status: ✅ in the sketch · 🟡 planned, technique decided · 🔵 via sampler/plugin backend.

### Drums and percussion
| Instrument | Technique | Key params | Status |
|---|---|---|---|
| `kick` | Sine with exponential pitch sweep, band-passed click, optional 808 sub tail, tanh drive | tune, sweep, sweep_time, decay, click, sub, drive, vel_sweep, vel_click | ✅ |
| `snare` | Two-mode shell + HP/LP-filtered wires + stick snap; velocity → brighter, longer wires | tone, tone_decay, tone_mix, noise_decay, noise_hp/lp, snap, vel_bright | ✅ |
| `clap` | 1–8 band-passed noise bursts with jittered spacing, long last tail | bursts, spread, decay, center, q | ✅ |
| `hat` | 808 six-square metal + noise, BP/HP; closed/open by `decay`; **choke group** (open hat cut by closed) | tune, decay, metal, hp, color, vel_decay, choke | ✅ |
| `tom` | Modal membrane (circular-membrane ratios 1, 1.59, 2.14, 2.30, 2.65) + pitch drop + stick noise | tune, decay, pitch_drop, stick | 🟡 |
| `cymbal` (ride/crash/china) | 40–80 inharmonic modes + high-passed noise with slow bloom; crash = bloom; ride = bell partials + ping | size, bell, bloom, decay, dark | 🟡 |
| `shaker`, `tambourine` | Stochastic particle model (PhISEM): Poisson-timed grains through resonant filters | grains, resonance, swing | 🟡 |
| `rim`, `clave`, `cowbell`, `woodblock` | 1–3 tuned modes with very short decays (cowbell: two detuned squares through a BP, 808-style) | tune, decay, tone | 🟡 |
| `brushes` | Shaped pink noise (swish = slow attack) + tap transients | swish, tap, decay | 🟡 |
| `timpani`, `taiko`, `cinematic_drum` | Modal membrane, large pitch-glide on hard hits, long room | tune, size, decay, room | 🟡 |

### Bass
| Instrument | Technique | Key params | Status |
|---|---|---|---|
| `bass` | Mono subtractive: PolyBLEP saw/square + sub, resonant SVF with velocity × envelope, glide | saw, square, sub, cutoff, res, env_amt, env_decay, glide, drive | ✅ |
| `bass808` | Sine + harmonics with long decay, pitch glide on slurs, distortion | tune, decay, glide, drive, punch | 🟡 |
| `acid` | 303 semantics: `^` accent = louder, more resonant, faster envelope; `~` slide = glide + held gate | cutoff, res, env_mod, accent, decay | 🟡 |
| `ebass` | Karplus-Strong with pick/finger excitation, pickup-position comb, palm-mute = short gate | pluck_pos, pickup, tone, mute | 🟡 |
| `upright` | Karplus-Strong + body resonances + finger-slide noise on glides | body, thump, slide | 🟡 / 🔵 |

### Keys
| Instrument | Technique | Key params | Status |
|---|---|---|---|
| `keys` (piano) | Modal: stiff-string partials `f_n = n·f0·√(1+Bn²)`, hammer-position comb, velocity → spectral tilt, two-stage decay, 2-string beating, damper release, pitch-dependent stereo | partials, inharm, hardness, hammer_pos, t60, aftersound, unison, thump, release, spread, vel_hard | ✅ (add: sustain pedal + sympathetic resonance, Phase 5) |
| `epiano` | Two-op FM, velocity → index ("bark"), 14:1 tine transient, stereo tremolo | index, index_decay, tine, t60, trem_rate/depth, vel_index | ✅ |
| `organ` | Additive tonewheels, 9 drawbars, percussion, key click, rotary (doppler + AM) | db1–db9, perc, click, rotor | ✅ |
| `clav`, `harpsichord` | Karplus-Strong, bright loop, pluck near the bridge; harpsichord: release "thunk" | brightness, pluck_pos, release_noise | 🟡 |
| `celesta`, `music_box` | Modal (ratios 1, 2.76, 5.4) + tine noise | hardness, decay | 🟡 |
| sampled grand | Salamander-style multi-velocity samples | — | 🔵 |

### Mallets and bells (all modal, `dsp.modal`)
| Instrument | Mode ratios | Notes | Status |
|---|---|---|---|
| `marimba` | 1, 3.93, 9.2 (tuned bar ≈ 1:4:10) + resonator tube | soft mallets = fewer upper modes | 🟡 |
| `vibes` | 1, 4, 10 + motor tremolo + pedal | | 🟡 |
| `glockenspiel` | 1, 2.71, 5.15, 8.43 | very bright, long | 🟡 |
| `bell` / `tubular` | hum 0.5, prime 1, tierce 1.2, quint 1.5, nominal 2, + 2.5, 2.67, 3 | slow beating pairs | 🟡 |
| `kalimba` | 1, 5.4, 13.1, short | | 🟡 |

### Strings
| Instrument | Technique | Status |
|---|---|---|
| `string_pluck` (guitar/harp/koto) | Karplus-Strong with fractional delay (pitch exact to under 3 cents in tests), pick-position comb, velocity-bright excitation, body EQ | ✅ |
| `bowed` (violin, viola, cello, contrabass) | **Option A (synth):** sawtooth-like source with bow-pressure noise, a formant **body filter** (fixed resonances per instrument), delayed vibrato with rate/depth wander, slow attack shaped by dynamics, legato crossfades. **Option B (physical):** bowed waveguide with a friction curve (numba, per-sample). Start with A; it is cheaper and controllable. | 🟡 |
| `strings` (ensemble section) | N detuned and slightly time-offset `bowed` players (N = 4–12), each with its own vibrato and drift. **Section size is a knob.** Articulations: sustain, tremolo (fast bow AM + noise), pizzicato (KS), spiccato (short gate + bow noise) | 🟡 / 🔵 (VSCO-2 CE samples for solo exposure) |

### Brass and winds
| Instrument | Technique | Status |
|---|---|---|
| `brass` (trumpet, horn, trombone, tuba, ensemble) | Additive or saw with **dynamics → brightness** (the "brass law": the spectrum widens strongly with loudness), lip "blat" at the attack, pitch scoop up, breath noise, formant body. Horn = darker, rounder. A cinematic "braam" = low brass ensemble + distortion | 🟡 |
| `flute` | Sine + 2nd/3rd harmonics + breath noise riding the envelope, jet "chiff" attack, delayed vibrato | 🟡 |
| `clarinet` | Odd-harmonic source (square-ish, band-limited) + register-dependent formant | 🟡 |
| `oboe`, `bassoon` | Saw through narrow formants; nasal | 🟡 / 🔵 |

### Voice
| Instrument | Technique | Status |
|---|---|---|
| `choir` | Formant synthesis (vowel tables for a/e/i/o/u; `vowel` is automatable), N singers with drift and vibrato, breath. "Oo"/"ah" pads | 🟡 |

### Synths
`pad` ✅, `pluck` ✅, `lead` ✅ (unison, delayed vibrato, glide, breath), and `supersaw` (in `dsp`). Planned 🟡: `fm` (4-op with algorithms), `wavetable` (frames from a WAV, position knob), `reese`, `string_machine`, `arp_synth`.

### FX
`riser` ✅ and `impact` ✅ (ported). Planned 🟡: `zap`, `tick` (port from synth_v0), `downlifter`, `whoosh`, `reverse_cymbal`, `sub_drop`, `tape_stop` (a bus effect), `braam`, `stab` (orchestral hit = brass + strings + timpani layered at once).

### Playable ranges (`range_check`)
Violin 55–103 · viola 48–91 · cello 36–81 · contrabass 28–67 · flute 60–96 · clarinet 50–94 · trumpet 54–82 · horn 34–77 · trombone 40–72 · tuba 28–65 · choir SATB 40–81 · harp 23–104 · guitar 40–88 · piano 21–108.

## 4. Building a realistic instrument: recipes

- **Plucked or struck:** excitation (filtered noise or a pulse, brighter with velocity) → resonator (Karplus-Strong, modal, or waveguide) → body (fixed EQ peaks or a modal body) → space. The *excitation* carries the velocity; the *resonator* carries the pitch and decay physics.
- **Sustained (bowed, blown, sung):** source (saw, pulse, or additive) whose **brightness tracks dynamics**, plus noise (bow or breath) that is loudest at the attack and on soft notes. Add vibrato that starts after about 200 ms and wanders in rate and depth (`smooth_noise`). Legato notes glide 30–80 ms and don't re-attack.
- **Ensembles:** never "one voice × N". Each player gets its own detune (±3–8 cents), start offset (±5–25 ms), vibrato phase and rate, and pan position.
- **Drums:** a pitch envelope on every tonal element, noise filtered differently per hit, at least 3 velocity-mapped parameters, and choke groups.
- **Never clicks:** start at zero phase or ramp in for at least 1 ms, end with a release ramp, and keep DC out (high-pass when using asymmetric drive). The test suite will add a click detector (energy above 8 kHz in the first and last 64 samples).

## 5. Samples and plugins (when synthesis isn't enough)

Two optional backends plug into the same `Instrument` contract, so a song can swap `keys/felt_piano` for `sampler/salamander` without other changes.

### 5.1 `sampler`: SFZ subset
- **Parse:** `<region>` + `sample`, `lokey`/`hikey`/`pitch_keycenter`, `lovel`/`hivel` (velocity layers), `seq_length`/`seq_position` (round-robin), `trigger=release` (release samples), `ampeg_attack`/`ampeg_release`, `tune`, `volume`, `group`/`off_by` (choke).
- **Render:** choose the region by key, velocity and round-robin. Repitch with high-quality resampling (`scipy.signal.resample_poly`, or sinc interpolation for fractional ratios). Crossfade adjacent velocity layers by `vel`, add the release sample on note-off, and apply the amp envelope.
- **Libraries to evaluate** (verify each license before use):
  - VSCO-2 Community Edition (orchestral, CC0)
  - Salamander Grand Piano (CC-BY)
  - Sonatina Symphonic Orchestra (CC Sampling+)
  - freesound.org packs filtered by CC0 (drum one-shots)
  - Keep a `LICENSES.md` listing every sample source used in a render.
- **Status:** ✅ `songmap/instruments/sampler/` (sfz.py parser, resample.py Kaiser-windowed sinc, library.py finder and licenses). Notes:
  - Regions are matched by `round(pitch)`, then repitched from the exact float MIDI pitch, so 36edo works.
  - Round-robin cycles with `Note.rr`, the part's note counter mod 8.
  - Chokes are applied by the engine across the notes of a part, with a 6 ms fade.
  - Extras beyond the list above: `key`, `default_path`, `amp_veltrack`, `pitch_keytrack`, `rt_decay`, `#define` and `#include`.
  - Offsets, explicit velocity fades, seeded random groups, decay/sustain, explicit loop points and one-shot playback
    are also supported. Other opcodes produce warnings; filters, LFOs, live pedals and keyswitches remain unsupported.
  - Knobs: `level`, `tune`, `xfade` (velocity crossfade width), `attack`, `release_mul` and `release_level`.

#### Using Salamander from a song
1. Install the extra: `pip install -e .[sampler]` (soundfile).
2. Download `SalamanderGrandPiano-SFZ+FLAC-V3+20200602.tar.gz` (707 MB, CC BY 3.0, Alexander Holm) from <https://freepats.zenvoid.org/Piano/acoustic-grand-piano.html>.
3. Unpack it so the `.sfz` sits somewhere under `samples/salamander/`. `samples/` is git-ignored, and sample audio is never committed. Instead of `./samples`, you can use `~/.songmap/samples/`, or any folder named in `SONGMAP_SAMPLES` (`os.pathsep`-separated).
4. In the song, write `instruments: {keys: sampler/salamander}`, or `{use: sampler/salamander, xfade: 0.7, release_mul: 1.5}`. Nothing else changes.
5. `songmap render` writes `LICENSES.md` next to `song.wav`, crediting every library used. Keep it with the published video's credits.

For a library with several programs, write `sampler/<library>/<program stem>`. For example, VSCO-2 CE (CC0, <https://github.com/sgossner/VSCO-2-CE/releases/tag/1.1.0>) unpacked as `samples/vsco2/` is used as `sampler/vsco2/<stem>`. If a library is missing, the error says where it looked and where to download it.

The curated free library offers 116 individual voices, including piano, FM keyboard, harp, mallets, orchestral
instruments, recorded bass techniques and acoustic kit pieces. `songmap samples install` downloads and verifies their pinned source files;
`songmap samples list` shows availability, and `songmap samples verify` checks the installation. Studio and the AI
catalog expose the individual names. See [SFZ_LIBRARY.md](SFZ_LIBRARY.md) for references, controls and limitations.
See [BASS_DRUM_PALETTE.md](BASS_DRUM_PALETTE.md) for drum articulations, electronic presets and groove templates.

### 5.2 `plugin`: VST3 hosting via DawDreamer
- **Status: planned.** No plugin host is implemented in the current engine.
- `pip install dawdreamer`, then load a VST3 instrument, send it the Played notes as MIDI, and render offline. Parameters come from `get_parameters_description()`, and the GUI shows them like native knobs.
- **Good free instruments:** Surge XT (GPL-3, superb synth), Dexed (DX7 FM), Vital (free tier), OB-Xd. Pianoteq (commercial) is the best non-sample piano.
- **Caveat:** plugin renders are reproducible only if the plugin is deterministic. Pin plugin versions in `render.log`.

## 6. Presets

```yaml
# presets/kick/punchy.yaml
instrument: kick
base: default            # or another preset to inherit from
description: Tight, clicky techno kick that cuts through a busy mix
tags: [techno, tight, bright]
params: {tune: 50, sweep: 34, sweep_time: 0.028, decay: 0.38, click: 0.55, click_tone: 4200, drive: 2.2, rr: 0.25}
```

- Presets are referenced as `kick/punchy`.
- The GUI saves them, the A/B compare feature diffs them, and `songmap describe` lists them with their descriptions.
- Starting packs, one per mood:
  - `techno`: kick/punchy, bass/acid_sub, pluck/glass.
  - `cinematic`: keys/felt_piano, strings/legato, brass/horns_soft, fx/impact_big.
  - `documentary`: keys/felt_piano, string_pluck/nylon, pad/air, mallets/soft_marimba.
  - `ambient`: pad/air, epiano/dream, bell/glass.

## 7. Patch instruments (arbitrary user-defined instruments)

An instrument can also be a **patch**: modules connected by wires, written in the song or kept in the library, with
no Python (`songmap/instruments/patch.py`). SongMap Studio's wiring editor (Instruments tab, Wiring) edits them.

```
patch acid osc1=osc(wave=saw) sweep=env(a=.002, d=.22, s=0, r=.05) f1=filter(cutoff=280, q=9) amp=vca out=out
patch acid osc1>f1 sweep>f1.cutoff*3 vel>f1.cutoff*1.5 f1>amp sweep>amp.gain amp>out
inst bass=patch/acid(f1.cutoff=400)
```

- **Modules** (`describe()` in patch.py lists their knobs):
  - Sources: `osc` (sine, saw, square with pulse width, triangle, supersaw), `wavetable` (single cycles scanned by
    `position`: basic sine-triangle-saw-square, bright, pwm, vowel a-e-i-o-u formants, organ registrations;
    band-limited for each note's pitch, every frame equally loud), `noise` (white to pink), `string` (Karplus-Strong,
    plucked internally or excited by what is wired in), `waveguide` (see below), `modal` (a resonator bank with bell,
    bar, glass or plate ratios).
  - Processing: `filter` (low-, band- or high-pass, resonance, key tracking), `shaper` (tanh drive, wavefolding),
    `comb` (tuned to the note), `delay`, `vca`, `mix`.
  - Control: `env` (ADSR), `lfo` (sine, triangle, square, saw, random steps; with a fade-in delay).
  - `out`: the level, the pan and the tail after the release.
- **Waveguides** (`dsp/waveguide.py`, after the STK instruments of Cook and Scavone): a delay line tuned to the note,
  kept sounding by a nonlinear exciter for as long as the note is held: `mode=bow` (a bow sticking and slipping on a
  string: `pressure` from airy through clean to raucous, `position` from glassy near the bridge to soft over the
  fingerboard), `mode=reed` (a clarinet reed on a closed-open bore: mostly odd harmonics) and `mode=flute` (an air jet
  over a bore; it speaks from about 220 Hz up, as a real flute's range starts at middle C). The loop filter and the
  exciter add a little delay that depends on the note and the settings, so each sustained note is measured and
  rendered once more with its frequency corrected: notes land within a few cents at any pitch, pressure or
  brightness (`tests/test_patch.py`). `tune` takes vibrato (an LFO wired in), `noise` adds breath or bow hair.
- **Wires.** `a>b` sends audio from a into b's input; into an oscillator it is **FM**: it bends the oscillator's phase
  by its `fm` depth (a sine into a sine at 1:1 is the electric piano, at an inharmonic ratio a bell).
  `a>b.knob*amount` moves a knob:
  - frequencies (cutoff, rate) move in octaves per unit;
  - pitch (`detune`, `tune`) moves in semitones;
  - a VCA's `gain` is replaced by what is wired into it (an envelope there is the note's loudness shape);
  - everything else is added.
- **Sources:** `vel` (velocity), `key` (octaves above middle C), `gate` (1 while held), `rand` (per note). Wire `vel`
  into a filter or shaper so velocity changes the timbre, not just the level (§1).
- **Params:** every knob becomes an instrument param named `<module>.<knob>`, so `inst`/`kit` lines, presets and the
  Studio's knobs set it like any other param. Values may name choices: `wave=saw`, `mode=hp`, `body=bell`.
- **Formulas:** a knob may be a formula of the note instead of a number, in quotes: `cutoff="800*2**(2*vel+key)"`
  (brighter for harder and higher notes), `pressure="0.35+0.5*vel"`, `pw="0.5+0.3*sin(2*pi*3*t)"` (a knob that moves
  over the note). Names: `vel` (0..1), `key` (octaves above middle C), `pitch` (MIDI), `freq` (Hz), `gate` (seconds
  held), `rand` (-1..1 per note), `t` (seconds), `pi`, `e`, and the patch's macros; functions `sin cos tan tanh exp
  log log2 log10 sqrt abs floor min max clip`. The formula is parsed into a syntax tree and evaluated with numpy (no
  attribute access, no calls but those functions, never `eval`); the result is kept inside the knob's range. A formula
  knob is not a param (the formula sets it); wires still move it.
- **Checks:** unknown modules, knobs and sources, audio wired out of an envelope, and loops are SongErrors with
  suggestions, at the line that wrote them.
- **Macros:** one 0..1 knob that moves several, `@punch(default=.5, drop.d=.03..0.2, drive.drive=.1..0.7)` on a
  `patch` line (YAML: `macros: {punch: {default: .5, map: {drop.d: [.03, .2]}}}`). The macro is a param like any
  other (`inst kick=patch/kick(punch=.8)`); a knob a macro maps follows the macro (log knobs move logarithmically).
- **Library:** `songmap/patches/*.yaml` (`modules:`, `wires:`, `macros:`, a description). Every built-in instrument has
  a patch sketch of the same name (`snare808` for the snare): its signal chain rebuilt from modules, so the Studio's
  "Build a patch" starts from the instrument you are on and you can rewire it. The sketches are simplifications (the
  hat has three metal squares, not six; the piano is a string, not 24 modal partials; the organ has three drawbars),
  and each says so in its description. Also: acid, bell, glass_pad, wobble, and for the new modules cello (a bowed
  waveguide), clarinet, flute, vowel_pad and scan_bass (wavetables). A song's own patch of the same name wins.
- **Evaluation:** notes render offline, so the graph is evaluated module by module as whole numpy arrays in
  topological order. Feedback exists only inside modules (`string`, `waveguide`, `comb`, `delay`), never between them.

### Instrument guides

`songmap/instruments/guides.yaml` explains every built-in instrument for the Studio's tutorial view (Instruments tab,
Learn). For each one it gives:

- what it imitates, a summary, how it is built and why it sounds the way it does;
- its signal chain as blocks, with the knobs of each block;
- every knob in plain words (what turning it up or down does);
- recipes to try, and drum audition patterns.

`tests/test_guides.py` keeps the guides in step with the code: every param covered, recipe values in range, and
every recipe rendering.

## 8. Checklist: adding an instrument

1. Subclass `Instrument`, declare `PARAMS` with ranges, units, curves, groups and docs, then `@register`.
2. Map velocity to at least 2 non-level parameters, apply `rr` variation, and declare `mono` and, if needed, a playable range.
3. `render()` returns at most `gate + tail` seconds and starts and ends without clicks.
4. Tests: renders finite at vel 0.3 and 1.0; centroid rises with velocity; pitch is accurate for pitched instruments (FFT peak within 5 cents); no clicks; render time under 50 ms per second of audio.
5. Ship 2–4 presets and add a row to the catalog above.
6. Run the gallery (`python demo.py`) and listen, or ask a human to.
