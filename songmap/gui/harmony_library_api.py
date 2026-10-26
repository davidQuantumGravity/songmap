"""Read-only Harmony Library routes, independent of score/project state."""
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, Response

from . import project
from .harmony_library import HarmonyLibrary, realization, render_preview

router = APIRouter(prefix="/api/harmony", tags=["harmony-library"])


@lru_cache(maxsize=4)
def _store(root: str):
    return HarmonyLibrary(root)


def store():
    return _store(project.ROOT)


def entry(kind: str, entry_id: str):
    try:
        return store().get(kind, entry_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from None


@router.get("/meta")
def meta():
    return store().metadata()


@router.get("/export")
def export():
    return JSONResponse(store().export(), headers={"Content-Disposition": 'attachment; filename="songmap-harmony-library.json"'})


@router.get("/{kind}")
def search(kind: str, q: str = Query("", max_length=300), family: str = "", mode: str = "",
           limit: int = Query(500, ge=1, le=1000)):
    try:
        return {"items": store().search(kind, q, family, mode, limit)}
    except ValueError as e:
        raise HTTPException(400, str(e)) from None


@router.get("/{kind}/{entry_id}")
def detail(kind: str, entry_id: str, tonic: str = "C", bpm: int = Query(100, ge=60, le=180)):
    item = entry(kind, entry_id)
    try:
        return {"entry": item, "realization": realization(item, tonic, bpm)}
    except ValueError as e:
        raise HTTPException(400, str(e)) from None


@lru_cache(maxsize=12)
def _audio(kind: str, entry_id: str, tonic: str, bpm: int, root: str) -> bytes:
    from .project import wav_bytes
    item = _store(root).get(kind, entry_id)
    return wav_bytes(render_preview(realization(item, tonic, bpm)))


@router.get("/{kind}/{entry_id}/audio")
def audio(kind: str, entry_id: str, tonic: str = "C", bpm: int = Query(100, ge=60, le=180)):
    entry(kind, entry_id)
    try:
        data = _audio(kind, entry_id, tonic, bpm, project.ROOT)
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    return Response(data, media_type="audio/wav", headers={"Cache-Control": "private, max-age=3600"})
