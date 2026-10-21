"""A four-note golden chain on 55 Hz: exact powers 55 * phi^k (55, 88.99, 143.99, 232.98 Hz),
then the integer Fibonacci frequencies 55, 89, 144, 233 Hz. The two differ by 0.008-0.016 Hz:
to the ear they are the same chord. Golden-spectrum pad tone."""
from _lib import PHI, chord, seq, silence

PAD = dict(spectrum=1, partials=8, rolloff=1.4, attack=0.6, release=1.2)


def render():
    exact = [55 * PHI ** k for k in range(4)]
    fib = [55, 89, 144, 233]
    return seq([chord(exact, 7.0, "clean/organ", **PAD), silence(0.8), chord(fib, 7.0, "clean/organ", **PAD)])
