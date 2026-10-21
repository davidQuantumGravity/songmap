"""Equal steps in hertz (110, 220, ..., 880 Hz), then equal ratios (110, 220, 440, 880 Hz)."""
from _lib import tone, silence, seq


def render():
    a = [tone(110.0 * k, 0.65, "clean/organ") for k in range(1, 9)]
    b = [tone(110.0 * 2 ** k, 0.65, "clean/organ") for k in range(4)]
    return seq([seq(a, gap=0.12), silence(1.0), seq(b, gap=0.12)])
