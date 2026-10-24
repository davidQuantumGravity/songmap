"""Verify Chapter 51's score claims and the actual encoded media; never renders or changes music."""
from pathlib import Path
import hashlib
import json
import math
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from songmap.arrange.expand import expand
from songmap.parse import load
from songmap.parse.fmt import song_to_raw
from songmap.theory.keys import parse_key
from songmap.visual.view import load as load_view, resolve as resolve_view


def collection(key):
    tonic, scale = parse_key(key)
    return {round(3 * (tonic + x)) % 36 for x in scale}


def played(arr, name, part=None):
    span = next(s for s in arr.timeline.sections if s.name == name)
    return {round(p * 3) % 36 for key, evs in arr.parts.items()
            if not arr.ensemble.is_kit(key) and (part is None or key == part)
            for e in evs if span.start <= e.beat < span.end for p in e.pitches}


def verify():
    songs = ROOT / "songs/golden_worlds"
    sources = ROOT / "textbook/audio/ch51"
    videos = ROOT / "textbook_site/video/ch51"
    arrays, receipts = {}, []
    for source in sorted(sources.glob("*.songmap.yaml")):
        arr = expand(load(str(source)))
        name = source.name.removesuffix(".songmap.yaml")
        canonical = songs / (name + ".sm")
        if canonical.is_file():
            assert song_to_raw(load(str(canonical))) == song_to_raw(load(str(source))), f"chapter score differs: {name}"
            original = expand(load(str(canonical)))
            assert original.digest() == arr.digest(), f"score translation differs: {name}"
            arrays[name] = arr
        path = videos / (name + ".mp4")
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                               check=True, capture_output=True, text=True)
        data = json.loads(probe.stdout)
        v = next(s for s in data["streams"] if s["codec_type"] == "video")
        a = next(s for s in data["streams"] if s["codec_type"] == "audio")
        assert v["codec_name"] == "h264" and a["codec_name"] == "aac"
        size = resolve_view(load_view(str(source)))["size"]
        assert [v["width"], v["height"]] == size
        assert v["r_frame_rate"] == "30/1" and a["channels"] == 2 and a["sample_rate"] == "48000"
        assert abs(float(data["format"]["duration"]) - arr.timeline.seconds) < .1
        assert abs(int(v["nb_frames"]) - math.ceil(arr.timeline.seconds * 30)) <= 1
        assert (videos / (name + ".jpg")).is_file()
        receipt = {"name": name, "source": str(source.relative_to(ROOT)).replace("\\", "/"),
                   "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "event_digest": arr.digest(),
                   "canonical_score_identical": canonical.is_file(), "video": str(path.relative_to(ROOT)).replace("\\", "/"),
                   "seconds": float(data["format"]["duration"]), "frames": int(v["nb_frames"]),
                   "fps": 30, "size": size, "audio": "AAC stereo 48000 Hz"}
        visual = sources / (name + ".video.json")
        if canonical.is_file():
            visual_receipt = json.loads(visual.read_text())
            assert visual_receipt["video_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
            assert visual_receipt["view_sha256"] == hashlib.sha256(source.with_suffix(".view.yaml").read_bytes()).hexdigest()
            receipt["visual_revision"] = visual_receipt["visual_revision"]
            receipt["audio_reused_without_changes"] = visual_receipt["audio_reused_without_changes"]
        receipts.append(receipt)
        print(name, receipt["seconds"], "seconds,",receipt["frames"],"frames; video/audio verified", flush=True)

    f53, f54 = collection("F golden10_63"), collection("F golden10_54")
    assert f53 - f54 == {9} and f54 - f53 == {7}             # Eb -> ^D
    pocket = arrays["02_pocket_algebra"]
    assert 9 in played(pocket,"head_left","lead") and 7 in played(pocket,"limma_room","lead")
    d7, d35 = collection("D golden7_42"), collection("D golden10_36")
    assert len(d7 & d35) == 6 and len(d7-d35) == 1 and len(d35-d7) == 4
    assert not (d35 & collection("^D golden10_36"))
    chamber = arrays["04_two_windows"]
    pa = {(x+21)%36 for x in (0,6,14,22,28)}
    pb = {(x+21)%36 for x in (3,11,17,25,33)}
    assert played(chamber,"first_window","lead") <= pa
    assert played(chamber,"second_window","keys") <= pb
    assert not (pa & pb) and pa | pb == collection("G golden10_36")
    assert not ({(27+x)%36 for x in (0,11,22)} <= collection("A golden7_15"))
    assert arrays["05_night_orchard"].timeline.total_bars == 64
    report = {"date": "2026-10-23", "chapter": "ch51", "musical_revision": 2, "videos": receipts,
              "score_claims_verified": ["F 6|3 to 5|4 replaces Eb by ^D; both defining pitches occur in the revised lead passages",
                    "D 4|2 to 35 retains six pitch classes, removes one, adds four",
                    "D and ^D 35 decatonic sets are disjoint",
                    "Two Windows opening subjects use complementary pentatonics",
                    "A 1|5 omits the tonic golden triad", "Night Orchard has 64 bars"],
              "checks": "Current score, audio, backing-event and instrument-range audit: songs/golden_worlds/verification.json. Encoded streams, timing and current chapter score equality checked here."}
    (sources / "verification.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report


if __name__ == "__main__":
    verify()
