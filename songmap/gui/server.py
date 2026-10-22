"""SongMap Studio server (docs/GUI.md §5, §7): FastAPI over the engine, serving the built web app.

    songmap gui [song.sm] [--port 8765] [--no-browser]

Every path the API accepts is repo-relative and must stay inside the repo.
"""
from __future__ import annotations

import io
import os
import re
import threading
import webbrowser

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from .project import ROOT, SONG_EXTS, Project, list_files

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app = FastAPI(title="SongMap Studio")
_projects: dict[str, Project] = {}
_plock = threading.Lock()


def _abs(rel: str) -> str:
    p = os.path.abspath(os.path.join(ROOT, rel))
    if os.path.commonpath([p, ROOT]) != ROOT:
        raise HTTPException(400, f"path outside the repo: {rel}")
    return p


def project(rel: str) -> Project:
    p = _abs(rel)
    if not p.endswith(SONG_EXTS):
        raise HTTPException(400, f"not a song map: {rel}")
    with _plock:
        if p not in _projects:
            if not os.path.isfile(p):
                raise HTTPException(404, f"no such song: {rel}")
            _projects[p] = Project.open(p)
        return _projects[p]


# ---------------------------------------------------------------------------------------------- files
@app.get("/api/files")
def files():
    return list_files()


@app.get("/api/project")
def get_project(path: str = Query(...)):
    pr = project(path)
    return {"path": pr.rel, "text": pr.text, "check": pr.check()}


@app.post("/api/check")
def check(path: str = Body(...), text: str = Body(...)):
    return project(path).check(text)


@app.put("/api/project")
def save(path: str = Body(...), text: str = Body(...)):
    pr = project(path)
    pr.save(text)
    return {"path": pr.rel, "saved": True, "check": pr.check()}


@app.post("/api/new")
def new_song(path: str = Body(...), text: str = Body("")):
    p = _abs(path)
    if not p.endswith(SONG_EXTS):
        raise HTTPException(400, "a song file ends in .sm or .yaml")
    if os.path.exists(p):
        raise HTTPException(409, f"{path} exists")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    pr = Project(p, text or TEMPLATE)
    pr.save(pr.text)
    with _plock:
        _projects[p] = pr
    return {"path": pr.rel, "text": pr.text, "check": pr.check()}


TEMPLATE = """# A new song.
song "Untitled" 100 4/4 C fps=30 seed=1 tail=3
chords C Am F G
intro 4 | keys:hold dyn=p
verse 8 | keys:comp bass:sub drums:half lead:{deg: "=mf 4/4 2 0 2 | 4/2 5/2 | 4/4 2 0/2 | 1/1"} dyn=mf
"""


# ---------------------------------------------------------------------------------------------- audio
@app.post("/api/render")
def render(path: str = Body(...), text: str = Body(...), mute: list[str] = Body(default=[]),
           solo: list[str] = Body(default=[])):
    pr = project(path)
    chk = pr.check(text)
    if not chk["ok"]:
        return {"ok": False, "check": chk}
    rd = pr.render(text, tuple(mute), tuple(solo))
    return {"ok": True, "key": rd.key, "seconds": rd.seconds, "elapsed": round(rd.elapsed, 2), "remixed": rd.remixed,
            "audio": f"/api/audio?path={pr.rel}&key={rd.key}", "check": chk, "qa": pr.measure(rd)}


@app.get("/api/audio")
def audio(request: Request, path: str = Query(...), key: str = Query(...)):
    """The WAV, with byte ranges (the browser seeks with them)."""
    rd = project(path).last()
    if not rd or rd.key != key:
        raise HTTPException(404, "render it first")
    data, n = rd.wav, len(rd.wav)
    headers = {"Accept-Ranges": "bytes", "Cache-Control": "no-store"}
    rng = request.headers.get("range")
    m = re.fullmatch(r"bytes=(\d*)-(\d*)", rng or "")
    if not m or (not m.group(1) and not m.group(2)):
        return Response(data, media_type="audio/wav", headers=headers)
    if m.group(1):
        a, b = int(m.group(1)), int(m.group(2)) if m.group(2) else n - 1
    else:                                                  # bytes=-N: the last N bytes
        a, b = max(0, n - int(m.group(2))), n - 1
    if a >= n:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{n}"})
    b = min(b, n - 1)
    return Response(data[a:b + 1], status_code=206, media_type="audio/wav",
                    headers={**headers, "Content-Range": f"bytes {a}-{b}/{n}"})


# ---------------------------------------------------------------------------------------------- edits
@app.post("/api/op")
def op(path: str = Body(...), text: str = Body(...), op: str = Body(...), args: dict = Body(default={})):
    """A GUI edit as a text operation: returns the new text (the client keeps it as its state)."""
    pr = project(path)
    if op == "mix":
        if not pr.path.endswith((".sm", ".sml")):
            raise HTTPException(400, "the mixer edits .sm songs (convert a YAML song with `songmap fmt --to sm`)")
        from .mixer import set_mix
        new = set_mix(text, args["part"], gain_db=args.get("gain_db"), pan=args.get("pan"), sends=args.get("sends"),
                      default_gain=float(args.get("default_gain", 0)))
    elif op == "voice":
        if not pr.path.endswith((".sm", ".sml")):
            raise HTTPException(400, "the rack edits .sm songs (convert a YAML song with `songmap fmt --to sm`)")
        from .rack import set_voice
        try:
            new = set_voice(text, args["part"], use=args.get("use"), params=args.get("params"), piece=args.get("piece"),
                            current_use=args.get("current_use"), clear=bool(args.get("clear")))
        except ValueError as e:
            raise HTTPException(400, str(e)) from None
    else:
        raise HTTPException(400, f"unknown op {op}")
    return {"text": new, "check": pr.check(new)}


@app.get("/api/catalog")
def get_catalog():
    from .rack import catalog
    return catalog()


@app.post("/api/audition")
def audition(path: str = Body(...), text: str = Body(...), part: str = Body(...), notes: list[dict] = Body(...),
             piece: str | None = Body(None), overrides: dict = Body(default={})):
    """A few notes played by one part's voice (with unsaved knob overrides), as WAV."""
    from ..parse.errors import NotationError, SongError
    from .project import parse_text, wav_bytes
    from .rack import audition as play
    pr = project(path)
    try:
        audio = play(parse_text(text, pr.path), part, notes[:64], piece, overrides)
    except (SongError, NotationError, ValueError) as e:
        raise HTTPException(400, getattr(e, "message", None) or str(e)) from None
    return Response(wav_bytes(audio), media_type="audio/wav", headers={"Cache-Control": "no-store"})


# ---------------------------------------------------------------------------------------------- visuals
@app.post("/api/frame")
def frame(path: str = Body(...), text: str = Body(...), t: float = Body(0.0), view: dict = Body(default={})):
    """One video frame at time t, as PNG (the video pane's live preview)."""
    pr = project(path)
    from ..arrange.expand import expand
    from ..visual.draw import Renderer
    from ..visual.score import score_of
    from .project import parse_text
    song = parse_text(text, pr.path)
    size = tuple(view.get("size", (1280, 720)))
    rnd = Renderer(score_of(expand(song), view.get("parts")), size=size, theme=view.get("theme", "light"),
                   page_seconds=float(view.get("page_seconds", 6.0)))
    buf = io.BytesIO()
    rnd.frame(max(0.0, float(t))).save(buf, "PNG")
    return Response(buf.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"})


# ---------------------------------------------------------------------------------------------- export
@app.post("/api/export")
def export(path: str = Body(...), text: str = Body(...), formats: list[str] = Body(...), view: dict = Body(default={})):
    pr = project(path)
    chk = pr.check(text)
    if not chk["ok"]:
        return {"ok": False, "check": chk}
    return {"ok": True, "files": pr.export(formats, text, view)}


@app.get("/api/file")
def get_file(path: str = Query(...)):
    p = _abs(path)
    if not os.path.isfile(p):
        raise HTTPException(404, path)
    return FileResponse(p)


# ---------------------------------------------------------------------------------------------- web app
@app.get("/", response_class=HTMLResponse)
def index():
    idx = os.path.join(STATIC, "index.html")
    if not os.path.exists(idx):
        return HTMLResponse("<h1>SongMap Studio</h1><p>The web app is not built: run "
                            "<code>npm install && npm run build</code> in <code>songmap/gui/web</code>.</p>")
    with open(idx, encoding="utf-8") as f:
        return HTMLResponse(f.read())


if os.path.isdir(os.path.join(STATIC, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC, "assets")), name="assets")


def _warm() -> None:
    """Import the engine and render a short song in the background, so the first check and render in the
    browser don't pay for imports and JIT compilation."""
    try:
        from ..render import render
        from .project import parse_text
        render(parse_text(TEMPLATE, os.path.join(ROOT, "songs", "_warm.sm")))
    except Exception:                                   # noqa: BLE001  (warming is best-effort)
        pass


def serve(song: str | None = None, port: int = 8765, open_browser: bool = True) -> None:
    import uvicorn
    threading.Thread(target=_warm, daemon=True).start()
    url = f"http://127.0.0.1:{port}/" + (f"?song={os.path.relpath(os.path.abspath(song), ROOT).replace(os.sep, '/')}"
                                         if song else "")
    if open_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    print(f"SongMap Studio on {url}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
