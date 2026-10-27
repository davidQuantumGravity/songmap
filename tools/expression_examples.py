"""Render three authored expression demonstrations and explicit, controlled baselines."""
from pathlib import Path
import hashlib
import html
import json
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def main():
    from songmap.parse.lang import load
    from songmap.parse.fmt import to_sm
    from songmap.arrange.expand import expand
    from songmap.listen import listen
    from songmap.render import render,write_outputs
    folder=ROOT/'songs/expression_lab';rows=[];cards=[]
    for file in sorted(folder.glob('*.sm')):
        song=load(str(file));baseline=load(str(file));baseline.expression={};baseline.techniques={}
        if file.stem.startswith('02_'):
            baseline.instruments['violin']={'use':'family/violin','technique':0}
        base=folder/'baselines'/file.name;base.parent.mkdir(exist_ok=True)
        base.write_text('# Controlled baseline: same notes and mix; continuous curves and technique changes removed.\n'+to_sm(baseline),encoding='utf-8')
        outputs=[]
        for source,score,suffix in [(base,baseline,'_baseline'),(file,song,'')]:
            arr=expand(score);arr.ensemble.check(score.parts());result=render(score)
            dest=folder/'renders'/(file.stem+suffix);write_outputs(result,str(dest),mp3=True)
            qa=json.loads((dest/'qa.json').read_text(encoding='utf-8'));assert qa['clipped_samples']==0
            row=dict(source=source.relative_to(folder).as_posix(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),clipped_samples=qa['clipped_samples'],listen=listen(arr).counts())
            rows.append(row);outputs.append(dest.relative_to(folder).as_posix());print(row,flush=True)
        title=html.escape(song.title);url='http://127.0.0.1:8867/?song=songs%2Fexpression_lab%2F'+file.name
        cards.append(f'<article><h2>{title}</h2><p><button data-src="{outputs[0]}/song.mp3">A · baseline</button> <button data-src="{outputs[1]}/song.mp3">B · written expression / techniques</button></p><p><a href="{url}">Open in Studio</a> · <a href="{file.name}">Editable score</a> · <a href="{outputs[1]}/LICENSES.md">Credits</a> · <a href="{outputs[1]}/qa.png">Audio QA</a></p></article>')
    (folder/'verification.json').write_text(json.dumps(dict(ok=True,scores=len(rows),renders=rows),indent=2)+'\n',encoding='utf-8')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SongMap · Expression</title><style>*{box-sizing:border-box}body{background:#101820;color:#eef3f6;font:17px/1.6 system-ui;margin:0}main{max-width:1000px;margin:auto;padding:30px 22px}a{color:#a3dec9}article{border:1px solid #607688;background:#1b2a36;border-radius:12px;padding:20px;margin:22px 0}button{font:inherit;border:1px solid #91adbe;background:#294150;color:white;padding:10px;cursor:pointer;border-radius:6px;max-width:100%}audio{width:100%}h1{line-height:1.2}p{color:#c5d2dc}</style><main><h1>Expression, real techniques and measured response</h1><p>Compare the same authored notes and mix with and without the new expression curves and technique schedule. Switch A/B at the current position. The baseline keeps source calibration fixed, so it isolates performance changes.</p><p>In Studio: Instruments → family · recorded techniques → Expression. Draw a curve, schedule techniques, Render, then Save. The calibration knob blends original and measured gain without flattening note dynamics.</p><p><a href="../ensemble_palette/index.html">Ensemble palette and corrected raw-source morph player</a> · <a href="../../docs/EXPRESSION_ARTICULATION_RESPONSE.md">Feature guide and calibration method</a></p><audio id="player" controls></audio><p id="status" aria-live="polite">Choose an audition</p>CARDS</main><script>const audio=document.getElementById('player'),status=document.getElementById('status');let selected=null;document.querySelectorAll('button[data-src]').forEach(b=>b.onclick=()=>{const group=b.closest('article');const position=selected===group?audio.currentTime:0;audio.pause();selected=group;audio.src=b.dataset.src;audio.onloadedmetadata=()=>{audio.currentTime=Math.min(position,audio.duration-.01);audio.play().catch(e=>status.textContent=e.message)};status.textContent=group.querySelector('h2').textContent+' · '+b.textContent});</script></html>'''
    (folder/'index.html').write_text(page.replace('CARDS','\n'.join(cards)),encoding='utf-8')


if __name__=='__main__':main()
