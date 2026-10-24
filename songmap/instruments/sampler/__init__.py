"""Sampler: SFZ-subset sample playback behind the ordinary Instrument contract (INSTRUMENTS.md §5.1).

`make('sampler/salamander')` finds the library on disk (library.py), parses its program (sfz.py)
and returns a `Sampler`. A song swaps `keys` for `sampler/salamander` with no other change.

Per note:
- choose the attack regions by key (round(pitch)), velocity and round-robin slot (`Note.rr`);
- crossfade adjacent velocity layers (equal power, width = `xfade`);
- repitch each sample from the exact float MIDI pitch (any tuning; resample.py);
- apply the amp envelope (ampeg_attack, then ampeg_release from the gate);
- add the `trigger=release` samples at note-off.
`group`/`off_by` chokes are applied by the engine across notes (`choke()`; render.py).
Also supports explicit velocity fades, random groups, sample offsets, decay/sustain and explicit loops.
Not in the subset: live MIDI CC/pedals, filters, LFOs, pitch/filter EGs and keyswitches.
"""
from __future__ import annotations

import os
from functools import lru_cache

import numpy as np

from ..base import A, P, V, Instrument, Note, Param
from ..dsp import SR, mtof, n_samples, undb
from ...parse.errors import SongError
from . import library, sfz
from .resample import ZEROS, repitch

ATTACK_MIN = 0.001     # s: never start a sample without a ramp (no clicks)
RELEASE_MIN = 0.005    # s
END_FADE = 0.002       # s: when a sample runs out before its envelope ends
RELEASE_SAMPLE_MAX = 8.0


@lru_cache(maxsize=None)
def _program(path: str, mtime: float) -> sfz.Program:
    return sfz.parse(path)


def load(name: str, **params) -> "Sampler":
    library.soundfile()                     # fail at load time, not mid-render
    path = library.find(name)
    defaults = library.manifest()["voices"].get(name, {}).get("params", {})
    program = _program(path, os.path.getmtime(path))
    missing = next((r.sample for r in program.regions if not os.path.isfile(r.sample)), None)
    if missing:
        raise SongError(f"sampler/{name}: missing sample {missing}",
                        suggestion=f"run songmap samples install {name}" if name in library.manifest()["voices"]
                        else "check that the complete sample library is unpacked")
    return Sampler(name, program, **{**defaults, **params})


def _ramp(n: int) -> np.ndarray:
    return 0.5 - 0.5 * np.cos(np.pi * np.arange(n) / max(n, 1))


def _apply(y: np.ndarray, gain: np.ndarray) -> np.ndarray:
    return y * gain[:, None] if y.ndim == 2 else y * gain


class Sampler(Instrument):
    """SFZ-subset sample player. `library` names the program; knobs adjust it."""
    name, family = "sampler", "keys"
    PARAMS = (
        Param("level", 0.0, -36, 12, "dB", "lin", A, "output level"),
        Param("tune", 0.0, -100, 100, "cents", "lin", P, "fine tune on top of the program's tune"),
        Param("xfade", 0.5, 0, 1, "", "lin", V, "automatic velocity-zone blend width (explicit SFZ fades still apply)"),
        Param("attack", 0.0, 0, 2, "s", "lin", A, "added to the region's ampeg_attack"),
        Param("release_mul", 1.0, 0.05, 8, "x", "log", A, "scales the region's ampeg_release"),
        Param("release_level", 1.0, 0, 2, "", "lin", A, "trigger=release sample level (0 = off)"),
    )

    def __init__(self, library_name: str = "", program: sfz.Program | None = None, **values):
        super().__init__(**values)
        self.library = library_name
        self.program = program
        known = library.CATALOG.get(library_name.partition("/")[0])
        if known:
            self.family = known.family
        voice = library.manifest()["voices"].get(library_name)
        self.fixed_pitch = None
        if voice:
            self.family = voice["family"]
            if self.family == "drum":
                self.fixed_pitch = voice.get("audition_pitch", 60)
        self.warnings = ([f"sampler/{library_name}: ignoring SFZ features outside the subset: "
                          + " ".join(sorted(program.unsupported))] if program and program.unsupported else [])

    @classmethod
    def from_sfz(cls, path: str, **values) -> "Sampler":
        path = os.path.abspath(path)
        return cls(os.path.splitext(os.path.basename(path))[0], _program(path, os.path.getmtime(path)), **values)

    @property
    def source(self) -> dict:
        return library.license_entry(self.library, self.program.path)

    # --- region choice ------------------------------------------------------------
    def regions(self, note: Note, release: bool = False) -> list[tuple[sfz.Region, float]]:
        """The regions this note plays, each with its velocity-crossfade weight."""
        pitch = note.pitch if self.fixed_pitch is None else self.fixed_pitch
        key = int(np.clip(round(pitch), 0, 127))
        v = float(np.clip(note.vel * 127.0, 1.0, 127.0))
        draw = self.rng(note).random()
        cand = [r for r in self.program.regions
                if r.is_release == release and r.lokey <= key <= r.hikey
                and r.lorand <= draw < r.hirand
                and note.rr % max(r.seq_length, 1) + 1 == r.seq_position]
        explicit = any(r.xfin_hivel > r.xfin_lovel or r.xfout_hivel > r.xfout_lovel for r in cand)
        if explicit:
            result = []
            for r in cand:
                if not r.lovel <= round(v) <= r.hivel:
                    continue
                fade_in = np.clip((v-r.xfin_lovel)/(r.xfin_hivel-r.xfin_lovel), 0, 1) if r.xfin_hivel > r.xfin_lovel else 1
                fade_out = np.clip((r.xfout_hivel-v)/(r.xfout_hivel-r.xfout_lovel), 0, 1) if r.xfout_hivel > r.xfout_lovel else 1
                weight = float(np.sin(fade_in*np.pi/2) * np.sin(fade_out*np.pi/2))
                if weight > 1e-6:
                    result.append((r, weight))
            return result
        layers = sorted({(r.lovel, r.hivel) for r in cand})
        disjoint = all(a[1] < b[0] for a, b in zip(layers, layers[1:]))
        if not disjoint:      # overlapping layers (e.g. a full-range noise layer): plain SFZ matching
            vi = int(round(v))
            return [(r, 1.0) for r in cand if r.lovel <= vi <= r.hivel]
        w = self._layer_weights(layers, v, self.p_(note, "xfade"))
        return [(r, w[(r.lovel, r.hivel)]) for r in cand if w.get((r.lovel, r.hivel), 0.0) > 1e-6]

    @staticmethod
    def _layer_weights(layers, v: float, xfade: float) -> dict:
        w = {L: 1.0 for L in layers if L[0] - 0.5 <= v < L[1] + 0.5}
        for lo, hi in zip(layers, layers[1:]):
            if hi[0] - lo[1] > 1:            # a gap between layers: no blend across it
                continue
            b = (lo[1] + hi[0]) / 2.0
            h = xfade * min(b - (lo[0] + lo[1]) / 2.0, (hi[0] + hi[1]) / 2.0 - b)
            if h > 0 and abs(v - b) < h:
                t = (v - b + h) / (2.0 * h)
                return {lo: float(np.cos(t * np.pi / 2)), hi: float(np.sin(t * np.pi / 2))}
        return w

    def choke(self, note: Note) -> tuple[int, int]:
        """(group, off_by) of the note's main region; the engine cuts this note when a later note
        of group `off_by` starts in the same part. (0, 0) = no choke."""
        rs = self.regions(note)
        if not rs:
            return 0, 0
        r = max(rs, key=lambda x: x[1])[0]
        return r.group, r.off_by

    def tail(self, note: Note) -> float:
        rs = self.regions(note)
        rel = max((r.ampeg_release for r, _ in rs), default=0.0)
        return max(rel * self.p_(note, "release_mul"), RELEASE_MIN)

    # --- rendering -----------------------------------------------------------------
    def _ratio(self, r: sfz.Region, note: Note) -> float:
        pitch = note.pitch if self.fixed_pitch is None else self.fixed_pitch
        shift = (pitch - r.pitch_keycenter) * r.pitch_keytrack / 100.0 + (r.tune + self.p_(note, "tune")) / 100.0
        return float(mtof(r.pitch_keycenter + shift) / mtof(r.pitch_keycenter)) * library.SAMPLES.rate(r.sample) / SR

    def _gain(self, r: sfz.Region, note: Note, weight: float) -> float:
        c = float(np.clip(note.vel, 1 / 127, 1.0)) ** 2           # SFZ default velocity curve
        if r.amp_velcurve:
            points = sorted({0: 0.0, 127: 1.0, **r.amp_velcurve}.items())
            c = float(np.interp(np.clip(note.vel * 127, 1, 127),
                                [p[0] for p in points], [p[1] for p in points]))
        vt = r.amp_veltrack / 100.0
        g = 1.0 - vt * (1.0 - c) if vt >= 0 else 1.0 + vt * c
        return float(undb(r.volume + self.p_(note, "level"))) * max(g, 0.0) * weight

    def _read(self, r: sfz.Region, note: Note, n_out: int, n_gate: int | None = None) -> tuple[np.ndarray, bool]:
        """The region's sample repitched to note.pitch, at most n_out samples; and whether it ran out."""
        ratio = self._ratio(r, note)
        needed = int(np.ceil(n_out * ratio)) + 4 * ZEROS + 2
        looping = r.loop_mode in ("loop_sustain", "loop_continuous")
        x, _ = library.SAMPLES.get(r.sample, max(r.offset + needed, r.loop_end + 2) if looping else r.offset + needed)
        if looping:
            if r.loop_end >= len(x) or r.offset > r.loop_end:
                raise ValueError(f"sampler: loop points outside sample {r.sample}")
            pos = np.arange(needed, dtype=np.int64) + r.offset
            wrapped = pos > r.loop_end
            pos[wrapped] = r.loop_start + (pos[wrapped] - r.loop_start) % (r.loop_end-r.loop_start+1)
            if r.loop_mode == "loop_sustain" and n_gate is not None:
                stop = min(needed, int(np.ceil(n_gate*ratio)))
                if stop:
                    pos[stop:] = pos[stop-1] + 1 + np.arange(needed-stop)
            valid = pos < len(x)
            virtual = np.zeros((needed, x.shape[1]), dtype=x.dtype)
            virtual[valid] = x[pos[valid]]
            avail = int(np.flatnonzero(~valid)[0] / ratio) if not np.all(valid) else n_out
            n = max(1, min(n_out, avail))
            return repitch(virtual, ratio, n), n < n_out
        x = x[r.offset:]
        if len(x) < 2:
            return np.zeros((1, x.shape[1])), True
        avail = int((len(x) - 1) / ratio)
        n = max(1, min(n_out, avail))
        return repitch(x, ratio, n), n < n_out

    def _envelope(self, n: int, n_gate: int, att: float, rel: float, ran_out: bool,
                  decay: float = 0.0, sustain: float = 100.0) -> np.ndarray:
        env = np.ones(n)
        na = min(n_samples(max(att, ATTACK_MIN)), n)
        env[:na] = _ramp(na)                    # raised cosine from 0: smoother than SFZ's linear ramp
        if sustain != 100:
            nd = max(1, n_samples(decay))
            env[na:] = sustain/100 + (1-sustain/100)*np.clip(1-np.arange(n-na)/nd, 0, 1)
        if n_gate < n:
            nr = n - n_gate
            x = np.arange(nr) / max(n_samples(rel), 1)
            level = env[n_gate - 1] if n_gate > 0 else 0.0
            env[n_gate:] = level * np.exp(-6.9 * x) * np.clip(1.0 - x, 0.0, 1.0)
        if ran_out:
            nf = min(n_samples(END_FADE), n)
            env[n - nf:] *= _ramp(nf)[::-1]
        return env

    def render(self, note: Note) -> np.ndarray:
        if self.program is None:
            raise ValueError("sampler: no program loaded; use make('sampler/<library>')")
        n_gate = n_samples(note.gate)
        parts = []
        for r, w in self.regions(note):
            rel = max(r.ampeg_release * self.p_(note, "release_mul"), RELEASE_MIN)
            gate = n_gate
            n_out = gate + n_samples(rel)
            if r.loop_mode == "one_shot":
                x, _ = library.SAMPLES.get(r.sample, 0)
                n_out = max(1, int((len(x)-r.offset-1) / self._ratio(r, note)))
                gate = n_out
            y, ran_out = self._read(r, note, n_out, gate)
            env = self._envelope(len(y), gate, r.ampeg_attack + self.p_(note, "attack"), rel, ran_out or r.loop_mode == "one_shot",
                                 r.ampeg_decay, r.ampeg_sustain)
            parts.append((0, self._pan(_apply(y, env * self._gain(r, note, w)), r.pan)))
        level = self.p_(note, "release_level")
        if level > 0:
            for r, w in self.regions(note, release=True):
                y, ran_out = self._read(r, note, n_samples(RELEASE_SAMPLE_MAX))
                env = self._envelope(len(y), len(y), r.ampeg_attack, RELEASE_MIN, True)
                g = self._gain(r, note, w) * level * float(undb(-r.rt_decay * note.gate))
                parts.append((n_gate, self._pan(_apply(y, env * g), r.pan)))
        if not parts:
            return np.zeros(n_gate)
        stereo = any(y.ndim == 2 and y.shape[1] > 1 for _, y in parts)
        n = max(o + len(y) for o, y in parts)
        out = np.zeros((n, 2)) if stereo else np.zeros(n)
        for o, y in parts:
            if stereo and y.ndim == 1:
                y = np.stack([y, y], 1)
            elif stereo and y.shape[1] == 1:
                y = np.repeat(y, 2, 1)
            elif not stereo and y.ndim == 2:
                y = y[:, 0]
            out[o:o + len(y)] += y
        return out

    @staticmethod
    def _pan(y: np.ndarray, position: float) -> np.ndarray:
        if not position:
            return y
        from ..dsp import pan_mono
        pan = float(np.clip(position / 100, -1, 1))
        if y.ndim == 1 or y.shape[1] == 1:
            return pan_mono(y.reshape(-1), pan)
        return y * np.array([1 - max(pan, 0), 1 + min(pan, 0)])
