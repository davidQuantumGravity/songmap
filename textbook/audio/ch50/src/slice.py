"""Write the four movements of A Comma Higher as textbook audio examples, and check each against the full song."""
import copy, re
from dataclasses import replace
from songmap.parse import load, fmt
from songmap.arrange.expand import expand

SRC = "songs/epic/a_comma_higher.sm"
MOV = [("m1_door", "I. The door", "veil", "riff_out", 3),
       ("m2_blue_gold", "II. Blue gold", "head_dorian", "giant", 3),
       ("m3_decatonic", "III. Decatonic", "deca_1", "still", 3),
       ("m4_thirteen_steps", "IV. Thirteen steps", "pump_a", "coda", 6)]
full = load(SRC)
fa = expand(full)
names = [s.name for s in full.sections]
for fn, title, a, z, tail in MOV:
    keep = names[names.index(a):names.index(z) + 1]
    s = copy.deepcopy(full)
    s.title = f"A Comma Higher, {title}"
    s.sections = [x for x in s.sections if x.name in keep]
    if s.sections[0].tempo is None:
        s.sections[0].tempo = full.tempo
    s.events = [e for e in s.events if re.match(r"[A-Za-z_]\w*", str(e.at)).group(0) in keep]
    s.tail_seconds = tail
    head = (f"# A Comma Higher, movement {title} (textbook Chapter 50): sections {keep[0]} .. {keep[-1]} of\n"
            f"# songs/epic/a_comma_higher.sm, exported with songmap fmt and cut at movement boundaries.\n")
    path = f"textbook/audio/ch50/{fn}.songmap.yaml"
    open(path, "w", encoding="utf-8").write(head + fmt.to_yaml(s))
    # check: the movement's notes are the full song's notes for these sections, shifted in time
    b = expand(load(path))
    off = fa.timeline.section(keep[0]).start
    def keys(arr, shift):
        out = []
        for p, evs in arr.parts.items():
            for e in evs:
                if e.section in keep:
                    out.append(replace(e, beat=round(e.beat - shift, 6)).key())
        return sorted(out)
    same = keys(fa, off) == keys(b, 0)
    print(fn, f"{b.timeline.seconds:.1f} s", "notes identical to the full song:", same)
