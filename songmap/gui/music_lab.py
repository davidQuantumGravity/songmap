"""Musical decisions using the existing durable A/B player and instrument lab."""
from __future__ import annotations

import copy
import math
import time
import uuid

from .instrument_lab import Lab, LOCK, digest, safe_path
from .project import parse_text
from ..arrange.expand import expand
from ..parse.fmt import song_to_raw

SCOPES = {"instrument", "riff", "arrangement", "snippet"}


def score(source, path):
    song = parse_text(source, path)
    return song, expand(song), song_to_raw(song)


def window(arr, start, seconds):
    if not (math.isfinite(start) and math.isfinite(seconds) and 0 <= start < arr.timeline.music_seconds
            and 1 <= seconds <= 30 and start + seconds <= arr.timeline.seconds + 1e-6):
        raise ValueError("Choose a start within the music and 1–30 seconds that fit within the score (including its tail)")


def protected_riff(raw, part):
    raw = copy.deepcopy(raw)
    for section in raw["sections"]:
        section["parts"].pop(part, None)
    raw.get("parts_feel", {}).pop(part, None)
    return raw


def grid(song):
    return (song.tempo, song.meter, song.tuning, song.seed, song.tail_seconds,
            [(s.name, s.bars, s.tempo, s.meter) for s in song.sections])


class MusicLab(Lab):
    def create(self, path, source, part, piece, start, seconds, brief, scope="instrument", comparison=None):
        if scope not in SCOPES:
            raise ValueError("Choose instrument, riff, arrangement or snippet")
        if scope == "instrument":
            return super().create(path, source, part, piece, start, seconds, brief)
        safe_path(self.root, path)
        _, arr, _ = score(source, str(self.root / path))
        window(arr, start, seconds)
        if scope == "riff" and (part not in arr.parts or not arr.parts[part]):
            raise ValueError("Choose a played part for the riff comparison")
        if scope == "riff" and piece:
            raise ValueError("Riff comparisons edit the whole part; choose the instrument tool for one kit piece")
        cid, sid = uuid.uuid4().hex, uuid.uuid4().hex
        c = self.take(source, path, start, "Original", "source", None)
        c["id"] = cid
        s = {"id": sid, "scope": scope, "path": path, "part": part if scope == "riff" else "Full mix",
             "piece": None, "use": "", "brief": brief[:4000], "start": start, "seconds": seconds,
             "base_source": source, "base_hash": digest(source), "candidates": [c], "incumbent": cid,
             "pair": [cid], "feedback": [], "status": "ready", "error": "", "applied": [],
             "created": time.time(), "updated": time.time()}
        # Validate the second excerpt before making a session visible.
        if scope == "snippet":
            if not comparison:
                raise ValueError("Choose B's saved source and start")
            b = self.excerpt(comparison, seconds)
            if b["source"] == source and b["start"] == start:
                raise ValueError("Choose a different excerpt for B")
            b["parent"] = cid
            s["candidates"].append(b)
            s["pair"].append(b["id"])
        return self.put(s)

    @staticmethod
    def take(source, path, start, label, origin, parent, reason=""):
        return {"id": uuid.uuid4().hex, "source": source, "path": path, "start": start,
                "label": label[:120], "origin": origin, "parent": parent, "reason": reason[:4000],
                "change": {"path": path, "start": start}, "audio": {}, "loudness": {}}

    def excerpt(self, change, seconds):
        path = change.get("path", "")
        if not isinstance(path, str):
            raise ValueError("Choose a saved score path")
        p = safe_path(self.root, path)
        source = p.read_text(encoding="utf-8-sig")
        try:
            start = float(change.get("start", 0))
        except (TypeError, ValueError):
            raise ValueError("Choose a numeric excerpt start") from None
        _, arr, _ = score(source, str(p))
        window(arr, start, seconds)
        return self.take(source, path, start, change.get("label", "Saved excerpt"), "excerpt", None)

    def add_candidate(self, sid, change, label, origin, reason=""):
        with LOCK:
            s = self.get(sid)
            scope = s.get("scope", "instrument")
            if scope == "instrument":
                return super().add_candidate(sid, change, label, origin, reason)
            if len(s["candidates"]) >= 24:
                raise ValueError("This session has reached 24 candidates; start a new session")
            parent = next(c for c in s["candidates"] if c["id"] == s["incumbent"])
            if scope == "snippet":
                c = self.excerpt(change, s["seconds"])
                if digest(c["source"]) == digest(parent["source"]) and c["start"] == parent["start"]:
                    raise ValueError("Choose a different excerpt")
                c.update(parent=parent["id"], label=label[:120])
            else:
                source = change.get("source")
                if not isinstance(source, str) or not source.strip() or len(source) > 250_000:
                    raise ValueError("Supply the complete edited score (at most 250,000 characters)")
                before, ba, br = score(parent["source"], str(self.root / s["path"]))
                after, aa, ar = score(source, str(self.root / s["path"]))
                window(aa, s["start"], s["seconds"])
                if br == ar:
                    raise ValueError("The challenger makes no musical change")
                if grid(before) != grid(after):
                    raise ValueError("Keep tempo, meter, tuning, seed, tail and section timing fixed for aligned A/B playback")
                if scope == "riff":
                    if protected_riff(br, s["part"]) != protected_riff(ar, s["part"]):
                        raise ValueError("Riff mode changes only the selected part's notes and expression. Keep backing, instruments, harmony and form fixed; inline a changed motif in that part.")
                    if repr(ba.parts.get(s["part"])) == repr(aa.parts.get(s["part"])):
                        raise ValueError("The selected part's performed notes and expression do not change")
                c = self.take(source, s["path"], s["start"], label, origin, parent["id"], reason)
                c["change"]["scope"] = scope
            s["candidates"].append(c)
            s["previous_pair"] = s["pair"]
            s["pair"] = [parent["id"], c["id"]]
            return self.put(s)

    def present(self, sid, focus=True):
        s = self.get(sid)
        if s.get("scope", "instrument") == "instrument":
            return super().present(sid, focus)
        if focus:
            self.prepare_focus(sid)
            s = self.get(sid)
        takes = {}
        for i, c in enumerate(s["candidates"], 1):
            _, arr, raw = score(c["source"], str(self.root / c["path"]))
            c.update(take=i, display_name=c["label"], verified_use=s["scope"], changes=[],
                     excerpt={"path": c["path"], "start": c["start"], "seconds": s["seconds"]},
                     parts=[{"part": p, "notes": len(events)} for p, events in arr.parts.items()])
            parent = takes.get(c["parent"])
            if parent:
                if s["scope"] == "snippet":
                    c["changes"] = [{"field": "Source window", "before": f"{parent['path']} @ {parent['start']:g}s",
                                     "after": f"{c['path']} @ {c['start']:g}s"}]
                else:
                    _, _, old = score(parent["source"], str(self.root / parent["path"]))
                    changed = [k for k in sorted(set(old) | set(raw)) if old.get(k) != raw.get(k)]
                    c["changes"] = [{"field": "Score", "before": "previous take", "after": ", ".join(changed)}]
            takes[c["id"]] = c
        s["audition"] = {"target": {"part": s["part"], "piece": None}, "accompaniment": [],
                         "solo_label": f"{s['part']} only", "can_solo": s["scope"] == "riff"}
        for f in s["feedback"]:
            chosen = f["pair"][f["choice"] == "b"] if f["choice"] in {"a", "b"} else None
            c = takes.get(chosen)
            f.update(selected_take=c["take"] if c else None, selected_voice=c["display_name"] if c else None)
        return s

    def context(self, sid):
        s = self.present(sid, focus=False)
        if s["scope"] == "instrument":
            return super().context(sid)
        parent = next(c for c in s["candidates"] if c["id"] == s["incumbent"])
        return {"scope": s["scope"], "brief": s["brief"], "path": s["path"], "part": s["part"],
                "source": parent["source"], "start": s["start"], "seconds": s["seconds"],
                "feedback": s["feedback"], "prior_feedback": s.get("inherited_feedback", []),
                "prior_choice": s.get("inherited_choice"), "current_take": parent["take"], "last_error": s.get("last_error", ""),
                "attempts": [{k: c[k] for k in ("take", "label", "reason", "changes")} for c in s["candidates"]]}

    def preview_apply(self, sid, cid, paths):
        s = self.get(sid)
        if s.get("scope", "instrument") == "instrument":
            return super().preview_apply(sid, cid, paths)
        if s["scope"] == "snippet":
            raise ValueError("Snippet comparisons are listening only. Use riff or arrangement mode to edit a score")
        if paths != [s["path"]]:
            raise ValueError("Musical edits apply only to the original score")
        c = next((c for c in s["candidates"] if c["id"] == cid), None)
        if c is None:
            raise ValueError("Choose a saved candidate")
        before = safe_path(self.root, s["path"]).read_text(encoding="utf-8-sig")
        if digest(before) != s["base_hash"]:
            raise ValueError("The source score changed since this comparison; start a new comparison")
        return [{"path": s["path"], "before": before, "hash": digest(before), "text": c["source"],
                 "targets": [(s["part"], None)]}]
