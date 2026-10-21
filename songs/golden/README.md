# Five songs: golden harmony inside Western music

Five complete songs written with the `songmap-compose` skill in 36-ET (`tuning=36edo`). Western harmony is home in all
five. Golden chords come in as passing light, sparkle, colour, a pivot between keys, and in one case a home of their own.
Each song explores one technique from [docs/GOLDEN_THEORY.md](../../docs/GOLDEN_THEORY.md) and
[docs/GOLDEN_BLENDING.md](../../docs/GOLDEN_BLENDING.md). Open [index.html](index.html) to listen to all five on one page.

| # | Song | Key, tempo | Golden technique | Length |
|---|---|---|---|---|
| 1 | [Golden Hour Lullaby](01_golden_hour_lullaby.sm) | C major, 72 | Passing chords: I–IV and V–I through one golden chord, the golden escalator into V, the four-chord golden authentic cadence, a golden plagal amen | 2:17 |
| 2 | [Deceptive Light](02_deceptive_light.sm) | G major, 120, pop | The golden deceptive cadence V – v♭VIg – ♭VIg – vi as a bass walk-up (D – vE♭ – E♭ – E), the escalator in the pre-chorus, golden modal mixture at the end (C – Cg – Cm – G) | 2:11 |
| 3 | [Tape Bloom](03_tape_bloom.sm) | A minor, 90, lo-fi | Golden colour chords by projection, held like borrowed chords: Fmaj7 → Fg, E7 → Eg (a "blue" dominant), Am → vAg; ends on the golden Picardy third Am – Am(^3) – Ag – A | 2:01 |
| 4 | [Andalusian Gold](04_andalusian_gold.sm) | A minor / E Phrygian, 100 | The golden Andalusian cadence Am – A♭g – vA♭g – G – ^F#g – vF#g – F – vF – ^E – E: the bass walks the tetrachord down in sixth-steps. Played plain first, then golden | 1:40 |
| 5 | [The Silver Third](05_silver_third.sm) | C → ^E♭ → golden home → C, 90 | Pivot-chord modulation between keys that share no note (C and ^E♭ share Fg and Gg); a golden-home interlude on golden-spectrum timbres; golden giant steps C – Cg – A♭ – A♭g – E – Eg – C | 2:07 |

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
| Golden Hour Lullaby | −21.6 LUFS | −0.95 dBTP | `glow` (the bridge), +3.2 dB |
| Deceptive Light | −18.2 | −0.99 | `chorus_3`, +4.7 dB |
| Tape Bloom | −19.2 | −0.99 | `bloom`, +1.9 dB |
| Andalusian Gold | −18.8 | −0.99 | `gold_full`, +1.8 dB |
| The Silver Third | −18.9 | −0.99 | `homecoming`, +1.8 dB |

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
