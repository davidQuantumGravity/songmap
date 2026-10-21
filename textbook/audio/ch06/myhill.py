"""Ch. 6, two sizes of every interval: in the Pythagorean C major scale, the seven diatonic thirds
C-E, D-F, E-G, F-A, G-B, A-C, B-D come in only two sizes, 407.82 c (three of them: C-E, F-A, G-B)
and 294.13 c (four: D-F, E-G, A-C, B-D). Then the seven fourths: six pure (498.04 c) and one
augmented fourth F-B (611.73 c)."""
from _lib import chord, freq, seq, silence

C4 = freq(60)
SCALE = [1, 9 / 8, 81 / 64, 4 / 3, 3 / 2, 27 / 16, 243 / 128]


def note(i):
    o, d = divmod(i, 7)
    return C4 * SCALE[d] * 2 ** o


def render():
    out = []
    for gen in (2, 3):
        for i in range(7):
            out.append(chord([note(i), note(i + gen)], 1.05))
        out.append(silence(0.9))
    return seq(out)
