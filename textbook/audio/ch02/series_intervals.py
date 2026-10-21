"""Neighbouring harmonics of C2 as two-note chords: 1:2 (octave), 2:3 (fifth), 3:4 (fourth), 4:5 (major third), 5:6 (minor third), 6:7, 7:8; then 4:5:6 and 4:5:6:7."""
from _lib import chord, silence, seq, freq


def render():
    f0 = freq(36)
    dy = [chord([f0 * n, f0 * (n + 1)], 1.5, "clean/organ") for n in range(1, 8)]
    return seq([seq(dy, gap=0.35), silence(0.6),
                chord([f0 * 4, f0 * 5, f0 * 6], 2.5, "clean/organ"), silence(0.4),
                chord([f0 * 4, f0 * 5, f0 * 6, f0 * 7], 3.0, "clean/organ")])
