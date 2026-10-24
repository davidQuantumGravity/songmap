# SongMap with recorded instruments

Open [the instrument gallery and song comparisons](index.html). The A/B buttons switch between original and sampled
masters at the same timestamp. Playback attenuates the louder version using integrated LUFS so volume alone does not
favor it. Only one player runs at a time.

Seventeen listening pieces have separate SFZ editions in this folder. The original scores and existing renders are
preserved. Written notes, harmony, form, tuning, tempo, frame counts, cues and binaural settings remain the same;
instrument choices and faders change. These are listening candidates, not user-approved replacements.

Start with **Two Windows** for piano, flute, harp and acoustic bass; **Pocket Algebra** for piano, vibraphone and plucked
accompaniment; **Andalusian Gold** for the recorded cello and violin alongside its original guitar parts; and **The Silver
Third** for piano, harp and horn. The epic keeps its designed guitar, synths and drums, with recorded acoustic and FM keyboards.

## Scope

| Collection | Revised | Approach |
|---|---:|---|
| Golden | 5 | Recorded keys, winds, harp or strings where the written part fits |
| Golden Worlds | 5 | Distinct acoustic and electronic combinations; golden-spectrum pads retained |
| Golden House | 3 | Recorded keyboard parts; electronic rhythm sections retained |
| Still Water | 3 | Recorded piano, harp and flute; headphone layers and golden-spectrum voices retained |
| Epic | 1 | Recorded keyboards within the existing progressive arrangement |

Four other current listening pieces were reviewed and retained:

- [Escalator](../golden_house/03_escalator.sm): its synthesized bass, lead and arpeggio define the electronic texture.
- [Quasicrystal](../golden_house/04_quasicrystal.sm): organ stabs, shimmer and the golden-spectrum pad are deliberate sound design.
- [Deep Water](../still_water/03_deep_water.sm): engineered golden partials are the musical material.
- [Moon on the Water](../still_water/04_moon_on_the_water.sm): its sustained golden-spectrum layers serve the piece's purpose.

Earlier score snapshots, demonstration fixtures and faithful video ports are preserved. This pass covers the 21 current
listening pieces in Golden, Golden Worlds, Golden House, Still Water and Epic.

## The library

The 17-voice selection uses CC0 recordings from VCSL and VSCO 2 Community Edition: Kawai grand piano, TX81Z FM piano,
folk harp, marimba, vibraphone, kalimba, plucked double bass, cellos, violins, solo violin, flute, horn, short bowed
cellos and violins, bass drum, snare and closed hi-hat. The download is about 1.08 GB, stored outside Git in `samples/`.

The [editable instrument demonstrations](../sfz_library/) play soft, medium and hard phrases, then a held sixth-step-up
note. Their renders and the revised songs contain WAV/MP3, QA plots and source credits. Full revised songs also have stems.

Recordings retain natural pitch variation and recorded vibrato. Their fractional-pitch resampling does not turn them
into the engineered spectra of `clean/golden_pad` or `clean/glass`. The sampler remains an SFZ subset; see
[the library documentation](../../docs/SFZ_LIBRARY.md) for supported features and limits.

## Verification and rebuilding

[edition.json](edition.json) records source and score hashes, changed instruments and final faders, event digests,
measurements, inherited findings and any new audio warnings. [checks.txt](checks.txt) contains the CLI check/listen output.
[sustain-audit.json](sustain-audit.json) checks the recorded winds and strings against the written note lengths.
The automatic ear evaluates the score and mix; it does not establish aesthetic preference. Existing composition
warnings are recorded alongside the originals. The five Golden scores retain their original clean peak normalization;
their measured true peaks are reported rather than treated as a true-peak limiter guarantee.
Those five historical cue files also predate the per-section `beats_per_bar` field. The receipt records that specific
schema addition; all existing cue values and all current-exporter cue objects are compared exactly.

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m songmap.cli samples install
.\.venv\Scripts\python.exe -m songmap.cli samples verify
.\.venv\Scripts\python.exe -X utf8 tools/sfz_revisit.py --gallery --render --audit --page
```

For a single edited score, use `songmap check`, `songmap listen` and `songmap render FILE -o FOLDER --mp3` as usual.
`--prepare` creates the initial instrumental edition and never overwrites an existing score. Keep the saved scores
when rebuilding the final mixes; the later fader refinements are written in those files.

Final verification (2026-10-23): 652 tests passed; the Studio build passed; 17 revised masters have zero clipped samples and zero new automated mix warnings. All written event digests, timing and current-exporter cue objects match the originals. The installed library has 17 voices and 749 verified files. The browser check confirmed all 17 voice choices, their defaults, and A/B playback. See [verification.json](verification.json).
