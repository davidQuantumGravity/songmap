"""Read-only musical display data for immutable comparison takes and saved sources."""
from __future__ import annotations

from functools import lru_cache
import json
import math

from .instrument_lab import safe_path, voice_name
from .project import parse_text
from ..arrange.expand import expand
from ..parse.fmt import song_to_raw
from ..perform.play import play
from ..render import held_beats
from ..theory.tuning import SIXTH, parse_tuning


def pitch_label(pitch):
    """Canonical nearest Western note plus signed sixth-step accidentals."""
    nearest = int(math.floor(float(pitch) + .5))
    delta = int(round((float(pitch) - nearest) / SIXTH))
    name = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")[nearest % 12]
    return ("^" * delta if delta > 0 else "v" * -delta) + name + str(nearest // 12 - 1)


def structure(arr):
    tl = arr.timeline
    bars = []
    for i in range(math.ceil(tl.total_bars)):
        beat, end = tl.bar_to_beat(i), tl.bar_to_beat(min(i + 1, tl.total_bars))
        span = tl.section_at(beat)
        bars.append({"index": i, "label": f"Bar {i + 1}", "section": span.name if span else "",
                     "start": round(tl.beat_to_sec(beat), 6), "end": round(tl.beat_to_sec(end), 6),
                     "beats": round(end - beat, 6)})
    return {"title": arr.song.title, "tuning": parse_tuning(arr.song.tuning).name,
            "seconds": tl.seconds, "music_seconds": tl.music_seconds,
            "bars": bars, "sections": [{"name": s.name, "first_bar": s.start_bar,
                "bars": s.bars, "start": tl.beat_to_sec(s.start), "end": tl.beat_to_sec(s.end)} for s in tl.sections]}


@lru_cache(maxsize=24)
def source_structure(path, source):
    return structure(expand(parse_text(source, path)))


def saved_structure(root, path):
    p = safe_path(root, path)
    return source_structure(str(p), p.read_text(encoding="utf-8-sig"))


def equivalent(a, b):
    """Ignore arithmetic noise at shifted excerpt origins, not musical timing edits."""
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-5)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(equivalent(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(equivalent(a[k], b[k]) for k in a)
    return a == b


@lru_cache(maxsize=32)
def take_score(path, source, start, seconds):
    arr = expand(parse_text(source, path))
    tl = arr.timeline
    data = structure(arr)
    raw = song_to_raw(arr.song)
    shared_mix = {key: raw.get(key) for key in ("returns", "master", "binaural")}
    data.update(start=start, seconds=seconds, parts=[])
    data["bars"] = [{**b, "start": max(0, b["start"] - start), "end": min(seconds, b["end"] - start)}
                    for b in data["bars"] if b["end"] > start and b["start"] < start + seconds]
    data["chords"] = [{"start": max(0, tl.beat_to_sec(sp.start) - start),
                       "end": min(seconds, tl.beat_to_sec(sp.end) - start), "symbol": sp.chord.symbol}
                      for sp in arr.harmony.spans if sp.chord is not None
                      and tl.beat_to_sec(sp.end) > start and tl.beat_to_sec(sp.start) < start + seconds]
    for part, events in play(arr).items():
        notes, fingerprint, voices = [], [], {}
        for event in events:
            a = tl.beat_to_sec(event.beat) - start
            b = tl.beat_to_sec(event.beat + max(held_beats(event), .001)) - start
            if b <= 0 or a >= seconds:
                continue
            voice = arr.ensemble.voice(part, event.piece)
            voices[event.piece or ""] = {"use": voice.use, "params": voice.params}
            for pitch in event.pitches or (None,):
                notes.append({"start": round(a, 6), "end": round(b, 6),
                              "pitch": float(pitch) if pitch is not None else None,
                              "label": pitch_label(pitch) if pitch is not None else event.piece or part,
                              "hz": 440 * 2 ** ((float(pitch) - 69) / 12) if pitch is not None else None,
                              "micro": pitch is not None and abs(float(pitch) - round(float(pitch))) > 1e-6,
                              "velocity": event.vel, "piece": event.piece})
            fingerprint.append([float(a), float(b), list(event.pitches), float(event.vel), event.piece,
                                event.art, event.pan, event.gain_db, event.params, list(event.patch)])
        if not notes:
            continue
        uses = list(dict.fromkeys(v["use"] for v in voices.values()))
        data["parts"].append({"part": part, "voice": ", ".join(voice_name(v) for v in uses),
                              "uses": uses, "kit": arr.ensemble.is_kit(part), "notes": notes,
                              "fingerprint": json.dumps(fingerprint, sort_keys=True),
                              "sound": json.dumps({"voices": voices, "patches": raw.get("patches") if any(v.startswith("patch/") for v in uses) else None}, sort_keys=True),
                              "mix": json.dumps({"part": arr.ensemble.mix.get(part, {}), "master_bus": arr.ensemble.mix.get("master", {}),
                                                 "shared": shared_mix}, sort_keys=True)})
    return data


def comparison_score(store, sid, candidates=None):
    s = store.get(sid)
    ids = s["pair"] if candidates is None else candidates
    if not 1 <= len(ids) <= 2 or len(set(ids)) != len(ids):
        raise ValueError("Choose one or two distinct saved takes")
    takes = []
    for cid in ids:
        c = next((c for c in s["candidates"] if c["id"] == cid), None)
        if c is None:
            raise ValueError("No such saved take")
        data = take_score(str(store.root / c.get("path", s["path"])), c["source"], c.get("start", s["start"]), s["seconds"])
        takes.append({**data, "id": cid, "parts": [dict(p) for p in data["parts"]]})
    names = sorted({p["part"] for t in takes for p in t["parts"]})
    changes = {}
    for part in names:
        a, b = [next((p for p in t["parts"] if p["part"] == part), None) for t in takes] if len(takes) == 2 else (None, None)
        reasons = []
        if len(takes) == 2:
            if not a or not b or not equivalent(json.loads(a["fingerprint"]), json.loads(b["fingerprint"])):
                reasons.append("notes / expression")
            if not a or not b or a["sound"] != b["sound"]:
                reasons.append("instrument")
            if not a or not b or a["mix"] != b["mix"]:
                reasons.append("mix")
        changes[part] = reasons
    for take in takes:
        for p in take["parts"]:
            p["changes"] = changes[p["part"]]
            for key in ("fingerprint", "sound", "mix"):
                p.pop(key)
    return {"takes": takes, "changes": changes}
