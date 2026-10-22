"""`songmap listen`: an automated ear. It reads the written arrangement (and a render's qa.json when
there is one) and reports what a listener would notice: clashes, crowding, mechanical repetition,
flat dynamics, hit fatigue, weak contrast, a buried melody, an unresolved ending.

It is a proxy, not a judge. It catches the common ways a score sounds wrong or robotic; whether
the music is *good* still needs ears. Each finding has a place (section, bar) and a suggestion.
"""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass

import numpy as np

SEVERITY = ("problem", "warning", "note")
MELODIC = ("lead", "keys", "piano", "melody", "gtr", "guitar", "epiano", "organ", "flute", "violin", "cello")
RANGES = {"bass": (28, 60), "lead": (55, 91), "keys": (36, 96), "piano": (36, 96), "epiano": (40, 88),
          "organ": (36, 88), "gtr": (40, 88), "guitar": (40, 88), "pad": (40, 91), "arp": (48, 96)}


@dataclass
class Finding:
    severity: str          # problem | warning | note
    kind: str
    where: str             # "chorus bar 3" or "song"
    message: str
    fix: str = ""


@dataclass
class Report:
    title: str
    findings: list
    facts: dict

    def counts(self) -> dict:
        c = Counter(f.severity for f in self.findings)
        return {s: c.get(s, 0) for s in SEVERITY}

    def text(self) -> str:
        c = self.counts()
        lines = [f"listen: {self.title}",
                 "  " + ", ".join(f"{k} {v}" for k, v in self.facts.items() if not isinstance(v, (dict, list))),
                 f"  {c['problem']} problems, {c['warning']} warnings, {c['note']} notes"]
        for s in SEVERITY:
            for f in self.findings:
                if f.severity == s:
                    lines.append(f"  {s:7s} {f.where}: {f.message}" + (f"  -> {f.fix}" if f.fix else ""))
        lines.append("  (an automated ear: it catches common faults; whether the music is good still needs listening)")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {"title": self.title, "facts": self.facts, "counts": self.counts(),
                "findings": [asdict(f) for f in self.findings]}


def _where(tl, beat: float) -> str:
    s = tl.section_at(beat)
    if s is None:
        return f"bar {int(beat // tl.bpb)}"
    return f"{s.name} bar {int((beat - s.start) // tl.bpb) + 1}"


def _pc_dist(a: float, b: float) -> float:
    d = (a - b) % 12
    return min(d, 12 - d)


def listen(arr, qa: dict | None = None) -> Report:
    """arr: an expanded Arrangement. qa: a render's qa.json (optional) for loudness checks."""
    song, tl, harm = arr.song, arr.timeline, arr.harmony
    bpb = tl.bpb
    out: list[Finding] = []
    kit = {p for p in arr.parts if arr.ensemble.is_kit(p)}
    pitched = {p: evs for p, evs in arr.parts.items() if p not in kit}

    # 1. clashes: a melody note held on a strong beat, a half step from a chord tone it isn't
    clashes, leans = defaultdict(list), defaultdict(list)
    checked = 0

    def chord_tone(p, beat):
        c = harm.chord_at(beat)
        return c is not None and any(_pc_dist(p, c.root + i) < 0.2 for i in c.intervals)

    for part, evs in pitched.items():
        if part not in MELODIC and part not in song.motifs and not any(len(e.pitches) == 1 for e in evs):
            continue
        line = [e for e in evs if len(e.pitches) == 1 and "grace" not in e.tags]
        nxt = {id(a): b for a, b in zip(line, line[1:])}
        for e in evs:
            if len(e.pitches) != 1 or e.dur < 0.75 or "grace" in e.tags or "ghost" in e.tags:
                continue
            pos = e.beat % bpb
            if not (abs(pos) < 1e-6 or abs(pos - bpb / 2) < 1e-6 or e.dur >= 1.5):
                continue
            ch = harm.chord_at(e.beat)
            if ch is None:
                continue
            checked += 1
            tones = [ch.root + i for i in ch.intervals]
            p = e.pitches[0]
            if any(_pc_dist(p, t) < 0.2 for t in tones):
                continue
            rub = [t for t in tones if 0.5 <= (p - t) % 12 <= 1.2]     # a minor 9th above a chord tone
            if rub:
                n = nxt.get(id(e))
                resolves = (n is not None and 0.5 <= abs(n.pitches[0] - p) <= 2.2 and n.beat - (e.beat + e.dur) < 0.26
                            and chord_tone(n.pitches[0], n.beat))
                (leans if resolves else clashes)[part].append((e.beat, p, ch.symbol))
    for part, hits in leans.items():
        b, p, sym = hits[0]
        out.append(Finding("note", "appoggiatura", _where(tl, b),
                           f"{part} leans on {len(hits)} dissonance(s) that resolve by step (first over {sym}): "
                           "expressive if intended", ""))
    for part, hits in clashes.items():
        names = "C C# D Eb E F F# G Ab A Bb B".split()
        b, p, sym = hits[0]
        note = names[int(round(p)) % 12]
        more = f" (and {len(hits) - 1} more)" if len(hits) > 1 else ""
        out.append(Finding("problem" if len(hits) > 2 else "warning", "clash", _where(tl, b),
                           f"{part} holds {note} over {sym}, a half step above a chord tone (a minor-9th rub){more}",
                           "move the note to a chord tone on strong beats, make it a short passing note, "
                           "or change the chord"))

    # 2. register collisions: two melodic or chord parts living in the same octave in one section
    for span in tl.sections:
        meds = {}
        for part, evs in pitched.items():
            ps = [p for e in evs if span.start <= e.beat < span.end for p in e.pitches]
            if len(ps) >= 6:
                meds[part] = float(np.median(ps))
        names = sorted(meds)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                both_melodic = a in MELODIC and b in MELODIC
                if abs(meds[a] - meds[b]) < 3 and (both_melodic or {a, b} & {"pad", "arp"} and {a, b} & set(MELODIC)):
                    out.append(Finding("warning", "register", f"{span.name}",
                                       f"{a} and {b} sit in the same register (around MIDI {int(meds[a])})",
                                       f"move one an octave (oct: 1 / oct: -1), or give one of them rests here"))

    # 3. mechanical repetition: the same bar over and over
    for part, evs in arr.parts.items():
        bars = defaultdict(list)
        for e in evs:
            if any(t.startswith("event:") for t in e.tags):
                continue
            bars[int(e.beat // bpb)].append((round(e.beat % bpb, 3), e.piece, tuple(e.pitches), round(e.vel, 2)))
        run, start, best = 1, 0, (1, 0)
        keys = sorted(bars)
        for i in range(1, len(keys)):
            same = keys[i] == keys[i - 1] + 1 and sorted(bars[keys[i]]) == sorted(bars[keys[i - 1]])
            run, start = (run + 1, start) if same else (1, i)
            if run > best[0]:
                best = (run, keys[start])
        if best[0] >= 16:
            out.append(Finding("warning", "repetition", f"bar {best[1]}",
                               f"{part} plays the identical bar {best[0]} times in a row",
                               "vary it every 4-8 bars: a fill, a velocity change, a rest, a new voicing"))

    # 4. flat dynamics: one velocity for a whole section's worth of notes
    for part, evs in arr.parts.items():
        by_sec = defaultdict(list)
        for e in evs:
            if not any(t.startswith("event:") for t in e.tags):
                by_sec[e.section].append(e.vel)
        flat = [s for s, v in by_sec.items() if len(v) >= 12 and np.std(v) < 0.01]
        if len(flat) >= 2 or (flat and len(by_sec) == 1):
            out.append(Finding("warning", "dynamics", ", ".join(flat[:3]),
                               f"every {part} note has the same velocity",
                               "shape it: dyn= arcs, accents (^ or X), ghosts (o), velocity lists"))
    no_dyn = [s.name for s in song.sections if not s.dyn]
    if len(song.sections) >= 3 and len(no_dyn) > len(song.sections) / 2:
        out.append(Finding("note", "dynamics", "song", f"{len(no_dyn)} of {len(song.sections)} sections have no dyn= shape",
                           "give most sections an arc (dyn=p<mf, dyn=mf>p)"))

    # 5. density: too many parts at once
    for span in tl.sections:
        for bar in range(int(span.start // bpb), int(np.ceil(span.end / bpb - 1e-9))):
            playing = {p for p, evs in arr.parts.items() if p != "fx"
                       and any(bar * bpb <= e.beat < (bar + 1) * bpb for e in evs)}
            if len(playing) > 6:
                out.append(Finding("warning", "density", _where(tl, bar * bpb),
                                   f"{len(playing)} parts play at once ({', '.join(sorted(playing))})",
                                   "keep 5-6 at most; drop a doubling or give a part rests"))
                break

    # 6. hit fatigue
    impacts = [e for e in arr.events if e.type == "impact"]
    secs = max(tl.seconds, 1.0)
    if impacts and len(impacts) > max(2, secs / 15):
        out.append(Finding("warning", "hits", "song",
                           f"{len(impacts)} impacts in {secs:.0f} s (about one every {secs / len(impacts):.0f} s)",
                           "keep big impacts for the main arrivals (one per 15-20 s); use a new layer, a fill or a "
                           "stop-time for the rest"))

    # 7. range
    for part, evs in pitched.items():
        lo, hi = RANGES.get(part, (24, 100))
        bad = [e for e in evs for p in e.pitches if p < lo or p > hi]
        if bad:
            out.append(Finding("warning", "range", _where(tl, bad[0].beat),
                               f"{part} goes outside its comfortable range ({len(bad)} notes outside MIDI {lo}-{hi})",
                               "move it with oct: or transpose the line"))

    # 8. the ending
    last = harm.chord_at(max(tl.total_beats - 0.01, 0))
    try:
        from .theory.keys import parse_key
        tonic, _ = parse_key(song.sections[-1].key or song.key)
        if last is not None and _pc_dist(last.root, tonic) > 0.2 and "sus" not in last.symbol:
            out.append(Finding("note", "ending", song.sections[-1].name,
                               f"the song ends on {last.symbol}, not on the home chord",
                               "end on I (or i, or its Picardy major) unless the hang is deliberate"))
    except Exception:                                                # noqa: BLE001
        pass

    # 9. loudness, from a render
    facts = {"bars": tl.total_bars, "seconds": round(tl.seconds, 1), "sections": len(song.sections),
             "parts": len(arr.parts), "impacts": len(impacts), "melody notes checked against chords": checked}
    if qa:
        out += _loudness_findings(qa, song)
        facts["lufs"] = qa.get("lufs")
    return Report(song.title, out, facts)


def _loudness_findings(qa: dict, song) -> list:
    out = []
    secs = qa.get("sections") or []
    loud = [(s["name"], s["loudness"]) for s in secs if s.get("loudness") is not None and s["loudness"] > -70]
    if len(loud) >= 3:
        order = sorted(loud, key=lambda x: -x[1])
        (peak, lp), (second, l2) = order[0], order[1]
        if lp - l2 < 2:
            out.append(Finding("warning", "contrast", peak,
                               f"the loudest section ({peak}, {lp:.1f} LUFS) is only {lp - l2:.1f} dB above {second}",
                               "make the peak bigger by arrangement (more parts, octave doubling) and quieten the "
                               "bar before it (!drop:1@-1)"))
        for i in range(1, len(loud) - 1):
            a, b, c = loud[i - 1][1], loud[i][1], loud[i + 1][1]
            if abs(b - a) < 1 and abs(b - c) < 1:
                out.append(Finding("note", "contrast", loud[i][0],
                                   f"{loud[i][0]} is within 1 dB of both neighbours",
                                   "contrast neighbouring sections by texture, register or density"))
                break
    for s in secs:
        if s.get("low", 0) > 0.9 and s.get("loudness", -99) > -40:
            out.append(Finding("note", "balance", s["name"], f"{s['name']} is very bass-heavy (low {s['low']:.2f})",
                               "lighten the sub or kick, or add mid/high parts"))
            break
    stems = qa.get("stems") or {}
    mel = [p for p in stems if p in MELODIC]
    acc = [p for p in stems if p not in mel and not p.startswith("return") and p != "fx"]
    if mel and acc:
        m = max(stems[p] for p in mel)
        top = max(acc, key=lambda p: stems[p])
        if stems[top] - m > 6:
            out.append(Finding("warning", "balance", "song",
                               f"the melody ({max(mel, key=lambda p: stems[p])}) is {stems[top] - m:.1f} dB under {top}",
                               f"raise it (mix {max(mel, key=lambda p: stems[p])} +3) or lower {top}"))
    if qa.get("clipped_samples"):
        out.append(Finding("problem", "clipping", "song", f"{qa['clipped_samples']} clipped samples", "lower the mix"))
    return out


def listen_file(path: str, qa_path: str | None = None, render_dir: str | None = None) -> Report:
    from .arrange.expand import expand
    from .parse import load
    arr = expand(load(path))
    qa = None
    for cand in filter(None, [qa_path, render_dir and os.path.join(render_dir, "qa.json")]):
        if os.path.isfile(cand):
            with open(cand, encoding="utf-8") as f:
                qa = json.load(f)
            break
    return listen(arr, qa)


__all__ = ["listen", "listen_file", "Report", "Finding"]
