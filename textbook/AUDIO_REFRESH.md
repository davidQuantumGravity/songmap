# Sampled textbook audio edition

The October 2026 refresh reviews every chapter example, every referenced golden-suite recording,
and every score in the generated Songbook. `audio_refresh.json` is the complete decision list.

| Source group | Updated playback | Retained | Reviewed |
|---|---:|---:|---:|
| Chapter examples | 256 | 141 | 397 |
| Referenced suite recordings | 14 | 13 | 27 |
| Original Songbook inventory | 24 | 44 | 68 |
| Total | 294 | 198 | 492 |

The 438 chapter audio placements include repeated references to those 27 suite recordings.
Seven additional editable sampled scores are generated under `songs/textbook_refresh/` and
also appear in the Songbook. The 17 earlier SFZ song editions remain under `songs/sfz_revisited/`.

## What changes

Musical teaching examples use recorded grand piano, FM piano, flute, harp and acoustic bass
where their registers and articulation fit. Full songs use the deliberately chosen, balanced
SFZ editions. Chapter YAML files state the actual instruments and faders; the manifest selects
the playback edition for referenced suite files and original Songbook scores. Original song
scores and suite recordings remain available.

The score check freezes the expanded note-event digest and total frame count. For chapter
sources, every YAML field other than `instruments` and `mix` is checked against the saved original.
Initial balance adjustments compare the energy of representative notes played by the original
and replacement voices. Recorded tuning and vibrato remain part of the sound.

Exact-frequency Python examples, pure tones, spectra, binaural layers, beating and roughness
comparisons, synthesis/processing examples, electronic sound design and historical score editions
retain their intended voices. Golden-spectrum glass and pads remain generated. Sustained wind
and string parts are checked against the available recording length after repitching.

## Rebuild and verify

Run from the repository root with its existing environment:

```powershell
.\.venv\Scripts\python.exe -X utf8 tools/textbook/refresh_audio.py --prepare
.\.venv\Scripts\python.exe -X utf8 tools/textbook/build.py --check
.\.venv\Scripts\python.exe -X utf8 -u tools/textbook/build.py --jobs 1 --reuse-notation
.\.venv\Scripts\python.exe -X utf8 tools/textbook/refresh_audio.py --audit --package
```

`--prepare` checks an existing manifest instead of replacing editorial decisions. A new revision
needs a new reviewed inventory; do not delete the manifest as a routine rebuild step.

`--reuse-notation` preserves an existing video's visual design when its cached source matches a
recorded score and its complete visual score equals the updated score. View and renderer edits are
left for a separate visual build. Changed audio is rendered and remuxed into the existing video;
current audio is reused. Missing or unverifiable videos are drawn normally. GUI and video edits
do not invalidate the audio cache. Finished media URLs are stamped from the actual published bytes.

Each SongMap chapter render publishes an MP3, QA measurements, automated review and spectrogram;
sampled renders also publish recording credits. Songbook renders receive the same checks. A failed
render stops the build. Media URLs include edition hashes so browsers can request the updated audio.
The audio index and the chapter videos point to the same edition.

Verification receipts live in `build/textbook_refresh_*.json` and build/test logs in
`build/textbook_refresh_*.log`. Automated checks establish source consistency and technical playback;
they do not represent a by-ear approval of every example.

## Website handoff

The complete local website is `textbook_site/index.html`. It includes the audio edition notice,
instrument credits and the clip manifest. The existing repository server can show it at
`http://127.0.0.1:8871/textbook_site/`.

`--package` prepares:

- `build/website_ready/music_theory_of_golden_harmony/`: the deployable folder;
- `build/website_ready/music_theory_of_golden_harmony.zip`: the same site in an archive;
- `build/website_ready/receipt.json`: file count, size and destination.

PDFs and print intermediates are excluded. The website audit checks local links, referenced media,
QA results, source hashes and the existing staging tool's per-file size threshold. Before replacing
the production copy, use the repository's normal staging command:

```powershell
.\.venv\Scripts\python.exe tools/textbook/stage.py "C:/Users/chest/Documents/Business/Deeper Research/website/landing/public/music_theory_of_golden_harmony" --dry
```

Removing `--dry` stages the verified local files into the website project; building and deploying
that project are separate actions. This refresh prepares a local publishing package and does not
deploy the live website or update the PDF edition.

The verified package has also been staged into the website project's
`landing/public/music_theory_of_golden_harmony/` folder. All 2,703 staged files were compared
byte for byte with the prepared snapshot. `build/website_ready/staging_receipt.json` records
the destination and checks; live deployment remains pending.
