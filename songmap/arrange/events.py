"""Events -> fx notes and mutes (SONGMAP_SPEC §8).

Rendered now: `impact` (starts at `at`), `riser` (ENDS at `at`), `zaps` (a run of chirps, one per
`every` note value, rising in pitch like synth_v0), and `drop`/`stop` (parts fall silent for a
span; for now by removing the notes that start inside it, P4 adds click-free mute masks).
The other types are validated and exported to cues.json, and render from P3/P4.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..parse import positions
from ..parse.errors import SongError, did_you_mean
from ..parse.notes import parse_duration
from .expand import ResolvedEvent, XEv, seed_for

EVENT_TYPES = ("impact", "riser", "downlifter", "hit", "zaps", "ticks", "stop", "drop", "fill", "swell", "crash",
               "reverse", "tape_stop", "filter_sweep", "cloud")
RENDERED = ("impact", "riser", "zaps", "stop", "drop")
SIZE_VEL = {"s": 0.6, "m": 0.8, "l": 1.0, "xl": 1.0}


@dataclass
class Mute:
    start: float
    end: float
    keep: frozenset


def _length(ev, tl, default_bars: float, at: float, sign: int = 1) -> float:
    """An event's length in beats; bars are counted forward (or, sign -1, backward) from `at`,
    so they follow the meters they cross."""
    p = ev.params
    if "beats" in p:
        return float(p["beats"])
    return abs(tl.bars_after(at, sign * float(p.get("bars", default_bars))) - at)


def expand_events(ctx) -> tuple[list[XEv], list[ResolvedEvent], list[Mute]]:
    song, tl = ctx.song, ctx.tl
    out, resolved, mutes = [], [], []
    for i, ev in enumerate(song.events):
        where = dict(file=song.file, line=ev.line)
        if ev.type not in EVENT_TYPES:
            raise SongError(f"unknown event type '{ev.type}'", **where, suggestion=did_you_mean(ev.type, EVENT_TYPES))
        try:
            pos = positions.resolve(ev.at, tl, song.cues, snap=str(ev.params.get("snap", "16")))
        except SongError as e:
            raise SongError(e.message, **where, suggestion=e.suggestion) from None
        if abs(pos.frame_error) > 1:
            ctx.warnings.append(f"{song.file}:{ev.line} event {ev.type}@{ev.at}: snapping to the 16th grid moves it "
                                f"{pos.frame_error:+d} frames; use snap: none to keep the exact frame")
        sec = tl.section_at(pos.beat)
        secname = sec.name if sec else None
        start = pos.beat
        rng = np.random.default_rng(seed_for(song.seed, "event", i, ev.type))
        t = ev.type
        if t == "impact":
            size = str(ev.params.get("size", "l"))
            out.append(XEv("fx", pos.beat, tl.bpb_at(pos.beat), (), SIZE_VEL.get(size, 1.0), "impact",
                           patch=(("decay", 4.5),) if size == "xl" else (), tags=frozenset({"event:impact"}),
                           section=secname or ""))
        elif t == "riser":
            n = _length(ev, tl, 1, pos.beat, -1)
            start = pos.beat - n
            out.append(XEv("fx", start, n, (), 1.0, "riser", length=n, tags=frozenset({"event:riser"}),
                           section=(tl.section_at(start).name if tl.section_at(start) else secname) or ""))
        elif t == "zaps":
            count = int(ev.params.get("count", 4))
            every = parse_duration(str(ev.params.get("every", 8)))
            for k in range(count):
                b = pos.beat + k * every
                s = tl.section_at(b)
                out.append(XEv("fx", b, every, (), 0.7, "zap", pan=float(rng.uniform(-0.5, 0.5)),
                               params={"f0": 2000.0 + 600.0 * k}, tags=frozenset({"event:zaps"}),
                               section=(s.name if s else secname) or ""))
        elif t in ("drop", "stop"):
            n = _length(ev, tl, 2 if t == "drop" else 0.5, pos.beat)
            keep = set(ev.params.get("keep") or []) | ({"fx"} if t == "stop" else set())
            mutes.append(Mute(pos.beat, pos.beat + n, frozenset(keep)))
        else:
            ctx.warn_once(("event", t), f"event type '{t}' is exported to cues.json but renders from P3/P4")
        resolved.append(ResolvedEvent(t, str(ev.at), pos.beat, start, dict(ev.params), secname))
    return out, resolved, mutes


def apply_mutes(parts: dict, mutes: list[Mute]) -> None:
    """Remove section-part notes that start inside a drop/stop. Notes made by events always play."""
    for m in mutes:
        for p in parts:
            if p in m.keep:
                continue
            parts[p] = [e for e in parts[p] if not (m.start - 1e-9 <= e.beat < m.end - 1e-9)
                        or any(t.startswith("event:") for t in e.tags)]
