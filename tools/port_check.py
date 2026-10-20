"""Port check for the three Oct-13 songs (ROADMAP P1 "done when").

    python tools/port_check.py                 # all three: notes vs synth_v0, loudness vs the original audio
    python tools/port_check.py swarm --stems   # also compare per-part levels against synth_v0's own stems

1. Notes: the engine's expanded event list against the notes synth_v0's `build()` plays
   (tools/v0_oracle.py), part by part. Random ticks are compared on their deterministic beats only.
2. Loudness: per-section loudness (K-weighted RMS) of our render vs the original audio decoded
   with ffmpeg, Pearson correlation across sections (target >= 0.9).
3. Section boundaries: start frames vs docs/SCENE_TIMELINES.md (bar n = frame 60 n at 120 BPM/30 fps)
   and the video's total frame count.
"""
from __future__ import annotations

import os
import subprocess
import sys
from collections import Counter, defaultdict

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from songmap.export.qa import k_weight  # noqa: E402
from songmap.instruments.dsp import SR  # noqa: E402

ASSETS = os.path.join(ROOT, "assets", "oct13")
SONGS = {
    # name: (v0 track, port file, original audio, video frames)
    "bench": ("A", "week_oct13_bench", "Week_Oct13_Bench_Fields_Thruster_v2.wav", 4530),
    "swarm": ("B", "week_oct13_swarm", "track_B_swarm.mp3", 3690),
    "deepdive": ("C", "deepdive_kapton", "DeepDive_Inside_the_56_Movies.wav", 9090),
}

# Section start frames, read off docs/SCENE_TIMELINES.md (Bars/Frames columns; bar n = 60 n).
SCENE_FRAMES = {
    "bench": {"cold_open": 0, "pulser": 240, "chain_test": 420, "problem": 780, "fixes": 960, "dashboard": 1320,
              "sim_break": 2040, "fields_a": 2160, "fields_b": 2640, "big_break": 3120, "thruster": 3240,
              "summary": 4200, "end_card": 4320},
    "swarm": {"terminal": 0, "swarm_in": 240, "goals": 480, "who": 960, "agents": 1080, "so_what": 2040,
              "output": 2160, "guardrails": 3120, "summary": 3360, "end_card": 3480},
    "deepdive": {"title": 0, "setup": 360, "movies_a": 1680, "coverage": 3960, "barrier": 5040, "findings": 6360,
                 "limits": 7320, "next": 8280, "outro": 8760},
}


def port_path(name: str, version: str = "v0.2") -> str:
    return os.path.join(ROOT, "examples", f"{version}_yaml", f"{SONGS[name][1]}.songmap.yaml")


def decode(path: str) -> np.ndarray:
    """Any audio file -> 48 kHz stereo float64 via ffmpeg."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(float)


def section_loudness(x: np.ndarray, spans) -> list[float]:
    y = k_weight(x)
    out = []
    for _, t0, t1 in spans:
        seg = y[int(t0 * SR):int(t1 * SR)]
        out.append(float(10 * np.log10(np.mean(seg ** 2) * 2 + 1e-12) - 0.691))
    return out


def pearson(a, b) -> float:
    return float(np.corrcoef(np.asarray(a), np.asarray(b))[0, 1])


# ----------------------------------------------------------------------------
# notes vs synth_v0
# ----------------------------------------------------------------------------
KIND = {"bass": "bass_note", "pad": "pad_chord", "arp": "pluck", "lead": "lead_note"}


def engine_notes(arr) -> list[tuple]:
    out = []
    for part, evs in arr.parts.items():
        for e in evs:
            kind = e.piece if part in ("drums", "fx") else KIND.get(part, part)
            out.append((part, kind, round(e.beat, 6), tuple(int(p) for p in e.pitches), e))
    return out


def compare_notes(arr, which: str) -> dict:
    """Per (part, kind): notes only in synth_v0, only in the engine. Ticks: deterministic beats only."""
    from v0_oracle import notes as v0_notes
    ref = v0_notes(which)
    a = Counter((p, k, b, pi) for p, k, b, pi, _ in ref if not (k == "tick" and b % 1))
    b = Counter((p, k, bt, pi) for p, k, bt, pi, _ in engine_notes(arr) if not (k == "tick" and bt % 1))
    report = {}
    for key in sorted({x[:2] for x in a} | {x[:2] for x in b}):
        missing = sum((a - b)[x] for x in a if x[:2] == key)
        extra = sum((b - a)[x] for x in b if x[:2] == key)
        total = sum(a[x] for x in a if x[:2] == key)
        report[key] = {"v0": total, "missing": missing, "extra": extra}
    return report


def compare_params(arr, which: str) -> list[str]:
    """Arp cutoff (brightness) and pad brightness per note against synth_v0."""
    from v0_oracle import notes as v0_notes
    problems = []
    ref = {(p, b, pi): info for p, k, b, pi, info in v0_notes(which) if k in ("pluck", "pad_chord")}
    for part, kind, beat, pitches, e in engine_notes(arr):
        if part == "arp":
            info = ref.get(("arp", beat, pitches))
            if info is None:
                continue
            want = info["cutoff"]
            got = dict(e.params).get("cutoff", dict(e.patch).get("cutoff"))
            if got is None or abs(got - want) > 1e-6:
                problems.append(f"arp@{beat}: cutoff {got} vs synth_v0 {want}")
        if part == "pad":
            info = ref.get(("pad", beat, pitches))
            if info is None:
                continue
            dark = dict(e.patch).get("cutoff") == 810
            if dark != (info["bright"] < 1):
                problems.append(f"pad@{beat}: dark={dark} vs synth_v0 bright={info['bright']}")
    return problems


# ----------------------------------------------------------------------------
# synth_v0's own stems, for level calibration
# ----------------------------------------------------------------------------
def v0_stems(which: str) -> dict[str, np.ndarray]:
    """Run synth_v0 for real and keep each Track after sidechain and reverb (pre-master), at 48 kHz."""
    from scipy.signal import resample_poly
    from v0_oracle import NBARS, _load
    v0 = _load(NBARS[which])
    made = []

    class Track(v0.Track):
        def __init__(self):
            super().__init__()
            made.append(self)

    v0.Track = Track
    v0.build({"A": v0.specA, "B": v0.specB, "C": v0.specC}[which])
    names = ["drums", "bass", "pad", "arp", "lead", "fx"]
    return {n: resample_poly(np.stack([t.L, t.R], 1), 160, 147, axis=0) for n, t in zip(names, made)}


def with_reverb(r, part: str) -> np.ndarray:
    """A part's stem plus its own share of the reverb returns (synth_v0 tracks include their reverb)."""
    from songmap.arrange.expand import seed_for
    from songmap.mix.fx import convolve, reverb_ir
    ens, x = r.arrangement.ensemble, r.stems[part]
    out = x.copy()
    for ret, amt in (ens.mix.get(part, {}).get("send") or {}).items():
        p = ens.returns[ret]
        ir = reverb_ir(float(p.get("seconds", 2.2)), predelay=float(p.get("predelay", 0.015)),
                       damping=float(p.get("damping", 0.5)), early=int(p.get("early", 10)),
                       width=float(p.get("width", 1.0)), seed=seed_for(r.song.seed, "return", ret) % 2**31)
        out += convolve(x * float(amt), ir)
    return out


def main(argv):
    from songmap.parse import yaml_form
    from songmap.render import render
    names = [a for a in argv if a in SONGS] or list(SONGS)
    version = "v0.1" if "--v01" in argv else "v0.2"
    for name in names:
        which, _, audio, frames = SONGS[name]
        song = yaml_form.load(port_path(name, version))
        r = render(song)
        arr = r.arrangement
        tl = arr.timeline
        print(f"== {name} ({version}): {tl.frames} frames (video {frames})")
        bad = {s.name: (tl.beat_to_frame(s.start), SCENE_FRAMES[name].get(s.name)) for s in tl.sections
               if tl.beat_to_frame(s.start) != SCENE_FRAMES[name].get(s.name)}
        print("   section frames:", "exact" if not bad else bad)
        rep = compare_notes(arr, which)
        for k, v in rep.items():
            flag = "" if not (v["missing"] or v["extra"]) else "   <-- differs"
            print(f"   {k[0]:6s} {k[1]:10s} v0 {v['v0']:5d}  missing {v['missing']:4d}  extra {v['extra']:4d}{flag}")
        probs = compare_params(arr, which)
        print(f"   arp/pad brightness mismatches: {len(probs)}", probs[:3])
        orig = decode(os.path.join(ASSETS, audio))
        spans = r.section_spans()
        a, b = section_loudness(r.audio, spans), section_loudness(orig, spans)
        print(f"   loudness r = {pearson(a, b):.3f}")
        for (sn, *_), x, y in zip(spans, a, b):
            print(f"     {sn:12s} ours {x:6.1f}  original {y:6.1f}  diff {x - y:+5.1f}")
        if "--stems" in argv:
            vs = v0_stems(which)
            for part in vs:
                if part not in r.stems:
                    continue
                ours = section_loudness(with_reverb(r, part), spans)
                theirs = section_loudness(vs[part][: len(r.audio)], spans)
                playing = arr.counts_by_section()
                d = [x - y for (sn, *_), x, y in zip(spans, ours, theirs)
                     if playing.get(sn, {}).get(part) and y > -60 and x > -60]
                print(f"   stem {part:6s} ours-v0 median {np.median(d):+6.2f} dB  spread {np.ptp(d) if d else 0:5.2f}")


if __name__ == "__main__":
    main(sys.argv[1:])
