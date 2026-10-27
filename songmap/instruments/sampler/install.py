"""Install pinned, curated SFZ programs; verify Git blobs or a published archive's SHA-256.

All downloads stay below a samples root. The receipt records SHA-256, upstream revision,
and license. Installation resumes without downloading files that already match upstream.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ...parse.errors import SongError
from . import library, sfz

RECEIPT = "songmap-library.json"


def _save_receipt(path: Path, receipt: dict) -> None:
    partial = path.with_suffix(".json.part")
    partial.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    os.replace(partial, path)


def _read(url: str) -> bytes:
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 SongMap-sample-library"})
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except (OSError, urllib.error.URLError) as error:
            if attempt == 2:
                raise SongError(f"could not download sample source {url}: {error}",
                                suggestion="check the network connection and rerun songmap samples install; verified downloads are reused") from None
            time.sleep(attempt + 1)


def _blob(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _within(root: Path, path: Path) -> Path:
    path = path.resolve()
    if not path.is_relative_to(root.resolve()):
        raise SongError(f"sample dependency escapes its library: {path}")
    return path


def _fetch(source: dict, relative: str, root: Path, entry: dict) -> dict:
    target = _within(root, root / relative)
    data = target.read_bytes() if target.is_file() else b""
    if _blob(data) != entry["sha"]:
        url = f"https://raw.githubusercontent.com/{source['repo']}/{source['revision']}/" + urllib.parse.quote(relative, safe="/")
        data = _read(url)
        if _blob(data) != entry["sha"]:
            raise SongError(f"sample integrity check failed: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(target.name + ".songmap-part")
        partial.write_bytes(data)
        os.replace(partial, target)
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "git_blob": entry["sha"]}


def _archive(source: dict, pack: Path, root: Path, receipt: dict) -> None:
    """Pinned ZIPs for libraries published outside Git. Verify before extracting anything."""
    target = root / "_downloads" / (source["sha256"] + ".zip")
    data = target.read_bytes() if target.is_file() else b""
    if hashlib.sha256(data).hexdigest() != source["sha256"]:
        data = _read(source["archive"])
        if hashlib.sha256(data).hexdigest() != source["sha256"]:
            raise SongError(f"sample archive integrity check failed: {source['archive']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        # Validate every member before the first write, including platform-specific paths.
        members = [(m, _within(pack, pack / m.filename.replace('\\', '/'))) for m in archive.infolist()]
        for member, path in members:
            if member.is_dir():
                continue
            content = archive.read(member)
            digest = hashlib.sha256(content).hexdigest()
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                path.parent.mkdir(parents=True, exist_ok=True)
                partial = path.with_name(path.name + ".songmap-part")
                partial.write_bytes(content)
                os.replace(partial, path)
            receipt["files"][path.relative_to(root).as_posix()] = {"sha256": digest, "bytes": len(content),
                                                                 "archive_sha256": source["sha256"]}


def install(names: list[str] | None = None, root: str | Path = "samples", log=print, workers: int = 6) -> dict:
    library.soundfile()                 # diagnose the optional decoder before downloading the audio
    manifest = library.manifest()
    requested = names or list(manifest["voices"])
    names = []
    for name in requested:
        matches = ([name] if name in manifest["voices"] else
                   [n for n, v in manifest["voices"].items() if v["source"] == name or v["family"] == name])
        names.extend(matches or [name])
    names = list(dict.fromkeys(names))
    unknown = set(names) - manifest["voices"].keys()
    if unknown:
        raise SongError(f"unknown sample voices: {', '.join(sorted(unknown))}",
                        suggestion="run songmap samples list")
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    receipt_path = root / RECEIPT
    receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.is_file() else {"version": 1, "voices": {}, "files": {}}
    for source_name in dict.fromkeys(manifest["voices"][name]["source"] for name in names):
        source = manifest["sources"][source_name]
        pack = root / "_packs" / source_name
        selected = [name for name in names if manifest["voices"][name]["source"] == source_name]
        if "archive" in source:
            log(f"{source_name}: verifying pinned archive for {len(selected)} voices")
            _archive(source, pack, root, receipt)
            for name in selected:
                program = sfz.parse(str(pack / manifest["voices"][name]["program"]))
                if program.unsupported:
                    raise SongError(f"{name}: unsupported SFZ features: {', '.join(sorted(program.unsupported))}")
                for region in program.regions:
                    if not _within(pack, Path(region.sample)).is_file():
                        raise SongError(f"{name}: missing archive sample {region.sample}")
                receipt["voices"][name] = {**manifest["voices"][name], **source}
            _save_receipt(receipt_path, receipt)
            continue
        url = f"https://api.github.com/repos/{source['repo']}/git/trees/{source['revision']}?recursive=1"
        tree = json.loads(_read(url))
        if tree.get("truncated"):
            raise SongError(f"incomplete upstream file list: {source_name}")
        entries = {e["path"]: e for e in tree["tree"] if e["type"] == "blob"}
        required: set[str] = set()

        def fetch(relative):
            if relative not in entries:
                raise SongError(f"missing upstream sample: {source_name}/{relative}")
            return relative, _fetch(source, relative, pack, entries[relative])

        def program_files(relative, depth=0, base=None):
            if depth > 8:
                raise SongError('SFZ includes nested too deeply')
            relative, metadata = fetch(relative)
            base = base or (pack/relative).parent
            receipt['files'][(pack/relative).relative_to(root).as_posix()] = metadata
            import re
            body = sfz._strip_comments((pack/relative).read_text(encoding='utf-8',errors='replace'))
            for inc in re.findall(r'#include\s+"([^"$]+)"',body):
                child = _within(pack,(pack/relative).parent/inc.replace('\\','/')).relative_to(pack).as_posix()
                if child not in entries:
                    child = _within(pack,base/inc.replace('\\','/')).relative_to(pack).as_posix()
                program_files(child,depth+1,base)

        for name in selected:
            program = manifest["voices"][name]["program"]
            program_files(program)
            path = pack/program
            if 'adapt' in manifest['voices'][name]:
                from .curate import prepare
                path = library.voice_path(root,name)
                prepare(pack/program,path,manifest['voices'][name]['adapt'])
                data = path.read_bytes()
                receipt['files'][path.relative_to(root).as_posix()] = {'sha256':hashlib.sha256(data).hexdigest(),
                    'bytes':len(data),'derived_from':program,'profile':manifest['voices'][name]['adapt']}
            parsed = sfz.parse(str(path))
            if parsed.unsupported:
                raise SongError(f"{name}: unsupported SFZ features: {', '.join(sorted(parsed.unsupported))}")
            for region in parsed.regions:
                sample = _within(pack, Path(region.sample)).relative_to(pack).as_posix()
                required.add(sample)
        required.update(p for p in entries if "/" not in p and p.lower().startswith(("license", "readme", "copying")))
        total_bytes = sum(entries[p].get("size", 0) for p in required)
        log(f"{source_name}: {len(selected)} voices, {len(required)} files, {total_bytes / 1e6:.1f} MB")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for i, (relative, metadata) in enumerate(pool.map(fetch, sorted(required)), 1):
                receipt["files"][(pack / relative).relative_to(root).as_posix()] = metadata
                if i % 25 == 0 or i == len(required):
                    log(f"  verified {i}/{len(required)} files")
        for name in selected:
            receipt["voices"][name] = {**manifest["voices"][name], **source}
        _save_receipt(receipt_path, receipt)
    log(f"Installed {len(names)} voices in {root}")
    return receipt


def verify(root: str | Path = "samples") -> dict:
    root = Path(root).resolve()
    path = root / RECEIPT
    if not path.is_file():
        return {"ok": False, "voices": 0, "files": 0, "errors": [f"no installation receipt in {root}"]}
    receipt = json.loads(path.read_text(encoding="utf-8"))
    errors = []
    for name, entry in receipt["files"].items():
        target = _within(root, root / name)
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != entry["sha256"]:
            errors.append(f"missing or changed: {name}")
    for name, voice in receipt["voices"].items():
        if voice["revision"] != library.manifest()["sources"][voice["source"]]["revision"]:
            errors.append(f"outdated source revision: {name}")
    return {"ok": not errors, "voices": len(receipt["voices"]), "files": len(receipt["files"]), "errors": errors}
