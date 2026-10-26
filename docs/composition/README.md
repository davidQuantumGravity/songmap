# Writing contexts for SongMap

These short Markdown files are context for a human or AI composer. They do not
execute, add parser directives or automatically attach themselves to Studio nodes.
Use them now alongside the current `.sm` language and composition skill. Proposed
automatic node attachment is described in [the form design](../RECURSIVE_COMPOSITION.md).

| Task | Read |
| --- | --- |
| Repeat a groove, phrase, section or group | [loops.md](loops.md) |
| Write a complete passage without automatic tiling | [through-composed.md](through-composed.md) |
| Combine stable accompaniment with continuous development | [hybrid.md](hybrid.md) |
| Connect passages, endings, returns or keys | [transitions.md](transitions.md) |
| Describe a particular node's purpose and constraints | [context-template.md](context-template.md) |
| Suggest an initial form or phrase pattern | [form-patterns.json](form-patterns.json) |

Load the general SongMap composition skill once, the piece brief, the ancestor
summary and only the contexts relevant to the requested task. A groove edit does
not need the entire song's note text, but it does need its bass relationship and
entry/exit context. A form edit needs the full structural map and arrival goals.

Keep executable facts in `.sm`: notes, durations, chords, instruments, dynamics,
meter, tempo and events. Keep purpose, protected identity, allowed development and
listening criteria in the node brief. The proposed machine-enforced locks live in
validated annotations; prose is not an enforcement mechanism.

Suggestions are options to audition. Technical QA cannot establish a likeable tune,
and a user's acceptance of a motif does not approve every later orchestration.
