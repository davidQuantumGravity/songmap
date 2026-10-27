"""Prepare controlled timbre auditions, render authored templates, and build their A/B page.

--prepare writes the benchmark auditions; hand-authored templates are preserved. Samples are
installed by songmap samples install, never downloaded here. Run from the repository root.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import gc
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLLECTION = ROOT/'songs/keys_guitars'
SAMPLED = ['grand_piano','steinway_piano','knight_piano','yamaha_piano','meta_piano',
           'fm_piano','tx_piano','clavisynth','rhodes_mono','rhodes_stereo','rhodes_vibrato',
           'english_harpsichord','lute_harpsichord','french_harpsichord','italian_harpsichord','flemish_harpsichord','flemish_full',
           'renaissance_8','renaissance_4','renaissance_4_8','renaissance_full','pipe_quiet','pipe_loud',
           'nylon_guitar','nylon_finger','nylon_pick','steel_guitar','archtop_mic','archtop_pickup','emily_clean','emily_release','emily_ensemble']
EPIANOS = ['round_tine','warm_suitcase','bright_bark','soft_ballad','bell_keys','wide_tremolo','dry_funk','fm_chime']
ORGANS = ['hollow_jazz','gospel','soft_chorale','rock_rotary']
TEMPLATES = [('01_upright_conversation','Upright conversation','An intimate piano question and answer, with sparse upright bass.'),
 ('02_rhodes_pocket','Rhodes pocket','Shell voicings, gaps in the comping and bass answers around the backbeat.'),
 ('03_harpsichord_dialogue','Harpsichord dialogue','Two independent plucked-keyboard voices; articulation creates the contrast.'),
 ('04_six_eight_organ','Six-eight organ','A lilting organ registration, rooted bass and a restrained drum pulse.'),
 ('05_nylon_fingerstyle','Nylon fingerstyle','Three-string shapes, alternating bass notes and a climbing reply.'),
 ('06_steel_open_chords','Steel open chords','Playable sparse chord shapes, spaces between strums and a quieter ending.'),
 ('07_electric_pocket','Electric pocket','Short DI double-stops leave room for bass and dry snare.'),
 ('08_archtop_after_hours','Archtop after hours','Small jazz voicings over walking fragments; room for the recorded attack.')]


def prepare():
    from songmap.instruments.sampler.library import manifest
    from songmap.instruments.presets import resolve
    rows=[]
    voices=[(n,'sampler/'+n,manifest()['voices'][n]['title'],manifest()['voices'][n]['category'],manifest()['voices'][n]['description']) for n in SAMPLED]
    for inst,names in [('epiano',EPIANOS),('organ',ORGANS)]:
        for n in names:
            voices.append((inst+'_'+n,inst+'/'+n,n.replace('_',' ').title(),'Synthesized electric keys' if inst=='epiano' else 'Tonewheel organ recipes',
                           'Native synthesis recipe; compare the envelope, velocity response and modulation.'))
    voices += [('native_piano','keys','Original modeled piano','Reference sounds','Existing modeled piano, retained as an A/B reference.'),
               ('native_guitar','string_pluck','Original modeled guitar','Reference sounds','Existing plucked-string model, retained as an A/B reference.')]
    for name,use,title,group,description in voices:
        guitar='guitar' in group.lower() or use=='string_pluck'
        part='gtr' if guitar else 'keys'
        phrases=(['=p 0/8^ 4/8 9/8 4/8 7/4 9/8 r/8',
                  '=mp [1,5,10]/4 8/8 5/8 3/4 r/4',
                  "=mf [-3,3,6]/8'^ r/8 [-3,3,6]/8' r/8 4/4 3/4",
                  '=p [0,4,7,9]/2_ r/2'] if guitar else
                 ['=p [0,2,4]/4 6/8 4/8 [0,2,4]/4 r/4',
                  '=mp [1,3,5]/4 7/8 5/8 [1,3,5]/4 r/4',
                  "=mf [1,3,6]/8'^ r/8 [1,3,6]/8' r/8 4/4 3/4",
                  '=p [0,2,4,6]/2_ 2/4 r/4'])
        score=f'''# Controlled {'guitar' if guitar else 'keyboard'} timbre audition: {title}.
# Notes: soft call, answering voicing, firmer detached attacks, then a resting resolution.
# Expression is written per phrase. This shared benchmark compares sounds; it is not a finished composition.
song "{title}" 100 4/4 C seed=83 tail=2 mood=balanced
inst {part}={use}
chords Cmaj7:1 Dm7:1 G7:1 Cmaj7:1
'''
        for sec,phrase in zip(['call','reply','firm','land'],phrases):
            score+=f'{sec} 1 | {part}:{{deg: "{phrase}", oct: {-1 if guitar else 0}}}\n'
        score+=f'mix {part} -5 hall=.04\nmaster standard lufs=-18 glue=none\n'
        path=COLLECTION/'auditions'/(name+'.sm');path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(score,encoding='utf-8')
        rows.append({'source':path.relative_to(COLLECTION).as_posix(),'id':name,'title':title,'group':group,
                     'description':description,'benchmark':'guitar' if guitar else 'keyboard','use':use})
    for name,title,description in TEMPLATES:
        rows.append({'source':'templates/'+name+'.sm','id':name,'title':title,'group':'Musical starters','description':description,'benchmark':None})
    (COLLECTION/'palette.json').write_text(json.dumps(rows,indent=2)+'\n')
    return rows


def render_one(row):
    from songmap.parse.lang import load
    from songmap.arrange.expand import expand
    from songmap.listen import listen
    from songmap.render import render,write_outputs
    from songmap.instruments.sampler.library import SAMPLES
    source=COLLECTION/row['source']
    song=load(str(source));arr=expand(song);arr.ensemble.check(song.parts())
    result=render(song)
    write_outputs(result,str(COLLECTION/'renders'/row['id']),mp3=True,stems=row['benchmark'] is None)
    record={'source':row['source'],'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'digest':arr.digest(),
            'listen':listen(arr).counts()}
    SAMPLES._data.clear();del result,arr;gc.collect()
    return record


def render_all(rows,jobs):
    receipt=COLLECTION/'render_receipt.json'
    previous={r['source']:r for r in json.loads(receipt.read_text())} if receipt.is_file() else {}
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        for row,record in zip(rows,pool.map(render_one,rows)):
            previous[row['source']]=record
            receipt.write_text(json.dumps(list(previous.values()),indent=2)+'\n')
            print('rendered',row['id'],record['listen'],flush=True)


def gallery(rows):
    cards=[]
    for row in rows:
        name=html.escape(row['title']);description=html.escape(row['description']);source=html.escape(row['source'])
        credits=(f'<a href="renders/{row["id"]}/LICENSES.md">Credits</a> · ' if row.get('use','').startswith('sampler/') or row['benchmark'] is None else 'Native synthesis · ')
        cards.append(f'''<article data-group="{html.escape(row['group'])}"><h3>{name}</h3><p>{description}</p>
<audio controls preload="none" src="renders/{row['id']}/song.mp3"></audio><p><a href="{source}">Editable score</a> ·
<a href="http://127.0.0.1:8867/?song=songs%2Fkeys_guitars%2F{source.replace('/','%2F')}">Open in Studio</a> ·
{credits}<a href="renders/{row['id']}/qa.png">Audio QA</a></p></article>''')
    options=''.join(f'<option>{html.escape(g)}</option>' for g in dict.fromkeys(r['group'] for r in rows))
    # Labels and references come from the same manifest as Studio, rather than invented model descriptions.
    data=json.dumps([{k:r[k] for k in ('id','title','benchmark')} for r in rows if r['benchmark']]).replace('<','\\u003c')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SongMap · Keys & guitars</title><style>
*{box-sizing:border-box}body{margin:0;background:#10151b;color:#edf1f6;font:16px/1.55 system-ui}main{max-width:1200px;margin:auto;padding:35px 24px}h1{font-size:clamp(2rem,5vw,3.5rem);line-height:1.1}h2{margin-top:30px}p{color:#becbd8}a{color:#9bd9c3}nav{display:flex;gap:18px;flex-wrap:wrap}.tag{color:#9bd9c3;text-transform:uppercase;letter-spacing:.14em}#grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px;margin-top:20px}article,.compare{border:1px solid #3e5062;border-radius:12px;padding:20px;background:#19222c}article h3{margin:0 0 8px}article p{font-size:.9rem}audio{width:100%}button,select{font:inherit;background:#263747;color:#fff;border:1px solid #698397;padding:8px;border-radius:6px;max-width:100%}button{cursor:pointer}.choices{display:grid;grid-template-columns:1fr 1fr;gap:15px}.choices label{display:flex;flex-direction:column;gap:7px}.choices audio{margin-top:10px}article[hidden]{display:none}.small{font-size:.9rem}#position{accent-color:#9bd9c3;width:100%}.controls{display:flex;gap:12px;flex-wrap:wrap;margin:14px 0}@media(max-width:600px){.choices{grid-template-columns:1fr}}</style>
<main><div class="tag">SongMap sound library</div><h1>Keys & guitars, with a player's touch.</h1>
<p>Five acoustic pianos, recorded Rhodes and FM keyboards, six harpsichord programs, six recorded organ registrations, nine guitar programs, eight new FM electric-piano recipes, four tonewheel recipes, and eight editable musical starters.</p>
<nav><a href="../rhythm_palette/index.html">Bass & drums</a><a href="../sfz_revisited/index.html#comparisons">Earlier song comparisons</a><a href="../../docs/KEYS_GUITAR_PALETTE.md">Palette guide</a><a href="http://127.0.0.1:8867/?lab=1">AI Lab · saved A/B feedback</a></nav>
<section class="compare" aria-label="Controlled A/B comparison"><h2>Compare the same phrase</h2>
<p class="small">Auditions within each family share the exact score, tempo and written expression and target −18 LUFS. Switch A/B at the current position; different sample attacks and tails remain audible. These controls audition sounds. Save preferences and text feedback in AI Lab.</p>
<label>Phrase family <select id="phrase"><option value="keyboard">Keyboard</option><option value="guitar">Guitar</option></select></label>
<div class="choices"><label>A <select id="a" aria-label="Sound A"></select></label><label>B <select id="b" aria-label="Sound B"></select></label></div>
<div class="controls"><button id="play-a">Play A</button><button id="play-b">Play B</button><button id="stop">Stop</button><span id="now" aria-live="polite">Choose two sounds</span></div>
<label>Position <input id="position" type="range" min="0" max="11.6" value="0" step=".01"></label></section>
<h2>Explore the palette and musical starters</h2><p class="small">Registrations, pickup channels, playing techniques and layered takes are labeled as such. They are not all different physical instruments. Guitar keyswitches and piano pedals are fixed during preparation; live pedals, connected legato, slides and amp modeling are not supplied by these programs.</p>
<label>Show <select id="family"><option>Everything</option>OPTIONS</select></label><section id="grid">CARDS</section></main>
<script>const rows=DATA;const $=id=>document.getElementById(id);const audio={a:new Audio(),b:new Audio()};let active=null,pos=0;
function stop(){Object.values(audio).forEach(a=>a.pause());active=null}
function choices(){stop();pos=0;$('position').value=0;const list=rows.filter(r=>r.benchmark===$('phrase').value);for(const side of ['a','b']){$(side).replaceChildren(...list.map(r=>new Option(r.title,r.id)));} $('b').selectedIndex=Math.min(1,list.length-1);$('now').textContent='Ready';}
function play(side){pos=active?audio[active].currentTime:pos;stop();document.querySelectorAll('article audio').forEach(a=>a.pause());active=side;const a=audio[side];const src=new URL('renders/'+$(side).value+'/song.mp3',location.href).href;if(a.src!==src){a.src=src;a.onloadedmetadata=()=>{if(active!==side)return;a.currentTime=Math.min(pos,a.duration||pos);a.play().catch(e=>$('now').textContent=e.message)}}else{a.currentTime=pos;a.play().catch(e=>$('now').textContent=e.message)}$('now').textContent=side.toUpperCase()+' · '+$(side).selectedOptions[0].textContent;}
for(const side of ['a','b']){$('play-'+side).onclick=()=>play(side);$(side).onchange=()=>{if(active===side)play(side)};audio[side].ontimeupdate=()=>{if(active===side){pos=audio[side].currentTime;$('position').max=audio[side].duration||11.6;$('position').value=pos}};audio[side].onended=()=>{stop();pos=0;$('now').textContent='Finished'};}
$('phrase').onchange=choices;$('position').oninput=()=>{pos=+$('position').value;if(active)audio[active].currentTime=pos};$('stop').onclick=()=>{stop();pos=0;$('position').value=0;$('now').textContent='Stopped'};choices();$('family').onchange=e=>document.querySelectorAll('article').forEach(a=>a.hidden=e.target.value!=='Everything'&&a.dataset.group!==e.target.value);document.addEventListener('play',e=>{if(e.target.tagName==='AUDIO'){stop();document.querySelectorAll('article audio').forEach(a=>{if(a!==e.target)a.pause()})}},true);</script></html>'''
    (COLLECTION/'index.html').write_text(page.replace('OPTIONS',options).replace('CARDS','\n'.join(cards)).replace('DATA',data),encoding='utf-8')


def audit(rows):
    receipts={r['source']:r for r in json.loads((COLLECTION/'render_receipt.json').read_text())}
    errors=[];clipped=0
    for row in rows:
        digest=hashlib.sha256((COLLECTION/row['source']).read_bytes()).hexdigest()
        if receipts.get(row['source'],{}).get('source_sha256')!=digest:
            errors.append(row['id']+': missing or stale render')
        out=COLLECTION/'renders'/row['id']
        names=['song.mp3','qa.json','review.json','qa.png']
        if row.get('use','').startswith('sampler/') or row['benchmark'] is None:names.append('LICENSES.md')
        for name in names:
            if not (out/name).is_file():errors.append(row['id']+': missing '+name)
        if (out/'qa.json').is_file():
            qa=json.loads((out/'qa.json').read_text());clipped+=qa.get('clipped_samples',0)
            if qa.get('clipped_samples',0):errors.append(row['id']+': clipping')
        counts=receipts.get(row['source'],{}).get('listen',{})
        if counts.get('problem') or counts.get('warning'):errors.append(row['id']+': score listener findings')
    report={'scores':len(rows),'clipped_samples':clipped,'errors':errors,'ok':not errors}
    (COLLECTION/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ('prepare','render','gallery','audit'):parser.add_argument('--'+flag,action='store_true')
    parser.add_argument('--only',nargs='*');parser.add_argument('--jobs',type=int,choices=(1,2),default=2)
    args=parser.parse_args()
    rows=prepare() if args.prepare else json.loads((COLLECTION/'palette.json').read_text())
    if args.render:render_all([r for r in rows if not args.only or r['id'] in args.only],args.jobs)
    if args.gallery:gallery(rows)
    if args.audit:
        result=audit(rows);print(json.dumps(result,indent=2));raise SystemExit(0 if result['ok'] else 1)
