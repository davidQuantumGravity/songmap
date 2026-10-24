"""Finding sample libraries on disk, reading their audio, and their licenses.

`sampler/<name>` looks in each samples root, in order:
  1. every folder in $SONGMAP_SAMPLES (os.pathsep-separated)
  2. ./samples (the current directory; git-ignored in this repo)
  3. ~/.songmap/samples
and accepts `<root>/<name>.sfz`, a folder `<root>/<name>/` holding one program (or the catalog's
default program), or `<root>/<dir>/.../<stem>.sfz` for `sampler/<dir>/<stem>`.
Sample audio is never committed; renders list what they used in LICENSES.md.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

from ...parse.errors import SongError

ENV = "SONGMAP_SAMPLES"


@dataclass(frozen=True)
class Known:
    title: str
    license: str
    credit: str
    url: str
    install: str
    family: str = "keys"
    program: str = ""        # preferred .sfz stem when the folder holds several


CATALOG = {
    "salamander": Known(
        "Salamander Grand Piano V3", "CC BY 3.0", "Alexander Holm",
        "https://freepats.zenvoid.org/Piano/acoustic-grand-piano.html",
        "download SalamanderGrandPiano-SFZ+FLAC-V3+20200602.tar.gz (707 MB) and unpack it as "
        "samples/salamander/", "keys", "SalamanderGrandPiano"),
    "vsco2": Known(
        "VSCO-2 Community Edition", "CC0 1.0", "Versilian Studios (Sam Gossner)",
        "https://github.com/sgossner/VSCO-2-CE/releases/tag/1.1.0",
        "download the SFZ release (1.1.0) and unpack it as samples/vsco2/; then use "
        "sampler/vsco2/<program stem>", "string"),
}


@lru_cache(maxsize=1)
def manifest() -> dict:
    with open(Path(__file__).with_name("voices.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def voice_path(root: str | Path, name: str) -> Path:
    v = manifest()["voices"][name]
    return Path(root) / "_packs" / v["source"] / v["program"]


def voices() -> list[dict]:
    """Curated programs, including missing ones so people can discover and install them."""
    out = []
    for name, v in manifest()["voices"].items():
        source = manifest()["sources"][v["source"]]
        path = next((voice_path(root, name) for root in roots() if voice_path(root, name).is_file()), None)
        installed = False
        if path:
            try:
                from .sfz import parse
                installed = all(Path(r.sample).is_file() for r in parse(str(path)).regions)
            except (SongError, OSError):
                pass
        out.append({"name": name, "ref": f"sampler/{name}", "title": v["title"],
                    "family": v["family"], "category": v.get("category", v["family"]),
                    "description": v["description"], "range": v["range"],
                    "license": source["license"], "credit": source["credit"], "url": source["url"],
                    "revision": source["revision"], "installed": installed,
                    "install": f"songmap samples install {name}", "params": v.get("params", {}),
                    "audition_pitch": v.get("audition_pitch", sum(v["range"]) / 2)})
    return out


def roots() -> list[str]:
    env = [p for p in os.environ.get(ENV, "").split(os.pathsep) if p]
    return [os.path.abspath(p) for p in env] + [os.path.abspath("samples"),
                                                 os.path.join(os.path.expanduser("~"), ".songmap", "samples")]


def _programs(d: str, depth: int = 3) -> list[str]:
    out = []
    for cur, dirs, files in os.walk(d):
        if cur[len(d):].count(os.sep) >= depth:
            dirs[:] = []
        out += [os.path.join(cur, f) for f in files if f.lower().endswith(".sfz")]
    return sorted(out, key=lambda p: (p.count(os.sep), p.lower()))


def _stem(p: str) -> str:
    return os.path.splitext(os.path.basename(p))[0]


def find(name: str) -> str:
    """'salamander' or 'vsco2/Cello Sus' -> path of the .sfz program."""
    if name in manifest()["voices"]:
        for root in roots():
            p = voice_path(root, name)
            if p.is_file():
                return str(p)
        raise SongError(f"sampler/{name}: sample voice is not installed",
                        suggestion=f"run songmap samples install {name}; or install every voice with songmap samples install")
    known = CATALOG.get(name.partition("/")[0])
    for root in roots():
        p = os.path.join(root, *name.split("/"))
        if os.path.isfile(p) and p.lower().endswith(".sfz"):
            return p
        if os.path.isfile(p + ".sfz"):
            return p + ".sfz"
        if os.path.isdir(p):
            progs = _programs(p)
            if len(progs) == 1:
                return progs[0]
            if known and known.program and "/" not in name:
                pick = [q for q in progs if known.program.lower().replace(" ", "") in _stem(q).lower().replace(" ", "")]
                if pick:
                    return pick[0]
            if progs:
                stems = ", ".join(_stem(q) for q in progs[:12])
                raise SongError(f"sampler/{name}: {p} holds {len(progs)} programs",
                                suggestion=f"pick one as sampler/{name}/<stem>; stems: {stems}")
        head, _, stem = name.rpartition("/")
        d = os.path.join(root, *head.split("/")) if head else None
        if d and os.path.isdir(d):
            for q in _programs(d, depth=6):
                if _stem(q).lower() == stem.lower():
                    return q
    where = "; ".join(roots())
    lib = name.partition("/")[0]
    if known:
        hint = f"{known.title} ({known.license}, {known.credit}): {known.url}; {known.install}"
    else:
        hint = (f"put <library>/<program>.sfz under one of the roots, or set {ENV}; free libraries: "
                + "; ".join(f"{k}: {v.title} ({v.license}) {v.url}" for k, v in CATALOG.items()))
    raise SongError(f"sampler library '{lib}' not found (looked for '{name}' in {where})", suggestion=hint)


def library_dir(sfz_path: str) -> str:
    """The library folder: the topmost folder below a samples root that holds the program."""
    p = os.path.abspath(sfz_path)
    for root in roots():
        if p.lower().startswith(root.lower() + os.sep):
            first = p[len(root) + 1:].split(os.sep)[0]
            return os.path.join(root, first) if first != os.path.basename(p) else os.path.dirname(p)
    return os.path.dirname(p)


def license_entry(name: str, sfz_path: str) -> dict:
    voice = manifest()["voices"].get(name)
    if voice:
        source = manifest()["sources"][voice["source"]]
        base = Path(sfz_path)
        for _ in Path(voice["program"]).parts:
            base = base.parent
        return {"name": f"sampler/{name}", "title": voice["title"], "program": sfz_path,
                **source, "files": [str(p) for p in base.glob("*") if p.is_file() and
                                    p.name.lower().startswith(("license", "readme", "copying"))]}
    known = CATALOG.get(name.partition("/")[0])
    d = library_dir(sfz_path)
    files = sorted(f for f in os.listdir(d) if f.lower().startswith(("license", "licence", "readme", "copying")))
    entry = {"name": f"sampler/{name}", "program": sfz_path, "files": [os.path.join(d, f) for f in files]}
    if known:
        entry.update(title=known.title, license=known.license, credit=known.credit, url=known.url)
    else:
        entry.update(title=os.path.basename(d), license="unknown: check the library's own files before publishing",
                     credit="", url="")
    return entry


def licenses_md(entries: list[dict]) -> str:
    lines = ["# Sample sources used in this render", ""]
    for e in entries:
        lines.append(f"## {e['title']} (`{e['name']}`)")
        lines.append(f"- License: {e['license']}")
        if e["credit"]:
            lines.append(f"- Credit: {e['credit']}")
        if e["url"]:
            lines.append(f"- Source: {e['url']}")
        if e.get("revision"):
            lines.append(f"- Source revision: `{e['revision']}`")
        lines.append(f"- Program: `{e['program']}`")
        lines += [f"- See also: `{f}`" for f in e["files"]]
        lines.append("")
    return "\n".join(lines)


def soundfile():
    """The optional `soundfile` module (the `sampler` extra)."""
    try:
        import soundfile as sf
    except ImportError:
        raise SongError("the sampler needs the soundfile package", suggestion="pip install -e .[sampler]") from None
    return sf


class Samples:
    """Decoded sample audio, read lazily and only as far as notes need (piano samples run 20 s+)."""

    def __init__(self):
        self._data: dict[str, tuple[np.ndarray, int, bool]] = {}   # path -> (frames, sr, whole file)

    def get(self, path: str, frames: int) -> tuple[np.ndarray, int]:
        have = self._data.get(path)
        if have and (have[2] or (frames > 0 and len(have[0]) >= frames)):
            return have[0], have[1]
        try:
            with soundfile().SoundFile(path) as f:
                want = max(frames, 2 * len(have[0]) if have else 0) if frames else 0
                x = f.read(frames=min(want, f.frames) if want else -1, dtype="float32", always_2d=True)
                whole = len(x) >= f.frames
                sr = f.samplerate
        except (RuntimeError, OSError) as e:      # soundfile raises LibsndfileError (a RuntimeError)
            raise SongError(f"sampler: cannot read sample {path}: {e}",
                            suggestion="check the library unpacked completely") from None
        self._data[path] = (x, sr, whole)
        return x, sr

    def rate(self, path: str) -> int:
        if path in self._data:
            return self._data[path][1]
        return self.get(path, 1)[1]


SAMPLES = Samples()
