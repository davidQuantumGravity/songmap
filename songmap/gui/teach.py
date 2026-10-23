"""The Studio's theory teacher: a deterministic reading of a song's harmony, explained in plain words.

No language model: Roman numerals from the key's scale, functions from the scale degree, cadences and
voice-leading from root motion and common tones, the golden (36-EDO) chords from their interval sizes,
and the automated ear's findings (listen.py) with what each kind of finding means. The client places the
sounding notes against the chord at the playhead (chord tone, tension, sixth-step inflection).
"""
from __future__ import annotations

from ..theory.harmony import QUALITY
from ..theory.keys import parse_key
from ..theory.tuning import OCTAVE, SIXTH, pc_semitones

NUMERALS = ("I", "II", "III", "IV", "V", "VI", "VII")
# where a root a given number of semitones above the tonic sits, measured against the major scale
CHROMATIC = {0: (0, ""), 1: (1, "b"), 2: (1, ""), 3: (2, "b"), 4: (2, ""), 5: (3, ""), 6: (3, "#"),
             7: (4, ""), 8: (5, "b"), 9: (5, ""), 10: (6, "b"), 11: (6, "")}
MAJOR = (0, 2, 4, 5, 7, 9, 11)

QUALITY_TEXT = {
    "": ("major", "bright and settled: a major third (4 semitones) over the root, a perfect fifth (7) above"),
    "m": ("minor", "darker and inward: a minor third (3 semitones) over the root"),
    "dim": ("diminished", "tense and unstable: two minor thirds stacked; the tritone between root and fifth wants to resolve"),
    "aug": ("augmented", "floating, unresolved: two major thirds stacked, no perfect fifth to anchor it"),
    "5": ("power chord", "neither major nor minor: root and fifth only, open and strong"),
    "sus2": ("suspended 2nd", "open and airy: the third is replaced by the 2nd, so it is neither major nor minor"),
    "sus4": ("suspended 4th", "leaning: the 4th sits where the third would be and usually wants to fall to it"),
    "6": ("major sixth", "sweet and settled: a major triad with the 6th added (a vintage, lounge colour)"),
    "m6": ("minor sixth", "bittersweet: a minor triad with a major 6th (a noir, tango colour)"),
    "7": ("dominant seventh", "pulls forward: a major triad plus a minor 7th; its tritone (3rd against 7th) wants to resolve"),
    "maj7": ("major seventh", "soft and glowing: the 7th a semitone under the octave adds shimmer without tension"),
    "mmaj7": ("minor-major seventh", "mysterious, cinematic: a minor triad with a major 7th"),
    "m7": ("minor seventh", "mellow and smooth: a minor triad with a minor 7th"),
    "m7b5": ("half-diminished", "yearning: a diminished triad with a minor 7th; a classic way into a minor-key V"),
    "dim7": ("diminished seventh", "maximally tense and symmetric: stacked minor thirds that can resolve almost anywhere"),
    "add9": ("add nine", "a major triad with a 9th on top: open and modern"),
    "madd9": ("minor add nine", "a minor triad with a 9th: wistful"),
    "9": ("dominant ninth", "a dominant 7th with a 9th: funky, rich"),
    "maj9": ("major ninth", "lush: a maj7 with a 9th"),
    "m9": ("minor ninth", "smooth and deep: an m7 with a 9th"),
    "g": ("golden triad", "the golden third (11 sixth-steps, 3.67 semitones) sits between minor and major: neither happy nor sad, "
                          "it glows; two golden thirds stack to 7.33 semitones, a fifth stretched by a sixth-step"),
    "g7": ("golden seventh", "a golden triad with an 11-semitone seventh on top: the golden colour with a maj7 shimmer"),
    "s": ("silver triad", "stacked silver thirds (10 sixth-steps, 3.33 semitones): a minor-ish, cooler shade between minor and "
                          "neutral, with a fifth narrowed by a sixth-step"),
    "T13": ("golden partner", "thirds of 13 sixth-steps (4.33 semitones): a stretched, wide major colour"),
}

FUNCTION_TEXT = {
    "tonic": "home: the music can rest here",
    "predominant": "moving away from home, preparing the dominant",
    "dominant": "tension that wants to resolve home",
    "borrowed": "borrowed from the parallel key (a modal colour from outside the scale)",
    "chromatic": "outside the key: a colour or a passing step",
    "golden": "a golden-harmony colour (36-EDO): its thirds are neither major nor minor",
}

FINDING_TEXT = {
    "clash": "a held note sits a half step above a chord tone (a minor-9th rub). Short or on weak beats it is a passing "
             "colour; held on a strong beat it sounds like a wrong note, because the two pitches beat against each other.",
    "appoggiatura": "a dissonance on the beat that resolves by step: one of the most expressive moves in melody "
                    "(the ear feels the lean, then the relief). Fine when you mean it.",
    "register": "two parts in the same octave mask each other: the ear can't tell them apart and the mix turns muddy. "
                "Arrangers give each part its own register.",
    "repetition": "the same bar repeated exactly sounds mechanical; real players vary a little every time. Small changes "
                  "(a fill, a velocity change, a rest, a new voicing) keep a loop alive.",
    "dynamics": "flat velocity or no dynamic shape sounds programmed. Music breathes: phrases swell and relax, accents "
                "mark the strong beats.",
    "density": "too many parts at once compete for attention and space; five or six layers is usually the limit before "
               "detail turns into noise.",
    "hits": "impacts lose their power when they come too often; the ear adapts. Save them for real arrivals.",
    "range": "a part outside its instrument's comfortable range sounds strained (too high) or muddy (too low).",
    "ending": "ending away from the home chord leaves the song unresolved, like a question with no answer.",
    "contrast": "sections that are equally loud feel the same; a chorus feels bigger only next to something smaller.",
    "balance": "the frequency or level balance is off: the melody is buried, or the low end swamps the rest.",
    "clipping": "the signal went over full scale and was cut flat, which sounds like crackle or harshness.",
    "binaural": "the binaural carrier tone forms an interval with the harmony; a fraction of a semitone off a chord tone it "
                "beats and sounds out of tune.",
}


def _quality_of(intervals: tuple) -> str | None:
    for name, ivs in QUALITY.items():
        if len(ivs) == len(intervals) and all(abs(a - b) < 1e-6 for a, b in zip(ivs, intervals)):
            return name
    return None


def roman(root: float, intervals: tuple, key: str) -> dict:
    """Roman numeral, scale degree and function of a chord in a key."""
    tonic, scale = parse_key(key)
    rel = pc_semitones(root - tonic)
    k = round(rel)
    micro = round((rel - k) / SIXTH)                     # sixth-steps off the semitone grid
    k %= OCTAVE
    in_scale = next((i for i, s in enumerate(scale) if abs(pc_semitones(s - rel)) < 1e-6
                     or abs(pc_semitones(s - rel) - OCTAVE) < 1e-6), None) if len(scale) == 7 else None
    if in_scale is not None:
        deg, acc = in_scale, ""
    else:
        deg, acc = CHROMATIC[k]
        if len(scale) == 7:                               # spell against this mode's own degree
            d = pc_semitones(k - scale[deg])
            d = d - OCTAVE if d > OCTAVE / 2 else d
            acc = "#" if d > 0.5 else "b" if d < -0.5 else ""
    q = _quality_of(intervals)
    third = intervals[1] if len(intervals) > 1 else 4
    minorish = third < 3.5
    num = NUMERALS[deg].lower() if minorish else NUMERALS[deg]
    suffix = {"dim": "°", "dim7": "°7", "m7b5": "ø7", "aug": "+", "7": "7", "m7": "7", "maj7": "maj7", "9": "9",
              "m9": "9", "maj9": "maj9", "6": "6", "m6": "6", "sus2": "sus2", "sus4": "sus4", "add9": "add9",
              "madd9": "add9", "mmaj7": "maj7", "g": "g", "g7": "g7", "s": "s", "T13": "T"}.get(q or "", "")
    ud = "↑" * micro if micro > 0 else "↓" * -micro           # sixth-steps (not "v", which reads as a numeral)
    golden = q in ("g", "g7", "s", "T13") or micro != 0
    if golden:
        func = "golden"
    elif in_scale is None:
        func = "borrowed" if acc == "b" and deg in (2, 5, 6) else "chromatic"
    else:
        func = {0: "tonic", 5: "tonic", 2: "tonic", 1: "predominant", 3: "predominant", 4: "dominant", 6: "dominant"}[deg]
    return {"numeral": ud + acc + num + suffix, "degree": deg + 1, "accidental": acc, "sixth_steps": micro,
            "function": func, "quality": q, "in_key": in_scale is not None}


def _common_tones(a, b) -> int:
    pa = {round(pc_semitones(a.root + i) * 3) for i in a.intervals}
    pb = {round(pc_semitones(b.root + i) * 3) for i in b.intervals}
    return len(pa & pb)


def motion(a, b) -> dict:
    """Root motion between two chords and what it does."""
    d = pc_semitones(b.root - a.root)
    up = round(d, 3)
    name = {0: "stays on the same root", 5: "rises a fourth (falls a fifth): the strongest root motion",
            7: "rises a fifth", 2: "steps up a whole tone", 10: "steps down a whole tone",
            1: "slides up a semitone", 11: "slides down a semitone", 3: "rises a minor third",
            9: "falls a minor third", 4: "rises a major third", 8: "falls a major third",
            6: "moves a tritone (the most distant root)"}.get(round(up) % 12 if abs(up - round(up)) < 1e-6 else -1)
    if name is None:
        steps = round(d / SIXTH)
        name = f"moves {steps} sixth-steps ({d:.2f} semitones): a golden slide off the semitone grid"
    return {"semitones": up, "text": name, "common_tones": _common_tones(a, b)}


def cadence(fa: dict, fb: dict, at_section_end: bool) -> str | None:
    na, nb = fa["numeral"].rstrip("0123456789°ø+maj").upper(), fb["numeral"].rstrip("0123456789°ø+maj").upper()
    if fa["function"] == "dominant" and fb["degree"] == 1 and fb["function"] == "tonic":
        return "authentic cadence (V → I): the strongest arrival home"
    if fa["function"] == "dominant" and fb["degree"] == 6 and fb["function"] == "tonic":
        return "deceptive cadence (V → vi): it sets up home and swerves away"
    if na.endswith("IV") and fb["degree"] == 1 and not fa["accidental"]:
        return "plagal cadence (IV → I): the soft 'amen' arrival"
    if at_section_end and fb["function"] == "dominant":
        return "half cadence: the section ends on the dominant, a question waiting for an answer"
    if fa["function"] == "golden" and fb["function"] == "tonic" and fb["degree"] == 1:
        return "golden cadence: a golden colour resolving home"
    if na.startswith("B") and fb["degree"] == 1:
        return "modal cadence: a borrowed chord (outside the scale) resolving home"
    return None


def analyze(arr) -> dict:
    """Every chord change of the song, with its numeral, function, quality, explanations, the motion into it
    and the cadences; per section a progression summary; and the automated ear's findings."""
    song, tl = arr.song, arr.timeline
    sections = {s.index: s for s in tl.sections}
    chords = []
    for sp in arr.harmony.spans:
        if sp.chord is None:
            continue
        a, b = tl.beat_to_sec(sp.start), tl.beat_to_sec(sp.end)
        if chords and not sp.onset and chords[-1]["symbol"] == sp.chord.symbol and abs(chords[-1]["end"] - a) < 1e-6:
            chords[-1]["end"] = round(b, 4)
            chords[-1]["end_beat"] = sp.end
            continue
        sec = tl.section_at(sp.start)
        key = (song.sections[sec.index].key if sec is not None and sec.index < len(song.sections) else None) or song.key
        info = roman(sp.chord.root, sp.chord.intervals, key)
        qname, qtext = QUALITY_TEXT.get(info["quality"] or "", ("chord", "an altered or extended chord"))
        chords.append({"symbol": sp.chord.symbol, "start": round(a, 4), "end": round(b, 4), "start_beat": sp.start,
                       "end_beat": sp.end, "key": key, "section": sec.name if sec else None,
                       "section_index": sec.index if sec else None, "root": sp.chord.root,
                       "tones": [round(pc_semitones(sp.chord.root + i), 4) for i in sp.chord.intervals],
                       "intervals": list(sp.chord.intervals), **info, "quality_name": qname, "quality_text": qtext,
                       "function_text": FUNCTION_TEXT[info["function"]], "_chord": sp.chord})
    for i, c in enumerate(chords):
        prev = chords[i - 1] if i else None
        end_of_section = i + 1 == len(chords) or chords[i + 1]["section_index"] != c["section_index"]
        c["motion"] = motion(prev["_chord"], c["_chord"]) if prev else None
        c["cadence"] = cadence(prev, c, end_of_section) if prev else None
        c["explain"] = _explain(c, prev)
    for c in chords:
        del c["_chord"]
    secs = []
    for s in tl.sections:
        cs = [c for c in chords if c["section_index"] == s.index]
        cads = [c["cadence"] for c in cs if c["cadence"]]
        fn = [c["function"] for c in cs]
        skey = (song.sections[s.index].key if s.index < len(song.sections) else None) or song.key
        secs.append({"name": s.name, "index": s.index, "start": round(tl.beat_to_sec(s.start), 4), "key": skey,
                     "progression": " – ".join(c["numeral"] for c in cs), "symbols": " ".join(c["symbol"] for c in cs),
                     "ends_on": cs[-1]["numeral"] if cs else None, "cadences": cads,
                     "summary": (f"{s.name} moves to {skey} (the song is in {song.key}). " if skey != song.key else "")
                     + _section_summary(s.name, cs, fn)})
    return {"key": song.key, "tuning": getattr(song, "tuning", "12edo"), "chords": chords, "sections": secs,
            "findings": _findings(arr)}


def _explain(c: dict, prev: dict | None) -> str:
    parts = [f"{c['symbol']} is {c['numeral']} in {c['key']}: a {c['quality_name']} chord on scale degree {c['degree']}"
             + (f" ({c['accidental']} — outside the scale)" if c["accidental"] else "")
             + (f", {abs(c['sixth_steps'])} sixth-step{'s' if abs(c['sixth_steps']) > 1 else ''} "
                f"{'above' if c['sixth_steps'] > 0 else 'below'} the semitone grid" if c["sixth_steps"] else "") + ".",
             f"Its sound: {c['quality_text']}.", f"Its role: {c['function_text']}."]
    if prev and c["motion"]:
        m = c["motion"]
        parts.append(f"From {prev['symbol']} the root {m['text']}; {m['common_tones']} note"
                     f"{'s' if m['common_tones'] != 1 else ''} stay{'s' if m['common_tones'] == 1 else ''} in common"
                     + (" (a smooth change)." if m["common_tones"] >= 2 else "."))
    if c["cadence"]:
        parts.append(f"That makes a {c['cadence']}.")
    return " ".join(parts)


def _section_summary(name: str, cs: list, fn: list) -> str:
    if not cs:
        return f"{name}: no chords."
    out = [f"{name} moves {' – '.join(c['numeral'] for c in cs)}."]
    if fn.count("dominant"):
        n = fn.count("dominant")
        out.append(f"{n} dominant chord{'s build' if n > 1 else ' builds'} tension.")
    if fn.count("golden"):
        out.append(f"{fn.count('golden')} golden colour{'s' if fn.count('golden') > 1 else ''} (36-EDO).")
    if fn.count("borrowed") + fn.count("chromatic"):
        out.append("It borrows from outside the key for colour.")
    last = cs[-1]
    out.append("It ends at home." if last["function"] == "tonic" and last["degree"] == 1 else
               "It ends on the dominant: a question for the next section." if last["function"] == "dominant" else
               f"It ends on {last['numeral']}, away from home.")
    return " ".join(out)


def _findings(arr) -> list:
    try:
        from ..listen import listen
        rep = listen(arr)
    except Exception:                                    # noqa: BLE001  (the ear is advisory)
        return []
    out = []
    for f in rep.findings:
        why = FINDING_TEXT.get(f.kind, "")
        out.append({"severity": f.severity, "kind": f.kind, "where": f.where, "message": f.message, "fix": f.fix,
                    "why": why})
    return out
