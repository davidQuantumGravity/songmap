"""Verify and package the authored Golden Cathedral score; no new synthesis/DSP.

The comparison renders reuse SongMap's existing binaural renderer and exported
stems. All versions use the full mix's clean-master gain. Run after songmap render.
"""
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
from songmap.render import held_beats
from songmap.theory.keys import parse_key
from songmap.visual.score import spell

COLLECTION = ROOT / "songs/golden_cathedral"
SCORE = COLLECTION / "as_above_so_below.sm"
OUT = COLLECTION / "renders/as_above_so_below"
SR = 48000


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def peak(x, target):
    """Measure the actual pure-pair audio, independently of the frequency plan."""
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x)), 8 * len(x)))
    freq = np.fft.rfftfreq(8 * len(x), 1 / SR)
    window = np.flatnonzero(abs(freq - target) < .35)
    return float(freq[window[np.argmax(spectrum[window])]])


def main():
    song = load(str(SCORE))
    arr = expand(song)
    tl = arr.timeline
    plan = bn.plan(song, tl)
    report = json.loads((OUT / "qa.json").read_text())
    assert tl.seconds == 300 and tl.total_bars == 72
    assert report["render"]["digest"] == arr.digest(), "Render is stale"
    assert report["clipped_samples"] == 0 and report["true_peak_db"] <= -1.9
    sections, outside, rubs, close = [], [], [], []
    named_notes = []
    for section, span, state in zip(song.sections, tl.sections, plan.states):
        tonic, scale = parse_key(section.key or song.key)
        allowed = {round(3 * (tonic + x)) % 36 for x in scale}
        events = [(part, e) for part, ee in arr.parts.items() for e in ee if e.section == section.name]
        flat = sorted((e.beat, e.beat + held_beats(e), float(p), part) for part, e in events for p in e.pitches)
        for start, end, pitch, part in flat:
            if round(pitch * 3) % 36 not in allowed:
                outside.append((section.name, part, pitch))
        harmony = arr.harmony.chord_at(span.start)
        chord_pcs = {round(3 * (harmony.root + x)) % 36 for x in harmony.intervals}
        assert chord_pcs <= allowed, section.name
        if "maj9" in harmony.symbol:
            assert [round(x * 3) for x in harmony.intervals] == [0, 11, 22, 33, 44]
        for carrier in state.carriers:
            pitch = 69 + 12 * math.log2(carrier.hz / 440)
            assert round(pitch * 3) % 36 in chord_pcs, (section.name, carrier.label)
            # At least one note in the section spells the corresponding upper octave.
            assert any(round(p - pitch, 6) in (12, 24) for _, e in events for p in e.pitches), (section.name, carrier.label)
        for i, (start, end, p, part) in enumerate(flat):
            for start2, end2, p2, part2 in flat[i + 1:]:
                if start2 >= end:
                    break
                overlap = min(end, end2) - start2
                steps = round(abs(p - p2) * 3) % 36
                if overlap >= .25 and steps in (1, 2, 34, 35):
                    rubs.append((section.name, part, part2, start2))
                if overlap >= .5 and .2 < abs(p - p2) <= 1.01:
                    close.append({"section": section.name, "time": tl.beat_to_sec(start2),
                                  "parts": [part, part2], "notes": [spell(p).text, spell(p2).text], "beats": overlap})
        sections.append({"name": section.name.replace("_", " ").title(), "id": section.name,
                         "start": state.t0, "end": state.t1, "key": section.key or song.key,
                         "symbol": harmony.symbol, "root": spell(60 + harmony.root).text[:-1],
                         "quality": "Golden ninth" if "maj9" in harmony.symbol else "Golden seventh" if "g7" in harmony.symbol else "Golden triad",
                         "carriers": [{"label": c.label, "hz": c.hz} for c in state.carriers],
                         "beat": list(state.beat)})
    assert not outside and not rubs
    assert len(close) == 1 and close[0]["section"] == "invocation", close
    # The one close suspension is prepared by unison, then resolves at the next bar.
    library = manifest()["voices"]
    sampled = {}
    for part in ("tenor", "alto", "cantus"):
        voice = song.instruments[part]["use"].split("/")[-1]
        pitches = [p for e in arr.parts[part] for p in e.pitches]
        bounds = library[voice]["range"]
        assert min(pitches) >= bounds[0] and max(pitches) <= bounds[1], (part, bounds)
        sampled[part] = {"voice": voice, "midi_range": [min(pitches), max(pitches)], "sample_range": bounds}
    for part, events in play(arr).items():
        for e in events:
            if e.pitches:
                named_notes.append({"part": part, "start": tl.beat_to_sec(e.beat),
                                    "end": tl.beat_to_sec(e.beat + held_beats(e)),
                                    "names": [spell(p).text for p in e.pitches]})
    # Sum exported pre-master stems; the binaural difference stem includes the
    # notches as well as the positive pure-tone layer, and is NOT a solo-pairs file.
    stems = sorted((OUT / "stems").glob("*.wav"))
    music = np.zeros((round(tl.seconds * SR), 2))
    for path in stems:
        if path.stem != "binaural":
            sr, data = wavfile.read(path)
            assert sr == SR and data.shape == music.shape
            music += data
    sr, difference = wavfile.read(OUT / "stems/binaural.wav")
    full = music + difference
    gain = 10 ** (song.master.ceiling_db / 20) / (np.max(np.abs(full)) + 1e-12)
    sr, written = read_wav(str(OUT / "song.wav"))
    assert np.max(abs(written - full * gain)) < 1e-6, "Stems do not reconstruct the delivered mix"
    del written, difference, full
    pairs = bn.render_layer(plan, tl, len(music), music, SR)
    assert abs(lufs(pairs) - lufs(music) - plan.level_db) < .06
    measured = []
    for section_id, begin in (("first_ninth", 84), ("empyrean", 244)):
        state = next(s for s in plan.states if s.name == section_id)
        segment = pairs[begin * SR:(begin + 4) * SR]
        for c, rate in zip(state.carriers, plan.rates(state)):
            for channel, sign in ((0, -1), (1, 1)):
                expected = c.hz + sign * rate / 2
                actual = peak(segment[:, channel], expected)
                assert abs(actual - expected) < .05, (section_id, c.label, actual, expected)
                measured.append({"section": section_id, "carrier": c.label, "ear": "left" if channel == 0 else "right",
                                 "expected_hz": round(expected, 5), "measured_hz": round(actual, 5)})
    versions = {}
    for name, data in (("music_only", music), ("binaural_pairs", pairs)):
        data *= gain
        assert true_peak_db(data) < -.1, f"Comparison would clip: {name}"
        write_wav24(str(OUT / f"{name}.wav"), data)
        write_mp3(str(OUT / f"{name}.mp3"), str(OUT / f"{name}.wav"), joint_stereo=False)
        versions[name] = {"seconds": len(data) / SR, "lufs": round(lufs(data), 2), "same_master_gain": True}
    del music, pairs
    oscillators = []
    for hz, amp, mul, _ in bn._oscillators(plan, tl.seconds):
        oscillators.append({"hz": hz, "label": spell(69 + 12 * math.log2(hz / 440)).text,
                            "amp": [x.tolist() for x in amp], "mul": [x.tolist() for x in mul]})
    beat_curve = bn._ramped(plan.states, lambda s: s.beat, plan.glide, True)
    page_data = {"sections": sections, "notes": named_notes, "oscillators": oscillators,
                 "beat_curve": [x.tolist() for x in bn._curve(beat_curve, log=True)]}
    (COLLECTION / "performance.json").write_text(json.dumps(page_data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    receipt = {"title": song.title, "seconds": tl.seconds, "bars": tl.total_bars, "tuning": song.tuning,
               "score_sha256": sha(SCORE), "audio_sha256": sha(OUT / "song.wav"), "event_digest": arr.digest(),
               "outside_scale": outside, "microtonal_rubs": rubs, "prepared_close_suspension": close,
               "carrier_chord_membership": True, "carriers_have_upper_octave_sources_in_each_section": True,
               "golden_ninth_steps": [0, 11, 22, 33, 44], "sampled_ranges": sampled,
               "pair_frequency_measurements": measured, "comparison_renders": versions,
               "pair_relative_lufs": plan.level_db, "master_gain_db": round(20 * math.log10(gain), 4),
               "qa": {k: report[k] for k in ("seconds", "lufs", "true_peak_db", "clipped_samples")},
               "intentional_advisories": ["The 32-second golden-vault/empyrean span is one broad climax, with a final crest rather than a separate jump.",
                                          "The still point is intentionally bass-heavy: most of the upper ensemble falls silent."],
               "listening_status": "Automated and visual checks only; awaiting human listening review."}
    (COLLECTION / "verification.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Verified {len(named_notes)} performed events, {len(sections)} harmonic states, {len(measured)} measured ear frequencies; wrote comparisons and player data.")


if __name__ == "__main__":
    main()
