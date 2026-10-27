# Bass and drums

SongMap now has eight recorded electric-bass voices, four acoustic-bass voices, eight new synth-bass presets,
four complete acoustic drum setups, a hybrid kit with recorded alternate takes, a hand-percussion set,
and eight electronic kick/snare/hat combinations. With the later [keys and guitar expansion](KEYS_GUITAR_PALETTE.md),
the shared sample catalog contains 146 recorded programs in total.

Listen at [the bass and drum gallery](../songs/rhythm_palette/index.html). It contains 42 rendered, editable examples,
including eight sixteen-bar templates. The [palette manifest](../songs/rhythm_palette/palette.json) lists their scores.
Studio groups sampled voices by family and drum type. `songmap describe` gives the same names to the AI.
Whole-kit setups are editable `kit` lines in the example scores; Studio's selector changes individual pieces.

## Installation and reproduction

No VST host is needed for these sounds. Recorded instruments use the existing SFZ backend; electronic presets
use SongMap's existing synthesis engine. Everything in this expansion is free to download and use in music.

```powershell
.venv/Scripts/python -m songmap.cli samples install black_pearl growly
.venv/Scripts/python -m songmap.cli samples install bass
.venv/Scripts/python -m songmap.cli samples verify
.venv/Scripts/python tools/rhythm_palette.py --prepare --render --gallery --audit
```

An install selector can be an individual voice, a source/kit name, or an instrument family (`bass`, `drum`).
The complete library is approximately 3 GB; install selected sources to keep it smaller.
Source revisions and archive hashes are pinned in `songmap/instruments/sampler/voices.yaml`.
The installer verifies Git blobs or an archive's SHA-256 before writing sample files. Its local receipt records every
installed file's SHA-256 and provenance. Audio stays under the ignored `samples/` directory.

Use `--only 01_soul_pocket --render --gallery --audit` to rerender one example after changing its source.
`--prepare` regenerates the starter scores; omit it when preserving your own edits. Copy a template to a new score
before composing from it. Two render workers are the default and maximum for this tool.

## Bass choices

| Reference after `sampler/` | Recording and use |
|---|---|
| `jazz_bass` | Growlybass sustained Jazz Bass, four dynamic layers and four alternate takes |
| `jazz_bass_staccato` | Separately recorded short Jazz Bass notes, five alternate takes |
| `flatwound_bass` | Swagbass: old flatwounds and neck pickup, three dynamic layers and four takes |
| `roundwound_bass` | Fashionbass: roundwounds and neck pickup, five dynamic layers and three takes |
| `bass_vi_roundwound` | Pastabass roundwounds, three dynamic layers and three takes |
| `bass_vi_pick` | Pastabass picked flatwounds, bridge pickup, three dynamic layers and four takes |
| `bass_vi_muted` | Pastabass muted pick, combined pickups, three dynamic layers and three takes |
| `bass_vi_finger` | Pastabass fingered flatwounds, neck pickup, three dynamic layers and four takes |
| `double_bass` | Existing VSCO plucked acoustic bass |
| `upright_bass` | Rubner plucked acoustic bass, an alternative recorded instrument |
| `upright_bass_arco` | Rubner bowed acoustic bass; orchestral lines |
| `double_bass_arco` | VSCO bowed acoustic bass without vibrato; orchestral lines |

The four acoustic choices comprise two plucked and two bowed voices. Bowed bass is a separate playing technique,
not a substitute for a plucked groove. There is no sampled slap/pop electric bass in this selection.

Eight electronic bass presets are `bass/round_sub`, `rubber`, `acid`, `mellow_square`, `disco_pluck`, `warm_saw`,
`reedy`, and `growl` (each uses the `bass/` prefix). They have different oscillator balances, envelopes, filters and
drive. They are synthesis recipes, not recordings of eight hardware instruments.

Recorded basses have no scripted slide, hammer-on, pull-off, or connected legato engine. Choose notes and gates for
the technique actually recorded. Use the synth bass when continuous portamento is the musical intention.
Keep electric and acoustic bass lines mainly below MIDI 60, within each voice's catalog range.

## Drum choices

`black_pearl`, `red_zeppelin`, `blonde_bop` and `blonde_bop_rods` are four AVL setups. Each exposes these suffixes:

| Sound | References use `<kit>_<suffix>` after `sampler/` |
|---|---|
| Kick | `kick` |
| Snare | `snare`, `snare_edge`, `sidestick` |
| Toms | `tom`, `tom_edge`, `floor_tom`, `floor_tom_edge` |
| Hats | `hat`, `hat_pedal`, `hat_semi`, `hat_open` |
| Cymbals | `crash`, `ride`, `ride_bell`, `splash`, `china` |

For example, `sampler/red_zeppelin_snare` and `sampler/blonde_bop_rods_floor_tom` are actual catalog names.
The kits offer five recorded dynamic layers per piece. Hot rods are a playing method, not a fifth independently
recorded drum set. Several setups share cymbal samples, so the number of catalog entries overstates the number of
distinct physical cymbals. Use the gallery and individual Studio auditions to choose by sound.

Additional VCSL voices include `studio_snare_2`, `studio_snare_2_rim`, `studio_snare_3`, `studio_snare_3_rim`,
`studio_tom_high_stick`, `studio_tom_high_mallet`, `studio_tom_low_stick`, `studio_tom_low_mallet`,
`suspended_crash_1`, and `suspended_crash_2`. These add separate recordings; the studio snares and toms include
recorded alternate takes. The `studio_takes` example combines them with AVL kick and cymbals.

The `busk_*` voices add cajon, left/right congas, shaker, tambourine and cowbell, with ten dynamic layers.
All sampled kit pieces map the engine's ordinary trigger to their actual SFZ key. Source panning, one-shot tails,
velocity curves and hat choke groups are preserved. Drum defaults disable automatic layer blending, so a boundary
between two velocity layers does not double the transient.

There are eight new presets each for `kick/`, `snare/` and `hat/`, demonstrated in the electronic sets.
They cover short/deep kicks, dry/noisy/shell-led snares, and closed/open/dark/bright hats.
Names such as `club_909` describe an intended synthesis character; they are not sampled hardware or exact emulations.
The tom and cymbal expansion is recorded acoustic percussion; no new electronic tom/cymbal model is claimed here.

## Performance and templates

New drum styles are `pocket`, `dry_funk`, `soul`, `ride_shuffle`, `light_rods`, `half_time`, `broken_beat`, and
`dub_space`. New bass styles are `pocket`, `syncopated`, `half_time`, and `dub`. They are ordinary pattern YAML,
available in both Studio and the AI catalog. No existing default ensemble or historical score was replaced.

The eight templates pair these patterns with specific instruments. They contain an opening, a reply, a lift,
a written transition, a quieter landing and a resolved stop. Acoustic transitions stop the hats while two hands
play the toms. Bass lines leave rests; quieter snare pickups remain below the backbeat. Hat pedal/open examples
exercise actual choke groups. Acoustic bass templates disable the old heavy kick sidechain.

Treat these as arrangements to develop, not finished songs to loop indefinitely. For each song:

1. Pick one coherent kit and one bass technique. Add a second articulation only where a player would use it.
2. Write strong/weak strokes and ghost notes before adding small timing variation.
3. Let the bass and kick agree on important arrivals. Use rests and note lengths to create the pocket.
4. Alternate a hat/ride part with a two-hand fill; avoid having every percussion lane run throughout.
5. Vary the phrase after four or eight bars. A response, pickup or omission often works better than more notes.
6. Render stems and compare their levels. The template mixes were adjusted from their measured stems.

Round robins reduce identical repeated recordings; they do not create phrasing. Velocity layers change the
recorded attack; random timing alone does not create a convincing player. AVL's missing recorded round robins
remain a limit, particularly for exposed fast rolls.

## Sources and verification

[Karoryfer's publisher](https://shop.karoryfer.com/pages/free-samples) dedicates its free libraries to CC0, including
older downloads whose bundled notices may predate that change. This expansion uses Growlybass, Swagbass,
Fashionbass, Pastabass and the original D. Smolken double bass. Their individual Git revisions remain in the manifest.
[VCSL](https://github.com/sgossner/VCSL) and [VSCO 2 CE](https://github.com/sgossner/VSCO-2-CE) are also CC0.

[AVL's publisher](https://www.bandshed.net/avldrumkits/) specifies CC BY-SA 3.0 for its samples and mappings, with
an explicit exception allowing music to be distributed or sold without attribution. Preserve that license and
credit when redistributing or modifying the sample library itself. SongMap records the publisher and pinned
archive hash in every relevant render's `LICENSES.md`. These site credits are retained even where optional.

The engine additions implement SFZ `amp_velcurve_N` interpolation and source panning, with static channel/bend
metadata handling. They also fix sampled take counters restarting at eight and cache collisions between pieces
that share one SFZ program. Native synthesis keeps its original seeded variation, and no golden event digests changed.

`verification.json` checks that every example has current source-matched audio, MP3, review and QA assets, with no
clipped samples. The score listener reports no problems. Render reviews retain some contrast warnings: these are
short groove starters with relatively steady playing levels, rather than complete dramatic cue arcs. Bass-heavy
notes in exposed bass/tom passages are intentional. Neither automated QA nor sample provenance establishes musical
realism; audition the examples before selecting replacements for the textbook or complete songs.

The existing textbook recordings and staged website package remain the previous edition. This collection prepares
the palette and templates for deliberate song-by-song replacement; it does not silently rescore the whole textbook.
