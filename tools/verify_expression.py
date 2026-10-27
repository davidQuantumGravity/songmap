"""Browser checks for expression, named techniques and measured response.

Uses a disposable project/database. Does not write creator feedback or real scores.
"""
from pathlib import Path
import json
import socket
import sys
import tempfile
import threading
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

SCORE='''# Keep this authored fixture intact until Save.
song "Expression QA" 120 4/4 C seed=4 mood=v0 tail=.5
inst lead=family/violin keys=epiano
chords C:3
a 2 | lead:{deg: "=mp 0/1~ | 0/1_"} keys:hold
b 1 | lead:{deg: "=p 0/4 2/4 4/4 0/4"} keys:hold
mix lead -9 | keys -12
'''


def main():
    import uvicorn
    from playwright.sync_api import expect,sync_playwright
    from songmap.gui import project,server
    from songmap.gui.music_lab import MusicLab
    from songmap.gui.project import parse_text
    from songmap.arrange.expand import expand
    repo=Path.cwd();out=repo/'.songmap/expression';out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='songmap-expression-qa-') as directory:
        root=Path(directory);(root/'songs').mkdir();project.ROOT=server.ROOT=str(root);server._projects={}
        path='songs/expression_fixture.sm';(root/path).write_text(SCORE,encoding='utf-8')
        store=MusicLab(root);s=store.create(path,SCORE,'lead',None,0,3,'Swell one held note',scope='riff')
        store.add_candidate(s['id'],{'source':SCORE+'set expression={a: {lead: {volume: [[0,.2],[4,1],[8,.3]]}}}\n'},'Written swell','manual')
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
                page=browser.new_page(viewport={'width':1500,'height':1200});page.on('pageerror',lambda e:errors.append(str(e)))
                try:
                    page.goto(f'http://127.0.0.1:{port}/?song={path}')
                    page.get_by_role('button',name='Instruments',exact=False).click()
                    expect(page.get_by_label('Instrument family',exact=True)).to_have_value('violin')
                    default=page.get_by_label('Default technique',exact=True)
                    with page.expect_response(lambda r:r.url.endswith('/api/op')) as pending:default.select_option('2')
                    assert pending.value.json()['check']['ok'];expect(default).to_have_value('2')
                    with page.expect_response(lambda r:r.url.endswith('/api/op')) as pending:default.select_option('-1')
                    assert pending.value.json()['check']['ok']
                    page.get_by_role('button',name='Expression',exact=True).click()
                    expect(page.get_by_label('Point 1 value',exact=True)).to_have_value('1')
                    page.get_by_role('button',name='Swell shape',exact=True).click()
                    expect(page.get_by_label('Point 1 value',exact=True)).to_have_value('0.25')
                    svg=page.get_by_role('img',name='Expression curve editor',exact=True)
                    svg.scroll_into_view_if_needed();box=svg.bounding_box();assert box
                    page.mouse.click(box['x']+box['width']*.72,box['y']+box['height']*.58)
                    assert page.locator('.expression-points>div').count()==4
                    circle=svg.locator('circle').nth(1);c=circle.bounding_box();assert c
                    page.mouse.move(c['x']+c['width']/2,c['y']+c['height']/2);page.mouse.down()
                    page.mouse.move(c['x']+30,c['y']+25,steps=4);page.mouse.up()
                    page.get_by_label('Point 1 value',exact=True).fill('.2')
                    page.get_by_label('Point 4 value',exact=True).fill('.3')
                    with page.expect_response(lambda r:r.url.endswith('/api/op')) as pending:
                        page.get_by_role('button',name='Apply expression curve',exact=True).click()
                    edited=pending.value.json();assert edited['check']['ok'];assert edited['text'].startswith('# Keep this authored fixture intact until Save.')
                    assert 'a 2 | lead:{deg: "=mp 0/1~ | 0/1_"} keys:hold' in edited['text']
                    assert len(edited['check']['summary']['expression']['a']['lead']['volume'])==4
                    page.get_by_label('Point 2 beat',exact=True).fill('0')
                    with page.expect_response(lambda r:r.url.endswith('/api/op')) as pending:
                        page.get_by_role('button',name='Apply expression curve',exact=True).click()
                    assert pending.value.status==400;expect(page.get_by_role('alert')).to_contain_text('increase')
                    page.get_by_label('Expression section',exact=True).select_option('1')
                    expect(page.get_by_label('Point 1 value',exact=True)).to_have_value('0.3')
                    expect(page.get_by_label('Point 2 value',exact=True)).to_have_value('0.3')
                    page.get_by_role('button',name='Add technique change',exact=True).click()
                    page.get_by_label('Technique 1 name',exact=True).select_option('pizzicato')
                    page.get_by_role('button',name='Add technique change',exact=True).click()
                    page.get_by_label('Technique 2 beat',exact=True).fill('2')
                    page.get_by_label('Technique 2 name',exact=True).select_option('spiccato')
                    with page.expect_response(lambda r:r.url.endswith('/api/op')) as pending:
                        page.get_by_role('button',name='Apply technique changes',exact=True).click()
                    edited=pending.value.json();assert edited['check']['ok']
                    expect(page.get_by_text('Performance updated · unsaved · render to hear changes',exact=True)).to_be_visible()
                    notes=expand(parse_text(edited['text'],path)).parts['lead']
                    assert [e.technique for e in notes if e.section=='b']==['pizzicato','pizzicato','spiccato','spiccato']
                    assert (root/path).read_text(encoding='utf-8')==SCORE
                    page.get_by_role('heading',name='Expression & techniques',exact=True).scroll_into_view_if_needed()
                    page.screenshot(path=str(out/'studio-expression.png'))
                    with page.expect_response(lambda r:r.url.endswith('/api/render'),timeout=30000) as pending:
                        page.get_by_role('button',name='Render',exact=True).click()
                    assert pending.value.status==200
                    page.get_by_role('button',name='Knobs',exact=True).click()
                    calibration=page.locator('.knob').filter(has=page.get_by_text('calibration',exact=True));expect(calibration).to_have_count(1)
                    calibration.scroll_into_view_if_needed();knob=calibration.locator('svg').bounding_box();assert knob
                    page.mouse.move(knob['x']+knob['width']/2,knob['y']+knob['height']/2);page.mouse.down()
                    page.mouse.move(knob['x']+knob['width']/2,knob['y']+knob['height']/2+60,steps=5)
                    with page.expect_response(lambda r:r.url.endswith('/api/op')) as pending:page.mouse.up()
                    edited=pending.value.json();assert edited['check']['ok']
                    assert 0<=edited['check']['summary']['voices']['lead']['values']['calibration']<1
                    assert (root/path).read_text(encoding='utf-8')==SCORE
                    page.goto(f'http://127.0.0.1:{port}/?lab=1&comparison={s["id"]}')
                    feedback=page.get_by_label('Listening feedback',exact=True);feedback.fill('QA draft: a softer opening')
                    page.get_by_role('button',name='Score focus',exact=True).click()
                    expect(page.get_by_text('notes / expression',exact=False).first).to_be_visible()
                    expect(feedback).to_have_value('QA draft: a softer opening')
                    assert not store.get(s['id'])['feedback']
                    page.screenshot(path=str(out/'lab-expression.png'))
                    page.goto('http://127.0.0.1:8871/songs/expression_lab/index.html')
                    expect(page.locator('article')).to_have_count(3)
                    page.locator('article').first.get_by_role('button',name='A · baseline',exact=True).click()
                    page.wait_for_function('!document.querySelector("audio").paused&&document.querySelector("audio").currentTime>.1')
                    page.locator('audio').evaluate('(a)=>a.currentTime=2')
                    page.locator('article').first.get_by_role('button',name='B · written expression / techniques',exact=True).click()
                    page.wait_for_function('!document.querySelector("audio").paused&&document.querySelector("audio").currentTime>=2')
                    expect(page.locator('#status')).to_contain_text('B · written expression')
                    for link in page.locator('article a').all():assert page.request.get(link.evaluate('(a)=>a.href')).status==200
                    page.screenshot(path=str(out/'auditions-desktop.png'))
                    page.set_viewport_size({'width':390,'height':844})
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    page.screenshot(path=str(out/'auditions-mobile.png'))
                    page.goto('http://127.0.0.1:8871/songs/ensemble_palette/index.html')
                    page.locator('#palette').select_option('trumpet_palette')
                    requested=[];page.on('request',lambda r:requested.append(r.url))
                    fault={'done':False}
                    def first_request_reset(route):
                        if not fault['done']:fault['done']=True;route.abort('connectionreset')
                        else:route.continue_()
                    page.route('**/source.wav',first_request_reset)
                    page.get_by_role('button',name='Play palette loop',exact=True).click()
                    page.wait_for_function('graph!==null || document.querySelector("#morph-status").textContent.includes("fetch") || document.querySelector("#morph-status").textContent.includes("timed")',timeout=30000)
                    assert page.evaluate('graph!==null'),page.locator('#morph-status').inner_text()
                    assert len(set(u for u in requested if u.endswith('/source.wav')))==4
                    assert fault['done'] and len([u for u in requested if u.endswith('/source.wav')])>=5
                    assert page.evaluate('graph.sources.length===4')
                    page.get_by_role('button',name='Stop palette',exact=True).click()
                    browser.close()
                except Exception:
                    page.screenshot(path=str(out/'browser-failure.png'));print(page.locator('body').inner_text()[-6500:]);raise
            assert not errors,errors
            report={'ok':True,'checks':['family and default technique selectors','curve add/drag/numeric editing','invalid curve rejected without replacing buffer','inherited terminal values','technique schedule selects real recordings','unsaved score preserved on disk','render endpoint','calibration knob','AI Lab curve-only change label and retained feedback draft','A/B position and labels','source/audio/license links','mobile audition width','four raw morph sources with recovery from an injected connection reset'],'browser_errors':errors}
            (out/'browser-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))
        finally:application.should_exit=True;thread.join(timeout=10)


if __name__=='__main__':main()
