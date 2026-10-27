# Compact SongMap (`.sm`): the LLM encoding

The compact form is the same song tree as the YAML form ([SONGMAP_SPEC.md](SONGMAP_SPEC.md)), written as **one line per section** with short directives. It is the flat subset of the SongMap language ([LANGUAGE.md](LANGUAGE.md)): the same `.sm` file can also name beats and sections, loop, branch and vary bars, and the parser is the same. It is designed for an LLM to write and revise cheaply:

- **No structural punctuation.** YAML's braces, quotes, `name:`/`bars:`/`parts:` keys and indentation are about half of a YAML song map.
- **Defaults do the work.** Default instruments, styles, groove and mix mean a line only states what differs.
- **Inheritance.** `like=goals` plus a diff makes a repeated section cost a few tokens.
- **Line-addressable edits.** A revision is "replace line `agents`", not a re-emit of the file.
- **Validated names.** Every style, mod, motif, setting, directive option and event is checked, and errors say how to fix them.

`songmap check song.sm` and `songmap render song.sm` read it (`.sml` is an alias). `songmap fmt x.yaml --to sm` prints any song map as `.sm`, and `--to yaml` prints it back; both are lossless. For agents, the [songmap-compose skill](../.claude/skills/songmap-compose/SKILL.md) (and [AGENTS.md](../AGENTS.md)) packages the authoring loop below.

## Measured size (the three Oct-13 ports, comments and blank lines stripped)

| Song | v0.2 YAML port | `.sm` | Ratio |
|---|---|---|---|
| Bench / Fields / Thruster (2:31) | 2,093 chars | 1,368 | 1.53× |
| Deep Dive (5:03) | 1,534 | 1,036 | 1.48× |
| The Swarm (2:03) | 1,761 | 1,158 | 1.52× (the `.sm` also carries a `qa` line) |

Each `.sm` port expands to exactly the same notes as its YAML port: the arrangement digest, events, instruments and master all match (`tests/test_lang.py`). Written with definitions and a form block instead of section lines, The Swarm is 1,081 chars ([LANGUAGE.md §14](LANGUAGE.md)).

For comparison, the engine that rendered them, `reference/synth_v0.py`, is 14,837 chars. A full new soundtrack is now **about 250–350 tokens** of output, against about 4,000 tokens to regenerate the prototype synth.

## Grammar

```
file      := line*
line      := directive | definition | section | eventline | comment
comment   := '#' ...                        (also allowed after any line)

directive :=
  song "<title>" <tempo> <meter> <key> [fps=] [seed=] [mood=] [tail=] [tuning=] [video=<Composition>:<frames>]
  inst  <part>[=<instrument>[/<preset>]][(k=v,...)] ...          # inst bass(cutoff=700) keys=keys/felt_piano
  kit   <piece>=<instrument>[/<preset>][(k=v,...)] ...           # kick= snare= hat= ohat= clap= tom=
  groove [swing=<0.5..0.75>[/8|/16]] [tpl=<template>] [hum=<time_ms>,<drift_ms>,<vel>] [metric=<0..1>]
  feel  <part> [offset=<ms>] [gate=<x>] [hum=<t>,<d>,<v>] [high_loud=<x>] [arch=<x>]
  chords <chord> <chord> ... [/<bars per chord>]                  # default progression
  prog  <name> "<chord:bars ...>"                                 # named progression
  motif <name> [deg|rel] [oct=<n>] [key=<key>] "<note language>"
  cue   <name>=<position>                                         # e.g. cue big=f3960
  mix   <part> <gain_db> [sc=<depth>] [hall=|room=|delay=|plate=<send>] [pan=<x>] [width=<x>] [| <part> ...]
  master [legacy|standard] [lufs=<x>] [ceiling=<x>] [glue=none|gentle|punchy] [contrast=<dB>]
  qa    [lufs=<x>|<a>..<b>] [contrast=<quiet><<loud>:<dB>,...] [silent!=<a>,<b>] [low<=<x>] [peak<=<dB>] [hits=true]
  set   <key>[.<key>...]=<value>                                 # any YAML field: set returns={hall: {type: reverb}}
  binaural <carrier>... [beat=octave] [octaves=<integer>] [level=<LU>] [fade=<s>] [glide=<s>]
           [breathe=<bars>] [breath=<dB>] [gain=<dB>] [carve=true|false]   # default difference = each carrier / 32
           # explicit fixed-Hz alternative: beat=<Hz>|<a>><b> [ladder=golden|same|[..]]; no octaves in this mode

definition := <name> = <value>                                    # lit = up(order=[0,2,1,3]); see LANGUAGE.md
            | <name> = !<event> ...                               # a named event list: lift = !impact !riser:2
eventline := <event> ...                                          # absolute positions only: !impact@agents+8

section   := <name> <bars> [x<N>] '|' <part-or-setting>* ['|' <event>*]
part      := <role>:<style>[+<mod>...][(k=v,...)]       drums:full+fill   bass:8ths(art=staccato)
           | <role>:{<map>}                              bass:{style: "sub", vary: [{bars: [3], part: "eighths"}]}
           | <role>:<variable>                           arp:lit   (any part or beat defined above)
           | <role>:<motif>[:<transform>][,<motif>...]   lead:m1,m2,m3,m4   lead:theme,answer:t+2
           | <role>:{<map>}:<transform>...              mel:{deg: q}:aug
           | <role>:<value>:<k>=<v>                      keys:lattice:dyn=pp
           | <role>="<note language>"                    keys="=p [e,b]1 | [c,g]"
           | <piece>="<step string>"                     kick="X...x...|X..x...."   (a drums lane)
           | -<role>                                     remove an inherited part
setting   := like=<section> | dyn=<shape> | prog=<name> | chords="<chord:bars ...>" | feel=<template>
           | swing=<x> | tempo=<bpm>|rit<a>><b>|accel<a>><b> | key=<key>
           | meter=<n>/<d> | meter="<n>/<d> <groups>"        meter=7/8   meter="13/16 3+3+3+2+2"   (this section's bars)
           | beat=<Hz>|<a>><b> | binaural={carriers: [A3, "^F4"], beat: 6.18, gain_db: -3}   (the binaural layer)
           | auto=<part>.<param>:<a>><b>                 auto="arp.cutoff:1500>4000 exp" (quote it with a space)
event     := !<type>[:<length>][@<position>][(k=v,...)] | !<named list>
length    := <bars> | <beats>b                           !riser:2   !stop:2b
position  := +<bars>[:<beat>] (from the section start) | <bar>[:<beat>] | f<frame> | cue:<name> | <section>[+<bars>]
k=v       := a number, a word, "a string" or [a, list]   !drop:2@0(keep=[pad,bass])
```

Notes on the grammar:

Conductor settings use quarter-note BPM and begin at section boundaries; a tempo ramp runs across its
section. `key="D dorian"` specifies tonic and scale/mode. Unpinned degree motifs follow it, while written
letter pitches and chord symbols keep their notes. `tempo=none`, `meter=none`, and `key=none` restore song
defaults for a section. For forms and loops, `set conductor={verse_2: {tempo: 108, key: "D dorian"}}` overrides
one expanded section instance without changing its shared definition. [SONGMAP_SPEC.md §9](SONGMAP_SPEC.md#9-tempo-meter-key-and-scale-changes)
describes the resolved format; Studio's Conductor tab edits these values visually.
- `like=` is applied first, wherever it appears on the line. The other items apply left to right.
- `<value>` options in `(...)` may be lists or variables: `arp:up(order=[0,2,4,2])`.
- A section line both defines the section, as a variable for later `like=` and `with`, and places it. `x<N>` places it N times; the repeats are named `<name>_2`, `<name>_3`, and so on.
- A file uses section lines or a `form:` block ([LANGUAGE.md §4](LANGUAGE.md)), not both.
- A section may be named like a directive (`groove 8 | ...`), because no directive's arguments start with a number.
- `set` writes any field of the YAML form that has no directive (`returns`, `harmony.voicing`, an `fx` kit). `songmap fmt` uses it so that printing is lossless.

**Defaults:**
- Every song plays on the default ensemble, shaped by its mood (`mood=balanced` unless the song names one: cinematic, documentary, ambient, techno, lofi, or v0 for the original synth_v0 sound). `inst`, `kit` and `mix` change only what they name.
- `groove` and `feel` are played by the performance layer (swing, templates, timing offsets and humanize), on top of the mood's own feel. `qa` rules are evaluated from P2. `songmap listen` (the automated ear) and every render's `review.json` report what a listener would notice.
- Events land at the section start. A riser *ends* at its position.

**Part roles** can be any name. A role without an instrument entry uses the instrument of the same name or the part fallback (`keys` → keys, `gtr` → string_pluck); `inst` sets it explicitly.

## Continuous performance and recorded techniques

Use a top-level `set expression={section: {part: {control: [[beat,value],...]}}}` map
for volume, tone, added pitch/vibrato, width and compatible sound-source morphs inside
held notes. Beats are quarter notes from the section start, beginning at 0 and ending
at its length; final values hold until another lane changes them. Use
`set techniques={section: {part: [[beat,"pizzicato"],...]}}` with `family/<instrument>`
for actual recorded techniques on subsequent notes, or `technique: pizzicato` in a
part specification for a phrase. See [complete ranges and examples](EXPRESSION_ARTICULATION_RESPONSE.md).

## A richer example (expression and orchestration)

```
song "Inside the 56 Movies (rescore sketch)" 100 4/4 Am fps=30 mood=documentary tail=4 seed=11
inst keys=keys bass(cutoff=650)
groove swing=.54/16 hum=6,4,.04
feel keys high_loud=.4 arch=.5
prog explain "Am:2 F:2 C:2 G:2"
prog doubt "Am:2 Dm7:2 Bbmaj7:2 Esus4:1 E7:1"
motif lattice deg oct=4 "=mp 0/8 2 4 2 5 4 2 4 | 0/8 2 4 7/2 4/8"
motif contact deg oct=5 "=p 4/2 3/4 2 | 1/2. 0/4"
cue thesis=f2880
reveal = !riser:2@cue:thesis !impact@cue:thesis(size=xl)
title    6 | pad:warm keys:lattice:dyn=pp dyn=pp<p
setup   22 | like=title arp:up bass:sub prog=explain dyn=p<mp
barrier 16 | prog=doubt keys:contact drums:half+ghosts -arp dyn=mp<f kick="X.....x...x....." | !reveal
mix keys -5 hall=.3 | pad -6 sc=.35
qa contrast=title<barrier:6 silent!=setup,barrier
```

When a section repeats with small changes, or a beat needs a fill every 8 bars, switch to definitions and a `form:` block ([LANGUAGE.md](LANGUAGE.md)). The header lines stay the same.

## The LLM authoring loop

1. **Load the catalog, not the engine.** `songmap describe --compact` prints about 450 tokens: every style and mod per role, kit pieces, instruments and presets, event types, the note language and the `.sm` syntax. That is all the context an LLM needs. Without `--compact` it adds style descriptions and every instrument's parameters.
2. **Read the video.** If `video=` is set, `songmap cues-from-video` (Phase 8) proposes `cue` lines from the Remotion source or `cues.json`. Otherwise use a scene timeline like [SCENE_TIMELINES.md](SCENE_TIMELINES.md).
3. **Write** the `.sm` file: header, then sections. Prefer `like=`, named event lists and motif transforms over new material when the music should recur.
4. **Check.** `songmap check song.sm` takes milliseconds. It parses, bar-checks motifs, validates names and checks the length against the video. Errors are one line each, written to be fixed without guessing:
   ```
   song.sm:14 agents: unknown bass style 'eigths' (did you mean 'eighths'? valid: 8ths eighths sub)
   song.sm:9 agents: motif m2: bar 1 has 3 beats, expected 4. Check durations before bar line 1 (durations are sticky).
   song.sm:12 cold_open: unknown setting 'vibe' (valid: auto chords dyn feel key like prog swing tempo)
   song.sm:22 unknown event type 'impakt' (did you mean 'impact'? valid: cloud crash downlifter drop ...)
   ```
5. **Render** with `songmap render song.sm -o build/`. It writes `song.wav`, `stems/`, `cues.json` and `qa.json`, in about 10–30 s for a 5-minute track.
6. **Read QA and revise.** QA reports section loudness contrast, band balance, true peak and whether hits are audible. Revise by replacing whole section lines.
7. **Audition (human).** The user listens and gives feedback in musical terms ("pad too bright in barrier", "hits should feel bigger"). The LLM maps that to parameter or line edits. `songmap why <section>` (P2) explains what was generated there (part by part, notes per bar, velocity range) so the LLM can reason about what it can't hear.

## Rules of thumb for LLM-written scores

- Put **section boundaries where the picture changes**, and **events where things land on screen**. A counter's landing frame matters, not its start frame. Use `cue` lines for frame-exact moments.
- Every **reveal** gets one of: an impact, a stop-time before it, a harmonic arrival (V→I), or a drop-out-then-return. Don't use the same device every time.
- Every **caveat or honesty beat** (disclaimers, "not yet", limits) gets *less*: thin the texture, add a suspended or unresolved chord, lower the dynamics. Never put full drums under a hedge.
- **Lists** (n items appearing on a cadence): match the cadence with an instrument entry or note per item, building in density, then resolve on the last item.
- Keep **one or two motifs per video** and transform them (`:t+2`, `:inv`, `:aug`, re-harmonize). Recognizable development beats new tunes every section.
- **Dynamics are relative.** Write `dyn=` arcs per section and let parts inherit. Spend `ff` once or twice per video.
