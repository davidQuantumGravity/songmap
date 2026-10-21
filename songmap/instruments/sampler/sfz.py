"""SFZ subset parser (INSTRUMENTS.md §5.1): headers, opcodes, inheritance, #define/#include.

Headers cascade the usual way: <control> < <global> < <master> < <group> < <region>, and a new
header clears the levels below it. Opcodes outside the subset are kept in `Region.extra` and
listed in `Program.unsupported`, so a library that needs them can say so instead of sounding wrong.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from ...parse.errors import SongError

# The subset. amp_veltrack, pitch_keytrack and rt_decay are cheap extras that real piano
# libraries (Salamander) rely on; key= is the SFZ shorthand for lokey=hikey=pitch_keycenter.
SUPPORTED = {"sample", "lokey", "hikey", "key", "pitch_keycenter", "lovel", "hivel",
             "seq_length", "seq_position", "trigger", "ampeg_attack", "ampeg_release",
             "tune", "volume", "group", "off_by", "amp_veltrack", "pitch_keytrack", "rt_decay",
             "default_path"}
LEVELS = ("control", "global", "master", "group", "region")

# SFZ note names are MIDI key numbers by the format's spec (c4 = 60), not tuning math.
_NOTE = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
_NOTE_RE = re.compile(r"^([a-gA-G])([#b]?)(-?\d+)$")
_OPCODE_RE = re.compile(r"([A-Za-z0-9_]+)=")


def note_number(value: str) -> int:
    v = value.strip()
    try:
        return int(float(v))
    except ValueError:
        m = _NOTE_RE.match(v)
        if not m:
            raise ValueError(f"not a key: '{value}'") from None
        acc = {"#": 1, "b": -1}.get(m.group(2), 0)
        return (int(m.group(3)) + 1) * 12 + _NOTE[m.group(1).lower()] + acc


@dataclass
class Region:
    sample: str                      # absolute path
    lokey: int = 0
    hikey: int = 127
    pitch_keycenter: int = 60
    lovel: int = 1
    hivel: int = 127
    seq_length: int = 1
    seq_position: int = 1
    trigger: str = "attack"          # attack | release (first/legato are played as attack)
    ampeg_attack: float = 0.0
    ampeg_release: float = 0.001
    tune: float = 0.0                # cents
    volume: float = 0.0              # dB
    group: int = 0
    off_by: int = 0                  # 0 = never choked
    amp_veltrack: float = 100.0      # %
    pitch_keytrack: float = 100.0    # cents per key
    rt_decay: float = 0.0            # dB per second the key was held (release samples)
    extra: dict = field(default_factory=dict)

    @property
    def is_release(self) -> bool:
        return self.trigger == "release"

    def covers(self, key: int, vel: float) -> bool:
        return self.lokey <= key <= self.hikey and self.lovel <= vel <= self.hivel


@dataclass
class Program:
    path: str
    regions: list[Region]
    unsupported: set[str] = field(default_factory=set)


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def _expand(path: str, defines: dict, depth: int = 0) -> str:
    """Read a file, applying #define and #include (relative to the including file)."""
    if depth > 8:
        raise SongError(f"sfz {path}: #include nested too deeply")
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = _strip_comments(f.read())
    except OSError as e:
        raise SongError(f"sfz: cannot read {path}: {e.strerror}") from None
    out = []
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r'#define\s+(\$\w+)\s+(.*)$', s)
        if m:
            defines[m.group(1)] = m.group(2).strip()
            continue
        for k in sorted(defines, key=len, reverse=True):
            line = line.replace(k, defines[k])
        m = re.match(r'\s*#include\s+"([^"]+)"', line)
        if m:
            inc = os.path.join(os.path.dirname(path), m.group(1).replace("\\", "/"))
            out.append(_expand(inc, defines, depth + 1))
            continue
        out.append(line)
    return "\n".join(out)


def _opcodes(chunk: str) -> list[tuple[str, str]]:
    """'a=1 sample=My Piano/C4.wav b=2' -> pairs; values may contain spaces (sample paths)."""
    marks = list(_OPCODE_RE.finditer(chunk))
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(chunk)
        out.append((m.group(1), chunk[m.end():end].strip()))
    return out


def parse(path: str) -> Program:
    path = os.path.abspath(path)
    text = _expand(path, {})
    root = os.path.dirname(path)
    scopes: dict[str, dict] = {lv: {} for lv in LEVELS}
    regions: list[Region] = []
    unsupported: set[str] = set()
    current = None

    def flush():
        if current != "region":
            return
        ops = {}
        for lv in LEVELS:
            ops.update(scopes[lv])
        if "sample" not in ops:
            return
        regions.append(_region(ops, root, path, unsupported))

    for tok in re.split(r"(<\w+>)", text):
        h = re.fullmatch(r"<(\w+)>", tok)
        if h:
            flush()
            current = h.group(1).lower()
            if current in LEVELS:
                for lv in LEVELS[LEVELS.index(current):]:
                    scopes[lv] = {}
            else:
                unsupported.add(f"<{current}>")
            continue
        if current in LEVELS:
            scopes[current].update(_opcodes(tok))
    flush()
    if not regions:
        raise SongError(f"sfz {path}: no <region> with a sample")
    return Program(path, regions, unsupported)


def _region(ops: dict, root: str, path: str, unsupported: set) -> Region:
    base = os.path.join(root, ops.get("default_path", "").replace("\\", "/"))
    r = Region(sample=os.path.normpath(os.path.join(base, ops["sample"].replace("\\", "/"))))
    try:
        if "key" in ops:
            r.lokey = r.hikey = r.pitch_keycenter = note_number(ops["key"])
        for k in ("lokey", "hikey", "pitch_keycenter"):
            if k in ops:
                setattr(r, k, note_number(ops[k]))
        for k in ("lovel", "hivel", "seq_length", "seq_position", "group", "off_by"):
            if k in ops:
                setattr(r, k, int(float(ops[k])))
        for k in ("ampeg_attack", "ampeg_release", "tune", "volume", "amp_veltrack",
                  "pitch_keytrack", "rt_decay"):
            if k in ops:
                setattr(r, k, float(ops[k]))
    except ValueError as e:
        raise SongError(f"sfz {path}: region {ops.get('sample')}: {e}") from None
    r.trigger = ops.get("trigger", "attack").lower()
    r.extra = {k: v for k, v in ops.items() if k not in SUPPORTED}
    unsupported.update(r.extra)
    return r
