"""Prepare, render and compare the SFZ edition without changing the original scores.

Run from the repo root: python tools/sfz_revisit.py --prepare --gallery --render --page
Later renders respect edits to the edition's .sm scores; --prepare never overwrites them.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import html
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
EDITION = ROOT / "songs/sfz_revisited"

# Exact instrumental decisions, not a global search-and-replace policy.
CHOICES = {
    "golden/01_golden_hour_lullaby": {"keys": "grand_piano", "mel": "grand_piano", "gtr": "folk_harp", "flute": "flute"},
    "golden/02_deceptive_light": {"ep": "fm_piano", "lead": "flute"},
    "golden/03_tape_bloom": {"ep": "fm_piano", "keys": "grand_piano", "flute": "flute"},
    "golden/04_andalusian_gold": {"strings": "cello", "vln": "solo_violin"},
    "golden/05_silver_third": {"keys": "grand_piano", "harp": "folk_harp", "horn": "horn"},
    "golden_worlds/01_sideways_sun": {"keys": "fm_piano", "lead": "flute", "bass": "double_bass", "bell": "marimba"},
    "golden_worlds/02_pocket_algebra": {"keys": "grand_piano", "lead": "vibraphone", "gtr": "folk_harp", "bass": "double_bass"},
    "golden_worlds/03_parallax_arcade": {"keys": "fm_piano", "arp": "marimba", "lead": "flute"},
    "golden_worlds/04_two_windows": {"keys": "grand_piano", "lead": "flute", "harp": "folk_harp", "low": "double_bass"},
    "golden_worlds/05_night_orchard": {"keys": "grand_piano", "lead": "flute", "bell": "marimba"},
    "golden_house/01_colour_field": {"keys": "grand_piano"},
    "golden_house/02_two_step_gold": {"epiano": "fm_piano"},
    "golden_house/05_silver_lift": {"keys": "grand_piano"},
    "still_water/01_dusk_on_the_water": {"keys": "grand_piano", "mel": "grand_piano", "harp": "folk_harp", "flute": "flute"},
    "still_water/02_the_slow_tide": {"keys": "grand_piano", "mel": "grand_piano", "harp": "folk_harp"},
    "still_water/05_first_light": {"keys": "grand_piano", "mel": "grand_piano", "harp": "folk_harp", "flute": "flute"},
    "epic/a_comma_higher": {"keys": "grand_piano", "epiano": "fm_piano"},
}
RETAINED = {
    "golden_house/03_escalator": "The synthesized bass, lead and arpeggio are the electronic identity of this piece.",
    "golden_house/04_quasicrystal": "Its organ stabs, shimmer and golden-spectrum pad are deliberate sound design.",
    "still_water/03_deep_water": "Golden-spectrum glass and pads are the musical material; an acoustic substitution would change that purpose.",
    "still_water/04_moon_on_the_water": "The golden-spectrum voices and sustained harmonic layers are intentional; retained for comparison.",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def prepare():
    import numpy as np
    from songmap.arrange.expand import expand
    from songmap.gui.rack import set_voice
    from songmap.gui.mixer import set_mix
    from songmap.instruments import Note, make
    from songmap.instruments.sampler.library import manifest
    from songmap.parse import load
    from songmap.render import held_beats
    records = []
    for key, choices in CHOICES.items():
        source = ROOT / "songs" / (key + ".sm")
        target = EDITION / (key + ".sm")
        arr = expand(load(str(source)))
        text = source.read_text(encoding="utf-8")
        changes = []
        for part, voice in choices.items():
            evs = arr.parts[part]
            native = arr.ensemble.instrument(part)
            sampled = make("sampler/" + voice)
            lo, hi = manifest()["voices"][voice]["range"]
            pitches = [p for e in evs for p in e.pitches]
            if min(pitches) < lo-.5 or max(pitches) > hi+.5:
                raise ValueError(f"{key}/{part}: pitches outside {voice}'s sample range")
            old_energy = new_energy = 0.0
            picks = np.linspace(0, len(evs)-1, min(18, len(evs)), dtype=int)
            for k, idx in enumerate(picks):
                e = evs[idx]
                t = arr.timeline.beat_to_sec(e.beat)
                gate = max(.01, arr.timeline.beat_to_sec(e.beat+held_beats(e))-t)
                n = Note(float(e.pitches[0]), float(e.vel), gate, seed=k+1, rr=k)
                a, b = native.render(n), sampled.render(n)
                cut = int((gate+.25)*48000)
                old_energy += float(np.sum(a[:cut]**2)) / (a.shape[1] if a.ndim == 2 else 1)
                new_energy += float(np.sum(b[:cut]**2)) / (b.shape[1] if b.ndim == 2 else 1)
            adjustment = float(np.clip(10*math.log10(max(old_energy,1e-15)/max(new_energy,1e-15)), -24, 24))
            old_gain = arr.ensemble.mix.get(part, {}).get("gain_db", 0)
            new_gain = round(old_gain + adjustment, 1)
            text = set_voice(text, part, use="sampler/"+voice, clear=True)
            text = set_mix(text, part, gain_db=new_gain)
            changes.append({"part": part, "before": arr.ensemble.voice(part).use, "after": "sampler/"+voice,
                            "gain_db": new_gain, "initial_energy_adjustment_db": round(adjustment, 2)})
        text = (f"# SFZ edition of songs/{key}.sm. Original score and renders preserved.\n"
                "# Instrumentation and faders revised; written notes, tuning, form, timing and binaural settings retained.\n"
                "# Listening candidate: automated measurements are not a human listening verdict.\n" + text)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        updated = expand(load(str(target)))
        updated.ensemble.check(updated.song.parts())
        if arr.digest() != updated.digest():
            raise ValueError(f"note events changed: {key}")
        records.append({"key": key, "title": arr.song.title, "source_sha256": sha(source),
                        "score": target.relative_to(ROOT).as_posix(), "note_digest": arr.digest(),
                        "frames": arr.timeline.frames, "changes": changes})
        print("prepared", key, flush=True)
    dump(EDITION / "edition.json", {"revised": records, "retained": RETAINED})


def render_one(score: Path, out: Path, stems=True):
    from songmap.instruments.sampler.library import SAMPLES
    from songmap.parse import load
    from songmap.render import render, write_outputs
    receipt = out / "score.json"
    if receipt.is_file() and json.loads(receipt.read_text())["sha256"] == sha(score) and (out / "song.mp3").is_file():
        print("current", score.relative_to(ROOT), flush=True)
        return
    print("rendering", score.relative_to(ROOT), flush=True)
    result = render(load(str(score)))
    write_outputs(result, str(out), stems=stems, mp3=True)
    dump(receipt, {"source": score.relative_to(ROOT).as_posix(), "sha256": sha(score)})
    del result
    SAMPLES._data.clear()
    gc.collect()


def gallery():
    from songmap.instruments.sampler.library import voices
    base = ROOT / "songs/sfz_library"
    base.mkdir(parents=True, exist_ok=True)
    base.joinpath("README.md").write_text("# Sampled instrument gallery\n\nFour-bar demonstrations: soft, medium, hard, then a held sixth-step-up note. Percussion uses fixed kit pitches.\nEach instrument has an editable score, WAV/MP3, QA and source credits under renders/. These are instrument tests, not finished songs.\n", encoding="utf-8")
    for v in voices():
        octave = 0
        while 60+12*octave < v["range"][0]:
            octave += 1
        if v["family"] == "bass":
            octave = -2
        if v["name"].startswith("cello"):
            octave = -1
        score = base / (v["name"]+".sm")
        head = f'# {v["title"]}: {v["description"]}\nsong "{v["title"]}" 100 4/4 C fps=30 seed=99 tail=3 tuning=36edo\n'
        if v["family"] == "drum":
            text = head + f'kit kick={v["ref"]}\nsoft 1 | drums:{{kick: "x...o...x...o..."}} dyn=p\nmedium 1 | drums:{{kick: "X...x...X...x..."}} dyn=mf\nhard 1 | drums:{{kick: "X.x.X.x.X.x.X.x."}} dyn=f\nlast 1 | drums:{{kick: "X..............."}} dyn=mp\nmix drums -12\n'
        else:
            text = head + f'inst voice={v["ref"]}\n'
            for name, dyn in [("soft","p"),("medium","mf"),("hard","f")]:
                text += f'{name} 1 | voice:{{deg: "0/4 2 4 r/4", oct: {octave}}} dyn={dyn}\n'
            text += f'sixth 1 | voice:{{deg: "^0/1", oct: {octave}}} dyn=mp\nmix voice -6 hall=.08\n'
        text += 'master standard lufs=-18 glue=none\n'
        score.write_text(text, encoding="utf-8")
        render_one(score, base / "renders" / v["name"], stems=False)


def render_edition(only=None):
    data = json.loads((EDITION / "edition.json").read_text(encoding="utf-8"))
    for entry in data["revised"]:
        key = entry["key"]
        if only and only not in key:
            continue
        source = ROOT / "songs" / (key+".sm")
        if sha(source) != entry["source_sha256"]:
            raise ValueError(f"original source changed since edition prepared: {source}")
        original_render = source.parent / "renders" / source.stem
        # Existing masters are references. Missing baselines are rendered inside the new edition.
        if not (original_render / "song.mp3").is_file():
            original_render = EDITION / Path(key).parent / "renders" / ("before_"+source.stem)
            render_one(source, original_render, stems=False)
        entry["before_render"] = original_render.relative_to(ROOT).as_posix()
        score = ROOT / entry["score"]
        out = score.parent / "renders" / score.stem
        render_one(score, out)
        entry["after_render"] = out.relative_to(ROOT).as_posix()
        entry["score_sha256"] = sha(score)
        entry["qa"] = json.loads((out / "qa.json").read_text())
        entry["review"] = json.loads((out / "review.json").read_text())
        dump(EDITION / "edition.json", data)


def page():
    from songmap.instruments.sampler.library import voices
    data = json.loads((EDITION / "edition.json").read_text(encoding="utf-8"))
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SongMap: sampled instruments and song revisions</title>',
             '<style>body{font:16px/1.55 system-ui;background:#101920;color:#e1eceb;max-width:1050px;margin:0 auto;padding:32px}h1{font-size:32px}h2{font-size:24px;margin-top:40px}article{background:#1a2a32;padding:22px;border-radius:12px;margin:16px 0}a{color:#8bddc1}audio{width:100%;margin:8px 0}button{padding:10px 18px;border:1px solid #70bda7;border-radius:6px;background:#27483f;color:white;cursor:pointer}small{color:#b2c8c8}.row{display:grid;grid-template-columns:1fr 1fr;gap:20px}@media(max-width:650px){.row{grid-template-columns:1fr}body{padding:18px}}</style>',
             '<h1>New instruments, familiar songs</h1><p>Seventeen free sampled voices, followed by seventeen revised songs. Original scores remain intact. The revisions preserve written notes, harmony, tempo, form, microtonal pitches and binaural settings; instrumentation and faders change.</p><p>Use the A/B buttons to switch at the same timestamp. Playback loudness is matched by attenuating the louder master using its measured LUFS. Recorded strings retain their natural vibrato. These are candidates for listening review, not approved improvements.</p><p><a href="../rhythm_palette/index.html">New bass and drum palette</a> · <a href="#comparisons">Jump to song comparisons</a> · <a href="#instruments">Instrument gallery</a> · <a href="README.md">Listening notes and scope</a> · <a href="edition.json">Verification and measurements</a></p><h2 id="instruments">Instrument gallery</h2><div class="row">']
    for v in voices():
        if not (ROOT / "songs/sfz_library/renders" / v["name"] / "song.mp3").is_file():
            continue
        path = "../sfz_library/renders/"+v["name"]+"/song.mp3"
        parts.append(f'<article><b>{html.escape(v["title"])}</b><p>{html.escape(v["description"])}</p><audio controls preload="none" src="{path}"></audio><small>{v["ref"]} · {v["license"]}</small></article>')
    parts.append('</div><h2 id="comparisons">Song comparisons</h2>')
    for e in data["revised"]:
        if "after_render" not in e:
            continue
        before = ROOT / e["before_render"]
        after = ROOT / e["after_render"]
        q0 = json.loads((before / "qa.json").read_text())
        q1 = e["qa"]
        target = min(q0["lufs"], q1["lufs"])
        import os
        a = Path(os.path.relpath(before / "song.mp3", EDITION)).as_posix()
        b = Path(os.path.relpath(after / "song.mp3", EDITION)).as_posix()
        changes = '; '.join(f'{c["part"]}: {c["after"].removeprefix("sampler/")}' for c in e["changes"])
        src = Path(os.path.relpath(ROOT / e["score"], EDITION)).as_posix()
        anchor = "song-"+e["key"].replace("/","-")
        credits = b.removesuffix("song.mp3")+"LICENSES.md"
        parts.append(f'<article id="{anchor}" class="comparison"><small>{html.escape(e["key"].split("/")[0])}</small><h3>{html.escape(e["title"])}</h3><p>{html.escape(changes)}</p><div class="row"><div><button onclick="swap(this,0)">A: original</button><audio controls preload="none" data-gain="{10**((target-q0["lufs"])/20):.6f}" src="{a}"></audio><small>{q0["lufs"]:.1f} LUFS · {q0["true_peak_db"]:.2f} dBTP</small></div><div><button onclick="swap(this,1)">B: samples</button><audio controls preload="none" data-gain="{10**((target-q1["lufs"])/20):.6f}" src="{b}"></audio><small>{q1["lufs"]:.1f} LUFS · {q1["true_peak_db"]:.2f} dBTP · <a href="{src}">editable score</a> · <a href="{credits}">credits</a></small></div></div></article>')
    parts.append('<h2>Reviewed and retained</h2>')
    for key, reason in RETAINED.items():
        parts.append(f'<p><b>{html.escape(key.split("/")[-1])}</b>: {html.escape(reason)}</p>')
    parts.append('''<script>for(const a of document.querySelectorAll('audio')){a.volume=Number(a.dataset.gain||1);a.addEventListener('play',()=>{for(const other of document.querySelectorAll('audio'))if(other!==a)other.pause()})}function swap(button,index){const audios=button.closest('.comparison').querySelectorAll('audio');const src=audios[1-index],dst=audios[index];const t=src.currentTime||dst.currentTime;src.pause();if(dst.readyState>=1){dst.currentTime=t;dst.play()}else{dst.addEventListener('loadedmetadata',()=>{dst.currentTime=Math.min(t,dst.duration);dst.play()},{once:true});dst.load()}}</script></html>''')
    (EDITION / "index.html").write_text("\n".join(parts), encoding="utf-8")


def audit():
    """Check the real outputs against current scores and the frozen originals."""
    import contextlib
    import io
    import soundfile as sf
    from songmap.arrange.expand import expand
    from songmap.cli import main as cli
    from songmap.instruments.sampler.install import verify
    from songmap.export.cues import build as build_cues
    from songmap.listen import listen
    from songmap.parse import load
    data = json.loads((EDITION / "edition.json").read_text(encoding="utf-8"))
    checks = io.StringIO()
    for e in data["revised"]:
        original = ROOT / "songs" / (e["key"]+".sm")
        score = ROOT / e["score"]
        before = ROOT / e["before_render"]
        after = ROOT / e["after_render"]
        a, b = expand(load(str(original))), expand(load(str(score)))
        assert sha(original) == e["source_sha256"], f"original changed: {original}"
        assert a.digest() == b.digest() == e["note_digest"], f"written notes changed: {score}"
        assert a.timeline.frames == b.timeline.frames == e["frames"]
        assert a.song.binaural == b.song.binaural, f"binaural settings changed: {score}"
        def musical_lines(path):
            return [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
                    if line.strip() and not line.lstrip().startswith(("#","inst ","mix "))]
        assert musical_lines(original) == musical_lines(score), f"non-instrument score lines changed: {score}"
        assert json.loads((after / "score.json").read_text())["sha256"] == sha(score), f"stale render: {score}"
        expected_cues = build_cues(a)
        assert expected_cues == build_cues(b) == json.loads((after / "cues.json").read_text())
        historical_cues = json.loads((before / "cues.json").read_text())
        additions = []
        by_name = {s["name"]:s for s in expected_cues["sections"]}
        for section in historical_cues["sections"]:
            if "beats_per_bar" not in section:
                # Older exports predate the per-section meter field. Preserve and compare every timing value.
                section["beats_per_bar"] = by_name[section["name"]]["beats_per_bar"]
                additions.append(f"sections/{section['name']}/beats_per_bar")
        assert historical_cues == expected_cues, f"historical cue timing changed: {score}"
        e["historical_cue_schema_additions"] = additions
        q0, q1 = (json.loads((p / "qa.json").read_text()) for p in (before, after))
        assert q0["render"]["digest"] == q1["render"]["digest"] == e["note_digest"]
        assert q1["clipped_samples"] == 0
        info = sf.info(after / "song.wav")
        assert info.samplerate == 48000 and info.channels == 2 and info.subtype == "PCM_24"
        assert abs(info.frames/48000 - q1["seconds"]) < .001
        assert (after / "qa.png").is_file() and (after / "LICENSES.md").is_file()
        old_findings, new_findings = listen(a).to_dict()["findings"], listen(b).to_dict()["findings"]
        assert old_findings == new_findings, f"new note-level findings: {score}"
        old_report, new_report = listen(a, q0).to_dict(), listen(b, q1).to_dict()
        prior = {(f["kind"],f["where"]) for f in old_report["findings"] if f["severity"] in ("problem","warning")}
        e["new_audio_warnings"] = [f for f in new_report["findings"] if f["severity"] in ("problem","warning")
                                   and f["kind"] in ("balance","contrast","clipping")
                                   and (f["kind"],f["where"]) not in prior]
        for c in e["changes"]:
            assert b.ensemble.voice(c["part"]).use == c["after"]
            c["final_gain_db"] = b.ensemble.mix.get(c["part"],{}).get("gain_db",0)
        e.update(qa=q1, review=new_report, original_review=old_report,
                 score_sha256=sha(score), wav_sha256=sha(after / "song.wav"), mp3_sha256=sha(after / "song.mp3"),
                 written_notes_unchanged=True, frames_unchanged=True, cues_unchanged=True,
                 binaural_settings_unchanged=True, note_findings_unchanged=True)
        with contextlib.redirect_stdout(checks):
            assert cli(["check",str(score)]) == 0
            assert cli(["listen",str(score),"--render",str(after)]) == 0
        print("verified",e["key"],q1["lufs"],"LUFS",q1["true_peak_db"],"dBTP",flush=True)
    installation = verify(ROOT / "samples")
    assert installation["ok"]
    data["validation"] = {"sample_installation": installation, "revised":len(data["revised"]),
                          "retained":len(data["retained"]), "all_written_events_and_cues_preserved":True,
                          "clipped_samples":0, "new_audio_warnings":sum(len(e["new_audio_warnings"]) for e in data["revised"]),
                          "human_auditory_approval":False}
    dump(EDITION / "edition.json",data)
    (EDITION / "checks.txt").write_text(checks.getvalue(),encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    for flag in ("prepare", "gallery", "render", "audit", "page"):
        parser.add_argument("--"+flag, action="store_true")
    parser.add_argument("--only", help="render only song paths containing this text")
    args = parser.parse_args()
    if args.prepare: prepare()
    if args.gallery: gallery()
    if args.render: render_edition(args.only)
    if args.audit: audit()
    if args.page: page()
