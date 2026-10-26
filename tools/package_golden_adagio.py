"""Audit and package Beyond the Veil with the existing SongMap audio renderer."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from songmap.arrange.expand import expand
from songmap.export.qa import lufs, true_peak_db
from songmap.export.wav import read_wav, write_mp3, write_wav24
from songmap.instruments.sampler.library import manifest
from songmap.mix import binaural as bn
from songmap.parse import load
from songmap.perform.play import play
from songmap.render import held_beats, render, write_outputs
from songmap.visual.score import spell

COLLECTION = ROOT / "songs/golden_adagio"
SCORE = COLLECTION / "beyond_the_veil.sm"
OUT = COLLECTION / "renders/beyond_the_veil"
SR = 48000


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def peak(x, target):
    size = 16 * len(x)
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x)), size))
    freq = np.fft.rfftfreq(size, 1 / SR)
    indices = np.flatnonzero(abs(freq - target) < .35)
    return float(freq[indices[np.argmax(spectrum[indices])]])


def main():
    song = load(str(SCORE))
    rendered = None
    if "--render" in sys.argv:
        rendered = render(song, log=print)
        write_outputs(rendered, str(OUT), stems=False, mp3=True)
    arr = expand(song)
    tl = arr.timeline
    plan = bn.plan(song, tl)
    report = json.loads((OUT / "qa.json").read_text())
    composition = json.loads((COLLECTION / "composition.json").read_text())
    assert tl.seconds == 300 and tl.total_bars == 96
    assert report["render"]["digest"] == arr.digest(), "Stale render"
    assert report["render"]["binaural"] == plan.summary, "Stale binaural render"
    assert plan.octaves == 5
    assert all(abs(rate * 32 - carrier.hz) < 1e-10 for state in plan.states
               for carrier, rate in zip(state.carriers, plan.rates(state)))
    assert report["clipped_samples"] == 0 and report["true_peak_db"] <= -1.9
    assert sum(s["kind"] == "golden" for s in composition) == 24
    sections, rubs, close, named_notes = [], [], [], []
    for section, span, state, authored in zip(song.sections, tl.sections, plan.states, composition):
        harmony = arr.harmony.chord_at(span.start)
        pcs = {round(3 * (harmony.root + x)) % 36 for x in harmony.intervals}
        events = [(part, e) for part, ee in arr.parts.items() for e in ee if e.section == section.name]
        sounded = {round(3 * p) % 36 for _, e in events for p in e.pitches}
        for carrier in state.carriers:
            midi = 69 + 12 * math.log2(carrier.hz / 440)
            assert round(midi * 3) % 36 in pcs & sounded, (section.name, carrier.label)
        if authored["kind"] == "golden":
            expected = [0, 11, 22, 33, 44] if "maj9" in harmony.symbol else [0, 11, 22, 33]
            assert [round(x * 3) for x in harmony.intervals] == expected
        else:
            assert all(abs(x - round(x)) < 1e-8 for x in (harmony.root, *harmony.intervals))
        flat = sorted((e.beat, e.beat + held_beats(e), float(p), part) for part, e in events for p in e.pitches)
        for i, (start, end, pitch, part) in enumerate(flat):
            for start2, end2, pitch2, part2 in flat[i + 1:]:
                if start2 >= end:
                    break
                overlap = min(end, end2) - start2
                steps = round(abs(pitch - pitch2) * 3) % 36
                if overlap >= .25 and steps in (1, 2, 34, 35):
                    rubs.append([section.name, part, part2, start2])
                if overlap >= .5 and .2 < abs(pitch - pitch2) <= 1.01:
                    close.append({"section": section.name, "time": tl.beat_to_sec(start2),
                                  "parts": [part, part2], "notes": [spell(pitch).text, spell(pitch2).text], "beats": overlap})
        quality = ("Golden ninth" if "maj9" in harmony.symbol else "Golden seventh") if authored["kind"] == "golden" else "Western " + ("ninth" if "9" in harmony.symbol else "seventh")
        sections.append({**authored, "name": authored["title"], "symbol": harmony.symbol, "quality": quality,
                         "root": spell(60 + harmony.root).text[:-1],
                         "carriers": [{"label": c.label, "hz": c.hz} for c in state.carriers], "beat": list(state.beat)})
    assert not rubs, rubs
    library = manifest()["voices"]
    sampled = {}
    for part, spec in song.instruments.items():
        if not spec["use"].startswith("sampler/"):
            continue
        voice = spec["use"].split("/")[-1]
        pitches = [p for e in arr.parts[part] for p in e.pitches]
        bounds = library[voice]["range"]
        assert min(pitches) >= bounds[0] and max(pitches) <= bounds[1], (part, bounds)
        sampled[part] = {"voice": voice, "midi_range": [min(pitches), max(pitches)], "sample_range": bounds}
    # The chosen B is the opening, compared as authored pitch/rhythm events.
    audition = expand(load(str(COLLECTION / "motif_ab_studio.sm")))
    chosen = [e for e in audition.parts["melody"] if e.section == "B_forward_lilt"]
    opening = [e for e in arr.parts["melody"] if e.beat < 32]
    def signature(events, offset):
        return [(round(e.beat - offset, 6), round(e.dur, 6), tuple(e.pitches)) for e in events]
    assert signature(chosen, 36) == signature(opening, 0), "Chosen B melody changed"
    for part, events in play(arr).items():
        for e in events:
            if e.pitches:
                named_notes.append({"part": part, "start": tl.beat_to_sec(e.beat), "end": tl.beat_to_sec(e.beat + held_beats(e)), "names": [spell(p).text for p in e.pitches]})
    music = np.zeros((round(tl.seconds * SR), 2))
    if rendered is not None:
        for name, values in rendered.stems.items():
            if name != "binaural":
                music += values
        difference = rendered.stems["binaural"]
        del rendered
    else:
        for path in sorted((OUT / "stems").glob("*.wav")):
            if path.stem != "binaural":
                sr, values = wavfile.read(path)
                assert sr == SR and values.shape == music.shape
                music += values
        sr, difference = wavfile.read(OUT / "stems/binaural.wav")
    full = music + difference
    gain = 10 ** (song.master.ceiling_db / 20) / (np.max(np.abs(full)) + 1e-12)
    sr, written = read_wav(str(OUT / "song.wav"))
    assert np.max(abs(written - full * gain)) < 1e-6, "Delivered mix does not match stems"
    del written, difference, full
    pairs = bn.render_layer(plan, tl, len(music), music, SR)
    assert abs(lufs(pairs) - lufs(music) - plan.level_db) < .06
    measured = []
    # Short steady windows avoid the 0.28-second chord-change crossfades.
    for section_id in ("p20_1", "p22_3"):
        state = next(s for s in plan.states if s.name == section_id)
        begin = state.t0 + .6
        segment = pairs[round(begin * SR):round((begin + 1.9) * SR)]
        for c, rate in zip(state.carriers, plan.rates(state)):
            for channel, sign in ((0, -1), (1, 1)):
                expected = c.hz + sign * rate / 2
                actual = peak(segment[:, channel], expected)
                assert abs(actual - expected) < .09, (section_id, c.label, actual, expected)
                measured.append({"section": section_id, "ear": "left" if channel == 0 else "right",
                                 "center_hz": round(c.hz, 5), "expected_hz": round(expected, 5), "measured_hz": round(actual, 5)})
    versions = {}
    for name, values in (("music_only", music), ("binaural_pairs", pairs)):
        values *= gain
        assert true_peak_db(values) < -.1, f"Comparison clips: {name}"
        write_wav24(str(OUT / f"{name}.wav"), values)
        write_mp3(str(OUT / f"{name}.mp3"), str(OUT / f"{name}.wav"), joint_stereo=False)
        versions[name] = {"seconds": len(values) / SR, "lufs": round(lufs(values), 2), "same_master_gain": True}
    del music, pairs
    oscillators = [{"hz": hz, "label": spell(69 + 12 * math.log2(hz / 440)).text,
                    "amp": [x.tolist() for x in amp], "mul": [x.tolist() for x in mul]}
                   for hz, amp, mul, _ in bn._oscillators(plan, tl.seconds)]
    beat_curve = bn._ramped(plan.states, lambda s: s.beat, plan.glide, True)
    page_data = {"sections": sections, "notes": named_notes, "oscillators": oscillators,
                 "rate_mode": "octave", "octaves": plan.octaves, "rate_divisor": 2 ** plan.octaves,
                 "beat_curve": [x.tolist() for x in bn._curve(beat_curve, log=True)]}
    (COLLECTION / "performance.json").write_text(json.dumps(page_data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    receipt = {"title": song.title, "seconds": tl.seconds, "bars": tl.total_bars, "tuning": song.tuning,
               "score_sha256": sha(SCORE), "audio_sha256": sha(OUT / "song.wav"), "event_digest": arr.digest(),
               "chosen_motif": "B - Forward Lilt", "opening_matches_chosen_B": True,
               "harmonic_duration": {"western_bars": 72, "golden_bars": 24, "western_percent": 75, "golden_percent": 25},
               "microtonal_rubs": rubs, "close_semitone_voicings": close,
               "carrier_chord_and_scored_pitch_class_membership": True,
               "carrier_register_note": "Octave-folded chord tones; a center may be above the lowest bass fundamental, in its harmonic octave class.",
               "golden_ninth_steps": [0, 11, 22, 33, 44], "sampled_ranges": sampled,
               "pair_frequency_measurements": measured, "comparison_renders": versions,
               "pair_relative_lufs": plan.level_db, "master_gain_db": round(20 * math.log10(gain), 4),
               "rate_mode": "octave", "beat_octaves": plan.octaves, "octave_rate_ratios_verified": True,
               "difference_range_hz": [min(r for s in plan.states for r in plan.rates(s)), max(r for s in plan.states for r in plan.rates(s))],
               "qa": {k: report[k] for k in ("seconds", "lufs", "true_peak_db", "clipped_samples")},
               "listening_status": "User selected motif B. The complete arrangement awaits human listening review; technical QA is not a listening judgment."}
    (COLLECTION / "full_verification.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Verified {len(named_notes)} performed events, 96 harmonic states, chosen B, 75/25 harmony, {len(measured)} measured ear frequencies.")


if __name__ == "__main__":
    main()
