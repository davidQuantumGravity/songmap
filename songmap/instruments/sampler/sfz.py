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
             "default_path", "offset", "ampeg_decay", "ampeg_sustain", "xfin_lovel", "xfin_hivel",
             "xfout_lovel", "xfout_hivel", "lorand", "hirand", "loop_mode", "loop_start", "loop_end",
             "group_label", "ampeg_dynamic", "pan", "lochan", "hichan", "bend_up", "bend_down",
             "off_mode", "offby"}
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
    pan: float = 0.0                # -100..100, SFZ stereo position
    amp_velcurve: dict[int, float] = field(default_factory=dict)
    amp_veltrack: float = 100.0      # %
    pitch_keytrack: float = 100.0    # cents per key
    rt_decay: float = 0.0            # dB per second the key was held (release samples)
    offset: int = 0                 # source frames, before repitching
    ampeg_decay: float = 0.0
    ampeg_sustain: float = 100.0     # percent
    xfin_lovel: float = 0.0
    xfin_hivel: float = 0.0
    xfout_lovel: float = 127.0
    xfout_hivel: float = 127.0
    lorand: float = 0.0
    hirand: float = 1.0
    loop_mode: str = "no_loop"
    loop_start: int = 0
    loop_end: int = -1              # inclusive, per SFZ
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


def _expand(path: str, defines: dict, depth: int = 0, root: str | None = None) -> str:
    """Read defines/includes, preferring included-file paths, then main-SFZ-relative paths."""
    if depth > 8:
        raise SongError(f"sfz {path}: #include nested too deeply")
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = _strip_comments(f.read())
    except OSError as e:
        raise SongError(f"sfz: cannot read {path}: {e.strerror}") from None
    root = root or os.path.dirname(os.path.abspath(path))
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
            # Some libraries resolve all includes from the main SFZ directory;
            # others use paths relative to each included file. Keep both explicit.
            if not os.path.isfile(inc):
                inc = os.path.join(root, m.group(1).replace('\\', '/'))
            out.append(_expand(inc, defines, depth + 1, root))
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


def effective_regions(path: str) -> tuple[list[dict], set[str]]:
    """Inherited raw opcodes, shared by playback and explicit fixed-program preparation."""
    path = os.path.abspath(path)
    text = _expand(path, {})
    scopes: dict[str, dict] = {lv: {} for lv in LEVELS}
    regions: list[dict] = []
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
        regions.append(ops)

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
    return regions, unsupported


def parse(path: str) -> Program:
    path = os.path.abspath(path)
    raw, unsupported = effective_regions(path)
    regions = [_region(ops, os.path.dirname(path), path, unsupported) for ops in raw]
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
        for k in ("lovel", "hivel", "seq_length", "seq_position", "group", "off_by", "offset", "loop_start", "loop_end"):
            if k in ops:
                setattr(r, k, int(float(ops[k])))
        for k in ("ampeg_attack", "ampeg_release", "tune", "volume", "amp_veltrack",
                  "pitch_keytrack", "rt_decay", "ampeg_decay", "ampeg_sustain", "xfin_lovel", "xfin_hivel",
                  "xfout_lovel", "xfout_hivel", "lorand", "hirand", "pan"):
            if k in ops:
                setattr(r, k, float(ops[k]))
    except ValueError as e:
        raise SongError(f"sfz {path}: region {ops.get('sample')}: {e}") from None
    if "off_by" not in ops and "offby" in ops:
        r.off_by = int(ops["offby"])
    for k, value in ops.items():
        if re.fullmatch(r"amp_velcurve_\d+", k):
            index = int(k.rsplit("_", 1)[1])
            point = float(value)
            if not 0 <= index <= 127 or not 0 <= point <= 1:
                raise SongError(f"sfz {path}: invalid {k}={value}")
            r.amp_velcurve[index] = point
    if ops.get("off_mode", "fast") != "fast":
        unsupported.add("off_mode=" + ops["off_mode"])
    if int(ops.get("lochan", 1)) > 1 or int(ops.get("hichan", 16)) < 1:
        unsupported.add("channel selection outside channel 1")
    r.trigger = ops.get("trigger", "attack").lower()
    r.loop_mode = ops.get("loop_mode", "no_loop")
    if r.loop_mode not in ("no_loop", "one_shot", "loop_sustain", "loop_continuous"):
        raise SongError(f"sfz {path}: unsupported loop_mode={r.loop_mode}")
    if r.offset < 0 or r.loop_start < 0 or (r.loop_mode.startswith("loop_") and r.loop_end < r.loop_start):
        raise SongError(f"sfz {path}: invalid sample offset or loop points")
    # ampeg_dynamic only changes behavior during live envelope modulation, which static notes don't send.
    # group_label is descriptive metadata, not an audio operation.
    # Static notes arrive on channel 1 with their final float pitch: channel bounds and
    # MIDI bend ranges do not alter their sound. No live bend events are accepted.
    r.extra = {k: v for k, v in ops.items() if k not in SUPPORTED and not re.fullmatch(r"amp_velcurve_\d+", k)}
    unsupported.update(r.extra)
    return r
