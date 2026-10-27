"""Browser QA for ensemble auditions, four-corner morphs and saved-take editing.

Uses a disposable score/database and a separate server. Never writes creator feedback.
"""
from pathlib import Path
import json
import socket
import sys
import tempfile
import threading
import time
import urllib.request

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    import uvicorn
    from playwright.sync_api import expect,sync_playwright
    from songmap.gui import project,server
    from songmap.gui.music_lab import MusicLab
    repo=Path.cwd();out=repo/'.songmap/ensemble-research';out.mkdir(parents=True,exist_ok=True)
    gallery='http://127.0.0.1:8871/songs/ensemble_palette/'
    rows=json.loads((repo/'songs/ensemble_palette/palette.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory(prefix='songmap-ensemble-qa-') as directory:
        root=Path(directory);(root/'songs').mkdir();project.ROOT=server.ROOT=str(root);server._projects={}
        score='''song "Ensemble QA" 100 4/4 C seed=4 tail=.5
inst voice=sound/violin_palette keys=epiano
chords C
verse 1 | voice:{deg: "=p 0/4 2/8 4/8 2/4 r/4"} keys:hold
mix voice -8 | keys -12
'''
        path='songs/ensemble_fixture.sm';(root/path).write_text(score,encoding='utf-8');store=MusicLab(root)
        s=store.create(path,score,'voice',None,0,2,'Fixture; no preference selected')
        s=store.add_candidate(s['id'],{'use':'sound/trumpet_palette','params':{}},'Different sources','manual')
        store.render_pair(s['id']);store.prepare_focus(s['id'])
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        application=uvicorn.Server(uvicorn.Config(server.app,host='127.0.0.1',port=port,log_level='error'))
        thread=threading.Thread(target=application.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
        deadline=time.monotonic()+15
        while not application.started:
            assert time.monotonic()<deadline;time.sleep(.05)
        errors=[]
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(channel='msedge',headless=True)
                page=browser.new_page(viewport={'width':1440,'height':1050});page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(gallery);expect(page.locator('article')).to_have_count(len(rows))
                page.locator('#phrase').select_option('Trumpet');page.get_by_label('Sound A',exact=True).select_option('trumpet')
                page.get_by_label('Sound B',exact=True).select_option('trumpet_harmon_mute')
                page.get_by_role('button',name='Play A',exact=True).click();page.wait_for_function('!audio.a.paused && audio.a.currentTime>.1')
                page.locator('#position').evaluate('(e)=>{e.value=2;e.dispatchEvent(new Event("input",{bubbles:true}))}')
                page.get_by_role('button',name='Play B',exact=True).click();page.wait_for_function('!audio.b.paused && audio.b.currentTime>=2')
                assert page.evaluate('audio.a.paused');expect(page.locator('#now')).to_contain_text('Harmon')
                page.locator('#palette').select_option('trumpet_palette');expect(page.locator('#corners')).to_contain_text('Harmon')
                page.get_by_role('button',name='Play palette loop',exact=True).click();page.wait_for_function('graph!==null')
                assert page.evaluate('audio.a.paused && audio.b.paused && graph.sources.length===4')
                for name,value in [('x',.25),('y',.6)]:
                    page.locator('#'+name).evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}))}',value)
                page.wait_for_function('graph.gains.every((g,i)=>Math.abs(g.gain.value-[.3,.1,.45,.15][i])<.005)')
                page.screenshot(path=str(out/'gallery-desktop.png'))
                page.get_by_role('button',name='Stop palette',exact=True).click();assert page.evaluate('graph===null')
                page.locator('#palette').select_option('oboe_palette');assert page.locator('#y').is_disabled()
                page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.screenshot(path=str(out/'gallery-mobile.png'));page.set_viewport_size({'width':1440,'height':1050})
                page.goto(f'http://127.0.0.1:{port}/?lab=1&comparison={s["id"]}')
                page.get_by_role('button',name='Shape this sound',exact=True).click()
                morph=page.get_by_label('Sound morph x',exact=False);expect(morph).to_be_enabled()
                morph.focus();morph.press('ArrowRight');morph.press('ArrowRight')
                page.get_by_label('Sound added vibrato',exact=True).focus();page.get_by_label('Sound added vibrato',exact=True).press('ArrowRight')
                page.get_by_label('Listening feedback',exact=True).fill('Fixture draft: keep the warm attack')
                page.get_by_role('button',name='Preview shape',exact=True).click();page.get_by_role('button',name='Stop shape preview',exact=True).wait_for(timeout=30000)
                page.get_by_role('button',name='Stop shape preview',exact=True).click()
                assert len(store.get(s['id'])['candidates'])==2 and not store.get(s['id'])['feedback']
                page.get_by_role('button',name='Save shaped take',exact=True).click()
                page.wait_for_function('!document.body.textContent.includes("Rendering saved comparison")')
                deadline=time.monotonic()+30
                while len(store.get(s['id'])['candidates'])<3 or store.get(s['id'])['status']!='ready':
                    assert time.monotonic()<deadline;page.wait_for_timeout(150)
                expect(page.get_by_label('Listening feedback',exact=True)).to_have_value('Fixture draft: keep the warm attack')
                assert not store.get(s['id'])['feedback'];assert (root/path).read_text(encoding='utf-8')==score
                page.screenshot(path=str(out/'lab-morph.png'))
                page.goto(f'http://127.0.0.1:{port}/?song={path}');page.get_by_role('button',name='Instruments',exact=False).click()
                selector=page.get_by_label('Sound palette',exact=True);expect(selector).to_have_value('violin_palette')
                with page.expect_response(lambda r:r.url.endswith('/api/op')) as pending:selector.select_option('trumpet_palette')
                assert pending.value.json()['check']['ok'];expect(selector).to_have_value('trumpet_palette')
                expect(page.get_by_text('morph_x',exact=True)).to_be_visible()
                assert (root/path).read_text(encoding='utf-8')==score
                page.screenshot(path=str(out/'rack-morph.png'));browser.close()
            for r in rows:
                for path in [r['source'],f'renders/{r["id"]}/song.mp3',f'renders/{r["id"]}/LICENSES.md']:
                    with urllib.request.urlopen(urllib.request.Request(gallery+path,method='HEAD')) as response:assert response.status==200,path
            assert not errors,errors
            report={'ok':True,'clips':len(rows),'checks':['A/B labels and preserved playback position','four synchronized corner sources','continuous complementary morph gains','two-source palette disables Y','mobile width','Lab morph and vibrato preview/save','unsent feedback preserved','no votes or score writes','Studio palette switching and dynamic knobs','all source/audio/license links'],'browser_errors':errors}
            (out/'browser-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))
        finally:application.should_exit=True;thread.join(timeout=10)


if __name__=='__main__':main()
