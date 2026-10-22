"""Why the music gives up a band around each carrier (HEADPHONES).

Level: the file starts with a 2 s reference tone (an organ A3 at the file's peak level). Set a comfortable, moderate
volume on it; everything after it is 12 dB lower (the build peak-normalizes the whole file).

The same 8 s twice: a soft organ holding A3 and E4 (the host of "Dusk on the Water") with the binaural layer on A3 and
E4 at 10 and 6.18 Hz. First without carving: in each ear the organ's own A3 (220 Hz) meets that ear's detuned tone
(215 Hz left, 225 Hz right), so each ear hears a monaural beat at 5 Hz, half the binaural rate and not on the ladder.
Then with carving (the default): the music gives up 220 +- 8 Hz and 329.63 +- 6.1 Hz while the pairs sound, the pairs
take the organ's place there, and the pulse in each ear is gone; only the binaural beat between the ears remains.
"""
import numpy as np
from _lib import silence, seq, tone

from songmap.parse import lang
from songmap.render import render as render_song

SONG = """song "carve" 60 4/4 A fps=30 seed=3 tail=1 tuning=36edo
inst host=clean/organ(partials=4, rolloff=2.2, attack=.6, release=1)
binaural A3 E4 beat=10 level=-6 fade=1 carve={carve}
x 2 | host:{{notes: "=mp [a-,e]1"}} chords="A:2"
master clean
"""


def render():
    clips = [render_song(lang.loads(SONG.format(carve=c), "carve.sm")).audio for c in ("false", "true")]
    body = seq([clips[0], silence(1.2), clips[1]])
    body *= 10 ** (-12 / 20) / np.abs(body).max()
    ref = tone(220.0, 2.0, "clean/organ", attack=0.3, release=0.4)
    ref /= np.abs(ref).max()
    return seq([ref, silence(1.5), body])
