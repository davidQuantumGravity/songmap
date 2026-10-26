# Golden harmony in a Western song (36-ET)

Golden chords are stacked golden thirds: 11 sixth-steps, 1/3 semitone flatter than a major third. They live in
`tuning=36edo` (on the `song` line). Theory: `docs/GOLDEN_THEORY.md` and `docs/GOLDEN_BLENDING.md`. Five worked songs,
each built on one technique below, are in `songs/golden/`.

This reference focuses on Western-led blending. Long golden-home passages can use ordinary instruments; follow the requested pitch/timbre boundary. For the user's melody, balance, suspension and binaural feedback, read [listening-feedback.md](listening-feedback.md).

## Spelling

| Write | Meaning |
|---|---|
| `Cg`, `Cg7` | golden triad, golden seventh (the golden 7th is exactly a 12-ET major 7th) |
| `Cmaj9(v3,^5,^^9)` | verified golden ninth: 0,11,22,33,44 sixth-steps; `g9` is not a supported shorthand |
| `Cs`, `CT13` | silver (0-10-20), bronze (0-13-26) |
| `^C`, `vEb`, `^F#m` | roots a sixth-step up or down; also on notes and degrees: `^c4`, `v3/4` |
| `Am(^3)`, `C(v3,^5)` | alterations by sixth-steps |
| `~`, `~g` in a progression | a placeholder the passing engine fills: `~` = strict (one golden chord), `~g` = natural (two in a row) |
| `vCg/G` | slash chords work as usual |

## Golden scales and modes (for `key=` and deg notes)

`key="C golden7"` (C C# vE vF ^G ^Ab B), `golden10`, `golden13`, `golden_penta` (C D vF ^G ^A). The modes of golden7 and
golden10 are named by their chain window b|a (textbook Chapter 36): `golden7_60` (brightest) … `golden7_33` (= golden7, the
golden Dorian) … `golden7_06` (darkest); `golden10_36` is the "35" decatonic, `golden10_63` the "53". Inside a single golden7 or golden10 collection, no two notes are a sixth-step or two apart, so notes confined to that same collection avoid those particular rubs. This does not establish melodic quality or resolve ordinary semitone suspensions.
`songs/epic/a_comma_higher.sm` walks all seven golden7 modes on C.

## Techniques that blend well (each worked in `songs/golden/`)

1. **Passing chords** (`01`). On a weak beat between I–IV, IV–I, V–I, I–V: `C:0.75 ~:0.25 F:1`. The golden escalator for IV–V:
   `F:0.5 ~g:0.25 ~g:0.25 G:1`. Golden authentic cadence: `G:0.5 vEbT13/G:0.25 vCg/G:0.25 C:1`.
2. **Deceptive sparkle** (`02`). `D:0.75 ~g:0.125 ~g:0.125 Em:1` gives D – vEbg – Ebg – Em, and a `rel:` bass on 8ths
   climbs D – vEb – Eb – E.
3. **Colour chords** (`03`). A diatonic chord bends into its golden projection for half a bar: `Fmaj7:0.5 Fg:0.5`,
   `E7:0.5 Eg:0.5`, `Am:1 vAg:1`. One note stays and two bend by a sixth-step. Golden Picardy: `Am:0.5 Am(^3):0.5 Ag:1 A:1`.
4. **Golden Andalusian** (`04`). `Am:0.5 ~g:0.25 ~g:0.25 G:0.5 ~g:0.25 ~g:0.25 F:0.5 vF:0.25 ^E:0.25 E:1`. Play it plain
   first, so the ear knows the cadence.
5. **Pivot between layers and golden home** (`05`). C major and `^Eb` major share Fg and Gg: `F:0.5 Fg:0.5 ^Fm:1 ^Bb7:1 ^Eb:1`,
   then `key=^Eb` re-keys the theme. For a golden home, optionally use `clean/golden_pad` and `clean/glass` and breathe along
   the circle (`^Ebg ^Ebg7 Gg Gg7 ...`), then return through a Western visitor (`Gg G7 | C`).
   Golden giant steps: `C:1 ~:0.5 Ab:1 ~:0.5 E:1 ~:0.5 C:1.5`.

## Rules that keep it tasteful

- **Passing color or harmonic home.** In a Western-led passage, short golden gestures on weak beats can introduce the color gently. Longer suspensions, golden sections and golden-home pieces are also valid when their preparation, phrasing and destination support them. Their timbres need not have golden spectra.
- **Give golden melodic tones a role.** A rest or shared tone can bridge a chord bend: C over vFg/C, F over Fg, E over Eg and vAg. An explicitly voiced golden melody can also prepare and resolve altered tones. Adjust incompatible accompaniment tones together with the melody. `rel:` follows declared chord tones; absent extensions can fall back to Western intervals, so inspect the expanded pitches.
- **Everything that sounds must change chord with it.** Use the voiced styles (`hold`, `comp`, `pulse`, `bassline`,
  `top`) or `rel:` figures. A `pad:warm` or a whole-bar `rel` pad keeps ringing the old chord into the golden one. Give
  comping a strike where a colour chord starts, or the bend goes unheard.
- **Write figures a full bar long.** A `rel:` figure shorter than a bar is padded with rest to a whole bar, not repeated:
  `"[R,3,5]/2"` strikes once per bar and misses a chord change on beat 3. Write `"[R,3,5]/2 [R,3,5]"`.
- **Section ends.** A `~` at the end of a progression resolves toward the progression's *first* chord, because it loops.
  Spell the golden chords out (`vCg/G`) when the next section starts somewhere else.
- **Pitch clarity.** Stable presets such as `keys/still`, `epiano/still`, `pad/still`, `string_pluck/still` and `clean/*` can expose sixth-step motion. Recorded voices are also valid; inspect their natural vibrato and tuning. Detune and pitch drift can obscure close pitch changes. `master clean` preserves the spectrum without added compression or saturation.
- **Check for rubs.** `python tools/rubs.py song.sm --min 0.25` lists notes 33 or 67 cents apart that overlap. Fix
  everything except one-beat golden chords over a held bass (the "golden six-four" pedal, which the theory treats as idiomatic).
  `--semis` also lists semitone clashes.

## Levels (measured in these songs; adjust from `qa.json` stems)

These are historical faders from the worked examples, not transferable loudness targets: `epiano/still` about `-14`, `pad/still` about `-24`, `clean/lead` `+14` to `+18`, `clean/glass` doubling about `-10`, and `clean/golden_pad` alone about `-12`. Rebalance each voice from its current rendered stem and ensemble context. Do not automatically apply the old lead boost to a lyrical or calming melody; this user found earlier leads too loud and shrill. Named parts need a reverb send when desired (`hall=.25`).
