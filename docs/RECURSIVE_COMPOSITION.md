# Nested form, continuous passages and AI composition

Design proposal, 25 October 2026. The Markdown writing contexts are usable now.
The form editor, persistent node identities and suggestion workflow described here
are proposed features. No parser, playback or Studio behavior changes in this work.

## Known facts

SongMap already has the musical building blocks: named drum patterns, motifs,
section maps, `with`, `xN`, nested `for` loops, iteration conditions and per-bar edits.
`tests/test_lang.py::test_nested_loops_and_last` proves nested form evaluation.
`songmap/parse/lang.py::run_form` expands them into placed sections;
`Song.sections` and Studio's `summary.sections` are flat lists. The formatter
preserves musical meaning but prints flat sections, not the original program.
Inline notes also tile when shorter than their section (`arrange/expand.py::_inline`).
Definition assignment has value-copy semantics; it is not a live shared reference.
Procedural/performance randomness can depend on section names, so repeated source
material is not a promise of identical performed notes or audio.

## Product model

Represent the composition as a finite hierarchy and show its expanded timeline.
The hierarchy explains where music comes from; the timeline shows when it plays.
A source definition can be placed several times. Each placement has its own identity,
local context and optional overrides. Selecting a note can reveal its containing
phrase, section, outer cycle and source definition.

Separate three properties:

| Property | Options | Meaning |
| --- | --- | --- |
| Structure | Sequence, parallel layers, bounded repeat, passage | After, together, repeat a group, or play written material |
| Writing method | Pattern-based, through-composed | Tile/develop a pattern, or author the complete passage without automatic tiling |
| Return policy | Reuse, vary selected properties, write a new occurrence | What should be shared when the containing section returns? |

A through-composed eight-bar melody may sit above a one-bar repeated drum groove.
It may be reused whole on a later verse, or have a new written occurrence there.
These are distinct choices. An entire piece can be one through-composed passage,
with internal thematic development and optional local accompaniment ostinatos.
Thematic resemblance is allowed; through-composed does not mean unrelated notes.

Use five semantic node kinds: `sequence`, `parallel`, `repeat`, `passage`, `reference`.
Roles such as verse, chorus, phrase and transition are labels, not additional
incompatible object classes. A repeat wraps any finite subtree, including a
sequence of a verse and chorus. A passage may contain multiple authored parts.

```text
Song · 64 bars
├─ Intro · 4
├─ Verse–chorus cycle ×3
│  ├─ Verse · 8
│  │  ├─ Drums: groove 1 bar ×8
│  │  ├─ Comp: progression/voicing phrase 2 bars ×4
│  │  └─ Melody: continuous 8 bars · new on each return
│  ├─ Chorus · 8 · recognizable hook, permitted ending variants
│  └─ After cycle 2 only: through-composed bridge · 8
└─ Coda · 4
```

The conditional bridge is a single occurrence, not three hidden copies. Group
duration is 16 + 24 + 16 = 56 bars; intro and coda bring the piece to 64.

## Already possible in .sm

This is a structural demonstration, not a finished song or listening recommendation.
It uses existing grammar. The drum grid is local to each section; the bridge has
eight explicitly written piano bars and is placed once.

```sm
song "Nested form study" 100 4/4 C seed=25 tail=2
chords Cmaj7 Am7 Dm7 G7
inst keys=keys/still
mix keys -8 | drums -8 | bass -6

beat = {kick: "X...x...x...x...", snare: "....x.......x...", hat: "x.x.x.x.x.x.x.x."}
intro = {keys: hold, dyn: "p"}
verse = {drums: beat, bass: sub, keys: hold, dyn: "p"}
chorus = verse with {bass: root5, keys: comp, dyn: "mf"}
bridge = {keys: {notes: "=p e2 g4 r4 | f4 e d2 | c4 d e g | f2 d4 r4 | =mp b4 g e4 r4 | a2 g4 e4 | f4 e d2 | =p e2 c2"}, dyn: "p"}
coda = {keys: hold, dyn: "p"}

form:
  intro 4
  for cycle in 1..3:
    verse 8:
      every 4 bars: drums.snare += "............x.x."
    chorus 8:
      if cycle == 3: drums += {clap: "....x.......x..."}
    if cycle == 2:
      bridge 8
  coda 4
```

The bridge's written phrase covers its full eight-bar span. If it contained only
four written bars, the engine would tile those twice under `bridge 8`. Naming a
section “bridge” or “continuous” does not disable current automatic tiling. The
future inspector should show written length and repeat count rather than infer
continuity from a label.

## Source and identity contract

Keep `.sm` as musical source of truth. Preserve its concrete syntax (comments,
definitions and control flow) when editing structure. Build a semantic form projection
with source spans and binding identities during parsing/evaluation. The existing
indentation `Node` is syntactic scaffolding, not yet the complete editable model.
Do not infer loops by matching similar flat section names or note fingerprints.

Suggested compilation boundary:

```text
.sm + optional composition annotations
  → preserved syntax + semantic form projection
  → resolved occurrences and provenance
  → existing Song / Timeline / performed events / renderer
```

An optional adjacent `<score>.compose.json` stores stable node IDs, source anchors,
context-file associations, locks and writing/return intent. It does not duplicate
notes, chord sequences or the executable form. Detect stale anchors against a
source revision; never silently attach a context to the wrong node after text edits.
Legacy .sm and YAML files require no sidecar and retain their current sound.

Each resolved occurrence needs `occurrence_id`, `definition_id`, `binding_id`,
`parent_occurrence_id`, `repeat_path`, `source_span`, effective overrides,
written/performed content hashes and musical start/end positions. Binding identity
matters because a name can be rebound inside a loop and `with` copies values at
the point of evaluation. Editing a shared definition must list all affected uses,
including derived definitions that will change when the program is re-evaluated.
Placement IDs must survive inserting an unrelated sibling; line numbers and
ordinal paths alone are not stable identities.

## Timing, repetition and boundaries

Sequence duration is the sum of children; a parallel group's explicit span bounds
its layers; repeat duration is the sum of resolved iterations, including conditional
children. Resolve bars through each section's meter into quarter-note beats, then
through the existing tempo map into seconds. Do not assume four beats per bar or
that every iteration has the same length. Show local and song bar numbers together.

Repeating material has an explicit phase policy: restart at placement, continue
from an enclosing pattern, or align to a named grid. Default to current section-local
behavior for imported scores. Non-dividing patterns require an explicit trim,
carry or pad decision; do not silently reset a five-bar phrase at an eight-bar edge.
Pickup notes, ties, release tails and fill exits belong to a named boundary and
must survive preview windows. A continuous part must account for its entire span
with written notes/holds/rests; shorter material is an error under that proposed
policy, never implicit looping. Ordinary long rests remain valid.

“Reuse material” keeps its written decisions. A separately selectable frozen
performance can also keep realized timing/velocity/chance outcomes. Do not call
legacy procedural repeats exact audio copies. Preserve legacy CRC32 seed behavior;
new policies should use stable definition/variant IDs and explicit occurrence
variation, never Python `hash()` or mutable display names. Changing a repeat count
must not regenerate previously accepted occurrences.

No infinite playback loops in a saved composition. Bound depth, references, expanded
placements, events and duration; reject reference cycles before expansion. Retain
the interpreter's existing 4096-step budget until an explicit compatible revision.

## Studio interaction

Use a **Form** view next to the existing arrangement and score views. A collapsible
outline shows sequence groups, repeat counts and writing methods. The expanded
timeline stays aligned below it, with iteration bands and a breadcrumb to the
selected placement. Double-click descends into a group; the score view shows that
group's actual performed notes and can zoom to the current bar.

The inspector first shows role, duration, occurrence, source, entry/exit harmony
and return policy. Show **This occurrence** and **Shared definition · N uses** as
explicit edit scopes. Default ordinary local edits to this occurrence. Changing
shared material previews the affected list; detaching makes an independent copy.
A through-composed node opens a continuous score instead of a pattern grid.

Support selecting several adjacent sections and choosing **Group → Repeat ×3**;
the group remains visible even before adding a repeat. Repeated instrument lanes
show `1 bar ×8` or `2 bars ×4`, while the melody lane can read `8 bars continuous`.
Distinguish composition repeats from the transport's temporary audition loop.
Keep each player's current note names and compact score panels from Score focus.

Use shape/text as well as color: repeat badge, continuous line, linked-instance
symbol and overridden-field marker. Keyboard navigation reaches nodes, breadcrumbs,
repeat count and edit scope. On small screens show the selected level with a
breadcrumb; do not squeeze the whole tree beside an unreadable score.

## Context and suggestion flow

Load [composition contexts](composition/README.md) by writing method and task.
Node-specific briefs use [context-template.md](composition/context-template.md).
Markdown supplies intent and craft; the executable score and validated constraints
still determine notes, timing, tuning and allowed changes.

For the selected node, assemble ancestor purpose and form position, current
occurrence's entry/exit state, harmony/key/meter map, instrument ranges, protected
motif, return policy, nearby performed notes, prior accepted choices and the
small relevant writing contexts. Locks accumulate; a child cannot weaken an ancestor
lock. More local unlocked choices can override general preferences. Report a real
constraint conflict rather than inventing a resolution.

Suggest two or three actions that address the node's current musical job:

| Selected material | Useful suggestion | Preserve |
| --- | --- | --- |
| One-bar groove | Fill only at the final bar; alternate hat response | Kick/bass anchors and playable kit |
| Four-bar melody | Answer the question; develop the final two bars | Recognizable opening and breathing space |
| Returning chorus | Add a counterline; broaden the last arrival | Hook, approved melody balance and duration |
| Verse–chorus boundary | Pickup, one-bar fill, shared-tone suspension | Following downbeat and arrival harmony |
| Key-changing bridge | Common-tone route or deliberate direct arrival | Destination, tuning and protected voices |
| One continuous piece | Develop a motif toward the next arrival | Whole-piece arc; no forced verse/chorus template |

The starting vocabulary in `composition/form-patterns.json` is editorial guidance,
not a learned frequency ranking. Attach Harmony Library progression IDs where useful
(for example `p049` major ii–V–I or `p016` minor-plagal color), but check chord fit,
bar budget and voice leading against the actual score. Library chord pairs are
harmonic transitions, not complete fills, phrase transitions or orchestration plans.

Pipeline: select scope → suggest action → author a frozen candidate → compile/check
boundaries → render a contextual audition → compare → adopt or revise. Playback
never calls AI. Regenerate only the requested instance/properties, retaining accepted
ancestors and descendants. Within an authorized delegated pass, routine steps can
proceed automatically; do not require a new chat confirmation for each instrument.
Adoption, favorite and lock remain separate states, and AI choice is not a human vote.

Existing Riff and Arrangement comparisons require aligned section timing, so use them
only for compatible node auditions. A topology, duration, meter or section-order
change needs a distinct future **Form comparison** contract with semantic boundary
alignment. A fixed 1–30 second waveform switch is not sufficient proof of a successful
whole-form edit. Include each transition's lead-in and destination in the audition.

## Actions and acceptance

All musical writes are reversible score revisions with source-hash conflict checks.
Normal local composition edits need no extra approval beyond the user's scope.

| ID | Action | Observable result / acceptance target |
| --- | --- | --- |
| RC01 | Inspect a group / occurrence | Tree, breadcrumb, timeline and score point to the same performed events |
| RC02 | Group and set repeat count | Correct expanded duration; prior occurrence IDs/content remain stable |
| RC03 | Edit this occurrence | Other uses and unrelated source regions remain unchanged |
| RC04 | Edit shared definition | Exact affected-use list; all dependent uses update; undo restores source |
| RC05 | Detach an occurrence | Independent identity and content; later shared edits leave it unchanged |
| RC06 | Set writing/return policy | One continuous melody can coexist with repeating accompaniment |
| RC07 | Load node contexts | Correct small context set and ancestor locks; stale association is visible |
| RC08 | Suggest and audition | Candidate changes stay within allowed fields; pickup and arrival are included |
| RC09 | Adopt / undo candidate | Valid score, preserved provenance, explicit human/AI decision origin |
| RC10 | Reconcile a text edit | Updated hierarchy or clear stale/unsupported state; no fabricated structure |

Acceptance fixtures: nested groove/phrase/section/cycle repeats; through-composed leaf
inside a repeat with both reuse and new-occurrence policies; a whole piece as one leaf;
different meters/tempos; a one-time conditional bridge; a five-against-eight span;
cross-boundary pickups/ties; definition rebinding/copy semantics; stable IDs after
sibling insertion; no reroll after transport seeks; unsupported syntax kept editable;
bounded expansion and cyclic-reference failure; legacy event digests unchanged.

## Delivery sequence

1. **Expose existing form:** preserved syntax, read-only hierarchy/provenance API,
   nested selection and local/expanded timing; legacy flat-file import as one sequence.
2. **Author structure safely:** scoped source edits, repeat/group controls, detach,
   context associations and explicit continuous-span validation. Retain the existing
   renderer; introduce only the missing policies with focused compatibility tests.
3. **Suggest in context:** small pattern vocabulary, Harmony Library retrieval,
   node-scoped candidates, return development, contextual auditions and semantic form
   comparison. Integrate current AI Lab where its timing contract fits.

## Likely commands and relevant paths

Run `.venv/Scripts/python -m pytest tests/test_lang.py -q`
for the existing language boundary, then
targeted source-map and node-edit tests as those features are implemented.
Frontend build: `npm run build` in `songmap/gui/web`. Relevant code:
`parse/lang.py`, `parse/fmt.py`, `model.py`, `arrange/expand.py`,
`arrange/timeline.py`, `gui/project.py`, `gui/lab_score.py`, `gui/music_lab.py`,
`gui/harmony_library.py`, and `gui/web/src/{Arrangement,LabScore,InstrumentLab}.tsx`.

## Prior art and limits

[music21's hierarchy documentation](https://music21.org/music21docs/usersGuide/usersGuide_06_stream2.html)
demonstrates nested musical containers with local offsets and flattened views.
[Ableton's documented scene and clip Follow Actions](https://help.ableton.com/hc/en-us/articles/360019101360-Updates-to-Follow-Actions-in-Live-11)
illustrate controls at more than one musical scale. Those support the interaction
analogy; they do not establish that SongMap already has these editors or AI policies.

Open questions for later listening/design review: which suggestions the user finds
useful and how much structural AI autonomy they prefer. Neither blocks these guides
or the first read-only form view. Live probabilistic performance, audio warping,
new synthesis and a replacement score language are outside this proposal.

## Verification of this design package

Both fenced `.sm` examples parse and expand in the current engine: the nested form
is 64 bars with one bridge, and the continuous example is one eight-bar section.
The existing language suite passed **85 tests**. The 15 starter patterns have unique
IDs and valid context-file and Harmony Library links. The JSON contract's nine
acceptance fixtures reference the ten documented actions; these are planned tests,
not claims that the editor actions are already implemented.

The Form map / Score focus design study was inspected in a browser. Changing three
outer cycles to four changed the resolved form from 64 to 80 bars; writing-policy,
local/shared proposal scope and targeted fill/answer sketches responded. The 390px
check had no horizontal body/app overflow, and the browser reported no script errors.
These checks establish the prototype interactions only. No new production UI or
automatic music generator was shipped by this design work.
