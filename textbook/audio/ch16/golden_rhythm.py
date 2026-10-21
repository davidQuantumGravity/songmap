"""A golden rhythm: inter-onset intervals long (L) and short (S) with L/S = phi, ordered by the
Fibonacci word L S L L S L S L L S L L S ... (rule L -> LS, S -> L). 34 onsets, then for comparison
a periodic rhythm L S L S ... with the same two durations. S = 0.2 s, L = 0.2 * phi = 0.3236 s.
"""
from _lib import PHI, tone, at, freq

S = 0.2
L = S * PHI


def fib_word(n):
    w = "L"
    while len(w) < n:
        w = "".join("LS" if c == "L" else "L" for c in w)
    return w[:n]


def onsets(word, t0):
    t, out = t0, []
    for c in word:
        out.append(t)
        t += L if c == "L" else S
    return out, t


def render():
    w = fib_word(34)
    assert w.startswith("LSLLSLSLLSLLS") and w.count("L") == 21 and w.count("S") == 13
    a, t = onsets(w, 0.0)
    b, _ = onsets("LS" * 17, t + 1.0)
    clips = [(x, tone(freq(84) if c == "L" else freq(79), 0.08, "clean/keys", vel=0.6)) for x, c in zip(a, w)]
    clips += [(x, tone(freq(84) if c == "L" else freq(79), 0.08, "clean/keys", vel=0.6)) for x, c in zip(b, "LS" * 17)]
    return at(clips)
