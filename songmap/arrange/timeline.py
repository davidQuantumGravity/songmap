"""Tempo map: beats <-> seconds <-> frames, and section spans.

Tempo is piecewise constant (a number per section, defaulting to the song tempo). Ramps
(`rit`/`accel`) arrive with P9. Every position resolves to absolute beats.
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass

from ..parse.errors import SongError, did_you_mean


@dataclass(frozen=True)
class SectionSpan:
    name: str
    index: int
    start_bar: float
    bars: float
    start: float          # beats
    end: float            # beats


class Timeline:
    def __init__(self, song):
        self.song = song
        self.fps = song.fps
        self.bpb = song.beats_per_bar
        self.sections: list[SectionSpan] = []
        self._tempo: list[tuple[float, float, float]] = []    # (start beat, bpm, start seconds)
        beat, bar, t = 0.0, 0.0, 0.0
        for i, s in enumerate(song.sections):
            bpm = song.tempo if s.tempo is None else s.tempo
            if isinstance(bpm, bool) or not isinstance(bpm, (int, float)) or bpm <= 0:
                raise SongError(f"tempo '{bpm}' is not supported yet (rit/accel ramps arrive in P9)",
                                file=song.file, line=s.line, section=s.name, suggestion="use a number of BPM")
            if not self._tempo or self._tempo[-1][1] != bpm:
                self._tempo.append((beat, float(bpm), t))
            length = s.bars * self.bpb
            self.sections.append(SectionSpan(s.name, i, bar, s.bars, beat, beat + length))
            t += length * 60.0 / bpm
            beat += length
            bar += s.bars
        if not self._tempo:
            self._tempo.append((0.0, float(song.tempo), 0.0))
        self.total_beats = beat
        self.total_bars = bar
        self._tb = [x[0] for x in self._tempo]
        self._ts = [x[2] for x in self._tempo]

    # --- conversions --------------------------------------------------------
    def _seg(self, keys, x):
        return self._tempo[max(bisect_right(keys, x + 1e-12) - 1, 0)]

    def bpm_at(self, beat: float) -> float:
        return self._seg(self._tb, beat)[1]

    def spb(self, beat: float = 0.0) -> float:
        """Seconds per beat at `beat`."""
        return 60.0 / self.bpm_at(beat)

    def beat_to_sec(self, beat: float) -> float:
        b0, bpm, t0 = self._seg(self._tb, beat)
        return t0 + (beat - b0) * 60.0 / bpm

    def sec_to_beat(self, t: float) -> float:
        b0, bpm, t0 = self._seg(self._ts, t)
        return b0 + (t - t0) * bpm / 60.0

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
        """True when every beat lands on a whole video frame (60*fps/tempo is an integer)."""
        return all(abs(60 * self.fps / bpm - round(60 * self.fps / bpm)) < 1e-9 for _, bpm, _ in self._tempo)
