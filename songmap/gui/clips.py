"""Piano-roll clips: a part's notes in one section, read from the arrangement and written back as
`role="<notes>"` on the section's line (parse/clip.py writes the notes).

A part played by a style, motifs or chord-relative figures is generated; baking writes what it plays as
explicit notes, which the piano roll then edits. Baking keeps onsets, lengths, pitches, velocities,
articulations and slurs; per-note automation, pan/gain offsets and grace notes are not written.
"""
from __future__ import annotations

import re

from ..parse.clip import ClipNote, clip_of, write_notes


def _sec(arr, index: int):
    secs = [s for s in arr.timeline.sections if s.index == index]
    if not secs:
        raise ValueError(f"no section #{index}")
    return secs[0]


def section_clip(arr, index: int, part: str) -> dict:
    """A part's notes in a section (beats from the section's start) and whether they are written notes."""
    tl, song = arr.timeline, arr.song
    sec = _sec(arr, index)
    spec = song.sections[index].parts.get(part) if index < len(song.sections) else None
    written = bool(spec is not None and getattr(spec, "notes", None) and getattr(spec, "notes_mode", "") == "letter")
    notes = [{"beat": round(n.beat, 5), "dur": round(n.dur, 5), "pitches": list(n.pitches), "vel": round(n.vel, 6),
              "art": n.art, "slur": n.slur, "grace": "grace" in n.tags} for n in clip_of(arr.parts.get(part, []), sec.start, sec.end)]
    line = song.sections[index].line if index < len(song.sections) else None
    return {"section": sec.name, "index": index, "part": part, "bars": sec.bars, "beats_per_bar": sec.bpb,
            "start": round(tl.beat_to_sec(sec.start), 4), "end": round(tl.beat_to_sec(sec.end), 4),
            "start_beat": sec.start, "tempo_spans": _beat_times(tl, sec), "line": line, "written": written,
            "kit": arr.ensemble.is_kit(part), "notes": notes}


def _beat_times(tl, sec) -> list[float]:
    """Seconds at each beat of the section (tempo can change): the piano roll's time axis."""
    n = int(round(sec.end - sec.start))
    return [round(tl.beat_to_sec(sec.start + k), 4) for k in range(n + 1)]


def _split_fields(raw: str) -> list[str]:
    from ..parse.lang import split_top
    return split_top(raw, "|")


def set_section_part(text: str, line_no: int, part: str, value: str) -> str:
    """Replace (or add) `part` on the section line `line_no` with `part=<value>` (value already quoted)."""
    from ..parse.lang import split_top
    lines = text.split("\n")
    if not line_no or line_no > len(lines):
        raise ValueError("this section has no line of its own to edit")
    raw = lines[line_no - 1]
    body, comment = raw, ""
    m = re.search(r"\s+#(?=[^\"']*$)", raw)
    if m:
        body, comment = raw[:m.start()], raw[m.start():]
    fields = _split_fields(body)
    if len(fields) < 2 or not re.fullmatch(r"\s*[A-Za-z_]\w*\s+\S.*", fields[0]):
        raise ValueError(f"line {line_no} isn't a section line (`name bars | parts`); edit it in the code")
    item = f"{part}={value}"
    rx = re.compile(rf"-?{re.escape(part)}(?=[:=]|$)")
    for i in range(1, len(fields)):
        toks = split_top(fields[i])
        for j, t in enumerate(toks):
            if rx.match(t):
                toks[j] = item
                fields[i] = " " + " ".join(toks) + " "
                return "\n".join(lines[:line_no - 1] + [_join(fields) + comment] + lines[line_no:])
    target = 1
    if all(t.startswith("!") for t in split_top(fields[1])) and split_top(fields[1]):
        fields.insert(1, "")
    fields[target] = " " + " ".join(split_top(fields[target]) + [item]) + " "
    return "\n".join(lines[:line_no - 1] + [_join(fields) + comment] + lines[line_no:])


def _join(fields: list[str]) -> str:
    return fields[0].rstrip() + " | " + " | ".join(f.strip() for f in fields[1:])


def write_clip(text: str, arr, index: int, part: str, notes: list[dict]) -> str:
    """The text with a section's part set to these notes."""
    sec = _sec(arr, index)
    clip = [ClipNote(float(n["beat"]), float(n["dur"]), tuple(float(p) for p in n["pitches"]), float(n.get("vel", .62)),
                     n.get("art", "normal"), bool(n.get("slur", False)),
                     frozenset({"grace"}) if n.get("grace") else frozenset()) for n in notes]
    body = write_notes(clip, bars=sec.bars, beats_per_bar=sec.bpb)
    line = arr.song.sections[index].line if index < len(arr.song.sections) else None
    return set_section_part(text, line, part, f'"{body}"')


def bake(text: str, arr, index: int, part: str) -> str:
    """Write what a part plays in a section as explicit notes."""
    return write_clip(text, arr, index, part, section_clip(arr, index, part)["notes"])


# ---------------------------------------------------------------------------------------------- drum steps
STEP_CHARS = (("X", 1.0), ("x", 0.78), ("-", 0.55), ("o", 0.38))


def section_hits(arr, index: int, part: str, text: str = "") -> dict:
    """A kit part's hits in a section, per piece: [[beat from the section's start, velocity], ...]."""
    sec = _sec(arr, index)
    pieces: dict[str, list] = {p: [] for p in sorted(arr.ensemble.kits.get(part, {}))}
    for e in arr.parts.get(part, []):
        if e.piece and sec.start - 1e-9 <= e.beat < sec.end - 1e-9 and "flam" not in e.tags:
            pieces.setdefault(e.piece, []).append([round(e.beat - sec.start, 5), round(e.vel, 4)])
    song = arr.song
    line = song.sections[index].line if index < len(song.sections) else None
    lanes = set()
    if line and text:
        src = text.split("\n")
        raw = src[line - 1] if line <= len(src) else ""
        lanes = {m for m in re.findall(r"(?:^|\s)([A-Za-z_]\w*)=\"", raw) if m in pieces}
    return {"section": sec.name, "index": index, "part": part, "bars": sec.bars, "beats_per_bar": sec.bpb,
            "line": song.sections[index].line if index < len(song.sections) else None,
            "start": round(arr.timeline.beat_to_sec(sec.start), 4), "end": round(arr.timeline.beat_to_sec(sec.end), 4),
            "pieces": pieces, "written": sorted(lanes)}     # lanes written on the section line


def steps_text(cells: list[str], per_bar: int) -> str:
    """['x', '.', ...] -> 'x...|....' with a bar line every `per_bar` steps."""
    return "|".join("".join(cells[i:i + per_bar]) for i in range(0, len(cells), per_bar))


def set_steps(text: str, arr, index: int, piece: str, steps: str) -> str:
    """Write one kit piece's lane in a section: `piece="x...|x..."` on the section's line."""
    import re as _re
    if not _re.fullmatch(r"[Xx\-o.fr|]+", steps):
        raise ValueError(f"steps use X x - o . f r and |, not '{steps}'")
    line = arr.song.sections[index].line if index < len(arr.song.sections) else None
    return set_section_part(text, line, piece, f'"{steps}"')
