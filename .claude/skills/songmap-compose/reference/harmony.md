# Harmony: chords, progressions, voicings

## What the engine understands

- **Chord symbols:** a root `C`–`B`, with `#` or `b`, then a quality:

  | Quality | Symbols |
  |---|---|
  | major | (nothing) |
  | minor | `m` |
  | 7ths | `7`, `maj7`, `m7`, `m7b5`, `dim7` |
  | 6ths | `6`, `m6` |
  | suspended | `sus2`, `sus4` |
  | added 9th | `add9`, `madd9` |
  | 9ths | `9`, `maj9`, `m9` |
  | other | `dim`, `aug`, `5` |

  `N.C.` means no chord: chord parts rest. A slash bass (`C/E`) is accepted, **but bass parts still play the root.** For an inversion in the bass, write the bass line in notes instead.
- **The song's progression** is `chords Am F C G /2`, where the number is bars per chord. It loops from bar 0 straight through every section that doesn't set its own.
- **A section's own progression** is `chords="Am:2 F:1 G:1"` on a section line, or `chords = "..."` under a form line; each number is that chord's length in bars. It starts at the section start and loops to fill the section.
- **Harmonic rhythm** is how often chords change. One chord per 2 bars feels calm, one per bar is moving, and two per bar is urgent. Change it between sections for contrast.
- **Which parts follow the chords:** `pad:` (holds a **triad** per chord change), `arp:` (arpeggiates the chord's tones), `bass:` styles (play the root) and any part written in **rel mode** (chord-relative notes, below).

## Rel mode: voicings that follow the chords

A rel part names chord tones instead of pitches:
- `R` is the root;
- `3 5 7` are the chord's own 3rd, 5th and 7th (a minor chord's 3 is minor; on a major triad, 7 is major unless the symbol says `7`);
- `9` is the 9th, and `2 4 6` are the major-scale 2nd, 4th and 6th above the root (on C: D, F, A; add `b` or `#` to alter: `b6`);
- `+`/`-` move a note an octave: `R+`, `5-`;
- `[ ]` makes a chord.

Durations are written as in deg mode (`/2`, `/4.`, `/8t`), and the pattern loops through the section, re-voiced on every chord. `oct=` moves the whole part: rel `R` sits near the key's tonic, around C4.

```sm
voicings 4 | pad:{rel: "[R,3,5,7]/1"} keys:{rel: "[5-,R,3]/2 [3,5,R+]"} epiano:{rel: "[3,7,9]/1"} bass:{rel: "R/2 5", oct: -2}
```

- `[R,3,5,7]` is a full 7th chord: **`pad:warm` and `pad:dark` play triads only**, so write this for 7ths and 9ths.
- `[5-,R,3]` is second inversion (5th in the bass), and `[3,5,R+]` is first inversion. Moving between inversions makes **smooth voice leading**.
- `[3,7,9]` is a rootless voicing (jazz and lo-fi colour). Let the bass play the root.
- `[R,5,9]` is open and modern; with no 3rd it is neither major nor minor, which suits caveats and wonder.

## Progressions by feeling

In C major / A minor; any key works the same way.

| Feeling | Progression | Notes |
|---|---|---|
| hopeful, pop | `C G Am F` (I–V–vi–IV) | Familiar; vary the order (`Am F C G`) to sound less stock |
| warm, open | `Cmaj7 Fmaj7` or `C Am7 Fmaj7 G` | maj7 and m7 soften everything |
| uplifting build | `F G Am` → `F G C` | IV–V–vi then IV–V–I: a deceptive turn, then the real resolution |
| epic, cinematic | `Am F C G`, `Am Fmaj7 G Esus4 E` | Minor with borrowed brightness; sus4→3 on V is a strong pull |
| heroic arrival | `F G C` with `Ab Bb C` (bVI–bVII–I) | Borrowed from the minor key: big, film-score |
| melancholy | `Am Dm Am E7` (i–iv–i–V7), `Am7 Dm9 G7 Cmaj7` | The harmonic-minor V7 (E7 in A minor) aches toward i |
| dark | `Am F Dm E7`, `Am Bb` (i–bII, phrygian) | bII is menace; keep the voicings low |
| tension, suspense | a long `Am` or `Am Bb`, `Am Ab` (i–bVI chromatic) | Static harmony plus a crescendo builds suspense |
| wonder (lydian) | `C D/C` written `C D` (I–II) | The major II gives the raised 4th; float, don't resolve |
| dorian groove | `Dm7 G7` or `Dm9 G` (i–IV major) | The major IV is dorian's colour: cool, not sad |
| mixolydian, rock | `C Bb F C` (I–bVII–IV–I) | Bright but earthy |
| jazz, lo-fi | `Dm9 G7 Cmaj9 Am7` (ii–V–I–vi) | Use rootless rel voicings and a shuffle |

## Cadences: how phrases end

| Cadence | Example | Effect |
|---|---|---|
| Authentic | V–I (`G C`, `E7 Am`) | Closure. End of a song or a section |
| Plagal | IV–I (`F C`) | Warm, "amen"; a gentle ending |
| Picardy | minor → its major I (`E7 A` in A minor) | A dark piece ends in light; use it for a "verified" moment |
| Half | ends on V (`... G`) | A question; keeps things moving. Phrase ends mid-song |
| Deceptive | V–vi (`G Am`) | A surprise or a caveat; avoids closure |
| Suspended | V held as `Gsus4`, or ending on `Csus2` | Hanging, unresolved; mystery or honesty |

The end of a section is a cadence, so choose it deliberately. Before a big entrance, end the previous section on V (or on a sus4 that resolves on the downbeat of the new section).

## Craft rules

- **Change and contrast.** Change something between sections: the progression, the harmonic rhythm or the voicing. The same four chords for three minutes is the most common "robotic" tell.
- **Pedal point.** Hold the bass on one note while chords move above it (write the bass in letter notes, not rel): tension that builds without changing key.
- **Modal mixture.** Borrow one chord from the parallel key for emotion: iv in major (`Fm` in C) is bittersweet, and bVI–bVII–I is triumphant.
- **Voice leading.** Upper voices move by step or stay put. In rel parts, pick inversions so each tone moves as little as possible from one chord to the next.
- **Register.** Keep chords between about C3 and C5. Below C3, chords turn to mud, so leave that to the bass.
- **Melody and chord.** Chord tones on strong beats, passing tones between them (see melody.md). A melody note a half step above a chord tone, held on a strong beat, clashes: check the progression under each held melody note.
