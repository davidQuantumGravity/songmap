"""Prepare controlled ensemble auditions, render authored scores and build a listening gallery.

The shared phrases are timbre benchmarks, not bulk compositions. --prepare preserves the
six hand-authored templates. Run from the repo root after songmap samples install.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import gc
import hashlib
import html
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
COLLECTION=ROOT/'songs/ensemble_palette'
BASE={'solo_violin':'Solo violin','violins':'Violin section','cello':'Cello section',
      'double_bass':'Double bass','double_bass_arco':'Double bass','flute':'Flute','horn':'French horn',
      'violins_spiccato':'Violin section','cello_spiccato':'Cello section','marimba':'Marimba','folk_harp':'Folk harp','vibraphone':'Vibraphone'}
ROOTS={'Solo violin':67,'Violin section':67,'Viola section':60,'Cello section':48,'Double bass':36,
       'Flute':67,'Piccolo':79,'Oboe':65,'Clarinet':60,'Bassoon':48,'French horn':60,
       'Trumpet':65,'Tenor trombone':48,'Tuba':36,'Tenor saxophone':60,'Saxello':67,
       'Soprano saxophone':67,'Alto saxophone':60,'Baritone saxophone':48,'Timpani':43,
       'Glockenspiel':72,'Tubular bells':60,'Xylophone':60,'Gong':60}
TEMPLATES=[('01_string_conversation','String conversation','Independent string voices; solo lead with recorded sections below.'),
 ('02_woodwind_replies','Woodwind replies','Flute, oboe, clarinet and bassoon exchange questions with written breaths.'),
 ('03_brass_quintet','Five brass voices','Two trumpets, French horn, trombone and tuba; real muted trumpet answers.'),
 ('04_jazz_quintet','Quintet after the rain','Tenor and Harmon-muted trumpet over piano, upright bass and restrained ride.'),
 ('05_sax_quartet','Four reeds','Actual soprano, alto, tenor and baritone sax recordings with independent parts.'),
 ('06_orchestral_handoff','Orchestral handoff','Melody moves through woodwinds, strings and brass; harp and timpani punctuate.')]


def pitch(n):
    return ['C','C#','D','Eb','E','F','F#','G','Ab','A','Bb','B'][n%12]+str(n//12-1)


def prepare():
    from songmap.instruments.sampler.library import manifest
    from songmap.instruments.sound import library
    voices=manifest()['voices'];rows=[]
    names=[n for n,v in voices.items() if n in BASE or v.get('category','').startswith(('Orchestral','Jazz'))]
    def score(n,use,title,group,description,instrument,lo,hi,params=''):
        root=ROOTS.get(instrument,60)
        root=max(lo,min(root,hi-7)) if instrument!='Gong' else lo
        offset={0:0,2:1,4:2,5:3,7:4,9:5,11:6}[root%12]
        notes=[offset+i for i in (0,2,4,1)] if instrument!='Gong' else [offset]*4
        octv=(root-60)//12
        a,b,c,d=notes
        chord='F' if root%12==5 else 'C'
        source=f'''# Controlled timbre benchmark: {title}.
# Notes: a rising question, descending reply and two detached repeated attacks; all variants of this instrument share these notes.
# Expression: soft beginning, firmer short notes, one held final note and a breath. This repeated benchmark is not a finished composition.
song "{title}" 100 4/4 C seed=211 tail=2 mood=balanced
inst voice={use}{params}
chords {chord}:2
question 1 | voice:{{deg: "=p {a}/4_ {b}/8 {c}/8 {d}/4 r/4", oct: {octv}}}
answer 1 | voice:{{deg: "=mf {b}/8'^ r/8 {b}/8' r/8 =p {a}/4_ r/4", oct: {octv}}}
mix voice -6 hall=.025
master standard lufs=-18 glue=none
'''
        target=COLLECTION/'auditions'/(n+'.sm');target.parent.mkdir(parents=True,exist_ok=True);target.write_text(source,encoding='utf-8')
        rows.append(dict(id=n,use=use,title=title,group=group,description=description,benchmark=instrument,source=target.relative_to(COLLECTION).as_posix()))
    for n in names:
        v=voices[n];inst=v.get('instrument') or BASE.get(n,v['title'])
        score(n,'sampler/'+n,v['title'],v.get('category','Core recordings'),v['description'],inst,*v['range'])
    for n,v in library().items():
        source_names=[s['use'].split('/')[1] for s in v['sources'].values()]
        first=source_names[0];inst=voices[first].get('instrument') or BASE[first]
        lo=max(voices[s]['range'][0] for s in source_names);hi=min(voices[s]['range'][1] for s in source_names)
        score(n,'sound/'+n,v['title'],'Continuous palettes',v['description'],inst,lo,hi,'(morph_x=.35, morph_y=.3)' if len(source_names)==4 else '(blend=.45)')
    for n,title,description in TEMPLATES:
        rows.append(dict(id=n,title=title,group='Authored ensemble starters',description=description,benchmark=None,source='templates/'+n+'.sm'))
    (COLLECTION/'palette.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
    return rows


def render_one(row):
    from songmap.parse.lang import load
    from songmap.arrange.expand import expand
    from songmap.listen import listen
    from songmap.render import render,write_outputs
    from songmap.instruments.sampler.library import SAMPLES
    source=COLLECTION/row['source'];song=load(str(source));arr=expand(song);arr.ensemble.check(song.parts())
    result=render(song);write_outputs(result,str(COLLECTION/'renders'/row['id']),mp3=True,stems=row['benchmark'] is None)
    if row['benchmark'] is not None:
        from songmap.export.wav import write_float
        # A common post-fader, pre-master signal. Never normalize sources independently:
        # the playground must use the same source balance as the saved engine recipe.
        write_float(str(COLLECTION/'renders'/row['id']/'source.wav'),result.stems['voice'])
    record=dict(source=row['source'],source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),digest=arr.digest(),listen=listen(arr).counts())
    SAMPLES._data.clear();del result,arr;gc.collect()
    return record


def render_all(rows,jobs):
    receipt=COLLECTION/'render_receipt.json'
    previous={r['source']:r for r in json.loads(receipt.read_text(encoding='utf-8'))} if receipt.is_file() else {}
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        for row,record in zip(rows,pool.map(render_one,rows)):
            previous[row['source']]=record;receipt.write_text(json.dumps(list(previous.values()),indent=2)+'\n',encoding='utf-8')
            print('rendered',row['id'],record['listen'],flush=True)


def gallery(rows):
    from songmap.instruments.sound import library
    cards=[]
    for r in rows:
        src=r['source'];url='http://127.0.0.1:8867/?song=songs%2Fensemble_palette%2F'+src.replace('/','%2F')
        cards.append(f'''<article data-group="{html.escape(r['group'])}"><h3>{html.escape(r['title'])}</h3><p>{html.escape(r['description'])}</p><audio controls preload="none" src="renders/{r['id']}/song.mp3"></audio><p><a href="{src}">Editable score</a> · <a href="{url}">Open in Studio</a> · <a href="renders/{r['id']}/LICENSES.md">Credits</a> · <a href="renders/{r['id']}/qa.png">Audio QA</a></p></article>''')
    page=(Path(__file__).with_name('ensemble_gallery.html')).read_text(encoding='utf-8')
    data=json.dumps({'rows':rows,'palettes':library()},ensure_ascii=False).replace('<','\\u003c')
    page=page.replace('<!-- CARDS -->','\n'.join(cards)).replace('/* DATA */',data)
    (COLLECTION/'index.html').write_text(page,encoding='utf-8')


def audit(rows):
    receipts={r['source']:r for r in json.loads((COLLECTION/'render_receipt.json').read_text(encoding='utf-8'))};errors=[];clipped=0;findings={}
    for r in rows:
        if receipts.get(r['source'],{}).get('source_sha256')!=hashlib.sha256((COLLECTION/r['source']).read_bytes()).hexdigest():errors.append(r['id']+': stale render')
        out=COLLECTION/'renders'/r['id']
        for f in ['song.mp3','qa.json','review.json','qa.png','LICENSES.md',*(['source.wav'] if r['benchmark'] is not None else [])]:
            if not (out/f).is_file():errors.append(r['id']+': missing '+f)
        if (out/'qa.json').is_file():
            q=json.loads((out/'qa.json').read_text(encoding='utf-8'));clipped+=q.get('clipped_samples',0)
            if q.get('clipped_samples',0):errors.append(r['id']+': clipping')
        counts=receipts.get(r['source'],{}).get('listen',{})
        if counts.get('problem') or counts.get('warning'):findings[r['id']]=counts
    report=dict(ok=not errors,scores=len(rows),clipped_samples=clipped,errors=errors,listener_findings=findings)
    (COLLECTION/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ['prepare','render','gallery','audit']:parser.add_argument('--'+flag,action='store_true')
    parser.add_argument('--only',nargs='*');parser.add_argument('--jobs',type=int,choices=[1,2],default=2);args=parser.parse_args()
    rows=prepare() if args.prepare else json.loads((COLLECTION/'palette.json').read_text(encoding='utf-8'))
    if args.render:render_all([r for r in rows if not args.only or r['id'] in args.only],args.jobs)
    if args.gallery:gallery(rows)
    if args.audit:
        result=audit(rows);print(json.dumps(result,indent=2));raise SystemExit(0 if result['ok'] else 1)
