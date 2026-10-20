"""Original soundtrack synthesizer for the two weekly videos.
120 BPM, 4/4, 60 bars = 120 s. Everything is generated from scratch (no samples)."""
import numpy as np, json, sys
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile

SR = 44100
BPM = 120
BEAT = 60 / BPM
BAR = 4 * BEAT
NBARS = int(__import__('os').environ.get('NBARS', '60'))
TAIL = 3.0
N = int((NBARS * BAR + TAIL) * SR)
rng = np.random.default_rng(7)

def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)

def env_adsr(n, a, d, s, r, sr=SR):
    a, d, r = int(a*sr), int(d*sr), int(r*sr)
    e = np.ones(n) * s
    if a: e[:min(a, n)] = np.linspace(0, 1, a)[:min(a, n)]
    if d and a < n:
        k = min(d, n - a); e[a:a+k] = np.linspace(1, s, d)[:k]
    if r:
        k = min(r, n); e[-k:] *= np.linspace(1, 0, k)
    return e

def saw(f, t, detune=0.0):
    ph = (f * (1 + detune)) * t
    return 2 * (ph - np.floor(ph + 0.5))

def square(f, t, pw=0.5):
    ph = (f * t) % 1.0
    return np.where(ph < pw, 1.0, -1.0)

def lp(x, fc, order=2):
    fc = min(fc, SR * 0.45)
    return sosfilt(butter(order, fc, 'low', fs=SR, output='sos'), x)

def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, 'high', fs=SR, output='sos'), x)

def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)

class Track:
    def __init__(self): self.L = np.zeros(N); self.R = np.zeros(N)
    def add(self, start_s, sig, gain=1.0, pan=0.0):
        i = int(start_s * SR)
        if i >= N: return
        sig = sig[:N - i] * gain
        l = np.cos((pan + 1) * np.pi / 4); r = np.sin((pan + 1) * np.pi / 4)
        self.L[i:i+len(sig)] += sig * l * 1.414
        self.R[i:i+len(sig)] += sig * r * 1.414

# ---------- instruments ----------
def kick(dur=0.45):
    n = int(dur*SR); t = np.arange(n)/SR
    f = 45 + 110*np.exp(-t*28)
    ph = 2*np.pi*np.cumsum(f)/SR
    body = np.sin(ph) * np.exp(-t*7)
    click = rng.standard_normal(n) * np.exp(-t*300) * 0.3
    return np.tanh((body + click) * 1.6)

def snare(dur=0.3):
    n = int(dur*SR); t = np.arange(n)/SR
    tone = np.sin(2*np.pi*190*t) * np.exp(-t*25)
    nz = bp(rng.standard_normal(n), 1200, 9000) * np.exp(-t*14)
    return 0.6*tone + 0.9*nz

def clap(dur=0.35):
    n = int(dur*SR); t = np.arange(n)/SR
    e = np.zeros(n)
    for k, off in enumerate([0, 0.011, 0.022, 0.034]):
        i = int(off*SR); e[i:] += np.exp(-(t[:n-i])*(60 if k < 3 else 13))
    return bp(rng.standard_normal(n), 900, 6000) * e * 0.8

def hat(dur=0.06, open_=False):
    dur = 0.28 if open_ else dur
    n = int(dur*SR); t = np.arange(n)/SR
    return hp(rng.standard_normal(n), 7000, 4) * np.exp(-t*(12 if open_ else 70))

def bass_note(m, dur, cutoff=900):
    n = int(dur*SR); t = np.arange(n)/SR; f = mtof(m)
    x = saw(f, t) + 0.5*saw(f, t, 0.006) + 0.8*np.sin(2*np.pi*f/2*t)
    x = lp(x, cutoff)
    return np.tanh(x*1.4) * env_adsr(n, 0.004, 0.12, 0.7, 0.04)

def pad_chord(ms, dur, cutoff=1800, bright=1.0):
    n = int(dur*SR); t = np.arange(n)/SR; x = np.zeros(n)
    for m in ms:
        f = mtof(m)
        for d in (-0.008, -0.003, 0.003, 0.008):
            x += saw(f, t + rng.random()*0.01, d)
    x = lp(x, cutoff*bright, 2) / (len(ms)*4)
    return x * env_adsr(n, 0.35, 0.3, 0.85, 0.6)

def pluck(m, dur=0.22, bright=4000, pw=0.35):
    n = int(dur*SR); t = np.arange(n)/SR; f = mtof(m)
    x = square(f, t, pw) * 0.6 + saw(f, t, 0.004) * 0.5
    x = lp(x, bright)
    return x * np.exp(-t*14) * env_adsr(n, 0.002, 0.0, 1.0, 0.02)

def lead_note(m, dur, cutoff=5000):
    n = int(dur*SR); t = np.arange(n)/SR; f = mtof(m)
    vib = 1 + 0.004*np.sin(2*np.pi*5.5*t) * np.clip((t-0.15)*4, 0, 1)
    x = np.zeros(n)
    for d in (-0.012, -0.005, 0, 0.005, 0.012):
        ph = np.cumsum(f*(1+d)*vib)/SR
        x += 2*(ph - np.floor(ph+0.5))
    x = lp(x/5, cutoff)
    return x * env_adsr(n, 0.01, 0.15, 0.75, 0.12)

def riser(dur):
    n = int(dur*SR); t = np.arange(n)/SR
    nz = rng.standard_normal(n); out = np.zeros(n); seg = 2048
    for i in range(0, n, seg):
        p = i/n; fc = 300 + 9000*p**2.2
        out[i:i+seg] = bp(nz[i:i+seg], fc*0.7, min(fc*1.4, 20000))
    tone_f = 110*2**(3*t/dur)
    tone = np.sin(2*np.pi*np.cumsum(tone_f)/SR)*0.25
    return (out*0.8 + tone) * (t/dur)**2

def impact(dur=3.0):
    n = int(dur*SR); t = np.arange(n)/SR
    f = 30 + 70*np.exp(-t*6)
    boom = np.sin(2*np.pi*np.cumsum(f)/SR) * np.exp(-t*1.6)
    nz = lp(rng.standard_normal(n), 2500) * np.exp(-t*3) * 0.5
    crash = hp(rng.standard_normal(n), 5000) * np.exp(-t*1.2) * 0.25
    return np.tanh((boom + nz + crash)*1.5)

def zap(dur=0.35, f0=2400):
    n = int(dur*SR); t = np.arange(n)/SR
    f = f0*np.exp(-t*14) + 80
    x = square(1, np.cumsum(f)/SR) * np.exp(-t*9)
    return lp(x, 6000) * 0.5

def tick(dur=0.03):
    n = int(dur*SR); t = np.arange(n)/SR
    return np.sin(2*np.pi*3200*t) * np.exp(-t*220)

def reverb(x, secs=2.2, wet=0.25):
    n = int(secs*SR); t = np.arange(n)/SR
    ir = rng.standard_normal(n) * np.exp(-t*3.2/secs*2.3)
    ir = lp(ir, 6000); ir /= np.sqrt(np.sum(ir**2))
    return x + wet*fftconvolve(x, ir)[:len(x)]

# ---------- arrangement ----------
def build(spec):
    root_seq = spec['chords']           # list of (root midi, chord tones) per 2 bars
    sections = spec['sections']         # bar -> set of active parts
    drums, bass, pad, arp, lead, fx = Track(), Track(), Track(), Track(), Track(), Track()
    kicks = []
    def chord_at(bar): return root_seq[(bar // 2) % len(root_seq)]
    for bar in range(NBARS):
        on = sections(bar)
        t0 = bar*BAR
        root, tones = chord_at(bar)
        # drums
        if 'kick' in on:
            for b in range(4):
                drums.add(t0+b*BEAT, kick(), 0.95); kicks.append(t0+b*BEAT)
        if 'halfkick' in on:
            for b in (0, 2.5):
                drums.add(t0+b*BEAT, kick(), 0.95); kicks.append(t0+b*BEAT)
        if 'snare' in on:
            for b in (1, 3): drums.add(t0+b*BEAT, snare(), 0.45); drums.add(t0+b*BEAT, clap(), 0.35)
        if 'halfsnare' in on:
            drums.add(t0+2*BEAT, snare(), 0.5); drums.add(t0+2*BEAT, clap(), 0.4)
        if 'hats' in on:
            for e in range(8):
                drums.add(t0+e*BEAT/2, hat(open_=(e % 2 == 1 and 'openhat' in on)), 0.16 if e % 2 else 0.1, pan=0.25)
        if 'hats16' in on:
            for s in range(16):
                drums.add(t0+s*BEAT/4, hat(0.04), 0.07 + 0.04*(s % 4 == 2), pan=-0.3)
        if 'ticks' in on:
            for s in range(16):
                if s % 4 == 0 or rng.random() < 0.35:
                    fx.add(t0+s*BEAT/4, tick(), 0.12, pan=rng.uniform(-0.7, 0.7))
        if 'fill' in on and bar % 8 == 7:
            for s in range(8):
                drums.add(t0+2*BEAT+s*BEAT/4, snare(0.15), 0.18+0.04*s)
        # bass: 8ths with octave bounce
        if 'bass' in on:
            for e in range(8):
                m = root - 24 + (12 if e % 2 else 0)
                bass.add(t0+e*BEAT/2, bass_note(m, BEAT/2*0.9, spec.get('basscut', 900)), 0.32)
        if 'subbass' in on:
            bass.add(t0, bass_note(root-24, BAR*0.98, 300), 0.35)
        # pad
        if 'pad' in on and bar % 2 == 0:
            br = 0.45 if 'darkpad' in on else 1.0
            pad.add(t0, pad_chord([m + 12 for m in tones], 2*BAR, 1800, br), 0.5)
        # arp
        if 'arp' in on or 'arpdark' in on:
            seq = spec['arp']
            for s in range(16):
                deg = seq[s % len(seq)]
                m = tones[deg % len(tones)] + 12*(1 + deg // len(tones))
                bright = 1500 if 'arpdark' in on else 2500 + 3000*((bar % 8)/8)
                arp.add(t0+s*BEAT/4, pluck(m, 0.2, bright), 0.13, pan=0.35*np.sin(s*0.8))
        # lead melody
        if 'lead' in on:
            mel = spec['melody'][(bar // 2) % len(spec['melody'])]
            half = bar % 2
            for (pos, deg, length) in mel:
                if int(pos // 4) != half: continue
                st = t0 + (pos - 4*half)*BEAT
                m = spec['scale'](root, deg)
                lead.add(st, lead_note(m, length*BEAT*0.95), 0.16, pan=0.0)
    # fx
    for (bar, kind, arg) in spec['fx']:
        t0 = bar*BAR
        if kind == 'riser': fx.add(t0 - arg*BAR, riser(arg*BAR), 0.35)
        if kind == 'impact': fx.add(t0, impact(), 0.75)
        if kind == 'zap':
            for k in range(arg): fx.add(t0 + k*BEAT/2, zap(f0=2000+600*k), 0.25, pan=rng.uniform(-0.5, 0.5))
    # sidechain
    sc = np.ones(N)
    for k in kicks:
        i = int(k*SR); n = int(0.28*SR)
        if i < N:
            seg = 1 - 0.6*np.exp(-np.arange(min(n, N-i))/SR*14)
            sc[i:i+len(seg)] = np.minimum(sc[i:i+len(seg)], seg)
    for tr in (bass, pad, arp, lead):
        tr.L *= sc; tr.R *= sc
    # reverb sends
    def wetify(tr, w):
        tr.L = reverb(tr.L, wet=w); tr.R = reverb(tr.R[::1], wet=w*1.05)
    for tr, w in ((pad, 0.35), (arp, 0.3), (lead, 0.35), (fx, 0.3)):
        wetify(tr, w)
    L = sum(t.L for t in (drums, bass, pad, arp, lead, fx))
    R = sum(t.R for t in (drums, bass, pad, arp, lead, fx))
    st = np.stack([L, R], 1)
    st = hp(st.T, 28).T
    st /= np.max(np.abs(st)) + 1e-9
    st = np.tanh(st * 1.6) / np.tanh(1.6)   # gentle master saturation / limiting
    # fade out tail
    fo = int(2.5*SR); st[-fo:] *= np.linspace(1, 0, fo)[:, None]
    return (st * 0.89).astype(np.float32)

# minor scale helper
MINOR = [0, 2, 3, 5, 7, 8, 10]
def scale_from(key_root):
    def f(root, deg):
        o, d = divmod(deg, 7)
        return key_root + 12 + MINOR[d] + 12*o
    return f

def S(*parts): return set(parts)

# ---- Video A: D minor, cinematic electro ----
D = 62
chA = [(D, [62, 65, 69]), (58, [58, 62, 65]), (65, [65, 69, 72]), (60, [60, 64, 67])]  # Dm Bb F C
def secA(bar):
    if bar < 2: return S('pad', 'darkpad', 'subbass')
    if bar < 4: return S('pad', 'darkpad', 'subbass', 'ticks', 'arpdark')
    if bar < 7: return S('kick', 'snare', 'hats', 'bass', 'pad', 'arp')
    if bar < 13: return S('halfkick', 'halfsnare', 'hats', 'subbass', 'pad', 'arpdark')
    if bar < 16: return S('pad', 'darkpad', 'ticks', 'subbass')
    if bar < 22: return S('kick', 'snare', 'hats', 'bass', 'pad', 'arp', 'fill')
    if bar < 34: return S('kick', 'snare', 'hats', 'openhat', 'bass', 'pad', 'arp', 'lead', 'fill')
    if bar < 36: return S('pad', 'arpdark', 'ticks')
    if bar < 44: return S('halfkick', 'halfsnare', 'hats', 'subbass', 'pad', 'arpdark')
    if bar < 52: return S('kick', 'snare', 'hats', 'bass', 'pad', 'arp', 'fill')
    if bar < 54: return S('pad', 'darkpad', 'ticks', 'subbass')
    if bar < 70: return S('kick', 'snare', 'hats', 'hats16', 'openhat', 'bass', 'pad', 'arp', 'lead', 'fill')
    if bar < 72: return S('pad', 'arp', 'subbass')
    return S('pad', 'darkpad')
melA = [
    [(0, 4, 1.5), (1.5, 3, 0.5), (2, 2, 1), (3, 4, 1), (4, 7, 2), (6, 6, 1), (7, 4, 1)],
    [(0, 3, 1.5), (1.5, 2, 0.5), (2, 1, 1), (3, 3, 1), (4, 5, 3), (7, 4, 1)],
    [(0, 2, 1), (1, 4, 1), (2, 6, 1), (3, 7, 1), (4, 9, 2), (6, 7, 1), (7, 6, 1)],
    [(0, 6, 1.5), (1.5, 5, 0.5), (2, 4, 2), (4, 6, 2), (6, 4, 2)],
]
specA = dict(chords=chA, sections=secA, arp=[0, 1, 2, 3, 2, 1, 4, 2], melody=melA,
             scale=lambda root, deg: scale_from(62)(root, deg),
             fx=[(4, 'riser', 2), (4, 'impact', 0), (2, 'zap', 6), (7, 'zap', 4), (13, 'impact', 0), (13, 'zap', 6),
                 (16, 'riser', 2), (16, 'impact', 0), (22, 'riser', 1), (36, 'riser', 2), (36, 'impact', 0),
                 (44, 'riser', 1), (54, 'riser', 2), (54, 'impact', 0), (62, 'riser', 1),
                 (70, 'impact', 0), (72, 'impact', 0)])

# ---- Video B: E minor, driving machine-techno ----
E = 64
chB = [(E, [64, 67, 71]), (60, [60, 64, 67]), (67, [67, 71, 74]), (62, [62, 66, 69])]  # Em C G D
def secB(bar):
    if bar < 4: return S('arpdark', 'ticks', 'subbass')
    if bar < 8: return S('kick', 'hats', 'bass', 'arpdark', 'ticks')
    if bar < 16: return S('kick', 'snare', 'hats', 'bass', 'arp', 'pad', 'fill')
    if bar < 18: return S('pad', 'darkpad', 'ticks')
    if bar < 34: return S('kick', 'snare', 'hats', 'openhat', 'bass', 'arp', 'pad', 'lead', 'fill')
    if bar < 36: return S('pad', 'arpdark', 'ticks', 'subbass')
    if bar < 52: return S('kick', 'snare', 'hats', 'hats16', 'openhat', 'bass', 'arp', 'pad', 'lead', 'fill', 'ticks')
    if bar < 56: return S('pad', 'arpdark', 'subbass')
    if bar < 58: return S('pad', 'arp')
    return S('pad', 'darkpad')
melB = [
    [(0, 7, 1), (1, 4, 1), (2, 7, 1), (3, 9, 1), (4, 8, 2), (6, 7, 2)],
    [(0, 5, 1), (1, 4, 1), (2, 5, 1), (3, 7, 1), (4, 6, 3), (7, 4, 1)],
    [(0, 9, 1), (1, 7, 1), (2, 9, 1), (3, 11, 1), (4, 10, 2), (6, 9, 2)],
    [(0, 8, 1.5), (1.5, 7, 0.5), (2, 6, 2), (4, 4, 4)],
]
specB = dict(chords=chB, sections=secB, arp=[0, 2, 1, 3, 0, 2, 4, 3, 1, 2, 0, 3], melody=melB,
             scale=lambda root, deg: scale_from(64)(root, deg - 7), basscut=700,
             fx=[(4, 'impact', 0), (8, 'riser', 1), (18, 'riser', 2), (18, 'impact', 0), (26, 'riser', 1),
                 (36, 'riser', 2), (36, 'impact', 0), (44, 'riser', 1), (56, 'impact', 0), (58, 'impact', 0)])

# ---- Video C: A minor, calm documentary electronica, 150 bars ----
chC = [(57, [57, 60, 64]), (53, [53, 57, 60]), (60, [60, 64, 67]), (55, [55, 59, 62])]  # Am F C G
def secC(bar):
    if bar < 6: return S('pad', 'darkpad', 'subbass')
    if bar < 28: return S('halfkick', 'hats', 'pad', 'arpdark', 'subbass')
    if bar < 66: return S('kick', 'hats', 'bass', 'pad', 'arp')
    if bar < 84: return S('kick', 'hats', 'openhat', 'bass', 'pad', 'arp', 'snare')
    if bar < 106: return S('halfkick', 'halfsnare', 'hats', 'subbass', 'pad', 'arpdark')
    if bar < 122: return S('kick', 'snare', 'hats', 'bass', 'pad', 'arp', 'lead')
    if bar < 138: return S('halfkick', 'hats', 'pad', 'arpdark', 'subbass')
    if bar < 146: return S('kick', 'snare', 'hats', 'bass', 'pad', 'arp', 'lead')
    return S('pad', 'darkpad')
melC = [
    [(0, 4, 2), (2, 2, 2), (4, 4, 1), (5, 5, 1), (6, 4, 2)],
    [(0, 2, 2), (2, 0, 2), (4, 2, 4)],
    [(0, 4, 2), (2, 6, 2), (4, 7, 2), (6, 6, 2)],
    [(0, 5, 3), (3, 4, 1), (4, 1, 4)],
]
specC = dict(chords=chC, sections=secC, arp=[0, 2, 4, 2, 1, 3, 2, 4], melody=melC,
             scale=lambda root, deg: scale_from(57)(root, deg), basscut=600,
             fx=[(6, 'impact', 0), (28, 'riser', 2), (28, 'impact', 0), (66, 'riser', 1), (84, 'impact', 0),
                 (106, 'riser', 2), (106, 'impact', 0), (138, 'riser', 2), (138, 'impact', 0), (146, 'impact', 0)])

if __name__ == '__main__':
    which = sys.argv[1]
    spec = {'A': specA, 'B': specB, 'C': specC}[which]
    out = build(spec)
    wavfile.write(f'/home/claude/vid/music/track_{which}.wav', SR, out)
    print('ok', which, out.shape[0]/SR)

