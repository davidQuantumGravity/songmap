"""A song open in the Studio: its source text, the parsed tree, the arrangement and the last render.

Everything the GUI shows is derived from the text, so the text is the state: typing in the code pane,
turning a knob and dragging a fader all end as new text (docs/GUI.md §3).
"""
from __future__ import annotations

import hashlib
import io
import os
import threading
import time
import wave
from dataclasses import dataclass, field

import numpy as np

from ..parse.errors import NotationError, SongError

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SONG_EXTS = (".sm", ".sml", ".yaml", ".yml")


def parse_text(text: str, path: str):
    """Source text -> Song, in the format the path's extension names."""
    from ..parse import lang, yaml_form
    if os.path.splitext(path)[1].lower() in lang.EXTS:
        return lang.loads(text, path)
    return yaml_form.from_raw(yaml_form.load_raw_text(text, path), file=path)


def diagnostic(e: Exception, path: str) -> dict:
    line = getattr(e, "line", None)
    msg = getattr(e, "message", None) or str(e)
    return {"severity": "error", "line": line, "section": getattr(e, "section", None), "message": msg,
            "suggestion": getattr(e, "suggestion", None), "text": str(e)}


def wav_bytes(audio: np.ndarray, sr: int = 48000) -> bytes:
    """Stereo float audio -> 16-bit PCM WAV bytes (for the browser)."""
    x = np.clip(np.asarray(audio, float), -1, 1)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    q = (x * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(q.tobytes())
    return buf.getvalue()


class NoteCache(dict):
    """The Studio's note cache, shared by every render: after a render it keeps only the notes that render
    used, so it holds at most one song's notes, and an edit re-synthesizes only the notes it changed."""

    def __init__(self):
        super().__init__()
        self.used: set = set()

    def get(self, key, default=None):
        self.used.add(key)
        return super().get(key, default)

    def prune(self) -> None:
        for k in [k for k in self if k not in self.used]:
            del self[k]
        self.used = set()


NOTES = NoteCache()
NOTES_LOCK = threading.Lock()


def _mmss(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:04.1f}"


@dataclass
class Rendered:
    key: str
    result: object                       # render.RenderResult (its stems are at `mix`)
    wav: bytes
    seconds: float
    elapsed: float
    mix: dict = field(default_factory=dict)          # the effective mix the stems were rendered with
    stripped: str = ""                               # the text without its mix lines
    remixed: bool = False                            # True: made from a full render's stems
    audio: object = None                             # the mastered audio (a remix's differs from result.audio)
    mute: tuple = ()
    solo: tuple = ()
    qa: dict | None = None                           # Project.measure, cached
    stem_lufs: dict | None = None                    # a full render's stem loudness (remixes adjust it)


@dataclass
class Project:
    path: str                            # absolute
    text: str = ""
    _rendered: Rendered | None = None
    _full: Rendered | None = None        # the last full render (its stems feed remixes)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @classmethod
    def open(cls, path: str) -> "Project":
        path = os.path.abspath(path)
        with open(path, encoding="utf-8") as f:
            return cls(path, f.read())

    @property
    def rel(self) -> str:
        return os.path.relpath(self.path, ROOT).replace(os.sep, "/")

    def key(self, text: str | None = None, mute=(), solo=()) -> str:
        t = (text if text is not None else self.text) + "|" + ",".join(sorted(mute)) + "|" + ",".join(sorted(solo))
        return hashlib.sha1(t.encode("utf-8")).hexdigest()

    # ---------------------------------------------------------------- check
    def check(self, text: str | None = None) -> dict:
        """Parse + expand (no audio). Returns diagnostics and, when it parses, the arrangement summary."""
        text = self.text if text is None else text
        t0 = time.time()
        try:
            from ..arrange.expand import expand
            song = parse_text(text, self.path)
            arr = expand(song)
        except (SongError, NotationError) as e:
            return {"ok": False, "diagnostics": [diagnostic(e, self.path)], "summary": None,
                    "ms": round((time.time() - t0) * 1000)}
        except Exception as e:                                       # noqa: BLE001  (an engine bug: report it)
            return {"ok": False, "diagnostics": [{"severity": "error", "line": None, "message":
                    f"internal error: {type(e).__name__}: {e}", "suggestion": "report this", "text": str(e)}],
                    "summary": None, "ms": round((time.time() - t0) * 1000)}
        warnings = [{"severity": "warning", "line": None, "message": w, "suggestion": None, "text": w}
                    for w in list(song.warnings) + list(arr.warnings)]
        return {"ok": True, "diagnostics": warnings, "summary": summarize(arr),
                "ms": round((time.time() - t0) * 1000)}

    # ---------------------------------------------------------------- save
    def save(self, text: str) -> None:
        tmp = self.path + ".tmp"
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                old = f.read()
            if old != text:
                with open(self.path + ".bak", "w", encoding="utf-8", newline="\n") as f:
                    f.write(old)
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, self.path)
        self.text = text

    # ---------------------------------------------------------------- render
    def render(self, text: str | None = None, mute=(), solo=()) -> Rendered:
        """The song's audio. A change only to faders, pans and sends (or to mute/solo) since the last full
        render is a remix of its stems; anything else renders in full."""
        from .mixer import effective_mix, remix, remixable, strip_mix
        text = self.text if text is None else text
        k = self.key(text, mute, solo)
        with self._lock:
            if self._rendered and self._rendered.key == k:
                return self._rendered
            t0 = time.time()
            song = parse_text(text, self.path)
            mix = effective_mix(song)
            stripped = strip_mix(text)
            full = self._full
            if (full and full.stripped == stripped and self.path.endswith((".sm", ".sml"))
                    and remixable(full.mix, mix, full.result.stems)):
                audio = remix(full.result, full.mix, mix, mute, solo)
                rd = Rendered(k, full.result, wav_bytes(audio), len(audio) / 48000, time.time() - t0,
                              mix, stripped, True, audio, tuple(mute), tuple(solo))
            else:
                from ..render import render
                with NOTES_LOCK:                 # one render at a time uses (and prunes) the shared cache
                    NOTES.used = set()
                    r = render(song, note_cache=NOTES)
                    NOTES.prune()
                audio = r.audio
                if mute or solo:
                    audio = remix(r, mix, mix, mute, solo)
                rd = Rendered(k, r, wav_bytes(audio), len(audio) / 48000, time.time() - t0, mix, stripped, False, audio,
                              tuple(mute), tuple(solo))
                self._full = Rendered(self.key(text), r, b"", rd.seconds, rd.elapsed, mix, stripped, False, r.audio)
            self._rendered = rd
            return rd

    def measure(self, rd: Rendered) -> dict:
        """The QA the Studio shows: loudness, true peak, clipping, per-section loudness and per-stem loudness.
        Stems are measured once per full render; after a remix they move with their faders."""
        if rd.qa is not None:
            return rd.qa
        from ..export.qa import k_weight, lufs, true_peak_db
        x = rd.audio
        kw = k_weight(x)
        sections = []
        for name, t0, t1 in rd.result.section_spans():
            seg = kw[int(t0 * 48000):int(t1 * 48000)]
            sections.append({"name": name, "loudness": round(float(10 * np.log10(np.mean(seg ** 2) * 2 + 1e-12) - 0.691), 1)
                             if len(seg) else -99.0})
        full = self._full
        if full is not None and full.result is rd.result and full.stem_lufs is None:
            full.stem_lufs = {k: round(lufs(v), 1) for k, v in rd.result.stems.items()}
        base = full.stem_lufs if full is not None and full.result is rd.result else None
        if base is None:
            base = {k: round(lufs(v), 1) for k, v in rd.result.stems.items()}
        stems = {}
        for k, v in base.items():
            a, b = (full.mix if full else rd.mix).get(k, {}), rd.mix.get(k, {})
            heard = k not in rd.mute and (not rd.solo or k in rd.solo or k.startswith("return_"))
            stems[k] = round(v + float(b.get("gain_db", 0)) - float(a.get("gain_db", 0)), 1) if heard else -70.0
        rd.qa = {"lufs": round(lufs(x), 2), "true_peak_db": round(true_peak_db(x), 2),
                 "clipped": int(np.sum(np.abs(x) >= 0.999)), "sections": sections, "stems": stems}
        return rd.qa

    def last(self) -> Rendered | None:
        return self._rendered

    # ---------------------------------------------------------------- export
    def out_dir(self) -> str:
        stem = os.path.basename(self.path).split(".")[0]
        return os.path.join(os.path.dirname(self.path), "renders", stem)

    def export(self, formats: list[str], text: str | None = None, view: dict | None = None) -> dict:
        """Write the requested outputs next to the song (renders/<name>/). Returns {format: path}."""
        from ..render import write_outputs
        rd = self.render(text)
        r = rd.result
        if rd.remixed:                       # exports are full renders: the stems and cues must match the audio
            self._full = None
            rd = self.render(text)
            r = rd.result
        out = self.out_dir()
        os.makedirs(out, exist_ok=True)
        paths: dict[str, str] = {}
        if {"wav", "mp3", "stems", "cues", "qa"} & set(formats):
            p = write_outputs(r, out, stems="stems" in formats, mp3="mp3" in formats)
            paths.update({"wav": p["song"], "cues": p["cues"], "qa": p["qa"]})
            if "mp3" in p:
                paths["mp3"] = p["mp3"]
            if "stems" in p:
                paths["stems"] = p["stems"]
        song = r.arrangement.song
        v = view or {}
        size = tuple(v.get("size", (1280, 720)))
        if "png" in formats:
            from ..visual.video import write_poster
            paths["png"] = write_poster(song, os.path.join(out, "poster.png"), t=v.get("t"), size=size,
                                        theme=v.get("theme", "light"), page_seconds=v.get("page_seconds", 6.0),
                                        parts=v.get("parts"))
        if "qa_png" in formats:
            from ..export import qa as qa_mod
            from ..export.qa_plot import write_png
            tl = r.arrangement.timeline
            spans = r.section_spans()
            loud = {s["name"]: s["loudness"] for s in qa_mod.qa(r.audio, spans)["sections"]}
            evs = [(e.type, tl.beat_to_sec(e.beat)) for e in r.arrangement.events]
            paths["qa_png"] = write_png(os.path.join(out, "qa.png"), r.audio, spans, evs, loud, song.title)
        if "mp4" in formats:
            from ..export.wav import write_wav24
            from ..visual.video import write_video
            wav = paths.get("wav") or os.path.join(out, "song.wav")
            if not os.path.exists(wav):
                write_wav24(wav, r.audio)
            paths["mp4"] = write_video(song, os.path.join(out, "song.mp4"), size=size, theme=v.get("theme", "light"),
                                       page_seconds=v.get("page_seconds", 6.0), parts=v.get("parts"), audio_wav=wav)
        return {k: os.path.relpath(p, ROOT).replace(os.sep, "/") for k, p in paths.items()}


def summarize(arr) -> dict:
    """What the arrangement and transport panes need: timing, sections, parts with their notes, events, cues."""
    from ..render import held_beats
    from .rack import voices
    song, tl = arr.song, arr.timeline
    sections = [{"name": s.name, "index": s.index, "bar": s.start_bar, "bars": s.bars,
                 "start": round(tl.beat_to_sec(s.start), 4), "end": round(tl.beat_to_sec(s.end), 4),
                 "line": song.sections[s.index].line if s.index < len(song.sections) else None}
                for s in tl.sections]
    parts = []
    for name, evs in arr.parts.items():
        notes = []
        for e in evs:
            t0 = tl.beat_to_sec(e.beat)
            t1 = tl.beat_to_sec(e.beat + max(held_beats(e), 1e-3))
            for p in (e.pitches or (None,)):
                notes.append([round(t0, 4), round(t1 - t0, 4), None if p is None else round(float(p), 4),
                              round(float(e.vel), 3), e.piece or ""])
        kit = arr.ensemble.is_kit(name)
        voice = None if kit else arr.ensemble.voice(name, None).use
        m = arr.ensemble.mix.get(name, {})
        parts.append({"name": name, "kit": kit, "instrument": voice, "count": len(evs), "notes": notes,
                      "mix": {"gain_db": float(m.get("gain_db", 0)), "pan": float(m.get("pan", 0) or 0),
                              "send": {k: float(v) for k, v in (m.get("send") or {}).items()},
                              "sidechain": bool(m.get("sidechain")), "inserts": list(m.get("inserts") or [])}})
    events = [{"type": e.type, "at": e.at, "time": round(tl.beat_to_sec(e.beat), 4),
               "start": round(tl.beat_to_sec(e.start), 4), "section": e.section} for e in arr.events]
    chords: list[list] = []                              # [start, end, symbol], repeats of one chord merged
    for sp in arr.harmony.spans:
        if sp.chord is None:
            continue
        a, b = round(tl.beat_to_sec(sp.start), 4), round(tl.beat_to_sec(sp.end), 4)
        if chords and not sp.onset and chords[-1][2] == sp.chord.symbol and abs(chords[-1][1] - a) < 1e-6:
            chords[-1][1] = b
        else:
            chords.append([a, b, sp.chord.symbol])
    return {
        "title": song.title, "tempo": song.tempo, "meter": f"{song.meter[0]}/{song.meter[1]}", "key": song.key,
        "tuning": getattr(song, "tuning", "12edo"), "mood": song.mood, "fps": song.fps,
        "bars": tl.total_bars, "seconds": round(tl.seconds, 4), "music_seconds": round(tl.music_seconds, 4),
        "frames": tl.frames, "length": _mmss(tl.seconds), "digest": arr.digest()[:16],
        "sections": sections, "parts": parts, "events": events, "chords": chords,
        "returns": sorted(arr.ensemble.returns), "voices": voices(arr.ensemble, arr.parts),
        "master_inserts": list((arr.ensemble.mix.get("master") or {}).get("inserts") or []),
        "bar_times": [round(tl.beat_to_sec(b * tl.bpb), 4) for b in range(int(tl.total_bars) + 1)],
    }


def list_files() -> dict:
    """Songs (and other editable files) in the repo, for the file browser."""
    groups: dict[str, list] = {"songs": [], "examples": [], "textbook": []}
    for top, key in (("songs", "songs"), ("examples", "examples"), (os.path.join("textbook", "audio"), "textbook")):
        base = os.path.join(ROOT, top)
        for dp, dns, fns in os.walk(base):
            dns[:] = sorted(d for d in dns if d not in ("renders", "__pycache__", "node_modules") and not d.startswith("."))
            for fn in sorted(fns):
                if fn.endswith(SONG_EXTS) and not fn.endswith(".view.yaml"):
                    groups[key].append(os.path.relpath(os.path.join(dp, fn), ROOT).replace(os.sep, "/"))
    return groups
