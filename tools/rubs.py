"""Flag microtonal rubs in a SongMap song: two notes sounding together 1 or 2 sixth-steps apart
(33 or 67 cents, mod the octave), overlapping for at least MIN_BEATS. Golden chords are built from
golden thirds (11 sixth-steps), so these intervals only appear when layers collide by accident:
a diatonic melody note held over a golden chord, or a pad still holding the previous chord.

    python rubs.py song.sm [--min 0.5] [--parts lead,keys]
"""
import sys

from songmap.arrange.expand import expand
from songmap.parse import lang, yaml_form
from songmap.render import held_beats

args = sys.argv[1:]
path = args[0]
MIN = float(args[args.index("--min") + 1]) if "--min" in args else 0.5
ONLY = set(args[args.index("--parts") + 1].split(",")) if "--parts" in args else None
BAD = (1, 2, 34, 35) + ((3, 33) if "--semis" in args else ())      # --semis: also semitones (minor 2nds/9ths)
song = lang.load(path) if path.endswith((".sm", ".sml")) else yaml_form.load(path)
arr = expand(song)
notes = []      # (start, end, pitch, part)
for part, evs in arr.parts.items():
    if part in ("drums", "fx"):
        continue
    for e in evs:
        end = e.beat + held_beats(e)
        for p in e.pitches:
            notes.append((e.beat, end, float(p), part))
notes.sort()
rubs = []
for i, (s1, e1, p1, a) in enumerate(notes):
    for s2, e2, p2, b in notes[i + 1:]:
        if s2 >= e1:
            break
        ov = min(e1, e2) - s2
        if ov < MIN:
            continue
        d = round(abs(p1 - p2) * 3) % 36          # sixth-steps, mod the octave
        if d in BAD and (ONLY is None or a in ONLY or b in ONLY):
            rubs.append((s2, ov, a, p1, b, p2, d))
bpb = arr.timeline.bpb
for s, ov, a, p1, b, p2, d in rubs:
    sec = arr.timeline.section_at(s)
    print(f"bar {int(s // bpb)} beat {s % bpb + 1:g} ({sec.name if sec else '?'}): {a} {p1:.2f} vs {b} {p2:.2f} "
          f"= {min(d, 36 - d) * 33.3:.0f} c for {ov:g} beats")
print(f"{len(rubs)} rubs >= {MIN} beats")
