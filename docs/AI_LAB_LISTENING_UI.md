# AI Lab listening workspace

## Known facts

The approved design puts listening first, offers Listening room and Score focus views, moves setup out of the main comparison, selects passages by section/bar, shows performed notes, and separates audition, favorite and applied state. Existing instrument/riff/arrangement/snippet sessions, candidate audio, feedback and apply/undo remain authoritative. The design preview is illustrative; production notes must come from expanded saved candidate scores.

## Likely commands

`python -m pytest -q tests/test_lab_score.py tests/test_music_lab.py tests/test_instrument_lab.py`; `npm run build` under `songmap/gui/web`; browser checks against the built local Studio.

## Relevant paths

`instrument_lab.py`, `music_lab.py`, `lab_score.py`, `lab_api.py`; frontend `InstrumentLab.tsx`, `LabScore.tsx`, `PassagePicker.tsx`, `MusicComparisonForm.tsx`, `instrument-lab.css`. No separate project-process registry exists.

## Existing conventions

Warm paper/ink theme, deterministic expanded notes, 36-ET pitch labels, stable saved take IDs, shared relative audio position, source snapshots, explicit preview/apply with durable undo. Inventory, score-display data and provider discovery must not block saved audio playback.

## Risk areas

Different excerpt offsets, mixed meters/tempo ramps, sustained notes crossing the excerpt, kit pieces, notes versus timbre/mix changes, stale async requests, keyboard shortcuts in text fields, loops ending between coarse audio time events, unsaved feedback during refresh, and source writes mistaken for votes.

## Open questions

None required for this implementation. Staff engraving, arbitrary media imports, selective merging and cartoon musicians remain outside this change. Piano-roll lanes display actual held notes; effect decay is not a new performed note.

## Actions and acceptance

| ID | Action | Observable result / side effect | Verification |
| --- | --- | --- | --- |
| UI-01 | New comparison / close setup | Accessible drawer; return focus; no score write; saved audio continues | Browser: open, Escape, focus and mobile |
| UI-02 | Resume / library / history | Current saved pair loads independently of inventory | Browser with delayed/failed inventory |
| UI-03 | Listening room / Score focus | Same pair, position and draft; score view shows each instrument and active notes | Browser plus expanded-note API tests |
| UI-04 | Play/pause, A/B, Space/A/B/L | Shared transport above notes; switching retains position; no shortcuts while editing text | Browser playback and typing |
| UI-05 | Select/drag loop bars | Valid relative start/end; loop playback honors window; tail remains reachable | Browser drag and loop boundary |
| UI-06 | Section/bar passage selection | Converts through actual tempo/meter map; seconds remain available; excerpt <=30s | Timing tests and browser setup |
| UI-07 | Prefer A/B, tie/neither, tags/comment | Scoped human feedback saved; favorite distinct from audition; tags and range included | API persistence and browser isolated QA |
| UI-08 | Keep favorite / revise / try another | Keep records choice; revision explicitly generates once from favorite and includes draft; auto-next opt-in | Browser request capture and backend job tests |
| UI-09 | Inspect source / preview / apply / undo | Existing hash checks, preimages and explicit writes; applied revision identified separately | Existing apply tests plus UI state |
| UI-10 | Loading / error / retry | Compact status near action; failed score display cannot disable audio; stale responses ignored | API errors and browser failure injection |

The new score endpoints are read-only. Notes use candidate-specific source windows, contain microtonal pitch/frequency labels, and distinguish performed-note, voice and mix differences. Section metadata uses `Timeline.bar_to_beat`, including mixed meter and fractional final bars. Transient loop/view state does not rewrite a saved candidate.
