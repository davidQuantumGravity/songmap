"""ch22: dividing one whole tone, C4 to D4, into 2 (12-ET semitones), 4 (quarter-tones, 24-ET), 6 (sixth-tones,
36-ET, Busoni's proposal) and 16 (sixteenth-tones, 96-ET, used by Carrillo) equal steps. Then a C major triad,
the same triad a quarter-tone higher (as on a second piano tuned a quarter-tone up), and both together."""
import numpy as np
from _lib import tone, chord, silence, seq, freq

C4 = 60


def run(steps, note=0.32):
    return seq([tone(freq(C4 + 2 * k / steps), note * 0.9, preset="clean/organ", vel=0.45) for k in range(steps + 1)],
               gap=note * 0.1)


def render():
    parts = []
    for steps in (2, 4, 6, 16):
        parts += [run(steps, 0.42 if steps < 16 else 0.24), silence(0.6)]
    tri = [C4, C4 + 4, C4 + 7]
    a = chord([freq(m) for m in tri], 2.0, preset="clean/keys", vel=0.4)
    b = chord([freq(m + 0.5) for m in tri], 2.0, preset="clean/keys", vel=0.4)
    both = chord([freq(m) for m in tri] + [freq(m + 0.5) for m in tri], 2.5, preset="clean/keys", vel=0.35)
    return seq(parts + [a, silence(0.3), b, silence(0.3), both])
