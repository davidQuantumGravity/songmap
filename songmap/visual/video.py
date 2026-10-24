"""Song -> MP4: the rendered audio with note-synchronised visuals (songmap.visual.draw), via ffmpeg.

    write_video(song, "out.mp4")                       # renders the audio too
    write_video(song, "out.mp4", audio_wav="x.wav")    # reuse an existing render of the same song
    write_poster(song, "poster.png", t=None)           # one frame (default: the first chord change)
"""
from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile

from .draw import Renderer
from .score import score_of


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg not found on PATH; install it to write videos")
    return exe


def _arrangement(song):
    from ..arrange.expand import expand
    return expand(song)


def write_video(song, out: str, *, fps: int = 30, size=(1280, 720), theme: str = "light",
                page_seconds: float = 6.0, parts: list[str] | None = None, audio_wav: str | None = None,
                master_mode: str | None = None, crf: int = 20, log=None, view: dict | None = None) -> str:
    """Write `out` (.mp4, H.264 + AAC). Returns the path. `view` (visual/view.py) overrides size, theme,
    page_seconds and parts, and chooses the layers."""
    tmp = None
    if audio_wav is None:
        from ..export.wav import write_wav24
        from ..render import render
        r = render(song, master_mode=master_mode)
        arr = r.arrangement
        tmp = tempfile.mkdtemp(prefix="songmap_video_")
        audio_wav = os.path.join(tmp, "song.wav")
        write_wav24(audio_wav, r.audio)
    else:
        arr = _arrangement(song)
    try:
        score = score_of(arr, parts if parts is not None or not view else view.get("parts"))
        rend = Renderer(score, size, theme, page_seconds, view=view)
        n = max(1, math.ceil(score.seconds * fps))
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        W, H = rend.W, rend.H
        cmd = [_ffmpeg(), "-y", "-loglevel", "error",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
               "-i", audio_wav, "-map", "0:v", "-map", "1:a",
               "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        try:
            for i in range(n):
                proc.stdin.write(rend.frame(i / fps).tobytes())
                if log and i and i % (fps * 10) == 0:
                    log(f"  video {i / fps:.0f}/{score.seconds:.0f} s")
        finally:
            proc.stdin.close()
            code = proc.wait()
        if code:
            raise RuntimeError(f"ffmpeg failed ({code}) writing {out}")
        return out
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def write_poster(song, out: str, *, t: float | None = None, size=(1280, 720), theme: str = "light",
                 page_seconds: float = 6.0, parts: list[str] | None = None, view: dict | None = None) -> str:
    """One frame as an image (video poster / still). Default: just after the second chord or first note."""
    score = score_of(_arrangement(song), parts if parts is not None or not view else view.get("parts"))
    if t is None:
        first = score.notes[0].start if score.notes else 0.0
        t = score.chords[1].start + 0.05 if len(score.chords) > 1 else min(first + 0.25, score.seconds / 2)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    image = Renderer(score, size, theme, page_seconds, view=view).frame(t)
    options = {"quality": 95, "subsampling": 0} if os.path.splitext(out)[1].lower() in (".jpg", ".jpeg") else {}
    image.save(out, **options)
    return out
