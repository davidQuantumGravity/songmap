# Melody: writing motifs and lines that sing

## Scale degrees

| Degree | −3 | −1 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D major | A below | C♯ below | D | E | F♯ | G | A | B | C♯ | D (up an octave) | F♯ |
| D minor (natural) | A below | C below | D | E | F | G | A | B♭ | C | D (up an octave) | F |
| D dorian | A below | C below | D | E | F | G | A | B | C | D (up an octave) | F |

- `#`/`b` before a degree alters it: in a minor key, `#6` is the raised 7th (C♯ in D minor). Use it whenever the chord is the major V (A or A7 in D minor), or the melody clashes with the chord.
- The key's mode decides the degrees (`song ... Dm`, `"D dorian"`). A section's `key=D` re-keys its inline deg notes, which is the Picardy or major-reprise move.

## Writing notes

There are two ways to write pitches:
- **deg mode:** scale degrees of the key; 0 is the tonic. Use it for melodies.
- **letter mode:** `c d e f g a b`, with `#`/`b`, and `+`/`-` for an octave up or down. `c` is C4.

**Durations:**
- **Values:** `1 2 4 8 16 32` (whole to 32nd), with `.` for dotted and `t` for triplet.
- **Where they go:** in deg mode after a slash (`0/4`, `2/8.`, `4/8t`); in letter mode directly (`a4`, `c+8.`).
- **Sticky:** a note without a duration repeats the last one, so `0/8 2 4 2` is four 8ths.
- **Bar lines:** write `|` between bars. **Every bar must add up to the meter**, and `check` counts it only when bars are written: notes without `|` are not checked.

Count every bar:

```
"=mp 4/8 2 0/4 2/8 4 5/4 | 5/4. 4/8 2/2"
bar 1: 4/8 (.5) + 2 (.5) + 0/4 (1) + 2/8 (.5) + 4 (.5) + 5/4 (1) = 4 ✓
bar 2: 5/4. (1.5) + 4/8 (.5) + 2/2 (2)                       = 4 ✓
```

**Expression inside the line.** Marks go **after** the note and its duration: `4/4^`, `0/8'`, `c4^`, `R/8^`. A `^` before a note is reserved for microtones and is an error. Marks belong to one note, while durations are sticky, so `0/8' 2' 4'` is three staccato 8ths.

| Mark | Meaning |
|---|---|
| `=pp =p =mp =mf =f =ff` | set the level |
| `<` `>` | a hairpin to the next level, e.g. `=p 0/4 < 2 4 5 =f` |
| `^` | accent (louder) |
| `'` | staccato (short) |
| `_` | tenuto (full length) |
| `~` | slur into the next note (a glide on the mono lead and bass) |
| `(2/8)` | a ghost note (very soft) |
| `{5}4/4` | a grace note before the main note |
| `@100` | an exact velocity |
| `r` | a rest, e.g. `r/4` |

## Placing a melody

Keep the notes in a **variable** and give them to a part as **inline notes**. They start with their section and loop to fill it:

```sm
q = "=mp 4/8 2 0/4 2/8 4 5/4 | 5/4. 4/8 2/2"
a = "=mf 7/4. 6/8 5/4 4 | 4/2 r/4 2"
tune = {deg: q + " | " + a, oct: 1}
verse 8 | keys:tune pad:warm
```

- **Octave.** `oct: 1` puts degree 0 in octave 5 (the default is 4); `oct: 0` keeps octave 4.
- **Key.** A section's `key=` re-keys its inline deg notes.
- **The other placement (avoid).** `motif m1 deg "..."` with `lead:m1,m2` *cycles motifs in blocks anchored at bar 0 of the song*. A section that doesn't start on a multiple of the cycle begins mid-motif. Use it only when sections are aligned. Inline notes are safer.

## Designing a motif

- **Short and recognisable.** One or two bars, with one rhythmic idea (a dotted figure, a syncopation, a repeated note) and one memorable interval (a leap of a 4th, 5th or 6th, then stepwise motion back).
- **Contour.** Arch (up then down) for completion, rising for hope and questions, falling for resolution, sadness or a caveat. Mix them across phrases.
- **Chord tones on strong beats** (beats 1 and 3), passing and neighbour tones on weak beats. Check each strong-beat note against the chord sounding there.
- **Range.** Stay within an octave and a half per phrase. The climax note (the highest) comes once, late, on a strong beat.
- **Breathe.** End phrases with a long note or a rest. Leave at least half a bar of space every 2–4 bars, so another instrument can answer.
- **Rhythm before pitch.** A strong rhythm with three pitches beats a weak rhythm with ten.

## Phrase structure

- **Question and answer** (2+2 or 4+4 bars): the question ends on an unstable degree (2, 4 or 6, or on V), and the answer ends on the tonic (0) or the 3rd (2).
- **Sentence** (1+1+2): a one-bar idea, the same idea varied, then a two-bar continuation that runs to the cadence.
- **Antecedent → consequent across sections:** the verse asks and the chorus answers.

## Developing it by hand (no transform syntax yet)

Write each variation as its own note string:

| Device | How | Example from `0/8 2 4/4 2/2` |
|---|---|---|
| **Sequence** (moving it up the scale: a lift) | add the same number to every degree | `1/8 3 5/4 3/2` |
| **Rhythmic augmentation** (grand, slow) | double every duration | `0/4 2 4/2 2/1` (now 2 bars) |
| **Fragmentation** (urgency, a question) | repeat only the head | `0/8 2 0 2 0/8 2 4/4` |
| **Inversion of contour** (mirror, doubt) | flip the direction of each step | `0/8 -2 -4/4 -2/2` |
| **Octave displacement** (a climax) | the same notes, `oct` + 1 | `{deg: ..., oct: 2}` |
| **Re-harmonisation** (new meaning) | the same melody over new chords | `chords="F G Em Am"` on the section |

## Counter-melody and call and response

- **Counter-melody:** longer notes against a busy melody (or a busy line against a long one), mostly in contrary motion, and in a different register (keys under lead, gtr above pad).
- **Call and response:** the lead plays bars 1–2 and rests for bars 3–4 while a second instrument answers in bars 3–4.

```sm
call = {deg: "=mf 0/8 2 4/4 2/2 | r/1", oct: 1}
reply = {deg: "r/1 | =mp 4/8 2 0/4 -1/2", oct: 0}
talk 4 | lead:call keys:reply pad:warm
```

## Ranges (MIDI; C4 = 60)

| Part | Comfortable range | Default octave |
|---|---|---|
| bass | 28–55 (E1–G3) | rel `oct: -2` |
| keys (piano) | 48–84 for melody, 43–72 for chords | |
| epiano, organ | 48–79 | |
| gtr | 40–84 | |
| lead | 60–88 | `oct: 1` (deg 0 in octave 5) |
| pad | chords 48–76 | |

A melody an octave above its accompaniment stays clear.
