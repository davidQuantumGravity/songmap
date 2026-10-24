"""The Studio rack: the instrument catalog, each part's voice, `inst`/`kit` line edits and note auditions.

Knob panels are built from each instrument's `PARAMS` schema (instruments/base.py), so a new instrument
or param appears in the GUI without GUI code. A turned knob writes `part=use(param=value)` on the song's
`inst` line (or `piece=use(...)` on its `kit` line); the code stays the source of truth.
"""
from __future__ import annotations

import os
import re
from dataclasses import asdict

import numpy as np
import yaml

_VOICE = re.compile(r"\s*([A-Za-z_]\w*)(?:=([\w/.-]+))?(?:\(([^)]*)\))?")


# ---------------------------------------------------------------------------------------------- catalog
def catalog() -> dict:
    """Every instrument's schema and presets (with their descriptions and values), and the sampler libraries."""
    from ..instruments import REGISTRY
    from ..instruments.presets import PRESET_DIR, list_presets, resolve
    presets: dict[str, list] = {}
    for inst, names in list_presets().items():
        for name in names:
            with open(os.path.join(PRESET_DIR, inst, name + ".yaml"), encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            presets.setdefault(inst, []).append({"name": name, "ref": f"{inst}/{name}",
                                                 "description": data.get("description", ""),
                                                 "tags": data.get("tags") or [], "params": resolve(f"{inst}/{name}")[1]})
    samplers = []
    try:
        from ..instruments.sampler.library import voices
        samplers = voices()
    except Exception:                                    # noqa: BLE001  (the sampler backend is optional)
        pass
    from ..instruments import Sampler
    from ..mix.inserts import UNITS
    return {"instruments": [cls.schema() for cls in REGISTRY.values()] + [Sampler.schema()], "presets": presets,
            "samplers": samplers, "inserts": [u.schema() for u in UNITS.values()], **patch_catalog(),
            "guides": guides()}


def guides() -> dict:
    """The instrument tutorials (instruments/guides.yaml): what each instrument imitates, how it is built, why it
    sounds the way it does, its signal chain, every knob in plain words, and recipes to try."""
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "instruments", "guides.yaml")
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def patch_catalog() -> dict:
    """The patch modules (types, knobs, docs) and the library's patches, for the wiring editor."""
    from ..instruments.patch import MODULES, SOURCES, library, raw_spec, validate
    mods = [{"name": m.name, "kind": m.kind, "doc": m.doc, "audio_in": m.audio_in, "output": m.output,
             "knobs": [asdict(k) for k in m.knobs]} for m in MODULES.values()]
    lib = {}
    for name, spec in library().items():
        try:
            lib[name] = {"description": spec.get("description", ""), **raw_spec(validate(spec, name))}
        except Exception:                                # noqa: BLE001
            continue
    return {"modules": mods, "sources": list(SOURCES), "patch_library": lib}


def voice_info(ens, part: str, piece: str | None = None) -> dict:
    """One voice as the rack shows it: what it uses, the song's overrides and every resolved value."""
    from ..instruments import REGISTRY, Sampler
    from ..instruments.presets import resolve
    v = ens.voice(part, piece)
    inst = v.instrument
    info = {"use": v.use, "instrument": inst, "preset": v.use.partition("/")[2] or None,
            "params": {k: _jsonable(x) for k, x in v.params.items()}, "values": {}}
    cls = Sampler if inst == "sampler" else REGISTRY.get(inst)
    if inst == "patch":                                  # a patch instrument: its params are <module>.<knob>
        from ..instruments.patch import build
        pname = v.use.partition("/")[2]
        try:
            cls = type(build(pname, ens.patch_spec(pname)))
            info["schema"] = [asdict(q) for q in cls.PARAMS]
            info["patch"] = pname
            info["patch_source"] = "song" if pname in (getattr(ens.song, "patches", None) or {}) else "library"
        except Exception as e:                           # noqa: BLE001  (shown as a check error elsewhere)
            info["error"] = str(e)
            cls = None
    if cls is not None:
        try:
            if cls is Sampler:
                from ..instruments.sampler.library import manifest
                base = manifest()["voices"].get(v.use.partition("/")[2], {}).get("params", {})
            else:
                base = resolve(v.use)[1]
        except Exception:                                # noqa: BLE001  (shown as a check error elsewhere)
            base = {}
        if inst == "patch":
            base = {}
        for q in cls.PARAMS:
            info["values"][q.name] = _jsonable(v.params.get(q.name, base.get(q.name, q.default)))
        info["preset_values"] = {q.name: _jsonable(base.get(q.name, q.default)) for q in cls.PARAMS}
    return info


def voices(ens, parts: dict) -> dict:
    out = {}
    for part, evs in parts.items():
        try:
            if ens.is_kit(part):
                pieces = sorted({e.piece for e in evs if e.piece} | set(ens.kits.get(part, {})))
                out[part] = {"kit": True, "pieces": {p: voice_info(ens, part, p) for p in pieces}}
            else:
                out[part] = {"kit": False, **voice_info(ens, part)}
        except Exception as e:                           # noqa: BLE001
            out[part] = {"error": str(e)}
    return out


def _jsonable(x):
    return x if isinstance(x, (int, float, str, bool)) or x is None else str(x)


# ---------------------------------------------------------------------------------------------- text edits
def _num(x) -> str:
    """Numbers as the language writes them: .8, -.25, 480."""
    if not isinstance(x, (int, float)):
        return str(x)
    s = f"{round(float(x), 4):g}"
    return s[1:] if s.startswith("0.") else "-" + s[2:] if s.startswith("-0.") else s


def _split_comment(s: str) -> tuple[str, str]:
    m = re.search(r"(^|\s)#", s)
    return (s, "") if not m else (s[:m.start() + len(m.group(1))].rstrip(), s[m.start() + len(m.group(1)):])


def _tokens(body: str) -> list[list]:
    """`gtr=string_pluck/still(brightness=.8) bass(cutoff=480)` -> [[name, use, [k=v, ...]], ...]"""
    from ..parse.lang import split_top
    out, pos = [], 0
    while pos < len(body.rstrip()):
        m = _VOICE.match(body, pos)
        if not m or m.end() == pos:
            raise ValueError(f"can't read '{body[pos:].split()[0]}'")
        out.append([m[1], m[2], [x.strip() for x in split_top(m[3], ",")] if m[3] else []])
        pos = m.end()
    return out


def _token(name: str, use: str | None, kvs: list[str]) -> str:
    return name + (f"={use}" if use else "") + (f"({', '.join(kvs)})" if kvs else "")


def _apply(kvs: list[str], params: dict | None, clear: bool) -> list[str]:
    kvs = [] if clear else list(kvs)
    for k, v in (params or {}).items():
        kvs = [kv for kv in kvs if kv.partition("=")[0].strip() != k]
        if v is not None:
            kvs.append(f"{k}={_num(v)}")
    return kvs


def set_voice(text: str, part: str, *, use: str | None = None, params: dict | None = None,
              piece: str | None = None, current_use: str | None = None, clear: bool = False) -> str:
    """Set a part's (or a kit piece's) instrument and/or params on the song's `inst` (`kit`) lines.
    `params` values of None remove that override; `clear` drops every override (switching instruments).
    A voice not written yet is added as `name=<use or current_use>(...)`."""
    directive, name = ("kit", piece) if piece else ("inst", part)
    lines = text.split("\n")
    rx = re.compile(rf"{directive}\s")
    hits = [i for i, ln in enumerate(lines) if rx.match(ln)]
    for i in hits:
        body, comment = _split_comment(lines[i][len(directive):])
        toks = _tokens(body)
        for t in toks:
            if t[0] == name:
                if use:
                    t[1] = use
                t[2] = _apply(t[2], params, clear)
                lines[i] = directive + " " + " ".join(_token(*x) for x in toks) + (("  " + comment) if comment else "")
                return "\n".join(lines)
    tok = _token(name, use or current_use, _apply([], params, False))
    if hits:
        i = hits[-1]
        body, comment = _split_comment(lines[i])
        lines[i] = body + " " + tok + (("  " + comment) if comment else "")
    else:
        from .mixer import _first_section_line
        lines.insert(_first_section_line(lines), f"{directive} {tok}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------------- audition
def audition(song, part: str, notes: list[dict], piece: str | None = None, overrides: dict | None = None) -> np.ndarray:
    """Render a few notes with a part's voice (as the song defines it, plus unsaved knob `overrides`):
    notes = [{t, pitch, vel, gate}]. Stereo, peak-safe."""
    from ..arrange.ensemble import Ensemble
    from ..instruments import Note, make
    from ..instruments.dsp import SR, as_stereo
    from ..render import _apply_chokes
    ens = Ensemble(song)
    v = ens.voice(part, piece)
    if v.use.startswith("patch/"):
        from ..instruments.patch import build
        pname = v.use.partition("/")[2]
        inst = build(pname, ens.patch_spec(pname), **{**v.params, **(overrides or {})})
    else:
        inst = make(v.use, **{**v.params, **(overrides or {})})
    rendered = []
    for k, n in enumerate(notes):
        note = Note(float(n.get("pitch", 60)), float(n.get("vel", 0.7)), float(n.get("gate", 0.5)), seed=k + 1, rr=k)
        y = as_stereo(inst.render(note))
        rendered.append([int(float(n.get("t", 0)) * SR), y, 1.0, 0.0, *inst.choke(note)])
    _apply_chokes(rendered)
    length = max((s + len(y) for s, y, *_ in rendered), default=SR // 10) + SR // 20
    out = np.zeros((length, 2))
    for s, y, *_ in rendered:
        out[s:s + len(y)] += y
    peak = float(np.abs(out).max()) if len(out) else 0.0
    if peak > 0.89:
        out *= 0.89 / peak
    fade = min(len(out), SR // 100)
    out[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return out


# ---------------------------------------------------------------------------------------------- patches
def set_patch(text: str, name: str, spec: dict | None) -> str:
    """Rewrite a patch's `patch <name> ...` lines from a spec (None removes the patch). Raises ParamError."""
    from ..instruments.patch import to_text, validate
    new = to_text(name, validate(spec, name)) if spec is not None else []
    lines = text.split("\n")
    rx = re.compile(rf"patch\s+{re.escape(name)}(\s|$)")
    hits = [i for i, ln in enumerate(lines) if rx.match(ln)]
    if hits:
        at = hits[0]
        lines = [ln for i, ln in enumerate(lines) if i not in hits]
    else:
        from .mixer import _first_section_line
        at = _first_section_line(lines)
    lines[at:at] = new
    return "\n".join(lines)
