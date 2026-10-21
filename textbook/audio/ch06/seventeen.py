"""Ch. 6, the next well-formed size after twelve: the 17-note Pythagorean scale (chain Gb..A#,
positions -6..10), played up from C4. Its steps are 12 limmas (90.22 c) and 5 commas (23.46 c): every
black key of the 12-note scale now comes as a sharp and a flat a comma apart, e.g. C# (113.69 c)
and Db (90.22 c). Then C, Db, C#, D slowly."""
from _lib import freq, seq, silence, tone

C4 = freq(60)


def fold(r):
    while r >= 2:
        r /= 2
    while r < 1:
        r *= 2
    return r


def render():
    s = sorted(fold(1.5 ** k) for k in range(-6, 11)) + [2.0]
    a = [tone(C4 * r, 0.3) for r in s]
    b = [tone(C4 * r, 0.8) for r in (1, 256 / 243, 2187 / 2048, 9 / 8)]
    return seq(a + [silence(1.0)] + b)
