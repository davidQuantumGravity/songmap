# Golden Cathedral

`as_above_so_below.sm` is a five-minute golden-harmony fantasia for organ, an instrumental choir of cello, horn and flute, golden-spectrum chimes, and chord-following binaural pairs. Its 72 bars at 60 BPM last 4:48; the decay lasts twelve seconds.

The form moves from a seven-note home through golden ninths and a neighboring decatonic key, pauses in a bare chamber, then opens into its largest sonority before returning to a triad. The writing borrows the staggered entries, breathing phrases and spaciousness of sacred polyphony; it is an imagined golden cathedral rather than a historical Renaissance reconstruction.

The binaural layer is an artistic headphone effect. The arithmetic center of each left/right pair is an octave reduction of an upper harmony note. The beat difference is five more octaves below its own center: `difference = carrier_hz / 32`, with `beat=octave octaves=5`. Thus 220 Hz produces 6.875 Hz, and every other note changes its difference proportionally. The shared divisor stays fixed through chords and key changes; carrier-list ordering has no effect. The differences span 4.0879–11.7871 Hz. Each ear is offset by half its pair's difference, with short carrier crossfades. Several simultaneous pairs also have ordinary acoustic interactions; this is not evidence of a neurological effect.

Golden sevenths stack three golden thirds; golden ninths stack four. The score writes the latter as `maj9(v3,^5,^^9)`, giving 36-ET intervals of 0, 11, 22, 33 and 44 sixth-steps. It does not use an unaltered Western ninth. The upper additive instruments use exact `2^m * phi^n` partial ratios on 36-ET fundamentals. The underlying tuning is tempered, not exact phi throughout.

Use stereo headphones at a comfortable level. The larger late sections gain their scale from register, counterpoint and harmonic density. Turning up the playback level is unnecessary.

Listening status: the user approved the original composition ("That was great"). The instrumental events are unchanged; the corrected note-derived headphone layer awaits a new listening verdict. Numerical and score checks remain separate from that verdict and do not establish a physiological effect. The former fixed-rate score and full/pair MP3s are preserved under `archives/binaural_fixed_rate_20261024/golden_cathedral/`.

Open [the synchronized player](http://127.0.0.1:56855/songs/golden_cathedral/) for the full piece, the instrumental bed and isolated binaural pairs. It shows the played notes for six instruments, the current harmony, and the predicted left/right frequencies. The comparisons retain the same clean-master gain. The instrumental comparison precedes the carrier notches, so summing the two comparisons does not reconstruct the full mix. When stems are exported, `stems/binaural.wav` is the subtractive difference stem; `binaural_pairs.wav` is the isolated positive layer. The old cached difference stem was removed after the correction; regenerate it with a normal render if needed.

The corrected render measures 300 seconds, -20.67 LUFS and -1.99 dBTP, with no clipped samples. Every planned difference is checked as its carrier / 32; steady left/right frequencies are also measured directly in the isolated audio. The horn was reduced 10 dB from the first render, and organ voicings were respaced around the independent voices. All sampled lines fit their recorded ranges. One brief close suspension at 0:43 is prepared by unison and resolves in the next bar; no accidental held 33- or 67-cent collision remains in the written events.

The automated ear's late-peak contrast advisory is retained intentionally: 3:44-4:16 is one broad wave, with its final crest at 4:00 rather than a second sudden level jump. Its bass-balance note at the still point reflects the deliberate removal of most upper voices.

To reproduce from the `SongMap` project directory:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m songmap.cli check songs/golden_cathedral/as_above_so_below.sm
.\.venv\Scripts\python.exe -X utf8 tools/package_golden_cathedral.py --render
.\.venv\Scripts\python.exe -X utf8 tools/check_golden_cathedral_browser.py
```

The binaural rates are musical choices, not a demonstrated neurological optimum. [Orozco Perez et al. (2020)](https://www.eneuro.org/content/7/2/ENEURO.0232-19.2020) measured auditory responses in a controlled binaural/monaural comparison without a corresponding self-reported mood effect.

`--render` packages directly from in-memory stems without writing large float WAV intermediates. To export all fresh stems as well, use the normal `songmap render` command and then run the packaging helper without `--render`. The displayed comparisons and verification receipts always refer to the current octave-derived render.
