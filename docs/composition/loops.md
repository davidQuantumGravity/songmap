# Write recurring material

Use when the same musical identity should return: a groove, ostinato, phrase,
section, or a sequence such as verse–chorus. Work at the requested scale.

Before writing, state the unit's length, role, entry/exit harmony and what makes it
recognizable. Choose its return policy: reuse the written material, vary named
properties, or author a separate occurrence. Keep phrase rests and release space.

- Preserve the anchor: kick/bass arrival, hook rhythm, bass contour or chord rhythm.
- Make the seam work. Check the last bar into the first and the exit into the next
  section. A strong loop ending may need a different final exit.
- Author a useful variation, not an arbitrary change on a timer. A last-bar fill,
  two-bar answer, removed attack or changed voicing may be enough. Exact recurrence
  and silence are valid when they serve the phrase.
- Separate repetition scales. Drums may repeat every bar, comping every two bars,
  harmony every four and melody every eight. Do not restart all parts together just
  because the smallest loop repeats.
- Treat a kit as one playable musician. During a fill, remove impossible simultaneous
  hits and preserve the bass relationship. More cymbals are not an automatic climax.
- On later returns, develop the arrangement around a liked motif before replacing
  it. Keep unfamiliar golden pitches supported by calm timbre and restrained level.

Current `.sm` tools: named lane maps, named motifs, section maps, `with`, `xN`,
nested `for`, `if cycle == ...`, `every 4 bars` and `bar -1`. Definitions copy values
at evaluation time. A later dotted assignment is not a live edit of earlier copies.
`first`/`last` refer to the innermost loop: use explicitly named outer variables when
you mean the third verse–chorus cycle.

Write each instrument's actual notes, then expression, and review in the ensemble.
Reuse is a deliberate musical decision; filling an entire piece with default styles
and new patches does not complete that writing pass.

Check the repeated unit, a middle occurrence, every exceptional occurrence and the
final exit. Random performance/chance can differ between current section instances.
Do not claim identical rendered repeats unless their performed events were checked.

Report what stays fixed, what develops, which occurrences changed and what still
needs a listening judgment. Render candidates once; never regenerate them during
playback or silently reroll previously accepted material.
