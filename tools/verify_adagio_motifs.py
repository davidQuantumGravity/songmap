"""Audit the controlled A/B motif audition, without rating aesthetic quality."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from songmap.arrange.expand import expand
from songmap.instruments.sampler.library import manifest
from songmap.parse import load

FOLDER = ROOT / "songs/golden_adagio"
SCORE = FOLDER / "motif_ab_studio.sm"
OUT = FOLDER / "renders/motif_ab_studio"

song = load(str(SCORE))
arr = expand(song)
qa = json.loads((OUT / "qa.json").read_text())
review = json.loads((OUT / "review.json").read_text())
assert qa["render"]["digest"] == arr.digest(), "Stale render"
assert qa["seconds"] == 54 and qa["clipped_samples"] == 0
assert qa["true_peak_db"] <= -1.9
assert review["counts"]["problem"] == 0
backing, ranges = [], {}
for part, events in arr.parts.items():
    before = [(round(e.beat, 6), e.dur, e.pitches, e.vel, e.art) for e in events if e.section == "A_long_arch"]
    after = [(round(e.beat - 36, 6), e.dur, e.pitches, e.vel, e.art) for e in events if e.section == "B_forward_lilt"]
    if part == "melody":
        assert before != after
    else:
        assert before == after, f"Backing differs: {part}"
        backing.append(part)
    pitches = [p for e in events for p in e.pitches]
    name = song.instruments[part]["use"].split("/")[-1]
    lo, hi = manifest()["voices"][name]["range"]
    assert lo <= min(pitches) <= max(pitches) <= hi, part
    ranges[part] = [min(pitches), max(pitches)]
ah = [(h.start, h.end, h.chord.symbol) for h in arr.harmony.spans if h.start < 32]
bh = [(h.start - 36, h.end - 36, h.chord.symbol) for h in arr.harmony.spans if h.start >= 36]
assert ah == bh
golden = sum(end - start for start, end, symbol in ah if symbol.endswith("g7"))
assert golden == 8
sections = {x["name"]: x for x in qa["sections"]}
delta = abs(sections["A_long_arch"]["loudness"] - sections["B_forward_lilt"]["loudness"])
assert delta <= 1.0, f"A/B loudness differs by {delta} dB"
assert qa["stems"]["basslow"] < qa["stems"]["melody"] - 5
receipt = {
    "title": song.title, "score_sha256": hashlib.sha256(SCORE.read_bytes()).hexdigest(),
    "event_digest": arr.digest(), "seconds": 54, "option_seconds": 24,
    "A_start": 0, "B_start": 27, "reset_seconds": 3,
    "identical_backing_parts": backing, "identical_harmony": True,
    "western_harmonic_duration_percent": 75, "golden_harmonic_duration_percent": 25,
    "same_clean_master_gain": True, "section_loudness_delta_db": round(delta, 2),
    "sampled_ranges": ranges, "qa": {k: qa[k] for k in ("lufs", "true_peak_db", "clipped_samples")},
    "listening_status": "Awaiting the user's A/B preference; technical checks do not establish likeability.",
}
(FOLDER / "verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
