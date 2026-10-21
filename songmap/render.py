"""Orchestration: parse -> expand -> render notes -> mix -> master -> export (ENGINE.md §3).

The performance layer (humanize, groove, dynamics shaping) is wired in at P3; until then
written events are played as written: onset on the grid, gate from the articulation.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field

import numpy as np

from .arrange.expand import Arrangement, XEv, expand, seed_for
from .export import cues as cues_mod
from .export import qa as qa_mod
from .export.wav import write_float, write_wav24
from .instruments import Note
from .instruments.dsp import SR, as_stereo, n_samples, pan_mono, undb
from .mix.fx import convolve, reverb_ir, sidechain_env
from .mix.master import master, master_clean, master_legacy
from .model import Song
from .perform.pipeline import GATE

RR_SLOTS = 8      # round-robin: each kit piece / part cycles through 8 seeded variations


@dataclass
class RenderResult:
    arrangement: Arrangement
    audio: np.ndarray                      # mastered, (n, 2)
    premaster: np.ndarray
    stems: dict[str, np.ndarray]           # per part (post fader, post sidechain) + returns
    stats: dict = field(default_factory=dict)

    @property
    def song(self) -> Song:
        return self.arrangement.song

    def section_spans(self) -> list[tuple[str, float, float]]:
        tl = self.arrangement.timeline
        return [(s.name, tl.beat_to_sec(s.start), tl.beat_to_sec(s.end)) for s in tl.sections]


def _place(buf: np.ndarray, start: int, sig: np.ndarray, gain: float, pan: float) -> None:
    s = pan_mono(sig, pan) if sig.ndim == 1 else sig * np.array([1 - max(pan, 0), 1 + min(pan, 0)])
    if start < 0:
        s, start = s[-start:], 0
    s = s[: len(buf) - start]
    if len(s):
        buf[start:start + len(s)] += s * gain


def held_beats(e: XEv) -> float:
    if e.length is not None:
        return float(e.length)
    frac = e.gate if e.gate is not None else GATE.get("legato" if e.slur else e.art, 0.9)
    return e.dur * frac


def render(song: Song, *, master_mode: str | None = None, log=None) -> RenderResult:
    t0 = time.time()
    arr = expand(song)
    tl, ens = arr.timeline, arr.ensemble
    n = n_samples(tl.seconds)
    buses: dict[str, np.ndarray] = {}
    triggers: dict[str, list[float]] = {}
    cache: dict = {}
    rendered = hits = 0
    for part, evs in arr.parts.items():
        buf = buses.setdefault(part, np.zeros((n, 2)))
        slot: dict = {}
        for e in evs:
            inst = ens.instrument(part, e.piece, e.patch)
            voice = ens.voice(part, e.piece)
            t = tl.beat_to_sec(e.beat)
            gate = max(tl.beat_to_sec(e.beat + held_beats(e)) - t, 1e-3)
            k = slot.get(e.piece, 0)
            slot[e.piece] = k + 1
            seed = seed_for(song.seed, part, e.piece or "", k % RR_SLOTS)
            gain = float(undb(voice.gain_db + e.gain_db))
            pan = float(np.clip(voice.pan + e.pan, -1, 1))
            for p in e.pitches or (60.0,):
                key = (id(inst), round(float(p), 4), round(e.vel, 5), round(gate, 5), seed,
                       tuple(sorted(e.params.items())))
                y = cache.get(key)
                if y is None:
                    y = inst.render(Note(float(p), float(e.vel), gate, seed=seed, params=dict(e.params)))
                    cache[key] = y
                    rendered += 1
                else:
                    hits += 1
                _place(buf, int(round(t * SR)), y, gain, pan)
            for name in (e.piece, part):
                if name:
                    triggers.setdefault(name, []).append(t)
    # --- mix: fader, sidechain, sends -> returns -----------------------------------------
    sends: dict[str, np.ndarray] = {}
    stems: dict[str, np.ndarray] = {}
    for part, buf in buses.items():
        m = ens.mix.get(part, {})
        buf *= float(undb(float(m.get("gain_db", 0))))
        if m.get("pan"):
            p = float(m["pan"])
            buf *= np.array([1 - max(p, 0), 1 + min(p, 0)])
        sc = m.get("sidechain")
        if sc and triggers.get(sc.get("from", "kick")):
            env = sidechain_env(triggers[sc.get("from", "kick")], n, depth=float(sc.get("depth", 0.5)),
                                release=float(sc.get("release", 0.15)), attack=float(sc.get("attack", 0.004)))
            buf *= env[:, None]
        for ret, amt in (m.get("send") or {}).items():
            if ret not in ens.returns:
                raise ValueError(f"mix {part}: send to unknown return '{ret}' (returns: {', '.join(ens.returns)})")
            sends.setdefault(ret, np.zeros((n, 2)))
            sends[ret] += buf * float(amt)
        stems[part] = buf
    for ret, x in sends.items():
        r = ens.returns[ret]
        if r.get("type", "reverb") != "reverb":
            continue
        ir = reverb_ir(float(r.get("seconds", 2.2)), predelay=float(r.get("predelay", 0.015)),
                       damping=float(r.get("damping", 0.5)), early=int(r.get("early", 10)),
                       width=float(r.get("width", 1.0)), seed=seed_for(song.seed, "return", ret) % 2**31)
        stems[f"return_{ret}"] = convolve(x, ir)
    mix = sum(stems.values()) if stems else np.zeros((n, 2))
    mode = master_mode or song.master.mode
    if mode == "legacy":
        out = master_legacy(mix)
    elif mode == "clean":
        out = master_clean(mix, song.master.ceiling_db)
    else:
        out = master(mix, song.master.target_lufs, song.master.ceiling_db, glue=song.master.glue != "none")
    stats = {"seconds": round(time.time() - t0, 2), "notes_rendered": rendered, "cache_hits": hits,
             "audio_seconds": round(n / SR, 3), "master": mode, "digest": arr.digest()}
    if log:
        log(f"rendered {n / SR:.1f}s of audio in {stats['seconds']}s ({rendered} notes synthesized, {hits} cached)")
    return RenderResult(arr, as_stereo(out), mix, stems, stats)


def write_outputs(r: RenderResult, out_dir: str, *, stems: bool = True, mp3: bool = False) -> dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    paths = {"song": os.path.join(out_dir, "song.wav"), "cues": os.path.join(out_dir, "cues.json"),
             "qa": os.path.join(out_dir, "qa.json"), "log": os.path.join(out_dir, "render.log")}
    write_wav24(paths["song"], r.audio)
    if mp3:
        from .export.wav import write_mp3
        paths["mp3"] = write_mp3(os.path.join(out_dir, "song.mp3"), paths["song"])
    if stems:
        for name, x in r.stems.items():
            write_float(os.path.join(out_dir, "stems", f"{name}.wav"), x)
        paths["stems"] = os.path.join(out_dir, "stems")
    cues_mod.write(paths["cues"], cues_mod.build(r.arrangement))
    report = qa_mod.qa(r.audio, r.section_spans())
    report["stems"] = {k: round(qa_mod.lufs(v), 2) for k, v in r.stems.items()}
    report["render"] = r.stats
    with open(paths["qa"], "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    with open(paths["log"], "w", encoding="utf-8") as f:
        f.write(render_log(r))
    return paths


def render_log(r: RenderResult) -> str:
    arr = r.arrangement
    lines = [f"{arr.song.title}: {arr.timeline.total_bars:g} bars, {arr.timeline.seconds:.2f}s, "
             f"{arr.timeline.frames} frames @ {arr.timeline.fps} fps", f"event digest {arr.digest()}",
             f"render {json.dumps(r.stats)}", ""]
    by = arr.counts_by_section()
    parts = sorted({p for d in by.values() for p in d})
    lines.append("section".ljust(14) + "".join(p.rjust(8) for p in parts))
    for s in arr.timeline.sections:
        d = by.get(s.name, {})
        lines.append(s.name.ljust(14) + "".join(str(d.get(p, 0)).rjust(8) for p in parts))
    lines.append("")
    lines += [f"warning: {w}" for w in arr.song.warnings + arr.warnings]
    return "\n".join(lines) + "\n"
