"""cues.json: sections, events, named cues and the beat grid, in beats, seconds and video frames.

    {
      "format": "songmap-cues", "version": 1,
      "title": "...", "fps": 30, "tempo": 120, "meter": "4/4", "beats_per_bar": 4,
      "seconds": 123.0, "frames": 3690, "music_frames": 3600,
      "video": {"composition": "WeekSwarm", "frames": 3690},              # when the song declares one
      "sections": [{"name", "index", "bar", "bars", "beat", "beats", "start_s", "end_s",
                    "start_frame", "end_frame"}],                           # end = next section's start
      "events":   [{"type", "at", "section", "beat", "bar", "time_s", "frame",
                    "start_beat", "start_s", "start_frame", "params"}],    # start_* differs for risers
      "cues":     [{"name", "at", "beat", "bar", "time_s", "frame", "frame_error"}],
      "grid":     {"beat_frames": [0, 15, 30, ...], "bar_frames": [0, 60, ...]}
    }

Frames are `round(seconds * fps)`. The Remotion helper (P8) reads this file.
"""
from __future__ import annotations

import json

from ..parse import positions

FORMAT = "songmap-cues"
VERSION = 1


def build(arr) -> dict:
    song, tl = arr.song, arr.timeline
    bpb = tl.bpb

    def at(beat):
        t = tl.beat_to_sec(beat)
        return {"beat": round(beat, 6), "bar": round(beat / bpb, 6), "time_s": round(t, 6),
                "frame": tl.sec_to_frame(t)}

    secs = []
    for s in tl.sections:
        a, z = tl.beat_to_sec(s.start), tl.beat_to_sec(s.end)
        secs.append({"name": s.name, "index": s.index, "bar": s.start_bar, "bars": s.bars, "beat": s.start,
                     "beats": s.end - s.start, "start_s": round(a, 6), "end_s": round(z, 6),
                     "start_frame": tl.sec_to_frame(a), "end_frame": tl.sec_to_frame(z)})
    evs = []
    for e in arr.events:
        d = {"type": e.type, "at": e.at, "section": e.section, **at(e.beat)}
        st = tl.beat_to_sec(e.start)
        d.update({"start_beat": round(e.start, 6), "start_s": round(st, 6), "start_frame": tl.sec_to_frame(st),
                  "params": e.params})
        evs.append(d)
    cues = []
    for name, pos in song.cues.items():
        p = positions.resolve(pos, tl, song.cues)
        cues.append({"name": name, "at": str(pos), **at(p.beat), "frame_error": p.frame_error})
    nbeats = int(tl.total_beats + 1e-9)
    out = {
        "format": FORMAT, "version": VERSION, "title": song.title, "fps": tl.fps, "tempo": song.tempo,
        "meter": f"{song.meter[0]}/{song.meter[1]}", "beats_per_bar": bpb,
        "seconds": round(tl.seconds, 6), "frames": tl.frames, "music_frames": tl.sec_to_frame(tl.music_seconds),
        "sections": secs, "events": evs, "cues": cues,
        "grid": {"beat_frames": [tl.beat_to_frame(b) for b in range(nbeats + 1)],
                 "bar_frames": [tl.beat_to_frame(b * bpb) for b in range(int(tl.total_bars + 1e-9) + 1)]},
    }
    if song.video:
        out["video"] = dict(song.video)
    return out


def write(path: str, cues: dict) -> None:
    problems = validate(cues)
    if problems:
        raise ValueError("cues.json would be invalid: " + "; ".join(problems))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cues, f, indent=1, ensure_ascii=False)


_TOP = {"format": str, "version": int, "title": str, "fps": int, "tempo": (int, float), "meter": str,
        "beats_per_bar": (int, float), "seconds": (int, float), "frames": int, "music_frames": int,
        "sections": list, "events": list, "cues": list, "grid": dict}
_SEC = {"name": str, "index": int, "bar": (int, float), "bars": (int, float), "beat": (int, float),
        "beats": (int, float), "start_s": (int, float), "end_s": (int, float), "start_frame": int, "end_frame": int}
_EV = {"type": str, "at": str, "beat": (int, float), "bar": (int, float), "time_s": (int, float), "frame": int,
       "start_beat": (int, float), "start_s": (int, float), "start_frame": int, "params": dict}
_CUE = {"name": str, "at": str, "beat": (int, float), "bar": (int, float), "time_s": (int, float), "frame": int,
        "frame_error": int}


def _fields(obj, spec, where, out):
    if not isinstance(obj, dict):
        out.append(f"{where}: not an object")
        return
    for k, t in spec.items():
        if k not in obj:
            out.append(f"{where}: missing '{k}'")
        elif isinstance(obj[k], bool) or not isinstance(obj[k], t):
            out.append(f"{where}.{k}: wrong type {type(obj[k]).__name__}")


def validate(c: dict) -> list[str]:
    """Structural + consistency checks. Returns a list of problems (empty = valid)."""
    out: list[str] = []
    _fields(c, _TOP, "cues", out)
    if out:
        return out
    if c["format"] != FORMAT:
        out.append(f"format is '{c['format']}', expected '{FORMAT}'")
    fps = c["fps"]
    prev_end = 0
    for i, s in enumerate(c["sections"]):
        _fields(s, _SEC, f"sections[{i}]", out)
        if out:
            return out
        if s["start_frame"] != prev_end:
            out.append(f"section {s['name']} starts at frame {s['start_frame']}, previous ended at {prev_end}")
        if s["end_frame"] < s["start_frame"]:
            out.append(f"section {s['name']} ends before it starts")
        if abs(s["start_frame"] - s["start_s"] * fps) > 0.5 + 1e-6:
            out.append(f"section {s['name']}: start_frame does not match start_s")
        prev_end = s["end_frame"]
    if c["sections"] and prev_end != c["music_frames"]:
        out.append(f"sections end at frame {prev_end}, music_frames is {c['music_frames']}")
    if c["frames"] < c["music_frames"]:
        out.append("frames < music_frames")
    names = {s["name"] for s in c["sections"]}
    for i, e in enumerate(c["events"]):
        _fields(e, _EV, f"events[{i}]", out)
        if not out and e.get("section") is not None and e["section"] not in names:
            out.append(f"events[{i}]: unknown section {e['section']}")
        if not out and abs(e["frame"] - e["time_s"] * fps) > 0.5 + 1e-6:
            out.append(f"events[{i}]: frame does not match time_s")
    for i, q in enumerate(c["cues"]):
        _fields(q, _CUE, f"cues[{i}]", out)
    g = c["grid"]
    for k in ("beat_frames", "bar_frames"):
        v = g.get(k)
        if not isinstance(v, list) or any(isinstance(x, bool) or not isinstance(x, int) for x in v):
            out.append(f"grid.{k}: expected a list of frame numbers")
        elif v != sorted(v):
            out.append(f"grid.{k}: not increasing")
    if "video" in c and isinstance(c["video"], dict) and "frames" in c["video"] and c["video"]["frames"] != c["frames"]:
        out.append(f"song is {c['frames']} frames, video is {c['video']['frames']}")
    return out
