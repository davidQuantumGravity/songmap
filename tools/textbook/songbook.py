"""The textbook's Songbook: every song in the repo, on one page, for review.

    python tools/textbook/songbook.py            # list what the Songbook will show, with each song's review
    python tools/textbook/build.py               # builds it into the textbook (chapter `songbook`)

Sources (nothing to register; a new file is enough):
    songs/**/<name>.sm | .sml | .songmap.yaml     each folder is a collection (its README.md titles it)
    .claude/skills/songmap-compose/examples/*.sm   the skill's worked examples

For each song the page shows its intent (the file's leading comments), facts (length, tempo, key,
mood, parts), a player, the render's spectrogram and section loudness, the automated ear's report
(`songmap listen`) and its review status. A song is reviewed by adding one comment line:

    # review: approved — <notes>          (or: rework — <what to change>, pending)

Songs with no review line are listed as "awaiting review". Renders are cached in build/songbook/
by the file's and the engine's hashes, so only new or changed songs (or a changed engine) render.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from contextlib import contextmanager

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
SONGS = os.path.join(ROOT, "songs")
SKILL_EXAMPLES = os.path.join(ROOT, ".claude", "skills", "songmap-compose", "examples")
CACHE = os.path.join(ROOT, "build", "songbook")
EXTS = (".sm", ".sml", ".songmap.yaml")
REVIEW = re.compile(r"^\s*#\s*review\s*:\s*(\w[\w-]*)\s*[—–:-]*\s*(.*)$", re.I | re.M)
STATUS = {"approved": "approved", "ok": "approved", "rework": "rework", "revise": "rework", "pending": "pending"}


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "songs"


def engine_hash() -> str:
    from audio_editions import audio_engine_hash
    return audio_engine_hash()


def _readme(folder: str) -> tuple[str, str]:
    p = os.path.join(folder, "README.md")
    if not os.path.isfile(p):
        return "", ""
    text = open(p, encoding="utf-8").read()
    m = re.search(r"^#\s+(.+)$", text, re.M)
    paras = [x.strip() for x in re.split(r"\n\s*\n", text) if x.strip() and not x.lstrip().startswith(("#", "|", "-", "`"))]
    return (m[1].strip() if m else ""), (paras[0] if paras else "")


def collections() -> list[dict]:
    out = []
    if os.path.isdir(SONGS):
        for d, dirs, files in sorted(os.walk(SONGS)):
            dirs[:] = sorted(x for x in dirs if x not in ("renders", "__pycache__") and not x.startswith("."))
            songs = sorted(os.path.join(d, f) for f in files if f.endswith(EXTS))
            if not songs:
                continue
            rel = os.path.relpath(d, SONGS).replace(os.sep, "/")
            title, blurb = _readme(d)
            out.append({"id": "songs-" + _slug(rel), "title": title or f"songs/{rel}", "blurb": blurb,
                        "folder": f"songs/{rel}", "songs": songs})
    if os.path.isdir(SKILL_EXAMPLES):
        songs = sorted(os.path.join(SKILL_EXAMPLES, f) for f in os.listdir(SKILL_EXAMPLES) if f.endswith(EXTS))
        if songs:
            out.append({"id": "skill-examples", "title": "Skill examples",
                        "blurb": "The worked examples the songmap-compose skill teaches from.",
                        "folder": ".claude/skills/songmap-compose/examples", "songs": songs})
    return out


def song_name(path: str) -> str:
    base = os.path.basename(path)
    for e in EXTS:
        if base.endswith(e):
            return base[: -len(e)]
    return base


def entry(path: str) -> dict:
    """Facts, intent, review status and the automated ear's note-level report for one song."""
    text = open(path, encoding="utf-8").read()
    intent = []
    for line in text.splitlines():
        if not line.startswith("#"):
            if line.strip():
                break
            continue
        if not REVIEW.match(line):
            intent.append(line.lstrip("#").strip())
    m = REVIEW.search(text)
    status = STATUS.get(m[1].lower(), m[1].lower()) if m else "awaiting"
    from audio_editions import edition_for
    playback = edition_for(path)
    playback_text = open(playback, encoding="utf-8").read()
    e = {"path": path, "playback_path": playback,
         "playback_rel": os.path.relpath(playback, ROOT).replace(os.sep, "/"),
         "rel": os.path.relpath(path, ROOT).replace(os.sep, "/"), "name": song_name(path),
         "intent": " ".join(x for x in intent if x), "status": status, "review_note": m[2].strip() if m else "",
         "hash": hashlib.sha1(playback_text.encode()).hexdigest()[:12]}
    try:
        from songmap.arrange.expand import expand
        from songmap.listen import listen
        from songmap.parse import load
        song = load(playback)
        arr = expand(song)
        tl = arr.timeline
        mins, secs = divmod(tl.seconds, 60)
        e.update(title=song.title, facts={
            "length": f"{int(mins)}:{secs:04.1f}", "bars": f"{tl.total_bars:g} bars", "tempo": f"{song.tempo:g} BPM",
            "meter": f"{song.meter[0]}/{song.meter[1]}", "key": song.key, "mood": song.mood or "balanced",
            "parts": ", ".join(sorted(arr.parts))})
        e["ear"] = listen(arr).to_dict()
    except Exception as ex:                                            # noqa: BLE001
        e.update(title=e["name"], facts={}, error=f"{type(ex).__name__}: {ex}")
    return e


@contextmanager
def _cache_publish(folder):
    """Serialize the short cache commit; OS locks release after a process exits."""
    with open(os.path.join(folder, ".publish.lock"), "a+b") as lock:
        lock.write(b"0")
        lock.flush()
        lock.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == "nt":
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def render_cached(e: dict, ehash: str) -> str | None:
    """Render one song (cached): returns a folder with song.mp3, qa.json, review.json, qa.png."""
    if e.get("error"):
        return None
    d = os.path.join(CACHE, f"{e['name']}-{e['hash']}-{ehash}")
    complete = ("review.json", "qa.json", "qa.png", "render.log", "song.mp3")
    if all(os.path.isfile(os.path.join(d, f)) for f in complete):
        Path(d, "song.wav").unlink(missing_ok=True)
        return d
    from songmap.parse import load
    from songmap.render import render, write_outputs
    r = render(load(e.get("playback_path", e["path"])))
    os.makedirs(CACHE, exist_ok=True)
    # Separate working files prevent two builds of one edition from removing or
    # truncating each other's WAV/MP3. Publish the completion marker last.
    with tempfile.TemporaryDirectory(prefix=".render-", dir=CACHE) as td:
        assert Path(td).resolve().is_relative_to(Path(CACHE).resolve())
        write_outputs(r, td, stems=False, mp3=shutil.which("ffmpeg") is not None)
        if os.path.isfile(os.path.join(td, "song.mp3")):
            Path(td, "song.wav").unlink(missing_ok=True)
        os.makedirs(d, exist_ok=True)
        with _cache_publish(d):
            for name in sorted(os.listdir(td), key=lambda n: n == "render.log"):
                os.replace(os.path.join(td, name), os.path.join(d, name))
    return d


def _render_job(args):
    e, ehash = args
    try:
        return e["path"], render_cached(e, ehash), None
    except Exception as ex:                                            # noqa: BLE001
        return e["path"], None, f"{type(ex).__name__}: {ex}"
    finally:
        import gc
        from songmap.instruments.sampler.library import SAMPLES
        SAMPLES._data.clear()
        gc.collect()


def render_all(entries: list[dict], jobs: int = 4, log=print) -> dict:
    """{song path: render folder} for every song, rendering only what isn't cached."""
    ehash = engine_hash()
    unique = {(e["name"], e["hash"]): e for e in entries if not e.get("error")}
    todo = [(e, ehash) for e in unique.values()]
    out = {}
    if jobs > 1 and len(todo) > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            results = list(pool.map(_render_job, todo))
    else:
        results = []
        for t in todo:
            result = _render_job(t)
            results.append(result)
            log("  songbook " + t[0].get("rel", t[0]["path"]))
    for path, d, err in results:
        if err:
            log(f"PROBLEM songbook render {os.path.relpath(path, ROOT)}: {err}")
        elif d:
            out[path] = d
    return {e["path"]: out[unique[e["name"], e["hash"]]["path"]]
            for e in entries if not e.get("error") and unique[e["name"], e["hash"]]["path"] in out}


# ------------------------------------------------------------------------------------------------
# the chapter
# ------------------------------------------------------------------------------------------------
BADGE = {"awaiting": ("awaiting review", "#b26b00"), "pending": ("pending", "#b26b00"),
         "approved": ("approved", "#2e7d32"), "rework": ("needs rework", "#c62828")}


def sections(cols: list[dict]) -> list[dict]:
    return [{"id": "about", "title": "How to review"}] + [{"id": c["id"], "title": c["title"]} for c in cols]


def _ear_html(ear: dict | None) -> str:
    if not ear:
        return ""
    c = ear["counts"]
    head = f"{c['problem']} problems, {c['warning']} warnings, {c['note']} notes"
    items = "".join(
        f'<li class="ear-{html.escape(f["severity"])}"><b>{html.escape(f["severity"])}</b> '
        f'{html.escape(f["where"])}: {html.escape(f["message"])}'
        + (f' <span class="ear-fix">→ {html.escape(f["fix"])}</span>' if f.get("fix") else "") + "</li>"
        for f in ear["findings"])
    return (f'<details class="ear"{" open" if c["problem"] else ""}><summary>Automated ear: {head}</summary>'
            f'<ul>{items or "<li>nothing flagged</li>"}</ul></details>')


def _loudness_html(qa: dict | None) -> str:
    if not qa:
        return ""
    rows = "".join(f"<tr><td>{html.escape(s['name'])}</td><td>{s['loudness']:.1f}</td>"
                   f"<td>{s.get('low', 0):.2f} / {s.get('mid', 0):.2f} / {s.get('high', 0):.2f}</td></tr>"
                   for s in qa.get("sections", []) if s.get("loudness") is not None)
    stems = ", ".join(f"{html.escape(k)} {v:.1f}" for k, v in sorted((qa.get("stems") or {}).items(), key=lambda x: -x[1]))
    return (f'<details class="loud"><summary>Loudness: {qa.get("lufs", 0):.1f} LUFS, true peak '
            f'{qa.get("true_peak_db", 0):.1f} dBTP</summary><table><tr><th>Section</th><th>LUFS</th>'
            f'<th>low / mid / high</th></tr>{rows}</table><p class="stems">Stems (LUFS over the song): {stems}</p>'
            f'</details>')


def fragment(cols: list[dict], entries: dict, renders: dict, media_rel: dict) -> str:
    """entries: {path: entry}; renders: {path: render folder}; media_rel: {path: (mp3 url, png url)}."""
    total = sum(len(c["songs"]) for c in cols)
    waiting = sum(1 for e in entries.values() if e["status"] in ("awaiting", "pending", "rework"))
    parts = [
        '<section id="about"><h2>How to review</h2>',
        f"<p>Every song in the repository, {total} in all, {waiting} waiting for a verdict. Each one is "
        "rendered from its source file when the book is built, so this page always plays the current version.</p>",
        "<p><b>Listen for:</b> does it make you feel what its intent says; does the melody sing and the harmony "
        "move; does the groove feel played; do the big moments land and the quiet ones breathe; is anything "
        "too loud, muddy, harsh or repetitive?</p>",
        "<p><b>To give a verdict</b>, add one line to the song's file, or tell Claude in words and it will: "
        "<code># review: approved — what works</code> or <code># review: rework — what to change</code>. "
        "The <i>automated ear</i> under each song lists what the engine itself could check (clashes, crowded "
        "registers, mechanical repetition, flat dynamics, weak contrast). It catches faults, not taste.</p>",
        "<p>New songs appear here automatically: put the file in <code>songs/&lt;collection&gt;/</code>.</p>",
        "</section>"]
    order = {"awaiting": 0, "rework": 1, "pending": 2, "approved": 3}
    for c in cols:
        parts.append(f'<section id="{c["id"]}"><h2>{html.escape(c["title"])}</h2>')
        parts.append(f'<p class="folder"><code>{html.escape(c["folder"])}/</code></p>')
        if c["blurb"]:
            parts.append(f"<p>{html.escape(c['blurb'])}</p>")
        for path in sorted(c["songs"], key=lambda p: (order.get(entries[p]["status"], 9), p)):
            e = entries[path]
            label, color = BADGE.get(e["status"], (e["status"], "#555"))
            facts = " · ".join(f"{v}" for v in (e.get("facts") or {}).values() if v)
            parts.append(f'<article class="song" id="{c["id"]}-{_slug(e["name"])}">')
            parts.append(f'<h3>{html.escape(e.get("title") or e["name"])} '
                         f'<span class="badge" style="background:{color}">{label}</span></h3>')
            parts.append(f'<p class="facts">{html.escape(facts)}<br><code>{html.escape(e["rel"])}</code></p>')
            if e.get("playback_rel") != e["rel"]:
                parts.append(f'<p class="sampled-edition">Sampled playback edition: <code>{html.escape(e["playback_rel"])}</code>. '
                             'The original score is preserved. <a href="../audio-credits.html">Instrument credits</a>.</p>')
            if e.get("review_note"):
                parts.append(f'<p class="verdict"><b>Review:</b> {html.escape(e["review_note"])}</p>')
            if e.get("intent"):
                parts.append(f'<p class="intent">{html.escape(e["intent"])}</p>')
            if e.get("error"):
                parts.append(f'<p class="error"><b>Does not load:</b> {html.escape(e["error"])}</p>')
            mp3, png = media_rel.get(path, (None, None))
            if mp3:
                parts.append(f'<audio controls preload="none" src="{mp3}"></audio>')
            elif not e.get("error"):
                parts.append('<p class="norender"><i>Not rendered in this build (built with --no-audio or --check).</i></p>')
            if png:
                parts.append(f'<details class="spectro"><summary>Spectrogram and loudness</summary>'
                             f'<a href="{png}"><img src="{png}" alt="spectrogram of {html.escape(e["name"])}" '
                             f'style="max-width:100%"></a></details>')
            review = qa = None
            d = renders.get(path)
            if d:
                with open(os.path.join(d, "review.json"), encoding="utf-8") as f:
                    review = json.load(f)
                with open(os.path.join(d, "qa.json"), encoding="utf-8") as f:
                    qa = json.load(f)
            parts.append(_ear_html(review or e.get("ear")))
            parts.append(_loudness_html(qa))
            parts.append("</article>")
        parts.append("</section>")
    return "\n".join(parts)


def publish(entries: dict, renders: dict, out_site: str) -> dict:
    """Copy each render's MP3 and spectrogram into the site; returns {path: (mp3 url, png url)} for the page."""
    media = {}
    for path, d in renders.items():
        e = entries[path]
        rel = os.path.join("audio", "songbook", e["hash"][:6] + "-" + e["name"])
        dst = os.path.join(out_site, rel)
        os.makedirs(dst, exist_ok=True)
        playback = e.get("playback_path", path)
        with open(os.path.join(dst, "source.json"), "w", encoding="utf-8") as f:
            json.dump({"source": os.path.relpath(playback, ROOT).replace(os.sep, "/"),
                       "sha256": hashlib.sha256(open(playback, "rb").read()).hexdigest(),
                       "engine_hash": engine_hash()}, f, indent=2)
        urls = []
        for f in ("song.mp3", "qa.png", "qa.json", "review.json", "LICENSES.md"):
            src = os.path.join(d, f)
            if os.path.isfile(src):
                shutil.copy(src, os.path.join(dst, f))
                if f in ("song.mp3", "qa.png"):
                    urls.append("../" + (rel + "/" + f).replace(os.sep, "/"))
            else:
                if f in ("song.mp3", "qa.png"):
                    urls.append(None)
        media[path] = tuple(urls)
    return media


def chapter(render: bool, out_site: str | None = None, jobs: int = 4, log=print):
    """(sections, fragment) for the builder; renders and publishes media when asked."""
    cols = collections()
    entries = {p: entry(p) for c in cols for p in c["songs"]}
    renders = render_all(list(entries.values()), jobs, log) if render else {}
    if render and len(renders) != len(entries):
        missing = [e["rel"] for p, e in entries.items() if p not in renders]
        raise RuntimeError("Songbook media missing; website is not ready to publish: " + ", ".join(missing))
    media = publish(entries, renders, out_site) if (render and out_site) else {}
    return sections(cols), fragment(cols, entries, renders, media)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="List the Songbook: every song, its status and the automated ear")
    ap.add_argument("--render", action="store_true", help="also render (cached) and include loudness")
    args = ap.parse_args()
    for c in collections():
        print(f"{c['title']}  ({c['folder']})")
        for p in c["songs"]:
            e = entry(p)
            ear = e.get("ear", {}).get("counts", {})
            print(f"  [{e['status']:>9}] {e['rel']}  {e.get('facts', {}).get('length', '')}  "
                  + (f"ERROR {e['error']}" if e.get("error") else
                     f"ear: {ear.get('problem', 0)} problems, {ear.get('warning', 0)} warnings"))
    if args.render:
        cols = collections()
        render_all([entry(p) for c in cols for p in c["songs"]])


if __name__ == "__main__":
    main()
