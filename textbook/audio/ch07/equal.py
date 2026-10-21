"""Ch. 7, equal temperament against just intonation on C4: the just major triad 4:5:6, then the
12-ET triad (third 13.69 c wide, fifth 1.96 c narrow). In the 12-ET triad the third shimmers: the
fifth partial of C (1308.13 Hz) against the fourth of E (1318.51 Hz) beats at about 10.4 Hz."""
from _lib import chord, freq, seq, silence

C4 = freq(60)


def render():
    just = [C4, C4 * 5 / 4, C4 * 3 / 2]
    et = [freq(60), freq(64), freq(67)]
    return seq([chord(just, 3.5), silence(0.6), chord(et, 3.5), silence(0.6), chord(just, 3.5)])
