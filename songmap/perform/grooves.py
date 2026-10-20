"""Groove templates."""


# 16th-step groove templates: (timing offset as a fraction of a 16th, velocity factor).
# Off-beats are where feel lives; values are starting points, tune by ear in the GUI.
GROOVES = {
    "straight": [(0.0, 1.0)] * 16,
    "push":     [(0.0, 1.0), (-0.06, 0.9), (-0.04, 0.95), (-0.06, 0.9)] * 4,      # slightly ahead (urgent)
    "laid_back": [(0.0, 1.0), (0.08, 0.9), (0.05, 0.95), (0.08, 0.88)] * 4,       # behind the beat (relaxed)
    "mpc": [(0.0, 1.0), (0.16, 0.82), (0.0, 0.95), (0.16, 0.8)] * 4,             # ~58% 16th swing feel
    "dilla": [(0.0, 1.0), (0.22, 0.8), (-0.05, 0.95), (0.18, 0.78),
              (0.04, 1.0), (0.2, 0.8), (-0.03, 0.92), (0.15, 0.82)] * 2,           # drunk / unquantized
}
