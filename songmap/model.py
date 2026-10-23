"""The song tree: what a song map means, independent of its spelling (YAML or compact)."""
from __future__ import annotations

from dataclasses import dataclass, field

from .parse.errors import SongError

# Default parts every song has (SONGMAP_SPEC §2). Drums and fx are kits (several pieces).
DEFAULT_PARTS = ("drums", "bass", "pad", "arp", "lead", "fx")
KIT_ROLES = ("drums", "fx")


@dataclass
class Motif:
    name: str
    text: str
    mode: str = "letter"          # letter | deg | rel
    octave: int = 4
    key: str | None = None        # deg mode: overrides the song key
    line: int | None = None


@dataclass
class PartSpec:
    """One part in one section. Exactly one source: style, motifs, notes (letter/deg/rel) or steps."""
    role: str
    style: str | None = None
    mods: list[str] = field(default_factory=list)
    motifs: list[str] = field(default_factory=list)
    notes: str | None = None
    notes_mode: str = "letter"    # letter | deg | rel (for inline `notes`/`deg`/`rel`)
    steps: dict[str, str] = field(default_factory=dict)
    opts: dict = field(default_factory=dict)    # dyn art oct transpose gain_db gate order mute feel voicing auto ...
    # per-bar variants: (bar offsets from the section start, PartSpec). In those bars the variant's
    # notes replace this spec's (notes are kept by the bar they start in); see expand._vary
    variants: list = field(default_factory=list)

    def source(self) -> str:
        return ("style" if self.style else "motifs" if self.motifs else "notes" if self.notes
                else "steps" if self.steps else "none")


@dataclass
class Section:
    name: str
    bars: float
    parts: dict[str, PartSpec] = field(default_factory=dict)
    harmony: str | None = None    # named progression or inline "Em:2 C:2"
    dyn: str | None = None
    feel: dict = field(default_factory=dict)
    tempo: float | None = None
    key: str | None = None
    meter: tuple | None = None    # (num, den) or (num, den, (groups...)), e.g. (7, 8, (2, 2, 3)); None = the song's
    binaural: dict = field(default_factory=dict)   # {beat, carriers, gain_db} (mix/binaural.py); carries over
    line: int | None = None


@dataclass
class EventSpec:
    type: str
    at: object                    # position (int bar, "name+8:2", "f3960", "cue:x", ...)
    params: dict = field(default_factory=dict)
    line: int | None = None


@dataclass
class HarmonySpec:
    default: list[str] = field(default_factory=list)
    chord_bars: float = 1.0
    progressions: dict[str, str] = field(default_factory=dict)
    voicing: dict = field(default_factory=dict)


@dataclass
class MasterSpec:
    mode: str = "standard"        # standard | legacy (synth_v0: normalize + tanh) | clean (peak-normalize only)
    target_lufs: float = -14.0
    ceiling_db: float = -1.0
    glue: str = "gentle"          # none | gentle | punchy
    preserve_contrast: float | None = None


@dataclass
class Song:
    title: str = "untitled"
    version: str = "0.2"
    tempo: float = 120.0
    meter: tuple[int, int] = (4, 4)
    key: str = "C major"
    tuning: str = "12edo"         # pitch grid (theory/tuning.py); 36edo arrives with P10
    fps: int = 30
    seed: int = 7
    tail_seconds: float = 3.0
    mood: str | None = None
    video: dict = field(default_factory=dict)
    instruments: dict = field(default_factory=dict)   # part -> {"use", params...} or {"kit": {piece: {...}}}
    groove: dict = field(default_factory=dict)
    parts_feel: dict = field(default_factory=dict)
    harmony: HarmonySpec = field(default_factory=HarmonySpec)
    motifs: dict[str, Motif] = field(default_factory=dict)
    sections: list[Section] = field(default_factory=list)
    events: list[EventSpec] = field(default_factory=list)
    cues: dict[str, object] = field(default_factory=dict)
    mix: dict = field(default_factory=dict)            # part -> {gain_db, pan, send, sidechain, ...}
    returns: dict = field(default_factory=dict)        # name -> {type, seconds, ...}
    patches: dict = field(default_factory=dict)        # name -> {modules: {...}, wires: [...]} (instruments/patch.py)
    master: MasterSpec = field(default_factory=MasterSpec)
    qa: dict = field(default_factory=dict)
    binaural: dict = field(default_factory=dict)       # a binaural-beat layer (mix/binaural.py); {} = none
    file: str | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def beats_per_bar(self) -> float:
        """Bar length in quarter-note beats (4/4 -> 4, 6/8 -> 3)."""
        num, den = self.meter
        return num * 4 / den

    def section_bpb(self, sec: "Section") -> float:
        """A section's bar length in quarter-note beats: its own `meter` or the song's."""
        if sec.meter is None:
            return self.beats_per_bar
        return sec.meter[0] * 4 / sec.meter[1]

    @property
    def bars(self) -> float:
        return sum(s.bars for s in self.sections)

    def section(self, name: str) -> Section:
        for s in self.sections:
            if s.name == name:
                return s
        from .parse.errors import did_you_mean
        raise SongError(f"unknown section '{name}'", file=self.file,
                        suggestion=did_you_mean(name, [s.name for s in self.sections]))

    def parts(self) -> list[str]:
        """Every part used anywhere, default parts first."""
        used = {p for s in self.sections for p in s.parts}
        used |= {"fx"} if self.events else set()
        return [p for p in DEFAULT_PARTS if p in used] + sorted(used - set(DEFAULT_PARTS))
