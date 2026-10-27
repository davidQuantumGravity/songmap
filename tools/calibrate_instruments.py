"""Measure repeatable source response without changing recordings or per-note dynamics.

Writes one opt-in reference gain per source, plus a diagnostic audit of range, dynamics,
attacks and release tails. Renders stay raw; no per-layer loudness normalization is used.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import gc
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def measure(row):
    import numpy as np
    from songmap.instruments import make,Note
    from songmap.instruments.dsp import SR
    from songmap.instruments.sampler.library import SAMPLES
    voice=make(row['ref']);low,high=row['range'];pitched=row.get('family')!='drum'
    pitches=sorted(set(round(low+(high-low)*q) for q in [.25,.5,.75])) if pitched else [row.get('audition_pitch',60)]
    trials=[]
    for pitch in pitches:
        for vel in [.37,.62,.87]:
            y=voice.render(Note(pitch,vel,.28,seed=317,rr=0))
            if y.ndim==2:y=y.mean(axis=1)
            window=y[:int(SR*.32)];rms=float(np.sqrt(np.mean(window**2))) if len(window) else 0
            peak=float(np.max(abs(y))) if len(y) else 0
            above=np.flatnonzero(abs(y)>max(peak*.1,1e-8))
            trials.append(dict(pitch=pitch,velocity=vel,rms_db=round(20*math.log10(max(rms,1e-12)),3),peak=round(peak,7),
                               attack_ms=round(above[0]/SR*1000,3) if len(above) else None,seconds=round(len(y)/SR,4)))
    mid=[t['rms_db'] for t in trials if t['velocity']==.62];level=float(np.median(mid));peak=max(t['peak'] for t in trials)
    # One constant gain for all registers, layers and velocities. Cap both gain
    # and measured headroom; noisy/quiet outliers are reported rather than boosted arbitrarily.
    gain=max(-18,min(12,-26-level,20*math.log10(.8/max(peak,1e-9)))) if level>-90 else 0
    flags=[]
    for pitch in pitches:
        levels=[t['rms_db'] for t in trials if t['pitch']==pitch]
        if min(levels)<-90:flags.append(f'silent or very quiet at MIDI {pitch}')
        if any(b<a-.5 for a,b in zip(levels,levels[1:])):flags.append(f'non-monotonic measured dynamics at MIDI {pitch}')
    profile={'gain_db':round(gain,4),'reference_rms_db':round(level,3),'measured_peak':round(peak,7),
             'range':[low,high],'reference_velocity':.62,'revision':row.get('revision','native'),'flags':flags}
    SAMPLES._data.clear();gc.collect()
    return row['ref'],profile,trials


def run(only=None,jobs=2):
    import yaml
    from songmap.instruments import REGISTRY,list_presets
    from songmap.instruments.sampler.library import voices
    from songmap.instruments.response import PATH
    rows=[v for v in voices() if v['installed']]
    # Native models/presets are measured too, with the same reference procedure.
    for name,cls in REGISTRY.items():
        family=cls.family
        for ref in [name,*[name+'/'+p for p in list_presets().get(name,[])]]:
            rows.append({'ref':ref,'range':[36,60] if family=='bass' else [48,84], 'family':family})
    rows=[v for v in rows if not only or v['ref'] in only or v.get('name') in only]
    previous=yaml.safe_load(PATH.read_text(encoding='utf-8')) if PATH.is_file() else {'version':1,'method':'fixed gain from three registers and three velocities; target reference RMS -26 dBFS; peak/gain capped','profiles':{}}
    out=ROOT/'.songmap/response';out.mkdir(parents=True,exist_ok=True)
    report_path=out/'measurements.json';report=json.loads(report_path.read_text(encoding='utf-8')) if report_path.is_file() else {}
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        for ref,profile,trials in pool.map(measure,rows):
            previous['profiles'][ref]=profile;report[ref]=trials
            PATH.write_text(yaml.safe_dump(previous,sort_keys=False,allow_unicode=True),encoding='utf-8')
            report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            print(ref,profile['gain_db'],profile['flags'],flush=True)
    print('Measured',len(rows),'programs; total profiles',len(previous['profiles']),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--only',nargs='*');p.add_argument('--jobs',type=int,choices=[1,2],default=2)
    a=p.parse_args();run(a.only,a.jobs)
