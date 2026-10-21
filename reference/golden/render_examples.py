"""Listening examples for GOLDEN_THEORY.md (writes reference/golden/out/*.wav).

    python reference/golden/render_examples.py

All examples use the `clean` additive instrument (exact partials, fixed phases, no vibrato,
drift, detune, noise or saturation), are DRY (no reverb), and are peak-normalized (no
compressor or limiter), so overtone interactions are heard exactly as tuned.

1-6  golden passing harmony (diatonic home): progressions from docs/golden_progressions.json,
     36-ET, sustained clean organ tone (8 harmonics). Diatonic chords long, golden passing short.
7    golden home: exact-phi chain drone (55 * phi^k) on the golden-spectrum clean tone,
     walking the golden circle (sliding window over phi powers), 13 s per chord.
8    golden home: close-voiced Cg7 at f0 = 110 Hz on the harmonic clean tone, so its beats
     (6.13, 7.58, 9.37, 12.26 Hz) are audible; breathes Cg -> Cg7 -> vEg.
"""
import json
import os
import sys

import numpy as np
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)

from songmap.instruments import Note, make          # noqa: E402
from songmap.instruments.dsp import SR              # noqa: E402

OUT = os.path.join(HERE, "out")
PHI = (1 + 5 ** 0.5) / 2

PASSING_EXAMPLES = [
    ("01_golden_authentic_cadence", "Authentic cadence V–I"),
    ("02_golden_full_cadence", "Full cadence I–IV–V–I"),
    ("03_golden_ii_V_I", "Golden cadence ii–V–I"),
    ("04_golden_staircase", "Golden staircase I–ii–iii–IV–V–vi"),
    ("05_golden_andalusian", "Golden Andalusian vi–V–IV–III"),
    ("06_golden_pop_axis", "Pop axis I–V–vi–IV"),
]


sys.path.insert(0, HERE)
from dictionary import CHORDS                       # noqa: E402


def is_home(label: str) -> bool:
    """Home (diatonic/chromatic) chords are exactly the dictionary's chord keys."""
    return label == "(re-voice)" or label in CHORDS


def place(buf, t, x, gain=1.0):
    i = int(t * SR)
    x = x if x.ndim == 2 else np.stack([x, x], 1)
    x = x[: len(buf) - i]
    buf[i:i + len(x)] += x * gain


def normalize(x, peak_db=-3.0):
    return x / (np.max(np.abs(x)) + 1e-12) * 10 ** (peak_db / 20)


def midi_of(freq):
    return 69 + 12 * np.log2(freq / 440.0)


def render_progression(entry, home_dur=1.6, pass_dur=0.6, final=4.0):
    roman, steps = entry["roman"], entry["steps36"]
    durs = [home_dur if is_home(r) else pass_dur for r in roman]
    durs[-1] = final
    organ = make("clean/organ")
    buf = np.zeros((int((sum(durs) + 2) * SR), 2))
    t = 0.3
    for r, ch, d in zip(roman, steps, durs):
        if r == "(re-voice)":
            continue
        for k, s in enumerate(ch):                    # B T A S, 36-ET step -> fractional MIDI
            place(buf, t, organ.render(Note(s / 3.0, 0.6, d, seed=0)), 0.9 if k == 0 else 0.7)
        t += d
    return normalize(buf)


def golden_circle_drone(steps=8, hold=13.0, f0=55.0):
    """Window of 3 consecutive chain tones f0*phi^j, sliding one chain step per chord."""
    pad = make("clean/golden_pad", attack=3.0, release=4.0)
    buf = np.zeros((int((steps * hold + 8) * SR), 2))
    for s in range(steps):
        for j in range(s, s + 3):
            f = f0 * PHI ** j
            while f > 700:
                f /= 2 ** int(np.log2(f / 350))       # octave-fold into a pad register
            place(buf, s * hold, pad.render(Note(midi_of(f), 0.6, hold + 1.0)), 1.0)
    return normalize(buf)


def beating_golden_seventh(f0=110.0):
    """Cg (0-13 s) -> Cg7 (13-26 s) -> vEg (26-40 s), close voicing, exact ratios, harmonic tone."""
    tone = make("clean/organ", attack=1.5, release=2.5)
    buf = np.zeros((int(48 * SR), 2))
    ratios = [1, 2 / PHI, 4 / PHI ** 2, 8 / PHI ** 3]
    for start, d, idx in [(0.0, 13.0, [0, 1, 2]), (13.0, 13.0, [0, 1, 2, 3]), (26.0, 14.0, [1, 2, 3])]:
        for i in idx:
            place(buf, start, tone.render(Note(midi_of(f0 * ratios[i]), 0.6, d)), 1.0)
    return normalize(buf)


def main():
    os.makedirs(OUT, exist_ok=True)
    data = json.load(open(os.path.join(ROOT, "docs", "golden_progressions.json"), encoding="utf-8"))
    for fname, title in PASSING_EXAMPLES:
        y = render_progression(data["progressions"][title])
        wavfile.write(os.path.join(OUT, fname + ".wav"), SR, y.astype(np.float32))
        print("wrote", fname, f"{len(y) / SR:.1f}s")
    y = golden_circle_drone()
    wavfile.write(os.path.join(OUT, "07_golden_circle_drone.wav"), SR, y.astype(np.float32))
    print("wrote 07_golden_circle_drone", f"{len(y) / SR:.1f}s")
    y = beating_golden_seventh()
    wavfile.write(os.path.join(OUT, "08_beating_golden_seventh.wav"), SR, y.astype(np.float32))
    print("wrote 08_beating_golden_seventh", f"{len(y) / SR:.1f}s")


if __name__ == "__main__":
    main()
