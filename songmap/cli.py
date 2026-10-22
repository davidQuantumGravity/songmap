"""songmap command line.

    songmap check  song.sm|song.yaml          parse, validate, expand; prints a summary or precise errors
    songmap render song.sm [-o build/x]       song.wav (24-bit), stems/, cues.json, qa.json, render.log  [--mp3]
    songmap migrate old.yaml [-o new.yaml]    rewrite a v0.1 song map as v0.2
    songmap fmt song.yaml --to sm [-o x.sm]   print a song map as .sm or YAML (lossless)
    songmap listen song.sm [--render DIR]     an automated ear: what a listener would notice (exit 2 on problems)
    songmap describe [--compact]              the catalog an LLM needs: styles, instruments, events, syntax
    songmap video  song.sm [-o song.mp4]      MP4 with letter names, staff and piano roll, sounding notes lit

Song maps are `.sm` (the SongMap language, docs/LANGUAGE.md; `.sml` is an alias) or YAML (`.yaml`, `.yml`).
Exit codes: 0 ok, 1 song error, 2 usage error.
"""
from __future__ import annotations

import argparse
import os
import sys

from . import __version__
from .parse.errors import NotationError, SongError


def _load(path: str):
    from .parse import load
    return load(path)


def _summary(arr) -> str:
    tl, song = arr.timeline, arr.song
    m, s = divmod(tl.seconds, 60)
    lines = [f"ok: {song.title}",
             f"  {len(tl.sections)} sections, {tl.total_bars:g} bars at {song.tempo:g} BPM {song.meter[0]}/{song.meter[1]}, "
             f"{int(m)}:{s:05.2f} ({tl.frames} frames @ {tl.fps} fps)",
             f"  parts: " + ", ".join(f"{p} {n}" for p, n in arr.counts().items()),
             f"  events: {len(arr.events)}   digest {arr.digest()[:16]}"]
    return "\n".join(lines)


def _video_check(arr) -> list[str]:
    v = arr.song.video or {}
    if "frames" not in v:
        return []
    want, got = int(v["frames"]), arr.timeline.frames
    if want == got:
        return []
    per_bar = arr.timeline.beat_to_frame(arr.timeline.bpb)
    msg = f"song is {got} frames but video {v.get('composition', '')} is {want} ({got - want:+d})"
    if abs(got - want) > per_bar:
        raise SongError(msg, file=arr.song.file, suggestion="check section bars and tail_seconds")
    return [msg]


def cmd_check(args) -> int:
    from .arrange.expand import expand
    song = _load(args.song)
    arr = expand(song)
    arr.ensemble.check(song.parts())
    warnings = list(song.warnings) + arr.warnings + _video_check(arr)
    if not arr.timeline.whole_frame_beats():
        warnings.append(f"60*fps/tempo is not an integer: beats do not land on whole video frames")
    print(_summary(arr))
    if song.binaural:
        from .mix.binaural import describe, plan
        for i, line in enumerate(describe(plan(song, arr.timeline))):
            print(("  binaural (headphones): " if i == 0 else " " * 26) + line)
    for w in warnings:
        print(f"  warning: {w}")
    return 0


def cmd_render(args) -> int:
    from .render import render, write_outputs
    song = _load(args.song)
    out = args.out or os.path.join("build", os.path.splitext(os.path.basename(args.song))[0].split(".")[0])
    r = render(song, master_mode=args.master, log=print)
    paths = write_outputs(r, out, stems=not args.no_stems, mp3=args.mp3)
    print(_summary(r.arrangement))
    for w in list(song.warnings) + r.arrangement.warnings + _video_check(r.arrangement):
        print(f"  warning: {w}")
    print(f"wrote {paths['song']}, {paths['cues']}, {paths['qa']}" + (", stems/" if "stems" in paths else "")
          + (f", {paths['mp3']}" if "mp3" in paths else ""))
    return 0


def cmd_video(args) -> int:
    from .visual import write_poster, write_video
    song = _load(args.song)
    stem = os.path.splitext(os.path.basename(args.song))[0].split(".")[0]
    out = args.out or os.path.join("build", stem, stem + ".mp4")
    try:
        w, h = (int(x) for x in args.size.lower().split("x"))
    except ValueError:
        print(f"error: --size must look like 1280x720, not {args.size}", file=sys.stderr)
        return 2
    parts = args.parts.split(",") if args.parts else None
    if args.poster:
        print("wrote", write_poster(song, args.poster, size=(w, h), theme=args.theme, parts=parts))
    write_video(song, out, fps=args.fps, size=(w, h), theme=args.theme, parts=parts, master_mode=args.master, log=print)
    print(f"wrote {out}")
    return 0


def cmd_migrate(args) -> int:
    from .parse import yaml_form
    raw = yaml_form.load_raw(args.song)
    if not yaml_form.is_v01(raw):
        print(f"{args.song} is already v{raw['songmap']}; nothing to do", file=sys.stderr)
        return 0
    new, notes = yaml_form.migrate(raw)
    text = yaml_form.dump(new, yaml_form.leading_comments(args.song))
    yaml_form.from_raw(yaml_form.load_raw_text(text), file=args.out or "<migrated>")   # must parse as v0.2
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    for n in notes:
        print(f"  {n}", file=sys.stderr)
    return 0


def _write(text: str, out: str | None) -> None:
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"wrote {out}", file=sys.stderr)
    else:
        sys.stdout.write(text)


def cmd_fmt(args) -> int:
    from .parse import fmt, yaml_form
    song = _load(args.song)
    to = {"compact": "sm", "sml": "sm"}.get(args.to, args.to)
    header = yaml_form.leading_comments(args.song)
    text = fmt.to_sm(song, header) if to == "sm" else fmt.to_yaml(song, header)
    _write(text, args.out)
    return 0


def cmd_listen(args) -> int:
    from .listen import listen_file
    rep = listen_file(args.song, qa_path=args.qa, render_dir=args.render)
    print(rep.text())
    if args.json:
        import json
        _write(json.dumps(rep.to_dict(), indent=1) + "\n", args.json)
    return 2 if rep.counts()["problem"] else 0


def cmd_describe(args) -> int:
    from .describe import catalog
    _write(catalog(compact=args.compact), args.out)
    return 0


def cmd_gui(args) -> int:
    from .gui.server import serve
    serve(args.song, port=args.port, open_browser=not args.no_browser)
    return 0


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(
        prog="songmap", description="SongMap: song maps -> audio, stems and frame-accurate cues",
        epilog="Song maps are .sm files in the SongMap language (docs/LANGUAGE.md, docs/COMPACT_FORMAT.md; "
               ".sml is an alias) or YAML (.yaml, docs/SONGMAP_SPEC.md). Exit codes: 0 ok, 1 song error, 2 usage.")
    ap.add_argument("--version", action="version", version=f"songmap {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check", help="parse, validate and expand a song map (fast, no audio)")
    p.add_argument("song", help="a .sm (.sml) or .yaml song map")
    p.set_defaults(fn=cmd_check)
    p = sub.add_parser("render", help="render song.wav, stems/, cues.json, qa.json")
    p.add_argument("song", help="a .sm (.sml) or .yaml song map")
    p.add_argument("-o", "--out", help="output folder (default build/<song>)")
    p.add_argument("--no-stems", action="store_true", help="skip stems/*.wav")
    p.add_argument("--mp3", action="store_true", help="also write song.mp3 (needs ffmpeg)")
    p.add_argument("--master", choices=["standard", "legacy", "clean"], help="override the song's master")
    p.set_defaults(fn=cmd_render)
    p = sub.add_parser("video", help="render an MP4: letter names, staff and piano roll with the sounding notes lit")
    p.add_argument("song", help="a .sm (.sml) or .yaml song map")
    p.add_argument("-o", "--out", help="output .mp4 (default build/<song>/<song>.mp4)")
    p.add_argument("--size", default="1280x720", help="frame size WxH (default 1280x720)")
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--theme", choices=["light", "dark"], default="light")
    p.add_argument("--parts", help="comma-separated parts to show (default: every pitched part)")
    p.add_argument("--poster", help="also write one frame as a PNG here")
    p.add_argument("--master", choices=["standard", "legacy", "clean"], help="override the song's master")
    p.set_defaults(fn=cmd_video)
    p = sub.add_parser("migrate", help="rewrite a v0.1 song map as v0.2")
    p.add_argument("song")
    p.add_argument("-o", "--out", help="write here instead of stdout")
    p.set_defaults(fn=cmd_migrate)
    p = sub.add_parser("fmt", help="print a song map as .sm or YAML (lossless; keeps leading comments)")
    p.add_argument("song", help="a .sm (.sml) or .yaml song map")
    p.add_argument("--to", choices=["sm", "compact", "sml", "yaml"], required=True, help="output format")
    p.add_argument("-o", "--out", help="write here instead of stdout")
    p.set_defaults(fn=cmd_fmt)
    p = sub.add_parser("listen", help="an automated ear: clashes, crowding, repetition, flat dynamics, contrast")
    p.add_argument("song", help="a .sm (.sml) or .yaml song map")
    p.add_argument("--render", metavar="DIR", help="also judge loudness from an existing render folder's qa.json "
                   "(it does not render; `songmap render` writes the full report to review.json)")
    p.add_argument("--qa", help="a qa.json to judge loudness from")
    p.add_argument("--json", metavar="FILE", help="also write the report as JSON")
    p.set_defaults(fn=cmd_listen)
    p = sub.add_parser("describe", help="the catalog for writing song maps: styles, instruments, events, syntax")
    p.add_argument("--compact", action="store_true", help="the ~500-token version for an LLM's context")
    p.add_argument("-o", "--out", help="write here instead of stdout")
    p.set_defaults(fn=cmd_describe)
    p = sub.add_parser("gui", help="SongMap Studio: edit songs, instruments, mixes and videos in the browser")
    p.add_argument("song", nargs="?", help="a song to open")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true", help="don't open a browser window")
    p.set_defaults(fn=cmd_gui)
    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except (SongError, NotationError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
