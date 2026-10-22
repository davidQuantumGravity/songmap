"""Parsers: the SongMap language (.sm), YAML song maps, the note language, step strings, positions."""
from __future__ import annotations

import os


def load(path: str):
    """Any song map -> Song: `.sm`/`.sml` (the SongMap language) or YAML (`.yaml`, `.yml`, anything else)."""
    from .errors import SongError
    if not os.path.isfile(path):
        raise SongError(f"no such file: {path}")
    from . import lang
    if os.path.splitext(path)[1].lower() in lang.EXTS:
        return lang.load(path)
    from . import yaml_form
    return yaml_form.load(path)
