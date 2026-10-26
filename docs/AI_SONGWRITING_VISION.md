# AI songwriting through listening and comparison

Product vision, 23 October 2026. The full songwriting workflows below are proposed behavior. On 24 October, [AI Lab](AI_LAB.md) implemented inventory and improvement priorities plus durable A/B comparisons for instruments, riffs, arrangements and saved snippets, scoped feedback, Codex challengers for musical edits, and explicit application or undo. These are bounded comparison tools; the complete blank-brief songwriting journey remains proposed. The broader implementation boundaries and existing foundations are identified near the end.

**SongMap should let a creator develop an entire song through listening, choosing, and directing AI.** A blank project can become a finished piece without requiring the user to write notes, program instruments, or operate a full DAW. The creator can also intervene at any depth, from a short instruction to an individual note, and return control to AI immediately afterward.

The central interaction is a musical proposal followed by an audible choice. The user describes an intention, SongMap generates alternatives, and the user selects, edits, combines, or delegates. The next proposal builds on the accepted material and the feedback. This applies to instrumentation, sound design, notes, expression, harmony, rhythm, structure, transitions, arrangement, and mixing.

Creator control means retaining the score, instrument definitions, performance detail, stems, source assets, and revision history. The product should make that material portable and editable through documented formats. A strategic aim is to give creators and general language models a larger role in music production. Adoption and market-share effects are business hypotheses to evaluate.

[Nested form and continuous composition](RECURSIVE_COMPOSITION.md) develops the proposed structural workflow:
visible repeats within repeats, per-layer through-composed writing, occurrence-scoped edits and contextual pattern
suggestions. Its [Markdown writing contexts](composition/README.md) are available now; the form editor and node-aware
AI pipeline remain proposed.

**A blank project should offer one prompt and several ways to begin.** The user can describe a mood, genre, scene, length, reference qualities, musical technique, or desired instruments. Partial instructions are enough. SongMap makes reasonable, visible assumptions and starts making music. It should request a decision only when that decision materially affects the direction, or when the user has chosen to supervise it.

Examples of equally valid starting points include a lead melody, chord progression, bass riff, drum groove, proposed structure, instrument palette, imported clip, and an empty timeline. A future recording workflow can begin with a played or sung idea. The order is flexible. Instrument selection can precede the first phrase or follow it, and an existing phrase can be tried with several instrument palettes.

For a prompt such as "a warm, restless instrumental that gradually opens up," the AI might suggest two instrument lists. One uses fingerstyle electric bass, acoustic drums, electric piano, and a plucked lead. The other uses upright bass, a restrained kit, mallets, and a soft synth. Each list explains the musical roles and, when rendered, provides a short audible sketch. These are tentative palettes. The user can choose A, choose B, combine parts, replace an instrument, ask for another direction, or let AI decide.

An instrument audition should expose the sound in a plausible register and performance. A palette sketch can require different voicings to suit its instruments. The comparison must identify those changes so it is clear whether the user is judging timbre alone or a broader arrangement.

**The song grows through revisitable decisions.** The following journey is one possible route, with every step available later from the timeline.

| Moment | AI work | Creator choices |
|---|---|---|
| Brief | Interpret the prompt, record assumptions, suggest a direction | Edit the brief or begin immediately |
| Palette | Propose two instrument lists with roles and audible sketches | A, B, merge, replace, or delegate |
| Instrument | Select a voice or design a patch, then demonstrate its useful expression | Refine the sound or move on |
| Seed | Write two purposeful riffs, melodies, chord sequences, or grooves | Choose, combine, edit, or reject both |
| Refinement | Challenge the current favorite with a targeted alternative | Keep the favorite or adopt the challenger |
| Ensemble | Develop accompanying parts one instrument at a time | Compare the whole arrangement or individual contributions |
| Form | Propose a structure, or extend outward from the accepted material | Build forward, backward, or around a destination |
| Transition | Write a lead-in, exit, modulation, breakdown, or return | Compare the route and its effect in context |
| Development | Transform motifs, create contrast, and shape the energy across sections | Preserve anchors and explore alternatives elsewhere |
| Performance | Complete detailed expression and check ensemble relationships | Compare feel, technique, dynamics, and articulation |
| Finish | Review the whole form, balance the mix, resolve problems, and export | Reopen any detail or accept a finished revision |

The ongoing comparison can follow the user's example exactly: A versus B, then the accepted A versus C, then the accepted C versus D. If C remains preferred, keep C and move on. Candidate identities remain stable in history even if blind auditions randomize the on-screen A/B labels.

Acceptance should mean "use this in the current version." A separate lock means "preserve this during further work." A favorite can also be saved without applying it. These distinctions allow a promising idea to survive without forcing it into the current song.

**The AI should recommend the next useful musical action.** After accepting a melody, the main action might be "Write accompaniment," with alternatives such as "Try another harmony," "Write what comes before," and "Build the chorus." The recommendation depends on the brief, accepted material, unresolved choices, and the user's preferred amount of involvement.

The user can ask for any other action in ordinary language. They should never need to complete a fixed wizard to reach the timeline. A project can pause, reopen, or change direction at any stage. A song plan records provisional sections, thematic relationships, harmonic destinations, and energy goals while allowing the form to evolve.

A request to move from key X to key Y should produce a route with an audible purpose: for example, a shared-tone passage or a more abrupt arrival. Audition the lead-in, transition, and destination together. Preserve the project's tuning system, including 36-ET when selected. The UI can offer a short explanation of the technique without requiring theory knowledge to make the choice.

**Each generation needs a musical question.** Alternatives should explore distinct, intentional possibilities. A melody pair might contrast a spacious line with a more syncopated reply. An instrument pair might compare attack and sustain while holding the notes fixed. Freer experiments can change several musical dimensions, provided the scope and changes are visible.

| Comparison | Typical editable material | Typical fixed context |
|---|---|---|
| Instrument | Sampled voice, individual kit piece, synth patch, sound parameters | Written notes and expression |
| Performance | Dynamics, articulation, microtiming, releases, ghost notes | Pitches and the intended rhythmic structure |
| Riff or melody | Pitches, rhythm, rests, phrase development | Selected harmony and surrounding parts |
| Harmony or rhythm | Voicing, harmonic movement, groove, meter where allowed | Protected motif, destination, or other selected anchors |
| Arrangement or transition | Entrances, instrumentation, density, section connections | Accepted material and explicit locks |
| Mix or production edit | Levels, effects, space, tonal balance | Musical writing unless the request includes it |

Sound modeling can begin with existing sampled instruments and editable synthesis patches. A language model can choose the sound, author supported patch parameters, and revise them through listening feedback. Learning a new audio-generating model or manufacturing a new multisampled instrument is a separate capability with its own data and quality requirements.

**The listening surface should stay small while the song remains accessible.** Keep a shared transport and loop above the arrangement. Show the current musical question, two candidates, and a few useful responses. Detailed editors, changes, history, and preferences can open when needed.

The normal response set is A, B, tie, neither, merge, and let AI choose. A short optional comment can refine the next attempt. Keyboard shortcuts should support playback, switching, and voting without requiring a trip through menus. Optional reason tags can include too busy, too stiff, wrong sound, weak groove, or better phrasing. The user should not have to fill out a form after listening.

Switching should preserve the musical position and use a short crossfade where appropriate. Match perceived loudness for the audition, with that adjustment separate from the saved mix. Provide solo, selected-group, and full-context listening. For changed forms or tempos, align by the relevant musical passage and show differing durations. A modulation comparison must include its arrival, and a fill comparison must include the following downbeat. Precise comparison windows should retain pickup notes and release tails.

Blind labels can reduce the influence of descriptions when the user wants to judge the sound first. Reveal the instrument, generation explanation, and change summary afterward. Explanations should identify actual changes in the score or patch. They should avoid unsupported claims about how a render sounds.

**Merging should operate on musical material.** "A's melody, B's drums" selects parts. "A's rhythm with B's ending" selects phrases. "Keep this bass line, use B's articulation" selects a performance layer. "Use the quieter first half and the stronger arrival" selects regions and dynamics. Direct timeline selections and plain language should describe the same operations.

The merged result becomes a new candidate with both parents recorded. The AI checks voicing, register, timing, harmony, and instrument capability across the selected boundary, then renders the result. When the sources conflict, it can propose a short repair. A merge is evaluated in context before it becomes the accepted revision. Accepted work outside the requested scope remains intact unless the user authorizes a broader change.

**The user controls attention as well as musical content.** Three operating modes provide a simple starting point.

| Mode | AI responsibility | User involvement |
|---|---|---|
| Guide me | Propose a next step and alternatives for the decisions the user wants to supervise | Frequent audible choices |
| Collaborate | Develop selected parts and refine challengers using feedback | Choose at useful musical checkpoints |
| Take the lead | Develop a bounded passage or complete draft, make routine choices, and present a shortlist | Give direction, intervene, and accept or revise the result |

These settings can differ by task. A user can supervise the lead melody, delegate drums and bass, and ask to review every modulation. A simple default should favor low effort, with advanced controls for generation limits, render time, model cost, exploration breadth, and protected material. "Finish this draft" should be a usable instruction once the required generation and review capabilities exist.

Delegated choices are recorded as AI selections, with their criteria and supporting evidence. Human feedback has its own provenance. The system must never turn an AI's self-critique into a human preference label. Pause and stop should be available while jobs run. On interruption or failure, preserve the accepted revision and completed candidates, then allow retry or resume.

**Low user effort requires substantial musical work from the AI.** The writing method follows the repository's [composition skill](../.claude/skills/songmap-compose/SKILL.md). For each instrument, reason about its role and write its notes deliberately. Then make a separate expression pass covering dynamics, phrasing, articulation, accents, rests, releases, and groove placement. Review it against the ensemble before developing the next instrument, and revisit earlier parts when their context changes.

A seed audition is a sketch with an explicitly limited scope. Every currently authored part needs complete note and expression decisions within that scope. As the form expands, extend the writing and review to the new sections. Before calling a full song finished, complete both passes for each active instrument across the full form. Automatic humanization and preset substitution do not complete this work.

Treat the drum kit as one playable musician, with deliberate lane interactions and room for fills. Match bass articulation to the recorded technique and available samples. Respect instrument ranges, dynamics, and actual synthesis or sampler capabilities. Keep concise musical decision notes so later revisions preserve the point of a passage. Repetition can be intentional, with development and contrast serving the brief.

The generation loop should interpret the request, choose a bounded scope, author a proposal, check it, render it, review available evidence, and present or select a candidate according to the chosen mode. Compiler checks, score analysis, and audio QA serve different purposes. A rendering failure or clipping is a technical finding. Musical preference comes from the user or a clearly labeled AI judgment. An AI with no audio input should describe its assessment as score and measurement analysis. A future listening-capable model can evaluate rendered sound through an explicit audio interface.

**Learning begins with a durable record of choices.** Save the alternatives, their exact context, the question being asked, the user's response, any explanation, and whether an edit was applied. Include ties and rejected pairs. A skip has its own meaning and should never be interpreted as rejection. Direct edits provide before-and-after examples, while suggested interpretations of those edits remain distinguishable from explicit instructions.

Preferences need context. The user may like sparse accompaniment under a busy lead, aggressive bass in one chorus, and a bright snare only for a particular style. A passage request should default to that passage. Broader song or personal preferences should be explicit or clearly marked as inferred. The user can inspect the examples behind an inference, change its scope, correct it, or remove it.

The first learning layer retrieves relevant choices and an editable preference profile into future generation prompts. This adapts behavior without changing the LLM's weights. A later ranking model can learn which candidates to present and which uncertain decisions merit a comparison. Actual preference training is a later option that requires enough suitable data and evaluation against held-out listening choices. The product should explain which mechanism is active.

Maintain an example library of successful riffs, performances, transitions, sound designs, instrument combinations, and rejected attempts with reasons. A new song can draw on these examples while developing its own material. Private project feedback should remain local by default. Configure external model use and any broader sharing explicitly. Records should support export and deletion. Preferences removed from the active profile should stop being retrieved.

**A useful system must finish songs and keep room for discovery.** Repeatedly challenging the incumbent with tiny edits can become tiring and can narrow the search too early. Keep a few distinct promising directions, occasionally offer a broader alternative, and allow the creator to park an idea for later. Accepted material can become an anchor without making every provisional decision permanent.

When the user repeatedly keeps the same candidate, recommend moving on. Ask for short excerpts when they answer the question, then return to the whole section or song at meaningful checkpoints. Full-song reviews should address development, repetition, contrast, pacing, transitions, and endings. Local improvements can damage the larger arc, so an accepted local change must remain reversible.

A finishing instruction should trigger a bounded completion pass: resolve open musical work, review each instrument across the form, inspect the ensemble and technical QA, produce a full render, and present the remaining choices. The creator can accept the draft or reopen a detail without restarting the process.

For example, begin with the warm instrumental brief, merge the bass from palette A with the keys from B, and delegate the rest of the palette. Compare two lead phrases. Keep A, prefer challenger C, then retain C over D. Ask for bass and drums around C. Accept A's bass rhythm with B's sound and make the release lengths less abrupt. Develop keys next, review the combined section, and request a transition into a new key. Compare two transitions with both their lead-ins and arrivals. Ask AI to complete a contrasting middle section and a return, then review the whole song. Later, replace one snare articulation in the first verse while preserving the chosen melody and form.

**The project needs a branching musical history beneath a simple UI.** The accepted song, candidates, and comparison results are related but distinct objects. Suggested records include the following. These are conceptual responsibilities, not a committed database schema.

- A project brief, evolving song plan, accepted revision, and scoped locks.
- Immutable candidate snapshots with stable IDs, parent revisions, source and patch content, asset references, and a change summary. The editable song and its external files form one revision bundle.
- Reproduction metadata covering model configuration, generation request, available musical context, random seeds, engine version, sample and patch versions, and audio render identity. Reproduction guarantees depend on the backend and retained assets.
- A comparison record with both candidates, label assignment, excerpt alignment, context mix, and audition gain adjustments.
- Feedback events with explicit or inferred provenance, musical scope, reasons, corrections, and a separate application decision.
- Preference entries connected to supporting and conflicting examples, plus an inspectable library of reusable material.
- Generation and render jobs with visible queued, running, ready, failed, cancelled, or interrupted states and resumable checkpoints.

A candidate based on an older accepted revision must not silently overwrite manual edits made while generation was running. Apply a proposal against its recorded base, preserve unrelated edits, and surface overlapping changes for a new musical merge. A missing sample or patch should produce a clear unresolved asset reference while retaining the score and feedback.

SQLite with versioned files is a reasonable first local persistence design. Cache reusable render assets, with an explicit retention policy for large audio files. Retain comparison metadata and source history when regenerable previews are pruned, and show when an old audition needs rebuilding. Source history alone cannot recreate a render if its original external assets are unavailable. Model adapters should allow a chosen local or remote LLM to author the same musical operations. Reuse the existing engine for validation and rendering.

**Manual editing, imports, and recording belong in the same revision system.** A note drawn in the piano roll, a patch knob change, a typed instruction, or a future recorded take can each become the next candidate. The user can compare a manual edit against the accepted version and return to AI development immediately. The accepted source remains the basis for edits and exports.

Import should eventually cover SongMap scores, MIDI, audio clips, stems, and reusable patches with source and asset provenance. MIDI should preserve the relevant tuning and expression information where representable. Imported audio initially remains an audio asset. Transcription, tempo estimation, and stem separation are distinct later analyses whose uncertainty must be shown. An audio waveform does not automatically provide an editable note score.

Recording is a later DAW milestone covering device selection, latency handling, monitoring, take management, overdubbing, and alignment to the project timeline. Recorded takes should enter the same comparison and revision flow. These capabilities should be phased separately from the first songwriting loop so early development can use the existing score and render engine.

**The current GUI supplies useful foundations, with substantial new work still required.** Verified foundations include text-based projects, instrument and patch editing, clip and step operations, rendering, stems, and technical QA. The Rack's existing recipe A/B plays the current sound followed by a recipe. See [Rack.tsx](../songmap/gui/web/src/Rack.tsx), [server.py](../songmap/gui/server.py), [project.py](../songmap/gui/project.py), and the existing API boundary tests in [test_gui.py](../tests/test_gui.py).

The ordinary project audio endpoint serves the latest render. AI Lab now supplies a durable candidate render store and candidate-addressed audio for saved musical comparisons. The current [Teacher](../songmap/gui/teach.py) performs deterministic theory analysis. It is not an LLM generation worker or a learned preference model. AI Lab implements scoped challenger jobs, comparison history, session feedback and explicit reversible application. Selective merging, a full revision graph and cross-project preference learning still require implementation. The broader existing GUI plan remains in [GUI.md](GUI.md).

The implementation should grow in useful increments:

1. Save candidate bundles and render assets, compare manual or existing alternatives with aligned playback, collect feedback, and support reversible adoption. This establishes the evidence and editing boundary.
2. Add the first complete AI journey: blank brief, two instrument palettes, seed phrase comparison, instrument-by-instrument accompaniment, one transition, a complete short song, and revision of an earlier detail. Include selective merging, locks, generation limits, and manual-edit conflict handling.
3. Expand delegated songwriting across larger forms, contextual preference retrieval, reusable examples, resumable jobs, and whole-song review. Record AI selections separately from human feedback.
4. Improve contextual ranking and comparison selection, evaluate whether preference adaptation helps, and broaden supported imports and audio-informed review. Any actual model training needs its own evaluation plan.
5. Add recording and the associated DAW workflow, integrating takes with the established musical revision system.

The first end-to-end demonstration should let a user create an editable short song using only a prompt, a handful of audible choices, and optional comments. They should be able to combine material from two candidates, delegate one instrument, request a key-change transition, revisit an early choice, and recover the previous result. The demonstration should visibly preserve manual edits made during generation and survive a stopped or failed job.

Measure useful progress through completed songs, retained edits, time and cost to an accepted revision, comparison burden, and occasional blind preferences against earlier versions. Review diversity and whole-song quality alongside local wins. A preference vote is evidence about that comparison and context. Claims that the system is improving should rest on repeated held-out choices and actual creator use.

Several design choices remain open for implementation planning: the first model adapter and its audio capabilities, the default autonomy level, the minimum complete song scope, import priorities, render retention limits, and which selective merges can initially be guaranteed. The working assumptions are a local-first project, a configurable model backend, existing SongMap instruments, low-effort collaboration, editable output, and recording as a later milestone. This vision does not require choosing a provider or rewriting the synthesis engine.
