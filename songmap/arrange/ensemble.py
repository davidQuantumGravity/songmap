"""Who plays what: resolve each part (and kit piece) to an instrument, preset, level and pan,
merging the song's `instruments:`/`mix:`/`returns:` over `defaults.yaml`."""
from __future__ import annotations

import copy
import os
from dataclasses import dataclass, field
from functools import lru_cache

import yaml

from ..instruments import REGISTRY, ParamError, make
from ..instruments.presets import preset_info
from ..model import KIT_ROLES
from ..parse.errors import SongError, did_you_mean

DEFAULTS_PATH = os.path.join(os.path.dirname(__file__), "defaults.yaml")
PLACEMENT = ("use", "gain_db", "pan", "layer")


@lru_cache(maxsize=None)
def _defaults_text() -> str:
    with open(DEFAULTS_PATH, encoding="utf-8") as f:
        return f.read()


def defaults() -> dict:
    return yaml.safe_load(_defaults_text())


@dataclass
class Voice:
    use: str                          # 'instrument' or 'instrument/preset'
    params: dict = field(default_factory=dict)
    gain_db: float = 0.0
    pan: float = 0.0

    @property
    def instrument(self) -> str:
        return self.use.partition("/")[0]


def _voice(entry, base: Voice | None = None, where: str = "") -> Voice:
    if isinstance(entry, str):
        v = Voice(entry)
        if base:
            v.gain_db, v.pan = base.gain_db, base.pan
        return v
    if not isinstance(entry, dict):
        raise SongError(f"instruments {where}: write 'instrument/preset' or {{use: ..., param: value}}")
    v = copy.deepcopy(base) if base and "use" not in entry else Voice(entry.get("use", base.use if base else where))
    if base and "use" in entry:
        v.gain_db, v.pan = base.gain_db, base.pan
    v.params.update({k: x for k, x in entry.items() if k not in PLACEMENT})
    v.gain_db = float(entry.get("gain_db", v.gain_db))
    v.pan = float(entry.get("pan", v.pan))
    return v


def _is_kit(role: str, entry) -> bool:
    return isinstance(entry, dict) and ("kit" in entry or (role in KIT_ROLES and "use" not in entry))


class Ensemble:
    def __init__(self, song):
        self.song = song
        d = defaults()
        self.kit_fallback: dict = d.get("kit_fallback", {})
        self.part_fallback: dict = d.get("part_fallback", {})
        self.single: dict[str, Voice] = {}
        self.kits: dict[str, dict[str, Voice]] = {}
        from .moods import get_mood
        self.mood = get_mood(song.mood, song.file)            # defaults < mood < the song
        for role, entry in d["instruments"].items():
            self._set(role, entry, defaults_pass=True)
        for role, entry in (self.mood.get("instruments") or {}).items():
            self._set(role, entry, defaults_pass=True)
        for role, entry in (song.instruments or {}).items():
            self._set(role, entry)
        self.mix: dict[str, dict] = {k: dict(v) for k, v in d.get("mix", {}).items()}
        for part, m in (self.mood.get("mix") or {}).items():
            self.mix[part] = {**self.mix.get(part, {}), **m}
        for part, m in (song.mix or {}).items():
            if not isinstance(m, dict):
                raise SongError(f"mix {part}: write a mapping like {{gain_db: -3, send: {{hall: 0.2}}}}",
                                file=song.file)
            self.mix[part] = {**self.mix.get(part, {}), **m}
        self.returns: dict[str, dict] = {k: dict(v) for k, v in d.get("returns", {}).items()}
        for name, r in (self.mood.get("returns") or {}).items():
            self.returns[name] = {**self.returns.get(name, {}), **r}
        for name, r in (song.returns or {}).items():
            self.returns[name] = {**self.returns.get(name, {}), **r}
        self._cache: dict = {}

    def _set(self, role, entry, defaults_pass=False):
        if _is_kit(role, entry):
            pieces = entry.get("kit", entry)
            kit = self.kits.setdefault(role, {})
            for piece, pe in pieces.items():
                kit[piece] = _voice(pe, kit.get(piece), f"{role}.{piece}")
            self.single.pop(role, None)
        else:
            self.single[role] = _voice(entry, self.single.get(role), role)
            if not defaults_pass:
                self.kits.pop(role, None)

    # --- lookup -----------------------------------------------------------------
    def is_kit(self, part: str) -> bool:
        return part in self.kits

    def voice(self, part: str, piece: str | None = None) -> Voice:
        if part in self.kits:
            kit = self.kits[part]
            if piece is None:
                raise SongError(f"part {part} is a kit; its notes need a piece ({' '.join(kit)})")
            if piece in kit:
                return kit[piece]
            fb = self.kit_fallback.get(piece)
            if fb in kit:
                return kit[fb]
            if piece in REGISTRY:
                return Voice(piece)
            raise SongError(f"{part}: no kit piece '{piece}'", file=self.song.file,
                            suggestion=did_you_mean(piece, kit) + f"; or add it under instruments: {part}: kit:")
        if part in self.single:
            return self.single[part]
        name = self.part_fallback.get(part, part)
        if name in REGISTRY:
            return Voice(name)
        raise SongError(f"part '{part}' has no instrument", file=self.song.file,
                        suggestion=f"add instruments: {{{part}: <instrument>/<preset>}}; "
                                   + did_you_mean(part, REGISTRY))

    def patch_for(self, part: str, piece: str | None, preset: str | None, params: dict | None) -> tuple:
        """Style-level overrides: a style's `preset:` contributes only the params its file sets
        itself (its difference from its base), and only when the part plays that instrument."""
        v = self.voice(part, piece)
        out = {}
        if preset:
            inst = preset.partition("/")[0]
            if inst == v.instrument:
                out.update((preset_info(preset).get("params") or {}))
        out.update(params or {})
        return tuple(sorted(out.items()))

    def instrument(self, part: str, piece: str | None = None, patch: tuple = ()):
        v = self.voice(part, piece)
        key = (v.use, tuple(sorted(v.params.items())), patch)
        if key not in self._cache:
            where = f"instruments {part}{'.' + piece if piece else ''}"
            try:
                inst = make(v.use, **{**v.params, **dict(patch)})
            except ParamError as e:
                raise SongError(f"{where}: {e}", file=self.song.file) from None
            except SongError as e:      # e.g. a sampler library that isn't installed
                raise SongError(f"{where}: {e.message}", file=self.song.file, suggestion=e.suggestion) from None
            self.song.warnings += [w for w in getattr(inst, "warnings", ()) if w not in self.song.warnings]
            self._cache[key] = inst
        return self._cache[key]

    def instruments(self) -> list:
        """Every instrument built so far (one per distinct voice + params)."""
        return list(self._cache.values())

    def check_sends(self, part, m) -> None:
        """A mix send must name a return the song has (only `hall` unless `set returns=` adds more)."""
        for ret in (m.get("send") or {}) if isinstance(m, dict) else ():
            if ret not in self.returns:
                raise SongError(f"mix {part}: send to unknown return '{ret}' (returns: {', '.join(self.returns)})",
                                file=self.song.file,
                                suggestion=f"for an echo use `inserts {part} delay(time=0.75, mix=.2)`, or add the "
                                f"return: set returns.{ret}={{type: reverb, seconds: 1.2}}"
                                if ret == "delay" else did_you_mean(ret, self.returns))

    def check(self, parts) -> None:
        """Build every instrument a song uses (validates names and params)."""
        for part in parts:
            if part in self.kits:
                for piece in self.kits[part]:
                    self.instrument(part, piece)
            else:
                self.instrument(part)
        for part, m in self.mix.items():
            self.check_sends(part, m)
        for name, r in self.returns.items():
            if r.get("type", "reverb") != "reverb":
                self.song.warnings.append(f"return {name}: type '{r.get('type')}' arrives in P4; skipped")
