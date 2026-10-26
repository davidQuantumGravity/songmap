"""Saved-score instrument reach and durable, scoped instrument listening experiments.

Candidates change one resolved voice. Written notes, tuning, form and expression are fixed.
No candidate is applied to a score until an explicit apply operation succeeds.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import threading
import time
import uuid
import wave

from .project import SONG_EXTS, parse_text

LOCK = threading.RLock()
STUDIES = {"sfz_revisited", "textbook_refresh", "sfz_library", "rhythm_palette", "skill_evals", "skill_examples"}


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def safe_path(root, rel):
    root = Path(root).resolve()
    p = (root / rel).resolve()
    if not p.is_relative_to(root) or p.suffix.lower() not in SONG_EXTS:
        raise ValueError("Select a score inside the SongMap repository")
    return p


def inventory(root):
    """Count expanded, played voices, including defaults and used kit fallbacks.

    Counts are saved source files, not claims about distinct musical compositions.
    Study/revisit collections are identified so callers can exclude duplicated material.
    """
    from ..arrange.expand import expand
    root = Path(root)
    rows, errors, sources = [], [], []
    for folder in ("songs", "textbook/audio", "examples"):
        base = root / folder
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if p.suffix.lower() not in SONG_EXTS or not p.is_file():
                continue
            if p.name.endswith((".view.yaml", ".view.yml")):
                continue
            if any(s in {"renders", "archives", ".git", "node_modules"} for s in p.relative_to(base).parts):
                continue
            rel = p.relative_to(root).as_posix()
            kind = "textbook" if folder == "textbook/audio" else "example" if folder == "examples" else "song"
            if folder == "songs" and any(s in STUDIES for s in p.relative_to(base).parts[:-1]):
                kind = "study"
            try:
                arr = expand(parse_text(p.read_text(encoding="utf-8-sig"), str(p)))
                grouped = {}
                for part, events in arr.parts.items():
                    for e in events:
                        v = arr.ensemble.voice(part, e.piece)
                        key = (part, e.piece, v.use)
                        if key not in grouped:
                            grouped[key] = dict(path=rel, title=arr.song.title, kind=kind, part=part, piece=e.piece,
                                                use=v.use, notes=0, sections=[], first_seconds=round(arr.timeline.beat_to_sec(e.beat), 3))
                        row = grouped[key]
                        row["notes"] += len(e.pitches) or 1
                        if e.section not in row["sections"]:
                            row["sections"].append(e.section)
                rows.extend(grouped.values())
                sources.append(dict(path=rel, title=arr.song.title, kind=kind, seconds=round(arr.timeline.seconds, 2),
                                    instruments=sorted({r["use"] for r in grouped.values()})))
            except Exception as e:
                errors.append({"path": rel, "message": str(e)})
    voices = {}
    for row in rows:
        v = voices.setdefault(row["use"], {"use": row["use"], "notes": 0, "occurrences": []})
        v["notes"] += row["notes"]
        v["occurrences"].append(row)
    for v in voices.values():
        v["source_count"] = len({o["path"] for o in v["occurrences"]})
    return {"sources": sources, "occurrences": rows, "instruments": sorted(voices.values(), key=lambda v: (-v["source_count"], v["use"])),
            "errors": errors, "scanned_at": time.time(), "basis": "Saved score files; archives and renders excluded"}


def current_voice(source, path, part, piece):
    from ..arrange.ensemble import Ensemble
    from .rack import voice_info
    return voice_info(Ensemble(parse_text(source, path)), part, piece)


def voice_name(use):
    """A catalog/source-derived name, never the model's proposed nickname."""
    if use.startswith("sampler/"):
        from ..instruments.sampler.library import manifest
        item = manifest()["voices"].get(use.partition("/")[2], {})
        return item.get("title") or use.partition("/")[2].replace("_", " ").capitalize()
    return (use.partition("/")[2] or use).replace("_", " ").capitalize()


def edit_voice(source, path, part, piece, change):
    """Validate a bounded voice edit, retaining the source format and musical tree."""
    from ..arrange.ensemble import Ensemble
    from ..instruments import make
    from ..parse.fmt import to_yaml
    from .rack import set_voice
    if set(change) - {"use", "params"}:
        raise ValueError("An instrument candidate contains only use and params")
    song = parse_text(source, path)
    ens = Ensemble(song)
    v = ens.voice(part, piece)
    use = change.get("use") or v.use
    params = change.get("params") or {}
    if not isinstance(use, str) or not isinstance(params, dict):
        raise ValueError("Invalid instrument edit")
    merged = {**(v.params if use == v.use else {}), **params}
    if use.startswith("patch/"):
        from ..instruments.patch import build
        inst = build(use.partition("/")[2], ens.patch_spec(use.partition("/")[2]), **merged)
    else:
        inst = make(use, **merged)
    spec = {q.name: q for q in inst.PARAMS}
    for k, value in params.items():
        if k not in spec or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"Invalid numeric parameter: {k}")
        if not spec[k].lo <= value <= spec[k].hi:
            raise ValueError(f"{k} must be between {spec[k].lo} and {spec[k].hi}")
    if path.lower().endswith((".sm", ".sml")) and (piece is None or part == "drums"):
        result = set_voice(source, part, piece=piece, use=use, params=params, current_use=v.use, clear=use != v.use)
    else:
        entry = {"use": use, **merged, "gain_db": v.gain_db, "pan": v.pan}
        if piece:
            kit = song.instruments.setdefault(part, {"kit": {}})
            if "kit" not in kit:
                kit = {"kit": kit}
                song.instruments[part] = kit
            kit["kit"][piece] = entry
        else:
            song.instruments[part] = entry
        if path.lower().endswith((".sm", ".sml")):
            from ..parse.fmt import to_sm
            result = to_sm(song)
        else:
            result = to_yaml(song)
    # Resolve again to catch a malformed resulting directive before persisting it.
    Ensemble(parse_text(result, path)).instrument(part, piece)
    return result


class Lab:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.home = self.root / ".songmap" / "instrument-lab"
        self.home.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS assessments (voice TEXT PRIMARY KEY, data TEXT NOT NULL)")

    def db(self):
        return sqlite3.connect(self.home / "lab.sqlite3", timeout=30)

    def get(self, sid):
        with self.db() as db:
            row = db.execute("SELECT data FROM sessions WHERE id=?", (sid,)).fetchone()
        if not row:
            raise ValueError("No such comparison session")
        return json.loads(row[0])

    def put(self, s):
        s["updated"] = time.time()
        with self.db() as db:
            db.execute("INSERT OR REPLACE INTO sessions VALUES (?,?)", (s["id"], json.dumps(s, allow_nan=False)))
        return s

    def present(self, sid, focus=True):
        """Stable take identities and verified audition facts for old and new sessions."""
        from ..arrange.expand import expand
        from ..render import held_beats
        if focus:
            self.prepare_focus(sid)
        s = self.get(sid)
        s["scope"] = s.get("scope", "instrument")
        takes = {}
        for i, c in enumerate(s["candidates"], 1):
            voice = current_voice(c["source"], s["path"], s["part"], s["piece"])
            c.update(take=i, verified_use=voice["use"], display_name=voice_name(voice["use"]))
            takes[c["id"]] = c
            parent = takes.get(c.get("parent"))
            c["changes"] = []
            if parent:
                before = current_voice(parent["source"], s["path"], s["part"], s["piece"])
                if before["use"] != voice["use"]:
                    c["changes"].append({"field":"Voice", "before":voice_name(before["use"]), "after":c["display_name"]})
                else:
                    c["changes"] = [{"field":k, "before":before["values"].get(k), "after":v}
                                    for k,v in voice["values"].items() if before["values"].get(k) != v]
        arr = expand(parse_text(s["base_source"], s["path"]))
        accompaniment = {}
        for part, evs in arr.parts.items():
            if part == s["part"]:
                continue
            for e in evs:
                if arr.timeline.beat_to_sec(e.beat) >= s["start"] + s["seconds"] or arr.timeline.beat_to_sec(e.beat + held_beats(e)) + 2 <= s["start"]:
                    continue
                v = arr.ensemble.voice(part, e.piece)
                accompaniment[(part,e.piece,v.use)] = {"part":part,"piece":e.piece,"use":v.use,"name":voice_name(v.use)}
        s["audition"] = {"target":{"part":s["part"],"piece":s["piece"],"original_use":s["use"]},
                         "accompaniment":list(accompaniment.values()), "solo_label":f"{s['part']} only" + (" (whole kit)" if s["piece"] else "")}
        for f in s["feedback"]:
            chosen = f["pair"][0 if f["choice"] == "a" else 1] if f["choice"] in {"a","b"} else None
            c = takes.get(chosen)
            f["selected_take"] = c["take"] if c else None
            f["selected_voice"] = c["display_name"] if c else None
        return s

    def prepare_focus(self, sid):
        """Add levelled solo previews without replacing any original listening evidence."""
        import numpy as np
        from ..export.qa import lufs
        from .project import wav_bytes
        with LOCK:
            s = self.get(sid)
            changed = False
            for c in s["candidates"]:
                if c["audio"].get("focus") and self.audio_path(sid,c["id"],"focus").exists():
                    continue
                original = self.audio_path(sid,c["id"],"solo")
                if not original.exists():
                    continue
                with wave.open(str(original)) as w:
                    clip = np.frombuffer(w.readframes(w.getnframes()),dtype="<i2").astype(float).reshape(-1,w.getnchannels())/32768
                level = float(lufs(clip)); peak = float(np.max(np.abs(clip))) if clip.size else 0
                gain = min(10 ** ((-20-level)/20), .94/peak) if peak > 0 and math.isfinite(level) and level > -80 else 1
                target = self.audio_path(sid,c["id"],"focus")
                tmp = target.with_suffix(".tmp"); tmp.write_bytes(wav_bytes(clip*gain)); os.replace(tmp,target)
                c["audio"]["focus"] = f"/api/lab/audio/{sid}/{c['id']}/focus"
                c["loudness"]["focus"] = level + 20*math.log10(gain) if math.isfinite(level) else -99
                c["preview_gain_db"] = round(20*math.log10(gain),2)
                changed = True
            if changed:
                self.put(s)

    def listing(self):
        with self.db() as db:
            sessions = [json.loads(r[0]) for r in db.execute("SELECT data FROM sessions")]
            assessments = {r[0]: json.loads(r[1]) for r in db.execute("SELECT voice,data FROM assessments")}
        return {"sessions": sorted([{**{k: s[k] for k in ("id", "path", "part", "piece", "use", "brief", "status", "updated")},
                                     "scope": s.get("scope", "instrument")} for s in sessions],
                                   key=lambda s: -s["updated"]), "assessments": assessments}

    def assess(self, use, need, note):
        if isinstance(need, bool) or need not in (0, 1, 2, 3) or len(note) > 4000:
            raise ValueError("Improvement need is 0 to 3; notes are at most 4000 characters")
        data = {"need": need, "note": note, "updated": time.time()}
        with self.db() as db:
            db.execute("INSERT OR REPLACE INTO assessments VALUES (?,?)", (use, json.dumps(data)))
        return data

    def create(self, path, source, part, piece, start, seconds, brief):
        from ..arrange.expand import expand
        safe_path(self.root, path)
        arr = expand(parse_text(source, str(self.root / path)))
        if part not in arr.parts or not any(e.piece == piece for e in arr.parts[part]):
            raise ValueError("Choose a part or kit piece that plays in this score")
        if not (math.isfinite(start) and math.isfinite(seconds) and 0 <= start < arr.timeline.music_seconds and 1 <= seconds <= 30):
            raise ValueError("Choose a start within the song and an excerpt of 1 to 30 seconds")
        voice = current_voice(source, path, part, piece)
        cid, sid = uuid.uuid4().hex, uuid.uuid4().hex
        c = {"id": cid, "source": source, "label": "Original", "origin": "source", "reason": "Saved baseline; notes and expression fixed",
             "change": {"use": voice["use"], "params": dict(voice["params"])}, "parent": None, "audio": {}, "loudness": {}}
        s = {"id": sid, "path": path, "part": part, "piece": piece, "use": voice["use"], "brief": brief[:4000],
             "start": start, "seconds": min(seconds, arr.timeline.seconds - start), "base_source": source,
             "base_hash": digest(source), "candidates": [c], "incumbent": cid, "pair": [cid], "feedback": [],
             "status": "ready", "error": "", "applied": [], "created": time.time(), "updated": time.time()}
        return self.put(s)

    def add_candidate(self, sid, change, label, origin, reason=""):
        with LOCK:
            s = self.get(sid)
            if len(s["candidates"]) >= 24:
                raise ValueError("This session has reached 24 candidates; start a new session")
            parent = next(c for c in s["candidates"] if c["id"] == s["incumbent"])
            source = edit_voice(parent["source"], s["path"], s["part"], s["piece"], change)
            if digest(source) == digest(parent["source"]):
                raise ValueError("The challenger makes no instrument change")
            voice = current_voice(source, s["path"], s["part"], s["piece"])
            before_voice = current_voice(parent["source"], s["path"], s["part"], s["piece"])
            if voice["use"] == before_voice["use"] and voice["values"] == before_voice["values"]:
                raise ValueError("The challenger resolves to the same sound parameters")
            same_backend = voice["instrument"] == before_voice["instrument"]
            comparable = voice["use"] == before_voice["use"] or (same_backend and voice["instrument"] not in {"sampler", "patch"})
            if comparable:
                from ..arrange.expand import expand
                from ..render import held_beats
                arr = expand(parse_text(parent["source"], s["path"]))
                changed = {k for k, v in voice["values"].items() if before_voice["values"].get(k) != v}
                evs = [e for e in arr.parts[s["part"]] if e.piece == s["piece"]
                       and arr.timeline.beat_to_sec(e.beat) < s["start"] + s["seconds"]
                       and arr.timeline.beat_to_sec(e.beat + held_beats(e)) + 2 > s["start"]]
                if evs and not any(changed - set(dict(e.patch)) - set(e.params) for e in evs):
                    raise ValueError("Style or note overrides mask every changed parameter in this excerpt. Choose an unmasked parameter or another instrument.")
            c = {"id": uuid.uuid4().hex, "source": source, "label": label[:120], "origin": origin, "reason": reason[:4000],
                 "change": {"use": voice["use"], "params": voice["params"]}, "parent": parent["id"], "audio": {}, "loudness": {}}
            s["candidates"].append(c)
            s["previous_pair"] = s["pair"]
            s["pair"] = [parent["id"], c["id"]]
            return self.put(s)

    def feedback(self, sid, vote):
        with LOCK:
            s = self.get(sid)
            if any(f["event_id"] == vote["event_id"] for f in s["feedback"]):
                return s
            if vote["pair"] != s["pair"] or (len(s["pair"]) != 2 and vote["choice"] != "comment"):
                raise ValueError("The comparison changed; reload before voting")
            if vote["choice"] not in {"a", "b", "tie", "neither", "comment"}:
                raise ValueError("Choose A, B, tie, neither, or comment")
            if len(vote.get("text", "")) > 4000:
                raise ValueError("Feedback must be at most 4000 characters")
            s["feedback"].append({**vote, "created": time.time(), "provenance": "human",
                                  "scope": "this passage and instrument" if s.get("scope", "instrument") == "instrument" else s["scope"]})
            if vote["choice"] in {"a", "b"}:
                s["incumbent"] = s["pair"][vote["choice"] == "b"]
            return self.put(s)

    def context(self, sid):
        from ..arrange.expand import expand
        s = self.present(sid, focus=False)
        parent = next(c for c in s["candidates"] if c["id"] == s["incumbent"])
        arr = expand(parse_text(parent["source"], s["path"]))
        overrides = {json.dumps({"style": dict(e.patch), "note": e.params}, sort_keys=True)
                     for e in arr.parts[s["part"]] if e.piece == s["piece"] and (e.patch or e.params)}
        return {"brief": s["brief"], "path": s["path"], "part": s["part"], "piece": s["piece"],
                "source": parent["source"], "voice": current_voice(parent["source"], s["path"], s["part"], s["piece"]),
                "start": s["start"], "seconds": s["seconds"], "feedback": s["feedback"],
                "audition": s["audition"], "current_take": parent["take"], "last_error":s.get("last_error", ""),
                "style_and_note_overrides": [json.loads(o) for o in sorted(overrides)],
                "attempts": [{k: c[k] for k in ("id", "take", "verified_use", "display_name", "change", "reason")} for c in s["candidates"]]}

    def audio_path(self, sid, cid, mode):
        s = self.get(sid)
        if mode not in {"solo", "context", "focus"} or not any(c["id"] == cid for c in s["candidates"]):
            raise ValueError("No such candidate audio")
        return self.home / sid / f"{cid}-{mode}.wav"

    def render_pair(self, sid):
        import numpy as np
        from ..export.qa import lufs
        from .project import wav_bytes
        from ..render import render
        s = self.get(sid)
        for cid in s["pair"]:
            c = next(c for c in s["candidates"] if c["id"] == cid)
            if c["audio"] and all(self.audio_path(sid, cid, m).exists() for m in ("solo", "context")):
                continue
            song = parse_text(c["source"], str(self.root / c.get("path", s["path"])))
            start = c.get("start", s["start"])
            result = render(song, preview_end=None if song.binaural else start + s["seconds"] + .05)
            a, b = int(start * 48000), int((start + s["seconds"]) * 48000)
            assets, levels = {}, {}
            for mode, track in (("context", result.audio), ("solo", result.stems.get(s["part"], result.audio))):
                clip = np.array(track[a:b], copy=True)
                level = float(lufs(clip))
                levels[mode] = level if math.isfinite(level) else -99
                # Peak-safe source assets; audition gains are applied independently in the player.
                peak = float(np.max(np.abs(clip))) if clip.size else 0
                if peak > .97:
                    scale = .97 / peak
                    clip *= scale
                    levels[mode] += 20 * math.log10(scale)
                p = self.audio_path(sid, cid, mode)
                p.parent.mkdir(parents=True, exist_ok=True)
                tmp = p.with_suffix(".tmp")
                tmp.write_bytes(wav_bytes(clip))
                os.replace(tmp, p)
                assets[mode] = f"/api/lab/audio/{sid}/{cid}/{mode}"
            with LOCK:
                latest = self.get(sid)
                target = next(c for c in latest["candidates"] if c["id"] == cid)
                target.update(audio=assets, loudness=levels, render={"engine_digest": result.stats["digest"], "samples": result.sources,
                                                                   "peak": peak, "created": time.time()})
                self.put(latest)
        return self.get(sid)

    def preview_apply(self, sid, cid, paths):
        s = self.get(sid)
        c = next((c for c in s["candidates"] if c["id"] == cid), None)
        if not c or not paths or len(paths) > 50:
            raise ValueError("Choose a candidate and 1 to 50 target scores")
        out = []
        for rel in dict.fromkeys(paths):
            p = safe_path(self.root, rel)
            text = p.read_text(encoding="utf-8-sig")
            # The source experiment must still refer to the exact saved base.
            if rel == s["path"] and digest(text) != s["base_hash"]:
                raise ValueError(f"{rel} changed since this experiment; start a new comparison")
            from ..arrange.expand import expand
            arr = expand(parse_text(text, str(p)))
            matches = []
            for part, events in arr.parts.items():
                for piece in {e.piece for e in events}:
                    if arr.ensemble.voice(part, piece).use == s["use"]:
                        matches.append((part, piece))
            if rel == s["path"]:
                matches = [(s["part"], s["piece"])]
            if not matches:
                raise ValueError(f"{rel} no longer uses {s['use']}")
            new = text
            change = c["change"]
            baseline = s["candidates"][0]["change"]
            if change["use"] == baseline["use"]:
                change = {"use": change["use"], "params": {k: v for k, v in change["params"].items()
                                                            if baseline["params"].get(k) != v}}
            for part, piece in matches:
                new = edit_voice(new, rel, part, piece, change)
            out.append({"path": rel, "before": text, "hash": digest(text), "text": new, "targets": matches})
        return out

    def apply(self, sid, cid, paths, expected=None):
        from .project import Project
        with LOCK:
            plan = self.preview_apply(sid, cid, paths)
            if expected is not None and expected != {p["path"]: p["hash"] for p in plan}:
                raise ValueError("A target changed since the preview; review the changes again")
            s = self.get(sid)
            receipt = {"id": uuid.uuid4().hex, "candidate": cid, "created": time.time(), "files": []}
            backup = self.home / sid / "applied" / receipt["id"]
            backup.mkdir(parents=True)
            # Durable preimages support restoration even after subsequent score saves replace .bak.
            for i, item in enumerate(plan):
                (backup / f"{i}.json").write_text(json.dumps(item), encoding="utf-8")
            try:
                for item in plan:
                    p = safe_path(self.root, item["path"])
                    if digest(p.read_text(encoding="utf-8-sig")) != item["hash"]:
                        raise ValueError(f"{item['path']} changed during apply; review targets")
                    Project(str(p)).save(item["text"])
                    receipt["files"].append({"path": item["path"], "before": item["hash"], "after": digest(item["text"])})
            except Exception:
                for item in plan[:len(receipt["files"])]:
                    p = safe_path(self.root, item["path"])
                    if digest(p.read_text(encoding="utf-8-sig")) == digest(item["text"]):
                        Project(str(p)).save(item["before"])
                raise
            (backup / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
            s["applied"].append(receipt)
            self.put(s)
            return receipt

    def restore(self, sid, receipt_id):
        from .project import Project
        with LOCK:
            s = self.get(sid)
            receipt = next((r for r in s["applied"] if r["id"] == receipt_id), None)
            if not receipt or receipt.get("restored"):
                raise ValueError("No active apply receipt to undo")
            folder = self.home / sid / "applied" / receipt_id
            saved = [json.loads((folder / f"{i}.json").read_text(encoding="utf-8")) for i in range(len(receipt["files"]))]
            for item, f in zip(saved, receipt["files"]):
                p = safe_path(self.root, item["path"])
                if digest(p.read_text(encoding="utf-8-sig")) != f["after"]:
                    raise ValueError(f"{item['path']} changed after apply; undo would overwrite newer edits")
            for item in saved:
                Project(str(safe_path(self.root, item["path"]))).save(item["before"])
            receipt["restored"] = time.time()
            self.put(s)
            return receipt
