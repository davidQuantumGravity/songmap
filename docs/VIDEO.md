# Video views and instrument panels

`songmap video FILE -o output.mp4` reads the adjacent `<song>.view.yaml`. Music remains in the `.sm` score.
The default classic layout has a shared grand staff, note letters and scrolling piano roll. An `instrument`
layer provides a separate, clipped staff window with its own part filter, register, clef and current-note names.

```yaml
size: [1280, 720]
theme: dark
color_by: part
part_colors: {lead: '#e9bb61', bass: '#a1c58e'}
layers:
  - {type: header, box: [0.02, 0.03, 0.96, 0.10]}
  - type: instrument
    box: [0.02, 0.17, 0.47, 0.70]
    parts: [lead]
    label: Lead
    mode: bar
    bars: 1
  - type: instrument
    box: [0.51, 0.17, 0.47, 0.70]
    parts: [bass]
    label: Bass
    mode: active
  - {type: sections, box: [0.02, 0.92, 0.96, 0.045]}
```

- `box` is `[x,y,width,height]`, in fractions of the output frame. Every panel draws within its own image.
- `parts` selects the part names in this panel. An empty list shows no notes; an omitted filter shows the
  score's selected parts. The top-level view filter still limits the score supplied to every layer.
- `mode: bar` shows the current bar, including held notes crossing into it. `bars` is a positive integer.
  Page changes use actual timeline bar boundaries, including tempo and meter changes. The audio tail keeps
  the final bar on screen.
- `mode: active` shows only notes whose written gates include the current time. A resting instrument retains
  its labeled panel, so the grid does not jump when parts enter or leave.
- Bright heads and the names at the upper right identify held notes. Dim heads show the rest of a bar.
  Horizontal lines indicate duration. This is proportional notation rather than a fully engraved part.
- Release and reverb tails can remain audible after a written note stops being highlighted.

## Performance cards

Set `style: performance` on an instrument layer for large, separate sounding-note chips, stronger note-on
highlighting and a fractional-pitch strip below the staff. Every member of a chord gets its own chip,
including its octave and `^`/`v` spelling. Distinct sixth-steps remain distinct even when their noteheads
share a staff position. The staff fits the current bar's register rather than the instrument's entire song.

```yaml
size: [1920, 1080]
layers:
  - type: instrument
    style: performance
    box: [0.02, 0.17, 0.47, 0.7]
    parts: [keys]
    label: Grand piano
    mode: bar
    note_chips: true
    pitch_strip: true
    glow: true
```

The three options default to `true` in performance cards and can be disabled individually. In 36-ET the
pitch strip has three cells per semitone; in 12-ET it has one. Colored cells and chips follow exact written
note gates. Playing/rest status describes those gates, rather than an inferred audio envelope. Octave
doublings retain separate labels. Dense chords wrap into multiple chip rows instead of losing notes.

A header can also use `style: performance`, with an optional `subtitle`, to show a larger chord symbol
and its individual pitch classes. The classic header and compact score cards remain available.

Studio's Video designer offers an **Instrument grid** button using the selected pitched parts. Individual
panels expose instrument, label, mode and bars-per-page controls, alongside the existing box and layer controls.
**Performance grid** selects the new cards at 1080p. Each selected card exposes individual note names,
pitch-strip and glow toggles. **Classic layout** restores the original design. Save view writes the
sidecar for CLI and Studio exports.

The textbook builder also reads a sidecar beside each `.songmap.yaml` audio source, for example
`textbook/audio/ch51/01_sideways_sun.songmap.view.yaml`. The sidecar content participates in the media cache key;
editing a view therefore invalidates that example's cached video and poster.

Chapter 51 uses the five melody-revision-2 Golden Worlds scores, translated losslessly into textbook YAML,
and a short two-mode teaching comparison. Its five song videos use 1080p performance cards, CRF 18 H.264,
and the existing verified audio. Redraw them without resynthesizing the music with:

```powershell
.\.venv\Scripts\python.exe -X utf8 tools/render_golden_performance_videos.py
```

For a normal chapter build:

```powershell
.\.venv\Scripts\python.exe -X utf8 tools/textbook/build.py --check --chapters ch51
.\.venv\Scripts\python.exe -X utf8 tools/textbook/build.py --chapters ch51 --jobs 2
```

Cartoon performers and animated notation bubbles are deferred. The instrument panel is a reusable cropped
notation surface; this release does not add character assets, animation states, speech bubbles or a compositor
for those future effects.
