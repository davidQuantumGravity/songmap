# The free sampled instrument library

SongMap includes a catalog of 116 recorded voices. Install their audio separately:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .[sampler,gui]
.\.venv\Scripts\python.exe -m songmap.cli samples list
.\.venv\Scripts\python.exe -m songmap.cli samples install
.\.venv\Scripts\python.exe -m songmap.cli samples verify
```

The complete selection downloads about 3 GB of uncompressed audio and source programs. Individual voices can be
installed by name, for example `songmap samples install grand_piano flute folk_harp`. Installation resumes and verifies
Git downloads against their pinned blobs and archive downloads against their pinned SHA-256. `samples/songmap-library.json` records SHA-256 hashes,
source revisions and credits. `verify` detects missing or changed installed files. Keep the receipt with backups.

`--root PATH` selects another installation folder; add it to `SONGMAP_SAMPLES` when rendering. Audio stays outside Git.
The source programs and recordings retain their upstream layout under `samples/_packs/`. No executable plugins are needed.

The bass/drum expansion adds recorded electric and acoustic basses, complete acoustic kits, and additional
snare/tom/cymbal articulations. See [BASS_DRUM_PALETTE.md](BASS_DRUM_PALETTE.md) for all families,
42 editable examples, eight groove templates and the performance limits.

## Original voices

| Reference, after `sampler/` | Character |
|---|---|
| `grand_piano` | Kawai acoustic grand, velocity layers and key releases |
| `fm_piano` | Recorded Yamaha TX81Z FM keyboard |
| `folk_harp` | Warm plucked harp, two explicit crossfaded velocity layers |
| `marimba` | Wooden mallets, round attack |
| `vibraphone` | Soft metallic mallets |
| `kalimba` | Plucked tines with a woody attack |
| `double_bass` | Pizzicato acoustic bass with alternate takes |
| `cello`, `violins`, `solo_violin` | Bowed strings with recorded vibrato |
| `cello_spiccato`, `violins_spiccato` | Short bowed string attacks |
| `flute` | Recorded flute without vibrato |
| `horn` | Sustained French horn |
| `bass_drum`, `snare_drum`, `hi_hat` | Acoustic percussion kit components |

```sm
song "Sampled quartet" 100 4/4 C fps=30 seed=7 tail=3 tuning=36edo
inst keys=sampler/grand_piano lead=sampler/flute harp=sampler/folk_harp bass=sampler/double_bass
chords C Am F G
theme 4 | keys:comp harp:{rel: "R/8 3 5 3 R+ 5 3 5"} bass:bassline lead:{deg: "0/4 2 4/2 | 5/4 4 2/2 | 3/4 2 0/2 | 1/2 0/2", oct: 1} dyn=p<mf
mix keys -5 hall=.15 | lead -2 hall=.15 | harp -8 hall=.2 | bass -4
master standard lufs=-18 glue=none
```

Studio's sampled-instrument selector lists each voice, its installed state, description and range. Missing voices are
disabled. Its existing knobs, phrase audition and sixth-step controls also work with samples. The AI catalog from
`songmap describe --compact` names every curated reference; `songmap describe` supplies descriptions, ranges and status.
The compact catalog is stable across machines; use `songmap samples list` to check installation before choosing voices.
Reload Studio after installing additional voices so its catalog reflects the new installation.

The percussion voices map SongMap's kit trigger to the recording's fixed source key; the closed hi-hat is MIDI 42.
This avoids silent hats when the engine emits its ordinary kit trigger at MIDI 60.

## Playback and limits

Supported additions: source-frame offsets; explicit equal-power velocity fades; seeded random groups; decay and
sustain envelopes; explicit sustain/continuous loop points; and one-shot playback that ignores note-off. Existing
velocity-zone blending, round-robin selection, release samples, choke groups and fractional-pitch resampling remain.
The expanded percussion/bass library also uses source panning and explicit amplifier velocity curves.
Drum defaults disable automatic velocity crossfading to avoid doubled transients.
`ampeg_dynamic` is inert for static notes because SongMap sends no live envelope-modulating MIDI CC messages.

This remains an SFZ subset. MIDI pedal automation, keyswitches, CC-driven expression, filters and LFOs are not implemented.
Loop points must be explicit in the SFZ; embedded WAV loop metadata is not read. Other unsupported opcodes still produce
warnings. The installer rejects curated programs with unsupported features rather than presenting them as fully supported.
Long sustained notes can reach the end of a source recording when that program has no loop.

Pitches are resampled from float MIDI without snapping to twelve tones. This preserves written 36-ET offsets;
recorded tuning deviations and vibrato remain audible. Bowed strings are not substitutes for the stable, engineered
partials of `clean/golden_pad` or `clean/glass`. Keep those voices when their spectrum is the musical point.

## Sources and listening review

[VCSL](https://github.com/sgossner/VCSL) and [VSCO 2 Community Edition](https://github.com/sgossner/VSCO-2-CE) supply the
original recordings and mappings under CC0 1.0. The expanded bass library adds Karoryfer CC0 recordings;
AVL kits use CC BY-SA 3.0 with the publisher's explicit music-use exception. See the palette guide for attribution details. `songmap/instruments/sampler/voices.yaml` pins their revisions and defines the
curated names and defaults. Every sampled song render writes its sources and revisions to `LICENSES.md`.

Run `python tools/sfz_revisit.py --gallery` to rebuild the editable instrument demonstrations in `songs/sfz_library/`.
The song revisions and loudness-matched A/B players are in `songs/sfz_revisited/`; originals are preserved.
Automated tests, scores and measurements establish operation, pitch handling and audio bounds. They do not establish
that a revision is aesthetically preferable; the listening page is provided for that decision.
