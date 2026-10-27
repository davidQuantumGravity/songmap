# Classical and jazz ensembles

The installed library now has 210 recorded programs, including 64 added for ensemble work.
Programs include techniques, dynamic subsets and registrations of the same recording sessions;
they are not 210 different physical instruments. Fourteen named hybrid instruments add
continuous blends and tone controls. No VST host or paid plugin is required.

Listen at [the ensemble gallery](http://127.0.0.1:8871/songs/ensemble_palette/index.html).
It includes 76 recorded-program auditions, 14 hybrid auditions and six authored ensemble
starters. Counts are checked in `songs/ensemble_palette/palette.json` and `verification.json`.

## Ensemble coverage

| Ensemble desk | Available recordings and variations | Limits |
|---|---|---|
| First and second violins | Solo violin and violin section; sustained vibrato, soft sustain, pizzicato, spiccato, tremolo | Two desks can have independent notes and expression; they share the same section recordings. Soft sustain is a subset of the sustained program, not a second instrument. |
| Violas | Viola section with sustain, soft sustain, pizzicato, spiccato and tremolo | No separately sampled solo viola. |
| Cellos | Cello section with the same five techniques | No separately sampled solo cello. |
| Double basses | Recorded solo bowed non-vibrato/vibrato, soft bowed vibrato, pizzicato, spiccato, tremolo; additional Rubner upright arco/pizzicato | Solo recordings can be layered, but are not a separately recorded orchestral bass section. |
| Flutes and piccolo | Flute non-vibrato, vibrato, expressive vibrato, staccato; piccolo sustain/staccato | Ranges differ by technique; flute staccato starts at MIDI 65. No alto/bass flute. |
| Oboes | Non-vibrato, vibrato, staccato | English horn and oboe d'amore remain gaps. |
| Clarinets | Sustain and staccato | Bass clarinet and E-flat clarinet remain gaps. |
| Bassoons | Sustain, vibrato and staccato | Contrabassoon remains a gap. |
| French horns | Open sustain, muted sustain and staccato | Recorded muted range is narrower. Blending does not model hand position. |
| Trumpets | Open sustain, vibrato, staccato, straight mute and Harmon mute | No sampled shakes, falls or connected legato. |
| Trombones | Tenor sustain, vibrato and staccato | Bass/alto trombone and euphonium remain gaps. |
| Tuba | Sustain and staccato | No alternate tuba player or section recording. |
| Jazz saxophones | Actual MTG soprano, alto, tenor and baritone; VCSL tenor non-vibrato/vibrato/staccato; saxello non-vibrato/vibrato/staccato | Saxello is a distinct instrument. MTG's three round-robin mappings reuse neighboring keys, rather than three independently played takes per key. No recorded falls, growls or subtone set. |
| Harp and mallets | Folk harp, orchestral harp, glockenspiel, tubular bells, soft/medium/hard xylophone, marimba, vibraphone | Mallet hardness has distinct recorded attacks. Celesta remains a gap. |
| Orchestral percussion | Pitched timpani hits and recorded rolls, two gongs; existing orchestral bass/snare, cymbals and toms | Gong keys select hit variations. Use an actual roll program rather than a rapid identical-hit loop. |
| Jazz rhythm section | Five acoustic pianos, Rhodes/FM/organ variants, archtop/steel/nylon/electric guitars, upright/electric basses, multiple acoustic/electronic drum lines | See the keys/guitar and bass/drum guides. Rods are not brush recordings; a dedicated brush kit remains a gap. |

A conventional orchestra can now give independent parts to the five string desks, paired
core woodwinds, piccolo, horns, trumpets, tenor trombones, tuba, harp and percussion.
Auxiliary instruments above remain explicit gaps; do not relabel a transposed sample as one.
For a big band, write separate alto 1/2, tenor 1/2, baritone, trumpet and tenor-trombone parts
over the existing rhythm section. Reusing a recording in separate parts is not another
recorded player, and the bass-trombone chair is still missing. Scores use sounding/concert
pitch; this update does not add transposed printed parts for B-flat/E-flat instruments.

## One instrument with continuous controls

In Studio, select a part, open **Rack**, choose **sound · continuous palettes**, choose a
palette and open **Knobs**. There are palettes for violin, viola, cello, double bass, flute,
oboe, clarinet, bassoon, French horn, trumpet, tenor trombone, tuba, tenor sax and xylophone.
The description identifies every source, including palettes that mix different instruments.

Two-source palettes use `blend`. Four-source palettes place A/B on the top row and C/D
on the bottom row. Their weights are:

```
A = (1-X)(1-Y)     B = X(1-Y)
C = (1-X)Y         D = XY
```

Weights sum to one. Each corner reproduces its source with neutral tone settings. A center
position layers recordings; it does not create a new physical bowing technique or mute.
Use sources' overlapping ranges when blending. Prefer discrete articulation choices for
realistic detached/pizzicato passages; their blends are also available for sound design.

```text
inst lead=sound/trumpet_palette(morph_x=.25, morph_y=.4, tone_brightness=-.2)
inst strings=sound/violin_palette(morph_x=.6, tone_body=.15, tone_attack=.2)
```

Brightness, body, attack, tightness, saturation, stereo width and added vibrato have neutral
defaults. Added vibrato delays 180 ms, fades in over 300 ms and reaches at most 35 cents;
recorded vibrato remains present. Width changes the stereo side signal; mono recordings
do not acquire a stereo ensemble. Source-prefixed controls (`a.attack`, `b.release_mul`,
`c.level`, `d.tune`) remain available in the rack.

Custom scores can define `sounds.<name>` with A, A/B, or all A/B/C/D sources; score definitions
override library names. Nesting still permits at most four levels and eight leaf voices.
AI Lab exposes the matching morph controls in **Shape this sound**, alongside the tone knobs.
Saving creates a new take for review; it does not vote or replace the score automatically.

The gallery's Web Audio playground blends unmastered `source.wav` stems with one common
output gain, preserving the balance of the saved recipes. Ordinary A/B files retain their
preview masters. Studio's [Expression editor](EXPRESSION_ARTICULATION_RESPONSE.md) now
moves source balance, tone, volume and added pitch/vibrato within held notes. The 23
`family/` instruments also select named recorded techniques per phrase or scheduled beat.
Connected sample-legato and a physically modeled bow/reed/bell remain future work.

## Authored starters and performance

Six editable scores cover a string conversation, woodwind quartet, brass quintet, jazz
quintet, sax quartet and an orchestral handoff. Each has comments recording per-instrument
note and expression decisions. The orchestral starter passes the melody between families;
it does not make every available desk play continuously. The sax quartet uses actual
soprano/alto/tenor/baritone recordings. The string starter uses a solo lead and recorded
sections below it, rather than pretending to be a sampled solo string quartet.

Write each instrument's notes first, its expression second, then check it in the ensemble.
Choose breaths, bow lengths, phrase peaks, mutes, vibrato, rests and dynamics deliberately.
Do not expect random humanization or a blended timbre to supply those musical decisions.

## Sources, preparation and validation

VSCO 2 CE and VCSL recordings are CC0; the pinned MTG saxophone set is CC BY 4.0 and requires
attribution. Renders write actual source credits in `LICENSES.md`. Upstream references:
[VSCO 2 CE](https://github.com/sgossner/VSCO-2-CE),
[VCSL](https://github.com/sgossner/VCSL),
[MTG Solo Sax](https://github.com/sfzinstruments/MTG.SoloSax).

MTG preparation fixes ordinary attacks and loops. It omits controller-triggered noise,
scripted legato, controller/filter envelopes and scripted vibrato, with each omitted opcode
recorded explicitly in the manifest. Sample tuning offsets, velocity layers and sequence
mappings are retained. Originals stay intact; generated mappings and source files are hashed
in the installation receipt. Nested include resolution supports libraries using either
included-file paths or paths from the main SFZ directory.

```powershell
.venv/Scripts/python.exe -m songmap.cli samples install
.venv/Scripts/python.exe -m songmap.cli samples verify
.venv/Scripts/python.exe tools/ensemble_palette.py --prepare --render --gallery --audit
.venv/Scripts/python.exe tools/verify_ensembles.py
```

The gallery audit checks score hashes, audio/QA/license assets and clipping; it reports score
listener findings separately. Numerical QA does not establish that a rendition sounds real.
Human A/B choices and text feedback in AI Lab remain the preference evidence.
