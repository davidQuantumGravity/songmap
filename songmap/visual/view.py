"""Views: what a song's video (and poster) shows, where and how.

A view lives next to the song as `<song>.view.yaml` (it is design, not music, so it stays out of the `.sm`):

    size: [1920, 1080]
    theme: dark
    colors: {bg: "#101418", accent: "#e3b54a"}       # override theme colours (bg panel ink muted line grid gold ...)
    page_seconds: 6
    parts: [lead, keys]                               # which parts the staff and roll show (none = every pitched part)
    color_by: part                                    # notes coloured by 36-EDO layer (spelling) or by part
    part_colors: {lead: "#e3b54a"}
    layers:                                           # drawn in this order; box = [x, y, w, h] as fractions of the frame
      - {type: header, box: [.02, .036, .96, .086]}
      - {type: staff, box: [.02, .264, .96, .458], veil: true}
      - {type: text, box: [.1, .4, .8, .2], text: "Chapter 1", size: .08, from: 0, to: 4}

Layer types: header (title, section, bar, chord chip), letters (the sounding notes' names), staff (grand staff,
paged), roll (a scrolling piano roll; `before`/`after` seconds around the playhead), progress (a bar), sections
(a strip of the song's sections with the playhead), text (a caption, optionally only between `from` and `to`).
Every layer takes `show: false` to hide it and `panel: false` to drop its rounded background.
The default view is the classic layout; a view file only needs what it changes.
"""
from __future__ import annotations

import copy
import os

LAYER_TYPES = ("header", "letters", "staff", "roll", "instrument", "progress", "sections", "text")
# the classic 1280x720 layout, as fractions (Renderer before views)
DEFAULT_LAYERS = [
    {"type": "header", "box": [26 / 1280, 26 / 720, 1228 / 1280, 62 / 720], "title": True, "info": True, "chord": True},
    {"type": "letters", "box": [26 / 1280, 96 / 720, 1228 / 1280, 84 / 720]},
    {"type": "staff", "box": [26 / 1280, 190 / 720, 1228 / 1280, 330 / 720], "veil": True, "chords": True, "bars": True},
    {"type": "roll", "box": [26 / 1280, 530 / 720, 1228 / 1280, 156 / 720], "before": 2.0, "after": 6.0},
    {"type": "progress", "box": [26 / 1280, 702 / 720, 1228 / 1280, 12 / 720], "panel": False},
]
DEFAULT = {"size": [1280, 720], "theme": "light", "colors": {}, "page_seconds": 6.0, "parts": None,
           "color_by": "spelling", "part_colors": {}, "layers": DEFAULT_LAYERS}
SIZES = {"720p": [1280, 720], "1080p": [1920, 1080], "square": [1080, 1080], "vertical": [1080, 1920], "4k": [3840, 2160]}


def default() -> dict:
    return copy.deepcopy(DEFAULT)


def resolve(view: dict | None) -> dict:
    """A view merged over the default and checked (raises ValueError with what is wrong)."""
    v = default()
    for k, x in (view or {}).items():
        if k not in DEFAULT:
            raise ValueError(f"view: unknown key '{k}' (keys: {', '.join(DEFAULT)})")
        v[k] = copy.deepcopy(x)
    if isinstance(v["size"], str):
        v["size"] = SIZES.get(v["size"]) or _bad(f"size '{v['size']}' (named sizes: {', '.join(SIZES)})")
    w, h = (int(x) for x in v["size"])
    if not (64 <= w <= 7680 and 64 <= h <= 7680):
        _bad(f"size {w}x{h} out of range")
    v["size"] = [w - w % 2, h - h % 2]                      # H.264 needs even sizes
    if v["theme"] not in ("light", "dark"):
        _bad(f"theme '{v['theme']}' (light or dark; colours: override any of them)")
    if v["color_by"] not in ("spelling", "part"):
        _bad("color_by is spelling or part")
    for i, layer in enumerate(v["layers"]):
        if layer.get("type") not in LAYER_TYPES:
            _bad(f"layer {i + 1}: type '{layer.get('type')}' (types: {', '.join(LAYER_TYPES)})")
        box = layer.get("box")
        if not (isinstance(box, (list, tuple)) and len(box) == 4 and all(isinstance(b, (int, float)) for b in box)):
            _bad(f"layer {i + 1} ({layer['type']}): box is [x, y, w, h] as fractions of the frame")
        if box[2] <= 0 or box[3] <= 0:
            _bad(f"layer {i + 1} ({layer['type']}): the box needs a width and a height")
        if layer["type"] == "instrument":
            if layer.get("style", "score") not in ("score", "performance"):
                _bad(f"layer {i + 1}: instrument style is score or performance")
            for setting in ("note_chips", "pitch_strip", "glow"):
                if setting in layer and not isinstance(layer[setting], bool):
                    _bad(f"layer {i + 1}: instrument {setting} must be true or false")
            if layer.get("mode", "bar") not in ("bar", "active"):
                _bad(f"layer {i + 1}: instrument mode is bar or active")
            bars = layer.get("bars", 1)
            if isinstance(bars, bool) or not isinstance(bars, int) or bars < 1:
                _bad(f"layer {i + 1}: instrument bars must be a positive integer")
            parts = layer.get("parts")
            if parts is not None and (not isinstance(parts, list) or not all(isinstance(p, str) for p in parts)):
                _bad(f"layer {i + 1}: instrument parts must be a list of part names")
    return v


def _bad(msg: str):
    raise ValueError("view: " + msg)


def path_for(song_path: str) -> str:
    base = song_path
    for ext in (".sm", ".sml", ".yaml", ".yml"):
        if base.endswith(ext):
            base = base[: -len(ext)]
            break
    return base + ".view.yaml"


def load(song_path: str) -> dict | None:
    """The song's view file, if it has one (unmerged: what the file says)."""
    p = path_for(song_path)
    if not os.path.isfile(p):
        return None
    import yaml
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save(song_path: str, view: dict) -> str:
    """Write the view file: only what differs from the default (layers are written whole)."""
    import yaml
    resolve(view)
    d = default()
    out = {k: v for k, v in view.items() if k in DEFAULT and v != d[k]}
    p = path_for(song_path)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("# What this song's video shows (songmap/visual/view.py). Edited in SongMap Studio's video designer.\n")
        yaml.safe_dump(out, f, sort_keys=False, allow_unicode=True, default_flow_style=None)
    return p
