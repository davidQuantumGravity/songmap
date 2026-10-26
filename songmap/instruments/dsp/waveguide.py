"""Digital waveguides: sustained physical models (bowed strings, reeds, flutes) and band-limited wavetables.

A waveguide is a delay line tuned to the note's period with a nonlinear exciter at one end, after the
STK instruments (Cook and Scavone): the string or air column rings at its own pitch, and the exciter (a bow
sticking and slipping, a reed opening and closing, an air jet flipping in and out of the mouthpiece) feeds
it energy for as long as the note is held. That is what makes these notes *live*: the tone settles into
oscillation, reacts to pressure and keeps moving, where an oscillator only repeats a cycle.
"""
from __future__ import annotations

import numpy as np
from numba import njit

from .core import SR

BOW_FIXED, REED_FIXED, JET_FIXED = 1.85, 0.97, 2.0     # loop delays besides the tuned lines (measured)


@njit(cache=True)
def _frac_read(buf, w, d, size):
    """Read `d` samples behind write index `w` (fractional, linear interpolation) from a circular buffer."""
    pos = w - d
    while pos < 0:
        pos += size
    i0 = int(pos)                                      # the older sample
    fr = pos - i0                                      # how far toward the newer one
    return (1.0 - fr) * buf[i0 % size] + fr * buf[(i0 + 1) % size]


@njit(cache=True)
def _lp_delay(a, period):
    """Phase delay (samples) of the one-pole loss filter y = (1-a) x + a y[-1] at the loop's frequency."""
    w = 2.0 * np.pi / period
    return np.arctan2(a * np.sin(w), 1.0 - a * np.cos(w)) / w


@njit(cache=True)
def _bowed(period, pressure, bowvel, beta, bright, exc, n):
    """Bowed string (STK Bowed): two delay lines meet at the bow, a velocity-dependent friction table
    makes the string stick and slip; a one-pole low-pass at the bridge is the string's damping."""
    size = int(4 * np.max(period)) + 8
    neck = np.zeros(size)
    bridge = np.zeros(size)
    out = np.zeros(n)
    wn = 0
    wb = 0
    lp = 0.0
    a = 1.0 - bright
    for i in range(n):
        p = period[i]
        base = p - BOW_FIXED - _lp_delay(a, p)                    # the loop's own delays come off the period (STK: -4)
        dn = max(1.0, base * (1.0 - beta))             # bow to nut
        db = max(1.0, base * beta)                     # bow to bridge
        bridge_out = _frac_read(bridge, wb, db, size)
        neck_out = _frac_read(neck, wn, dn, size)
        lp = (1.0 - a) * bridge_out + a * lp           # string loss at the bridge
        bridge_refl = -0.95 * lp                       # STK: string filter gain 0.95
        nut_refl = -neck_out
        string_vel = bridge_refl + nut_refl
        dv = bowvel[i] - string_vel + exc[i]
        # bow table: friction falls as the slip speed grows (stick-slip)
        s = dv * (5.0 - 4.0 * pressure[i]) + 0.001
        f = (abs(s) + 0.75) ** -4.0
        if f > 1.0:
            f = 1.0
        new_vel = dv * f
        wn = (wn + 1) % size
        wb = (wb + 1) % size
        neck[wn] = bridge_refl + new_vel
        bridge[wb] = nut_refl + new_vel
        out[i] = bridge_out
    return out


@njit(cache=True)
def _reed(period, breath, stiffness, bright, exc, n):
    """Single reed (STK Clarinet): a bore (delay line, closed at the reed, open at the bell) driven by
    a reed whose opening depends on the pressure difference across it."""
    size = int(2 * np.max(period)) + 8
    bore = np.zeros(size)
    out = np.zeros(n)
    w = 0
    lp = 0.0
    a = 1.0 - bright
    for i in range(n):
        d = max(1.0, 0.5 * period[i] - REED_FIXED - _lp_delay(a, period[i]))   # a closed-open bore: the wave goes there and back
        back = _frac_read(bore, w, d, size)
        lp = (1.0 - a) * back + a * lp
        pdiff = -0.95 * lp - breath[i] - exc[i]
        r = 0.7 + (-0.2 - 0.2 * stiffness[i]) * pdiff  # reed table: offset + slope (STK -0.3) * pressure difference
        if r > 1.0:
            r = 1.0
        if r < -1.0:
            r = -1.0
        w = (w + 1) % size
        bore[w] = breath[i] + exc[i] + pdiff * r
        out[i] = back
    return out


@njit(cache=True)
def _jet(period, breath, ratio, bright, exc, n):
    """Flute (STK Flute): an air jet crosses the embouchure (a short delay) and is deflected in or out of
    the bore by the returning wave (the cubic jet table x^3 - x); the bore is the long delay. The bore is
    tuned 1.5 times the period because the model overblows to the twelfth's partner (STK's 0.66666)."""
    size = int(2 * np.max(period) / 0.66666) + 8
    bore = np.zeros(size)
    jet = np.zeros(size)
    out = np.zeros(n)
    wb = 0
    wj = 0
    lp = 0.0
    dc_x = 0.0
    dc_y = 0.0
    a = 1.0 - bright
    for i in range(n):
        db = max(1.0, period[i] / 0.66666 - JET_FIXED - _lp_delay(a, period[i] / 0.66666))
        dj = max(1.0, db * ratio[i])
        back = _frac_read(bore, wb, db, size)
        lp = (1.0 - a) * back + a * lp
        temp = -lp
        dc_y = temp - dc_x + 0.99 * dc_y               # DC blocker
        dc_x = temp
        temp = dc_y
        pdiff = breath[i] + exc[i] - 0.5 * temp        # jet minus the bore's reflection (jetReflection 0.5)
        wj = (wj + 1) % size
        jet[wj] = pdiff
        j = _frac_read(jet, wj, dj, size)
        jt = j * (j * j - 1.0)                         # jet table
        if jt > 1.0:
            jt = 1.0
        if jt < -1.0:
            jt = -1.0
        wb = (wb + 1) % size
        bore[wb] = jt + 0.5 * temp                     # endReflection 0.5
        out[i] = back
    return out


def waveguide(mode: int, freq, pressure, env, position: float, bright: float, exc) -> np.ndarray:
    """mode 0 bowed string, 1 reed, 2 flute. `freq` and `pressure` are per-sample; `env` shapes the
    excitation (bow speed or breath), `position` is the bow position (0.04..0.5 from the bridge) or, for
    the flute, sets the jet length (0.2 + position of the bore; the default 0.12 gives 0.32), `exc` is extra excitation (e.g. breath noise). Notes long enough to sustain
    are measured and re-rendered in tune. The flute speaks cleanly from about 300 Hz up (a real flute starts at 262 Hz); lower,
    breath noise makes it overblow."""
    f = np.clip(np.asarray(freq, float), 20.0, 0.45 * SR) * np.ones(len(env))
    target = float(np.median(f))
    tuned = f
    y = _raw(mode, tuned, pressure, env, position, bright, exc)
    # the loop filter and the nonlinear exciter (bow friction, reed, jet) add phase delay that depends on the
    # note and the settings; the pitch is steady within a note, so measure it on the sustained part and
    # render again with the frequency corrected (twice: the correction itself moves the loop a little)
    for _ in range(2):
        got = _sustained_pitch(y, env, target)
        if not got or abs(1200 * np.log2(got / target)) < 2:
            break
        tuned = tuned * (target / got)
        y = _raw(mode, tuned, pressure, env, position, bright, exc)
    return y


def _sustained_pitch(y: np.ndarray, env: np.ndarray, target: float) -> float | None:
    """The pitch (Hz) over the note's sustained part, from the autocorrelation peak near the target period
    (robust to which partial is loudest), or None when the note is too short or doesn't speak."""
    on = np.nonzero(env > 0.9 * float(np.max(env)))[0] if len(env) else []
    if len(on) < int(0.12 * SR):
        return None
    seg = y[on[0] + int(0.04 * SR):on[-1]][: int(0.5 * SR)]
    if len(seg) < int(0.08 * SR) or float(np.sqrt(np.mean(seg ** 2))) < 1e-3:
        return None
    seg = seg - seg.mean()
    m = len(seg)
    spec = np.fft.rfft(seg, 2 * m)
    ac = np.fft.irfft(spec * np.conj(spec))[:m]
    if ac[0] <= 0:
        return None
    p0 = SR / target
    lo, hi = max(2, int(p0 * 0.85)), min(m - 2, int(p0 * 1.18) + 1)
    if hi <= lo:
        return None
    k = lo + int(np.argmax(ac[lo:hi]))
    if ac[k] < 0.3 * ac[0]:                            # not periodic at this pitch (noise, overblown)
        return None
    a_, b_, c_ = ac[k - 1], ac[k], ac[k + 1]           # parabolic interpolation of the peak
    den = a_ - 2 * b_ + c_
    period = k + (0.5 * (a_ - c_) / den if den < 0 else 0.0)
    return float(SR / period)


def _raw(mode: int, freq: np.ndarray, pressure: np.ndarray, env: np.ndarray, position: float,
              bright: float, exc: np.ndarray) -> np.ndarray:
    """The untuned models (see `waveguide`)."""
    freq = np.clip(np.asarray(freq, float), 20.0, 0.45 * SR)
    period = np.ascontiguousarray(SR / freq)
    n = len(period)
    pr = np.ascontiguousarray(np.clip(pressure, 0.0, 1.0))
    e = np.ascontiguousarray(env, dtype=np.float64)
    x = np.ascontiguousarray(exc, dtype=np.float64)
    b = float(np.clip(bright, 0.05, 0.99))
    if mode == 2:
        b *= 0.6                                       # the flute's bore is darker (STK pole ~0.65): bright 0.6 -> 0.36
    if mode == 0:
        y = _bowed(period, pr, 0.03 + 0.25 * pr * e, float(np.clip(position, 0.03, 0.5)), b, x, n)
    elif mode == 1:
        y = _reed(period, 0.55 + 0.45 * pr * e - (1 - e) * 0.55, np.full(n, 0.5), b, x * e, n)
    else:
        ratio = float(np.clip(0.2 + position, 0.1, 0.6))   # the default position (0.12) gives STK's jet ratio 0.32
        y = _jet(period, (0.8 + 0.5 * pr) * e, np.full(n, ratio), b, x * e, n)
    peak = float(np.max(np.abs(y))) if n else 0.0
    return y / peak * 0.8 if peak > 1e-9 else y


# ---------------------------------------------------------------------------------------------- wavetables
TABLES = ("basic", "bright", "pwm", "vowel", "organ")
_VOWELS = ((730, 1090, 2440), (530, 1840, 2480), (270, 2290, 3010), (570, 840, 2410), (300, 870, 2240))  # a e i o u
_ORGANS = ((8, 8, 8, 0, 0, 0, 0, 0, 0), (8, 0, 8, 8, 0, 8, 0, 0, 8), (8, 8, 8, 8, 8, 8, 8, 8, 8),
           (0, 0, 8, 8, 6, 4, 0, 0, 0), (6, 8, 8, 6, 0, 0, 0, 0, 0))


def _frames(table: int, f0: float, h: np.ndarray) -> np.ndarray:
    """Amplitude spectra (frames x harmonics) of a wavetable for a note at f0: the frames the position
    scans through, evenly spaced from 0 to 1."""
    H = len(h)
    if table == 0:                                      # sine -> triangle -> saw -> square
        sine = (h == 1).astype(float)
        tri = np.where(h % 2 == 1, 1.0 / h ** 2, 0.0) * 8 / np.pi ** 2
        saw = 1.0 / h * 2 / np.pi
        sq = np.where(h % 2 == 1, 1.0 / h, 0.0) * 4 / np.pi
        return np.stack([sine, tri, saw, sq])
    if table == 1:                                      # dark -> bright: harmonics falling as h^-p
        return np.stack([h ** -p for p in (4.0, 2.6, 1.8, 1.2, 0.8, 0.5)]) * 0.6
    if table == 2:                                      # pulse width 50% -> 5%
        return np.stack([np.abs(np.sin(np.pi * h * w)) / h * 4 / np.pi for w in (0.5, 0.35, 0.25, 0.15, 0.08, 0.05)])
    if table == 3:                                      # vowels a e i o u: formant peaks at fixed Hz
        fr = []
        for fs in _VOWELS:
            amp = np.zeros(H)
            for k, F in enumerate(fs):
                bw = 80 + 40 * k
                amp += np.exp(-0.5 * ((h * f0 - F) / bw) ** 2) * (1.0, 0.6, 0.35)[k]
            fr.append(amp / h ** 0.6 + 0.02 / h)
        return np.stack(fr)
    frames = []                                         # organ drawbar registrations, harmonics of the 16' pipe
    for reg in _ORGANS:
        amp = np.zeros(H)
        for lvl, mult in zip(reg, (1, 3, 2, 4, 6, 8, 10, 12, 16)):
            if mult <= H:
                amp[mult - 1] += lvl / 8
        frames.append(amp)
    return np.stack(frames)


def wavetable(table: int, freq: np.ndarray, position: np.ndarray, phase0: float = 0.0, fm: np.ndarray | None = None):
    """A band-limited wavetable oscillator: harmonics up to just below Nyquist for the note's highest pitch,
    the spectrum interpolated between frames as `position` (0..1, per sample) scans the table. Every frame
    has the same loudness, so scanning changes the colour, not the level."""
    freq = np.clip(np.asarray(freq, float), 1.0, 0.45 * SR)
    if int(table) == 4:
        freq = freq / 2                                 # organ: the cycle is the 16' sub-octave; 8' is the note
    n = len(freq)
    fmax = float(np.max(freq))
    H = max(1, min(96, int(0.45 * SR / fmax)))
    h = np.arange(1, H + 1, dtype=float)
    frames = _frames(int(table), float(np.median(freq)), h)
    frames = frames / np.maximum(np.sqrt((frames ** 2).sum(1, keepdims=True)), 1e-9) * 0.7   # same loudness per frame
    F = len(frames)
    pos = np.clip(np.asarray(position, float) * np.ones(n), 0.0, 1.0) * (F - 1)
    i0 = np.minimum(pos.astype(int), F - 2) if F > 1 else np.zeros(n, int)
    fr = (pos - i0) if F > 1 else np.zeros(n)
    ph = phase0 + np.cumsum(freq) / SR
    if fm is not None:
        ph = ph + fm / (2 * np.pi)
    # each frame as one band-limited cycle (N samples, from its harmonics), read by phase with linear
    # interpolation, frames cross-faded by position: O(n) instead of a sine per harmonic per sample
    N = 2048
    spec = np.zeros((F, N // 2 + 1), dtype=complex)
    spec[:, 1:H + 1] = -0.5j * N * frames               # sin(2 pi h x) for each harmonic h
    cycles = np.fft.irfft(spec, N, axis=1)
    cycles /= np.maximum(1.0, np.abs(cycles).max(1, keepdims=True))   # equal loudness, but never above 1
    x = (ph % 1.0) * N
    j0 = x.astype(int) % N
    jf = x - np.floor(x)
    j1 = (j0 + 1) % N
    a = cycles[i0, j0] * (1 - jf) + cycles[i0, j1] * jf
    if F > 1:
        b = cycles[np.minimum(i0 + 1, F - 1), j0] * (1 - jf) + cycles[np.minimum(i0 + 1, F - 1), j1] * jf
        return a * (1 - fr) + b * fr
    return a
