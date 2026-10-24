# Golden Worlds: five songs wholly in golden harmony

Five contrasting instrumental songs, each 3-4 minutes, with golden harmony throughout and a free choice of timbres. These are listening drafts for review: the musical checker, pitch audit and audio measurements do not establish that they sound good.

User listening review (2026-10-23): **rework the melodies and lead sound**. The bass lines, chords and comping were liked; leads were often too loud and shrill. Retain that backing as a reference for quieter, calmer melodic comparisons. The existing renders are unchanged.

Open [the listening page](index.html) for all five players. Each render folder contains `song.mp3`, 24-bit stereo 48 kHz `song.wav`, individual stems, `cues.json`, `qa.json`, `review.json` and `qa.png`.

[Chapter 51](../../textbook_site/chapters/ch51.html) contains the full chord-and-note videos, timed explanations,
three pitch figures and a short comparison of the two decatonic modes. Each song now has a `.view.yaml` sidecar
with separate one-bar instrument windows; Studio also offers a sounding-notes-only option.

| Song / editable score | Style | Length incl. tail | LUFS | True peak dBTP |
|---|---|---:|---:|---:|
| 1. [Sideways Sun](01_sideways_sun.sm) | Broken-beat | 3:20 | -16.1 | -1.00 |
| 2. [Pocket Algebra](02_pocket_algebra.sm) | Jazz / funk | 3:29 | -16.6 | -1.00 |
| 3. [Parallax Arcade](03_parallax_arcade.sm) | Progressive electronic | 3:26 | -16.8 | -1.00 |
| 4. [Two Windows](04_two_windows.sm) | Chamber counterpoint | 3:12 | -18.0 | -1.44 |
| 5. [Night Orchard](05_night_orchard.sm) | Atmospheric | 3:20 | -20.1 | -1.49 |

All five use 36-ET, the engine's tempered approximation to golden intervals. All composed pitched notes and every chord tone were checked against their local golden scale. Drum-kit voices are treated as percussion. There are no Western chord visits or Western cadences. Timbres include stable electric piano, plucked strings, reed-like additive leads and golden-spectrum pad/glass sounds.

All pass `songmap check`, the note-level automated ear, the render-aware ear with zero problems/warnings, local scale membership and `tools/rubs.py --min 0.25` with zero microtonal rubs. No render clips. The frame-integrality warning is expected for these listening tempos: there is no video synchronization brief. Parallax Arcade retains two informational audio notes: its opening is deliberately bass-led, and part of the middle maintains similar loudness while the harmony changes. All five QA images were visually inspected.

The per-score hashes, audio format, note-event digests, measurements and remaining informational notes are in [verification.json](verification.json). Scores and this listening guide are editable; renders are gitignored and can be regenerated.

## 1. Sideways Sun

A syncopated question and answer in C golden7; the 35 decatonic opens the middle, a neighboring vE golden7 supplies a detour, and a drumless breath prepares the return.

Listen for: 0:08 head one; 1:02 ten windows; 1:20 side door; 2:13 held breath; 2:31 sunburst.

## 2. Pocket Algebra

A 53-decatonic head in F, instrumental trading, a 5|4 bridge on shared pitches, and a written sixteen-bar solo. The final phrase contracts into Fg7.

Listen for: 0:08 head left; 1:00 limma room; 1:17 solo first; 1:51 trading keys; 2:34 whole room.

## 3. Parallax Arcade

D golden7 4|2 changes to the 35 decatonic, retaining six pitch classes, removing one and adding four. After the quiet middle, every pitched player rises to ^D, one sixth-step higher; the transformed head returns in that new key.

Listen for: 0:15 sign one; 1:01 decatonic drive; 1:32 empty lane; 1:48 comma crossing; 2:34 arcade summit.

## 4. Two Windows

A chamber invention in 3/4 on G. Two subjects use the complementary pentatonics of the 35 decatonic; they meet, exchange roles, develop in the 53 mode and return in a twelve-bar synthesis.

Listen for: 0:15 first window; 0:30 second window; 0:45 interlaced; 1:15 brighter glass; 2:30 both windows.

## 5. Night Orchard

A melodic atmospheric arc through A golden7 5|1, centered 3|3 and dark 1|5, then a decatonic bloom and a neighboring vC# golden7 detour. The last phrase returns to A golden7; no binaural layer.

Listen for: 0:15 first branches; 1:03 unlit leaves; 1:24 lantern bloom; 1:48 elsewhere river; 2:48 roots and stars.

## Re-render

From the repository root:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m songmap.cli render songs/golden_worlds/01_sideways_sun.sm -o songs/golden_worlds/renders/01_sideways_sun --mp3
.\.venv\Scripts\python.exe -X utf8 -m songmap.cli listen songs/golden_worlds/01_sideways_sun.sm --render songs/golden_worlds/renders/01_sideways_sun
```

The scores are included by the textbook's generated Songbook (appendix H). Theory sources: Chapters 31 (golden homes), 32 (golden modulation), 36 (modes and the decatonic), 40 (melodic development), and 44 (timbre). The Codex composing skill is installed at `C:/Users/chest/.codex/skills/songmap-compose/SKILL.md`.

For a verdict, tell Codex which song, time and musical change you want; the score can record `# review: approved ...` or `# review: rework ...`. No user approval is presumed.
