"""Versioned harmony reference, materialized in SQLite; never edits a score.

Descriptions of concrete pitches/motions are computed with the same parser/grid as
the renderer. Source references support families, not fictitious popularity ranks.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import threading
from pathlib import Path

import yaml

from ..theory.harmony import Chord
from ..theory.keys import parse_key
from ..theory.tuning import DEFAULT, EDO36, OCTAVE, centered, pc_semitones

SEED = Path(__file__).with_name("data") / "harmony_library.yaml"
KINDS = ("chords", "transitions", "progressions")
TONICS = ("C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")


def pitch_name(pitch: float, octave: bool = False) -> str:
    # Practical enharmonic display, including repeated sixth-step accidentals.
    nearest = round(pitch)
    steps = round((pitch - nearest) / EDO36.step)
    prefix = "^" * steps if steps > 0 else "v" * -steps
    name = TONICS[DEFAULT.pc(nearest)]
    return prefix + name + (str(math.floor(nearest / OCTAVE) - 1) if octave else "")


def transpose(symbol: str, tonic: str) -> str:
    if tonic not in TONICS:
        raise ValueError("Choose one of the twelve tonic keys")
    shift = parse_key(tonic)[0]
    if shift == 0:
        return symbol
    # Preserve the engine's exact suffix/alterations; transpose slash bass too.
    head, slash, bass = symbol.partition("/")
    match = re.match(r"[\^v]*[A-G][#b]?", head)
    assert match
    chord = Chord.parse(symbol)
    out = pitch_name(pc_semitones(chord.root + shift)) + head[match.end():]
    if slash:
        out += "/" + pitch_name(pc_semitones(chord.bass + shift))
    return out


def _quality(chord: Chord) -> tuple[int, ...]:
    return tuple(round(i / EDO36.step) for i in chord.intervals)


FAMILY_SOURCES = {
    "Pop and folk": ["pop", "schemas"], "Borrowed and rock": ["plagal", "modal"],
    "Modal vamps": ["modal"], "Minor-key songs": ["minor", "cycle"],
    "Jazz and soul": ["jazz"], "Blues forms": ["blues", "jazz"],
    "Cadences and sequences": ["cadence", "cycle"],
}


def _pair_text(a: str, b: str, mode: str) -> dict:
    ca, cb = Chord.parse(a), Chord.parse(b)
    common = sorted({EDO36.pc(ca.root + i) for i in ca.intervals}
                    & {EDO36.pc(cb.root + i) for i in cb.intervals})
    motion = centered(cb.root - ca.root)
    direction = "a repeated root" if abs(motion) < 1e-8 else f"a root move of {motion:+g} semitones"
    major_third = any(abs(i - 4) < 1e-8 for i in ca.intervals)
    dominant = major_third and any(abs(i - 10) < 1e-8 for i in ca.intervals)
    target_tonic = EDO36.pc(cb.root) == 0
    if target_tonic and EDO36.pc(ca.root) == EDO36.pc(7) and major_third:
        role, advice = "Dominant return", "The source's B can rise to C; an F, when present, can fall to E or E-flat according to the destination."
    elif target_tonic and EDO36.pc(ca.root) == EDO36.pc(5):
        role, advice = "Plagal return", "The subdominant-root approach can support a softer return; phrasing determines whether it becomes a cadence."
    elif dominant and EDO36.pc(ca.root - cb.root) == EDO36.pc(7):
        role, advice = "Local dominant motion", "A major third and minor seventh on the source can point toward this fifth-related target, even within a larger key."
    elif target_tonic and EDO36.pc(ca.root) == EDO36.pc(1) and dominant:
        role, advice = "Substitute-dominant approach", "The flat-II dominant permits a semitone bass approach to tonic; keep its guide tones near their destination."
    elif abs(motion) < 1e-8:
        role, advice = "Common-root color change", "Keep the root steady and let the changing inner notes reveal the new quality; a fresh bass attack need not dominate the change."
    elif abs(motion) <= 1 + 1e-8:
        role, advice = "Chromatic neighbor motion", "A close root movement can sound smoother when the upper voices move independently rather than copying the bass in parallel."
    elif EDO36.pc(ca.root - cb.root) == EDO36.pc(7):
        role, advice = "Descending-fifths link", "The fifth-related roots can form one stage of a longer sequence; shape the melody across the pair rather than restarting it."
    else:
        role, advice = "Connecting motion", "The pair's role depends on the surrounding phrase; a common tone or a small upper-voice step can connect the bass changes."
    names = [pitch_name(i * EDO36.step) for i in common]
    holding = (f"The chord-tone collections share {', '.join(names)} (octaves ignored)."
               if names else "The chord-tone collections share no pitch classes, so look for a small step in an upper voice.")
    target_pcs = sorted({EDO36.pc(cb.root + i) * EDO36.step for i in cb.intervals})
    short_moves = []
    for source in sorted({EDO36.pc(ca.root + i) * EDO36.step for i in ca.intervals}):
        target = min(target_pcs, key=lambda p: abs(centered(p - source)))
        distance = centered(target - source)
        if abs(distance) > 1e-8:
            short_moves.append(f"{pitch_name(source)} to {pitch_name(target)} ({distance:+.3g} semitones)")
    options = (" Possible individual upper-voice moves include " + "; ".join(short_moves[:2]) + "."
               if short_moves else " The upper pitch collection can stay fixed while the bass or spelling changes.")
    return {"summary": f"{a} moves to {b} with {direction} in a C-{mode} reference context.",
            "description": f"In the C-{mode} reference, {a} → {b} is a {role.lower()}. {holding}{options} {advice}",
            "function": role, "root_motion": motion, "common_tones": names}


def seed_catalog() -> dict:
    raw = yaml.safe_load(SEED.read_text(encoding="utf-8"))
    chords, progressions, transitions = [], [], {}
    for line in raw["chord_rows"].splitlines():
        cid, name, suffix, family, formula, summary, description = (s.strip() for s in line.split(" | "))
        symbol = "C" + ("" if suffix == "_" else suffix)
        c = Chord.parse(symbol)
        chords.append({"id": cid, "kind": "chords", "name": name, "family": family, "mode": "",
                       "summary": summary, "description": description, "formula": formula,
                       "symbols": [symbol], "bars": [1], "intervals": list(c.intervals),
                       "tuning": "36edo" if family == "Golden 36-ET" else "12edo",
                       "source_ids": ["golden"] if family == "Golden 36-ET" else ["chords"],
                       "provenance": "Project definition" if family == "Golden 36-ET" else "Chord construction + editorial voicing advice"})
    # Inversions of the same quality link to the quality record; the actual bass is
    # retained in every event and preview. Explicit inversion records stay browsable.
    quality_ids = {}
    for c in chords:
        quality_ids.setdefault(_quality(Chord.parse(c["symbols"][0])), c["id"])

    def pair(a: str, b: str, mode: str, pid: str | None) -> str:
        tid = "t-" + hashlib.sha256(f"{mode}\0{a}\0{b}".encode()).hexdigest()[:16]
        if tid not in transitions:
            transitions[tid] = {"id": tid, "kind": "transitions", "name": f"{a} → {b}",
                                "family": "Golden bridges" if "golden" in mode else "Directed pairs",
                                "mode": mode, "symbols": [a, b], "bars": [1, 1],
                                "tuning": "36edo" if "golden" in mode else "12edo",
                                "chord_ids": [quality_ids[_quality(Chord.parse(s))] for s in (a, b)],
                                "progression_ids": [], "source_ids": [],
                                "provenance": "Computed adjacency + editorial analysis", **_pair_text(a, b, mode)}
        if pid and pid not in transitions[tid]["progression_ids"]:
            transitions[tid]["progression_ids"].append(pid)
        return tid

    for line in raw["progression_rows"].splitlines():
        pid, name, family, mode, roman, symbols, bars, summary, description = (s.strip() for s in line.split(" | "))
        syms, lengths = symbols.split(), list(map(float, bars.split()))
        if len(syms) != len(lengths) or len(roman.split()) != len(syms) or any(b <= 0 for b in lengths):
            raise ValueError(f"Bad event lengths in {pid}")
        # Pop/modal/blues frames repeat; closed cadential examples do not gain an
        # invented last-to-first pair. Loop closure remains visibly marked.
        loop = family in ("Pop and folk", "Borrowed and rock", "Modal vamps", "Blues forms")
        edges = [(i, i + 1, False) for i in range(len(syms) - 1)]
        if loop:
            edges.append((len(syms) - 1, 0, True))
        tids = [{"id": pair(syms[i], syms[j], mode, pid), "position": i, "loop_closure": closure}
                for i, j, closure in edges if syms[i] != syms[j]]
        progressions.append({"id": pid, "kind": "progressions", "name": name,
                             "family": family, "mode": mode, "roman": roman, "symbols": syms,
                             "bars": lengths, "total_bars": sum(lengths), "loop": loop,
                             "summary": summary, "description": description, "tuning": "12edo",
                             "chord_ids": [quality_ids[_quality(Chord.parse(s))] for s in syms],
                             "transition_links": tids, "source_ids": FAMILY_SOURCES[family],
                             "provenance": "Schema-family reference; editorial realization and description"})
    for a, b in (("Cmaj7", "Cg7"), ("Cg7", "Cmaj7"), ("Cmaj9", "Cmaj9(v3,^5,^^9)"),
                 ("Cmaj9(v3,^5,^^9)", "Cmaj9"), ("Cg", "Fg"), ("Fg", "Cg")):
        t = transitions[pair(a, b, "golden bridge", None)]
        t["source_ids"] = ["golden"]
    by_pid = {p["id"]: p for p in progressions}
    for t in transitions.values():
        t["source_ids"] = sorted(set(t["source_ids"]).union(
            *(by_pid[pid]["source_ids"] for pid in t["progression_ids"])))
        t["catalog_uses"] = len(t["progression_ids"])
    for c in chords:
        c["progression_ids"] = [p["id"] for p in progressions if c["id"] in p["chord_ids"]]
        c["transition_ids"] = [t["id"] for t in transitions.values() if c["id"] in t["chord_ids"]]
    return {"version": raw["version"], "title": raw["title"], "selection_note": raw["selection_note"],
            "sources": raw["sources"], "tonics": list(TONICS), "chords": chords,
            "transitions": list(transitions.values()), "progressions": progressions}


class HarmonyLibrary:
    """An indexed, reproducible SQLite reference store (no user-authored rows)."""
    def __init__(self, root: str | Path):
        self.path = Path(root) / ".songmap" / "harmony-library" / "library.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._seed()

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _seed(self):
        fingerprint = hashlib.sha256(SEED.read_bytes() + Path(__file__).read_bytes()).hexdigest()
        with self._lock, self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS entries (
                    kind TEXT NOT NULL, id TEXT NOT NULL, ordinal INTEGER NOT NULL,
                    name TEXT NOT NULL, family TEXT NOT NULL, mode TEXT NOT NULL,
                    search TEXT NOT NULL, data TEXT NOT NULL, PRIMARY KEY(kind,id));
                CREATE INDEX IF NOT EXISTS entry_filters ON entries(kind,family,mode);
                CREATE TABLE IF NOT EXISTS links (
                    source_kind TEXT NOT NULL, source_id TEXT NOT NULL,
                    target_kind TEXT NOT NULL, target_id TEXT NOT NULL, position INTEGER NOT NULL,
                    FOREIGN KEY(source_kind,source_id) REFERENCES entries(kind,id),
                    FOREIGN KEY(target_kind,target_id) REFERENCES entries(kind,id));
                CREATE INDEX IF NOT EXISTS link_targets ON links(target_kind,target_id);
            """)
            old = db.execute("SELECT value FROM metadata WHERE key='fingerprint'").fetchone()
            if old and old[0] == fingerprint:
                return
            catalog = seed_catalog()
            db.execute("DELETE FROM links")
            db.execute("DELETE FROM entries")
            for kind in KINDS:
                for i, item in enumerate(catalog[kind]):
                    search = " ".join(str(item.get(k, "")) for k in
                                      ("name", "summary", "description", "roman", "symbols", "formula", "family", "mode", "function")).casefold()
                    db.execute("INSERT INTO entries VALUES(?,?,?,?,?,?,?,?)",
                               (kind, item["id"], i, item["name"], item["family"], item["mode"], search, json.dumps(item)))
            for kind in ("transitions", "progressions"):
                for item in catalog[kind]:
                    for pos, cid in enumerate(item["chord_ids"]):
                        db.execute("INSERT INTO links VALUES(?,?,?,?,?)", (kind, item["id"], "chords", cid, pos))
                    if kind == "progressions":
                        for link in item["transition_links"]:
                            db.execute("INSERT INTO links VALUES(?,?,?,?,?)", (kind, item["id"], "transitions", link["id"], link["position"]))
            meta = {k: catalog[k] for k in ("version", "title", "selection_note", "sources", "tonics")}
            meta["counts"] = {k: len(catalog[k]) for k in KINDS}
            db.execute("INSERT OR REPLACE INTO metadata VALUES('catalog',?)", (json.dumps(meta),))
            db.execute("INSERT OR REPLACE INTO metadata VALUES('fingerprint',?)", (fingerprint,))

    def metadata(self) -> dict:
        with self._connect() as db:
            out = json.loads(db.execute("SELECT value FROM metadata WHERE key='catalog'").fetchone()[0])
            out["families"] = {kind: [row[0] for row in db.execute(
                "SELECT DISTINCT family FROM entries WHERE kind=? ORDER BY family", (kind,))] for kind in KINDS}
            out["names"] = {kind: dict(db.execute("SELECT id,name FROM entries WHERE kind=?", (kind,))) for kind in KINDS}
            return out

    def search(self, kind: str, q: str = "", family: str = "", mode: str = "", limit: int = 500) -> list[dict]:
        if kind not in KINDS:
            raise ValueError("Unknown library database")
        terms, args = ["kind=?"], [kind]
        for token in q.casefold().split():
            terms.append("instr(search,?)>0")
            args.append(token)
        for key, value in (("family", family), ("mode", mode)):
            if value:
                terms.append(f"{key}=?")
                args.append(value)
        with self._connect() as db:
            rows = db.execute("SELECT data FROM entries WHERE " + " AND ".join(terms) + " ORDER BY ordinal LIMIT ?",
                              (*args, min(max(limit, 1), 1000))).fetchall()
        return [json.loads(row[0]) for row in rows]

    def get(self, kind: str, entry_id: str) -> dict:
        with self._connect() as db:
            row = db.execute("SELECT data FROM entries WHERE kind=? AND id=?", (kind, entry_id)).fetchone()
        if not row:
            raise KeyError("Library entry not found")
        return json.loads(row[0])

    def export(self) -> dict:
        return {**self.metadata(), **{kind: self.search(kind, limit=1000) for kind in KINDS}}


def realization(entry: dict, tonic: str = "C", bpm: int = 100) -> dict:
    """Symbols, explicit voiced MIDI notes and valid compact notation from one plan."""
    from ..theory.voicing import voice_lead
    if not 60 <= bpm <= 180:
        raise ValueError("Preview tempo must be 60–180 bpm")
    symbols = [transpose(s, tonic) for s in entry["symbols"]]
    tuning = EDO36 if entry["tuning"] == "36edo" else DEFAULT
    events, notes, now, prev = [], [], 0.0, None
    for symbol, bars in zip(symbols, entry["bars"]):
        c = Chord.parse(symbol)
        upper = voice_lead(prev, c.root, c.intervals, lo=53, hi=79,
                           voices=len(c.intervals), tuning=tuning)
        prev = upper
        bass = 3 * OCTAVE + c.bass
        pitches = (bass, *upper)
        duration = bars * 4 * 60 / bpm
        event = {"symbol": symbol, "start": now, "duration": duration, "bars": bars,
                 "pitches": list(pitches), "notes": [pitch_name(p, True) for p in pitches]}
        events.append(event)
        for p in pitches:
            notes.append({"t": now, "pitch": p, "gate": max(0.1, duration * .88), "vel": .45})
        now += duration
    mode = entry["mode"] if entry["mode"] in ("minor", "dorian", "phrygian", "mixolydian", "lydian") else "major"
    key = tonic + ("m" if mode == "minor" else "" if mode == "major" else f" {mode}")
    # Header key can be quoted if it has a mode name; score is checked by tests.
    header_key = f'"{key}"' if " " in key else key
    chord_line = "chords " + " ".join(f"{s}:{b:g}" for s, b in zip(symbols, entry["bars"]))
    score = (f'# Harmony Library: {entry["name"]}\n# {entry["summary"]}\n'
             f'song "{entry["name"]}" {bpm} 4/4 {header_key} seed=1 tail=2 tuning={entry["tuning"]}\n'
             f'{chord_line}\ninst keys=keys/still\nmix keys -8\n'
             f'example {sum(entry["bars"]):g} | keys:hold dyn=p\n')
    return {"tonic": tonic, "bpm": bpm, "seconds": now, "events": events,
            "notes": notes, "score": score, "chord_line": chord_line,
            "preview_note": "Stable piano, all chord tones above an explicit bass; illustrative voice leading."}


def render_preview(plan: dict):
    """Bounded quiet piano preview; shared with rack audition (no project needed)."""
    from ..instruments import Note, make
    from ..instruments.dsp import SR, as_stereo
    import numpy as np
    inst = make("keys/still", hardness=.28, t60=2.2)
    out = np.zeros((math.ceil((plan["seconds"] + 2.5) * SR), 2))
    for i, n in enumerate(plan["notes"]):
        y = as_stereo(inst.render(Note(n["pitch"], n["vel"], n["gate"], seed=i + 1, rr=0)))
        start = round(n["t"] * SR)
        end = min(len(out), start + len(y))
        out[start:end] += y[:end - start]
    peak = float(np.max(np.abs(out)))
    out *= min(.55 / max(peak, 1e-9), .65)
    fade = min(SR // 10, len(out))
    out[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return out
