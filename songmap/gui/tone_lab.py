"""Pure design proposals and disposable previews; only saving creates a take."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import math
import os

from .instrument_lab import current_voice, edit_voice
from .project import parse_text
from ..instruments.sound import TONE_PARAMS, MORPH_PARAMS, BLEND


def _mix_controls(voice):
    names = {q['name'] for q in voice.get('schema', [])}
    return [q for q in (*MORPH_PARAMS,BLEND) if q.name in names]


def controls(store, sid, candidate):
    s = store.get(sid)
    if s.get("scope", "instrument") != "instrument":
        raise ValueError("Sound shaping and blending are available in instrument comparisons")
    c = next((c for c in s["candidates"] if c["id"] == candidate), None)
    if c is None:
        raise ValueError("Choose a saved take")
    voice = current_voice(c["source"], s["path"], s["part"], s["piece"])
    params = [*TONE_PARAMS, *_mix_controls(voice)]
    return {"params":[asdict(q) for q in params],
            "values":{q.name:voice["values"].get(q.name, q.default) if voice["instrument"]=="sound" else q.default for q in params}}


def design_change(store, sid, recipe):
    s = store.get(sid)
    if s.get("scope", "instrument") != "instrument":
        raise ValueError("Choose an instrument comparison to shape or blend sounds")
    if not isinstance(recipe, dict) or set(recipe)-{"base", "pair", "amount", "tone"}:
        raise ValueError("A design needs a base take or the current pair, and numeric tone controls")
    tone = recipe.get("tone", {})
    spec = {q.name:q for q in (*TONE_PARAMS,*MORPH_PARAMS,BLEND)}
    if not isinstance(tone, dict):
        raise ValueError("Tone controls must be a mapping")
    for k, v in tone.items():
        if (k not in spec or isinstance(v, bool) or not isinstance(v, (float, int))
                or not math.isfinite(v) or not spec[k].lo <= v <= spec[k].hi):
            raise ValueError(f"Invalid tone control: {k}")
    blending = "pair" in recipe
    ids = recipe.get("pair") if blending else [recipe.get("base")]
    if blending:
        if "base" in recipe or ids != s["pair"] or len(ids) != 2:
            raise ValueError("The comparison pair changed; reopen the blend controls")
        amount = recipe.get("amount")
        if isinstance(amount, bool) or not isinstance(amount, (float, int)) or not math.isfinite(amount) or not 0 <= amount <= 1:
            raise ValueError("Blend amount must be between 0 and 1")
    elif "amount" in recipe:
        raise ValueError("A blend amount needs a pair of takes")
    sources = [next((c for c in s["candidates"] if c["id"] == cid), None) for cid in ids]
    if any(c is None for c in sources):
        raise ValueError("Choose a saved take from this comparison")
    definitions, layers = {}, []
    voice = None
    for c in sources:
        song = parse_text(c["source"], s["path"])
        voice = current_voice(c["source"], s["path"], s["part"], s["piece"])
        for name, definition in song.sounds.items():
            if name in definitions and definitions[name] != definition:
                raise ValueError("Source sound recipes conflict")
            definitions[name] = definition
        layer = {"use":voice["use"], "params":voice["params"]}
        if voice["instrument"] == "patch":
            from ..arrange.ensemble import Ensemble
            layer["patch"] = Ensemble(song).patch_spec(voice["use"].partition("/")[2])
        layers.append(layer)
    mix_names = {q.name for q in (*MORPH_PARAMS,BLEND)} & tone.keys()
    if mix_names and (blending or not mix_names <= {q.name for q in _mix_controls(voice)}):
        raise ValueError("Morph controls need a saved sound with the matching source layout")
    if not blending and voice["instrument"] == "sound":
        use, values = voice["use"], {**voice["params"], **tone}
    else:
        definition = dict(zip(("a", "b"), layers))
        name = "lab_" + hashlib.sha256(json.dumps(definition, sort_keys=True).encode()).hexdigest()[:16]
        definitions[name] = definition
        use, values = "sound/"+name, {**tone, **({"blend":amount} if blending else {})}
    description = (f"Blend of saved takes at {amount:.1%} B. " if blending else "Tone controls applied to the selected saved take. ")
    description += ", ".join(f"{k.removeprefix('tone_')}={v:g}" for k,v in tone.items())
    return {"use":use,"params":values,"sounds":definitions}, description


def preview(store, sid, recipe):
    import numpy as np
    from ..render import render
    from ..export.qa import lufs
    from .project import wav_bytes
    s = store.get(sid)
    change, description = design_change(store, sid, recipe)
    base = next(c for c in s["candidates"] if c["id"] == s["incumbent"])
    source = edit_voice(base["source"], s["path"], s["part"], s["piece"], change)
    # Include the complete resolved source and window in the disposable cache key.
    key = hashlib.sha256((source+json.dumps([s["start"],s["seconds"]])).encode()).hexdigest()
    folder = store.home / sid / "design-previews"
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / (key+".wav")
    if not dest.exists():
        song = parse_text(source, str(store.root / s["path"]))
        result = render(song, preview_end=None if song.binaural else s["start"]+s["seconds"]+.05)
        clip = np.array(result.stems[s["part"]][int(s["start"]*48000):int((s["start"]+s["seconds"])*48000)], copy=True)
        peak = np.max(np.abs(clip)) if clip.size else 0
        loudness = lufs(clip)
        if peak > 0 and math.isfinite(loudness):
            clip *= min(10**((-20-loudness)/20), .94/peak)
        # Concurrent identical requests can share the final asset safely.
        import uuid
        tmp = dest.with_suffix("."+uuid.uuid4().hex+".tmp")
        tmp.write_bytes(wav_bytes(clip)); os.replace(tmp, dest)
        # Disposable auditions cannot grow without bound as knobs are explored.
        for old in sorted(folder.glob("*.wav"), key=lambda p:p.stat().st_mtime, reverse=True)[32:]:
            if old != dest:
                try:
                    old.unlink()
                except OSError:  # A browser may still be reading the old preview.
                    pass
    return {"audio":f"/api/lab/sessions/{sid}/design/audio/{key}","description":description}
