"""Instruments: the Param/Note/Instrument contract, the registry, presets and the suite.

`make('pad')` builds an instrument with default params; `make('pad/warm', cutoff=900)` starts
from a preset (`presets/pad/warm.yaml`) and applies overrides on top. `make('sampler/salamander')`
loads a sample library instead (the optional SFZ backend, `instruments/sampler/`).
"""
from . import drums, bass, synth, strings, keys, fx, clean  # noqa: F401,I001  (registers the suite, in catalog order)
from .base import REGISTRY, Instrument, Note, Param, ParamError, describe, register
from .base import make as _make
from .presets import list_presets, resolve
from .sampler import Sampler  # noqa: F401
from .sampler import load as _load_sampler
from .family import load as _load_family

BACKENDS = {"sampler": _load_sampler,"family":_load_family}


def make(name: str, **params) -> Instrument:
    backend, _, lib = name.partition("/")
    if backend in BACKENDS:
        if not lib:
            raise ParamError(f"'{backend}' needs a library: write {backend}/<library>, e.g. sampler/salamander")
        voice=BACKENDS[backend](lib, **params)
        voice.response_ref=name
        return voice
    inst, preset = resolve(name)
    voice=_make(inst, **{**preset, **params})
    voice.response_ref=name
    return voice
