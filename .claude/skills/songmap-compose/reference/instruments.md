# Instruments and arrangement

## The palette

Name parts by role. The six default parts (`drums bass pad arp lead fx`) have instruments and a mix already. **Name any other part after its instrument** (`keys`, `piano`, `epiano`, `organ`, `gtr`/`guitar`) and it gets that instrument and a calibrated level, near the pad's. A part with another name needs `inst <name>=<instrument>`, and set its level with `mix <name> <dB>`.

| Part (instrument) | Character | Good for | Range | Shape it with `inst` |
|---|---|---|---|---|
| `keys` (piano) | modal piano: hammer, two-stage decay, warm sustain | melody, chords, intimacy, "human" scenes | 43–84 | `keys(hardness=.3, t60=8)` soft and felt-like; `hardness=.7` bright; `t60` sets ring time |
| `epiano` (FM tine) | Rhodes-like, bell bark when played hard, tremolo | lo-fi, warm chords, nostalgia | 48–79 | `epiano(trem_depth=.35, index=.9)` mellow; `index=1.8` barky |
| `organ` (tonewheel) | sustained, churchy or soulful, rotary swirl | pads with motion, gospel, retro | 48–79 | drawbars `db1..db9` (0–8): `organ(db1=8, db2=8, db3=8)` full; `organ(db3=8, db4=6, db1=0, db2=0)` softer; `rotor=6.5` fast tremolo |
| `gtr` (string_pluck) | Karplus-Strong guitar, harp or koto | arpeggios, ripples, folk warmth | 40–84 | `string_pluck(brightness=.6)` nylon-ish; `.85` steel/harp; `pick_pos=.1` thin; `body=.8` woody |
| `pad` (detuned saws) | wide, soft attack | harmony bed, atmosphere | 48–76 | styles `warm` and `dark` (triads); write rel for 7ths; `inst pad(attack=.8, cutoff=1200)` darker and slower |
| `arp` (pluck) | short synth plucks | motion, tech, data | 55–84 | `arp:up` brightens over 8 bars; `arp:dark` filtered; `order=[...]` sets the figure |
| `lead` (mono synth) | vibrato, glides with `~` | featured melody, hooks | 60–88 | `inst lead(vib_depth=20, glide=.08)`. Its default level is low, so **for a featured melody add `mix lead 6`** |
| `bass` (mono synth) | saw plus sub, a filter envelope | low end | 28–55 | `bass(cutoff=500)` round; `cutoff=1200` growl; `glide=.08` with `~` slides |
| `drums` (kit) | kick snare clap hat ohat hat16 fill ghost rim | groove | — | `kit kick=kick/v0(tune=44, decay=.6)` deeper and longer kick |
| `fx` (kit) | riser impact zap tick | events, transitions, data texture | — | via events (`!riser`, `!impact(size=xl)`, `!zaps(count=6)`) and `fx:ticks` |

Instrument names only appear in `inst` lines. A part always names its role, e.g. `inst gtr=string_pluck(brightness=.6)` and then `gtr:{rel: ...}`.

## Combinations that work

| Mood | Palette |
|---|---|
| warm explainer | keys melody, gtr ripples, pad:warm, pocket drums, rel bass |
| tech, data | arp:up, pad:dark, `fx:ticks`, four_floor, bass:eighths, lead hook |
| cinematic | pad:dark into pad:warm, halftime drums, sub bass, lead theme at the climax, impacts |
| lo-fi, nostalgic | epiano rootless chords, keys melody, shuffle drums, slide bass, quiet pad |
| reflective, solo | keys alone, or keys and pad. Silence is part of the sound |
| playful | gtr bright and staccato, arp, light pocket, zaps on list items |

## Ambience and sound design with this palette

There are no field recordings. Suggest the world with musical gestures, kept quiet and sparse:

| Effect | Recipe |
|---|---|
| rain, data, clock | `fx:ticks` with `mix fx -9`; denser for heavier rain. `!zaps` for digital chatter |
| distant thunder, a boom | an `!impact(size=s)` plus a low bass note: `bass:{rel: "R/1", oct: -2}` under `dyn=pp<mp`. The bass is audible from about `oct: -2` (E1–G2); lower is felt, not heard |
| a heartbeat | `drums:{kick: "X.x.....X.x....."}`, quiet: `dyn=p` and `mix drums -6` |
| wind, mist, breath | `pad:dark` with a slow swell (`dyn=pp<p>pp`) on an open chord (`[R,5,9]`), and no drums |
| birdsong, sparkle | sparse, high, short notes: `gtr:{deg: "=pp r/2 11/8' 9 r/4", oct: 1}` or epiano grace notes (`{9}11/16'`), with rests in between |
| water, shimmer | `arp:dark(order=[0, 2, 4, 2])` very quiet (`dyn=pp`), or slow guitar ripples |
| tension drone | a held `bass:{rel: "R/1", oct: -2}` plus `pad:dark` on one chord for several bars, with `dyn=pp<mf` |
| an arrival, landing | `!riser:2` ending on the frame, `!impact`, every part entering together |

## Arrangement: making a texture

- **One job per instrument.** Every part is one of: melody (one at a time), counter-line, harmony (chords), rhythm (drums, plucks), bass. Two parts in the same job and register blur.
- **Frequency slots:** bass below C3 (MIDI 48), chords C3–C5, melody above the chords (an octave apart is clear), hats and plucks on top. If the melody and the chords share a register, move one by an octave (`oct`).
- **Density follows the story.** Start sparse (2–3 parts), add one layer per section or scene, peak with everything, then subtract. Entries and exits are themselves events: a new instrument entering on a cut is a free "hit".
- **Contrast between sections:** a change of texture (who plays), register, rhythm density or harmonic rhythm. Changing only the drums is weak; change two things.
- **Leave room for the voice-over.** In a narrated video, keep the melody sparse and mid-low under speech, and bring it forward between lines.
- **Balance.** Start new songs with `mix drums -6 | fx -6 | lead 6` (the defaults are tuned to the drum-heavy Oct-13 tracks). After rendering, look at `qa.json`: `stems` holds per-part LUFS over the whole song (a part that plays less reads lower), and `sections` holds the contrast.
  - **Melody.** A featured melody belongs within a few dB of the loudest accompaniment: `mix keys 0` to `2` for a piano tune, `mix lead 6` to `8`.
  - **Soft pieces.** For a soft or reflective piece, go further: `mix drums -9`.
