"""Explicit textbook playback sources, credits, and checked notation reuse."""
from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import html
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def records():
    path = ROOT / "textbook/audio_refresh.json"
    return json.loads(path.read_text(encoding="utf-8"))["records"] if path.is_file() else []


@lru_cache(maxsize=1)
def audio_engine_hash():
    """Invalidate audio after engine, shared demo helpers or sample-install changes."""
    h = hashlib.sha256()
    paths = [p for p in (ROOT / "songmap").rglob("*")
             if p.suffix in (".py", ".yaml")
             and not set(p.relative_to(ROOT / "songmap").parts).intersection(("gui", "visual"))
             and p.name not in ("cli.py", "describe.py", "guides.yaml")]
    paths += list((ROOT / "textbook/audio").rglob("*.py"))
    receipt = ROOT / "samples/songmap-library.json"
    if receipt.exists():
        paths.append(receipt)
    for p in sorted(paths):
        h.update(p.relative_to(ROOT).as_posix().encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def versioned(url, source):
    """New audio must also be new to a browser/CDN holding the previous URL."""
    if not source or not Path(source).is_file():
        return url
    h = hashlib.sha256(Path(source).read_bytes())
    h.update(audio_engine_hash().encode())
    return url + "?v=" + h.hexdigest()[:12]


def edition_for(source):
    try:
        relative = Path(source).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(source)
    record = next((r for r in records() if r["kind"] == "songbook" and r["source"] == relative), None)
    return str(ROOT / record["playback_source"]) if record else str(source)


def suite_source(filename):
    record = next((r for r in records() if r["kind"] == "suite" and r["id"] == Path(filename).stem), None)
    if record and record["status"] == "updated":
        return str(ROOT / record["playback_source"])
    return None


def caption(chapter, name):
    record = next((r for r in records() if r["kind"] == "chapter" and r["id"] == chapter + "/" + name), None)
    if not record or record["status"] != "updated":
        return ""
    voices = sorted({c["after"].removeprefix("sampler/").replace("_", " ") for c in record["changes"]})
    return ' <small class="sampled-edition">Sampled edition: ' + ", ".join(voices) + '. <a href="../audio-credits.html">Instrument credits</a>.</small>'


def reusable_notation(source, old_cache, qa_path=None):
    """True when a recorded input proves that existing notation still fits.

    An instrument-only revision can replace a video's audio without drawing its
    identical notation again. The explicit builder flag opts into preserving the
    existing visual design, even if newer renderer code has become available.
    """
    from songmap.parse import load
    from songmap.arrange.expand import expand
    from songmap.visual.score import score_of
    from songmap.visual.view import path_for
    source = Path(source)
    relative = source.resolve().relative_to(ROOT)
    sidecar = Path(path_for(str(source)))
    candidates = [ROOT / "build/textbook_previous_audio" / relative,
                  ROOT / "build/textbook_originals" / relative, source]
    if old_cache and qa_path and Path(qa_path).is_file():
        cached_source = json.loads(Path(qa_path).read_text(encoding="utf-8")).get("source_sha256")
        for original in candidates:
            if original.is_file() and hashlib.sha256(original.read_bytes()).hexdigest() == cached_source:
                return asdict(score_of(expand(load(str(original))))) == asdict(score_of(expand(load(str(source)))))
    for original in candidates:
        if not original.is_file():
            continue
        h = hashlib.sha1(original.read_bytes())
        if sidecar.is_file():
            h.update(b"\0view\0")
            h.update(sidecar.read_bytes())
        if old_cache and old_cache.split("|")[0] == h.hexdigest():
            return asdict(score_of(expand(load(str(original))))) == asdict(score_of(expand(load(str(source)))))
    return False


def stamp_media_urls(site):
    """Publish URLs for the finished bytes, after every render has completed."""
    site = Path(site).resolve()
    hashes = {}
    def replace(page, match):
        url = html.unescape(match[2])
        u = urlsplit(url)
        if u.scheme or u.netloc or Path(u.path).suffix.lower() not in (".mp3", ".mp4", ".jpg"):
            return match[0]
        target = (page.parent / u.path).resolve()
        if not target.is_relative_to(site) or not target.is_file():
            return match[0]
        if target not in hashes:
            hashes[target] = hashlib.sha256(target.read_bytes()).hexdigest()[:12]
        params = [(k, v) for k, v in parse_qsl(u.query) if k != "v"] + [("v", hashes[target])]
        result = urlunsplit(("", "", u.path, urlencode(params), u.fragment))
        return match[1] + html.escape(result, quote=True) + match[3]
    for page in site.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        page.write_text(re.sub(r'((?:src|href|poster)=")([^"]+)(")', lambda m: replace(page, m), text), encoding="utf-8")


def publish_credits(site):
    from songmap.instruments.sampler.library import manifest
    site = Path(site)
    sources = manifest()["sources"]
    items = "".join(f'<li>{s["credit"]}: <a href="{s["url"]}">{s["repo"]}</a>, {s["license"]}; source revision <code>{s["revision"]}</code>.</li>' for s in sources.values())
    body = ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<title>Audio edition and instrument credits</title><link rel="stylesheet" href="assets/style.css">'
            '<main style="max-width:55rem;margin:3rem auto;padding:1rem"><h1>Audio edition and instrument credits</h1>'
            '<p>Musical examples use recorded instruments where appropriate. Exact-frequency experiments, pure tones, '
            'engineered golden spectra, synthesis demonstrations and historical score editions retain their intended sounds. '
            'Instrument changes preserve the written pitches, rhythms, form, tuning settings and cue timing.</p>'
            '<p>Recordings retain natural tuning and vibrato; equal-tempered score pitches describe the playback targets. '
            'Pure-tone and spectral comparisons use generated tones. Mastering follows each source score.</p>'
            f'<ul>{items}</ul><p>The recordings are dedicated under CC0 1.0. Source audio is installed separately; '
            'the website contains finished renders, not the sample library.</p>'
            '<p><a href="audio-refresh.json">Complete clip decisions and source hashes</a> · <a href="index.html">Back to the book</a></p></main></html>')
    (site / "audio-credits.html").write_text(body, encoding="utf-8")
    (site / "audio-refresh.json").write_text(json.dumps({"records": records()}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
