"""The comma pump in exact golden tuning lands 3.16 c below 36-ET's ^C.

Thirteen steps up the exact golden chain raise the tonic by one golden comma, phi^13 / 2^9
(30.17 c). 36-ET's ^C is one sixth-step, 33.33 c. Above C5 (523.25 Hz) the two arrivals are
523.25 * (2^(33.33/1200) - 2^(30.17/1200)) = 0.97 Hz apart, so together on pure tones they beat
about once a second. Order: C5; the 36-ET ^C5 (sustained reference); the exact
arrival; both together on sines; both together on a harmonic organ tone (partials beat faster).
"""
from _lib import PHI, at, freq, silence, seq, sine, tone

C5 = freq(72)                          # 523.25 Hz
ET = C5 * 2 ** (1 / 36)                # 36-ET ^C5, 33.33 c
EXACT = C5 * PHI ** 13 / 2 ** 9        # exact golden comma above C5, 30.17 c


def render():
    sines = at([(0, sine(ET, 7.0, 0.22)), (0, sine(EXACT, 7.0, 0.22))])
    organ = at([(0, tone(ET, 6.0, vel=0.45)), (0, tone(EXACT, 6.0, vel=0.45))])
    return seq([sine(C5, 1.6), silence(0.3), sine(ET, 2.0), silence(0.3), sine(EXACT, 2.0),
                silence(0.6), sines, silence(0.6), organ])
