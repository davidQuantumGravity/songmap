"""Ch. 6, growing a scale on the chain of fifths: the notes F C G D A E B F# are added one at a time
(pure fifths, folded into the octave above C4) and each scale is played upward from C4 to C5.
Sizes 3, 5 and 7 have two step sizes (well-formed); sizes 4, 6 and 8 have three.
  3: C F G            steps 498.04, 203.91, 498.04
  4: C D F G          203.91, 294.13, 203.91, 498.04
  5: C D F G A        two sizes: 203.91 and 294.13
  6: C D E F G A      90.22, 203.91, 294.13
  7: C D E F G A B    two sizes: 203.91 and 90.22 (the major scale)
  8: + F#             90.22, 113.69, 203.91"""
from _lib import freq, seq, silence, tone

C4 = freq(60)


def fold(r):
    while r >= 2:
        r /= 2
    while r < 1:
        r *= 2
    return r


def render():
    clips = []
    for n in range(3, 9):
        notes = sorted(fold(1.5 ** k) for k in range(-1, n - 1)) + [2.0]
        clips += [tone(C4 * r, 0.34) for r in notes] + [silence(0.7)]
    return seq(clips)
