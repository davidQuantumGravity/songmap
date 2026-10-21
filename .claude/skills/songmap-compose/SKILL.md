---
name: songmap-compose
description: Write, score or revise music with the SongMap engine in this repo. Covers writing a .sm song map for a video or brief, placing hits on exact frames, checking it, rendering song.wav/stems/cues.json, reading QA and revising. Use whenever asked to compose, score, rescore, arrange or edit a soundtrack or song here.
---

# Composing with SongMap

You write **musical decisions as text**, in a `.sm` song map. The engine does the synthesis, mixing and frame-accurate cue export. Never write DSP or edit engine code to change the music. If the engine can't do something, say so and pick the closest thing it can do.

## 0. Setup (once per shell)

From the repo root, activate the venv (`.venv/Scripts/activate` on Windows, `source .venv/bin/activate` elsewhere), or call `.venv/Scripts/python -m songmap.cli` directly.

| Command | What it does |
|---|---|
| `songmap describe --compact` | the catalog: every style, mod, instrument, preset, event and the syntax (~450 tokens) |
| `songmap check song.sm` | parse, validate, expand. Milliseconds. Prints bars, length and frames, or one error per line |
| `songmap render song.sm -o build/x` | `song.wav`, `stems/`, `cues.json`, `qa.json` (about 5–30 s) |
| `songmap fmt song.yaml --to sm` | convert YAML ↔ `.sm` losslessly |

## 1. The loop

1. **Load the catalog, not the engine.** Read [catalog.txt](catalog.txt), the output of `songmap describe --compact`, and use only the names it lists. Anything else is an error, and the error suggests the nearest valid name.
2. **Spot the picture.** List the scenes with their start frames and the moments that must land: reveals, counters landing, stamps, list items. A scene timeline like `docs/SCENE_TIMELINES.md` is ideal. Then convert frames to bars (§2).
3. **Write the `.sm`.** The header comes first, then one line per section (§3). Put section boundaries where the picture changes and events where things land.
4. **Check.** Run `songmap check song.sm` and fix each error exactly as its suggestion says. Repeat until it prints `ok:` with no length warning and the frame count equals the video's.
5. **Render** with `songmap render song.sm -o build/<name>`.
6. **Read QA.** Look at `qa.json` for section loudness contrast, peaks and band balance. Compare quiet and loud sections against your intent.
7. **Revise by replacing whole section lines.** Map feedback in musical terms ("pad too bright in barrier", "bigger hit at 970 M") to a line edit or a parameter, then check and render again.

## 2. Time: frames, bars and positions

- **Frames per bar.** `fps × beats_per_bar × 60 / tempo`, which is 60 at 120 BPM, 4/4, 30 fps (one beat = 15 frames). Bars count from **0**: bar = `frame / frames_per_bar`.
- **Length.** The song is all section bars plus `tail=` **seconds** of ring-out. With `video=Comp:frames` on the `song` line, `check` compares `bars × frames_per_bar + tail × fps` with the video's frames. It prints a warning when they differ by less than a bar and an error beyond that; aim for an exact match.
  - So the bars are `(frames − tail × fps) / frames_per_bar`.
  - If that isn't a whole number, adjust `tail` (it may be fractional: `tail=3.5`) or give the last section a fractional length (`end_card 2.5`).
- **Scene starts.** Round each one to the nearest bar for section boundaries.
- **Off-grid moments** (a counter landing at f1145): define `cue name=f1145` and place `!impact@cue:name`. Cue positions snap to the nearest 16th, and `check` warns if that moves one by more than a frame.
- **Positions** in `@...`:

  | Position | Meaning |
  |---|---|
  | (none) | the start of the section the event is written on |
  | `@+3`, `@+3:2` | 3 bars after this section's start (on beat 2) |
  | `@12`, `@12:3` | absolute bar 12 counted from 0 (beat 3) |
  | `@f735` | video frame 735 |
  | `@cue:name` | a named cue |
  | `@agents+8` | 8 bars into the section `agents` |

  Beats are **1-based** (beat 1 is the downbeat). Any section line may carry an event at any position, including a boundary such as `@10`.
- **Risers end at their position.** `!riser:2@cue:x` starts 2 bars earlier, which may be in an earlier section. A riser on a section line with no `@` ends at that section's start, so it plays during the section before.

## 3. The `.sm` format: a complete example

A 21-bar video with a counter, a caveat and a three-item list (`check` passes on it):

```
song "Example: Thruster Test" 120 4/4 Dm fps=30 seed=7 tail=3 video=ThrusterTest:1350
chords Dm Bb F C /2                  # loops from bar 0, straight across section boundaries
motif hook deg oct=5 "0/4 2 4 2 | 4/2 3/4 2"
cue landed=f735                      # the counter lands at bar 12, beat 2
lift = !impact !riser:2              # a named event list, placed with !lift
# name    bars | parts and settings                                         | events
title       4 | pad:dark arp:dark dyn=pp<p
problem     4 | drums:half bass:sub pad:dark fx:ticks dyn=p<mf
build       4 | drums:full+fill bass:8ths arp:up pad:warm lead:hook dyn=mf<f | !lift
counter     2 | like=build drums:full+fill+hats16 dyn=f<ff                   | !riser:2@cue:landed !impact@cue:landed
caveat      2 | pad:dark dyn=pp
results     3 | pad:warm bass:sub keys="=mp d1 | f | a" dyn=mp               | !impact
end_card    2 | pad:warm dyn=mp>pp                                          | !impact
```

The bars total 21, and 21 × 60 + 3 × 30 = 1350 frames. The counter's riser lands on the counter, the caveat drops to a quiet pad, and the list gets one new note per result: `keys` plays d, f, a, one per bar.

- **Header lines:**
  - `song "Title" tempo meter key fps= seed= tail=<seconds> video=Comp:frames` (optional extras: `mood=`, `tuning=`);
  - `inst part(param=v)`;
  - `chords ... /<bars per chord>` and `prog name "Am:2 F:2"`;
  - `motif name [deg|rel] [oct=n] "notes"`;
  - `cue name=f123`;
  - `master legacy|standard`;
  - `qa contrast=quiet<loud:6`.
- **Parts:**
  - `role:style[+mod...]`, or `role:style(k=v)` for options;
  - `role:m1,m2` for motifs (cycled every 2 bars, anchored at bar 0);
  - `keys="=p c e g"` for inline letter notes (looped to fill the section);
  - `kick="X...x..."` for a drum lane;
  - `-role` removes an inherited part.
  - Roles with styles in the catalog take styles. `lead` and any other role (keys, ...) take motifs or inline notes.
- **Settings:** `like=<earlier section>` (copies its parts and settings), `dyn=`, `prog=<name>` or `chords="Am:2 G:2"`, `tempo=`, `key=`.
- **Dynamics:**
  - levels are `ppp pp p mp mf f ff fff`;
  - `dyn=` takes a level (`dyn=pp`) or an arc across the section (`dyn=p<f` grows, `dyn=mp>pp` fades);
  - inside notes, `=mf` sets the level and `<`/`>` are hairpins to the next level.
- **Notes:**
  - durations are **sticky**: `c4 d e` is three quarter notes, and every bar must add up to the meter;
  - in `deg` motifs the duration follows a slash: in `"0/4 2 4 2 | 4/2 3/4 2"`, bar 1 is four quarters (0, 2, 4, 2), and bar 2 is a half (4) then two quarters (3, 2);
  - degree 0 is the key's tonic in octave `oct=`, and `-3` is three scale steps down;
  - durations are `1 2 4 8 16`, `.` dots, `t` triplets.
- **Events:**
  - `!type[:bars | :<beats>b][@position][(k=v)]`;
  - rendered now: `impact riser zaps stop drop`, for example `!zaps(count=6)` or `!stop:2b@+3:3`;
  - the catalog's "cue-only" events are exported to `cues.json` and render from later phases.
- **When sections repeat with small changes, or need per-bar variation, or loops**, use definitions and a `form:` block (`docs/LANGUAGE.md`):
  - `chorus = verse with {pad: warm}`;
  - `form:` then `verse 8 x2`, `for i in 1..4:`, `if i == last: drums += fill`, `every 4 bars: bass = 8ths`, `bar -1: lead = [m2]`.

## 4. Writing efficiently

- **Say only what differs.** Defaults cover the instruments, mix and master. `like=` plus a diff makes a repeated section cost a few tokens, and named event lists (`!lift`) replace repeated hit groups.
- **Reuse material.** Keep one or two motifs per video and develop them; don't write a new tune per section.
- **Revise by line.** Replace the one section line that changed instead of re-emitting the file.
- **Trust `check`.** It is faster than reasoning about validity. Write, check, fix.
- **Convert instead of rewriting.** For a YAML song map, `songmap fmt x.yaml --to sm` gives the compact form.

## 5. Scoring rules of thumb

These are **not** checked by `check`, which validates syntax, names, bar sums and length. Judge them yourself, and use `qa.json` after rendering for loudness contrast.

- **Reveals.** Every reveal gets one of: an impact, a stop-time before it (`!stop:2b`), a harmonic arrival, or a drop-out-then-return. Vary the device.
- **Caveats.** Every caveat or honesty beat (disclaimers, "not yet", limits) gets *less*: thin the texture (pad only), a lower `dyn`, no drums. Never put full drums under a hedge.
- **Counters.** A counter gets a gesture (a riser ending on it, a rising arp section) that **lands on the counter's landing frame**, not its start. Use a `cue` for the exact frame.
- **Lists.** A list of n items gets one new note or instrument per item, at the list's cadence (inline notes, one per item, as in `results` above), resolving on the last item.
- **Dynamics are relative.** Write `dyn=` arcs per section and spend `ff` once or twice per video. A quiet bar before a big section should be at least 6 dB quieter (`qa contrast=who<agents:6`).
- **Tempo.** Keep 120 BPM at 30 fps (60 frames per bar). For calm passages use a half-time feel (`drums:half`, chords every 2 bars), not a slower tempo.
- **Shared devices across a series** (`docs/RESCORE_PLAN.md` §2): a "verified" sus4→3 cadence for confirmations, a "caveat" falling line on a sus2 for limits, and act colours mapped to orchestration.

## 6. Gotchas

- **Section names** are identifiers. Avoid style and motif names, because a section is also a variable, and `pad:warm` would pick up a section called `warm`. Positions refer to sections (`@agents+8`), and the n-th repeat of a section is `<name>_n`.
- **`like=`** copies the earlier section's parts *and* settings. Use `-role` to drop a part.
- **Not yet available:** motif transforms (`m1:aug`, `:t+2`) and instruments outside the catalog (bell, strings, felt piano) arrive in later phases, and `check` says so. Use what exists.
