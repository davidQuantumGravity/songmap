# AI Lab

AI Lab is the workspace for comparing and refining music through AI proposals and human feedback. Its current tool maps saved scores to their played instruments and runs instrument-sound comparisons. Melody writing and mastering are future tools in the same workspace. It is the first implemented slice of the [AI songwriting vision](AI_SONGWRITING_VISION.md).

Start Studio with `songmap gui --no-browser --port 8866`, then open `http://127.0.0.1:8866/?lab=1`. The AI Lab dock also opens from an ordinary Studio project. Saved comparisons have direct links through the `comparison` query parameter.

The inventory scans `songs/`, `textbook/audio/`, and `examples/`. It expands each score and resolves the actual voice for every played part and kit piece, including inherited defaults and kit fallbacks. Unused instrument declarations are excluded. Video view files, archives, and render folders are excluded. Source errors are listed with their paths. Counts refer to saved score files, so two editions of a composition can count separately.

The default scope includes songs and textbook examples. Study and revisit collections are available separately, as are engine examples and the complete inventory. Search matches voice, song title, file path, part, and kit piece. A CSV export provides the complete source-to-instrument map. Each inventory refresh also saves `inventory.json` and `instrument-usage.csv` under `.songmap/instrument-lab/` for composing agents and other local tools.

The improvement-need control stores an explicit assessment from 0 to 3, with optional text. Most-used sorting uses distinct source-file counts. Improvement-priority sorting uses `source count × (1 + need)`. This makes reach and the user's assessment visible. It does not infer sound quality from usage or invent a learned quality score.

To compare an instrument:

1. Select its voice, a source score, and a played part or kit piece.
2. Choose an excerpt start and a length of 1 to 30 seconds. Describe what needs improvement.
3. Start the comparison and generate an AI challenger, or add a manual voice/parameter edit.
4. Listen to A and B at a shared playback position. Choose the song context or dry part solo, with optional loudness matching and looping.
5. Prefer A or B, record a tie or neither, or save a text comment. The next AI request receives all of that session's feedback and attempts. Clicking Generate next challenger also saves and includes the text currently in the feedback field.
6. Keep iterating from the current favorite. The automatic-next setting generates one challenger after each vote, with a maximum of 24 candidates per session. Saving a comment alone does not launch a request.

Generation uses the installed, signed-in Codex CLI and its configured model. No model name or API key is hardcoded. The adapter calls non-interactive `codex exec` with a structured response schema, a read-only sandbox, and a four-minute timeout. This mechanism follows the [official Codex command documentation](https://learn.chatgpt.com/docs/developer-commands#codex-exec). Each request provides the score, selected voice, parameter schemas, installed sampled voices, preset names, instrument assessment, previous attempts, and scoped human feedback. Its request and JSON result remain in the session's `jobs/` directory. A failed generation remains visible and can be retried. The manual path works without Codex.

The model authors one instrument edit at a time. This slice fixes the written notes, expression, tuning, form, and other parts. It can change an instrument or its supported numeric parameters. Note writing, performance rewriting, synthesis-graph restructuring, broad arrangement generation, and a global learned preference model remain future work. The existing [composition skill](../.claude/skills/songmap-compose/SKILL.md) governs later note and expression generation.

Style and per-note overrides are supplied to the model. A candidate whose entire parameter change is masked by those overrides in the selected passage is rejected before rendering. Changing a label or restating the same resolved parameters also fails validation. Passing these checks establishes a potentially effective edit, not a guarantee of perceptual improvement.

The system does not give the model an audio input. Its explanation is score and parameter reasoning. Actual listening preferences come from the user. Applying feedback here means retrieving it into the next generation request, without retraining model weights. Assessment notes apply to the selected voice. Comparison feedback stays within its instrument and passage session.

Each candidate retains its source, resolved instrument edit, parent, origin, reasoning, stable audio files, loudness measurements, and render metadata. Rendering a later candidate does not invalidate an earlier audition. Both sides use the same source seed. Excerpts are rendered from the original song's beginning through the excerpt end to preserve note indices, section-relative expression, and effects history. The player then crops the requested passage. Preview mastering can differ from the final full-song master. Binaural songs currently use a full render before cropping.

Dry solo is the entire selected part, including the whole kit when comparing one drum piece. It excludes shared effect returns. Loudness matching uses levelled solo previews or attenuates full-song auditions toward the quieter mix; it is not written into the score. A/B switching keeps position and uses a pause/seek/play handoff. A crossfade and blind label assignment are future enhancements.

Votes select the session's current favorite. They do not write song files. The apply panel lets the user select the source and other scores that use the original voice, inspect before/after source previews, and apply the chosen favorite. It handles both compact and YAML scores. Applying a parameter tweak preserves unrelated overrides in other files. Changing backend replaces incompatible instrument parameters.

The source experiment checks its original saved-source hash. Every selected target is checked again against the preview before writing. Unsaved edits in the current Studio editor must be saved before applying to that score. Preimages and receipts are stored independently of the ordinary `.bak` file. Undo restores an applied batch only when its targets still match the applied revisions. Newer edits block undo. A failed apply attempts to roll back files it already wrote while retaining preimages for recovery.

Application and undo update editable score files. They do not rebuild existing rendered songs or the textbook website. After accepting changes, render the affected scores and run the relevant publishing build through the normal project workflow.

Local persistence uses `.songmap/instrument-lab/lab.sqlite3` for sessions, assessments, feedback, and apply receipts. Audio, model requests, responses, and apply preimages live beside it. `.songmap/` is Git-ignored. Keep this directory to retain experiments across server restarts. Stop preserves completed candidates and feedback. A render already running finishes its current work before the single-worker queue can advance. An interrupted session is marked on reopening and can be retried.

The HTTP boundary is under `/api/lab`: `inventory`, `inventory.csv`, `assessment`, `provider`, `sessions`, and candidate-addressed `audio`. Session operations include `generate`, `render`, `candidate`, `feedback`, `context`, `preview`, `apply`, `undo`, and `stop`. The context endpoint lets a composing agent inspect exactly which source and feedback should guide its next instrument proposal.

Validation covers expanded-voice inventory, malformed sources, SM/YAML musical preservation, parameter validation, durable/idempotent feedback, incumbent continuity, stable audio, preview rendering, multi-score application, preservation of unrelated overrides, conflict rejection, undo, and the API generation/render/vote/apply sequence. The real Codex adapter and browser A/B playback were also exercised on a saved textbook bass passage. Technical tests establish behavior. They do not decide whether its challenger sounds better.

Run the focused checks with `python -m pytest -q tests/test_instrument_lab.py tests/test_gui.py`. Build the frontend with `npm run build` in `songmap/gui/web/`. To verify a ready comparison against a running server, run `python tools/verify_instrument_lab.py --session SESSION_ID`. It checks the CSV and WAV assets, browser A/B switching, solo/context controls, and mobile width. It saves screenshots and a verification receipt without submitting taste votes or changing scores.

Stable take numbers identify candidates across rounds. A and B identify positions in the current comparison. A keeps the chosen take; B presents the new challenger and becomes the selected audition when it is ready. Catalog and score data provide the main instrument names and parameter differences. Model nicknames and reasoning appear separately as AI proposal notes.

The default audition isolates the selected part. The full-song option lists the unchanged accompaniment explicitly. Levelled solo preview files aim for -20 LUFS with a peak ceiling of 0.94, making quiet parts audible. Original solo and full-song files remain intact. Disabling loudness matching uses the original-level audio. Audition gain never changes the score.

Generation records the selected base take, included feedback IDs, request time, new take, and completion time. Retrying the same pending feedback event does not queue another job. New feedback records the listening mode; historical votes resolve to stable takes while preserving their original A/B labels and comments.
