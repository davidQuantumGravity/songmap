"""Hand-wired demo (from the v1 sketch): notation -> performance -> instruments -> mix -> master -> QA.

    python tools/demo.py      # writes out/demo.wav, out/gallery.wav, prints QA JSON

Everything is wired by hand for 8 bars so each layer is easy to see; `songmap render` does the
same from a song map. `gallery()` plays every registered instrument at p, mf and ff.
"""
import json
import zlib
import os
import time

import numpy as np
from scipy.io import wavfile

from types import SimpleNamespace

import songmap.instruments as I
from songmap.export import qa as _qa
from songmap.instruments.dsp import SR, svf  # noqa: F401
from songmap.mix import bus as _bus
from songmap.mix import fx as _fx
from songmap.mix import master as _master
from songmap.parse import notes as _notes
from songmap.parse import steps as _steps
from songmap.perform import pipeline as _perform
from songmap.theory import harmony as _harmony
from songmap.theory import voicing as _voicing

# the sketch's module names, now spread over the package
M = SimpleNamespace(Bus=_bus.Bus, sidechain_env=_fx.sidechain_env, reverb_ir=_fx.reverb_ir, convolve=_fx.convolve,
                    compressor=_fx.compressor, master=_master.master, qa=_qa.qa)
N = SimpleNamespace(Ev=_notes.Ev, parse_steps=_steps.parse_steps, parse_motif=_notes.parse_motif,
                    parse_chord=_harmony.parse_chord)
P = SimpleNamespace(Feel=_perform.Feel, perform=_perform.perform, voice_lead=_voicing.voice_lead)

TEMPO, BPB = 100, 4                  # 100 BPM @ 30 fps = 18 frames per beat
SPB = 60 / TEMPO
KEY = "A minor"
CHORDS = ["Am", "F", "C", "G", "Am", "F", "Dm7", "E7"]   # one per bar
BARS = len(CHORDS)
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")


def place(bus, inst, played, gain=1.0, pan=0.0):
    for p in played:
        bus.add(p.time, inst.render(p.note), gain, pan)


def main():
    t0 = time.time()
    length = BARS * BPB * SPB + 4
    drums, bass, keys, pad, gtr, lead = (M.Bus(length, n) for n in ("drums", "bass", "keys", "pad", "gtr", "lead"))
    kit = {"kick": I.make("kick", tune=50, decay=0.5), "snare": I.make("snare"),
           "hat": I.make("hat"), "ohat": I.make("hat", decay=0.35)}

    # --- drums: step strings, light swing, humanized; section builds mp -> f
    pat = {"kick":  "X.....x...x.....|X.....x...x...x.",
           "snare": "....X..o....X...|....X..o....X.oo",
           "hat":   "x-x-x-x-x-x-x-x-|x-x-x-x-x-x-x-r-",
           "ohat":  "................|..............x."}
    kick_times = []
    for name, steps in pat.items():
        evs, nb = N.parse_steps(steps, BPB, name)
        for rep in range(BARS // nb):
            feel = P.Feel(swing=0.56, swing_grid=0.25, time_ms=4, drift_ms=3, vel_sd=0.04,
                          offset_ms=6 if name == "snare" else 0, seed=zlib.crc32(f"{name}{rep}".encode()))
            played = P.perform(evs, start_beat=rep * nb * BPB, spb=SPB, feel=feel,
                               section_shape="p<f", section_beats=BARS * BPB, section_start=0)
            place(drums, kit[name], played, {"kick": 0.55, "snare": 0.8, "hat": 0.5, "ohat": 0.35}[name],
                  {"hat": 0.25, "ohat": 0.25}.get(name, 0.0))
            if name == "kick":
                kick_times += [p.time for p in played]

    # --- bass: chord roots, 8ths with an octave bounce, slurred pickups glide
    bass_inst = I.make("bass", cutoff=500, env_amt=2.5, glide=0.05)
    for bar, ch in enumerate(CHORDS):
        root = N.parse_chord(ch)[0]
        r = 33 + (root - 9) % 12              # roots around A1
        motif = f"=mf {root_tok(r)}8 {root_tok(r)} {root_tok(r + 12)}' {root_tok(r)} r {root_tok(r)} {root_tok(r + 7)}~ {root_tok(r + 12)}"
        evs = N.parse_motif(motif, octave=1, name=f"bass{bar}")
        place(bass, bass_inst, P.perform(evs, start_beat=bar * BPB, spb=SPB, mono=True,
                                         section_shape="mp<f", section_beats=BARS * BPB,
                                         feel=P.Feel(time_ms=3, vel_sd=0.03, seed=bar)), 0.3)

    # --- pad: voice-led chords
    pad_inst = I.make("pad", cutoff=1400, attack=0.6, release=1.2)
    prev = None
    for bar, ch in enumerate(CHORDS):
        root, ivs, _ = N.parse_chord(ch)
        prev = P.voice_lead(prev, root, ivs, 52, 74)
        for m in prev:
            pad.add(bar * BPB * SPB, pad_inst.render(I.Note(m, 0.5, BPB * SPB * 0.98, seed=bar * 7 + m)), 0.18)

    # --- guitar-ish arpeggio (Karplus-Strong) on chord tones, 16ths, high-loud shaping
    gtr_inst = I.make("string_pluck", t60=2.0, pick_pos=0.18)
    for bar, ch in enumerate(CHORDS):
        root, ivs, _ = N.parse_chord(ch)
        tones = [57 + (root - 9) % 12 + i for i in ivs[:3]]
        order = [0, 1, 2, 1, 0 + 12, 2, 1, 2] * 2
        evs = [N.Ev(i * 0.25, 0.5, ((tones[o % 12] if o < 12 else tones[0] + 12),), 0.55) for i, o in enumerate(order)]
        place(gtr, gtr_inst, P.perform(evs, start_beat=bar * BPB, spb=SPB,
                                       feel=P.Feel(swing=0.56, swing_grid=0.25, time_ms=5, vel_sd=0.05,
                                                   high_loud=0.6, seed=100 + bar)), 0.6, -0.35)

    # --- melody on modal piano: dynamics, hairpin, accents, staccato, slurs, ghost note
    melody = ("=mp e4_ c8 d e4 a | c4. b8 a4 r | =mp < e4 g8 a b4 c+^ | d+2~ c+4 r "
              "| =f e+4^ d+8' c+' b4 a | g4. a8 b4 (g8) e | =mf > f4 e8 d c4 b- | e2. r4 =p")
    evs = N.parse_motif(melody, octave=4, name="melody")
    keys_inst = I.make("keys", hardness=0.55)
    place(keys, keys_inst, P.perform(evs, start_beat=0, spb=SPB,
                                     feel=P.Feel(time_ms=7, drift_ms=6, vel_sd=0.03, high_loud=0.4, arch=0.6, seed=7)), 1.15, 0.1)

    # --- mix: sidechain, sends, buses
    n = len(drums.x)
    sc = M.sidechain_env(kick_times, n, depth=0.5, release=0.15)
    bass.x *= sc[:, None]
    pad.x *= sc[:, None]
    hall = M.reverb_ir(2.4, predelay=0.02, damping=0.6)
    room = M.reverb_ir(0.8, predelay=0.005, damping=0.3, seed=2)
    wet = M.convolve(pad.x * 0.5 + keys.x * 0.35 + gtr.x * 0.3, hall) * 0.35 + M.convolve(drums.x * 0.2, room) * 0.25
    drums_bus = M.compressor(drums.x, threshold_db=-16, ratio=3, attack=0.008, release=0.12, makeup_db=2)
    mixdown = drums_bus + bass.x + pad.x + keys.x + gtr.x + wet
    song = M.master(mixdown, target_lufs=-14)

    os.makedirs(OUT, exist_ok=True)
    wavfile.write(os.path.join(OUT, "demo.wav"), SR, song.astype(np.float32))
    sections = [("build", 0.0, 4 * BPB * SPB), ("peak", 4 * BPB * SPB, 8 * BPB * SPB)]
    print(json.dumps(M.qa(song, sections), indent=1))
    print(f"rendered {len(song) / SR:.1f}s of audio in {time.time() - t0:.1f}s")
    gallery()


def root_tok(m: int) -> str:
    """MIDI -> letter token relative to octave 1 (e.g. 33 -> a, 45 -> a+)."""
    names = ["c", "c#", "d", "eb", "e", "f", "f#", "g", "ab", "a", "bb", "b"]
    o = m // 12 - 2
    return names[m % 12] + ("+" * o if o > 0 else "-" * -o)


def gallery():
    """Every instrument at three velocities (p, mf, ff): audition timbre-vs-velocity."""
    seq = []
    for name in I.REGISTRY:
        inst = I.make(name)
        pitch = 36 if name == "bass" else 48 if name in ("pad", "organ") else 60
        for v in (0.3, 0.62, 1.0):
            gate = 2.0 if name == "riser" else 0.6
            y = inst.render(I.Note(pitch, v, gate, seed=int(v * 10)))
            y = y if y.ndim == 2 else np.stack([y, y], 1)
            seq += [y * 0.5, np.zeros((int(0.25 * SR), 2))]
        seq.append(np.zeros((int(0.5 * SR), 2)))
    g = np.concatenate(seq)
    g /= np.max(np.abs(g)) * 1.12
    wavfile.write(os.path.join(OUT, "gallery.wav"), SR, g.astype(np.float32))
    print("gallery order:", ", ".join(I.REGISTRY), "(each at p / mf / ff)")


if __name__ == "__main__":
    main()
