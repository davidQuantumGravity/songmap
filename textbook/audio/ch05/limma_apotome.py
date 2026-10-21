"""Ch. 5, two semitones: E-F, the limma 256/243 (90.22 c), then F-F#, the apotome 2187/2048
(113.69 c), each played melodically and then together; then C# (seven fifths up, 113.69 c above C)
and Db (five fifths down, 90.22 c above C) alternate over a low C, and finally sound together:
they differ by the Pythagorean comma and beat at about 3.8 Hz."""
from _lib import chord, freq, seq, silence, tone

C4 = freq(60)
E, F, Fs = C4 * 81 / 64, C4 * 4 / 3, C4 * 4 / 3 * 2187 / 2048
Cs, Db = C4 * 2187 / 2048, C4 * 256 / 243


def render():
    return seq([
        tone(E, 0.7), tone(F, 0.9), silence(0.2), chord([E, F], 1.6), silence(0.6),
        tone(F, 0.7), tone(Fs, 0.9), silence(0.2), chord([F, Fs], 1.6), silence(0.8),
        chord([C4 / 2, Cs], 1.4), chord([C4 / 2, Db], 1.4), chord([C4 / 2, Cs], 1.4), chord([C4 / 2, Db], 1.4),
        silence(0.4), chord([Cs, Db], 4.0),
    ])
