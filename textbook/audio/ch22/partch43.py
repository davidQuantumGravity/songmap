"""ch22: Harry Partch's 43-tone just scale, all 43 ratios from 1/1 to 160/81 and then 2/1, on G3 = 196.0 Hz;
then an 11-limit otonal hexad 1:5/4:3/2:7/4:9/8(+8ve):11/8(+8ve), i.e. harmonics 4:5:6:7:9:11."""
from fractions import Fraction as F
from _lib import tone, chord, silence, seq, freq

RATIOS = ("1/1 81/80 33/32 21/20 16/15 12/11 11/10 10/9 9/8 8/7 7/6 32/27 6/5 11/9 5/4 14/11 9/7 21/16 4/3 "
          "27/20 11/8 7/5 10/7 16/11 40/27 3/2 32/21 14/9 11/7 8/5 18/11 5/3 27/16 12/7 7/4 16/9 9/5 20/11 "
          "11/6 15/8 40/21 64/33 160/81").split()
G3 = freq(55)


def render():
    notes = [tone(G3 * float(F(r)), 0.2, preset="clean/organ", vel=0.45) for r in RATIOS + ["2/1"]]
    run = seq(notes, gap=0.03)
    hexad = chord([G3 * h / 4 for h in (4, 5, 6, 7, 9, 11)], 4.0, preset="clean/organ", vel=0.35)
    return seq([run, silence(0.8), hexad])
