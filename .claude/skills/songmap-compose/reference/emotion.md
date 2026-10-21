# Emotion → music: recipes

Start from what the viewer should *feel*, then choose the musical means. Every row uses only what the engine has now. Combine rows across a piece: an arc of contrasting moods is what makes a score feel composed rather than looped.

## Recipes

| Feeling | Key / mode | Harmony | Rhythm and tempo feel | Palette and register | Dynamics and devices |
|---|---|---|---|---|---|
| **Hopeful, curious** | major (D, G, C) or lydian for wonder | I–V–vi–IV, I–iii–IV–V; add9 and maj7 colour | moderate motion: 8th-note guitar or piano ripples, light pocket groove | keys (piano), gtr (string_pluck), pad:warm; melody in octave 5 | `dyn=p<mf` arcs; a rising melody that ends on a pickup |
| **Triumphant, achievement** | major | I–IV–V–I, IV–V–vi, bVI–bVII–I (borrowed, epic) | four_floor or full drums, 8th bass, open hats | lead doubled by keys an octave below, pad:warm, arp:up | `dyn=f<ff` once, `!impact(size=xl)` on the arrival, `!riser:2` into it |
| **Tense, suspense** | minor, phrygian (bII), harmonic minor (V7) | a static chord or pedal, i–bII, chromatic i–bVI–V | half-time or a heartbeat kick, ticking 16ths (`fx:ticks`), little melody | pad:dark, arp:dark with a narrow `order`, sub bass | `dyn=pp<mp` long crescendo; a riser into the release; a stop (`!stop:2b`) just before it |
| **Dark, ominous** | minor, phrygian | i–bVI–bVII–i, i–iv with m7b5 | slow, sparse: half_kick, long notes | sub bass (`bass:sub`), pad:dark, organ low and quiet | `dyn=pp`/`p`; few events; low register |
| **Mysterious, wonder** | lydian (#4), dorian | Imaj7–II (lydian), sus2/sus4 chords that don't resolve | floating: no drums or only hats, arpeggios on euclid rhythms | arp:dark, epiano bells high, pad:dark | `dyn=p`, an unresolved last chord |
| **Melancholy, reflective** | minor, dorian | i–VI–III–VII, iv–i, ii–V–i with 9ths | slow or half-time, lots of space; a 12-step shuffle for lo-fi | keys (soft: `hardness=.3`), epiano with tremolo, sparse bass | `dyn=p>pp`; long notes; rests between phrases |
| **Calm, focused (background)** | major or dorian | two chords alternating (I–IV, i–IV in dorian) | steady and quiet: soft hats, no fills | pad, epiano, soft gtr | `dyn=p` steady; no impacts; let it loop |
| **Playful, light** | major, mixolydian (bVII) | I–IV–bVII–IV, short chords | staccato (`'`), syncopated plucks, a shuffle | gtr high (`brightness=.8`), pluck/arp, `zaps` for list items | `dyn=mp`; small accents (`^`), grace notes |
| **Urgent, action** | minor | i–bVI–bVII–i, fast harmonic rhythm (1 bar per chord) | 16th hats (`+hats16`), driving 8th bass, fills every 4 bars | arp:up, bass:eighths, full drums | `dyn=mf<f`, risers every 8 bars, impacts on cuts |
| **Warm, human, nostalgic** | major or dorian | I–vi–IV–V with 7ths, Imaj7–IVmaj7 | shuffle on the 12-step grid, brushed (soft) snare ghosts | keys or epiano, gtr, round bass (`cutoff=500`) | `dyn=mp`; anticipated chords; a slide in the bass |
| **Caveat, honesty, limits** | same key, but sus or unresolved | sus2/sus4 or an add9 held; deceptive V–vi | drums out; one or two instruments | pad:dark, solo keys | drop at least 6 dB (`dyn=pp`), a falling line ending on the 2nd degree |
| **Reveal, landing** | — | arrive on I (or the Picardy major I in a minor key) | a stop before it (`!stop:2b@-1:3`), then everything at once | everything enters together | `!impact` on the frame, riser ending on it, `dyn=f` |

## Arcs for a 1–3 minute video

- **Explainer:** curious intro (sparse) → problem (tension rises) → idea (energy builds) → result (triumphant peak) → caveat (drop) → summary (warm, mid energy) → end card (resolve, fade).
- **Story/profile:** reflective intro → warm theme → growth (layers enter, one per scene) → emotional peak (melody up an octave, fullest texture) → quiet coda with the theme alone.
- **Product/demo:** a hook in the first bars → steady pulse under the demos (calm, focused) → a lift for each key feature (impact plus a new layer) → the biggest moment at the call to action → a short tail.

**Rules for arcs:**
- **Pace the peak.** Spend the loudest moment once, about 70–85% of the way through.
- **Contrast neighbours.** Make adjacent sections differ by at least 4–6 dB or by a clear texture change.
- **Earn the drop.** A quiet section before the biggest one makes the big one feel bigger.

## Small recipes

A caveat bar after a full section: drums out, a held sus chord, the pad quiet.

```sm
peak     8 | drums:full+fill bass:eighths arp:up pad:warm dyn=f
caveat   2 | pad:dark keys:{rel: "[R,5,9]/1"} chords="Asus4:2" dyn=pp
```

A reveal on an exact frame: the riser lands on it, and the band stops for two beats before it. Here the reveal lands at f255, which is bar 4, beat 2 at 120 BPM and 30 fps.

```sm
cue landed=f255
build    4 | drums:full bass:eighths arp:up dyn=mf<f         | !stop:2b@+3:3
reveal   4 | like=build pad:warm dyn=f                       | !riser:2@cue:landed !impact@cue:landed(size=xl)
```
