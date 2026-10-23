# Golden House: five electronic songs with golden harmony

Five dance tracks (deep house, UK garage, progressive house, tech house and melodic house) written in 36-ET, each
built around a golden technique from the textbook, used the way that genre uses harmony: in a chord stab, a bass
walk-up, a build, a breakdown, a key change for the last drop. Western harmony is home in all five. Chapter 49 of the
textbook (*Golden House*) features each track with a listening guide, excerpts and the theory; the tracks are also in
the Songbook (appendix H) for review.

| # | Song | Style | Golden technique | Length |
|---|---|---|---|---|
| 1 | [Colour Field](01_colour_field.sm) | deep house, A minor, 122 BPM, swung | colour chords by projection on the organ stabs (Fmaj7 → Fg7, E7 → Eg, Am → vAg); the golden Picardy ending | 2:26 |
| 2 | [Two-Step Gold](02_two_step_gold.sm) | UK garage, E minor, 132 BPM, 2-step | the golden deceptive cadence D – vEbg – Ebg – Em as the bass walk-up on the swung pickups | 2:15 |
| 3 | [Escalator](03_escalator.sm) | progressive house, C major, 126 BPM | the golden escalator F – vF#g – ^F#g – G in every loop; the golden authentic cadence G – vEbT13/G – vCg/G – C lands the drop | 2:36 |
| 4 | [Quasicrystal](04_quasicrystal.sm) | tech house, D minor, 124 BPM | Fibonacci-word percussion over a straight kick (a 9-bar near-repeat instead of a 1-, 2- or 4-bar loop); a close Dg7 whose beats drift through the 16th notes; a golden home on the golden circle and golden modal mixture back to Dm9 | 2:54 |
| 5 | [Silver Lift](05_silver_lift.sm) | melodic progressive house, 128 BPM | golden giant steps C – Cg – Ab – Abg – E – Eg – C in the build; the last drop rises a silver third, C → ^Eb, pivoting through Fg | 2:23 |

## Production rules that keep the gold clean

- **Stable synths.** The supersaw pad and lead run with 3 voices and 3 cents of detune and no drift, so the 33-cent
  sixth-steps stay distinct; plucks, basses, organs and bells have no detune at all.
- **Everything that sounds changes chord with the gold.** Pads are voice-led (`hold`), basses and stabs are
  chord-relative (`rel:`), and stabs and leads either strike on the golden chord or rest. `tools/rubs.py` finds no
  notes a sixth-step or two apart overlapping for a quarter beat or more, in any of the five, and `songmap listen`
  reports no problems or warnings.
- **Sidechain and space.** Pads, basses and stabs duck under the kick (`sc=`); the garage and tech-house stabs have a
  tempo-synced delay.
- **Mastered for contrast.** All five use `master standard lufs=-14 glue=none`: loudness-normalized to the streaming
  norm, with the limiter touching only the loudest peaks, so each drop keeps its lift. (With glue compression at −12
  LUFS the drops measured only about 1 dB above the sections before them; before mastering they stand 5–6 dB clear.)

## Numbers (from each render's `qa.json`)

| Song | Integrated loudness | True peak | Loudest section, and its margin over every other section |
|---|---|---|---|
| Colour Field | −14.5 LUFS | −1.0 dBTP | `peak`, +3.4 dB |
| Two-Step Gold | −14.4 | −1.0 | `chorus_2`, +3.1 dB |
| Escalator | −14.3 | −1.0 | `peak`, +3.4 dB |
| Quasicrystal | −14.3 | −1.1 | `regroup`, +2.5 dB |
| Silver Lift | −14.3 | −1.0 | `drop_2`, +3.3 dB |

None clips, and `songmap listen` reports no problems or warnings for any of them (only the note that a kick-and-bass
intro is bass-heavy, which is the genre).

**Not checked by ear.** Everything above was judged from the score, the automated ear, the rub checker and the
loudness numbers. Whether it grooves is for you to decide.

## Re-render

```bash
songmap render songs/golden_house/01_colour_field.sm -o songs/golden_house/renders/01_colour_field --mp3
python tools/rubs.py songs/golden_house/01_colour_field.sm --min 0.25
```
