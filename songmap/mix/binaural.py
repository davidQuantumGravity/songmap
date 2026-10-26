"""Binaural beats: a layer of exact pure-tone pairs, one frequency in each ear (textbook ch41, ch48).

A song's `binaural:` block names carrier pitches. By default its difference d = f / 2**octaves (five octaves).
Each carrier f is split into a left tone
f - d/2 and a right tone f + d/2 (the mirrored detune of ch41: the pair is heard at f, and the ears differ by d).
Neither ear receives a beat; the flutter at d per second is made by the brain, on headphones only.

    binaural:
      carriers: [A3, E4]         # note names in the song's tuning (^F4, vD5), MIDI numbers, "220hz", "A3*phi^2"
      beat: octave               # default: each difference follows its own carrier, independent of list position
      octaves: 5                 # one shared divisor: A3=220 Hz -> 6.875 Hz; E4 -> 10.300861 Hz
      level_db: -12              # the layer's integrated loudness relative to the music's (LU)
      fade: 6                    # seconds in at the start and out at the end of the audio
      glide: 4                   # seconds: changes at a section start (beat, carriers) move smoothly
      breathe: 2                 # optional: a slow swell, one cycle every 2 bars (follows the tempo)
      breath_db: 3               # its depth
      carve: true                # the music gives up a narrow band around each carrier (see carve())

Explicit numeric beat values retain the older fixed-Hz mode, with optional `ladder: golden`, `same`, or a list.
Octave mode has no independent ladder or numeric section-rate overrides: the frequency ratio stays constant.
Sections may set carriers and gain; fixed-Hz mode also accepts beat ramps such as "10>6.18". Unset values
carry over from the previous section. A carrier that leaves or enters crossfades over `glide` seconds, so the pairs
never jump in pitch; beat changes glide, so they never click. Phases are integrated sample by sample from the
frequency curves. The layer is a stem (`binaural`), dry (never sent to a reverb, which would mix the ears).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np

from ..parse.errors import SongError, did_you_mean

PHI = (1 + 5 ** 0.5) / 2
SONG_KEYS = ("carriers", "beat", "octaves", "ladder", "level_db", "fade", "glide", "gain_db", "breathe", "breath_db", "carve")
SECTION_KEYS = ("carriers", "beat", "gain_db")
REF_HZ = 220.0          # carrier loudness weighting (f / 220)^-1/2: higher pairs a little softer
BLOCK = 1 << 15
CARVE_MARGIN = 3.0      # Hz beyond each carrier's widest beat/2 that the music gives up (see carve)
_NOTE = re.compile(r"([A-Ga-g])(#{1,2}|b{1,2})?(-?\d+)")
_PCS = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}


@dataclass
class Carrier:
    label: str
    hz: float


@dataclass
class State:
    """Per-section carriers and gain; beat is a fixed-mode Hz ramp, or unity in octave mode."""
    name: str
    t0: float
    t1: float
    carriers: list[Carrier]
    beat: tuple[float, float]
    gain: tuple[float, float]


@dataclass
class Plan:
    states: list[State]
    ladder: list[float]                    # independent multipliers in explicit fixed-Hz mode only
    level_db: float = -12.0
    fade: float = 4.0
    glide: float = 4.0
    breathe: float | None = None
    breath_db: float = 3.0
    carve: bool = True
    seconds: float = 0.0
    summary: list[dict] = field(default_factory=list)
    octaves: int | None = None              # None: explicit legacy fixed-Hz mode; integer: d = carrier / 2**n

    def rates(self, st: State, which: int = 0) -> list[float]:
        if self.octaves is not None:
            return [c.hz / 2 ** self.octaves for c in st.carriers]
        b = st.beat[which]
        return [b * self.ladder[i] for i in range(len(st.carriers))]


# ------------------------------------------------------------------------------------------------
# parsing
# ------------------------------------------------------------------------------------------------
def _err(msg, song, line=None, section=None, suggestion=None):
    return SongError(f"binaural: {msg}", file=song.file, line=line, section=section, suggestion=suggestion)


def carrier_hz(tok, song, line=None, section=None) -> Carrier:
    """'A3' -> 220 Hz; '^F4' (36edo); 57 (MIDI); '355.97hz'; 'A3*phi^2' (exact golden-chain tones)."""
    label = str(tok).strip()
    if isinstance(tok, (int, float)) and not isinstance(tok, bool):
        return Carrier(label, 440.0 * 2 ** ((float(tok) - 69) / 12))
    s = label.replace(" ", "")
    m = re.fullmatch(r"(\d+(?:\.\d+)?)hz", s, re.I)
    if m:
        return Carrier(label, float(m[1]))
    mult = 1.0
    m = re.fullmatch(r"(.+?)\*(phi|φ)(?:\^(-?\d+(?:\.\d+)?))?", s, re.I)
    if m:
        s, mult = m[1], PHI ** float(m[3] or 1)
    from ..theory.tuning import split_updown
    off, rest = split_updown(s)
    m = _NOTE.fullmatch(rest)
    if not m:
        raise _err(f"carrier '{label}' not understood", song, line, section,
                   "write a note with its octave (A3, ^F4, vD5), a MIDI number, '220hz' or 'A3*phi^2'")
    if off and song.tuning == "12edo":
        raise _err(f"carrier '{label}' uses a sixth-step accidental", song, line, section,
                   "add tuning=36edo to the song, or give the carrier in hz")
    acc = (len(m[2]) if m[2] and m[2][0] == "#" else -len(m[2]) if m[2] else 0)
    midi = 12 * (int(m[3]) + 1) + _PCS[m[1].lower()] + acc + off
    hz = 440.0 * 2 ** ((midi - 69) / 12) * mult
    if not 90 <= hz <= 1500:
        raise _err(f"carrier '{label}' is {hz:.1f} Hz", song, line, section,
                   "binaural beats are heard on carriers of about 100-1000 Hz (clearest at 200-500)")
    return Carrier(label, hz)


def _carriers(v, song, line=None, section=None) -> list[Carrier]:
    items = v.split() if isinstance(v, str) else v if isinstance(v, (list, tuple)) else [v]
    if not items:
        raise _err("no carriers", song, line, section, "give one or more chord tones, e.g. carriers: [A3, E4]")
    return [carrier_hz(x, song, line, section) for x in items]


def _ramp(v, what, song, line=None, section=None, positive=True) -> tuple[float, float]:
    """10 -> (10, 10); '10>6.18' -> (10, 6.18)."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        a = b = float(v)
    else:
        m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*(?:>\s*(-?\d+(?:\.\d+)?)\s*)?", str(v))
        if not m:
            raise _err(f"{what} '{v}' not understood", song, line, section, f"write {what}: 10 or {what}: 10>6.18")
        a = float(m[1])
        b = float(m[2]) if m[2] is not None else a
    if positive and (a <= 0 or b <= 0):
        raise _err(f"{what} must be positive", song, line, section)
    if what == "beat" and max(a, b) > 45:
        raise _err(f"beat {max(a, b):g} Hz is too fast to be heard as a binaural beat", song, line, section,
                   "binaural beats are heard up to about 30-40 Hz; the bands are delta < 4, theta 4-8, alpha 8-13")
    return a, b


def _ladder(v, n, song) -> list[float]:
    if v is None or v == "golden":
        return [PHI ** -i for i in range(max(n, 1))]
    if v == "same":
        return [1.0] * max(n, 1)
    if isinstance(v, (list, tuple)) and all(isinstance(x, (int, float)) and x > 0 for x in v):
        if len(v) < n:
            raise _err(f"ladder has {len(v)} rungs for {n} carriers", song,
                       suggestion="give one multiplier per carrier, or ladder: golden")
        return [float(x) for x in v]
    raise _err(f"ladder '{v}' not understood", song,
               suggestion="ladder: golden (1, 1/phi, 1/phi^2, ...), same, or a list of multipliers [1, 0.618]")


def _check(d, keys, song, where, line=None, section=None):
    if not isinstance(d, dict):
        raise _err(f"{where} must be a mapping", song, line, section,
                   "e.g. binaural: {carriers: [A3, E4], beat: 10}")
    for k in d:
        if k not in keys:
            raise _err(f"unknown key '{k}' in {where}", song, line, section, did_you_mean(k, keys))


def plan(song, tl) -> Plan | None:
    """The layer's plan, validated (errors carry the song file and line); None when the song has no layer."""
    spec = song.binaural
    if not spec:
        return None
    _check(spec, SONG_KEYS, song, "the song's binaural block")
    if "carriers" not in spec:
        raise _err("the song's binaural block needs carriers", song,
                   suggestion="name chord tones that sound throughout, e.g. carriers: [A3, E4]")
    carriers = _carriers(spec["carriers"], song)
    mode = spec.get("beat", "octave")
    octaves = None
    if mode == "octave":
        octaves = spec.get("octaves", 5)
        if isinstance(octaves, bool) or not isinstance(octaves, int) or not 1 <= octaves <= 24:
            raise _err("octaves must be a positive integer from 1 to 24", song,
                       suggestion="use beat: octave and octaves: 5 for difference = carrier frequency / 32")
        if "ladder" in spec:
            raise _err("octave-derived differences have no independent ladder", song,
                       suggestion="omit ladder; each carrier supplies its own difference as f / 2**octaves")
        beat = (1.0, 1.0)                 # unity base; the oscillator multiplier is its own octave-reduced Hz
    else:
        if "octaves" in spec:
            raise _err("octaves cannot be combined with a fixed beat rate", song,
                       suggestion="use beat: octave to derive rates from the notes, or remove octaves for fixed-Hz mode")
        beat = _ramp(mode, "beat", song)
    gain = _ramp(spec.get("gain_db", 0), "gain_db", song, positive=False)
    width = len(carriers)
    states = []
    for sec, span in zip(song.sections, tl.sections):
        d = sec.binaural or {}
        _check(d, SECTION_KEYS, song, f"section {sec.name}'s binaural", sec.line, sec.name)
        if "carriers" in d:
            carriers = _carriers(d["carriers"], song, sec.line, sec.name)
        if "beat" in d:
            if octaves is not None:
                if d["beat"] != "octave":
                    raise _err("a fixed section beat would break octave tracking", song, sec.line, sec.name,
                               "omit the section beat; carrier changes automatically change the differences")
            else:
                beat = _ramp(d["beat"], "beat", song, sec.line, sec.name)
        elif states:
            beat = (states[-1].beat[1],) * 2          # a ramp ends where it ends: the next section holds it
        if "gain_db" in d:
            gain = _ramp(d["gain_db"], "gain_db", song, sec.line, sec.name, positive=False)
        elif states:
            gain = (states[-1].gain[1],) * 2
        width = max(width, len(carriers))
        states.append(State(sec.name, tl.beat_to_sec(span.start), tl.beat_to_sec(span.end), carriers, beat, gain))
    num = lambda k, dflt: float(_ramp(spec.get(k, dflt), k, song, positive=False)[0])     # noqa: E731
    p = Plan(states, _ladder(spec.get("ladder"), width, song) if octaves is None else [1.0] * width, level_db=num("level_db", -12),
             fade=max(num("fade", 4), 0.0), glide=max(num("glide", 4), 0.05),
             breathe=float(spec["breathe"]) if spec.get("breathe") else None, breath_db=num("breath_db", 3),
             carve=bool(spec.get("carve", True)), octaves=octaves)
    p.seconds = tl.seconds
    for st in states:
        if octaves is not None and any(not np.isfinite(r) or r <= 0 or r > 45 for r in p.rates(st)):
            raise _err("octave-derived beat rates must be positive and at most 45 Hz", song, section=st.name,
                       suggestion="increase octaves to reduce the differences while preserving note-frequency ratios")
        p.summary.append({"section": st.name, "carriers_hz": [round(c.hz, 3) for c in st.carriers],
                          "beats_hz": [[round(a, 3), round(b, 3)] for a, b in zip(p.rates(st, 0), p.rates(st, 1))]})
        if octaves is not None:
            p.summary[-1].update(rate_mode="octave", octaves=octaves)
    return p


def describe(p: Plan) -> list[str]:
    """One line per change, for `songmap check`."""
    out, last = [], None
    for st, s in zip(p.states, p.summary):
        txt = ", ".join(f"{c.label} {c.hz:.2f} Hz @ " + (f"{a:.2f}" if abs(a - b) < 1e-9 else f"{a:.2f}>{b:.2f}")
                        for c, (a, b) in zip(st.carriers, s["beats_hz"]))
        if p.octaves is not None:
            txt += f" (each difference = its carrier / 2^{p.octaves})"
        if txt != last:
            out.append(f"{st.name}: {txt}")
        last = txt
    return out


# ------------------------------------------------------------------------------------------------
# synthesis
# ------------------------------------------------------------------------------------------------
def _curve(points, log=False):
    """[(t, v)] (t non-decreasing) -> (times, values) for np.interp; log curves interpolate geometrically."""
    t = np.array([p[0] for p in points], dtype=np.float64)
    v = np.array([p[1] for p in points], dtype=np.float64)
    return t, (np.log(v) if log else v)


def _ramped(states, get, glide, log):
    """Breakpoints of a per-section ramp (a at the start, b at the end) that glides from the previous value."""
    pts, cur = [], None
    for st in states:
        a, b = get(st)
        g = min(glide, (st.t1 - st.t0) / 2) if st.t1 > st.t0 else 0.0
        if cur is None:
            pts.append((st.t0, a))
        elif abs(a - cur) > 1e-12 and g > 0:
            frac = g / (st.t1 - st.t0)
            mid = a * (b / a) ** frac if log else a + (b - a) * frac
            pts += [(st.t0, cur), (st.t0 + g, mid)]
        else:
            pts.append((st.t0, a))
        pts.append((st.t1, b))
        cur = b
    return pts


def _oscillators(p: Plan, end: float):
    """One pair per distinct carrier: (hz, amplitude curve, rung-multiplier curve, widest beat in Hz). A carrier
    that enters or leaves crossfades over `glide` seconds; one that changes rung glides to its new rate."""
    keys: dict[float, Carrier] = {}
    for st in p.states:
        for c in st.carriers:
            keys.setdefault(round(c.hz, 6), c)
    out = []
    for k, c in keys.items():
        amp, mul, cur_a, cur_m, widest = [], [], None, None, 0.0
        for st in p.states:
            idx = next((i for i, x in enumerate(st.carriers) if round(x.hz, 6) == k), None)
            a = 1.0 if idx is not None else 0.0
            m = (c.hz / 2 ** p.octaves if p.octaves is not None else
                 p.ladder[idx] if idx is not None else (cur_m if cur_m is not None else p.ladder[0]))
            if idx is not None:
                widest = max(widest, max(st.beat) * m)
            g = min(p.glide, (st.t1 - st.t0) / 2) if st.t1 > st.t0 else 0.0
            for pts, cur, new in ((amp, cur_a, a), (mul, cur_m, m)):
                if cur is None:
                    pts.append((st.t0, new))
                elif abs(new - cur) > 1e-12 and g > 0:
                    pts += [(st.t0, cur), (st.t0 + g, new)]
                else:
                    pts.append((st.t0, new))
            cur_a, cur_m = a, m
        amp.append((end, cur_a))
        mul.append((end, cur_m))
        out.append((c.hz, _curve(amp), _curve(mul), widest))
    return out


def _fade(p: Plan, t: np.ndarray, end: float) -> np.ndarray:
    if p.fade <= 0:
        return np.ones_like(t)
    return (np.sin(0.5 * np.pi * np.clip(t / p.fade, 0, 1)) ** 2
            * np.sin(0.5 * np.pi * np.clip((end - t) / p.fade, 0, 1)) ** 2)


def render_layer(p: Plan, tl, n: int, music: np.ndarray | None = None, sr: int = 48000) -> np.ndarray:
    """The layer, (n, 2) float64, at `level_db` LU relative to `music` (its integrated loudness)."""
    end = n / sr
    beat_pts = _ramped(p.states, lambda st: st.beat, p.glide, True) + [(end, p.states[-1].beat[1])]
    gain_pts = _ramped(p.states, lambda st: st.gain, p.glide, False) + [(end, p.states[-1].gain[1])]
    bt, bv = _curve(beat_pts, log=True)
    gt, gv = _curve(gain_pts)
    osc = [(hz, (REF_HZ / hz) ** 0.5, amp, mul, [0.0, 0.0]) for hz, amp, mul, _ in _oscillators(p, end)]
    bpb = tl.bpb
    sec_grid = np.linspace(0.0, end, max(int(end * 20), 2))
    beat_grid = np.array([tl.sec_to_beat(float(t)) for t in sec_grid])
    y = np.zeros((n, 2))
    for i0 in range(0, n, BLOCK):
        m = min(BLOCK, n - i0)
        t = (i0 + np.arange(m)) / sr
        B = np.exp(np.interp(t, bt, bv))
        env = 10 ** (np.interp(t, gt, gv) / 20) * _fade(p, t, end)
        if p.breathe:
            cyc = np.interp(t, sec_grid, beat_grid) / (bpb * p.breathe)
            env *= 10 ** (-p.breath_db * (0.5 + 0.5 * np.cos(2 * np.pi * cyc)) / 20)
        for hz, w, (at, av), (mt, mv), ph in osc:
            a = np.interp(t, at, av)
            d = B * np.interp(t, mt, mv)
            for ch, f in ((0, hz - d / 2), (1, hz + d / 2)):
                inc = f / sr
                phase = ph[ch] + np.cumsum(inc) - inc              # phase at each sample, in cycles
                y[i0:i0 + m, ch] += w * a * env * np.sin(2 * np.pi * phase)
                ph[ch] = (ph[ch] + float(inc.sum())) % 1.0
    from ..export.qa import lufs
    ref = lufs(music) if music is not None and np.any(music) else -70.0
    if ref <= -69:
        ref = -30.0                                    # no music: place the layer at -30 + level_db LUFS
    have = lufs(y)
    if have > -69:
        y *= 10 ** ((ref + p.level_db - have) / 20)
    return y


def carve(p: Plan, music: np.ndarray, sr: int = 48000) -> np.ndarray:
    """What the layer takes out of the music: a narrow band around each carrier (its widest beat, plus
    CARVE_MARGIN Hz on each side), wherever that carrier sounds. Subtract it from the mix. Without it, a music
    tone held at a carrier's own pitch (a host organ's A3, a pad's A3) beats against each ear's detuned tone
    at half the binaural rate: a pulse in the air that is not on the ladder. With it, the pair replaces the
    music's own tone at that pitch, so the layer sits inside the music rather than on top of it."""
    from scipy.signal import butter, sosfiltfilt
    n = len(music)
    end = n / sr
    t = np.arange(n) / sr
    fade = _fade(p, t, end)
    out = np.zeros_like(music)
    for hz, (at, av), _, widest in _oscillators(p, end):
        w = widest / 2 + CARVE_MARGIN
        sos = butter(2, [hz - w, hz + w], btype="bandpass", fs=sr, output="sos")
        out += sosfiltfilt(sos, music, axis=0) * (np.interp(t, at, av) * fade)[:, None]
    return out


def beat_rates(p: Plan) -> list[float]:
    """Every distinct steady beat rate the plan reaches (Hz, rounded), for reports."""
    out = sorted({round(r, 3) for st in p.states for w in (0, 1) for r in p.rates(st, w)})
    return out


__all__ = ["plan", "render_layer", "carve", "carrier_hz", "describe", "beat_rates", "PHI", "SONG_KEYS",
           "SECTION_KEYS"]
