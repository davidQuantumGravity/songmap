"""Two pure sines, 440 Hz and 441, 443, 446, 452 Hz: beats at 1, 3, 6 and 12 per second."""
from _lib import sine, silence, seq


def render():
    clips = []
    for d in (1, 3, 6, 12):
        clips += [sine(440.0, 3.5, amp=0.25, fade=0.05) + sine(440.0 + d, 3.5, amp=0.25, fade=0.05), silence(0.6)]
    return seq(clips)
