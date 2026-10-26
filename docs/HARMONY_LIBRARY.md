# Harmony Library

## Known facts

Studio uses FastAPI and React; the existing chord parser accepts Western qualities,
slash basses and 36-ET golden chords. The listening lab and open score must retain
their state while browsing. The library is useful without opening a score.

## Likely commands

` .venv/Scripts/python -m pytest tests/test_harmony_library.py -q ` and
`npm run build` in `songmap/gui/web`; the existing GUI suite covers integration.

## Relevant paths

`songmap/gui/harmony_library.py`, `harmony_library_api.py`,
`data/harmony_library.yaml`, `web/src/HarmonyLibrary.tsx`,
`songmap/theory/harmony.py`, `songmap/theory/tuning.py`.

## Existing conventions

Reuse the actual chord parser and tuning helpers. Seed data ships with the package;
the searchable SQLite materialization lives in ignored `.songmap/harmony-library/`.
This is a read-only reference library: changing the versioned seed rebuilds its
materialization, with no effect on scores, listening choices or instrument presets.

## Feature brief

Give composers three linked databases: chord types, directed chord transitions,
and 100 essential progressions. Every record has a one-sentence summary and a
paragraph description. Include formulae, reference symbols, modes, families, sources,
and relationships. Search, filter, transpose, audition and export/copy valid `.sm`.
The preview uses a quiet, stable piano sound and displays the notes it plays.

“Top 100 of all time” is interpreted as a curated teaching collection, not a
measured global ranking. No fabricated popularity figures or song attributions.
Recognized schemas and editorial realizations are distinguished. Variants are
included for meaningful differences in harmony, bass or form, not key changes.
Golden chord types are project extensions, not purported historical chart staples.
The 100 progression selection spans pop, rock, folk, modal, minor, jazz, blues,
cadences and sequences. Durations are illustrative 4/4 realizations.

## Actions and acceptance

| ID | Action | Effect/result | Verification |
| --- | --- | --- | --- |
| HL01 | Browse/search/filter | Read-only results for each database, clear empty/error states | API tests + browser |
| HL02 | Open linked record | Chords, transitions and containing progressions remain navigable | Link integrity tests + browser |
| HL03 | Transpose | Symbols, bass, played notes and copied score agree in all 12 tonic keys | Engine/parser tests |
| HL04 | Listen/stop/seek | Short bounded local preview with chord and note display | Audio tests + browser |
| HL05 | Copy score | Valid editable `.sm` text; never overwrite the current score | Parse/expand tests + browser |
| HL06 | Export library | Download complete structured data, source metadata and links | Export tests |
| HL07 | Share entry | URL restores database tab, selection and tonic | Browser |

## Risk areas

Context determines harmonic function; a pair is not an unconditional cadence.
Directed pairs include mode context and only occur between actual adjacent events
(plus explicit loop closure). Repeated held chords do not create artificial edges.
Preview voicing is illustrative and may differ from an arrangement. Source links
support families/theory unless explicitly marked exact; editorial commentary is
original. Auditions and reading are authorized local actions; scores stay untouched.

## Open questions

None block implementation. CRUD, personal annotations, audio recognition and
automatic insertion into an existing arrangement are deferred.

## Using the library

Open **Harmony Library** in Studio's dock, or use `/?harmony=1`. No open score is
required. The three database tabs show 100 progressions, 30 chord entries and 196
mode-specific directed pairs, including six project-defined golden bridges.
Select a family or mode, or search names, symbols, Roman numerals and prose.
Click a chord card to seek. Listen plays the phrase once; Stop returns to its start.
Tonic and tempo controls update the actual notes, preview and copied score.
Descriptions explicitly retain their C-reference context after transposition.

Chord records are transposable types with reference examples, not 360 duplicated
root/quality descriptions. Transition links retain event positions and distinguish
loop returns. Different form lengths can have the same chord order (the short
dominant turnaround and eight-bar rhythm bridge, for example); they are labeled
as different phrase realizations, not independent historical popularity results.

The seed is `songmap/gui/data/harmony_library.yaml`; SQLite is rebuilt from this
versioned source when its fingerprint changes on server startup. JSON export
includes every entry, source scope, relationship, and the selection note.

API: `GET /api/harmony/meta`, `/{kind}?q=&family=&mode=`, `/{kind}/{id}?tonic=D&bpm=100`,
`/{kind}/{id}/audio?tonic=D&bpm=100`, and `/export` under `/api/harmony`.
Kinds are `chords`, `transitions`, `progressions`. Preview requests accept only the
twelve listed tonic keys and 60–180 bpm. Short WAV previews are cached in memory;
there are no score writes or external model requests.

## Verification, 2026-10-24

The complete non-port suite passed: **793 passed, 5 skipped, 3 deselected**.
Eight library tests cover descriptions, adjacency and foreign keys, SQLite reopening,
filtering, literal SQL-like searches, all-record score expansion, all-tonic chord
transposition, slash basses, golden pitches, bounded stereo audio and API exports.
The frontend typecheck and production build passed (the pre-existing bundle-size
advisory remains). Live Studio checks cover playback/note synchronization, search,
transposition, score copying, linked navigation and URL restoration. At a 390px
viewport the library and detail pane have no horizontal overflow after fixing the
score grid's intrinsic minimum width.
