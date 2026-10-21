# SongMap: instructions for coding agents (Codex, Claude Code, OpenCode, ...)

SongMap is a from-scratch Python music engine. Songs are short text files (`.sm`, the SongMap language; YAML also works) that compile to a song tree. The engine expands that tree into notes and renders audio, stems and frame-accurate cues for videos.

## Writing or revising music

Follow **[.claude/skills/songmap-compose/SKILL.md](.claude/skills/songmap-compose/SKILL.md)**. It is the full authoring loop, the `.sm` format on one screen, and the scoring rules of thumb. Its catalog, [catalog.txt](.claude/skills/songmap-compose/catalog.txt), lists every style, instrument and event you may use. In short:

1. `songmap describe --compact`: read the catalog and use only its names.
2. Spot the video. Frames per bar = `fps × beats_per_bar × 60 / tempo`, which is 60 at 120 BPM, 4/4, 30 fps.
3. Write `song.sm`: header lines, then one line per section, `name bars | parts | !events`.
4. `songmap check song.sm`: fix each error as its suggestion says, until it prints `ok:` with the right frame count.
5. `songmap render song.sm -o build/<name>`, then read `qa.json`, then revise by replacing section lines.

Express music as song-map text. Don't change engine code to get a musical result.

## Working on the engine

- **Setup:** `python -m venv .venv`, then `.venv/Scripts/pip install -e .[dev,gui]` (or `.venv/bin/pip`).
- **Tests:** `python -m pytest -q`. Use `-m "not port"` to skip the render-vs-original-audio checks, which need `assets/oct13`.
- **Golden digests:** the event-list hashes of every example live in `tests/golden/`. A change that moves notes must be deliberate: rerun `python tools/update_golden.py` and say why in the commit.
- **Layout:** `docs/ENGINE.md` §2.
  - Parsers are in `songmap/parse/` (`lang.py` reads `.sm`, `yaml_form.py` reads YAML, `fmt.py` prints both).
  - `songmap/arrange/expand.py` turns the song tree into notes, and `songmap/render.py` turns notes into audio.
- **Conventions:**
  - **Seeds** come from `zlib.crc32` of names (`expand.seed_for`), never Python's `hash()`.
  - **Errors** are a `SongError` with file, line and a suggestion (`did_you_mean`).
  - **Pitch** is float MIDI, and pitch-class math goes through `songmap/theory/tuning.py`, so don't hard-code 12.
  - **Styles** are data, in `songmap/arrange/patterns/<role>/*.yaml`.
- **Docs:**
  - `docs/LANGUAGE.md`: the language and its decisions;
  - `docs/COMPACT_FORMAT.md`: the `.sm` grammar;
  - `docs/SONGMAP_SPEC.md`: the YAML form;
  - `ROADMAP.md`: what is built and what is next.
