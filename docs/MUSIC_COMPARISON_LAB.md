# Musical comparisons in AI Lab

## Context and decisions

Known facts: the existing AI Lab persists instrument takes, human feedback and explicit apply/undo receipts. Its player already switches A/B at a shared relative position. The requested extension compares riffs, arrangements and saved song snippets as well as instrument sounds.

Relevant paths: `songmap/gui/instrument_lab.py` provides persistence and instrument edits; `music_lab.py` extends it; `lab_api.py` exposes the jobs; `web/src/InstrumentLab.tsx` provides the shared player. Existing sessions default to instrument scope.

Commands: `.venv/Scripts/python -m pytest -q tests/test_instrument_lab.py tests/test_music_lab.py`; `npm run build` in `songmap/gui/web`.

Conventions: saved source snapshots, deterministic seeds, human taste decisions, no automatic score writes. Slow inventory loading must not block saved comparisons.

Risks: source changes between comparison and apply; misleading scope labels; different excerpt offsets; audio cache reuse; model proposals that change protected backing. Address these at validation and rendering boundaries.

Open questions: none required for this bounded extension. Longer excerpts and arbitrary media-file comparisons remain future work.

## Scope contracts

| Type | Editable material | Audition | Apply |
| --- | --- | --- | --- |
| Instrument | One voice and parameters; existing behavior | Isolated part or context | Existing multi-score preview and undo |
| Riff | Notes and expression of one selected part across the score; backing, voice, harmony and form fixed | Selected 1–30 second window, solo or context | Only original score, preview and undo |
| Arrangement | Parts, orchestration, harmony and mix across the score; section timing, tuning and seed fixed | Selected 1–30 second window, full mix | Only original score, preview and undo |
| Song snippet | Two saved score snapshots, each with its own source and start offset | Equal-duration 1–30 second full-mix excerpts | Listening only; never replace a song with another excerpt's source |

Riff and arrangement changes may extend beyond the listening window. Show this clearly; the source preview covers the full change. Snippet comparisons may contain entirely different music and do not imply isolated experimental control.

## Actions and acceptance

- Create: choose type, saved source, window and brief; riff requires a played part. Snippets additionally choose B's source and start. Reject invalid paths, nonfinite times and windows beyond the rendered song. Store source snapshots before rendering.
- Add challenger: instrument parameters, a full edited score for riff/arrangement, or another saved excerpt for snippets. Validate protected material and reject musical no-ops. Cap sessions at 24 takes.
- Generate: instrument/riff/arrangement only, one candidate using the incumbent and all human feedback. A generated score must pass the same validation as a manual edit. Never claim the model listened.
- Listen: A/B shares relative position; each source window is cropped independently. Match loudness and loop without changing the saved evidence. Preserve audio URLs and prior takes.
- Vote/comment: durable, idempotent and tied to the actual candidate pair and comparison scope. Votes choose an incumbent; they do not write source files.
- Apply/undo: explicit source preview, source hash checks and durable preimages. Riff/arrangement cannot batch-copy music into unrelated songs. Snippet apply is rejected at the API boundary.
- Resume: saved sessions open independently of inventory availability; older instrument sessions remain usable.

Verification covers offset-specific rendered audio, protected backing, invalid inputs, feedback persistence, conflict-safe apply/undo, API job routing, frontend build and actual browser controls.
