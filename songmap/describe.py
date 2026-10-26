"""`songmap describe [--compact]`: everything an LLM needs to write a song map, built from the live
registries (styles, mods, instruments, presets, kit pieces, events), plus the note-language and `.sm`
cheat sheets. The compact form includes the curated sample names (tests/test_describe.py bounds its size)."""
from __future__ import annotations

NOTES = """notes   c d e f g a b, #/b, +/- octave (c=C4) | deg: 0 1 -3 #4 b7 | [c,e,g] chord | r rest | bars checked
        durations 1 2 4 8 16 32 . t, STICKY; deg: 3/8 | =p =mf =f, < > hairpins | ^ accent ' stacc _ ten ~ slur
steps   X x - o . f r = accent hit soft ghost rest flam ratchet; chars per bar = grid; | next bar"""

SM = """header  song "T" 120 4/4 Em fps=30 seed=7 tail=3 video=Comp:3690 | inst bass(cutoff=700) | chords Em C G D /2
        motif m1 deg oct=5 "0 2 4 | 3/2" | prog p "Am:2 F:2" | cue x=f3960 | mix pad -6 sc=.35 | master legacy
line    name bars | role:style+mod role:m1,m2 role:style(k=v) kick="X..." -role like=prev dyn=p<f prog=p | !events
event   !type[:bars|:Nb][@+bar:beat|@bar|@f123|@cue:x][(k=v)]; risers END at @; lift = !impact !riser:2 -> !lift
more    lit = up(order=[0,2,1,3]); form: verse 8 x2 / for i in 1..4: / if i == last: / every 4 bars: bass = 8ths
        / bar -1: lead = [m2]; b = a with {pad: none}; euclid(3,8) rot rev &  (docs/LANGUAGE.md)
        binaural A3 E4 beat=octave octaves=5 (headphones; each difference = its carrier / 32)"""


def _styles() -> dict:
    from .arrange.styles import load_styles
    return {role: {st.name: st for st in d.values()} for role, d in load_styles().items()}


def _first_comment(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                return line.lstrip("# ").strip()
            if line.strip():
                break
    return ""


def catalog(compact: bool = True) -> str:
    from .arrange.ensemble import defaults
    from .arrange.events import EVENT_TYPES, RENDERED
    from .instruments import REGISTRY, describe, list_presets
    lines = ["SongMap catalog (songmap describe" + (" --compact)" if compact else ")")]
    for i, (role, styles) in enumerate(_styles().items()):
        names = " ".join("|".join([n, *st.get("aliases", [])]) for n, st in styles.items())
        mods = sorted({m for st in styles.values() for m in (st.get("mods") or {})})
        lines.append(f"{'styles' if i == 0 else '':7} {role}: {names}" + (f"  +{' +'.join(mods)}" if mods else ""))
        if not compact:
            lines += [f"          {n}: {_first_comment(st.path)}" for n, st in styles.items()]
    d = defaults()
    pieces = list((d["instruments"].get("drums") or {}).get("kit", {})) + list(d.get("kit_fallback", {}))
    lines.append(f"kit     {' '.join(dict.fromkeys(pieces))}")
    presets = list_presets()
    lines.append("inst    " + " ".join(n + (f"/{','.join(presets[n])}" if n in presets else "") for n in REGISTRY))
    from .instruments.sampler.library import manifest, voices
    lines.append("sfz     " + " ".join(f"sampler/{name}" for name in manifest()["voices"]))
    lines.append("        install/status: songmap samples install | songmap samples list")
    lines.append(f"events  {' '.join(RENDERED)}; cue-only until P3/P4: "
                 + " ".join(t for t in EVENT_TYPES if t not in RENDERED))
    lines.append("roles   drums bass pad arp lead fx; any other role plays the instrument of its name (inst to set)")
    lines += NOTES.splitlines() + SM.splitlines()
    if not compact:
        lines += ["", "instrument params (defaults):"] + ["  " + x for x in describe().splitlines()]
        lines += ["", "sampled instruments (exact float pitch; recorded vibrato remains in the samples):"]
        lines += [f"  {v['ref']} ({v['family']}, {'installed' if v['installed'] else 'not installed'}): "
                  f"{v['description']} Range MIDI {v['range'][0]}..{v['range'][1]}; {v['license']}."
                  for v in voices()]
    return "\n".join(lines) + "\n"


__all__ = ["catalog"]
