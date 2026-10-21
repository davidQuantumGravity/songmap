"""Five small steps above C4, each played melodically then as a dyad:
12-ET semitone 100 c; golden apotome phi^3/4 = 99.27 c; golden limma 2^7/phi^10 = 69.10 c;
Pythagorean limma 256/243 = 90.22 c; Pythagorean apotome 2187/2048 = 113.69 c."""
from _lib import PHI, chord, freq, seq, silence, tone

C4 = freq(60)


def render():
    ratios = [2 ** (1 / 12), PHI ** 3 / 4, 2 ** 7 / PHI ** 10, 256 / 243, 2187 / 2048]
    clips = []
    for r in ratios:
        clips += [tone(C4, 0.6, "clean/keys"), tone(C4 * r, 0.9, "clean/keys"), silence(0.15),
                  chord([C4, C4 * r], 1.4, "clean/organ", vel=0.45), silence(0.6)]
    return seq(clips)
