# Piano, keyboards and guitars

The [listening page](../songs/keys_guitars/index.html) contains 46 controlled four-bar timbre auditions and
eight authored eight-bar musical starters. Its A/B player switches between two sounds at the current position.
Keyboard auditions share one score; guitar auditions share another. Their renders target -18 LUFS and retain
written soft/firm contrasts. The original modeled piano and guitar remain available as references.

The sample catalog now contains 146 programs, including 30 additions in this expansion. Programs include
registrations, playing techniques, recorded channels and layered takes of the same instruments. These counts
do not mean 146 different physical instruments. Studio and the AI Lab generation context use the same catalog.

## Recorded choices

References below follow `sampler/`.

| Group | References | What differs |
|---|---|---|
| Acoustic piano | `grand_piano`, `steinway_piano`, `knight_piano`, `yamaha_piano`, `meta_piano` | Kawai and Steinway grands; Knight, Yamaha and Meta upright recordings. Different attacks, decays, ranges and velocity mappings. |
| Electric piano / FM | `rhodes_mono`, `rhodes_stereo`, `rhodes_vibrato`, `fm_piano`, `tx_piano`, `clavisynth` | One sampled 1977 Rhodes Mark I with dry, baked chorus and baked vibrato outputs; three different recorded TX81Z programs. |
| Harpsichord | `english_harpsichord`, `lute_harpsichord`, `french_harpsichord`, `italian_harpsichord`, `flemish_harpsichord`, `flemish_full` | Different recorded instruments and stop/registration choices. English lute and Flemish full are alternate registrations. |
| Recorded organ | `renaissance_8`, `renaissance_4`, `renaissance_4_8`, `renaissance_full`, `pipe_quiet`, `pipe_loud` | Fixed registrations of Renaissance and pipe-organ recordings. |
| Acoustic guitar | `nylon_guitar`, `nylon_finger`, `nylon_pick`, `steel_guitar`, `archtop_mic` | Nylon automatic, finger and picked techniques; steel-string acoustic; microphone channel of the Shiny archtop. |
| Electric guitar | `archtop_pickup`, `emily_clean`, `emily_release`, `emily_ensemble` | Shiny magnetic pickup; Emily direct recording with/without release noises; a three-voice layer of Emily takes. |

The nylon and steel mappings select first-position strings on channel 1 and retain per-string choke groups:
plucking a new note on a string damps its previous note. Nylon samples ring naturally as one-shots. Their note-off
does not invent a recorded mute. Keep chord shapes small and playable; the fixed string map cannot choose a new
fingering for each chord. Explicit string-channel selection is not currently a Studio control.

Emily has four velocity layers and three recorded alternate takes. Shiny has four velocity layers and four
alternate takes, with microphone and pickup recorded separately. They provide varied attacks, not connected
hammer-ons, pull-offs or slides. The ensemble program layers existing takes; it is not another guitar.

## Native keyboard recipes and tone controls

Eight new FM synthesis presets are `epiano/round_tine`, `warm_suitcase`, `bright_bark`, `soft_ballad`, `bell_keys`,
`wide_tremolo`, `dry_funk`, and `fm_chime` (use the `epiano/` prefix for each). They vary the FM index, its decay,
tine level, release and tremolo. They are synthesis recipes, not recordings or hardware emulations.

Four tonewheel recipes are `organ/hollow_jazz`, `gospel`, `soft_chorale`, and `rock_rotary`. Their drawbars,
percussion, key click and rotary rate are editable. Recorded pipe organs are separate from this tonewheel model.

Every new sample voice works with the existing AI Lab **Shape this sound** and **Blend A ↔ B** controls.
Brightness, body, attack softness, tightness and grit change continuously; a blend combines two sources.
Those controls change the sound without claiming to morph the physical instrument or manufacture a missing
recorded technique. Sampler controls expose velocity-zone crossfade, added attack, release multiplier and
release-noise level. Native keyboards expose their own synthesis parameters in Studio's Instruments pane.

Electric guitars can use existing EQ, drive, compression, chorus, tremolo and delay inserts. The electric-pocket
starter includes gentle EQ/drive. These are simple processing chains, not a convolution cabinet or a complete
guitar amplifier model. Keep a clean DI reference when evaluating an effect.

## Musical starters

The eight templates develop a question, reply, lift/turn and ending. Each score records the musical and expression
decisions for its instruments. They cover upright conversation, Rhodes comping, harpsichord counterpoint, 6/8
organ, nylon fingerstyle, steel chords, electric double-stops and archtop jazz voicings. Bass and drum parts leave
room for the main instrument; mixes were revised from the rendered stem measurements.

Use these as editable starting arrangements. They do not replace previous songs or user-approved parts.
Their note-level dynamics and gates are deliberate; automatic humanization is supplementary. Some short-template
render reviews retain contrast warnings. A passed source/audio check does not establish a preferred musical sound.

## Install, reproduce and verify

```powershell
.venv/Scripts/python.exe -m songmap.cli samples install steinway_piano knight_piano yamaha_piano meta_piano
.venv/Scripts/python.exe -m songmap.cli samples install rhodes_mono nylon_finger steel_guitar archtop_pickup emily_clean
.venv/Scripts/python.exe -m songmap.cli samples verify
.venv/Scripts/python.exe tools/keys_guitar_palette.py --prepare --render --gallery --audit
```

Use `--only rhodes_mono` to render a single audition. `--prepare` regenerates controlled audition scores and the
manifest; it preserves the hand-authored templates. Copy a template before developing a new song. Samples remain
in the ignored local `samples/` directory. Source revisions and hashes are pinned in `sampler/voices.yaml`, and
the installer verifies all downloaded blobs and records SHA-256 hashes, including derived fixed programs.
The complete installed collection is about 5.5 GB. Meta programs use the publisher's pinned OGG recordings;
their separate original-WAV release archives are not installed by these recipes.

Fixed preparation resolves pedal, keyswitch and channel selection before playback. The original mappings remain
untouched beside the prepared mappings. Unexpected unsupported opcodes still fail installation. This prevents
simultaneous pedal-up/down attacks, doubled guitar string-channel maps and controller noises becoming notes.
Extra source pitch/level randomization is disabled in the prepared Meta mappings; recorded variation is retained.
Shiny uses a fixed single voice and full microphone or pickup selection, without its live modulation controls.
Guitar choke releases use SongMap's existing short choke fade. Live piano pedal/half-pedal and continuous guitar
controllers remain outside the sampler subset. Long notes can reach the end of recordings that have no loop.

## Sources and rights

[VCSL](https://github.com/sgossner/VCSL), [Meta Open Sound's instrument collections](https://github.com/facebookincubator/Meta-open-sound)
and [Karoryfer's free instruments](https://shop.karoryfer.com/pages/free-samples) are CC0. Meta's separate Oculus
sound-effects collection is not included here. Older Karoryfer notices can differ; the publisher now dedicates
these free instruments to CC0.

[jRhodes3d's license](https://github.com/sfzinstruments/jlearman.jRhodes3d/blob/master/LICENSE) explicitly permits
musicians to use its sounds in music under CC0. Distribution of its raw samples uses CC BY-NC 4.0; commercial
sample/software redistribution requires a separate license. SongMap downloads the samples locally and keeps
the original notice. Rendered music and raw-sample redistribution have different permissions.

Sampled renders write `LICENSES.md` with source, author and revision. Keep those credits with published music.
The listening gallery provides them beside each sampled example. This expansion does not stage or publish a
new textbook edition; existing textbook audio remains unchanged.
