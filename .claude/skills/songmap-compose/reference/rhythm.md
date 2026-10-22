# Rhythm: grooves, feel and drums

## Step strings

Each character is one step: `X` accent, `x` hit, `-` soft, `o` ghost, `.` rest, `f` flam, `r` ratchet (two quick hits).
- **The grid.** The number of characters per bar sets it: 16 gives 16ths, 8 gives 8ths, **12 gives 8th-note triplets (swing and shuffle)**, and 24 gives 16th triplets.
- **Several bars.** `|` starts the next bar; the lane loops over all its bars, so a 4-bar pattern can vary in bar 4.
- **Exact velocities.** `{steps: "x.x.x.x.", vel: [0.6, 0.3, 0.5, 0.3]}` gives each hit its own velocity, cycling the list.
- **Kit pieces:** `kick snare clap hat ohat hat16 fill ghost rim`. A beat is a map of lanes: `{kick: "...", snare: "..."}`. Add it to a style to layer lanes (`full + {ohat: "..x...x...x...x."}`), or set one lane (`drums.kick = "..."`).

## Feel: what makes drums sound played, not programmed

1. **Shape the hats.** Velocities should follow the beat (strong on the beat, weaker off it, a lift before the backbeat), never all the same.
2. **Ghost notes** (`o`) on the snare just before or after the backbeat: the groove gets a pulse.
3. **Swing.**
   - `groove swing=.56/16` swings 16ths and `swing=.58/8` swings 8ths (0.5 is straight, 0.66 is a full triplet shuffle).
   - `tpl=push|laid_back|mpc|dilla` adds a groove template; `feel snare offset=6` lays one player back.
   - A hard triplet shuffle can also be written on the 12-step grid: `x.xx.xx.xx.x`.
   - The mood adds human timing and velocity on top (the kick stays tight).
4. **Push.** A kick or bass a 16th before the beat (step 16 of the previous bar) anticipates and propels.
5. **Vary every 4 or 8 bars.** Use a multi-bar lane (`"…|…|…|x..x..x.xxxxxxxx"`), a fill (`bar -1: drums.snare = "........xxxxXXXX"` in a form block), or drop the kick for a bar before a section change.
6. **Lock bass to kick.** Bass notes land on the kick hits, and the bass rests where the kick rests.
7. **Space is rhythm.** A bar of only hats, or a 2-beat stop (`!stop:2b`) before a hit, says more than more notes.

Every drum hit also varies slightly in tone (each instrument's `rr` round-robin), so repeated hits are never identical.

## Groove library

All are 4/4. Use the tempo in brackets; at 30 fps the whole-frame tempos are 60, 72, 75, 90, 100, 120, 150 and 180.

```sm
house = {kick: "X...x...X...x...", clap: "....X.......X...", hat: {steps: "..x...x...x...x.", vel: [0.5, 0.45, 0.55, 0.4]}, ohat: "..........x....."}
pocket = {kick: "X.....x...x.....", snare: "....X..o....X.o.", hat: {steps: "x.x.x.x.x.x.x.x.", vel: [0.55, 0.3, 0.45, 0.3, 0.55, 0.3, 0.45, 0.35]}}
halftime = {kick: "X.........x.....", snare: "........X.......", hat: {steps: "x.x.x.x.x.x.x.x.", vel: [0.45, 0.25, 0.35, 0.25]}}
boombap = {kick: "X.......x.x.....|X.......x...x...", snare: "....X..o....X...", hat: {steps: "x.x.x.x.x.x.x.x.", vel: [0.5, 0.3, 0.45, 0.28]}}
shuffle = {kick: "x.....x..x..|x.....x.....", snare: "...X.....X.o", hat: {steps: "x.xx.xx.xx.x", vel: [0.5, 0.25, 0.45, 0.22]}}
drive = {kick: "X...x...X...x...", snare: "....X.......X...", hat16: {steps: "xxxxxxxxxxxxxxxx", vel: [0.5, 0.2, 0.35, 0.2]}}
ballad = {kick: "X.......x.......", snare: "........-.......", hat: {steps: "x...x...x...x...", vel: [0.35, 0.25, 0.3, 0.25]}}
grooves 8 | drums:house
```

| Groove | Tempo | Use |
|---|---|---|
| `house` | 120 | upbeat, product, explainer energy |
| `pocket` | 100–120 | warm explainer, pop |
| `halftime` | 120 (feels like 60) | cinematic, calm but moving |
| `boombap` | 90 | hip-hop, documentary cool |
| `shuffle` | 90 | lo-fi, nostalgic, playful (12-step swing) |
| `drive` | 120–150 | action, urgency |
| `ballad` | 60–90 | reflective, emotional |

Built-in styles: `four_floor full half half_kick`, with mods `+fill` (a roll every 8 song bars), `+hats16`, `+open` and `+ghosts`.

## Builds and drops

- **Build (4–8 bars):**
  - raise `dyn` (`dyn=p<f`);
  - densify the snare from quarters to 8ths to 16ths: `"x...x...x...x...|x.x.x.x.x.x.x.x.|xxxxxxxxxxxxxxxx|xxxxxxxxXXXXXXXX"`;
  - thin the hats in the last bar;
  - end with `!riser:2` into the drop.
- **Drop:** `!impact` on the downbeat, everything enters together, `dyn=f`.
- **Breakdown:** drums out, or hats only. Keep the bass or pad so the harmony carries.
- **Euclidean rhythms** spread hits evenly: `euclid(3, 8)` is a tresillo, `euclid(5, 16)` a bossa-like pulse. Good for hats and percussion that should feel organic and unusual: `drums.hat = euclid(5, 16)`.

## Bass rhythm (rel mode, `oct: -2`)

```sm
basslines 4 | bass:{rel: "R/4. R/8 r/8 5/8 R+/4", oct: -2}
```

| Pattern | Feel |
|---|---|
| `R/4. R/8 r/8 5/8 R+/4` | lands with a `pocket` kick: warm pop |
| `R/8 R R+ R R R+ R 5` | driving 8ths (like the `eighths` style) |
| `R/2 5/4 R+` | half-time, cinematic |
| `R/4. r/8 5/4~ R` | lo-fi, with a slide (`~`) into the root |
| `R/1` | a held root: calm, or under a build |

## Arpeggio patterns (`arp:up(order=[...])`)

`order` indexes the chord's tones; past the last tone it wraps to the next octave (3 is the root an octave up).

| Order | Feel |
|---|---|
| `[0, 1, 2, 1]` | rocking, gentle |
| `[0, 2, 4, 2]` | wide, bright |
| `[0, 2, 1, 3, 0, 2, 4, 3]` | busy, a 2-bar figure |
| `[4, 3, 2, 1]` | falling, wistful |

`arp:dark` is the same figure with the filter closed: use it for tension and intros.
