# The SongMap language (`.sml`)

A small programming layer for song maps. It gives you:
- named beats, parts and sections;
- `with` and dotted assignment (`chorus.drums.kick = "x..x..x."`);
- `+` to layer drum lanes;
- the song's form as a block of section references with bar counts;
- loops (`x4`, `for i in 1..4:`) and conditions (`if i == last:`, `every 8 bars:`);
- small functions (`def four(acc=0.8): ...`);
- operators on step strings.

The language **compiles to the existing `Song` tree**. Under it, expand, render, the golden tests and `cues.json` are unchanged: a program means exactly what its compiled YAML song map would mean. The prototype is [`songmap/parse/lang.py`](../songmap/parse/lang.py), and `songmap check` and `songmap render` read `.sml` files.

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

A program is evaluated once, top to bottom. Each line is one of the following:
- a header directive;
- a definition (`name = value`);
- an edit (`name.role = value`, `name.role.lane += "..."`);
- a function (`def`);
- the `form:` block.

**Header directives** are the compact format's lines ([COMPACT_FORMAT.md](COMPACT_FORMAT.md)), kept verbatim so that both spellings share them:

```
song "<title>" <tempo> <meter> <key> [fps= seed= mood= tail= tuning= video=<Composition>:<frames>]
inst <part>[=<instrument>[/<preset>]][(k=v, ...)] ...      e.g. inst bass(cutoff=700) keys=keys/felt_piano
kit <piece>=<instrument>[/<preset>] ...
chords <chord> ... [/<bars per chord>]
prog <name> "<chord:bars ...>"
motif <name> [deg|rel] [oct=<n>] [key=<key>] "<note language>"
cue <name>=<position>
master legacy|standard [lufs=] [ceiling=] [glue=] [contrast=]
```

The prototype does not read `groove`, `feel`, `mix` or `qa` yet. Each of them raises an error that says so.

**Values:**

| Value | Written | Notes |
|---|---|---|
| number | `8`, `0.8`, `-2` | |
| string | `"x...x..."` | step strings, note text, chord text |
| boolean, nothing | `true` `false` `none` | `none` removes a key in `with` and in dotted assignment |
| list | `[m1, m2, m3]` | indexing is 0-based and **cyclic**: `xs[i]` never runs out |
| map | `{kick: "x...", hat: "-.x."}` | keys are names or strings; order is kept |
| part | `full`, `full+fill`, `up(order=[0,2,1,3])`, `{deg: "0 2 4"}` | what one role plays in a section |
| section | `{drums: full, bass: sub, dyn: "p<f"}` | a map from role to part, plus section settings |
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

A misspelt variable therefore surfaces at its use, with a suggestion:

```
song.sml:2 v: unknown drums style 'ful' (did you mean 'full'? valid: four_floor full half half_kick)
```

A definition may shadow a style with a variant of itself, because the right side is evaluated first: `up = up(order=order)`.

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

Layering two step strings keeps the louder step at each position (`X > f > r > x > - > o > .`). Two strings with different bar lengths are placed on their common grid.

`-` removes a mod: `drums - fill`.

**Dotted assignment** edits one field of a definition and rebinds the name to the edited copy:

```
chorus.drums = full + hats16          # replace the part
chorus.drums += open                  # add a mod
chorus.drums.kick = "x..x..x."        # replace one lane
chorus.drums.kick += "....x..."       # layer onto the lane (including the style's kick)
chorus.pad = none                     # remove the part
```

**Values, not references.** `b = a with {...}` copies `a` at that line. A later `a.drums = ...` does not change `b`. This is the YAML `like:` rule, and it keeps every line's meaning local: to know what `b` is, read upward.

## 3. The form block

`form:` is the song. Each line places a section:

```
form:
  <section> [<bars>] [xN] [as <name>] [!event ...] [: <edit> | indented edits]
```

- **`<bars>`** is any expression, so `chorus 4*i` works.
- **Names.** The first instance of `verse` is called `verse`; later ones are `verse_2`, `verse_3` and so on. `as outro` names an instance explicitly. These names appear in `cues.json`, in event positions (`@verse_2+4`) and in the per-section seeds.
- **Events** use the compact syntax: `!type[:bars | :<beats>b][@position][(k=v, ...)]`. Positions:
  - `@+8:2` is relative to this instance's start;
  - `@12` is an absolute bar;
  - `@f3960` is a video frame;
  - `@cue:x` is a named cue.

  An event line on its own in the form needs an absolute position.
- **Edits under a form line** change that instance only. In them, a target's first name is a *role*, so `drums += fill` means "this instance's drums".

```
  bridge 8:
    dyn = "p<f"
    drums.kick = euclid(3, 8)
    !riser:2@+6
```

## 4. Repetition

**`xN`** places a section N times. Under a repeated line, `rep` is the repetition number (1..N), and `first`/`last` are 1 and N:

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

## 5. Conditions

**Per iteration:** `if`, `elif` and `else` are evaluated as the form unrolls. They can sit around form lines or under one:

```
  for i in 1..4:
    if i % 2 == 1:
      verse 8
    else:
      chorus 8:
        if i == last: drums += fill
```

**Per bar:** `every N bars [at K]: <role> += <beat>` applies an edit to the K-th bar of every group of N bars. K defaults to N, the last bar of each group.
- Under a form line, the bars are counted within that instance.
- At the top of the form block, they are counted from the song start and apply to every instance that has the role.

The right-hand side may also be a set/add mod of the part's style, or a lane edit such as `drums.snare = "...x"`.

```
form:
  every 16 bars: drums += {ohat: "x..............."}      # song bars 16, 32, ...
  verse 8:
    every 4 bars at 1: drums.kick += "x.x............."  # bars 1 and 5 of this verse
```

Per-bar edits work on drum kits. They compile to per-bar step strings (`"a|a|a|b"`), which the engine already cycles bar by bar. A pitched part needs the section split instead, for example `verse 7` followed by a one-bar variant. Phrase mods that already have their own period, such as the styles' `fill` (every 8 song bars), are refused with a hint to use them without `every`.

## 6. Functions

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
- A function sees the definitions above it, a snapshot taken at the `def` line, so it cannot call itself. Passing a function to itself is caught at the call: `f() calls itself; SongMap functions can't recurse`.
- Calling a style is shorthand for options: `up(order=[0, 2, 1, 3])` means `up with {order: [...]}`.

## 7. Step-string operators

| Expression | Result | Meaning |
|---|---|---|
| `"x..." + "..x."` | `"x.....x."` | concatenate (one bar on a finer grid) |
| `"x.x." * 4` | `"x.x.x.x.x.x.x.x."` | repeat |
| `"x...x..." \| "x.x.x.x."` | `"x...x...\|x.x.x.x."` | join bars (lanes cycle bar by bar) |
| `"x...x..." & "..x...x."` | `"x.x.x.x."` | overlay, louder step wins |
| `rot("x..x..x.", 2)` | `"x.x..x.."` | rotate each bar right (negative: left) |
| `rev("x..x....")` | `"....x..x"` | reverse each bar |
| `euclid(3, 8)` | `"x..x..x."` | Bjorklund: k hits spread over n steps; `euclid(k, n, rot)` rotates |

`+` concatenates strings but layers beats. Inside beats the same idea becomes "play both": `{kick: a} + {kick: b}` is `{kick: a & b}`.

## 8. What it leaves out on purpose

- **No unbounded loops or recursion.** There is no `while`, and functions cannot recurse. Loops run over ranges and lists whose values are known when the file is read. The whole form may unroll to at most 4,096 steps, and lists and step strings are capped at 4,096 items.
- **No input, no clock, no randomness.** A program is a pure function of its text. Randomness stays in the engine, seeded with crc32 from the song seed, section, part and bar.

So every program terminates quickly with one song tree. `songmap check` still reports the exact length:

```
ok: Week of Oct 13 — The Swarm
  10 sections, 60 bars at 120 BPM 4/4, 2:03.00 (3690 frames @ 30 fps)
```

The language is not Turing complete, and it doesn't need to be. Anything generative, such as a Markov melody or a search over grooves, belongs in Python that writes a song map.

## 9. Grammar

Blocks are indented with spaces. A line ending in `:` opens a block, or the statement can follow the `:` on the same line. Brackets continue a line, and `#` starts a comment.

```
program   := (directive | def | assign | form)*
directive := ("song" | "inst" | "kit" | "chords" | "prog" | "motif" | "cue" | "master") <compact-format arguments>
def       := "def" NAME "(" [param ("," param)*] ")" ":" (expr | INDENT (assign | if | "return" expr)+ DEDENT)
param     := NAME ["=" expr]
assign    := target ("=" | "+=" | "-=") expr
target    := NAME ("." NAME)*                      # in edits under a form line, NAME is a role
form      := "form" ":" INDENT formstmt+ DEDENT
formstmt  := place | for | if | every | assign | events
place     := NAME [expr] ["x" INT] ["as" NAME] events? [":" (edit | INDENT edit+ DEDENT)]
edit      := assign | if | every | events
for       := "for" NAME "in" expr ":" block           # expr: a range a..b or a list
if        := "if" expr ":" block ("elif" expr ":" block)* ["else" ":" block]
every     := "every" expr ["bars"] ["at" expr] ":" assign+
events    := ("!" NAME [":" NUM ["b"]] ["@" position] ["(" k=v ("," k=v)* ")"])+

expr      := with ["if" with "else" expr]
with      := or ("with" or)*
or        := and ("or" and)*          and := not ("and" not)*          not := "not" not | cmp
cmp       := range [("==" | "!=" | "<" | "<=" | ">" | ">=") range]
range     := bar [".." bar]           bar := amp ("|" amp)*            amp := sum ("&" sum)*
sum       := term (("+" | "-") term)* term := unary (("*" | "/" | "//" | "%") unary)*
unary     := "-" unary | postfix      postfix := atom ("(" args ")" | "[" expr "]" | "." NAME)*
atom      := NUMBER | STRING | NAME | "true" | "false" | "none" | "(" expr ")"
           | "[" [expr ("," expr)*] "]" | "{" [key ":" expr ("," key ":" expr)*] "}"
```

`with` binds loosest of the binary operators, so `a + b with {...}` is `(a + b) with {...}`.

## 10. How it maps onto the `Song` tree

The evaluator unrolls the form into a list of instances. It then writes the **v0.2 raw mapping**, the same dict a YAML file loads into, and hands that to `yaml_form.from_raw`. All validation and every later stage are shared with YAML.

| Language | Song tree |
|---|---|
| `song`, `inst`, `chords`, `motif`, ... | `Song` fields, `instruments`, `harmony`, `motifs` |
| one form line (or one `xN` repetition, or one loop iteration) | one `Section`, with `name` set to its instance name and `line` to the form line |
| a section map's roles | `Section.parts` via `parse_part`: a reference becomes `"style"` or a motif, a list becomes `motifs`, a part becomes `{style: "full+fill", order: [...], steps: {...}}` |
| lane edits and layers | `PartSpec.steps` (each replaces its lane in expand). Layers are pre-merged with the style's own lane, so `+` adds hits instead of replacing them |
| `every` | per-bar step strings in `PartSpec.steps` |
| `dyn`, `harmony`, `feel`, `tempo`, `key` in a section map | the same `Section` fields |
| `!events` | `Song.events`, with positions written as `<instance>+<bar>:<beat>` |

`like:`, `add:` and `drop:` are not needed, because `with` resolves them at compile time. The arrangement digest of a program equals that of its YAML equivalent. `tests/test_lang.py` checks this for The Swarm.

## 11. `.sm` (P6): one grammar, not two

**Recommendation: make this language the `.sm` grammar.** The P6 compact parser then becomes this parser plus one extra statement, the section line. Keep `.sml` as an alias until P6 lands.

The section line `name bars | role:style ... | !events` becomes sugar for a definition followed by a form line:

```
goals 8 | drums:full+fill bass:eighths arp:up | !riser:1
  ≡  goals = {drums: full+fill, bass: eighths, arp: up}      and, in the form:  goals 8 !riser:1
```

A file with section lines and no `form:` block gets its form from those lines in order.

Reasons:
1. **One thing to learn.** The LLM loop in COMPACT_FORMAT.md depends on a small catalog and one cheat sheet. Two dialects with overlapping directives would double both, and they would drift apart.
2. **The header is already shared.** `song`, `inst`, `chords`, `motif`, `cue` and `master` are identical in both. The language only adds statements.
3. **Flat files stay valid.** Loops, `with` and functions are opt-in. A song that needs none of them is still one line per section, and stays line-addressable.
4. **Same target.** Both compile to the v0.2 raw mapping and then to `Song`. A second extension would be a second front end for the same back end.

The cost is that P6 must accept two spellings of a part map: compact `role:style` tokens on section lines, and `{role: style}` maps in expressions. That is a small lexer concern. The section-line tokens can parse into exactly the map this prototype builds.

## 12. The Swarm, rewritten

[`examples/lang/week_oct13_swarm.sml`](../examples/lang/week_oct13_swarm.sml) is the YAML port [`examples/v0.2_yaml/week_oct13_swarm.songmap.yaml`](../examples/v0.2_yaml/week_oct13_swarm.songmap.yaml) in the language. Its expanded arrangement has the same digest (`fe4ba61f…`), the same 3,690 frames and the same 10 events.

```
# The Swarm (2:03): the v0.2 port (examples/v0.2_yaml/week_oct13_swarm.songmap.yaml) in the
# SongMap language. Same notes, same digest (tests/test_lang.py).
song "Week of Oct 13 — The Swarm" 120 4/4 Em fps=30 seed=7 mood=techno tail=3 video=WeekSwarm:3690
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
  agents 16     !impact !riser:2 !riser:1@+8
  so_what 2
  output 16     !impact !riser:2 !riser:1@+8
  guardrails 4
  summary 2     !impact
  end_card 2    !impact
```

| The Swarm | Whole file | Without comments and blank lines |
|---|---|---|
| v0.2 YAML port | 2,356 chars | 1,761 chars |
| SongMap language | 1,312 chars | **1,091 chars (1.6× smaller)** |
| compact `.sm` sketch (not parsed yet; also carries `groove`, `mix` and `qa` lines) | 1,364 | 1,204 |

The savings come from two places. Repeated material is now named once (`terminal`, `so_what`, `order`), where the YAML needed anchors under `x-` keys. Events move onto the form lines. Two places where the YAML was shorter: `with` chains spell out which section each derives from, and the header line is the same as in `.sm`.

## 13. Error messages

Errors are one line each: `file:line [section:] what (how to fix it)`.

```
song.sml:4 v: drums style 'full' has no mod '+hat16' (did you mean 'hats16'? valid: fill ghosts hats16 open)
song.sml:3 'chorus' is not a section: it was built from 'vers', which is not defined (did you mean 'verse'? valid: verse)
song.sml:6 'j' is not defined (valid: first i last)
song.sml:4 range 1..100000 has more than 4096 steps (loops have static, small bounds)
song.sml:2 f() calls itself; SongMap functions can't recurse (unroll it with a for loop in the form block)
song.sml:5 v: every: per-bar edits work on drum kits, and bass is not one (split the section instead: v 3 then a 1-bar variant)
song.sml:2 v: arp: unknown part option 'oder' (arp is not a drum kit, so it has no lanes) (did you mean 'order'? ...)
```

## 14. Status and open questions

**The prototype implements everything above**, apart from the `groove`, `feel`, `mix` and `qa` directives (P6), a section expression in the head of a form line (`(verse with {...}) 8`; use an edit block under the line instead), and `every` on pitched parts.

**Open questions:**
1. **Instance names under edits.** The second `verse` is `verse_2`. Inserting a verse earlier in the form renames the later ones, which moves their cue names and their per-section seeds (tick scatter, pan). An alternative is to name every instance by its base plus an ordinal that stays fixed, or to always require `as` when a section repeats. The current rule matches what people write by hand.
2. **Counting for `every`.** Under a form line, it counts the instance's own bars. The styles' phrase mods (`fill`) count song bars, like synth_v0. Should instance counting be the default, with `every 8 song bars:` for the other?
3. **`+` on strings.** It concatenates strings but layers beats, and `&` is the string overlay. An alternative is to make `+` overlay everywhere and add a `concat`. The current choice follows Python for strings and music for beats.
4. **Value semantics.** `b = a with {...}` copies `a`, so edits to `a` must come before the copy (in The Swarm, `agents.drums += open` precedes `output = agents with ...`). Live inheritance, where `b` follows later edits of `a`, would read more like a score but makes a line's meaning depend on lines below it.
5. **Per-bar edits on pitched parts.** These need either automatic sub-sections, which would add names to cues, or a per-bar mask in `PartSpec`, which is an expand change. A mask fits P4's mute masks.
6. **Events as values.** `drop = !impact !riser:2` reused on several form lines would shorten The Swarm further. Should events be values?
7. **Overlay grid.** Layering `"x..."` (4 steps) with an 8-step string puts the result on 8 steps, so the written durations of the existing hits halve. That doesn't matter for drums today (they are one-shots), but it might for gated pieces.
