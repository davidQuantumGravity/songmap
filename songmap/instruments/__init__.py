"""Instruments: the Param/Note/Instrument contract, the registry, presets and the suite.

`make('pad')` builds an instrument with default params; `make('pad/warm', cutoff=900)` starts
from a preset (`presets/pad/warm.yaml`) and applies overrides on top.
"""
from . import drums, bass, synth, strings, keys, fx  # noqa: F401,I001  (registers the suite, in catalog order)
from .base import REGISTRY, Instrument, Note, Param, ParamError, describe, register
from .base import make as _make
from .presets import list_presets, resolve


def make(name: str, **params) -> Instrument:
    inst, preset = resolve(name)
    return _make(inst, **{**preset, **params})
