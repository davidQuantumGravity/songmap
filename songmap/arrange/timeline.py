"""Tempo map: beats <-> seconds <-> frames, and section spans.

Each section has a constant tempo (a number, defaulting to the song tempo) or a linear ramp
across the section: `rit 120>96`, `accel 90>120` or just `120>96` (BPM changes linearly with
beats). Seconds are the exact integral of 60/bpm, so frames and cues stay exact on a ramp.
Every position resolves to absolute beats.
"""
from __future__ import annotations

import math
import re
from bisect import bisect_right
from dataclasses import dataclass

from ..parse.errors import SongError, did_you_mean

_RAMP = re.compile(r"\s*(?:(rit|accel)\s*)?(\d+(?:\.\d+)?)\s*>\s*(\d+(?:\.\d+)?)\s*")


@dataclass(frozen=True)
class SectionSpan:
    name: str
    index: int
    start_bar: float
    bars: float
    start: float          # beats
    end: float            # beats


@dataclass(frozen=True)
class _Seg:
    b0: float             # start beat
    b1: float             # end beat
    bpm0: float
    bpm1: float           # == bpm0 for a constant tempo
    t0: float             # start seconds

    def bpm(self, b: float) -> float:
        if self.bpm1 == self.bpm0 or self.b1 <= self.b0:
            return self.bpm0
        return self.bpm0 + (self.bpm1 - self.bpm0) * (b - self.b0) / (self.b1 - self.b0)

    def sec(self, b: float) -> float:
        x = b - self.b0
        if self.bpm1 == self.bpm0:
            return self.t0 + x * 60.0 / self.bpm0
        k = (self.bpm1 - self.bpm0) / (self.b1 - self.b0)          # bpm per beat
        return self.t0 + 60.0 / k * math.log((self.bpm0 + k * x) / self.bpm0)

    def beat(self, t: float) -> float:
        dt = t - self.t0
        if self.bpm1 == self.bpm0:
            return self.b0 + dt * self.bpm0 / 60.0
        k = (self.bpm1 - self.bpm0) / (self.b1 - self.b0)
        return self.b0 + self.bpm0 / k * (math.exp(k * dt / 60.0) - 1)

    @property
    def t1(self) -> float:
        return self.sec(self.b1)


def parse_tempo(value, song, sec) -> tuple[float, float]:
    """A section tempo -> (start bpm, end bpm)."""
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
        return float(value), float(value)
    m = _RAMP.fullmatch(str(value)) if isinstance(value, str) else None
    if m and float(m[2]) > 0 and float(m[3]) > 0:
        a, b = float(m[2]), float(m[3])
        if (m[1] == "rit" and b > a) or (m[1] == "accel" and b < a):
            raise SongError(f"tempo '{value}': {m[1]} goes {'down' if m[1] == 'rit' else 'up'}", file=song.file,
                            line=sec.line, section=sec.name, suggestion=f"write {m[1]} {b:g}>{a:g}")
        return a, b
    raise SongError(f"tempo '{value}' not understood", file=song.file, line=sec.line, section=sec.name,
                    suggestion="write a BPM (90) or a ramp across the section: rit 120>96, accel 90>120")


class Timeline:
    def __init__(self, song):
        self.song = song
        self.fps = song.fps
        self.bpb = song.beats_per_bar
        self.sections: list[SectionSpan] = []
        self._segs: list[_Seg] = []
        beat, bar, t = 0.0, 0.0, 0.0
        for i, s in enumerate(song.sections):
            a, b = parse_tempo(song.tempo if s.tempo is None else s.tempo, song, s)
            length = s.bars * self.bpb
            self.sections.append(SectionSpan(s.name, i, bar, s.bars, beat, beat + length))
            if length > 0:
                last = self._segs[-1] if self._segs else None
                if last and last.bpm0 == last.bpm1 == a == b:
                    self._segs[-1] = _Seg(last.b0, beat + length, a, a, last.t0)      # merge equal tempos
                else:
                    self._segs.append(_Seg(beat, beat + length, a, b, t))
                t = self._segs[-1].t1
            beat += length
            bar += s.bars
        if not self._segs:
            self._segs.append(_Seg(0.0, 0.0, float(song.tempo), float(song.tempo), 0.0))
        self.total_beats = beat
        self.total_bars = bar
        self._tb = [s.b0 for s in self._segs]
        self._ts = [s.t0 for s in self._segs]

    # --- conversions --------------------------------------------------------
    def _seg_beat(self, beat: float) -> _Seg:
        return self._segs[max(bisect_right(self._tb, beat + 1e-12) - 1, 0)]

    def bpm_at(self, beat: float) -> float:
        s = self._seg_beat(beat)
        return s.bpm(min(beat, s.b1)) if beat >= s.b0 else s.bpm0

    def spb(self, beat: float = 0.0) -> float:
        """Seconds per beat at `beat`."""
        return 60.0 / self.bpm_at(beat)

    def beat_to_sec(self, beat: float) -> float:
        s = self._seg_beat(beat)
        if beat <= s.b1 or s is not self._segs[-1]:
            return s.sec(beat) if beat >= s.b0 else s.t0 + (beat - s.b0) * 60.0 / s.bpm0
        return s.t1 + (beat - s.b1) * 60.0 / s.bpm1          # after the last section: hold the end tempo

    def sec_to_beat(self, t: float) -> float:
        s = self._segs[max(bisect_right(self._ts, t + 1e-12) - 1, 0)]
        if t < s.t0:
            return s.b0 + (t - s.t0) * s.bpm0 / 60.0
        if s is self._segs[-1] and t > s.t1:
            return s.b1 + (t - s.t1) * s.bpm1 / 60.0
        return s.beat(t)

    def sec_to_frame(self, t: float) -> int:
        return int(round(t * self.fps))

    def beat_to_frame(self, beat: float) -> int:
        return self.sec_to_frame(self.beat_to_sec(beat))

    def frame_to_beat(self, frame: float) -> float:
        return self.sec_to_beat(frame / self.fps)

    def bar_to_beat(self, bar: float) -> float:
        return bar * self.bpb

    # --- song extents ---------------------------------------------------------
    @property
    def music_seconds(self) -> float:
        return self.beat_to_sec(self.total_beats)

    @property
    def seconds(self) -> float:
        return self.music_seconds + self.song.tail_seconds

    @property
    def frames(self) -> int:
        return self.sec_to_frame(self.seconds)

    def section(self, name: str) -> SectionSpan:
        for s in self.sections:
            if s.name == name:
                return s
        raise SongError(f"unknown section '{name}'", file=self.song.file,
                        suggestion=did_you_mean(name, [s.name for s in self.sections]))

    def section_at(self, beat: float) -> SectionSpan | None:
        for s in self.sections:
            if s.start - 1e-9 <= beat < s.end - 1e-9:
                return s
        return None

    def whole_frame_beats(self) -> bool:
        """True when every beat lands on a whole video frame (60*fps/tempo is an integer, no ramps)."""
        return all(s.bpm0 == s.bpm1 and abs(60 * self.fps / s.bpm0 - round(60 * self.fps / s.bpm0)) < 1e-9
                   for s in self._segs)
