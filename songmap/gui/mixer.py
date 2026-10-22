"""The Studio mixer: fast remixes from a render's stems, and the `mix` line edits a fader writes.

A render keeps every part's stem (post fader, pan and sidechain). When the only change since that render is
in faders, pans and send amounts, the new mix is the old stems rescaled, the returns re-convolved from the
new sends, and the master re-run: seconds instead of a full render, and the same audio a full render gives.
Mute and solo are listening state (not in the song): they act on the remix only.
"""
from __future__ import annotations

import re

import numpy as np

REMIXABLE = ("gain_db", "pan", "send")


def effective_mix(song) -> dict[str, dict]:
    """part -> the mix entry the renderer uses (defaults < mood < song)."""
    from ..arrange.ensemble import Ensemble
    return {k: dict(v) for k, v in Ensemble(song).mix.items()}


def strip_mix(text: str) -> str:
    """The text without its top-level `mix` lines (.sm): equal stripped texts differ only in the mix."""
    return "\n".join(ln for ln in text.splitlines() if not re.match(r"mix\s", ln))


def _balance(p: float) -> np.ndarray:
    return np.array([1 - max(p, 0.0), 1 + min(p, 0.0)])


def _undb(db: float) -> float:
    return 10 ** (db / 20)


def remixable(old: dict[str, dict], new: dict[str, dict], parts) -> bool:
    for part in parts:
        a, b = old.get(part, {}), new.get(part, {})
        if {k: v for k, v in a.items() if k not in REMIXABLE} != {k: v for k, v in b.items() if k not in REMIXABLE}:
            return False
        pa, pb = float(a.get("pan", 0) or 0), float(b.get("pan", 0) or 0)
        ba, bb = _balance(pa), _balance(pb)
        if np.any((ba < 1e-6) & (bb > 1e-6)):            # a hard-panned stem lost that channel
            return False
    return True


def remix(r, old: dict[str, dict], new: dict[str, dict], mute=(), solo=()) -> np.ndarray:
    """The mastered audio of render `r` with mix `new` (it was rendered with `old`), mute and solo applied."""
    from ..arrange.expand import seed_for
    from ..mix.fx import convolve, reverb_ir
    from ..mix.master import master, master_clean, master_legacy
    song = r.arrangement.song
    ens = r.arrangement.ensemble
    parts = [k for k in r.stems if not k.startswith("return_")]
    n = len(next(iter(r.stems.values()))) if r.stems else 0
    stems: dict[str, np.ndarray] = {}
    sends: dict[str, np.ndarray] = {}
    for part in parts:
        a, b = old.get(part, {}), new.get(part, {})
        g = _undb(float(b.get("gain_db", 0)) - float(a.get("gain_db", 0)))
        ba, bb = _balance(float(a.get("pan", 0) or 0)), _balance(float(b.get("pan", 0) or 0))
        ratio = np.where(ba > 1e-6, bb / np.maximum(ba, 1e-6), 0.0)
        buf = r.stems[part] * (g * ratio)
        for ret, amt in (b.get("send") or {}).items():
            if ret in ens.returns:
                sends.setdefault(ret, np.zeros((n, 2)))
                sends[ret] += buf * float(amt)
        heard = part not in mute and (not solo or part in solo)
        stems[part] = buf if heard else buf * 0.0
    for ret, x in sends.items():
        rc = ens.returns[ret]
        if rc.get("type", "reverb") != "reverb":
            continue
        if solo or mute:                                  # what you hear in the hall follows mute/solo too
            x = sum(stems[p] * float((new.get(p, {}).get("send") or {}).get(ret, 0)) for p in parts) + np.zeros((n, 2))
        ir = reverb_ir(float(rc.get("seconds", 2.2)), predelay=float(rc.get("predelay", 0.015)),
                       damping=float(rc.get("damping", 0.5)), early=int(rc.get("early", 10)),
                       width=float(rc.get("width", 1.0)), seed=seed_for(song.seed, "return", ret) % 2**31)
        stems[f"return_{ret}"] = convolve(x, ir)
    mix = sum(stems.values()) if stems else np.zeros((n, 2))
    mode = r.stats.get("master") or song.master.mode
    if mode == "legacy":
        return master_legacy(mix)
    if mode == "clean":
        return master_clean(mix, song.master.ceiling_db)
    return master(mix, song.master.target_lufs, song.master.ceiling_db, glue=song.master.glue != "none")


# ---------------------------------------------------------------------------------------------- text edits
def _num(x: float) -> str:
    return f"{round(float(x), 2):g}"


def set_mix(text: str, part: str, *, gain_db: float | None = None, pan: float | None = None,
            sends: dict[str, float] | None = None, default_gain: float = 0.0) -> str:
    """Set a part's fader / pan / sends on the song's `mix` lines (.sm), adding the part if it isn't there.
    Other parts and the line's other options stay as written."""
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if not re.match(r"mix\s", ln):
            continue
        body, hash_, comment = _split_comment(ln[3:])
        chunks = [c.strip() for c in body.split("|")]
        for j, ch in enumerate(chunks):
            words = ch.split()
            if words and words[0] == part:
                chunks[j] = _chunk(part, words[1:], gain_db, pan, sends)
                lines[i] = "mix " + " | ".join(chunks) + (("  #" + comment) if hash_ else "")
                return "\n".join(lines)
    new = _chunk(part, [_num(default_gain)], gain_db, pan, sends)
    mix_lines = [i for i, ln in enumerate(lines) if re.match(r"mix\s", ln)]
    if mix_lines:
        i = mix_lines[-1]
        body, hash_, comment = _split_comment(lines[i])
        lines[i] = body.rstrip() + " | " + new + (("  #" + comment) if hash_ else "")
    else:
        at = _first_section_line(lines)
        lines.insert(at, "mix " + new)
    return "\n".join(lines)


def _split_comment(s: str) -> tuple[str, str, str]:
    m = re.search(r"(^|\s)#", s)
    if not m:
        return s, "", ""
    k = m.start() + len(m.group(1))
    return s[:k], "#", s[k + 1:]


def _chunk(part: str, words: list[str], gain_db, pan, sends) -> str:
    gain = words[0] if words else "0"
    opts = list(words[1:])
    if gain_db is not None:
        gain = _num(gain_db)

    def put(key: str, val: float | None):
        nonlocal opts
        if val is None:
            return
        opts = [o for o in opts if not o.startswith(key + "=")]
        if abs(val) > 1e-9:
            opts.append(f"{key}={_num(val)}")
    put("pan", pan)
    for k, v in (sends or {}).items():
        put(k, v)
    return " ".join([part, gain, *opts])


def _first_section_line(lines: list[str]) -> int:
    """Where a new header line goes: after the last header directive before the sections start."""
    from ..parse.lang import DIRECTIVES
    last = 0
    for i, ln in enumerate(lines):
        w = ln.split()
        if not w or ln.startswith("#"):
            continue
        if ln[0].isspace():
            continue
        if w[0] in DIRECTIVES:
            last = i + 1
        else:
            break
    return last
