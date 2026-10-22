# Five songs: golden harmony inside Western music

Five complete songs written with the `songmap-compose` skill in 36-ET (`tuning=36edo`). Western harmony is home in all
five. Golden chords come in as passing light, sparkle, colour, a pivot between keys, and in one case a home of their own.
Each song explores one technique from [docs/GOLDEN_THEORY.md](../../docs/GOLDEN_THEORY.md) and
[docs/GOLDEN_BLENDING.md](../../docs/GOLDEN_BLENDING.md). Open [index.html](index.html) to listen to all five on one page. The textbook's Chapter 47, *Five songs: golden harmony
in Western music* ([textbook/content/ch47.html](../../textbook/content/ch47.html)), features each full song with a timed
listening guide, then short excerpts, piano rolls of the exact voicings, the theory behind it, and exercises.

| # | Song | Style | Instruments | Golden technique | Length |
|---|---|---|---|---|---|
| 1 | [Golden Hour Lullaby](01_golden_hour_lullaby.sm) | C major lullaby, 72 BPM | music box, felt piano, harp, flute, strings, bass, soft brushes | passing chords on the weak beats, the golden escalator into V, the four-chord golden authentic cadence, the golden plagal amen | 2:31 |
| 2 | [Deceptive Light](02_deceptive_light.sm) | G major pop, 120 BPM | drums with claps and fills, bass, electric piano, strummed guitar, pluck arpeggio, pad, lead, glass bell | the golden deceptive cadence D – vE♭g – E♭g – Em as a bass walk-up, and as the form's surprise ending of choruses 2 and 3; the escalator; golden modal mixture C – Cg – Cm – G | 2:37 |
| 3 | [Tape Bloom](03_tape_bloom.sm) | A minor lo-fi, 90 BPM | swung drums, vinyl crackle, electric piano, sliding bass, piano melody, nylon guitar, flute, pad, bells | golden colour chords by projection (Fmaj7 → Fg, E7 → Eg, Am → vAg); the golden Picardy third Am – Am(^3) – Ag – A | 2:23 |
| 4 | [Andalusian Gold](04_andalusian_gold.sm) | A minor flamenco, 100 BPM | rasgueado and picado guitars, palmas and cajón, walking bass, strings, cante lead, violin line, bell | the golden Andalusian cadence Am – A♭g – vA♭g – G – ^F#g – vF#g – F – vF – ^E – E, played plain first, then golden | 2:14 |
| 5 | [The Silver Third](05_silver_third.sm) | cinematic, 90 BPM | piano, strings, harp ostinato, drums and toms, bass, lead, horn, organ choir, bells, golden pad | a pivot from C to ^E♭ through Fg (keys with no note in common); a golden home on golden-spectrum timbres; golden giant steps C – Cg – A♭ – A♭g – E – Eg – C | 2:39 |

The first, shorter versions (1:40–2:17, fewer instruments) are kept in [v1/](v1/).

## How the golden moments were kept tasteful

- **Golden chords sit on weak beats.** As passing chords they last one beat or less (2 and 4); colour chords last half a bar.
  The only longer golden stretch is song 5's golden home, which changes timbre so that golden chords are the consonant ones.
- **The melody never fights the gold.** On every golden chord it rests, or holds a tone the chord shares (C over
  vFg/C, F over Fg, E over Eg). In the giant steps it holds exactly the common tone of each step.
- **Parts that sound together change chord together.** Pads and comping use the voice-led styles (`hold`, `comp`,
  `bassline`), and bass and guitar figures are chord-relative (`rel:`), so they all follow the golden chords.
  [tools/rubs.py](../../tools/rubs.py) checked every song for accidental microtonal rubs: notes 33 or 67 cents apart that
  overlap for at least a quarter beat. All five are clean, apart from the one-beat golden chords over a held bass in song 1:
  the "golden six-four" pedal of the passing engine, which the theory treats as idiomatic.
- **Stable timbres.** `keys/still`, `epiano/still`, `pad/still` and `string_pluck/still` have no detune, drift or
  tremolo; leads and bass are `clean/*`; `master clean` only normalises the peak. Nothing wobbles against the 36-ET pitches.

## Numbers (from each render's `qa.json`)

| Song | Integrated loudness | True peak | Loudest section, and its margin over every other section |
|---|---|---|---|
| Golden Hour Lullaby | −22.2 LUFS | −0.99 dBTP | `finale`, +2.9 dB |
| Deceptive Light | −17.5 | −0.95 | `chorus_3`, +3.0 dB |
| Tape Bloom | −22.2 | −0.86 | `reprise`, +3.1 dB |
| Andalusian Gold | −19.5 | −0.95 | `climax`, +3.2 dB |
| The Silver Third | −19.6 | −0.99 | `homecoming`, +3.0 dB |

None clips. The melody stem sits within about 2 dB of the loudest accompaniment in every song.

**Not checked by ear.** Everything above was judged from the score, the chord analysis and the loudness numbers.
Whether it sounds good is for you to decide.

## Re-render

```bash
cd songs/golden
songmap render 01_golden_hour_lullaby.sm -o renders/01_golden_hour_lullaby --mp3
python ../../tools/rubs.py 01_golden_hour_lullaby.sm --min 0.25        # microtonal rub check
```

Renders go to `renders/` (WAV, MP3, stems, `cues.json`, `qa.json`). They aren't committed, since every one can be rebuilt from its `.sm` file.
