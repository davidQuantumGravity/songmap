"""Ch. 7, key color: the cadence I-IV-V-I in C major and then in F# major, first in quarter-comma
meantone (Eb..G#), then in Werckmeister III (1691). In meantone C major is sweet (pure thirds), but
F# major needs A#, D# and E#, which this layout supplies as Bb, Eb and F: every third is a
427.37 c diminished fourth. In Werckmeister III both keys work: C's thirds (390.22, 390.22, 396.09) are
narrower than F#'s (407.82, 401.96, 407.82), so the keys differ in color."""
from math import log2
from _lib import chord, freq, seq, silence

P = 1200 * log2(1.5)
PC = 1200 * (12 * log2(3) - 19)
NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"]


def meantone():
    f = 1200 * log2(5) / 4
    order = ["Eb", "Bb", "F", "C", "G", "D", "A", "E", "B", "F#", "C#", "G#"]
    return {n: ((k - 3) * f) % 1200 for k, n in enumerate(order)}


def werckmeister3():
    order = ["C", "G", "D", "A", "E", "B", "F#", "C#", "G#", "Eb", "Bb", "F"]
    tempered = {"C", "G", "D", "B"}        # C-G, G-D, D-A and B-F# narrowed by 1/4 comma
    out, cur = {}, 0.0
    for n in order:
        out[n] = cur % 1200
        cur += P - (PC / 4 if n in tempered else 0)
    return out


def f(table, pc, midi_oct):
    """Pitch class pc (0..11) in the given tuning table, in the octave starting at MIDI midi_oct."""
    return freq(midi_oct) * 2 ** (table[NAMES[pc]] / 1200)


def triad(table, root, base):
    """Close root-position triad, root in the octave from MIDI `base`."""
    r = f(table, root % 12, base)
    t = f(table, (root + 4) % 12, base)
    fi = f(table, (root + 7) % 12, base)
    t = t * 2 if t < r else t
    while fi < t:
        fi *= 2
    return [r / 2, r, t, fi]


def cadence(table, tonic):
    return [chord(triad(table, tonic + k, 48), 1.1) for k in (0, 5, 7)] + [chord(triad(table, tonic, 48), 2.0)]


def render():
    mt, w3 = meantone(), werckmeister3()
    return seq(cadence(mt, 0) + [silence(0.6)] + cadence(mt, 6) + [silence(1.2)]
               + cadence(w3, 0) + [silence(0.6)] + cadence(w3, 6))
