"""Styles are data: `patterns/<role>/<style>.yaml` (ENGINE.md §4).

Four shapes, told apart by their keys:

| Keys                     | Shape                                                              |
|--------------------------|--------------------------------------------------------------------|
| `steps` (+ `mods`, `chance`, `pan_random`) | kit pattern: one step string per kit piece        |
| `rel` (+ `oct`, `gate`)  | chord-relative figure, looped from the section start (bass)        |
| `hold: chord` + `rel`    | one voicing per chord change, held for the whole chord (pads)      |
| `grid` + `order`         | arpeggio over the current chord's tones (indices wrap up octaves)  |

Common keys: `preset` (applies that preset's own params when the part plays that instrument),
`params` (instrument overrides), `gain_db`, `aliases`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

import yaml

from ..parse.errors import SongError, did_you_mean

PATTERN_DIR = os.path.join(os.path.dirname(__file__), "patterns")
COMMON = ("style", "role", "aliases", "preset", "params", "gain_db", "bars", "description")
SHAPES = {
    "kit": ("steps", "mods", "chance", "pan_random"),
    "rel": ("rel", "oct", "gate", "art"),
    "hold": ("hold", "rel", "oct", "gate"),
    "arp": ("grid", "order", "oct", "len", "pan_lfo", "brightness_ramp"),
}


@dataclass(frozen=True)
class Style:
    name: str
    role: str
    shape: str
    data: dict
    path: str

    def get(self, k, default=None):
        return self.data.get(k, default)


def _shape(d: dict, path: str) -> str:
    if "steps" in d:
        shape = "kit"
    elif d.get("hold") == "chord":
        shape = "hold"
    elif "grid" in d:
        shape = "arp"
    elif "rel" in d:
        shape = "rel"
    else:
        raise SongError(f"style {path}: needs steps:, rel:, hold: chord or grid:")
    bad = [k for k in d if k not in COMMON + SHAPES[shape]]
    if bad:
        raise SongError(f"style {path}: unknown key '{bad[0]}' for a {shape} style",
                        suggestion=did_you_mean(bad[0], COMMON + SHAPES[shape]))
    return shape


@lru_cache(maxsize=None)
def load_styles() -> dict[str, dict[str, Style]]:
    out: dict[str, dict[str, Style]] = {}
    for role in sorted(os.listdir(PATTERN_DIR)):
        d = os.path.join(PATTERN_DIR, role)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith(".yaml"):
                continue
            path = os.path.join(d, f)
            with open(path, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            name = data.get("style", f[:-5])
            st = Style(name, data.get("role", role), _shape(data, path), data, path)
            for n in [name, *data.get("aliases", [])]:
                out.setdefault(st.role, {})[n] = st
    return out


def get_style(role: str, name: str) -> Style:
    styles = load_styles()
    if role not in styles:
        raise SongError(f"no styles for role '{role}'",
                        suggestion=f"roles with styles: {' '.join(styles)}; or give notes:/motifs/steps")
    if name not in styles[role]:
        raise SongError(f"unknown {role} style '{name}'", suggestion=did_you_mean(name, styles[role]))
    return styles[role][name]


def catalog() -> dict[str, list[str]]:
    """role -> style names (aliases excluded), for `describe`."""
    return {role: sorted({s.name for s in d.values()}) for role, d in load_styles().items()}
