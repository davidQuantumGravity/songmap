"""Song -> {part: [XEv]}: written events, section by section, against the harmony timeline.

Each part in each section is one of: a style (patterns/*.yaml), a motif list, inline notes
(letter, deg or rel mode) or drum step strings. Motif lists cycle per block, anchored at the
song start like synth_v0 (`melody[(bar // 2) % 4]`), so a section entering mid-song picks up
the motif that block would have played. Events (impact, riser, zaps, ...) become fx notes.

Nothing here is random except where a style asks for it (ticks, pan scatter), and that is
seeded per song/section/part/bar with crc32, so the event list is reproducible and hashable.
"""
from __future__ import annotations

import hashlib
import math
import zlib
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

from ..model import Song
from ..parse.errors import NotationError, SongError, did_you_mean
from ..parse.notes import DYN, Ev, motif_length, parse_motif, rel_to_midi
from ..parse.steps import parse_steps
from ..perform.pipeline import parse_shape, shape_at
from ..theory.harmony import HarmonyTimeline, build_harmony, parse_progression
from ..theory.keys import tonic_midi
from ..theory.tuning import on_grid, octaves, parse_tuning
from .ensemble import Ensemble
from .styles import Style, get_style
from .timeline import SectionSpan, Timeline

LATER_OPTS = {"feel": "P3", "voicing": "P3", "auto": "P3", "fills": "P3", "crash": "P3", "octaves": "P3"}


def seed_for(*names) -> int:
    """Stable seed from names (crc32; never Python's per-process `hash()`)."""
    return zlib.crc32("/".join(str(n) for n in names).encode())


@dataclass
class XEv:
    """One written note of one part, at an absolute beat."""
    part: str
    beat: float
    dur: float                       # written duration (beats)
    pitches: tuple = ()
    vel: float = 0.62
    piece: str | None = None         # kit piece for drums/fx
    art: str = "normal"
    gate: float | None = None        # fraction of `dur` held; None = articulation default
    length: float | None = None      # held length in beats (overrides dur * gate)
    pan: float = 0.0
    gain_db: float = 0.0
    params: dict = field(default_factory=dict)    # per-note instrument params (automation snapshot)
    patch: tuple = ()                # style-level instrument overrides
    slur: bool = False
    tags: frozenset = frozenset()
    section: str = ""

    def key(self) -> str:
        f = lambda x: f"{x:.6f}"  # noqa: E731
        return "|".join([self.part, self.piece or "", f(self.beat), f(self.dur),
                         ",".join(f(p) for p in self.pitches), f(self.vel), self.art,
                         "" if self.gate is None else f(self.gate), "" if self.length is None else f(self.length),
                         f(self.pan), f(self.gain_db), repr(sorted(self.params.items())), repr(self.patch),
                         str(int(self.slur)), ",".join(sorted(self.tags)), self.section])


@dataclass
class ResolvedEvent:
    type: str
    at: str
    beat: float                      # where the event lands (a riser ENDS here)
    start: float                     # where its sound starts
    params: dict
    section: str | None


@dataclass
class Arrangement:
    song: Song
    timeline: Timeline
    harmony: HarmonyTimeline
    ensemble: Ensemble
    parts: dict[str, list[XEv]]
    events: list[ResolvedEvent]
    warnings: list[str]

    def digest(self) -> str:
        """sha256 of the whole expanded event list: the golden-test fingerprint."""
        h = hashlib.sha256()
        for part in sorted(self.parts):
            for e in self.parts[part]:
                h.update(e.key().encode())
                h.update(b"\n")
        return h.hexdigest()

    def counts(self) -> dict[str, int]:
        return {p: len(v) for p, v in self.parts.items()}

    def counts_by_section(self) -> dict[str, dict[str, int]]:
        out: dict[str, dict[str, int]] = {}
        for p, evs in self.parts.items():
            for e in evs:
                out.setdefault(e.section, {}).setdefault(p, 0)
                out[e.section][p] += 1
        return out


# ----------------------------------------------------------------------------
# harmony
# ----------------------------------------------------------------------------
def harmony_timeline(song: Song, tl: Timeline) -> HarmonyTimeline:
    bpb = song.beats_per_bar
    try:
        default = parse_progression(song.harmony.default, bpb, song.harmony.chord_bars) if song.harmony.default else []
    except NotationError as e:
        raise SongError(f"harmony default: {e}", file=song.file) from None
    progs = []
    for sec, span in zip(song.sections, tl.sections):
        prog = None
        if sec.harmony:
            text = song.harmony.progressions.get(sec.harmony, sec.harmony)
            if sec.harmony not in song.harmony.progressions and ":" not in text and " " not in text.strip():
                raise SongError(f"unknown progression '{sec.harmony}'", file=song.file, line=sec.line,
                                section=sec.name, suggestion=did_you_mean(sec.harmony, song.harmony.progressions)
                                if song.harmony.progressions else "define it under harmony: progressions:")
            try:
                prog = parse_progression(text, bpb)
            except NotationError as e:
                raise SongError(str(e), file=song.file, line=sec.line, section=sec.name) from None
        progs.append((span.start, span.end, prog))
    return build_harmony(default, progs, tl.total_beats, tonic_midi(song.key))


# ----------------------------------------------------------------------------
# expansion
# ----------------------------------------------------------------------------
class _Ctx:
    def __init__(self, song: Song):
        self.song = song
        self.tl = Timeline(song)
        self.harm = harmony_timeline(song, self.tl)
        self.ens = Ensemble(song)
        self.bpb = song.beats_per_bar
        self.tonic = tonic_midi(song.key)
        self.tuning = parse_tuning(song.tuning)
        self.warnings: list[str] = []
        self._motif_cache: dict = {}
        self._voicing_cache: dict = {}
        self._warned: set = set()

    def warn_once(self, key, msg):
        if key not in self._warned:
            self._warned.add(key)
            self.warnings.append(msg)

    def motif(self, ref: str, sec_name: str) -> list[Ev]:
        if ref in self._motif_cache:
            return self._motif_cache[ref]
        name = ref.split(":")[0]
        if ":" in ref:
            raise SongError(f"motif transform '{ref}' arrives in P3", file=self.song.file, section=sec_name,
                            suggestion=f"use '{name}' for now")
        if name not in self.song.motifs:
            raise SongError(f"unknown motif '{name}'", file=self.song.file, section=sec_name,
                            suggestion=did_you_mean(name, self.song.motifs) if self.song.motifs else
                            "define it under motifs:")
        m = self.song.motifs[name]
        try:
            evs = parse_motif(m.text, deg=m.mode == "deg", rel=m.mode == "rel", key=m.key or self.song.key,
                              octave=m.octave, beats_per_bar=self.bpb, name=f"motif {name}")
        except NotationError as e:
            raise SongError(str(e), file=self.song.file, line=m.line) from None
        self._motif_cache[ref] = evs
        return evs


def _whole_bars(length: float, bpb: float) -> float:
    return max(1, math.ceil(length / bpb - 1e-9)) * bpb


def _resolve_rel(ctx: _Ctx, e: Ev, beat: float, oct_: int) -> tuple | None:
    if not e.rel:
        return e.pitches
    chord = ctx.harm.chord_at(beat)
    if chord is None:
        return None
    root = chord.home_root(ctx.tonic) + octaves(oct_)
    return tuple(rel_to_midi(t, o, chord.intervals, root, ctx.tuning) for t, o in e.rel)


def _from_ev(part, e: Ev, beat, pitches, sec, **kw) -> "XEv":
    kw.setdefault("tags", frozenset(e.tags))
    return XEv(part=part, beat=beat, dur=e.dur, pitches=tuple(pitches), vel=e.vel, art=e.art, slur=e.slur,
               section=sec, **kw)


def _kit(ctx: _Ctx, sec, span: SectionSpan, role: str, style: Style | None, mods: list[str],
         steps: dict, patch_src) -> list[XEv]:
    lanes: dict[str, list] = defaultdict(list)
    phrase: list[tuple[int, dict]] = []
    chance, pan_random, gain = {}, 0.0, 0.0
    if style:
        for k, v in style.get("steps", {}).items():
            lanes[k].append(v)
        chance = style.get("chance", {}) or {}
        pan_random = float(style.get("pan_random", 0) or 0)
        gain = float(style.get("gain_db", 0) or 0)
        for mod in mods:
            m = (style.get("mods") or {}).get(mod)
            if m is None:
                raise SongError(f"{role} style '{style.name}' has no mod '+{mod}'", file=ctx.song.file,
                                line=sec.line, section=sec.name, suggestion=did_you_mean(mod, style.get("mods") or {}))
            for k, v in (m.get("set") or {}).items():
                lanes[k] = [v]
            for k, v in (m.get("add") or {}).items():
                lanes[k].append(v)
            if "every" in m:
                phrase.append((int(m["every"]), m.get("last_bar") or {}))
    elif mods:
        raise SongError(f"{role}: mods (+{mods[0]}) need a style", file=ctx.song.file, section=sec.name)
    for k, v in steps.items():
        lanes[k] = [v]
    bpb, out = ctx.bpb, []
    nbars = math.ceil(span.bars - 1e-9)
    for bi in range(nbars):
        bar_beat = span.start + bi * bpb
        abs_bar = int(round(span.start_bar + bi))
        active = {k: list(v) for k, v in lanes.items()}
        for every, extra in phrase:
            if abs_bar % every == every - 1:
                for k, v in extra.items():
                    active.setdefault(k, []).append(v)
        rng = np.random.default_rng(seed_for(ctx.song.seed, sec.name, role, bi))
        for lane, specs in active.items():
            patch = patch_src(lane)
            for spec in specs:
                hits, opts = _lane_hits(spec, bi, bpb, f"{sec.name} {role}.{lane}")
                vels = opts.get("vel")
                for k, e in enumerate(hits):
                    b = bar_beat + e.beat
                    if b >= span.end - 1e-9:
                        continue
                    vel = float(vels[k % len(vels)]) if isinstance(vels, list) else e.vel
                    pan = float(opts.get("pan", 0)) + (rng.uniform(-pan_random, pan_random) if pan_random else 0.0)
                    out.append(XEv(role, b, e.dur, (), vel, lane, length=opts.get("len"), pan=pan,
                                   gain_db=gain + float(opts.get("gain_db", 0)), patch=patch,
                                   tags=frozenset(e.tags), section=sec.name))
        for lane, ch in chance.items():
            hits, _ = _lane_hits(ch.get("steps", ""), bi, bpb, f"{sec.name} {role}.{lane}")
            patch = patch_src(lane)
            for e in hits:
                b = bar_beat + e.beat
                if rng.random() < float(ch.get("p", 0.5)) and b < span.end - 1e-9:
                    pan = rng.uniform(-pan_random, pan_random) if pan_random else 0.0
                    out.append(XEv(role, b, e.dur, (), e.vel, lane, pan=pan, gain_db=gain, patch=patch,
                                   tags=frozenset(e.tags | {"chance"}), section=sec.name))
    return out


def _lane_hits(spec, bar_index: int, bpb: float, name: str):
    opts = {}
    if isinstance(spec, dict):
        opts = spec
        spec = spec.get("steps", "")
    segs = [s for s in str(spec).split("|")]
    seg = segs[bar_index % len(segs)]
    try:
        evs, _ = parse_steps(seg, bpb, name)
    except NotationError as e:
        raise SongError(str(e)) from None
    return evs, opts


def _rel_figure(ctx, sec, span, role, style, p_oct, patch) -> list[XEv]:
    try:
        evs = parse_motif(style.get("rel"), rel=True, beats_per_bar=ctx.bpb, name=f"style {style.name}")
    except NotationError as e:
        raise SongError(str(e), file=style.path) from None
    L = _whole_bars(motif_length(evs), ctx.bpb)
    oct_ = int(style.get("oct", 0)) + p_oct
    out, base = [], span.start
    while base < span.end - 1e-9:
        for e in evs:
            b = base + e.beat
            if b >= span.end - 1e-9 or b < span.start - 1e-9:
                continue
            pitches = _resolve_rel(ctx, e, b, oct_)
            if pitches is None:
                continue
            out.append(_from_ev(role, e, b, pitches, sec.name, gate=style.get("gate"), patch=patch,
                                gain_db=float(style.get("gain_db", 0))))
        base += L
    return out


def _hold(ctx, sec, span, role, style, p_oct, patch) -> list[XEv]:
    evs = parse_motif(style.get("rel"), rel=True, beats_per_bar=ctx.bpb, name=f"style {style.name}")
    oct_ = int(style.get("oct", 0)) + p_oct
    out = []
    for h in ctx.harm.changes(span.start, span.end):
        if h.chord is None:
            continue
        root = h.chord.home_root(ctx.tonic) + octaves(oct_)
        for e in evs:
            pitches = tuple(rel_to_midi(t, o, h.chord.intervals, root, ctx.tuning) for t, o in e.rel)
            x = _from_ev(role, e, h.start + e.beat, pitches, sec.name, gate=style.get("gate"), patch=patch,
                         gain_db=float(style.get("gain_db", 0)))
            x.dur = h.end - h.start
            out.append(x)
    return out


def _voicings(ctx: _Ctx, voices: int, lo: float, hi: float) -> dict:
    """Voice-led voicing for every chord change of the song (shared by all parts with the same
    settings, so a `voice: top` melody is exactly the soprano of the `voiced` chords)."""
    from ..theory.voicing import voice_lead
    key = (voices, lo, hi)
    if key not in ctx._voicing_cache:
        out, prev, shifts = {}, None, {}
        for sp in ctx.harm.spans:
            if sp.chord is None:
                prev = None
                continue
            if not sp.onset and prev is not None:
                out[sp.start] = prev
                continue
            if sp.chord.lines is not None and voices in (3, 4):
                # a golden passing path: play the engine's own lines, moved by whole octaves (one shift
                # for the whole run, fixed by its first chord) toward the middle of the part's range
                if sp.chord.run not in shifts:
                    shifts[sp.chord.run] = 12 * round(((lo + hi) / 2 - sum(sp.chord.lines[1:]) / 3) / 12)
                v = tuple(p + shifts[sp.chord.run] for p in sp.chord.lines[4 - voices:])
                out[sp.start] = v
                prev = v
                continue
            v = voice_lead(prev, sp.chord.home_root(ctx.tonic), sp.chord.intervals, lo, hi, voices, ctx.tuning)
            out[sp.start] = v
            prev = v
        ctx._voicing_cache[key] = out
    return ctx._voicing_cache[key]


def _voiced(ctx, sec, span, role, style, spec, p_oct, patch) -> list[XEv]:
    o = {**style.data, **{k: v for k, v in spec.opts.items() if k in ("voices", "range", "rhythm", "voice", "vel")}}
    voices = int(o.get("voices", 4))
    lo, hi = (float(x) for x in o.get("range", [52, 76]))
    rhythm = o.get("rhythm")
    which = o.get("voice", "all")
    vel = float(o.get("vel", 0.62))
    accent = float(style.get("accent", 1.0))
    oct_ = int(style.get("oct", 0)) + p_oct
    vmap = _voicings(ctx, voices, lo, hi)
    out = []
    for sp in ctx.harm.spans:
        if sp.chord is None or sp.end <= span.start + 1e-9 or sp.start >= span.end - 1e-9:
            continue
        v = vmap.get(sp.start)
        if v is None:
            continue
        a, z = max(sp.start, span.start), min(sp.end, span.end)
        if which == "top":
            pitches = (v[-1],)
        elif which == "bottom":
            pitches = (v[0],)
        elif which == "upper":
            pitches = tuple(v[1:])
        elif isinstance(which, int) or str(which).lstrip("-").isdigit():
            pitches = (v[int(which)],)
        else:
            pitches = tuple(v)
        if style.get("bass_note") and abs(sp.chord.bass - sp.chord.root) > 1e-9:
            b = sp.chord.home_root(ctx.tonic) + ((sp.chord.bass - sp.chord.root) % 12) - 12
            pitches = (b,) + pitches
        pitches = tuple(p + octaves(oct_) for p in pitches)
        hits = [a]
        if rhythm:
            bar = str(rhythm).replace(" ", "")
            stepb = ctx.bpb / len(bar)
            t = math.floor((a + 1e-9) / ctx.bpb) * ctx.bpb
            while t < z - 1e-9:
                for i, c in enumerate(bar):
                    hb = t + i * stepb
                    if a + 1e-9 < hb < z - 1e-9 and c not in ".-":
                        hits.append(hb)
                t += ctx.bpb
        hits = sorted(set(round(h, 9) for h in hits))
        for k, h in enumerate(hits):
            end = hits[k + 1] if k + 1 < len(hits) else z
            out.append(XEv(role, h, end - h, pitches, min(1.0, vel * (accent if k == 0 else 1.0)),
                           gate=style.get("gate"), patch=patch, gain_db=float(style.get("gain_db", 0)),
                           section=sec.name))
    return out


def _arp(ctx, sec, span, role, style, spec, p_oct, patch) -> list[XEv]:
    grid = int(style.get("grid", 16))
    order = list(spec.opts.get("order", style.get("order", [0, 1, 2])))
    steps = max(1, round(grid * ctx.bpb / 4))
    step = ctx.bpb / steps
    oct_ = int(style.get("oct", 0)) + p_oct
    length = spec.opts.get("len", style.get("len"))
    lfo = style.get("pan_lfo") or {}
    ramp = style.get("brightness_ramp")
    out = []
    for bi in range(math.ceil(span.bars - 1e-9)):
        abs_bar = int(round(span.start_bar + bi))
        params = {}
        if ramp:
            over = float(ramp.get("over", 8))
            params[ramp.get("param", "cutoff")] = float(ramp["from"]) + (float(ramp["to"]) - float(ramp["from"])) * (
                (abs_bar % over) / over)
        for s in range(steps):
            b = span.start + bi * ctx.bpb + s * step
            if b >= span.end - 1e-9:
                break
            chord = ctx.harm.chord_at(b)
            if chord is None:
                continue
            tones = chord.tones(ctx.tonic)
            idx = int(order[s % len(order)])
            m = tones[idx % len(tones)] + octaves(oct_ + idx // len(tones))
            pan = float(lfo.get("depth", 0)) * math.sin(s * float(lfo.get("rate", 0)))
            out.append(XEv(role, b, step, (m,), 0.62, length=length, pan=pan, params=dict(params), patch=patch,
                           gain_db=float(style.get("gain_db", 0)), section=sec.name))
    return out


def _motifs(ctx, sec, span, role, refs, p_oct) -> list[XEv]:
    mots = [(r, ctx.motif(r, sec.name)) for r in refs]
    lens = [_whole_bars(motif_length(evs), ctx.bpb) for _, evs in mots]
    out = []
    if len(set(lens)) == 1:            # synth_v0: blocks anchored at the song start
        L = lens[0]
        for k in range(int(span.start // L), math.ceil(span.end / L - 1e-9)):
            ref, evs = mots[k % len(mots)]
            for e in evs:
                b = k * L + e.beat
                if span.start - 1e-9 <= b < span.end - 1e-9:
                    pitches = _resolve_rel(ctx, e, b, p_oct)
                    if pitches is not None:
                        out.append(_from_ev(role, e, b, [p + octaves(p_oct) * (not e.rel) for p in pitches], sec.name,
                                            tags=frozenset(e.tags | {f"motif:{ref}"})))
    else:                              # mixed lengths: play them in order from the section start
        base, k = span.start, 0
        while base < span.end - 1e-9:
            ref, evs = mots[k % len(mots)]
            for e in evs:
                b = base + e.beat
                if b < span.end - 1e-9:
                    pitches = _resolve_rel(ctx, e, b, p_oct)
                    if pitches is not None:
                        out.append(_from_ev(role, e, b, [p + octaves(p_oct) * (not e.rel) for p in pitches], sec.name,
                                            tags=frozenset(e.tags | {f"motif:{ref}"})))
            base += lens[k % len(mots)]
            k += 1
    return out


def _inline(ctx, sec, span, role, spec, p_oct) -> list[XEv]:
    try:
        evs = parse_motif(spec.notes, deg=spec.notes_mode == "deg", rel=spec.notes_mode == "rel",
                          key=sec.key or ctx.song.key, octave=int(spec.opts.get("octave", 4)),
                          beats_per_bar=ctx.bpb, name=f"{sec.name} {role}")
    except NotationError as e:
        raise SongError(str(e), file=ctx.song.file, line=sec.line, section=sec.name) from None
    L = _whole_bars(motif_length(evs), ctx.bpb)
    out, base = [], span.start
    while base < span.end - 1e-9:
        for e in evs:
            b = base + e.beat
            if b < span.end - 1e-9:
                pitches = _resolve_rel(ctx, e, b, p_oct)
                if pitches is not None:
                    out.append(_from_ev(role, e, b, [p + octaves(p_oct) * (not e.rel) for p in pitches], sec.name))
        base += L
    return out


def _expand_part(ctx: _Ctx, sec, span: SectionSpan, role: str, spec) -> list[XEv]:
    p_oct = int(spec.opts.get("oct", 0))
    for k in spec.opts:
        if k in LATER_OPTS:
            ctx.warn_once(("opt", k), f"part option '{k}' is parsed; it takes effect in {LATER_OPTS[k]}")
    is_kit = ctx.ens.is_kit(role)
    if spec.style:
        style = get_style(spec.opts.get("role", role), spec.style)
        preset, params = style.get("preset"), style.get("params")
        if style.shape == "kit" or spec.steps:
            if not is_kit:
                raise SongError(f"{role} style '{spec.style}' is a kit pattern but {role} is not a kit",
                                suggestion="give the part a kit under instruments:")
            return _kit(ctx, sec, span, role, style if style.shape == "kit" else None, spec.mods, spec.steps,
                        lambda lane: ctx.ens.patch_for(role, lane, preset, params))
        if spec.mods:
            raise SongError(f"{role} style '{spec.style}' has no mods (+{spec.mods[0]})")
        patch = ctx.ens.patch_for(role, None, preset, params) if not is_kit else ()
        if style.shape == "rel":
            return _rel_figure(ctx, sec, span, role, style, p_oct, patch)
        if style.shape == "hold":
            return _hold(ctx, sec, span, role, style, p_oct, patch)
        if style.shape == "voiced":
            return _voiced(ctx, sec, span, role, style, spec, p_oct, patch)
        return _arp(ctx, sec, span, role, style, spec, p_oct, patch)
    if spec.steps:
        if not is_kit:
            raise SongError(f"{role}: step strings need a kit part", suggestion="use notes: for pitched parts")
        return _kit(ctx, sec, span, role, None, [], spec.steps, lambda lane: ())
    if is_kit:
        raise SongError(f"{role} is a kit: give it a style or step strings")
    if spec.motifs:
        return _motifs(ctx, sec, span, role, spec.motifs, p_oct)
    if spec.notes:
        return _inline(ctx, sec, span, role, spec, p_oct)
    return []


def _apply_opts(evs: list[XEv], spec, sec, span: SectionSpan):
    shapes = [parse_shape(str(s)) for s in (sec.dyn, spec.opts.get("dyn")) if s]
    tr = int(spec.opts.get("transpose", 0))
    gain = float(spec.opts.get("gain_db", 0))
    gate = spec.opts.get("gate")
    art = spec.opts.get("art")
    width = max(span.end - span.start, 1e-9)
    for e in evs:
        for sh in shapes:
            e.vel = float(min(1.0, e.vel * shape_at(sh, (e.beat - span.start) / width) / DYN["mf"]))
        if tr and e.pitches:
            e.pitches = tuple(p + tr for p in e.pitches)
        e.gain_db += gain
        if gate is not None:
            e.gate = float(gate)
        if art and e.art == "normal":
            e.art = str(art)


def expand(song: Song) -> Arrangement:
    from .events import apply_mutes, expand_events
    ctx = _Ctx(song)
    parts: dict[str, list[XEv]] = defaultdict(list)
    for sec, span in zip(song.sections, ctx.tl.sections):
        for role, spec in sec.parts.items():
            if spec.opts.get("mute"):
                continue
            try:
                evs = _expand_part(ctx, sec, span, role, spec)
                _apply_opts(evs, spec, sec, span)
            except NotationError as e:
                raise SongError(str(e), file=song.file, line=sec.line, section=sec.name) from None
            except SongError as e:
                e.file, e.line = e.file or song.file, e.line or sec.line
                e.section = e.section or sec.name
                raise SongError(e.message, file=e.file, line=e.line, section=e.section,
                                suggestion=e.suggestion) from None
            parts[role] += evs
    fx_evs, resolved, mutes = expand_events(ctx)
    for e in fx_evs:
        parts[e.part].append(e)
    apply_mutes(parts, mutes)
    for p in parts:
        parts[p].sort(key=lambda e: (e.beat, e.piece or "", e.pitches))
    _check_grid(song, ctx, parts)
    return Arrangement(song, ctx.tl, ctx.harm, ctx.ens, dict(parts), resolved, ctx.warnings)


def _check_grid(song: Song, ctx: "_Ctx", parts) -> None:
    """Every pitch must sit on the song's tuning grid; microtones need `tuning: 36edo`."""
    for sp in ctx.harm.spans:
        c = sp.chord
        if c is not None and not all(on_grid(c.root + i, ctx.tuning) for i in (0, *c.intervals)):
            raise SongError(f"chord {c.symbol} at beat {sp.start:g} is off the {ctx.tuning.name} grid",
                            file=song.file, suggestion="golden/silver chords, sixth-step roots and alterations "
                                                       "need `tuning: 36edo`")
    for role, evs in parts.items():
        for e in evs:
            for m in e.pitches:
                if not on_grid(m, ctx.tuning):
                    raise SongError(f"part {role}: pitch {m:.3f} at beat {e.beat:g} is off the {ctx.tuning.name} grid",
                                    file=song.file, section=e.section,
                                    suggestion="sixth-step accidentals (^ v), golden/silver chords and golden "
                                               "scales need `tuning: 36edo`")
