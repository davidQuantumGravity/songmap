"""Build the textbook website from textbook/toc.yaml and textbook/content/*.html.

    python tools/textbook/build.py                 # full build into textbook_site/ (renders audio, cached)
    python tools/textbook/build.py --check         # validate only: tags, sections, references, audio sources
    python tools/textbook/build.py --check --chapters ch05 ch23
    python tools/textbook/build.py --no-audio      # build pages, skip audio rendering

Content fragments (textbook/content/<id>.html) use plain HTML plus these tags:
    <section id="sec">          one per TOC section, in order
    <div class="layer hear|understand|derive"> ... </div>
    <aside class="mirror"> ... </aside>      <aside class="box math|history|note"> ... </aside>
    <div class="exercise"> ... <details class="answer"><summary>Answer</summary>...</details></div>
    <audio-ex src="name" caption="..."></audio-ex>
        -> textbook/audio/<id>/<name>.songmap.yaml (SongMap song) or <name>.py (defines render() -> (n,2) float array at 48 kHz)
           SongMap songs are shown as videos (letter names, staff and piano roll, sounding notes lit;
           songmap.visual) with an MP3 alongside; Python examples (exact frequencies) are audio only
    <audio-ref file="P01b_lullaby_in_gold.mp3" caption="..."></audio-ref>     (from golden_audio/)
    <pianoroll edo="12|36" notes="C4 E4 G4 ; C4 vE4 ^G4" labels="C ; Cg" title="..."></pianoroll>
    <pc-circle edo="12|36" marks="0 4 7" path="0 7 2 9" title="..."></pc-circle>   (pitch classes in steps)
    <a href="ch:ch05#comma">...</a>     cross-reference, resolved and checked
    $...$ and $$...$$                   math (rendered at build time by KaTeX: cd tools/textbook && npm install)
"""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import yaml

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, ROOT)
TB = os.path.join(ROOT, "textbook")
CONTENT = os.path.join(TB, "content")
AUDIO_SRC = os.path.join(TB, "audio")
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
OUT = os.path.join(ROOT, "textbook_site")
GOLDEN_AUDIO = os.path.join(ROOT, "golden_audio")
CACHE = os.path.join(ROOT, "build", "textbook_audio_cache.json")
VIDEO = True                                  # SongMap examples as videos (--no-video turns it off)
VIDEO_SIZE = (1280, 720)
SR = 48000
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")       # PROBLEM lines carry note names like ♭

NAMES12 = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
LETTER = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def name36(st: int) -> str:
    q, r = divmod(st % 36, 3)
    return NAMES12[q] if r == 0 else ("^" + NAMES12[q] if r == 1 else "v" + NAMES12[(q + 1) % 12])


def note_steps(tok: str) -> int:
    """'^C4' / 'vEb4' / 'F#3' / 'C' -> absolute 36-ET steps (MIDI*3)."""
    m = re.fullmatch(r"([\^v]*)([A-G])(#|b)?(-?\d+)?", tok.strip())
    if not m:
        raise ValueError(f"bad note '{tok}'")
    octv = int(m[4]) if m[4] else 4
    semis = 12 * (octv + 1) + LETTER[m[2]] + {"#": 1, "b": -1, None: 0}[m[3]]
    return 3 * semis + m[1].count("^") - m[1].count("v")


# ------------------------------------------------------------------------------------------------
# toc
# ------------------------------------------------------------------------------------------------
def load_toc():
    with open(os.path.join(TB, "toc.yaml"), encoding="utf-8") as f:
        toc = yaml.safe_load(f)
    chapters = []
    for part in toc["parts"]:
        for ch in part["chapters"]:
            ch["part"] = part
            chapters.append(ch)
    return toc, chapters


# ------------------------------------------------------------------------------------------------
# figures
# ------------------------------------------------------------------------------------------------
def svg_pianoroll(attrs) -> str:
    """Compact piano roll: one row per step (sixth-steps in 36-ET), naturals labelled, sounding rows bold."""
    edo = int(attrs.get("edo", "12"))
    cols = [c.split() for c in attrs["notes"].split(";")]
    labels = [x.strip() for x in attrs.get("labels", "").split(";")] if attrs.get("labels") else [""] * len(cols)
    pitches = [[note_steps(n) for n in c] for c in cols]
    flat = [p for c in pitches for p in c]
    sounding = set(flat)
    spelled = {}                                             # step -> the spelling written in `notes`
    for c in cols:
        for n in c:
            spelled.setdefault(note_steps(n), n.replace("#", "♯").replace("b", "♭") if len(n) > 1 else n)
    step = 3 if edo == 12 else 1
    lo, hi = min(flat) - step, max(flat) + step
    rows = list(range(lo, hi + 1, step))
    rh = 5 if edo == 36 else 8
    cw, lw, top = 58, 52, 4
    W = lw + cw * len(cols) + 6
    H = top + rh * len(rows) + (18 if any(labels) else 6)
    Z = 1.3                                                  # display scale (CSS px per unit)
    out = [f'<svg class="fig pianoroll" width="{W * Z:.0f}" height="{H * Z:.0f}" viewBox="0 0 {W:.0f} {H:.0f}" role="img" '
           f'aria-label="{html.escape(attrs.get("title", "piano roll"))}">']
    placed = []                                              # (y, column) of labels already drawn
    for i, r in enumerate(reversed(rows)):
        y = top + i * rh
        layer = r % 3
        black = (r // 3) % 12 in (1, 3, 6, 8, 10) and layer == 0
        cls = "row-black" if black else ("row-l0" if layer == 0 else "row-l1" if layer == 1 else "row-l2")
        out.append(f'<rect x="{lw}" y="{y:.1f}" width="{cw * len(cols)}" height="{rh}" class="{cls}"/>')
    for i, r in enumerate(reversed(rows)):                   # labels: sounding rows first, then C/E/G
        if r not in sounding:
            continue
        y = top + i * rh + rh / 2 + 3
        col = next(c for c in range(4) if all(abs(y - py) >= 9 or pc != c for py, pc in placed))
        placed.append((y, col))
        out.append(f'<text x="{lw - 4 - 25 * col}" y="{y:.1f}" class="lab on" text-anchor="end">{html.escape(spelled.get(r, name36(r) + str((r // 3) // 12 - 1)))}</text>')
    for i, r in enumerate(reversed(rows)):
        natural = r % 3 == 0 and (r // 3) % 12 in ((0, 2, 4, 5, 7, 9, 11) if edo == 12 else (0, 4, 7))
        y = top + i * rh + rh / 2 + 3
        if r in sounding or not natural or any(abs(y - py) < 9 for py, _ in placed):
            continue
        placed.append((y, 0))
        out.append(f'<text x="{lw - 4}" y="{y:.1f}" class="lab" text-anchor="end">{name36(r)}{(r // 3) // 12 - 1}</text>')
    for j, c in enumerate(pitches):
        x = lw + j * cw
        for p in c:
            y = top + (hi - p) / step * rh
            out.append(f'<rect x="{x + 5}" y="{y:.1f}" width="{cw - 10}" height="{rh - 0.6:.1f}" rx="1.5" class="note l{p % 3}"/>')
        if j < len(labels) and labels[j]:
            out.append(f'<text x="{x + cw / 2}" y="{H - 5}" text-anchor="middle" class="cl">{html.escape(labels[j])}</text>')
    out.append("</svg>")
    return "".join(out)


def svg_pc_circle(attrs) -> str:
    edo = int(attrs.get("edo", "12"))
    marks = [int(x) % edo for x in attrs.get("marks", "").split()]
    path = [int(x) % edo for x in attrs.get("path", "").split()]
    R, cx, cy = 120, 160, 160
    W = 320
    pos = lambda k: (cx + R * math.sin(2 * math.pi * k / edo), cy - R * math.cos(2 * math.pi * k / edo))  # noqa: E731
    out = [f'<svg class="fig pccircle" viewBox="0 0 {W} {W}" role="img" aria-label="{html.escape(attrs.get("title", "pitch-class circle"))}">',
           f'<circle cx="{cx}" cy="{cy}" r="{R}" class="ring"/>']
    if path:
        pts = " ".join(f"{pos(k)[0]:.1f},{pos(k)[1]:.1f}" for k in path)
        out.append(f'<polyline points="{pts}" class="path"/>')
    if len(marks) > 1:
        pts = " ".join(f"{pos(k)[0]:.1f},{pos(k)[1]:.1f}" for k in marks)
        out.append(f'<polygon points="{pts}" class="poly"/>')
    for k in range(edo):
        x, y = pos(k)
        on = k in marks
        if edo == 12:
            lab = NAMES12[k]
        else:
            lab = name36(k) if (on or k % 3 == 0) else ""
        r = 9 if on else (4 if edo == 36 else 6)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" class="{"dot on" if on else "dot"} l{k % 3 if edo == 36 else 0}"/>')
        if lab:
            lx, ly = cx + (R + 22) * math.sin(2 * math.pi * k / edo), cy - (R + 22) * math.cos(2 * math.pi * k / edo)
            out.append(f'<text x="{lx:.1f}" y="{ly + 4:.1f}" text-anchor="middle" class="{"lab on" if on else "lab"}">{html.escape(lab)}</text>')
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------------------------------------------------------
# audio
# ------------------------------------------------------------------------------------------------
def audio_source(chid, name):
    for ext in (".songmap.yaml", ".py"):
        p = os.path.join(AUDIO_SRC, chid, name + ext)
        if os.path.exists(p):
            return p
    return None


def _write_mp3(x: np.ndarray, path: str, normalize: bool = True):
    """normalize: peak to -1 dBFS (Python examples, `master: clean` songs). A song mastered to a loudness target
    keeps its level (only a peak above -1 dBFS is trimmed), so the songs of a suite stay matched."""
    from scipy.io import wavfile
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    peak = np.max(np.abs(x)) or 1.0
    if normalize or peak > 10 ** (-1 / 20):
        x = x / peak * 10 ** (-1 / 20)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with tempfile.TemporaryDirectory() as d:
        w = os.path.join(d, "a.wav")
        wavfile.write(w, SR, x.astype(np.float32))
        # separate left/right coding: binaural examples need each ear's tone intact
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", w, "-codec:a", "libmp3lame", "-q:a", "2",
                        "-joint_stereo", "0", path], check=True)


def _visual_hash() -> str:
    """Version of the video renderer: a change to songmap/visual re-renders every video."""
    h = hashlib.sha1()
    vdir = os.path.join(ROOT, "songmap", "visual")
    for f in sorted(os.listdir(vdir)):
        if f.endswith(".py"):
            h.update(open(os.path.join(vdir, f), "rb").read())
    h.update(repr(VIDEO_SIZE).encode())
    return h.hexdigest()[:12]


def render_song_media(src: str, mp3: str, mp4: str | None) -> None:
    """One SongMap example: render the audio once; write the MP3 and (optionally) the video and its poster."""
    from songmap.parse import yaml_form
    from songmap.render import render
    song = yaml_form.load(src)
    r = render(song)
    _write_mp3(r.audio, mp3, normalize=song.master.mode == "clean")
    if mp4:
        from songmap.export.wav import write_wav24
        from songmap.visual import write_poster, write_video
        os.makedirs(os.path.dirname(mp4), exist_ok=True)
        with tempfile.TemporaryDirectory() as td:
            wav = os.path.join(td, "song.wav")
            write_wav24(wav, r.audio)
            write_video(song, mp4, size=VIDEO_SIZE, audio_wav=wav, crf=23)
        im_path = mp4[:-4] + ".jpg"
        write_poster(song, im_path, size=VIDEO_SIZE)


def _media_job(job):
    src, mp3, mp4 = job
    try:
        render_song_media(src, mp3, mp4)
        return job, None
    except Exception as e:                                           # noqa: BLE001
        return job, f"{type(e).__name__}: {e}"


def render_audio(src: str, dst: str):
    if AUDIO_SRC not in sys.path:
        sys.path.insert(0, AUDIO_SRC)                 # so examples can `from _lib import ...`
    if src.endswith(".py"):
        spec = importlib.util.spec_from_file_location("tb_audio", src)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _write_mp3(mod.render(), dst)
    else:
        from songmap.parse import yaml_form
        from songmap.render import render
        song = yaml_form.load(src)
        r = render(song)
        _write_mp3(r.audio, dst, normalize=song.master.mode == "clean")


def file_hash(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------
# page processing
# ------------------------------------------------------------------------------------------------
TAG = re.compile(r"<(audio-ex|audio-ref|pianoroll|pc-circle)\b([^>]*?)(/?)>(?:\s*</\1>)?", re.S)
ATTR = re.compile(r'([\w-]+)\s*=\s*"([^"]*)"')


def figcap(attrs) -> str:
    """A figure's title becomes an HTML caption (wraps, and can hold math) rather than SVG text."""
    t = attrs.get("title") or attrs.get("caption")
    return f"<figcaption>{t}</figcaption>" if t else ""


def process(chid, frag, ids, sec_ids, problems, audio_jobs, audio_list):
    def sub(m):
        tag, attrs = m[1], dict(ATTR.findall(m[2]))
        try:
            if tag == "audio-ex":
                name = attrs.get("src", "")
                src = audio_source(chid, name)
                if not src:
                    problems.append(f"{chid}: audio-ex '{name}' has no source (textbook/audio/{chid}/{name}.songmap.yaml or .py)")
                rel = f"audio/{chid}/{name}.mp3"
                audio_jobs.append((src, os.path.join(OUT, rel)))
                audio_list.append((chid, name, attrs.get("caption", ""), rel))
                cap = attrs.get("caption", "")
                if VIDEO and src and src.endswith(".songmap.yaml"):
                    v = f"video/{chid}/{name}"
                    return (f'<figure class="audio video"><video controls preload="none" playsinline '
                            f'poster="../{v}.jpg" src="../{v}.mp4"></video>'
                            f'<figcaption>{cap} <a class="mp3" href="../{rel}">MP3</a></figcaption></figure>')
                return (f'<figure class="audio"><div class="player"><span class="ico">♪</span>'
                        f'<audio controls preload="none" src="../{rel}"></audio></div><figcaption>{cap}</figcaption></figure>')
            if tag == "audio-ref":
                f = attrs.get("file", "")
                if not os.path.exists(os.path.join(GOLDEN_AUDIO, f)):
                    problems.append(f"{chid}: audio-ref '{f}' not found in golden_audio/")
                rel = f"audio/suite/{f}"
                audio_jobs.append(("copy:" + os.path.join(GOLDEN_AUDIO, f), os.path.join(OUT, rel)))
                audio_list.append((chid, f, attrs.get("caption", ""), rel))
                return (f'<figure class="audio suite"><div class="player"><span class="ico">♫</span>'
                        f'<audio controls preload="none" src="../{rel}"></audio></div>'
                        f'<figcaption>{attrs.get("caption", "")}</figcaption></figure>')
            if tag == "pianoroll":
                return f'<figure class="svgfig">{svg_pianoroll(attrs)}{figcap(attrs)}</figure>'
            if tag == "pc-circle":
                return f'<figure class="svgfig">{svg_pc_circle(attrs)}{figcap(attrs)}</figure>'
        except Exception as e:                                       # noqa: BLE001
            problems.append(f"{chid}: <{tag}> {attrs}: {e}")
            return f'<p class="err">[figure error: {html.escape(str(e))}]</p>'
        return m[0]

    frag = TAG.sub(sub, frag)

    def xref(m):
        target = m[1]
        chap, _, anchor = target.partition("#")
        if chap not in ids:
            problems.append(f"{chid}: cross-reference to unknown chapter '{chap}'")
        elif anchor and anchor not in sec_ids.get(chap, set()):
            problems.append(f"{chid}: cross-reference to unknown section '{chap}#{anchor}'")
        return f'href="{chap}.html' + (f'#{anchor}"' if anchor else '"')

    frag = re.sub(r'href="ch:([\w-]+(?:#[\w-]+)?)"', xref, frag)
    return frag


def check_structure(ch, frag, problems):
    want = [s["id"] for s in ch.get("sections", [])]
    got = re.findall(r'<section id="([\w-]+)"', frag)
    for s in want:
        if s not in got:
            problems.append(f"{ch['id']}: missing <section id=\"{s}\">")
    for s in got:
        if s not in want:
            problems.append(f"{ch['id']}: section '{s}' is not in toc.yaml")
    if ch["part"]["id"] not in ("front", "appendices"):
        for layer in ("hear", "understand", "derive"):
            if f'class="layer {layer}' not in frag:
                problems.append(f"{ch['id']}: no '{layer}' layer anywhere")
    if frag.count("<section") != frag.count("</section>"):
        problems.append(f"{ch['id']}: unbalanced <section> tags")
    for t in ("div", "aside", "details", "figure", "table", "ul", "ol"):
        if len(re.findall(fr"<{t}\b", frag)) != frag.count(f"</{t}>"):
            problems.append(f"{ch['id']}: unbalanced <{t}> tags")


# ------------------------------------------------------------------------------------------------
# math (rendered at build time with KaTeX via node; falls back to client-side rendering)
# ------------------------------------------------------------------------------------------------
TOOLS = os.path.dirname(os.path.abspath(__file__))
KATEX_DIST = os.path.join(TOOLS, "node_modules", "katex", "dist")
HTML_TAG = re.compile(r"<(/?[A-Za-z][\w-]*)(?:\s[^<>]*)?/?>")
NO_MATH = re.compile(r"<(pre|code|script|style|svg)\b.*?</\1>", re.S | re.I)
MATH = re.compile(r"\$\$(.+?)\$\$|(?<![\\$])\$(?![\s$])((?:\\\$|[^$])+?)(?<![\s\\])\$(?!\d)", re.S)
CLIENT_MATH = False                                        # set when node/KaTeX is unavailable


def _text_ranges(frag):
    spans = sorted([m.span() for m in NO_MATH.finditer(frag)] + [m.span() for m in HTML_TAG.finditer(frag)],
                   key=lambda s: (s[0], -s[1]))
    pos = 0
    for a, b in spans:
        if a < pos:
            continue
        if a > pos:
            yield pos, a
        pos = b
    if pos < len(frag):
        yield pos, len(frag)


def find_math(frag):
    """(start, end, tex, display) for each $...$ / $$...$$ outside tags and pre/code/svg."""
    out = []
    for a, b in _text_ranges(frag):
        for m in MATH.finditer(frag, a, b):
            disp = m[1] is not None
            out.append((m.start(), m.end(), html.unescape(m[1] if disp else m[2]).strip(), disp))
    return out


def render_tex(items):
    """{(tex, display): {"html": ...} | {"error": ...}}, or None if node/KaTeX is unavailable."""
    uniq = list(dict.fromkeys(items))
    if not uniq:
        return {}
    if not os.path.isdir(KATEX_DIST):
        return None
    try:
        r = subprocess.run(["node", os.path.join(TOOLS, "katex_render.js")], input=json.dumps(uniq),
                           capture_output=True, text=True, encoding="utf-8", check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return dict(zip(uniq, json.loads(r.stdout)))


def apply_math(chid, frag, rendered, problems):
    out, pos = [], 0
    for a, b, tex, disp in find_math(frag):
        r = rendered.get((tex, disp), {})
        out.append(frag[pos:a])
        if "html" in r:
            out.append(r["html"])
        else:
            problems.append(f"{chid}: math error in {frag[a:b][:70]!r}: {r.get('error', 'not rendered')}")
            out.append(f'<span class="err">{html.escape(frag[a:b])}</span>')
        pos = b
    out.append(frag[pos:])
    return "".join(out)


# ------------------------------------------------------------------------------------------------
# templates
# ------------------------------------------------------------------------------------------------
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700'
         '&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=Inter:wght@400;500;600;700&display=swap">')
KATEX_CDN = ('<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>'
             '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>')
THEME_BOOT = ("<script>try{var t=localStorage.getItem('tb-theme');if(t)document.documentElement.setAttribute('data-theme',t)}"
              "catch(e){}</script>")
GOLDEN_PARTS = {"part6", "part7", "part8"}


def chap_num(ch):
    m = re.fullmatch(r"ch(\d+)", ch["id"])
    if m:
        return str(int(m[1])), f"Chapter {int(m[1])}"
    m = re.fullmatch(r"app([A-Z])", ch["id"])
    if m:
        return m[1], f"Appendix {m[1]}"
    return "", "Front matter"


def part_bits(part):
    """("Part VI", "The golden tonal system"), or (title, "") for front matter and appendices."""
    m = re.match(r"(Part [IVX]+)\.\s*(.*)", part["title"])
    return (m[1], m[2]) if m else (part["title"], "")


def hero_art(kind: str) -> str:
    """Decorative hero figure: a golden spiral over 36 dots, or the circle of fifths as a {12/5} star."""
    c, R = 100, 92
    if kind == "golden":
        phi = (1 + 5 ** 0.5) / 2
        tmax, pts = 9.0 * math.pi, []
        for i in range(0, 433):
            t = tmax * i / 432
            r = R * 0.98 * phi ** (2 * (t - tmax) / math.pi)
            pts.append(f"{c + r * math.cos(t):.1f},{c - r * math.sin(t):.1f}")
        dots = "".join(f'<circle cx="{c + R * math.sin(2 * math.pi * k / 36):.1f}" cy="{c - R * math.cos(2 * math.pi * k / 36):.1f}" '
                       f'r="{2.6 if k % 3 == 0 else 1.6}" class="{"d0" if k % 3 == 0 else "d1"}"/>' for k in range(36))
        tri = " ".join(f"{c + R * math.sin(2 * math.pi * k / 36):.1f},{c - R * math.cos(2 * math.pi * k / 36):.1f}" for k in (0, 11, 22))
        return (f'<svg viewBox="0 0 200 200" class="art" aria-hidden="true"><circle cx="{c}" cy="{c}" r="{R}" class="ring"/>'
                f'<polygon points="{tri}" class="tri"/><polyline points="{" ".join(pts)}" class="spiral"/>{dots}</svg>')
    pts = " ".join(f"{c + R * math.sin(2 * math.pi * (7 * k % 12) / 12):.1f},{c - R * math.cos(2 * math.pi * (7 * k % 12) / 12):.1f}"
                   for k in range(13))
    dots = "".join(f'<circle cx="{c + R * math.sin(2 * math.pi * k / 12):.1f}" cy="{c - R * math.cos(2 * math.pi * k / 12):.1f}" r="3" class="d0"/>'
                   for k in range(12))
    return (f'<svg viewBox="0 0 200 200" class="art" aria-hidden="true"><circle cx="{c}" cy="{c}" r="{R}" class="ring"/>'
            f'<polyline points="{pts}" class="star"/>{dots}</svg>')


def number_sections(ch, frag):
    num = chap_num(ch)[0]
    order = {s["id"]: i + 1 for i, s in enumerate(ch.get("sections", []))}

    def f(m):
        i = order.get(m[2])
        return m[0] if i is None else f'{m[1]}<span class="secnum">{f"{num}.{i}" if num else i}</span>'
    return re.sub(r'(<section id="([\w-]+)"[^>]*>\s*<h2[^>]*>)', f, frag)


def sidebar(toc, chapters, current_id, depth_prefix):
    out = ['<nav class="tree"><a class="home" href="' + depth_prefix + 'index.html">Contents</a><ul>']
    for part in toc["parts"]:
        cur_part = any(c["id"] == current_id for c in part["chapters"])
        chip, name = part_bits(part)
        label = f"{chip}{'. ' + name if name else ''}"
        out.append(f'<li class="part"><details{" open" if cur_part else ""}><summary data-part="{part["id"]}">'
                   f'<i class="dot"></i>{html.escape(label)}</summary><ul>')
        for c in part["chapters"]:
            cls = ' class="cur"' if c["id"] == current_id else ""
            n = chap_num(c)[0]
            out.append(f'<li{cls}><a href="{depth_prefix}chapters/{c["id"]}.html"><span class="n">{n}</span>'
                       f'<span>{html.escape(c["title"])}</span></a>')
            if c["id"] == current_id and c.get("sections"):
                out.append("<ul class='secs'>" + "".join(f'<li><a href="#{s["id"]}">{html.escape(s["title"])}</a></li>'
                                                          for s in c["sections"]) + "</ul>")
            out.append("</li>")
        out.append("</ul></details></li>")
    out.append("</ul></nav>")
    return "".join(out)


_ASSET_TEXT: dict = {}


def inline_assets(prefix: str) -> str:
    """Site CSS, KaTeX CSS and the page script inlined, so a page looks right however it is opened
    (file viewers and previews often refuse to load neighbouring files). Fonts stay as files."""
    if not _ASSET_TEXT:
        _ASSET_TEXT["css"] = open(os.path.join(ASSETS, "style.css"), encoding="utf-8").read()
        _ASSET_TEXT["js"] = open(os.path.join(ASSETS, "app.js"), encoding="utf-8").read()
        k = os.path.join(KATEX_DIST, "katex.min.css")
        _ASSET_TEXT["katex"] = open(k, encoding="utf-8").read() if os.path.exists(k) else ""
    katex = _ASSET_TEXT["katex"].replace("url(fonts/", f"url({prefix}assets/katex/fonts/")
    return (f"<style>{_ASSET_TEXT['css']}</style><style>{katex}</style>"
            f"<script>{_ASSET_TEXT['js']}</script>")


def social_meta(toc, chapters, current_id, title) -> str:
    """Description, canonical link, Open Graph and Twitter-card tags (absolute URLs from toc.yaml site_url)."""
    site = toc.get("site_url", "")
    ch = next((c for c in chapters if c["id"] == current_id), None) if current_id else None
    desc = (ch.get("summary") if ch else None) or toc.get("description") or toc.get("subtitle", "")
    tags = [f'<meta name="description" content="{html.escape(desc)}">',
            f'<meta name="author" content="{html.escape(toc.get("author", ""))}">']
    if site:
        # the Worker serves /chapters/x.html by redirecting to /chapters/x (auto-trailing-slash): use the final URL
        url = site + (f"chapters/{current_id}" if current_id else "")
        img = site + "assets/og-cover.png"
        og_title = html.escape(title)
        tags += [f'<link rel="canonical" href="{url}">',
                 '<meta property="og:type" content="' + ("article" if ch else "book") + '">',
                 f'<meta property="og:site_name" content="{html.escape(toc["title"])}">',
                 f'<meta property="og:title" content="{og_title}">',
                 f'<meta property="og:description" content="{html.escape(desc)}">',
                 f'<meta property="og:url" content="{url}">',
                 f'<meta property="og:image" content="{img}">',
                 '<meta property="og:image:type" content="image/png">',
                 '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">',
                 f'<meta property="og:image:alt" content="{html.escape(toc["title"])}: the golden spiral and the 36-note circle">',
                 '<meta name="twitter:card" content="summary_large_image">',
                 f'<meta name="twitter:title" content="{og_title}">',
                 f'<meta name="twitter:description" content="{html.escape(desc)}">',
                 f'<meta name="twitter:image" content="{img}">']
    return "".join(tags)


def page(title, body, toc, chapters, current_id, prefix, layers=True, part_id="front"):
    layer_ui = ('<div class="layers" role="group" aria-label="Depth"><span>Depth</span>'
                '<button data-layer="hear" aria-pressed="true">Hear it</button>'
                '<button data-layer="understand" aria-pressed="true">Understand it</button>'
                '<button data-layer="derive" aria-pressed="true">Derive it</button></div>') if layers else ""
    math_head = KATEX_CDN if CLIENT_MATH else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>{social_meta(toc, chapters, current_id, title)}{THEME_BOOT}{FONTS}
{inline_assets(prefix)}{math_head}</head>
<body data-part="{part_id}"><div class="progress"><i></i></div>
<header class="top"><button class="menu" aria-label="Contents">☰</button>
<a class="book" href="{prefix}index.html"><span class="phi">φ</span>{html.escape(toc["title"])}</a>{layer_ui}
<button class="theme" aria-label="Toggle light or dark theme" title="Light / dark">◐</button></header>
<div class="wrap"><aside class="side">{sidebar(toc, chapters, current_id, prefix)}</aside>
<main>{body}</main></div><a class="totop" href="#" aria-label="Back to top">↑</a></body></html>"""


def chapter_body(ch, frag, chapters, idx):
    names = {c["id"]: c for c in chapters}
    mir = ""
    if ch.get("mirror"):
        links = "".join(f'<a href="{m}.html"><b>{chap_num(names[m])[0]}</b> {html.escape(names[m]["title"])}</a>'
                        for m in ch["mirror"] if m in names)
        mir = f'<div class="mirrorlinks"><span>Mirror</span>{links}</div>'
    chip, pname = part_bits(ch["part"])
    num, label = chap_num(ch)
    secs = ch.get("sections", [])
    onpage = ('<nav class="onpage" aria-label="On this page">' + "".join(
        f'<a href="#{s["id"]}"><b>{f"{num}.{i}" if num else i}</b>{html.escape(s["title"])}</a>'
        for i, s in enumerate(secs, 1)) + "</nav>") if secs else ""
    art = hero_art("golden" if ch["part"]["id"] in GOLDEN_PARTS else "fifths")
    hero = (f'<header class="hero"><div class="hero-text"><div class="kicker"><span class="chip">{html.escape(chip)}</span>'
            f'{html.escape(pname)}</div>{f'<div class="chlabel">{label}</div>' if num else ""}<h1>{html.escape(ch["title"])}</h1>'
            f'<p class="summary">{html.escape(ch.get("summary", ""))}</p>{mir}</div><div class="hero-art">{art}</div></header>')

    def pn(c, cls, arrow):
        if not c:
            return "<span></span>"
        return (f'<a class="{cls}" href="{c["id"]}.html"><small>{arrow} {chap_num(c)[1]}</small>'
                f'<span>{html.escape(c["title"])}</span></a>')
    nav = ('<nav class="pn">' + pn(chapters[idx - 1] if idx > 0 else None, "prev", "←")
           + pn(chapters[idx + 1] if idx + 1 < len(chapters) else None, "next", "→") + "</nav>")
    return hero + onpage + number_sections(ch, frag) + nav


def placeholder(ch):
    secs = "".join(f'<section id="{s["id"]}"><h2>{html.escape(s["title"])}</h2><p class="todo">In preparation.</p></section>'
                   for s in ch.get("sections", []))
    return secs


def cover_art() -> str:
    """The cover: the classical golden spiral of quarter circles in nested golden rectangles, the 36-note ring at
    its eye, and three golden triads, one rooted on each layer (C, ^C, vC#), in the three layer colours."""
    phi = (1 + 5 ** 0.5) / 2
    S = 560.0
    x, y, w, h = 40.0, 70.0, S * phi, S
    sq, arcs = [], []
    for i in range(12):
        d = i % 4
        if d == 0:
            s_ = h; sq.append((x, y, s_)); arcs.append(((x, y + h), (x + h, y), s_)); x, w = x + h, w - h
        elif d == 1:
            s_ = w; sq.append((x, y, s_)); arcs.append(((x, y), (x + w, y + w), s_)); y, h = y + w, h - w
        elif d == 2:
            s_ = h; sq.append((x + w - h, y, s_)); arcs.append(((x + w, y), (x + w - h, y + h), s_)); w = w - h
        else:
            s_ = w; sq.append((x, y + h - w, s_)); arcs.append(((x + w, y + h), (x, y + h - w), s_)); h = h - w
    eye = (x + w / 2, y + h / 2)
    rects = "".join(f'<rect x="{a:.1f}" y="{b:.1f}" width="{c:.1f}" height="{c:.1f}" class="cv-sq"/>' for a, b, c in sq)
    path = "M {:.1f} {:.1f} ".format(*arcs[0][0]) + " ".join(
        f"A {r:.2f} {r:.2f} 0 0 1 {e[0]:.2f} {e[1]:.2f}" for _, e, r in arcs)
    R0 = 128.0
    pos = lambda k, r=R0: (eye[0] + r * math.sin(2 * math.pi * k / 36), eye[1] - r * math.cos(2 * math.pi * k / 36))  # noqa: E731
    dots = "".join(f'<circle cx="{pos(k)[0]:.1f}" cy="{pos(k)[1]:.1f}" r="{4.2 if k % 3 == 0 else 2.6}" class="cv-dot l{k % 3}"/>'
                   for k in range(36))
    tris = ""
    for root, layer in ((0, 0), (1, 1), (2, 2)):
        pts = " ".join("{:.1f},{:.1f}".format(*pos(root + iv)) for iv in (0, 11, 22))
        tris += f'<polygon points="{pts}" class="cv-tri l{layer}"/>'
    # drawn upside down (eye at the top right, clear of the title); a golden triad's mirror image is a golden triad
    return (f'<svg class="cover-art" viewBox="0 0 1000 720" preserveAspectRatio="xMaxYMin slice" aria-hidden="true">'
            f'<defs><radialGradient id="cvg" cx="{eye[0] / 10:.1f}%" cy="{(720 - eye[1]) / 7.2:.1f}%" r="75%">'
            f'<stop offset="0" stop-color="#3a2c10"/><stop offset="1" stop-color="#0c0b09"/></radialGradient></defs>'
            f'<rect width="1000" height="720" fill="url(#cvg)"/><g transform="translate(0 720) scale(1 -1)">'
            f'{rects}<path d="{path}" class="cv-spiral"/>'
            f'<circle cx="{eye[0]:.1f}" cy="{eye[1]:.1f}" r="{R0}" class="cv-ring"/>{tris}{dots}</g></svg>')


def _build_stamp() -> str:
    try:
        h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        h = ""
    import datetime
    return datetime.date.today().isoformat() + (f", commit {h}" if h else "")


def front_pages(toc) -> str:
    t, sub, au = (html.escape(toc.get(k, "")) for k in ("title", "subtitle", "author"))
    year, ed = toc.get("year", ""), html.escape(str(toc.get("edition", "")))
    pub = html.escape(toc.get("publisher", ""))
    cover = (f'<section class="book-cover">{cover_art()}<div class="cv-text">'
             f'<p class="cv-kicker">A textbook in ten parts</p><h1 class="cv-title">{t}</h1>'
             f'<p class="cv-sub">{sub}</p><p class="cv-author">{au}</p>'
             f'<p class="cv-ed">{ed} · {year}</p></div>'
             f'<a class="cv-open" href="#contents">Open the book ↓</a></section>')
    title = (f'<section class="book-sheet title-page"><p class="tp-orn">φ</p><h1>{t}</h1><p class="tp-sub">{sub}</p>'
             f'<p class="tp-author">{au}</p><p class="tp-pub">{pub} · {year}</p></section>')
    copy = (f'<section class="book-sheet copyright-page"><div>'
            f'<p><b>{t}</b><br>{ed}, {year}</p>'
            f'<p>Copyright © {year} {au}. {html.escape(toc.get("rights", ""))}</p>'
            f'<p>{pub}. No ISBN has been assigned to this edition.</p>'
            f'<p>{html.escape(toc.get("note", ""))}</p>'
            f'<p>Every audio and video example was generated from text with SongMap, the engine described in Part X: '
            f'clean additive instruments, exact 36-ET or exact-ratio tuning, no compression. Set for the web in Fraunces, '
            f'Source Serif 4 and Inter; mathematics typeset with KaTeX.</p>'
            f'<p>Built {_build_stamp()}.</p>'
            f'<p>Cite as: {au}, <i>{t}</i>, {ed.lower()} ({year}).</p></div></section>')
    epi = ""
    if toc.get("epigraph"):
        epi = (f'<section class="book-sheet epigraph"><blockquote>{html.escape(toc["epigraph"])}</blockquote>'
               f'<p class="ep-src">{html.escape(toc.get("epigraph_source", ""))}</p></section>')
    return cover + title + copy + epi


def index_body(toc, chapters):
    out = [front_pages(toc), '<h2 class="contents-title" id="contents">Contents</h2>',
           '<div class="trio">'
           '<div class="tri hear"><b>Hear it</b><p>Listening and intuition, in plain language with audio. No formulas.</p></div>'
           '<div class="tri understand"><b>Understand it</b><p>Concepts, notation, worked examples and tables, with light mathematics.</p></div>'
           '<div class="tri derive"><b>Derive it</b><p>Definitions, theorems, proofs and exact numbers, for the full fire hose.</p></div>'
           '</div>',
           '<p class="lead">Every chapter is written in these three layers; the Depth buttons at the top of each chapter '
           'show or hide them. Western theory (Parts I–V) and the golden tonal system (Parts VI–VIII) mirror each other '
           'chapter by chapter, and golden mirror boxes connect the two.</p>']
    for part in toc["parts"]:
        chip, name = part_bits(part)
        out.append(f'<section class="partcard" data-part="{part["id"]}"><div class="parthead"><span class="chip">{html.escape(chip)}</span>'
                   + (f'<h2>{html.escape(name)}</h2>' if name else "")
                   + (f'<p>{html.escape(part["summary"])}</p>' if part.get("summary") else "") + '</div><div class="tiles">')
        for c in part["chapters"]:
            n = chap_num(c)[0]
            out.append(f'<a class="tile" href="chapters/{c["id"]}.html"><span class="num">{n or "·"}</span>'
                       f'<span class="tt">{html.escape(c["title"])}</span><span class="ts">{html.escape(c.get("summary", ""))}</span></a>')
        out.append("</div></section>")
    return "".join(out)


# ------------------------------------------------------------------------------------------------
# main
# ------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate only (no files written)")
    ap.add_argument("--chapters", nargs="*", help="limit to these chapter ids")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--no-video", action="store_true", help="SongMap examples as audio players, no videos")
    ap.add_argument("--jobs", type=int, default=min(12, max(1, (os.cpu_count() or 2) - 1)), help="parallel renders")
    ap.add_argument("--test-audio", action="store_true",
                    help="with --chapters: render those chapters' audio into build/tbtest/<id>/ and report errors")
    args = ap.parse_args()
    global VIDEO
    VIDEO = not args.no_video and shutil.which("ffmpeg") is not None
    toc, chapters = load_toc()
    ids = {c["id"] for c in chapters}
    sec_ids = {c["id"]: {s["id"] for s in c.get("sections", [])} for c in chapters}
    problems, audio_jobs, audio_list, bodies = [], [], [], {}
    for idx, ch in enumerate(chapters):
        if args.chapters and ch["id"] not in args.chapters:
            continue
        if ch.get("generated") == "songbook":          # every song in songs/** (tools/textbook/songbook.py)
            if TOOLS not in sys.path:
                sys.path.insert(0, TOOLS)
            import songbook
            secs, frag = songbook.chapter(render=not (args.check or args.no_audio or args.test_audio),
                                          out_site=OUT, jobs=args.jobs)
            ch["sections"] = secs
            check_structure(ch, frag, problems)
            bodies[ch["id"]] = (idx, ch, frag)
            continue
        path = os.path.join(CONTENT, ch["id"] + ".html")
        if os.path.exists(path):
            frag = open(path, encoding="utf-8").read()
            check_structure(ch, frag, problems)
            frag = process(ch["id"], frag, ids, sec_ids, problems, audio_jobs, audio_list)
        else:
            if args.chapters:
                problems.append(f"{ch['id']}: no content file textbook/content/{ch['id']}.html")
            frag = placeholder(ch)
        bodies[ch["id"]] = (idx, ch, frag)
    global CLIENT_MATH
    rendered = render_tex([(t, d) for _, _, f in bodies.values() for _, _, t, d in find_math(f)])
    if rendered is None:
        CLIENT_MATH = True
        print("WARNING node/KaTeX unavailable (npm install in tools/textbook): math will render in the browser")
    else:
        for cid, (idx, ch, frag) in list(bodies.items()):
            bodies[cid] = (idx, ch, apply_math(cid, frag, rendered, problems))
    for p in problems:
        print("PROBLEM", p)
    print(f"{len(bodies)} chapters checked, {len(audio_list)} audio examples, {len(problems)} problems")
    if args.test_audio:
        bad = 0
        for src, dst in audio_jobs:
            if not src or src.startswith("copy:"):
                continue
            out = os.path.join(ROOT, "build", "tbtest", os.path.relpath(dst, os.path.join(OUT, "audio")))
            try:
                render_audio(src, out)
                print("  ok", os.path.relpath(out, ROOT), f"{os.path.getsize(out) // 1024} KB")
            except Exception as e:                                   # noqa: BLE001
                bad += 1
                print(f"PROBLEM audio {os.path.relpath(src, ROOT)}: {e}")
        sys.exit(1 if (problems or bad) else 0)
    if args.check:
        sys.exit(1 if problems else 0)

    os.makedirs(os.path.join(OUT, "chapters"), exist_ok=True)
    shutil.copytree(ASSETS, os.path.join(OUT, "assets"), dirs_exist_ok=True)
    if os.path.isdir(KATEX_DIST):
        kdst = os.path.join(OUT, "assets", "katex")
        os.makedirs(kdst, exist_ok=True)
        shutil.copy(os.path.join(KATEX_DIST, "katex.min.css"), kdst)
        shutil.copytree(os.path.join(KATEX_DIST, "fonts"), os.path.join(kdst, "fonts"), dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("*.ttf", "*.woff"))
    for cid, (idx, ch, frag) in bodies.items():
        if cid == "appG":
            rows = "".join(f'<tr><td><a href="{c}.html">{c}</a></td>'
                           f'<td>{html.escape(n.rsplit(".", 1)[0].replace("_", " "))}</td><td>{cap}</td>'
                           f'<td><audio controls preload="none" src="../{rel}"></audio></td></tr>'
                           for c, n, cap, rel in audio_list)
            frag = re.sub(r'(<section id="index">.*?)(</section>)', lambda m: m[1] + f'<table class="aidx"><tr><th>Ch.</th><th>Example</th><th>Description</th><th>Listen</th></tr>{rows}</table>' + m[2], frag, flags=re.S) \
                if '<section id="index">' in frag else frag + f'<table class="aidx">{rows}</table>'
        with open(os.path.join(OUT, "chapters", cid + ".html"), "w", encoding="utf-8") as f:
            f.write(page(ch["title"] + " · " + toc["title"], chapter_body(ch, frag, chapters, idx), toc, chapters, cid, "../",
                         part_id=ch["part"]["id"]))
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(page(toc["title"], index_body(toc, chapters), toc, chapters, None, "", layers=False))
    if not args.no_audio:
        cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
        vhash = _visual_hash() if VIDEO else ""
        done, songs = 0, []
        for src, dst in audio_jobs:
            if not src:
                continue
            if src.startswith("copy:"):
                s = src[5:]
                if os.path.exists(s):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy(s, dst)
                continue
            key = os.path.relpath(dst, OUT)
            hsh = file_hash(src)
            if src.endswith(".songmap.yaml"):
                mp4 = os.path.join(OUT, "video", os.path.relpath(dst, os.path.join(OUT, "audio")))[:-4] + ".mp4" if VIDEO else None
                want = hsh + ("|" + vhash if mp4 else "")
                if cache.get(key) == want and os.path.exists(dst) and (not mp4 or os.path.exists(mp4)):
                    continue
                songs.append(((src, dst, mp4), key, want))
                continue
            if cache.get(key) == hsh and os.path.exists(dst):
                continue
            try:
                render_audio(src, dst)
                cache[key] = hsh
                done += 1
                print("  audio", key)
            except Exception as e:                                   # noqa: BLE001
                print(f"PROBLEM audio {key}: {e}")
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            json.dump(cache, open(CACHE, "w"), indent=0)
        if songs:
            from concurrent.futures import ProcessPoolExecutor
            by_job = {job: (key, want) for job, key, want in songs}
            with ProcessPoolExecutor(max_workers=args.jobs) as pool:
                for job, err in pool.map(_media_job, list(by_job)):
                    key, want = by_job[job]
                    if err:
                        print(f"PROBLEM media {key}: {err}")
                        continue
                    cache[key] = want
                    done += 1
                    print("  " + ("video" if job[2] else "audio"), key)
                    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
                    json.dump(cache, open(CACHE, "w"), indent=0)
        print(f"rendered {done} examples" + (" (SongMap examples with video)" if VIDEO else ""))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
