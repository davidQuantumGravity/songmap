# The SongMap language (`.sm`)

`.sm` is SongMap's text format. The flat compact form in [COMPACT_FORMAT.md](COMPACT_FORMAT.md) is the subset with one line per section. On top of that subset the language adds:
- named beats, parts and sections;
- `with` and dotted assignment (`chorus.drums.kick = "x..x..x."`);
- `+` to layer drum lanes;
- named event lists;
- a `form:` block with loops (`x4`, `for i in 1..4:`);
- conditions per iteration (`if i == last:`) and per bar (`every 8 bars:`, `bar 4:`), on any part;
- small functions (`def four(acc=0.8): ...`);
- operators on step strings.

`.sml` is accepted as an alias.

The language **compiles to the existing `Song` tree**. Under it, expand, render, the golden tests and `cues.json` are unchanged: a program means exactly what its compiled YAML song map would mean. The parser is [`songmap/parse/lang.py`](../songmap/parse/lang.py), and `songmap check` and `songmap render` read `.sm` and `.sml` files.

```
song "Loops demo" 120 4/4 Am
chords Am F C G
motif hook deg "0 2 4 2 | 4/2 2"

roll = {snare: "........xxxxxxxx"}
verse = {drums: four_floor, bass: sub, lead: [hook]}
chorus = verse with {drums: full + hats16, pad: warm}
chorus.drums.kick = euclid(5, 16)

form:
  verse 8 x2
  for i in 1..3:
    chorus 4*i:
      if i == last: drums += {clap: "....x.......x..."}
      every 4 bars: drums += roll
  verse 4 as outro    !impact !riser:1@+3
```

## 1. Definitions

A program is evaluated once, top to bottom. Each line is one of:
- a header directive;
- a definition (`name = value`) or an edit (`name.role = value`, `name.role.lane += "..."`);
- a named event list (`lift = !impact !riser:2`);
- a function (`def`);
- either section lines (§3) or one `form:` block (§4), not both.

**Header directives** are the compact format's lines:

```
song "<title>" <tempo> <meter> <key> [fps= seed= mood= tail= tuning= video=<Composition>:<frames>]
inst <part>[=<instrument>[/<preset>]][(k=v, ...)] ...       inst bass(cutoff=700) keys=keys/felt_piano(hardness=.35)
kit <piece>=<instrument>[/<preset>][(k=v, ...)] ...         kit kick=kick/v0(tune=44) clap=clap
groove [swing=<x>[/8|/16]] [tpl=<template>] [hum=<time_ms>,<drift_ms>,<vel>] [metric=<x>]
feel <part> [offset=<ms>] [gate=<x>] [hum=<t>,<d>,<v>] [high_loud=<x>] [arch=<x>]
chords <chord> ... [/<bars per chord>]
prog <name> "<chord:bars ...>"
motif <name> [deg|rel] [oct=<n>] [key=<key>] "<note language>"
cue <name>=<position>
mix <part> <gain_db> [sc=<depth>] [hall= room= delay= plate=<send>] [pan=<x>] [width=<x>] [| <part> ...]
inserts <part|master|return> <unit>[(k=v, ...)] ... [| <part> ...]   inserts lead eq(high=2) comp(threshold=-20) | master eq(low=1)
master legacy|standard [lufs=] [ceiling=] [glue=none|gentle|punchy] [contrast=<dB>]
patch <name> <id>=<module>[(knob=value, ...)] ... <src>><dst>[.<knob>][*amount] ... @<macro>(default=x, mod.knob=a..b)
qa [lufs=<x>|<a>..<b>] [contrast=<quiet><<loud>:<dB>,...] [silent!=<a>,<b>] [low<=<x>] [peak<=<dB>] [hits=true]
set <key>[.<key>...]=<value>                               set returns={hall: {type: "reverb", seconds: 2.4}}
```

`set` writes any field of the YAML form that has no directive, such as `returns`, `harmony.voicing` or an `fx` kit. Each other directive maps onto a field of the song: `instruments`, `groove`, `parts_feel`, `harmony`, `motifs`, `cues`, `mix`, `master` or `qa` ([SONGMAP_SPEC.md](SONGMAP_SPEC.md)). In `mix`, `sc=` and the sends change only the depth or send they name; the rest of the part's default sidechain and sends is kept. `inserts` names a part, `master` (before mastering) or a return such as `hall` or `room` (its wet output, after the reverb and before it joins the mix): `inserts hall eq(lp=6000, low=-4) | master comp(ratio=2)`. `groove` and `feel` are played by the performance layer, on top of the song's mood. `qa` rules are evaluated from P2.

A `patch` builds an instrument from modules and wires (docs/INSTRUMENTS.md §7): oscillators, wavetables, noise, plucked strings, waveguides (bowed strings, reeds, flutes), resonators, filters, shapers, echoes, envelopes and LFOs. Several lines with one name add to the same patch, and a voice plays it as `patch/<name>` (`inst bass=patch/acid(f1.cutoff=500)`). A knob value may be a quoted formula of the note: `f1=filter(cutoff="800*2**(2*vel+key)")`. Patches in `songmap/patches/` (a sketch of every built-in instrument, plus acid, bell, glass_pad, snare808, wobble, cello, clarinet, flute, vowel_pad and scan_bass) need no `patch` line.

**Values:**

| Value | Written | Notes |
|---|---|---|
| number | `8`, `0.8`, `-2` | |
| string | `"x...x..."` | step strings, note text, chord text |
| boolean, nothing | `true` `false` `none` | `none` removes a key in `with` and in dotted assignment |
| list | `[m1, m2, m3]` | indexing is 0-based and **cyclic**, so `xs[i]` never runs out |
| map | `{kick: "x...", hat: "-.x."}` | keys are names or strings; order is kept |
| part | `full`, `full+fill`, `up(order=[0,2,1,3])`, `{deg: "0 2 4"}` | what one role plays in a section |
| section | `{drums: full, bass: sub, dyn: "p<f"}` | a map from role to part, plus section settings |
| event list | `!impact !riser:2` | defined with `name = !...` and placed with `!name` (§6) |
| function | `def four(acc=0.8): ...` | |

A **beat** is a part for a drum kit. It is a style with mods, a map of lanes to step strings, or both:

```
four = {kick: "x...x...x...x...", hat: "-.x.-.x.-.x.-.x."}
busy = full + hats16 + {kick: "......x.......x."}
```

**A section is a map from role to part.** Its keys are roles, plus the section settings `harmony`, `dyn`, `feel`, `tempo`, `key` and `bars`. A `bars` key is the default length when the form line gives none.

**Names** resolve as follows:
1. A defined variable (or, in a loop, the loop variables).
2. A builtin (`euclid rot rev len min max`).
3. Otherwise the name is kept as a **reference**. It is resolved when the value is bound to a role: first as a motif, then as a style of that role (`drums: full`, `pad: warm`). A mod is used as `full + fill`.

So a misspelt variable surfaces at its use, with a suggestion. A definition may shadow a style with a variant of itself, because the right side is evaluated first: `up = up(order=order)`. Give sections names that differ from your motifs: a section called `a` hides the motif `a`.

## 2. Composition

**`with`** merges a map into a section or part and returns a copy. Keys on the right replace keys on the left, and `none` deletes a key:

```
agents = goals with {lead: [m1, m2, m3, m4]}
guardrails = so_what with {fx: none}
bright = up with {order: [0, 2, 1, 3]}        # on a part: options (order, oct, gain_db, ...) or lanes
```

**`+` layers beats.** It is the language's word for "play both":

| Left | Right | Result |
|---|---|---|
| style | mod name | the mod is added: `full + fill` (the same as `full+fill` in YAML) |
| beat | `{lane: steps}` | hits are added to that lane, on top of the style's own lane |
| `{lanes}` | `{lanes}` | the lanes are merged, and a lane on both sides is layered |
| style | style | an error: layer lanes instead |
| event list | event list | the lists are joined |

Layering two step strings keeps the louder step at each position (`X > f > r > x > - > o > .`). Two strings with different bar lengths are placed on their common grid. `-` removes a mod: `drums - fill`.

**Dotted assignment** edits one field of a definition and rebinds the name to the edited copy:

```
chorus.drums = full + hats16          # replace the part
chorus.drums += open                  # add a mod
chorus.drums.kick = "x..x..x."        # replace one lane
chorus.drums.kick += "....x..."       # layer onto the lane (including the style's kick)
chorus.lead.oct = 1                   # set a part option (a motif list gains options too)
chorus.pad = none                     # remove the part
```

**Values, not references.** `b = a with {...}` copies `a` at that line, so a later `a.drums = ...` does not change `b` (§13, decision 4).

## 3. Section lines: the flat form

The simplest song is one line per section. Each section line **defines** the section as a variable and **places** it, in file order:

```
<name> <bars> [xN] | <part or setting> ... | !event ...
```

| Item | Meaning | Example |
|---|---|---|
| `role:style[+mod...][(k=v, ...)]` | a part. The name may be a variable (`arp:lit`) | `drums:full+fill`, `bass:8ths(art=staccato)`, `arp:up(order=[0,2,1,3])` |
| `role:m1,m2[:transform]` | a motif list | `lead:m1,m2,m3,m4`, `lead:theme,answer:t+2` |
| `role:<value>:k=v` | a part with options | `keys:lattice:dyn=pp` |
| `piece="<steps>"` | a drum lane: a kit piece, set on `drums` | `kick="X...x...|X..x...."` |
| `role="<notes>"` | inline notes for a pitched part | `keys="=p [e,b]1 \| [c,g]"` |
| `-role` | remove an inherited part | `-gtr` |
| `like=<section>` | start from an earlier section (applied first) | `like=goals` |
| `dyn=`, `prog=`, `chords="..."`, `feel=`, `swing=`, `tempo=`, `key=`, `meter=` | section settings | `dyn=p<mf`, `prog=doubt`, `tempo=rit120>96`, `meter="7/8 2+2+3"` |
| `auto=<part>.<param>:<ramp>` | automation on one part | `auto="arp.cutoff:1500>4000 exp"` |

Events go after the second `|`, or anywhere a token starts with `!`. A line of only events (`!impact@agents+8`) needs absolute positions, and it keeps its place in the event order. Section lines may use any variable defined above them: parts, beats and named events. A file uses either section lines or a `form:` block. Mixing them is an error that says which line to change.

## 4. The form block

`form:` is the song when you need loops, conditions or edits per instance. Each line places a section:

```
form:
  <section> [<bars>] [xN] [as <name>] [!event ...] [: <edit> | indented edits]
```

- **`<bars>`** is any expression, so `chorus 4*i` works.
- **Names.** The first instance of `verse` is called `verse`; later ones are `verse_2`, `verse_3` and so on (§13, decision 1). `as outro` names an instance explicitly. These names appear in `cues.json`, in event positions (`@verse_2+4`) and in the per-section seeds.
- **Events** use the syntax `!type[:bars | :<beats>b][@position][(k=v, ...)]`. Positions:
  - `@+8:2` is relative to this instance;
  - `@12` is an absolute bar;
  - `@f3960` is a video frame;
  - `@cue:x` is a named cue.

  Option values may be lists: `!drop:2@0(keep=[pad,bass])`. An event line on its own in the form needs an absolute position.
- **Edits under a form line** change that instance only. In them, a target's first name is a *role*, so `drums += fill` means "this instance's drums".

```
  bridge 8:
    dyn = "p<f"
    drums.kick = euclid(3, 8)
    !riser:2@+6
```

## 5. Repetition

**`xN`** places a section N times. It works on form lines and on section lines. Under a repeated form line, `rep` is the repetition number (1..N), and `first`/`last` are 1 and N:

```
  verse 8 x4:
    if rep == last: drums += fill
```

**`for`** loops over a range (`1..4`, inclusive) or a list. The loop variable can be used in any expression: bar counts, indexes, arguments and conditions. `first` and `last` are the first and last items of the innermost loop:

```
  for i in 1..4:
    build 2:
      drums.kick = euclid(i + 2, 16)
      lead = [m1, m2, m3][i]
      if i == last: !impact@+2
```

**Assignments in the form block** rebind variables for the lines below them. So a loop can evolve a section:

```
  for i in 1..3:
    pulse 4
    pulse.drums += {hat: rot("x...", i)}
```

## 6. Named events

```
lift = !impact !riser:2 !riser:1@+8
outro_hits = !lift !zaps(count=3)       # a list may include another list
both = lift + outro_hits                # or join two lists
```

- **Defining.** A named event list is defined at the top level from `!` events and other named lists, and two lists join with `+`.
- **Placing.** `!lift` places the list, on a section line, a form line or under a form line. Each event's position is relative to the instance it is placed on, exactly as if written there.
- **Restrictions.** A named list takes no `:length`, `@position` or options of its own; put those on the events inside it. Its name can't be an event type (`hit`, `drop`, ...), because `!hit` must keep meaning the event.

## 7. Conditions

**Per iteration.** `if`, `elif` and `else` are evaluated as the form unrolls. They can sit around form lines or under one:

```
  for i in 1..4:
    if i % 2 == 1:
      verse 8
    else:
      chorus 8:
        if i == last: drums += fill
```

**Per bar.** Two forms, both under a form line, work on **any part**: drums, bass, pad, lead and so on.

```
  verse 8:
    every 4 bars: bass = eighths          # bars 4 and 8 of this verse
    every 4 bars at 1: drums.kick += "x.x............."
    every 8 song bars: drums += {ohat: "x..............."}   # counted from the song start
    bar 2, -1: lead = [answer]            # the 2nd and the last bar
    bar 3: pad = none                     # silence the pad's new notes in bar 3
```

- `every N bars [at K]` picks the K-th bar of every group of N. K defaults to N, the last bar of each group.
  - Under a form line, bars are counted within the instance; `every N song bars` counts from the song start.
  - At the top of the form block, `every` counts song bars and applies to every instance that has the part.
- `bar K, ...` picks bars by number: 1 is the first, and -1 is the last.
- An edit may replace the part (`bass = eighths`), change one of its options (`lead.oct = 1`), layer onto it (`drums += roll`), set a lane (`drums.snare = "...x"`), or silence it (`= none`).
- Edits that pick the same bar apply in order.

How a per-bar edit compiles:
- **Lane edits on a drum kit** (`+= {lane: ...}`, `+= <set/add mod>`, `.lane = "..."`) become per-bar step strings (`"a|a|a|b"`), which the engine already cycles bar by bar.
- **Every other per-bar edit** becomes a **variant of the part** for those bars: `vary:` in the song tree ([SONGMAP_SPEC.md §6](SONGMAP_SPEC.md)). In a variant's bars, its notes replace the part's. A note belongs to the bar it starts in, so a pad chord held from the bar before keeps sounding. Sections stay whole, so names, cues, seeds and dynamic arcs don't move.

Phrase mods that already have their own period, such as the styles' `fill` (every 8 song bars), are refused under `every` with a hint to use them without it. The section settings (`dyn`, `harmony`, `tempo`) can't vary per bar; split the section instead.

## 8. Functions

```
def four(acc=0.8): {kick: "x...x...x...x...", hat: {steps: "-.x." * 4, vel: [0.4, acc]}}

def build(n, base=full):
  hats = euclid(n, 16)
  return base + {hat16: hats}

verse = {drums: four(acc=1), bass: sub}
lift = verse with {drums: build(7)}
```

- A function body is either one expression after the `:`, or indented `name = value`, `if` and `return` lines.
- Arguments can be positional or named, and defaults are evaluated where the function is defined.
- A function sees the definitions above it, a snapshot taken at the `def` line, so it cannot call itself. Passing a function to itself is caught at the call.
- Calling a style is shorthand for options: `up(order=[0, 2, 1, 3])` means `up with {order: [...]}`.

## 9. Step-string operators

| Expression | Result | Meaning |
|---|---|---|
| `"x..." + "..x."` | `"x.....x."` | concatenate (one bar on a finer grid) |
| `"x.x." * 4` | `"x.x.x.x.x.x.x.x."` | repeat |
| `"x...x..." \| "x.x.x.x."` | `"x...x...\|x.x.x.x."` | join bars (lanes cycle bar by bar) |
| `"x...x..." & "..x...x."` | `"x.x.x.x."` | overlay, louder step wins |
| `rot("x..x..x.", 2)` | `"x.x..x.."` | rotate each bar right (negative: left) |
| `rev("x..x....")` | `"....x..x"` | reverse each bar |
| `euclid(3, 8)` | `"x..x..x."` | Bjorklund: k hits spread over n steps; `euclid(k, n, rot)` rotates |

`+` concatenates strings but layers beats (§13, decision 3). Inside beats the same idea becomes "play both": `{kick: a} + {kick: b}` is `{kick: a & b}`.

## 10. What it leaves out on purpose

- **No unbounded loops or recursion.** There is no `while`, and functions cannot recurse. Loops run over ranges and lists whose values are known when the file is read. The whole form may unroll to at most 4,096 steps, and lists and step strings are capped at 4,096 items.
- **No input, no clock, no randomness.** A program is a pure function of its text. Randomness stays in the engine, seeded with crc32 from the song seed, section, part and bar.

So every program terminates quickly with one song tree, and `songmap check` reports the exact length:

```
ok: Week of Oct 13 — The Swarm
  10 sections, 60 bars at 120 BPM 4/4, 2:03.00 (3690 frames @ 30 fps)
```

Anything generative, such as a Markov melody or a search over grooves, belongs in Python that writes a song map.

## 11. Grammar

Blocks are indented with spaces. A line ending in `:` opens a block, or the statement can follow the `:` on the same line. Brackets continue a line, and `#` starts a comment.

```
program   := (directive | def | assign | evdef | secline* | event+ | form)*   # section lines or one form, not both
directive := ("song" | "inst" | "kit" | "groove" | "feel" | "chords" | "prog" | "motif" | "cue" | "mix"
              | "master" | "qa" | "set") <arguments, see §1>
secline   := NAME expr ["x" INT] ("|" (item | event)*)*                    # §3
item      := role ":" pvalue | NAME "=" STRING | "-" NAME | NAME "=" value
pvalue    := NAME ("+" NAME)* ["(" k=v ("," k=v)* ")"] (":" k=v)* | NAME (":" transform)* ("," ...)+
evdef     := NAME "=" event+
def       := "def" NAME "(" [param ("," param)*] ")" ":" (expr | INDENT (assign | if | "return" expr)+ DEDENT)
param     := NAME ["=" expr]
assign    := target ("=" | "+=" | "-=") expr
target    := NAME ("." NAME)*                      # in edits under a form line, NAME is a role
form      := "form" ":" INDENT formstmt+ DEDENT
formstmt  := place | for | if | every | assign | event+
place     := NAME [expr] ["x" INT] ["as" NAME] event* [":" (edit | INDENT edit+ DEDENT)]
edit      := assign | if | every | bar | event+
for       := "for" NAME "in" expr ":" block           # expr: a range a..b or a list
if        := "if" expr ":" block ("elif" expr ":" block)* ["else" ":" block]
every     := "every" expr ["song"] ["bars"] ["at" expr] ":" assign+
bar       := "bar" expr ("," expr)* ":" assign+
event     := "!" NAME [":" NUM ["b"]] ["@" position] ["(" k=v ("," k=v)* ")"]

expr      := with ["if" with "else" expr]
with      := or ("with" or)*
or        := and ("or" and)*          and := not ("and" not)*          not := "not" not | cmp
cmp       := range [("==" | "!=" | "<" | "<=" | ">" | ">=") range]
range     := bar_ [".." bar_]         bar_ := amp ("|" amp)*           amp := sum ("&" sum)*
sum       := term (("+" | "-") term)* term := unary (("*" | "/" | "//" | "%") unary)*
unary     := "-" unary | postfix      postfix := atom ("(" args ")" | "[" expr "]" | "." NAME)*
atom      := NUMBER | STRING | NAME | "true" | "false" | "none" | "(" expr ")"
           | "[" [expr ("," expr)*] "]" | "{" [key ":" expr ("," key ":" expr)*] "}"
```

`with` binds loosest of the binary operators, so `a + b with {...}` is `(a + b) with {...}`.

## 12. How it maps onto the `Song` tree

The evaluator unrolls the form (or the section lines) into a list of instances. It then writes the **v0.2 raw mapping**, the same dict a YAML file loads into, and hands that to `yaml_form.from_raw`. All validation and every later stage are shared with YAML.

| Language | Song tree |
|---|---|
| header directives | `Song` fields: `instruments`, `groove`, `parts_feel`, `harmony`, `motifs`, `cues`, `mix`, `master`, `qa` |
| one section line or form line (or one `xN` repetition, or one loop iteration) | one `Section`, with `name` set to its instance name and `line` to its source line |
| a section's roles | `Section.parts` via `parse_part`: a reference becomes `"style"` or a motif, a list becomes `motifs`, a part becomes `{style: "full+fill", order: [...], steps: {...}}` |
| lane edits and layers | `PartSpec.steps`. Each step string replaces its lane in expand, so layers are pre-merged with the style's own lane, and `+` adds hits instead of replacing them |
| per-bar lane edits on a kit | per-bar step strings in `PartSpec.steps` |
| other per-bar edits | `PartSpec.variants` (YAML `vary: [{bars: [3, 7], part: ...}]`) |
| `dyn`, `harmony`, `feel`, `tempo`, `key` | the same `Section` fields |
| events and named events | `Song.events`, with positions written as `<instance>+<bar>:<beat>`; an absolute bar stays a number |

`like:`, `add:` and `drop:` are not needed, because `with` and `like=` resolve at compile time. The other direction is [`songmap/parse/fmt.py`](../songmap/parse/fmt.py) (`songmap fmt`). It prints a song as section lines, with `like=`, named part variables and `set` lines, so that parsing the printout gives the same song: `tests/test_fmt.py` checks every example. A program's arrangement digest equals its YAML equivalent's. `tests/test_lang.py` checks this for the three Oct-13 ports in `.sm` and for The Swarm in `.sml`.

## 13. Decisions

These were the prototype's open questions. Each is now settled and implemented, and the decisions are also logged in [DESIGN.md §7](DESIGN.md).

1. **Instance names.** The n-th instance of a section is `<name>_n`, counted only among instances of that same section (`as` overrides). *Inserting or removing other sections never renames an instance, so its cue names and seeds stay put. Only reordering a section's own repeats moves them, and `as` pins those.*
2. **What `every` counts.** Under a form line it counts the instance's own bars; `every N song bars` counts from the song start; at the top of the form block it always counts song bars. *A phrase usually means "this section's 4th bar". Song-wide rules (a crash every 16 bars) need song bars, and the keyword makes the choice visible.*
3. **`+` on strings.** It concatenates; `&` overlays; `+` on beats layers. *This matches Python for text and music for beats. A beat's lanes merge by overlay, so "play both" holds wherever `+` meets drums.*
4. **Value semantics.** `b = a with {...}` copies `a` at that line, and later edits to `a` don't reach `b`. *Each line's meaning is local (read upward only), as with YAML `like:`. Live inheritance would make a line depend on lines below it.*
5. **Per-bar edits on pitched parts.** These compile to part variants (`vary:`), a per-bar mask in expand, rather than to automatic sub-sections. *Sub-sections would add names to `cues.json`, reseed the random parts and restart loops and dynamic arcs. The mask touches only the bars named, and songs without variants expand exactly as before.*
6. **Events as values.** Yes: `lift = !impact !riser:2`, placed with `!lift`, positions relative to where it is placed. *Repeated hit-and-riser groups are the most common repetition in the Oct-13 scores, and naming them shortens The Swarm and Bench.*
7. **Overlay grid.** Layering strings of different lengths puts the result on their common grid, so the written step length of the coarser string shrinks. *The drum voices are one-shots that ignore note length, so the sound doesn't change. Keeping one string per lane keeps lanes printable and editable.*

## 14. The Swarm, rewritten

[`examples/lang/week_oct13_swarm.sml`](../examples/lang/week_oct13_swarm.sml) is the YAML port [`examples/v0.2_yaml/week_oct13_swarm.songmap.yaml`](../examples/v0.2_yaml/week_oct13_swarm.songmap.yaml) written with definitions and a form block. Its arrangement has the same digest (`fe4ba61f…`), the same 3,690 frames and the same 10 events.

```
# The Swarm (2:03): the v0.2 port (examples/v0.2_yaml/week_oct13_swarm.songmap.yaml) in the
# SongMap language. Same notes, same digest (tests/test_lang.py).
song "Week of Oct 13 — The Swarm" 120 4/4 Em fps=30 seed=7 mood=v0 tail=3 video=WeekSwarm:3690
inst bass(cutoff=700)
chords Em C G D /2
master legacy
motif m1 deg oct=5 "0 -3 0 2 | 1/2 0"
motif m2 deg oct=5 "-2 -3 -2 0 | -1/2. -3/4"
motif m3 deg oct=5 "2 0 2 4 | 3/2 2"
motif m4 deg oct=5 "1/4. 0/8 -1/2 | -3/1"

# this song's 12-step arp order, shared by both arp colours
order = [0, 2, 1, 3, 0, 2, 4, 3, 1, 2, 0, 3]
up = up(order=order)
dim = dark(order=order)
lift = !impact !riser:2 !riser:1@+8

terminal = {arp: dim, fx: ticks, bass: sub}
swarm_in = terminal with {drums: four_floor, bass: eighths}
goals = {drums: full+fill, bass: eighths, arp: up, pad: warm}
who = {pad: dark, fx: ticks}
agents = goals with {lead: [m1, m2, m3, m4]}
agents.drums += open
so_what = terminal with {pad: warm}
output = agents with {fx: ticks}
output.drums += hats16
guardrails = so_what with {fx: none}
summary = {pad: warm, arp: up}
end_card = {pad: dark}

form:
  terminal 4
  swarm_in 4    !impact
  goals 8       !riser:1
  who 2
  agents 16     !lift
  so_what 2
  output 16     !lift
  guardrails 4
  summary 2     !impact
  end_card 2    !impact
```

The same song as section lines is [`examples/week_oct13_swarm.sm`](../examples/week_oct13_swarm.sm).

| The Swarm | Whole file | Without comments and blank lines |
|---|---|---|
| v0.2 YAML port | 2,356 chars | 1,761 chars |
| definitions + form (`.sml` above) | 1,302 | **1,081 (1.6× smaller)** |
| section lines (`.sm`, also carries a `qa` line) | 1,423 | 1,158 (1.5×) |

The other two ports, as section lines, are in [COMPACT_FORMAT.md](COMPACT_FORMAT.md).

## 15. Error messages

Errors are one line each: `file:line [section:] what (how to fix it)`.

```
song.sm:4 v: drums style 'full' has no mod '+hat16' (did you mean 'hats16'? valid: fill ghosts hats16 open)
song.sm:3 'chorus' is not a section: it was built from 'vers', which is not defined (did you mean 'verse'? valid: verse)
song.sm:6 'j' is not defined (valid: first i last)
song.sm:4 range 1..100000 has more than 4096 steps (loops have static, small bounds)
song.sm:2 f() calls itself; SongMap functions can't recurse (unroll it with a for loop in the form block)
song.sm:5 'hit' is an event type, so it can't name an event list (pick another name, e.g. hits or my_hit)
song.sm:8 v: bar 5: the section has 4 bars (bars count 1..4 from the start, -1..-4 from the end)
song.sm:7 section lines and a form: block can't be mixed (the first section line is line 5; ...)
```

## 16. Left out

- **Section expressions in the head of a form line** (`(verse with {...}) 8`). Use an edit block under the line instead.
- **Shifting a named event list** (`!lift@+8`). Define a second list with the offsets written in.
- **Per-bar changes to section settings** (`dyn`, `harmony`, `tempo`). Split the section.
