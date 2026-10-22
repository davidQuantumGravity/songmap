# Still Water: five songs on the golden beat ladder

A suite of five songs, about eighteen minutes in all, built from the bliss conjecture of the textbook's Chapter 41.
Each song is ordinary music on its surface: piano, harp, strings, a golden-spectrum pad, glass bells, no drums. Under
it, all the way through, runs a binaural layer: pure tones a few hertz apart in the two ears, pitched on the chords'
own notes so that they hide inside the harmony. Chapter 48 of the textbook (*Still Water*) features each song with a
listening guide, excerpts and the design; the songs are also in the Songbook (appendix H) for review.

**Listen on headphones,** at a moderate level, in order, without doing anything else. Binaural beats exist only on
headphones. If you have epilepsy or are sensitive to rhythmic stimulation, be cautious with any sustained pulsing
sound. The design comes from a hypothesis (Chapter 41); nothing here promises a state of mind.

| # | Song | Harmony | Hidden layer: carriers | Beats (Hz) | Tempo | Length |
|---|---|---|---|---|---|---|
| 1 | [Dusk on the Water](01_dusk_on_the_water.sm) | A major | A3, E4 | 16.18 and 10 slowing to 10 and 6.18 | 60 → 54 | 3:33 |
| 2 | [The Slow Tide](02_the_slow_tide.sm) | A major turning golden (D → vDg) | A3, E4 → A3·φ | 10 and 6.18 slowing to 6.18 and 3.82 | 54 → 48 | 3:43 |
| 3 | [Deep Water](03_deep_water.sm) | golden: vDg, ^Fg, vDg7, A#g | A3, A3·φ, A3·φ² → A4/φ | 6.18, 3.82, 2.36 | 44 | 3:57 |
| 4 | [Moon on the Water](04_moon_on_the_water.sm) | golden: Ag, Ag7, ^Fg7 | A3, A4/φ, A5/φ² | 10, 6.18, 3.82 (the ch41 ladder) | 48 | 3:38 |
| 5 | [First Light](05_first_light.sm) | Ag opening into A major | A3, A4/φ, A5/φ² → A3, E4 | 10 and 6.18, then up to 16.18 | 48 → 56 | 3:05 |

## How the layer hides

- **One thread.** The A3 pair (220 Hz) never stops: each song starts with the carriers and beat rate the previous one
  ended on, so the five files play as one continuous layer.
- **Carriers are chord tones.** While the harmony is Western the second carrier is E4; when it turns golden the
  carriers move to the golden chain (A3·φ = 355.97 Hz = ^F4, A3·φ² = 575.97 Hz = vD5, A4/φ = 271.93 Hz = vC#4,
  A5/φ² = 336.13 Hz = ^E4), always tones of the chords sounding. `songmap listen` checks it: a carrier a sixth-step
  from a chord tone is a problem; a half step (a pedal point) is a note.
- **The music makes room.** Around each carrier the engine removes a narrow band of the music (`carve`), so that no
  held note at the carrier's own pitch beats against the detuned ear tones. The pair replaces the music's tone there:
  in Deep Water the three carriers are exactly the first, second and fourth partials of the golden pad's A3.
- **Golden at every scale.** Beat rates step down the ladder 10·φ^k (16.18, 10, 6.18, 3.82, 2.36 Hz), each the
  difference of the two above it; the bells of songs 3 to 5 fall on a Fibonacci-word rhythm that never repeats a
  bar; songs 3 and 4 use golden-spectrum timbres; section lengths are 5, 8, 13 and 21 bars.
- **Breath.** Two-bar phrases slow from 8 s to 11 s (7.5 to 5.5 a minute) and come back to 8.6 s; the layer swells
  once per phrase.

## Numbers (from each render's `qa.json`, and a 10 s window in one section of each song)

| Song | Integrated loudness | True peak | Loudest section, margin over the next | Ear separation WAV / MP3 | Music left at a carrier |
|---|---|---|---|---|---|
| Dusk on the Water | −23.0 LUFS | −1.3 dBTP | `homeward`, +4.1 dB | 72 / 54 dB | −65 dB |
| The Slow Tide | −23.0 | −7.5 | `undertow`, +3.5 dB | 82 / 55 dB | −85 dB |
| Deep Water | −23.0 | −10.6 | `depth`, +0.5 dB | 87 / 47 dB | −69 dB |
| Moon on the Water | −23.0 | −11.4 | `bloom`, +1.4 dB | 86 / 67 dB | −52 dB |
| First Light | −23.0 | −1.4 | `morning`, +2.9 dB | 59 / 57 dB | −79 dB |

All five are mastered to −23 LUFS (EBU R128) without glue compression, so they play in sequence at one level; none
clips. "Ear separation" is how far a left-ear tone is below itself in the right channel (and vice versa); "music left"
is the music at a carrier's centre frequency relative to that carrier, after carving. Songs 3 and 4 are deliberately
even (a 4 and 5.4 dB section range): they are the stillest.

**Not checked by ear.** Everything above was judged from the score, the automated ear and measurements. Whether it
sounds good, and whether it does anything for a listener, is for you to decide.

## Re-render

```bash
songmap render songs/still_water/01_dusk_on_the_water.sm -o songs/still_water/renders/01_dusk_on_the_water --mp3
songmap listen songs/still_water/01_dusk_on_the_water.sm
```

Renders go to `renders/` and aren't committed. The MP3 is written with separate left and right channels (no joint
stereo) whenever a song has a binaural layer.
