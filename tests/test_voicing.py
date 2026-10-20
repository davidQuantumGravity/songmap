"""Voicing and voice leading (moved from the sketch)."""
from songmap.theory import voicing as P


def test_voice_leading_is_smooth():
    c = P.voice_lead(None, 0, (0, 4, 7))
    f = P.voice_lead(c, 5, (0, 4, 7))
    assert sum(abs(a - b) for a, b in zip(c, f)) <= 6     # C -> F moves by step, not jumps
    assert set(c) & set(f)                                 # keeps a common tone
