# Compact SongMap (`.sm`): the LLM encoding

The compact form is the same song tree as the YAML form ([SONGMAP_SPEC.md](SONGMAP_SPEC.md)), written as **one line per section** with short directives. It is designed for an LLM to write and revise cheaply:

- **No structural punctuation.** YAML's braces, quotes, `name:`/`bars:`/`parts:` keys and indentation are about half of a YAML song map.
- **Defaults do the work.** Default instruments, styles, groove and mix mean a line only states what differs.
- **Inheritance.** `like=goals` plus a diff makes a repeated section cost a few tokens.
- **Line-addressable edits.** A revision is "replace line `agents`", not a re-emit of the file.
- **Validated names.** Every style, instrument, parameter and event is checked, and errors say how to fix them.

## Measured size (the three Oct-13 ports in `examples/`, comments stripped)

| Song | v0.1 YAML | v0.2 compact | Ratio |
|---|---|---|---|
| Bench / Fields / Thruster (2:31) | 2,046 chars | 1,013 | 2.0× |
| Deep Dive (5:03) | 1,413 | 708 | 2.0× |
| The Swarm (2:03) | 1,489 | 1,027 | 1.45× (the compact file also carries `inst`, `groove`, `mix` and `qa` lines the YAML lacks) |

For comparison, the engine that renders them, `reference/synth_v0.py`, is 14,837 chars. A full new soundtrack is now **about 250–300 tokens** of output, against about 4,000 tokens to regenerate the prototype synth. Richer through-composed scores (see [RESCORE_PLAN.md](RESCORE_PLAN.md)) run about 2–4k chars, because the extra content is musical decisions, not boilerplate.

## Grammar

```
file      := line*
line      := directive | section | comment
comment   := '#' ...                        (also allowed after any line)

directive :=
  song "<title>" <tempo> <meter> <key> [k=v ...]     # fps= mood= tail= seed= video=<Composition>:<frames>
  inst  <part>=<instrument>[/<preset>][(k=v,...)] ...
  kit   <piece>=<instrument>[/<preset>][(k=v,...)] ...           # kick= snare= hat= ohat= clap= tom=
  groove [swing=<0.5..0.75>[/8|/16]] [tpl=<template>] [hum=<time_ms>,<drift_ms>,<vel>] [metric=<0..1>]
  feel  <part> [offset=<ms>] [gate=<x>] [hum=...] [high_loud=<x>] [arch=<x>]
  chords <chord> <chord> ... [/<bars per chord>]                  # default progression
  prog  <name> "<chord:bars ...>"                                 # named progression
  motif <name> [deg] [oct=<n>] [key=<key>] "<note language>"
  cue   <name>=<position>                                         # e.g. cue big=f3960
  mix   <part> <gain_db> [sc=<depth>] [hall=<send>] [room=<send>] [delay=<send>] [pan=<x>] [| <part> ...]
  master [lufs=<x>] [ceiling=<x>] [glue=none|gentle|punchy] [contrast=<dB>]
  qa    [lufs=<x>] [contrast=<a><<b>:<dB>,...] [silent!=<a>,<b>] [low<=<x>]

section   := <name> <bars> '|' <part-or-setting>* ['|' <event>*]
part      := <role>:<style>[+<mod>...][(k=v,...)]       e.g. drums:full+fill   bass:8ths(art=staccato)
           | <role>:<motif>[,<motif>...]                 e.g. lead:theme,answer:t+2
           | <role>="<note language>"                    inline notes, e.g. keys="=p [e,b]1 | [c,g]"
           | <piece>="<step string>"                     drum step pattern, e.g. kick="X...x...|X..x...."
           | -<role>                                     remove an inherited part
setting   := like=<section> | dyn=<shape> | prog=<name> | chords="<...>" | feel=<template>
           | tempo=<bpm>|rit<a>><b> | key=<key> | swing=<x>
           | auto=<part>.<param>:<a>><b>[ exp]           ramp across the section
           | auto=<part>.<param>:<v>@<pos>,<v>@<pos>,...  breakpoints (steps, or ramps with `~` between)
event     := !<type>[:<length>][@<position>][(k=v,...)]
length    := <bars> | <beats>b                           e.g. !riser:2   !stop:2b
position  := +<bars>[:<beat>] (relative to section start) | <bar>[:<beat>] | f<frame> | cue:<name>
```

**Defaults:**
- Every `song` gets the default parts (`drums bass pad arp lead fx`) with the mood preset's instruments.
- `groove` defaults to `swing=.5 hum=4,3,.03 metric=.5`, so even an un-annotated song is humanized slightly.
- Events land at the section start. A riser *ends* at its position.

**Part roles** can be any name. A role not in `inst` errors unless it matches a default role or an instrument name (`keys:block` implies `inst keys=keys`).

## A richer example (expression and orchestration)

```
song "Inside the 56 Movies (rescore sketch)" 100 4/4 Am fps=30 mood=documentary tail=4 seed=11
inst keys=keys/felt_piano(hardness=.35) gtr=string_pluck/nylon cello=bowed/cello pad=pad/air
kit  kick=kick(tune=44,decay=.6) snare=snare(tone=170) hat=hat
groove swing=.54/16 hum=6,4,.04
feel keys high_loud=.4 arch=.5
prog explain "Am:2 F:2 C:2 G:2"
prog doubt   "Am:2 Dm7:2 Bbmaj7:2 E7sus4:1 E7:1"
motif lattice deg oct=4 "=mp 0/8 2 4 2 5 4 2 4 | 0/8 2 4 7/2 r/8 4"
motif contact deg oct=5 "=p < 4/2_ 3/4 2 | 1/2.~ 0/4 =mf"
cue  thesis=f6070
title    6 | pad:air keys:lattice:dyn=pp dyn=pp<p
setup   22 | like=title gtr:arp16(pattern=0213) bass:sub prog=explain dyn=p<mp
# ... more sections ...
barrier 16 | prog=doubt keys:contact cello:sustain(dyn=p) drums:half(ghosts=on) -gtr dyn=mp<f | !riser:2@cue:thesis !impact@cue:thesis(size=xl)
```

## The LLM authoring loop

1. **Load the catalog, not the engine.** `songmap describe --compact` prints about 400 tokens: every style per role, instruments with key params, event types, transforms and the note-language cheat sheet. That is all the context an LLM needs. (`instruments.describe()` in the sketch already does the instrument part, at roughly 40 tokens per instrument.)
2. **Read the video.** If `video=` is set, `songmap cues-from-video` (Phase 8) proposes `cue` lines from the Remotion source or `cues.json`. Otherwise use a scene timeline like [SCENE_TIMELINES.md](SCENE_TIMELINES.md).
3. **Write** the `.sm` file: header, then sections. Prefer `like=` and motif transforms over new material when the music should recur.
4. **Check.** `songmap check song.sm` takes milliseconds: it parses, bar-checks motifs, validates names and checks cue alignment. Errors are one line each, written to be fixed without guessing:
   ```
   song.sm:14 agents: unknown bass style 'eigths' (did you mean 'eighths'? valid: sub eighths octaves walking pedal syncopated root5)
   song.sm:9 motif m2: bar 2 has 3 beats, expected 4. Check durations before bar line 2 (durations are sticky).
   song.sm:22 event !impact@f3962: lands 2 frames after beat 66:1; use @66 or snap=none
   ```
5. **Render** with `songmap render song.sm --out build/`. It writes `qa.json` and `qa.png`, about 10–30 s for a 5-minute track.
6. **Read QA and revise.** QA reports section loudness contrast, band balance, true peak and whether hits are audible. Revise by replacing whole section lines.
7. **Audition (human).** The user listens and gives feedback in musical terms ("pad too bright in barrier", "hits should feel bigger"). The LLM maps that to parameter or line edits. `songmap why <section>` explains what was generated there (part by part, notes per bar, velocity range) so the LLM can reason about what it can't hear.

## Rules of thumb for LLM-written scores

- Put **section boundaries where the picture changes**, and **events where things land on screen**. A counter's landing frame matters, not its start frame. Use `cue` lines for frame-exact moments.
- Every **reveal** gets one of: an impact, a stop-time before it, a harmonic arrival (V→I), or a drop-out-then-return. Don't use the same device every time.
- Every **caveat or honesty beat** (disclaimers, "not yet", limits) gets *less*: thin the texture, add a suspended or unresolved chord, lower the dynamics. Never put full drums under a hedge.
- **Lists** (n items appearing on a cadence): match the cadence with an instrument entry or note per item, building in density, then resolve on the last item.
- Keep **one or two motifs per video** and transform them (`:t+2`, `:inv`, `:aug`, re-harmonize). Recognizable development beats new tunes every section.
- **Dynamics are relative.** Write `dyn=` arcs per section and let parts inherit. Spend `ff` once or twice per video.
