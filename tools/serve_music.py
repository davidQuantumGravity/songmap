"""Local music preview with byte-range seeking and generated-site junctions.

Run from the repository: .venv/Scripts/python tools/serve_music.py 56855
Uses the web dependencies already installed for SongMap Studio.
"""
from pathlib import Path
import argparse
import json
import os

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
import uvicorn

ROOT = Path(__file__).resolve().parents[1]


class MusicFiles(StaticFiles):
    """Retain existing URLs for workspace assets during the repository move."""
    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code != 404:
                raise
            return await StaticFiles(directory=ROOT.parent, html=True, follow_symlink=True).get_response(path, scope)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", type=int, nargs="?", default=56855)
    args = parser.parse_args()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/", MusicFiles(directory=ROOT, html=True, follow_symlink=True))
    (ROOT / "build").mkdir(exist_ok=True)
    (ROOT / "build/golden_worlds_server.json").write_text(json.dumps({"port": args.port, "pid": os.getpid(),
        "url": f"http://127.0.0.1:{args.port}/songs/golden_adagio/", "command": "tools/serve_music.py"}))
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
