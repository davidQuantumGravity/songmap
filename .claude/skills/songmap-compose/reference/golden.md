# Golden harmony in a Western song (36-ET)

Golden chords are stacked golden thirds: 11 sixth-steps, 1/3 semitone flatter than a major third. They live in
`tuning=36edo` (on the `song` line). Theory: `docs/GOLDEN_THEORY.md` and `docs/GOLDEN_BLENDING.md`. Five worked songs,
each built on one technique below, are in `songs/golden/`.

## Spelling

| Write | Meaning |
|---|---|
| `Cg`, `Cg7` | golden triad, golden seventh (the golden 7th is exactly a 12-ET major 7th) |
| `Cs`, `CT13` | silver (0-10-20), bronze (0-13-26) |
| `^C`, `vEb`, `^F#m` | roots a sixth-step up or down; also on notes and degrees: `^c4`, `v3/4` |
| `Am(^3)`, `C(v3,^5)` | alterations by sixth-steps |
| `~`, `~g` in a progression | a placeholder the passing engine fills: `~` = strict (one golden chord), `~g` = natural (two in a row) |
| `vCg/G` | slash chords work as usual |

## Golden scales and modes (for `key=` and deg notes)

`key="C golden7"` (C C# vE vF ^G ^Ab B), `golden10`, `golden13`, `golden_penta` (C D vF ^G ^A). The modes of golden7 and
golden10 are named by their chain window b|a (textbook Chapter 36): `golden7_60` (brightest) … `golden7_33` (= golden7, the
golden Dorian) … `golden7_06` (darkest); `golden10_36` is the "35" decatonic, `golden10_63` the "53". Inside one golden
scale no two notes are a sixth-step or two apart, so a deg melody in it can't make a microtonal rub with its own chords.
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
   then `key=^Eb` re-keys the theme. For a golden home, switch to `clean/golden_pad` and `clean/glass` and breathe along
   the circle (`^Ebg ^Ebg7 Gg Gg7 ...`), then return through a Western visitor (`Gg G7 | C`).
   Golden giant steps: `C:1 ~:0.5 Ab:1 ~:0.5 E:1 ~:0.5 C:1.5`.

## Rules that keep it tasteful

- **Short and weak.** Passing golden chords take one beat or less, on beats 2 or 4. Colour chords take half a bar.
  Save long golden stretches for golden timbres.
- **The melody never sits on a golden clash.** On a golden chord it rests, or holds a tone the chord keeps: C over vFg/C,
  F over Fg, E over Eg and vAg. Writing the melody in `rel:` mode makes it follow the golden chord automatically.
- **Everything that sounds must change chord with it.** Use the voiced styles (`hold`, `comp`, `pulse`, `bassline`,
  `top`) or `rel:` figures. A `pad:warm` or a whole-bar `rel` pad keeps ringing the old chord into the golden one. Give
  comping a strike where a colour chord starts, or the bend goes unheard.
- **Write figures a full bar long.** A `rel:` figure shorter than a bar is padded with rest to a whole bar, not repeated:
  `"[R,3,5]/2"` strikes once per bar and misses a chord change on beat 3. Write `"[R,3,5]/2 [R,3,5]"`.
- **Section ends.** A `~` at the end of a progression resolves toward the progression's *first* chord, because it loops.
  Spell the golden chords out (`vCg/G`) when the next section starts somewhere else.
- **Stable instruments.** `keys/still`, `epiano/still`, `pad/still`, `string_pluck/still`, `clean/*`, and `master clean`.
  Detune, drift and tremolo smear sixth-steps.
- **Check for rubs.** `python tools/rubs.py song.sm --min 0.25` lists notes 33 or 67 cents apart that overlap. Fix
  everything except one-beat golden chords over a held bass (the "golden six-four" pedal, which the theory treats as idiomatic).
  `--semis` also lists semitone clashes.

## Levels (measured in these songs; adjust from `qa.json` stems)

`epiano/still` and `pad/still` run hot: start them around `-14` and `-24`. `clean/lead` is quiet: start it around `+14` to
`+18`. `clean/glass` doubling a melody at about `-10`, and `clean/golden_pad` alone at about `-12`. Named parts need a
reverb send in the mix line (`hall=.25`).
