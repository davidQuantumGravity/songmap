"""Record every note synth_v0 plays, by running its own `build()` with the instruments stubbed out.

    python tools/v0_oracle.py A            # prints a summary of synth_v0's note list for track A

`notes(which)` returns [(part, kind, beat, pitches, info)] in synth_v0's own arrangement, which
the port check compares against the engine's expanded event list (tests/test_port.py).
"""
from __future__ import annotations

import importlib.util
import os
import sys
from collections import Counter

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NBARS = {"A": 74, "B": 60, "C": 150}


def _load(nbars: int):
    os.environ["NBARS"] = str(nbars)
    spec = importlib.util.spec_from_file_location(f"synth_v0_{nbars}", os.path.join(ROOT, "reference", "synth_v0.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def notes(which: str) -> list[tuple]:
    v0 = _load(NBARS[which])
    beat_s = v0.BEAT
    log, last = [], {}

    def stub(kind):
        def f(*a, **k):
            last["call"] = (kind, a, k)
            return np.zeros(1)
        return f

    for kind in ("kick", "snare", "clap", "hat", "bass_note", "pad_chord", "pluck", "lead_note", "riser", "impact",
                 "zap", "tick"):
        setattr(v0, kind, stub(kind))
    v0.reverb = lambda x, secs=2.2, wet=0.25: x
    tracks = {}

    class Track(v0.Track):
        def __init__(self):
            self.L = np.zeros(1)
            self.R = np.zeros(1)
            tracks[id(self)] = len(tracks)

        def add(self, start_s, sig, gain=1.0, pan=0.0):
            kind, a, k = last.pop("call")
            log.append((tracks[id(self)], kind, round(start_s / beat_s, 6), a, k, gain, pan))

    v0.Track = Track
    v0.N = 1
    try:
        v0.build({"A": v0.specA, "B": v0.specB, "C": v0.specC}[which])
    except Exception:
        pass      # the mixdown at the end is meaningless with 1-sample tracks; the note log is complete
    names = ["drums", "bass", "pad", "arp", "lead", "fx"]
    out = []
    for tr, kind, beat, a, k, gain, pan in log:
        part = names[tr]
        if kind == "hat":
            kind = "ohat" if k.get("open_") else "hat16" if a and a[0] == 0.04 else "hat"
        if kind == "snare" and a and a[0] == 0.15:
            kind = "fill"
        pitches = ()
        info = {"gain": gain}
        if kind in ("bass_note", "pluck", "lead_note"):
            pitches = (a[0],)
            info["dur_s"] = a[1]
            if kind == "pluck":
                info["cutoff"] = a[2]
            if kind == "bass_note":
                info["cutoff"] = a[2]
        elif kind == "pad_chord":
            pitches = tuple(a[0])
            info["bright"] = a[3]
        elif kind == "riser":
            info["dur_s"] = a[0]
        elif kind == "zap":
            info["f0"] = k.get("f0")
        out.append((part, kind, beat, pitches, info))
    return out


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "A"
    ns = notes(which)
    print(len(ns), "notes")
    print(Counter((p, k) for p, k, *_ in ns))
