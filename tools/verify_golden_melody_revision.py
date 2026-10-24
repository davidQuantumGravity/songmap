"""Audit the Golden Worlds melody revision against the archived listening drafts.

Checks the actual scores, renders, backing events and sample ranges. It does not
rate aesthetic quality, or rewrite scores/audio to satisfy a numerical target.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from songmap.arrange.expand import expand
from songmap.instruments.sampler.library import manifest
from songmap.listen import listen
from songmap.parse import load
from songmap.render import held_beats
from songmap.theory.keys import parse_key
from songmap.visual.score import spell

SCORES = ROOT / "songs/golden_worlds"
ARCHIVE = ROOT / "archives/golden_worlds/v1_before_melody_rewrite"
BACKING = {
    "01_sideways_sun": {"keys": set(), "bass": set(), "drums": set(), "pad": set(),
                        "bell": {"streetlights", "held_breath"}},
    "02_pocket_algebra": {"bass": set(), "drums": set(), "gtr": {"head_right", "answer_back"},
                          "keys": {"trading_keys"}},
    "03_parallax_arcade": {"keys": set(), "arp": set(), "bass": set(), "drums": set(), "pad": set()},
    "04_two_windows": {"harp": {"different_shadow"}, "low": set()},
    "05_night_orchard": {"pad": set(), "bell": set(), "low": set()},
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def melody(events):
    events = sorted((e for e in events if len(e.pitches) == 1), key=lambda e: e.beat)
    ps = np.array([e.pitches[0] for e in events])
    jumps = [abs(b.pitches[0]-a.pitches[0]) for a,b in zip(events,events[1:])
             if a.section == b.section and b.beat-(a.beat+a.dur) < 1]
    return {"notes": len(events), "range": [spell(min(ps)).text,spell(max(ps)).text],
            "midi_range": [round(float(min(ps)),4),round(float(max(ps)),4)],
            "span_semitones": round(float(np.ptp(ps)),3),
            "notes_at_or_above_C6": int(np.sum(ps>=84)),
            "median_successive_interval_semitones": round(float(np.median(jumps)),3),
            "sounding_beats": round(sum(held_beats(e) for e in events),3)}


def verify():
    reports = []
    for path in sorted(SCORES.glob("*.sm")):
        song = load(str(path)); arr = expand(song)
        original = expand(load(str(ARCHIVE/path.name)))
        out = SCORES/"renders"/path.stem
        qa = json.loads((out/"qa.json").read_text())
        old_qa = json.loads((ARCHIVE/(path.stem+".qa.json")).read_text())
        assert qa["render"]["digest"] == arr.digest(), f"stale render: {path.name}"
        assert 180 <= arr.timeline.seconds <= 240
        assert arr.timeline.seconds == original.timeline.seconds
        assert qa["clipped_samples"] == 0 and qa["true_peak_db"] <= -.9
        preserved = []
        for part,exclude in BACKING[path.stem].items():
            before = [e.key() for e in original.parts[part] if e.section not in exclude]
            after = [e.key() for e in arr.parts[part] if e.section not in exclude]
            assert before == after, f"backing changed: {path.stem}/{part}"
            preserved.append(part)
        assert [(h.start,h.end,h.chord) for h in arr.harmony.spans] == [
            (h.start,h.end,h.chord) for h in original.harmony.spans], "harmony changed"
        notes = []
        sampled = {}
        for part,events in arr.parts.items():
            if arr.ensemble.is_kit(part):
                continue
            use = arr.ensemble.voice(part).use
            ps = [p for e in events for p in e.pitches]
            if use.startswith("sampler/"):
                voice = use.removeprefix("sampler/")
                lo,hi = manifest()["voices"][voice]["range"]
                assert min(ps) >= lo and max(ps) <= hi, (part,use,min(ps),max(ps))
                sampled[part] = use
            for e in events:
                sec = next(s for s in song.sections if s.name == e.section)
                root,scale = parse_key(sec.key or song.key)
                pool = {round(3*(root+x))%36 for x in scale}
                for p in e.pitches:
                    assert round(p*3)%36 in pool, (path.name,part,e.section,p)
                    notes.append((e.beat,e.beat+held_beats(e),p,part))
        notes.sort(); rubs=[]
        for i,(a,b,p,part) in enumerate(notes):
            for c,d,q,other in notes[i+1:]:
                if c>=b:
                    break
                if min(b,d)-c >= .25-1e-8 and round(abs(p-q)*3)%36 in (1,2,34,35):
                    rubs.append((c,part,other))
        assert not rubs, (path.name,rubs[:5])
        for h in arr.harmony.spans:
            if not h.chord:
                continue
            sec = next(s for s in song.sections if s.name==arr.timeline.section_at(h.start).name)
            root,scale=parse_key(sec.key or song.key)
            pool={round(3*(root+x))%36 for x in scale}
            assert all(round(3*(h.chord.root+x))%36 in pool for x in h.chord.intervals)
        review=listen(arr,qa)
        assert review.counts()["problem"] == 0
        assert not any(f.kind in ("clash","repetition","dynamics","clipping") for f in review.findings)
        new_mel=melody(arr.parts['lead']); old_mel=melody(original.parts['lead'])
        assert new_mel['notes_at_or_above_C6']==0 and new_mel['span_semitones']<=12
        change=round(qa['stems']['lead']-old_qa['stems']['lead'],2)
        assert change <= -5, (path.name,'lead has not become quieter',change)
        with wave.open(str(out/'song.wav')) as w:
            fmt=dict(sample_rate=w.getframerate(),channels=w.getnchannels(),sample_width_bytes=w.getsampwidth(),
                     frames=w.getnframes(),seconds=w.getnframes()/w.getframerate())
        assert fmt['sample_rate']==48000 and fmt['channels']==2 and fmt['sample_width_bytes']==3
        report={"file":path.name,"title":song.title,"revision":2,"score_sha256":sha(path),
                "event_digest":arr.digest(),"mp3_sha256":sha(out/'song.mp3'),"bars":arr.timeline.total_bars,
                "duration_seconds":arr.timeline.seconds,"wav_format":fmt,"lufs":qa['lufs'],
                "true_peak_db":qa['true_peak_db'],"clipped_samples":qa['clipped_samples'],
                "sampled_voices":sampled,"preserved_backing_parts":preserved,"harmony_and_timing_unchanged":True,
                "original_lead":old_mel,"revised_lead":new_mel,"lead_stem_change_db":change,
                "golden_pitch_audit":{"off_scale_notes":0,"off_scale_chords":0,"microtonal_rubs_at_least_quarter_beat":0},
                "review_counts":review.counts(),"review_findings":review.to_dict()['findings'],
                "sections":[dict(name=s.name,seconds=round(arr.timeline.beat_to_sec(s.start),3),
                     key=next(x for x in song.sections if x.name==s.name).key or song.key) for s in arr.timeline.sections]}
        reports.append(report)
        print(path.stem,new_mel['range'],'lead change',change,'dB;',review.counts(),flush=True)
    receipt={"date":"2026-10-23","collection":"Golden Worlds","revision":2,"tuning":"36edo",
        "scope":"All composed pitches and chord tones belong to the local golden collection; unpitched kit voices excluded.",
        "listening_status":"Melodies rewritten after the user's rework verdict. New listening review pending; measurements do not establish aesthetic quality.",
        "original_archive":"archives/golden_worlds/v1_before_melody_rewrite",
        "checks":["score parsing and expansion","unchanged bass, harmony, groove and accompaniment events",
                  "actual sample ranges","local pitch and chord membership","sustained sixth-step rubs",
                  "render digest matches score","zero clipped samples","24-bit stereo 48 kHz WAV",
                  "lead range, phrasing and measured level against the original render"],
        "accepted_findings":{
            "register":"Flute/short electric-piano comping, low mallets/plucked replies, and atmospheric harp/pad deliberately share registers. Rests, timbre and stereo placement separate their roles. Retaining the liked backing and avoiding shrill octaves takes priority over blanket octave separation.",
            "range":"Pocket Algebra's vibraphone uses F3 (MIDI 53), inside its published 53-89 sample range. The generic lead-role warning assumes a minimum of MIDI 55.",
            "contrast":"The groove pieces keep related sections near one another in level; no added lead boost is used merely to satisfy a single-peak loudness rule.",
            "balance":"Parallax's marimba sits below the drums by design; its melody and the organ remain comparable in stem level."},
        "tracks":reports}
    (SCORES/'verification.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return receipt


if __name__ == '__main__':
    verify()
