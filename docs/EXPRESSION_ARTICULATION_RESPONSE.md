# Expression, recorded techniques and response calibration

These features are available in the renderer, `.sm` and YAML scores, Studio and AI Lab's
score-generation context. Start with the three controlled A/B examples in
[`songs/expression_lab/`](../songs/expression_lab/index.html).

## Continuous expression inside held notes

In Studio, open **Instruments → Expression**. Choose a section and control, click the
graph to add points, drag them, or enter exact beat/value pairs. **Apply expression curve**
changes the unsaved score. **Render** produces the new audio; **Save** persists the score.
Removing a lane restores inheritance from the preceding lane, or the neutral value when
there is no preceding lane. Edits are validated before replacing the score buffer.

```text
inst violin=family/violin
verse 2 | violin:{deg: "=mp 0/1~ | 0/1_"}
set expression={verse: {violin: {volume: [[0,.25],[4,1],[8,.3]], brightness: [[0,-.3],[4,.2],[8,-.2]], vibrato_depth: [[0,0],[3,0],[8,18]]}}}
```

Positions are **quarter-note beats from the section start**, including in compound and
additive meters. Points must increase strictly, begin at 0 and end at the section's exact
length. A number is shorthand for a constant lane. Linear interpolation follows musical
beats through tempo ramps. The terminal value holds through subsequent sections and
release tails until another explicit lane for that part/control begins. Before the first
lane, the neutral value applies. Curves apply to all notes sounding in the part, including
held notes that cross a section boundary.

| Control | Range | Neutral / meaning |
|---|---|---|
| `volume` | 0–1 | 1; performance gain after the written note velocity |
| `brightness` | −1–1 | 0; blend toward a −12/+12 dB high shelf at 3.5 kHz |
| `body` | −1–1 | 0; blend toward a −9/+9 dB low shelf at 180 Hz |
| `vibrato_depth` | 0–100 cents | 0; added pitch vibrato, recorded vibrato remains |
| `vibrato_rate` | 0.1–12 Hz | 5.2 Hz; speed of added vibrato |
| `pitch_cents` | −200–200 cents | 0; bend added to the score's exact fractional pitch |
| `stereo_width` | 0–2 | 1; side gain, 0 mono; mono recordings remain mono |
| `blend` | 0–1 | two-source sound A/B balance |
| `morph_x`, `morph_y` | 0–1 | four-source complementary corner gains |

Mix lanes require a `sound/` instrument with the corresponding source layout. They replace
that sound's static balance for the specified times. Initially silent corners are rendered
so a held note can fade into them. Other controls operate on native, recorded and hybrid
voices. Studio currently offers lanes for melodic parts, rather than individual kit pieces.

Brightness/body are continuous output tone changes, not crossfades between recorded
soft and loud sample layers. Pitch/vibrato use resampling within the note buffer, not
independent pitch/time stretching. Controls are rendered into audio; MIDI CC export and
live input/recording are outside this implementation. The older parsed `auto:` field is
not a working general parameter-automation engine. Use `expression`, not `auto`, for
these controls. Existing knob settings remain static unless an expression lane overrides
the corresponding performance control.

## One instrument with named recorded techniques

Select **family · recorded techniques** in the Rack, then choose the instrument family.
The 23 families cover solo/section strings, orchestral winds, all four saxophone ranges
plus saxello, horn/trumpet/trombone/tuba, nylon guitar, upright bass, timpani and xylophone.
Each family's menu lists only recordings actually present in the curated library.

The default technique can be **Auto**, or an explicit recording. Auto selects a matching
short recording for written staccato/staccatissimo where that family defines one; otherwise
it uses the family's default. Slurs retain their phrasing role without inventing recorded
connected transitions. A part's explicit `technique` option overrides the default:

```text
answer 1 | violin:{deg: "=p 0/4 r/4 2/4 r/4", technique: pizzicato}
```

For changes inside a section, use the **Recorded technique changes** schedule in
Expression, or write:

```text
set techniques={story: {violin: [[0,"sustain"],[4,"pizzicato"],[8,"spiccato"],[12,"tremolo"]]}}
```

Technique changes are steps, affecting notes that start at or after the beat. Held notes
finish their original recording. Beats must increase and lie inside the section; names
and the selected recording's pitch range are checked. `"auto"` returns that passage to
written-articulation selection. A schedule applies within its named section; it does not
carry into later sections. Continuous crossfades between techniques use a suitable
`sound/` recipe instead. Connected recorded legato and extra round-robin recordings are
not manufactured by these selectors.

Score expansion checks technique names, published catalog ranges and curve/source layouts
without opening optional audio packs. Rendering still requires the selected recordings
and checks the installed SFZ's actual regions. Missing packs produce an installation
instruction; they do not prevent inspecting the score's notes and timing.

## Measured response without flattening dynamics

`calibration` is a 0–1 knob on each instrument: 0 retains its original level, 1 applies
its measured reference gain, and intermediate values interpolate in dB. New `family/`
voices enable it by default. Older native, sampler and sound scores retain their original
defaults, so previous mixes are not silently rebalanced.

The bundled `songmap/instruments/response.yaml` contains **298 source profiles**, including
the **210 installed sample programs** and native models/presets. The repeatable procedure
renders three registers at velocities .37/.62/.87 with a .28-second gate; it measures the
first .32 seconds' RMS, the full-buffer peak, attack threshold and output duration. It
targets −26 dBFS reference RMS using **one fixed gain per source**, capped to −18…+12 dB
and measured peak .8. This is response calibration, not perceptual loudness matching or
normalization of individual notes, layers or round-robin takes. Other pitches, velocities
and stacked arrangements still require mix/headroom review.

The full local audit is `.songmap/response/measurements.json`. Eleven programs have
non-monotonic measured energy at one or more tested pitches: picked/muted Bass VI,
steel guitar, mic/pickup archtop, Emily ensemble, violin spiccato, viola pizzicato,
vibrato/staccato oboe and clarinet. Those flags remain visible with source profiles;
they identify listening work and do not justify flattening genuine timbre differences.
No automatic retuning or claim of measured pitch accuracy is made. Existing SFZ tune
offsets and fractional-pitch rendering remain in effect.

Reproduce with `.venv/Scripts/python.exe -X utf8 tools/calibrate_instruments.py`
(`--only sampler/clarinet` for a bounded rerun). Profiles affect render-cache identity.
The ensemble gallery's morph player now uses unmastered post-fader stems and one common
output gain, preserving the source balance of saved recipes. Its ordinary A/B audition
files still have their own preview masters.

For the local audition site, use `.venv/Scripts/python.exe tools/serve_music.py 8871`.
The existing async music server supports audio byte-range seeking and concurrent source
downloads. The morph player retries transient download failures up to twice within its
20-second loading limit, and Stop cancels loading.

## AI writing and verification

AI Lab supplies the family definitions, installed sources, control ranges and score syntax
to generation. **Riff** candidates may change the selected part's notes, expression and
techniques while keeping its instrument and backing fixed. **Arrangement** candidates may
coordinate those changes across parts. The instrument-only scope retains its existing
voice/parameter contract. User preferences and unsent feedback are not fabricated by tests.

Write one instrument's notes first, then its continuous expression and recorded techniques,
and review it with the ensemble before moving on. Rendered QA checks clipping and musical
heuristics; the listener still decides whether the result is convincing.
