"""One note, A3 = 220 Hz, on five spectra (2 s each):
1. a pure sine; 2. 12 harmonics with amplitudes ~1/k (bright, sawtooth-like); 3. odd harmonics only
(hollow, clarinet-like); 4. 12 harmonics with amplitudes ~1/k^2 (soft); 5. a golden spectrum,
partials 2^m * phi^n (1, 1.618, 2, 2.618, 3.236, 4, ...). Same pitch, same loudness envelope.
"""
from _lib import tone, seq, silence

F = 220.0
SPECS = [
    dict(partials=1),
    dict(partials=12, rolloff=1.0),
    dict(partials=12, rolloff=1.0, even=0.0),
    dict(partials=12, rolloff=2.0),
    dict(partials=12, rolloff=1.0, spectrum=1),
]


def render():
    parts = []
    for p in SPECS:
        parts += [tone(F, 1.6, "clean/organ", vel=0.6, **p), silence(0.5)]
    return seq(parts)
