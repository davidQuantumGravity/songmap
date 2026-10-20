"""Presets: `presets/<instrument>/<name>.yaml`, referenced as `instrument/name`.

    instrument: kick
    base: default            # or another preset of the same instrument to inherit from
    description: ...
    tags: [...]
    params: {tune: 50, ...}
"""
from __future__ import annotations

import os
from functools import lru_cache

import yaml

from .base import REGISTRY, ParamError

PRESET_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "presets")


def list_presets() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    if not os.path.isdir(PRESET_DIR):
        return out
    for inst in sorted(os.listdir(PRESET_DIR)):
        d = os.path.join(PRESET_DIR, inst)
        if os.path.isdir(d):
            out[inst] = sorted(f[:-5] for f in os.listdir(d) if f.endswith(".yaml"))
    return out


@lru_cache(maxsize=None)
def _load(ref: str) -> tuple[str, tuple]:
    inst, _, name = ref.partition("/")
    path = os.path.join(PRESET_DIR, inst, name + ".yaml")
    if not os.path.isfile(path):
        if inst not in REGISTRY:
            from ..parse.errors import did_you_mean
            raise ParamError(f"unknown instrument '{inst}' in '{ref}'; {did_you_mean(inst, REGISTRY)}")
        from ..parse.errors import did_you_mean
        raise ParamError(f"unknown preset '{ref}'; {did_you_mean(name, list_presets().get(inst, []))}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if data.get("instrument", inst) != inst:
        raise ParamError(f"preset {path} declares instrument '{data['instrument']}', expected '{inst}'")
    params = {}
    base = data.get("base", "default")
    if base and base != "default":
        params.update(_load(f"{inst}/{base}" if "/" not in base else base)[1])
    params.update(data.get("params") or {})
    return inst, tuple(sorted(params.items()))


def resolve(ref: str) -> tuple[str, dict]:
    """'pad/warm' -> ('pad', {params}); 'pad' -> ('pad', {})."""
    if "/" not in ref:
        return ref, {}
    inst, params = _load(ref)
    return inst, dict(params)


def preset_info(ref: str) -> dict:
    inst, _, name = ref.partition("/")
    with open(os.path.join(PRESET_DIR, inst, name + ".yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
