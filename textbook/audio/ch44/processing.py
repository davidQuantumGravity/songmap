"""What processing does to a designed sound (pure sines, so every change is audible as such).

1. Beats: 220 Hz + 226 Hz (a 6 Hz beat), 7 s clean, then 7 s through a fast compressor
   (threshold -30 dB, ratio 8:1, attack 2 ms, release 40 ms), loudness-matched (BS.1770).
   Measured on the 10 ms RMS envelope: the beat's depth (95th vs 10th percentile) drops from
   about 15.8 dB to about 9.9 dB. (A slow 'glue' setting, 3:1 with 30 ms / 200 ms, barely changes it.)
2. Saturation: 440 Hz + 550 Hz (a just major third), 4 s clean, then 4 s through tanh saturation
   with drive 1.6 (the curve of the original prototype's master): new tones appear at
   2*440 - 550 = 330 Hz and 2*550 - 440 = 660 Hz, about 20 dB below the two notes.
"""
import numpy as np
from _lib import sine, silence, seq
from songmap.export.qa import lufs
from songmap.mix.fx import compressor


def render():
    beat = sine(220, 7.0, 0.3) + sine(226, 7.0, 0.3)
    comp = compressor(beat, threshold_db=-30, ratio=8.0, attack=0.002, release=0.04, knee_db=2)
    comp = comp * 10 ** ((lufs(beat) - lufs(comp)) / 20)
    third = sine(440, 4.0, 0.5) + sine(550, 4.0, 0.5)
    third = third / np.abs(third).max() * 0.5
    sat = np.tanh(1.6 * third / 0.5) / np.tanh(1.6) * 0.5
    sat = sat * 10 ** ((lufs(third) - lufs(sat)) / 20)
    return seq([beat, silence(1.0), comp, silence(1.5), third, silence(1.0), sat])
