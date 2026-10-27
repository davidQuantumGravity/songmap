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
from .instruments.sampler.library import licenses_md
from .mix.fx import convolve, reverb_ir, sidechain_env
from .mix.inserts import apply_chain
from .mix.master import master, master_clean, master_legacy
from .model import Song
from .perform.pipeline import GATE

RR_SLOTS = 8      # round-robin: each kit piece / part cycles through 8 seeded variations
CHOKE_FADE = int(0.006 * SR)   # SFZ off_mode=fast: a choked note fades out over 6 ms


@dataclass
class RenderResult:
    arrangement: Arrangement
    audio: np.ndarray                      # mastered, (n, 2)
    premaster: np.ndarray
    stems: dict[str, np.ndarray]           # per part (post fader, post sidechain) + returns
    stats: dict = field(default_factory=dict)
    sources: list[dict] = field(default_factory=list)   # sample libraries used (-> LICENSES.md)

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


END_FADE = int(0.003 * SR)     # a note still sounding when its buffer ends fades over its last 3 ms


def declick(y: np.ndarray) -> np.ndarray:
    """A note whose sound is still loud at the end of its buffer would click when it stops: fade its last 3 ms.
    Notes that already end in silence are returned unchanged."""
    if len(y) < 2 * END_FADE:
        return y
    tail = float(np.max(np.abs(y[-END_FADE:])))
    if tail <= 1e-3 * max(float(np.max(np.abs(y))), 1e-12):
        return y
    y = y.copy()
    fade = 0.5 + 0.5 * np.cos(np.pi * np.arange(1, END_FADE + 1) / END_FADE)
    y[-END_FADE:] *= fade[:, None] if y.ndim == 2 else fade
    return y


def _apply_chokes(placed: list) -> None:
    """SFZ-style choke: a note whose off_by is G is cut (fast fade) when a later note of group G
    starts in the same part. `placed` holds [start, y, gain, pan, group, off_by]; y is replaced."""
    starts = {}
    for start, _, _, _, group, _ in placed:
        starts.setdefault(group, []).append(start)
    for item in placed:
        start, y, _, _, _, off_by = item
        if not off_by or off_by not in starts:
            continue
        later = [s for s in starts[off_by] if s > start]
        if not later:
            continue
        cut = min(later) - start
        if cut >= len(y):
            continue
        nf = min(CHOKE_FADE, cut)
        fade = 0.5 + 0.5 * np.cos(np.pi * np.arange(1, nf + 1) / nf)     # ends exactly at 0
        y = y[:cut].copy()
        y[cut - nf:] *= fade[:, None] if y.ndim == 2 else fade
        item[1] = y


def held_beats(e: XEv) -> float:
    if e.length is not None:
        return float(e.length)
    frac = e.gate if e.gate is not None else GATE.get("legato" if e.slur else e.art, 0.9)
    return e.dur * frac


def inst_key(inst) -> tuple:
    """An instrument's identity for the note cache: its class, params and (samplers) its program."""
    src = getattr(inst, "source", None)
    from .instruments.response import fingerprint as response_fingerprint
    return (type(inst).__name__, getattr(inst, "name", ""), tuple(sorted((k, repr(v)) for k, v in inst.p.items())),
            src.get("program") if isinstance(src, dict) else None,
            getattr(inst, "fixed_pitch", None), getattr(inst, "fingerprint", None),response_fingerprint(inst))


def render(song: Song, *, master_mode: str | None = None, log=None, note_cache: dict | None = None,
           preview_end: float | None = None) -> RenderResult:
    """`note_cache`: a dict kept across renders (the Studio's) so notes that didn't change aren't synthesized
    again; keys are (instrument identity, pitch, velocity, gate, seed, params)."""
    t0 = time.time()
    arr = expand(song)
    tl, ens = arr.timeline, arr.ensemble
    # Preview from the original beginning so note seeds, expression, effect history and
    # section-relative patterns remain intact. The caller crops the desired excerpt afterward.
    n = n_samples(min(tl.seconds, max(.1, preview_end)) if preview_end is not None else tl.seconds)
    buses: dict[str, np.ndarray] = {}
    triggers: dict[str, list[float]] = {}
    cache: dict = {} if note_cache is None else note_cache
    ikeys: dict[int, tuple] = {}
    rendered = hits = 0
    from .perform.play import play, played_digest
    played = play(arr)                     # the performance stage (mood v0: the written notes as they are)
    from .expression import Expression, apply as apply_expression
    expression = Expression(arr)
    for part, evs in played.items():
        buf = buses.setdefault(part, np.zeros((n, 2)))
        slot: dict = {}
        placed: list = []
        for e in evs:
            if preview_end is not None and tl.beat_to_sec(e.beat) >= preview_end:
                continue
            inst = ens.instrument(part, e.piece, e.patch)
            voice = ens.voice(part, e.piece)
            t = tl.beat_to_sec(e.beat)
            gate = max(tl.beat_to_sec(e.beat + held_beats(e)) - t, 1e-3)
            k = slot.get(e.piece, 0)
            slot[e.piece] = k + 1
            seed = seed_for(song.seed, part, e.piece or "", k % RR_SLOTS)
            # SFZ sequences may have 3, 5 or more than 8 takes. Keep the full counter;
            # native synths retain their original eight seeded variations.
            rr = k if getattr(inst, "program", None) is not None or getattr(inst, "full_rr", False) else k % RR_SLOTS
            gain = float(undb(voice.gain_db + e.gain_db))
            pan = float(np.clip(voice.pan + e.pan, -1, 1))
            for p in e.pitches or (60.0,):
                ik = ikeys.get(id(inst))
                if ik is None:
                    ik = ikeys[id(inst)] = inst_key(inst) if note_cache is not None else (id(inst),)
                key = (ik, round(float(p), 4), round(e.vel, 5), round(gate, 5), seed, rr,
                       tuple(sorted(e.params.items())))
                note = Note(float(p), float(e.vel), gate, seed=seed, rr=rr, params=dict(e.params))
                if hasattr(inst,'select'):
                    note.technique=inst.select(e.technique,'legato' if e.slur else e.art)
                    key += (note.technique,)
                note.curves = expression.bind(part,t,{**inst.p,**note.params})
                if note.curves:
                    key += (expression.fingerprint,part,round(t,8))
                placed_by_instrument = hasattr(inst, "render_at_pan")
                if placed_by_instrument:
                    key += (pan,)
                y = cache.get(key)
                if y is None:
                    y = inst.render_at_pan(note, pan, finish=declick) if placed_by_instrument else declick(inst.render(note))
                    y = apply_expression(y,note)
                    cache[key] = y
                    rendered += 1
                else:
                    hits += 1
                placed.append([int(round(t * SR)), y, gain, 0 if placed_by_instrument else pan, *inst.choke(note)])
            for name in (e.piece, part):
                if name:
                    triggers.setdefault(name, []).append(t)
        _apply_chokes(placed)
        for start, y, gain, pan, _, _ in placed:
            _place(buf, start, y, gain, pan)
    # --- mix: fader, sidechain, sends -> returns -----------------------------------------
    sends: dict[str, np.ndarray] = {}
    stems: dict[str, np.ndarray] = {}
    for part, buf in buses.items():
        m = ens.mix.get(part, {})
        if m.get("inserts"):                          # insert effects, before the fader
            buf = apply_chain(buf, m["inserts"], {"tempo": song.tempo, "seed": seed_for(song.seed, "insert", part)})
        buf *= float(undb(float(m.get("gain_db", 0))))
        if m.get("pan"):
            p = float(m["pan"])
            buf *= np.array([1 - max(p, 0), 1 + min(p, 0)])
        sc = m.get("sidechain")
        if sc and triggers.get(sc.get("from", "kick")):
            env = sidechain_env(triggers[sc.get("from", "kick")], n, depth=float(sc.get("depth", 0.5)),
                                release=float(sc.get("release", 0.15)), attack=float(sc.get("attack", 0.004)))
            buf *= env[:, None]
        ens.check_sends(part, m)
        for ret, amt in (m.get("send") or {}).items():
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
        wet = convolve(x, ir)
        chain = (ens.mix.get(ret) or {}).get("inserts") if ret not in buses else None
        if chain:                                     # `inserts hall ...`: the return's own chain, after the reverb
            wet = apply_chain(wet, chain, {"tempo": song.tempo, "seed": seed_for(song.seed, "insert", ret)})
        stems[f"return_{ret}"] = wet
    layer = None
    if song.binaural:                       # dry, after the returns: a reverb would mix the ears
        from .mix.binaural import carve, plan as binaural_plan, render_layer
        layer = binaural_plan(song, tl)
        music = sum(stems.values()) if stems else np.zeros((n, 2))
        # the stem is the layer's whole effect on the mix: its tones, minus the music they replace
        stems["binaural"] = render_layer(layer, tl, n, music, SR) - (carve(layer, music, SR) if layer.carve else 0)
    mix = sum(stems.values()) if stems else np.zeros((n, 2))
    if (ens.mix.get("master") or {}).get("inserts"):  # the master's insert chain, before mastering
        mix = apply_chain(mix, ens.mix["master"]["inserts"], {"tempo": song.tempo, "seed": seed_for(song.seed, "insert")})
    mode = master_mode or song.master.mode
    if mode == "legacy":
        out = master_legacy(mix)
    elif mode == "clean":
        out = master_clean(mix, song.master.ceiling_db)
    else:
        out = master(mix, song.master.target_lufs, song.master.ceiling_db, glue=song.master.glue != "none")
    stats = {"seconds": round(time.time() - t0, 2), "notes_rendered": rendered, "cache_hits": hits,
             "audio_seconds": round(n / SR, 3), "master": mode, "digest": arr.digest(),
             "performed": played is not arr.parts, "played_digest": played_digest(played)}
    if layer is not None:
        stats["binaural"] = layer.summary
    if log:
        log(f"rendered {n / SR:.1f}s of audio in {stats['seconds']}s ({rendered} notes synthesized, {hits} cached)")
    sources = {s["program"]: s for i in ens.instruments()
               for s in (i.sources if hasattr(i, "sources") else [i.source] if hasattr(i, "source") else [])}
    if sources:
        stats["samples"] = sorted(s["name"] for s in sources.values())
    return RenderResult(arr, as_stereo(out), mix, stems, stats, list(sources.values()))


def write_outputs(r: RenderResult, out_dir: str, *, stems: bool = True, mp3: bool = False) -> dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    paths = {"song": os.path.join(out_dir, "song.wav"), "cues": os.path.join(out_dir, "cues.json"),
             "qa": os.path.join(out_dir, "qa.json"), "log": os.path.join(out_dir, "render.log")}
    write_wav24(paths["song"], r.audio)
    if mp3:
        from .export.wav import write_mp3
        paths["mp3"] = write_mp3(os.path.join(out_dir, "song.mp3"), paths["song"],
                                 joint_stereo=not r.song.binaural)       # keep the ears' tones apart
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
    from .listen import listen
    review = listen(r.arrangement, report)
    paths["review"] = os.path.join(out_dir, "review.json")
    with open(paths["review"], "w", encoding="utf-8") as f:
        json.dump(review.to_dict(), f, indent=1)
    try:
        from .export.qa_plot import write_png
        tl = r.arrangement.timeline
        paths["png"] = write_png(os.path.join(out_dir, "qa.png"), r.audio, r.section_spans(),
                                 [(e.type, tl.beat_to_sec(e.beat)) for e in r.arrangement.events],
                                 {s["name"]: s.get("loudness") for s in report.get("sections", [])},
                                 r.arrangement.song.title)
    except ImportError:                       # matplotlib is optional for the picture
        pass
    with open(paths["log"], "w", encoding="utf-8") as f:
        f.write(render_log(r))
    if r.sources:
        paths["licenses"] = os.path.join(out_dir, "LICENSES.md")
        with open(paths["licenses"], "w", encoding="utf-8") as f:
            f.write(licenses_md(r.sources))
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
