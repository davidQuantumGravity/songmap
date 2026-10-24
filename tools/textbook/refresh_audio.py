"""Prepare explicit sampled editions and audit the textbook's complete media inventory.

python tools/textbook/refresh_audio.py --prepare
python tools/textbook/build.py --jobs 3
python tools/textbook/refresh_audio.py --audit --package

Original musical scores remain available. Teaching YAML is edited only in its
instrument and mix mappings; the manifest pins the unchanged note-event digest.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlsplit
import zipfile

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
MANIFEST = ROOT / "textbook/audio_refresh.json"
SITE = ROOT / "textbook_site"

# These examples compare engineered spectra, fusion, organ/choir sound, processing,
# or an exact quoted score. Replacing their tone would change the lesson.
PROTECTED = {
    "ch14/fusion", "ch15/antiphony", "ch17/melody_contrast",
    "ch26/timbre_flip", "ch30/transplant", "ch30/counterpoint", "ch30/antiphony",
    "ch31/asymmetry", "ch31/visitation", "ch32/bend_modulation",
    "ch42/organum", "ch42/fauxbourdon", "ch43/first_song",
    "ch46/stability_order", "ch48/layer_revealed", "ch48/bliss_chord",
    "ch49/beating_chord", "ch50/distortion_ab", "ch51/modal_note_comparison",
    "ch48/moon_on_the_water", "ch49/escalator", "ch49/quasicrystal",
}
PROTECTED_SUITE = {
    "P08a_golden_seventh_shimmer_definition", "P11a_golden_breathing_and_the_timbre_flip_definition",
    "P15a_golden_beats_definition", "P06a_light_and_shade_definition",
    "P07a_metallic_means_definition", "P12a_layer_prism_definition",
    "P13a_rational_visitation_definition",
}
FULL_SONGS = {
    "ch47/golden_hour_lullaby": "golden/01_golden_hour_lullaby",
    "ch47/deceptive_light": "golden/02_deceptive_light",
    "ch47/tape_bloom": "golden/03_tape_bloom",
    "ch47/andalusian_gold": "golden/04_andalusian_gold",
    "ch47/silver_third": "golden/05_silver_third",
    "ch48/dusk_on_the_water": "still_water/01_dusk_on_the_water",
    "ch48/the_slow_tide": "still_water/02_the_slow_tide",
    "ch48/first_light": "still_water/05_first_light",
    "ch49/colour_field": "golden_house/01_colour_field",
    "ch49/two_step_gold": "golden_house/02_two_step_gold",
    "ch49/silver_lift": "golden_house/05_silver_lift",
    **{"ch51/" + n: "golden_worlds/" + n for n in (
        "01_sideways_sun", "02_pocket_algebra", "03_parallax_arcade", "04_two_windows", "05_night_orchard")},
}
EPIC_MOVEMENTS = {"ch50/m1_door", "ch50/m2_blue_gold", "ch50/m3_decatonic", "ch50/m4_thirteen_steps"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rel(path):
    return Path(path).relative_to(ROOT).as_posix()


def replace_mapping(text, key, value):
    """Replace just one top-level YAML field; preserve the rest verbatim."""
    node = yaml.compose(text)
    for kn, vn in node.value:
        if kn.value == key:
            dumped = yaml.safe_dump({key: value}, sort_keys=False, allow_unicode=True, width=130).rstrip()
            def content_end(n):
                if isinstance(n, yaml.MappingNode) and not n.flow_style and n.value:
                    return content_end(n.value[-1][1])
                if isinstance(n, yaml.SequenceNode) and not n.flow_style and n.value:
                    return content_end(n.value[-1])
                return n.end_mark.index
            end = content_end(vn)
            # Block mapping nodes end at the next field's start; scalar/flow nodes
            # stop before the newline. Preserve comments after a flow mapping.
            suffix = text[end:]
            if not suffix.startswith(("\n", "\r", " #", "  #")):
                dumped += "\n"
            return text[:kn.start_mark.index] + dumped + suffix
    return text.rstrip() + "\n\n" + yaml.safe_dump({key: value}, sort_keys=False, allow_unicode=True, width=130)


def choose_voice(ref, part, pitches, gates):
    from songmap.instruments.sampler.library import manifest
    if ref.startswith("sampler/") or not pitches:
        return None
    candidates = []
    if ref in ("clean/keys", "keys/still", "keys/v0", "keys"):
        candidates = ["grand_piano"]
    elif ref.startswith("epiano"):
        candidates = ["fm_piano", "grand_piano"]
    elif ref.startswith("string_pluck") or part in ("harp", "guitar", "gtr", "pluck") and ref.startswith("pluck"):
        candidates = ["folk_harp", "grand_piano"]
    elif ref == "clean/lead":
        candidates = ["flute", "grand_piano"]
    elif ref == "clean/bass":
        # The bowed/synthetic sustain remains when a long bass pedal is the point.
        if max(gates) <= 2.5:
            candidates = ["double_bass", "grand_piano"]
    elif ref == "clean/organ":
        candidates = ["grand_piano"]
    for voice in candidates:
        low, high = manifest()["voices"][voice]["range"]
        if min(pitches) >= low - .49 and max(pitches) <= high + .49:
            return voice
    return None


def balance(arr, part, voice):
    from songmap.instruments import Note, make
    from songmap.render import held_beats
    old, new = arr.ensemble.instrument(part), make("sampler/" + voice)
    events = arr.parts[part]
    old_energy = new_energy = 0.0
    for k, idx in enumerate(np.linspace(0, len(events) - 1, min(12, len(events)), dtype=int)):
        e = events[idx]
        gate = max(.01, arr.timeline.beat_to_sec(e.beat + held_beats(e)) - arr.timeline.beat_to_sec(e.beat))
        for pitch in e.pitches[:3]:
            note = Note(float(pitch), float(e.vel), gate, seed=k + 1, rr=k)
            for instrument, which in ((old, 0), (new, 1)):
                x = instrument.render(note)[:int((gate + .2) * 48000)]
                energy = float(np.sum(x * x)) / (x.shape[1] if x.ndim == 2 else 1)
                if which:
                    new_energy += energy
                else:
                    old_energy += energy
    adjustment = float(np.clip(10 * math.log10(max(old_energy, 1e-15) / max(new_energy, 1e-15)), -24, 24))
    return round(float(arr.ensemble.mix.get(part, {}).get("gain_db", 0)) + adjustment, 1)


def revise(source, target, identity, kind):
    from songmap.arrange.expand import expand
    from songmap.parse import load
    from songmap.render import held_beats
    from songmap.gui.rack import set_voice
    from songmap.gui.mixer import set_mix
    from songmap.instruments.sampler.library import SAMPLES
    text = source.read_text(encoding="utf-8")
    original = sha(source)
    arr = expand(load(str(source)))
    changes = []
    reason = "Engineered spectrum, synthesis/processing, choir/fusion comparison, exact-tone control, or quoted source score."
    protected = identity in PROTECTED or kind == "suite" and identity in PROTECTED_SUITE
    # Whole-song editions already have measured balances and deliberate palettes.
    full = ROOT / "songs/sfz_revisited" / (FULL_SONGS.get(identity, "missing") + ".sm")
    if full.is_file() and not protected:
        edition = load(str(full))
        if arr.digest() != expand(edition).digest():
            raise ValueError(f"full-song edition changes notes: {identity}")
        before = yaml.safe_load(text)
        before["instruments"], before["mix"] = edition.instruments, edition.mix
        for part in arr.parts:
            after = expand(edition).ensemble.voice(part).use if not arr.ensemble.is_kit(part) else "kit"
            if after.startswith("sampler/"):
                changes.append({"part": part, "before": arr.ensemble.voice(part).use, "after": after,
                                "gain_db": edition.mix.get(part, {}).get("gain_db", 0)})
        text = replace_mapping(text, "instruments", before["instruments"])
        text = replace_mapping(text, "mix", before["mix"])
        reason = "Uses the previously balanced SFZ song edition."
    elif not protected:
        data = yaml.safe_load(text) if source.name.endswith(".yaml") else None
        instruments = dict((data or {}).get("instruments") or {})
        mix = dict((data or {}).get("mix") or {})
        for part, events in arr.parts.items():
            if arr.ensemble.is_kit(part) or not events:
                continue
            old = arr.ensemble.voice(part)
            if part in ("drone", "pedal"):
                continue
            if identity.startswith("ch49/") and not old.use.startswith(("keys", "epiano", "clean/keys")):
                continue
            if identity in EPIC_MOVEMENTS and part not in ("keys", "epiano"):
                continue
            # Golden partials and deliberately edited spectra remain engineered.
            if old.params.get("spectrum", 0) or old.use in ("clean/glass", "clean/golden_pad", "clean/sine"):
                continue
            pitches = [p for e in events for p in e.pitches]
            gates = [arr.timeline.beat_to_sec(e.beat + held_beats(e)) - arr.timeline.beat_to_sec(e.beat) for e in events]
            voice = choose_voice(old.use, part, pitches, gates)
            if not voice:
                continue
            gain = balance(arr, part, voice)
            ref = "sampler/" + voice
            changes.append({"part": part, "before": old.use, "after": ref, "gain_db": gain})
            if data is not None:
                instruments[part] = ref
                mix[part] = {**mix.get(part, {}), "gain_db": gain}
            else:
                text = set_voice(text, part, use=ref, clear=True)
                text = set_mix(text, part, gain_db=gain)
        if data is not None and changes:
            text = replace_mapping(text, "instruments", instruments)
            text = replace_mapping(text, "mix", mix)
        reason = "Sampled musical voices; engineered golden spectra, electronic patches and long pedals retained."
    if changes:
        backup = ROOT / "build/textbook_originals" / rel(source)
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(source, backup)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        updated = expand(load(str(target)))
        if arr.digest() != updated.digest() or arr.timeline.frames != updated.timeline.frames:
            raise ValueError(f"instrument refresh changed score events: {identity}")
    record = {"id": identity, "kind": kind, "source": rel(source), "playback_source": rel(target if changes else source),
              "status": "updated" if changes else "retained", "reason": reason,
              "original_sha256": original, "sha256": sha(target if changes else source),
              "note_digest": arr.digest(), "frames": arr.timeline.frames, "changes": changes}
    SAMPLES._data.clear()
    gc.collect()
    return record


def prepare():
    if MANIFEST.exists():
        print("Manifest exists; checking existing decisions. Remove it only to plan a new edition.")
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for r in data["records"]:
            if sha(ROOT / r["playback_source"]) != r["sha256"]:
                raise ValueError("source changed since preparation: " + r["playback_source"])
        return
    import songbook
    from sfz_revisit import CHOICES, RETAINED
    partial = MANIFEST.with_suffix(".partial.json")
    records = json.loads(partial.read_text(encoding="utf-8"))["records"] if partial.exists() else []
    completed = {(r["kind"], r["id"]) for r in records}
    def checkpoint():
        save(partial, {"edition": "sampled-2026-10", "records": records})
    refs = set()
    for page in sorted((ROOT / "textbook/content").glob("*.html")):
        text = page.read_text(encoding="utf-8")
        refs.update(re.findall(r'<audio-ref[^>]*file="([^"]+)"', text))
        for name in re.findall(r'<audio-ex[^>]*src="([^"]+)"', text):
            identity = page.stem + "/" + name
            if ("chapter", identity) in completed:
                continue
            base = ROOT / "textbook/audio" / identity
            source = Path(str(base) + ".songmap.yaml")
            if source.exists():
                records.append(revise(source, source, identity, "chapter"))
            else:
                source = Path(str(base) + ".py")
                records.append({"id": identity, "kind": "chapter", "source": rel(source), "playback_source": rel(source),
                                "status": "retained", "reason": "Exact-frequency, waveform, spectrum or physics demonstration.",
                                "original_sha256": sha(source), "sha256": sha(source), "changes": []})
            print(records[-1]["status"], identity, flush=True)
            checkpoint()
    for filename in sorted(refs):
        name = filename.removesuffix(".mp3")
        if ("suite", name) in completed:
            continue
        source = ROOT / "examples/golden/suite" / (name + ".songmap.yaml")
        if source.is_file():
            target = ROOT / "textbook/audio/suite" / source.name
            records.append(revise(source, target, name, "suite"))
        else:
            source = ROOT / "golden_audio" / filename
            records.append({"id": name, "kind": "suite", "source": rel(source), "playback_source": rel(source),
                            "status": "retained", "reason": "Exact-ratio reference recording.",
                            "original_sha256": sha(source), "sha256": sha(source), "changes": []})
        print(records[-1]["status"], name, flush=True)
        checkpoint()
    # Take inventory before generating new scores, so a rerun has a stable scope.
    sources = [Path(p) for c in songbook.collections() for p in c["songs"]]
    for source in sources:
        if "/textbook_refresh/" in rel(source):
            continue
        key = rel(source).removeprefix("songs/").removesuffix(".sm")
        if ("songbook", key) in completed:
            continue
        if key in CHOICES:
            target = ROOT / "songs/sfz_revisited" / (key + ".sm")
            from songmap.arrange.expand import expand
            from songmap.parse import load
            a, b = expand(load(str(source))), expand(load(str(target)))
            assert a.digest() == b.digest()
            records.append({"id": key, "kind": "songbook", "source": rel(source), "playback_source": rel(target),
                            "status": "updated", "reason": "Previously balanced SFZ edition; original score retained.",
                            "original_sha256": sha(source), "sha256": sha(target), "note_digest": a.digest(),
                            "frames": a.timeline.frames, "changes": []})
        elif "/v1/" in rel(source) or key in RETAINED or "/sfz_" in rel(source):
            records.append({"id": key, "kind": "songbook", "source": rel(source), "playback_source": rel(source),
                            "status": "retained", "reason": "Historical archive, sampled edition/audition, or intentional synthesis.",
                            "original_sha256": sha(source), "sha256": sha(source), "changes": []})
        else:
            folder = "skill_examples" if rel(source).startswith(".claude/") else source.parent.name
            target = ROOT / "songs/textbook_refresh" / folder / source.name
            records.append(revise(source, target, key, "songbook"))
        print(records[-1]["status"], key, flush=True)
        checkpoint()
    readme = ROOT / "songs/textbook_refresh/README.md"
    readme.parent.mkdir(parents=True, exist_ok=True)
    readme.write_text("# Textbook sampled editions\n\nInstrument and balance updates for the worked examples and evaluation songs. Written notes, timing and original scores are preserved. See `textbook/audio_refresh.json` for exact decisions.\n", encoding="utf-8")
    save(MANIFEST, {"edition": "sampled-2026-10", "records": records})
    partial.unlink(missing_ok=True)
    print("prepared", len(records), "decisions", flush=True)


def audit():
    from songmap.arrange.expand import expand
    from songmap.parse import load
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    from audio_editions import audio_engine_hash
    from stage import wanted
    errors = []
    for r in data["records"]:
        source = ROOT / r["playback_source"]
        if r["source"] != r["playback_source"] and sha(ROOT / r["source"]) != r["original_sha256"]:
            errors.append("original source changed: " + r["source"])
        if sha(source) != r["sha256"]:
            errors.append("stale source: " + rel(source))
        if r.get("note_digest"):
            a = expand(load(str(source)))
            if a.digest() != r["note_digest"] or a.timeline.frames != r["frames"]:
                errors.append("changed musical events: " + r["id"])
    # Resolve every local HTML reference, including posters, scripts, downloads,
    # Songbook media and the duplicate players in the generated audio index.
    missing, media = [], set()
    for page in SITE.rglob("*.html"):
        if not wanted(page.relative_to(SITE).as_posix()):
            continue
        text = page.read_text(encoding="utf-8")
        for url in re.findall(r'(?:src|href|poster)="([^"]+)"', text):
            u = urlsplit(url)
            if u.scheme or u.netloc or not u.path or u.path.startswith("/"):
                continue
            target = (page.parent / unquote(u.path)).resolve()
            if not target.exists():
                missing.append(rel(page) + ": " + url)
            if target.suffix in (".mp3", ".mp4"):
                media.add(target)
    oversized = [rel(p) for p in SITE.rglob("*") if p.is_file()
                 and wanted(p.relative_to(SITE).as_posix()) and p.stat().st_size > 25 * 1024 * 1024]
    errors += missing + ["over 25 MiB: " + x for x in oversized]
    qa = []
    for p in sorted(set(SITE.rglob("*.qa.json")) | set((SITE / "audio/songbook").rglob("qa.json"))):
        q = json.loads(p.read_text())
        qa.append({"file": rel(p), "clipped_samples": q.get("clipped_samples"), "true_peak_db": q.get("true_peak_db")})
        if q.get("clipped_samples", 0):
            errors.append("clipped audio: " + rel(p))
    for r in data["records"]:
        if r["kind"] == "chapter":
            mp3 = SITE / "audio" / (r["id"] + ".mp3")
            if not mp3.is_file():
                errors.append("missing chapter audio: " + r["id"])
            if r["playback_source"].endswith(".songmap.yaml") and not mp3.with_suffix(".qa.json").is_file():
                errors.append("missing chapter QA: " + r["id"])
            if r["playback_source"].endswith(".songmap.yaml") and mp3.with_suffix(".qa.json").is_file():
                q = json.loads(mp3.with_suffix(".qa.json").read_text())
                if q.get("source_sha256") != r["sha256"] or q.get("audio_engine_hash") != audio_engine_hash():
                    errors.append("stale chapter render: " + r["id"])
        elif r["kind"] == "suite":
            mp3 = SITE / "audio/suite" / (r["id"] + ".mp3")
            if not mp3.is_file():
                errors.append("missing suite audio: " + r["id"])
            elif r["status"] == "updated":
                qp = mp3.with_suffix(".qa.json")
                q = json.loads(qp.read_text()) if qp.exists() else {}
                if q.get("source_sha256") != r["sha256"] or q.get("audio_engine_hash") != audio_engine_hash():
                    errors.append("stale suite render: " + r["id"])
            elif sha(mp3) != r["sha256"] and r["playback_source"].endswith(".mp3"):
                errors.append("changed exact-ratio reference: " + r["id"])
    def probe(path):
        if not path.exists():
            return {"file": rel(path), "error": "missing"}
        run = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                             capture_output=True, text=True, encoding="utf-8")
        if run.returncode:
            return {"file": rel(path), "error": run.stderr[:300]}
        meta = json.loads(run.stdout)
        types = [s["codec_type"] for s in meta["streams"]]
        duration = float(meta.get("format", {}).get("duration", 0))
        error = None
        if "audio" not in types or path.suffix == ".mp4" and "video" not in types or duration <= 0:
            error = "missing playable stream or duration"
        if path.suffix == ".mp4":
            qp = (SITE / "audio" / path.relative_to(SITE / "video")).with_suffix(".qa.json")
        else:
            qp = path.with_suffix(".qa.json")
            if not qp.exists() and path.name == "song.mp3":
                qp = path.with_name("qa.json")
        if qp.exists():
            seconds = json.loads(qp.read_text()).get("seconds", duration)
            if abs(seconds - duration) > .2:
                error = f"duration {duration:.3f} differs from rendered {seconds:.3f}"
        return {"file": rel(path), "seconds": duration, "streams": types, "error": error}
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as pool:
        probes = list(pool.map(probe, sorted(media)))
    errors += [p["file"] + ": " + p["error"] for p in probes if p["error"]]
    save(ROOT / "build/textbook_refresh_media.json", {"media": probes})
    result = {"decisions": len(data["records"]), "updated": sum(r["status"] == "updated" for r in data["records"]),
              "retained": sum(r["status"] == "retained" for r in data["records"]),
              "referenced_media": len(media), "playable_media": sum(not p["error"] for p in probes),
              "qa_reports": len(qa), "clipped_samples": sum(q["clipped_samples"] or 0 for q in qa),
              "missing_links": missing, "oversized": oversized, "errors": errors, "human_auditory_approval": False}
    save(ROOT / "build/textbook_refresh_verification.json", result)
    print(json.dumps(result, indent=2))
    if errors:
        raise SystemExit(1)


def package():
    from stage import wanted
    dest = ROOT / "build/website_ready/music_theory_of_golden_harmony"
    files = [p for p in SITE.rglob("*") if p.is_file() and wanted(p.relative_to(SITE).as_posix())]
    for p in files:
        target = dest / p.relative_to(SITE)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
    receipt = {"files": len(files), "bytes": sum(p.stat().st_size for p in files),
               "source": str(SITE), "prepared_folder": str(dest), "live_deployment": False}
    save(ROOT / "build/website_ready/receipt.json", receipt)
    # Store media uncompressed; MP3/MP4/JPEG already are compressed.
    archive = ROOT / "build/website_ready/music_theory_of_golden_harmony.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as z:
        for p in files:
            z.write(p, "music_theory_of_golden_harmony/" + p.relative_to(SITE).as_posix())
    print(json.dumps({**receipt, "archive": str(archive)}, indent=2))


def main():
    # Both tools live under tools/; do not require an editable installation.
    sys.path.insert(0, str(ROOT / "tools"))
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prepare", action="store_true")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--package", action="store_true")
    args = ap.parse_args()
    if args.prepare:
        prepare()
    if args.audit:
        audit()
    if args.package:
        if not args.audit:
            audit()
        package()


if __name__ == "__main__":
    main()
