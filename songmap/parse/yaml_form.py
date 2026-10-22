"""YAML song maps -> Song (SONGMAP_SPEC.md), with v0.1 migration.

v0.1 files (no `songmap:` key) still load, with a deprecation warning. The one semantic change
is durations: in v0.1 a note without a duration was a quarter note; in v0.2 durations are
sticky. `migrate()` rewrites v0.1 motifs with explicit durations where they would differ, and
sets `master: legacy`, because v0.1 songs were rendered by synth_v0's normalize + tanh master.
"""
from __future__ import annotations

import copy
import json
import os
import re

import yaml

from ..model import (DEFAULT_PARTS, KIT_ROLES, EventSpec, HarmonySpec, MasterSpec, Motif, PartSpec, Section,
                     Song)
from .errors import NotationError, SongError, did_you_mean
from .notes import _DEG_TOK, _PITCH_TOK, _REL_TOK

VERSION = "0.2"
TOP_KEYS = ("songmap", "title", "tempo", "meter", "key", "tuning", "fps", "seed", "tail_seconds", "mood", "video",
            "instruments", "groove", "parts_feel", "harmony", "motifs", "sections", "events", "cues", "mix",
            "returns", "master", "qa", "binaural")
SECTION_KEYS = ("name", "bars", "parts", "like", "add", "drop", "harmony", "dyn", "feel", "tempo", "key", "binaural")
PART_SOURCES = ("style", "motif", "motifs", "notes", "deg", "rel", "steps", "vary")
PART_OPTS = ("mods", "dyn", "art", "oct", "transpose", "feel", "voicing", "auto", "mute", "gain_db", "gate",
             "order", "octaves", "fills", "crash", "pan", "len", "role", "voices", "range", "rhythm", "voice", "vel",
             "octave", "transform")
MOTIF_KEYS = ("notes", "deg", "rel", "octave", "key")
MASTER_KEYS = ("mode", "target_lufs", "ceiling_db", "glue", "preserve_contrast")


# ----------------------------------------------------------------------------
# YAML with line numbers
# ----------------------------------------------------------------------------
class LineDict(dict):
    line: int | None = None


class _Loader(yaml.SafeLoader):
    pass


def _construct_mapping(loader, node):
    loader.flatten_mapping(node)
    d = LineDict(loader.construct_pairs(node, deep=True))
    d.line = node.start_mark.line + 1
    return d


_Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def _plain(x):
    """LineDict -> dict, recursively (for dumping)."""
    if isinstance(x, dict):
        return {k: _plain(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_plain(v) for v in x]
    return x


def load_raw(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return load_raw_text(f.read(), path)


def load_raw_text(text: str, path: str | None = None) -> dict:
    try:
        raw = yaml.load(text, Loader=_Loader)
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        raise SongError(f"YAML syntax: {getattr(e, 'problem', e)}", file=path,
                        line=mark.line + 1 if mark else None) from None
    if not isinstance(raw, dict):
        raise SongError("a song map is a YAML mapping (title:, tempo:, sections: ...)", file=path)
    return raw


# ----------------------------------------------------------------------------
# v0.1 -> v0.2
# ----------------------------------------------------------------------------
def is_v01(raw: dict) -> bool:
    return "songmap" not in raw


def explicit_durations(text: str, mode: str) -> str:
    """Rewrite a v0.1 motif (bare note = quarter) so it means the same under sticky durations."""
    tok_re = {"deg": _DEG_TOK, "rel": _REL_TOK}.get(mode, _PITCH_TOK)
    sep = "" if mode == "letter" else "/"
    cur = "4"
    out = []
    for raw in text.split():
        m = tok_re.match(raw)
        if raw == "|" or raw.startswith("=") or raw in ("<", ">") or not m:
            out.append(raw)
            continue
        d = m["dur"] or (m.groupdict().get("dur2"))
        if d is None:
            d = "4"
            if cur != "4":
                i = m.start("marks")
                raw = raw[:i] + sep + "4" + raw[i:]
        cur = d
        out.append(raw)
    return " ".join(out)


def migrate(raw: dict) -> tuple[dict, list[str]]:
    """v0.1 raw mapping -> v0.2 raw mapping (plain dicts) + notes on what changed."""
    raw = _plain(raw)
    notes = []
    out = {"songmap": float(VERSION)}
    for k, v in raw.items():
        out[k] = copy.deepcopy(v)
    for name, m in (out.get("motifs") or {}).items():
        if isinstance(m, str):
            new = explicit_durations(m, "letter")
            if new != m:
                out["motifs"][name] = new
                notes.append(f"motif {name}: durations made explicit")
            continue
        for mode in ("notes", "deg", "rel"):
            if mode in m:
                new = explicit_durations(str(m[mode]), "letter" if mode == "notes" else mode)
                if new != m[mode]:
                    m[mode] = new
                    notes.append(f"motif {name}: durations made explicit")
    for sec in out.get("sections") or []:
        for role, val in (sec.get("parts") or {}).items():
            if isinstance(val, dict):
                for mode in ("notes", "deg", "rel"):
                    if mode in val:
                        val[mode] = explicit_durations(str(val[mode]), "letter" if mode == "notes" else mode)
    if "master" not in out:
        out["master"] = "legacy"
        notes.append("master: legacy (v0.1 songs were mastered by synth_v0: normalize + tanh)")
    return out, notes


# ----------------------------------------------------------------------------
# dumping (used by `songmap migrate`; full Song -> YAML/compact printing is P6's fmt.py)
# ----------------------------------------------------------------------------
_PLAIN = re.compile(r"[A-Za-z_][\w./+-]*")


def _flow(v) -> str:
    """One-line YAML: flow mappings/lists; strings quoted unless they are simple names."""
    if isinstance(v, dict):
        return "{" + ", ".join(f"{_flow(k)}: {_flow(x)}" for k, x in v.items()) + "}"
    if isinstance(v, list):
        return "[" + ", ".join(_flow(x) for x in v) + "]"
    if isinstance(v, str):
        if _PLAIN.fullmatch(v) and yaml.safe_load(v) == v:
            return v
        return json.dumps(v, ensure_ascii=False)       # a JSON string is a valid double-quoted YAML scalar
    if v is None:
        return "null"
    return yaml.safe_dump(v).strip().removesuffix("...").strip()


def dump(raw: dict, header: str = "") -> str:
    """Readable YAML: top-level scalars, one line per section/event/motif, flow style inside."""
    lines = [header.rstrip("\n")] if header else []
    for k, v in raw.items():
        if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
            lines.append(f"{k}:")
            lines += [f"  - {_flow(x)}" for x in v]
        elif isinstance(v, dict) and v and k not in ("video",):
            lines.append(f"{k}:")
            lines += [f"  {_flow(kk)}: {_flow(vv)}" for kk, vv in v.items()]
        else:
            lines.append(f"{k}: {_flow(v)}")
        if k in ("tail_seconds", "harmony", "motifs", "sections", "cues", "instruments", "mix"):
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def leading_comments(path: str) -> str:
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("#"):
                break
            out.append(line.rstrip("\n"))
    return "\n".join(out)


# ----------------------------------------------------------------------------
# raw -> Song
# ----------------------------------------------------------------------------
def load(path: str) -> Song:
    raw = load_raw(path)
    warnings = []
    if is_v01(raw):
        lines = {id(s): getattr(s, "line", None) for s in raw.get("sections") or []}
        ev_lines = [getattr(e, "line", None) for e in raw.get("events") or []]
        sec_lines = [lines[id(s)] for s in raw.get("sections") or []]
        raw, _ = migrate(raw)
        _restore_lines(raw, sec_lines, ev_lines)
        warnings.append(f"{os.path.basename(path)}: v0.1 song map (no 'songmap:' key); migrated in memory. "
                        f"Run `songmap migrate {path}` to update the file.")
    song = from_raw(raw, file=path)
    song.warnings[:0] = warnings
    return song


def _restore_lines(raw, sec_lines, ev_lines):
    for key, lines in (("sections", sec_lines), ("events", ev_lines)):
        items = raw.get(key) or []
        for i, item in enumerate(items):
            d = LineDict(item)
            d.line = lines[i] if i < len(lines) else None
            items[i] = d


def _line(x) -> int | None:
    return getattr(x, "line", None)


def _num(v, what, file, line=None, section=None, positive=True) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise SongError(f"{what} must be a number, got '{v}'", file=file, line=line, section=section)
    if positive and v <= 0:
        raise SongError(f"{what} must be > 0, got {v}", file=file, line=line, section=section)
    return v


def _check_keys(d: dict, valid, what, file, line=None, section=None):
    for k in d:
        if k not in valid:
            raise SongError(f"unknown {what} key '{k}'", file=file, line=_line(d) or line, section=section,
                            suggestion=did_you_mean(k, valid))


def from_raw(raw: dict, file: str | None = None) -> Song:
    # `x-...` keys are free-form (e.g. YAML anchors shared by several sections) and ignored.
    _check_keys({k: v for k, v in raw.items() if not str(k).startswith("x-")}, TOP_KEYS, "top-level", file)
    s = Song(file=file)
    s.version = str(raw.get("songmap", VERSION))
    if s.version not in ("0.2",):
        raise SongError(f"songmap version {s.version} not supported", file=file, suggestion="this engine reads 0.2")
    s.title = str(raw.get("title", s.title))
    s.tempo = _num(raw.get("tempo", s.tempo), "tempo", file)
    meter = str(raw.get("meter", "4/4"))
    m = re.fullmatch(r"\s*(\d+)\s*/\s*(\d+)\s*", meter)
    if not m:
        raise SongError(f"meter '{meter}' not understood", file=file, suggestion="write e.g. 4/4, 3/4, 6/8")
    s.meter = (int(m[1]), int(m[2]))
    s.key = str(raw.get("key", s.key))
    try:
        from ..theory.keys import parse_key
        parse_key(s.key)
    except NotationError as e:
        raise SongError(str(e), file=file) from None
    if "tuning" in raw:
        from ..theory.tuning import parse_tuning
        try:
            s.tuning = parse_tuning(raw["tuning"]).name
        except ValueError as e:
            raise SongError(str(e), file=file) from None
    s.fps = int(_num(raw.get("fps", s.fps), "fps", file))
    s.seed = int(raw.get("seed", s.seed))
    s.tail_seconds = _num(raw.get("tail_seconds", s.tail_seconds), "tail_seconds", file, positive=False)
    s.mood = raw.get("mood")
    s.video = dict(raw.get("video") or {})
    s.instruments = _plain(raw.get("instruments") or {})
    s.groove = _plain(raw.get("groove") or {})
    s.parts_feel = _plain(raw.get("parts_feel") or {})
    s.cues = dict(raw.get("cues") or {})
    s.mix = _plain(raw.get("mix") or {})
    s.returns = _plain(raw.get("returns") or {})
    s.qa = _plain(raw.get("qa") or {})
    s.binaural = _binaural(raw.get("binaural"), "binaural", file)
    s.master = _master(raw.get("master"), file)
    s.harmony = _harmony(raw.get("harmony") or {}, file)
    s.motifs = _motifs(raw.get("motifs") or {}, file)
    s.sections = _sections(raw.get("sections") or [], s, file)
    s.events = _events(raw.get("events") or [], file)
    if not s.sections:
        raise SongError("no sections", file=file, suggestion="add sections: [{name: intro, bars: 4, parts: {...}}]")
    return s


def _master(v, file) -> MasterSpec:
    if v is None:
        return MasterSpec()
    if isinstance(v, str):
        if v not in ("legacy", "standard", "clean"):
            raise SongError(f"master '{v}' unknown", file=file, suggestion="valid: legacy standard clean, or a mapping")
        return MasterSpec(mode=v)
    if not isinstance(v, dict):
        raise SongError("master must be 'legacy' or a mapping", file=file)
    _check_keys(v, MASTER_KEYS, "master", file)
    return MasterSpec(**{**MasterSpec().__dict__, **v})


def _harmony(h, file) -> HarmonySpec:
    _check_keys(h, ("default", "chord_bars", "progressions", "voicing"), "harmony", file)
    default = h.get("default") or []
    if isinstance(default, str):
        default = default.replace("|", " ").split()
    return HarmonySpec(default=[str(c) for c in default], chord_bars=float(h.get("chord_bars", 1)),
                       progressions={k: str(v) for k, v in (h.get("progressions") or {}).items()},
                       voicing=_plain(h.get("voicing") or {}))


def _motifs(ms, file) -> dict[str, Motif]:
    out = {}
    for name, m in ms.items():
        line = _line(ms)
        if isinstance(m, str):
            out[name] = Motif(name, m, "letter", line=line)
            continue
        if not isinstance(m, dict):
            raise SongError(f"motif {name}: write a string or {{deg: ..., octave: 5}}", file=file, line=line)
        _check_keys(m, MOTIF_KEYS, f"motif {name}", file, line)
        modes = [k for k in ("notes", "deg", "rel") if k in m]
        if len(modes) != 1:
            raise SongError(f"motif {name}: give exactly one of notes:, deg:, rel:", file=file, line=_line(m))
        mode = modes[0]
        out[name] = Motif(name, str(m[mode]), "letter" if mode == "notes" else mode, int(m.get("octave", 4)),
                          m.get("key"), _line(m))
    return out


def parse_part(role: str, value, motifs: dict, *, file=None, line=None, section=None) -> PartSpec:
    """Part value forms: 'style' | 'style+mod' | motif name | [motifs] | {style|motifs|notes|deg|rel|steps, opts}."""
    p = PartSpec(role)
    if isinstance(value, str):
        if value.split(":")[0] in motifs:
            p.motifs = [value]
        else:
            p.style, *p.mods = [x.strip() for x in value.split("+")]
        return p
    if isinstance(value, list):
        p.motifs = [str(x) for x in value]
        return p
    if not isinstance(value, dict):
        raise SongError(f"part {role}: write a style name, a motif list or a mapping", file=file, line=line,
                        section=section)
    for k, v in value.items():
        if k == "style":
            p.style, *mods = [x.strip() for x in str(v).split("+")]
            p.mods += mods
        elif k == "mods":
            p.mods += list(v) if isinstance(v, list) else str(v).split("+")
        elif k in ("motif", "motifs"):
            p.motifs = [str(x) for x in v] if isinstance(v, list) else [str(v)]
        elif k in ("notes", "deg", "rel"):
            p.notes, p.notes_mode = str(v), "letter" if k == "notes" else k
        elif k == "steps":
            p.steps.update({str(a): b for a, b in dict(v).items()})
        elif k == "vary":
            p.variants += _variants(role, v, motifs, file=file, line=line, section=section)
        elif k in PART_OPTS:
            p.opts[k] = _plain(v)
        elif role in KIT_ROLES and isinstance(v, (str, dict)):
            p.steps[str(k)] = _plain(v)          # drums: {kick: "X...", snare: "...."}
        else:
            raise SongError(f"part {role}: unknown key '{k}'", file=file, line=line, section=section,
                            suggestion=did_you_mean(k, PART_SOURCES + PART_OPTS))
    sources = [x for x in (p.style, p.motifs, p.notes) if x]
    if len(sources) > 1:
        raise SongError(f"part {role}: give one of style, motifs or notes (steps may add to a style)",
                        file=file, line=line, section=section)
    return p


def _variants(role, v, motifs, *, file, line, section) -> list:
    """vary: [{bars: [3, 7], part: eighths}, ...]; bars are offsets from the section start (like name+3)."""
    if not isinstance(v, list):
        raise SongError(f"part {role}: vary is a list like [{{bars: [3, 7], part: eighths}}]", file=file,
                        line=line, section=section)
    out = []
    for item in v:
        if not isinstance(item, dict) or "bars" not in item or "part" not in item:
            raise SongError(f"part {role}: each vary item needs bars: and part:", file=file, line=line,
                            section=section, suggestion="e.g. {bars: [7], part: {style: eighths}}")
        bars = item["bars"] if isinstance(item["bars"], list) else [item["bars"]]
        if not all(isinstance(b, int) and not isinstance(b, bool) and b >= 0 for b in bars):
            raise SongError(f"part {role}: vary bars are whole bar offsets >= 0, got {item['bars']}", file=file,
                            line=line, section=section)
        sub = parse_part(role, item["part"], motifs, file=file, line=line, section=section)
        if sub.variants:
            raise SongError(f"part {role}: a vary part can't vary again", file=file, line=line, section=section)
        out.append((tuple(bars), sub))
    return out


def _sections(secs, song: Song, file) -> list[Section]:
    out: list[Section] = []
    seen: dict[str, Section] = {}
    if not isinstance(secs, list):
        raise SongError("sections must be a list", file=file)
    for i, raw in enumerate(secs):
        line = _line(raw)
        if not isinstance(raw, dict) or "name" not in raw or "bars" not in raw:
            raise SongError(f"section {i + 1}: needs name: and bars:", file=file, line=line)
        name = str(raw["name"])
        _check_keys(raw, SECTION_KEYS, "section", file, line, name)
        if name in seen:
            raise SongError(f"duplicate section name '{name}'", file=file, line=line, section=name,
                            suggestion="names must be unique; positions refer to them")
        if not re.fullmatch(r"[A-Za-z_]\w*", name):
            raise SongError(f"section name '{name}' must start with a letter (letters, digits, _)",
                            file=file, line=line)
        sec = Section(name, _num(raw["bars"], "bars", file, line, name), line=line)
        if "like" in raw:
            base = seen.get(str(raw["like"]))
            if base is None:
                raise SongError(f"like: '{raw['like']}' is not an earlier section", file=file, line=line, section=name,
                                suggestion=did_you_mean(raw["like"], seen) if seen else "like: needs an earlier section")
            sec.parts = copy.deepcopy(base.parts)
            sec.harmony, sec.feel, sec.dyn = base.harmony, dict(base.feel), base.dyn
        for key in ("parts", "add"):
            for role, val in (raw.get(key) or {}).items():
                sec.parts[role] = parse_part(role, val, song.motifs, file=file, line=line, section=name)
        for role in raw.get("drop") or []:
            if role not in sec.parts:
                song.warnings.append(f"{file}:{line} {name}: drop '{role}' but the section has no such part")
            sec.parts.pop(role, None)
        sec.harmony = raw.get("harmony", sec.harmony)
        if sec.harmony is not None:
            sec.harmony = str(sec.harmony)
        sec.dyn = raw.get("dyn", sec.dyn)
        sec.feel = {**sec.feel, **_plain(raw.get("feel") or {})}
        sec.tempo = raw.get("tempo")
        sec.key = raw.get("key")
        sec.binaural = _binaural(raw.get("binaural"), f"section {name}: binaural", file, line, beat_only=True)
        seen[name] = sec
        out.append(sec)
    return out


def _binaural(v, what, file, line=None, beat_only=False) -> dict:
    """A song's or section's binaural block (checked in full by mix/binaural.plan); a section's bare value is its beat."""
    if v is None:
        return {}
    if beat_only and isinstance(v, (int, float, str)) and not isinstance(v, bool):
        return {"beat": v}
    if not isinstance(v, dict):
        raise SongError(f"{what} must be a mapping", file=file, line=line,
                        suggestion="e.g. binaural: {carriers: [A3, E4], beat: 10}" if not beat_only
                        else "e.g. binaural: {beat: 10>6.18} or binaural: 6.18")
    return _plain(v)


def _events(evs, file) -> list[EventSpec]:
    out = []
    for raw in evs:
        line = _line(raw)
        if not isinstance(raw, dict) or "at" not in raw or "type" not in raw:
            raise SongError("an event needs at: and type:, e.g. {at: goals, type: impact}", file=file, line=line)
        params = {k: _plain(v) for k, v in raw.items() if k not in ("at", "type")}
        out.append(EventSpec(str(raw["type"]), raw["at"], params, line))
    return out


__all__ = ["load", "load_raw", "from_raw", "migrate", "dump", "explicit_durations", "parse_part", "DEFAULT_PARTS"]
