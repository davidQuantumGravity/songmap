"""Browser checks for the new gallery and piano/guitar Lab controls, using fixture-only Lab data."""
from pathlib import Path
import json
import socket
import tempfile
import threading
import time
import urllib.request


def main():
    import uvicorn
    from playwright.sync_api import expect,sync_playwright
    from songmap.gui import project,server
    from songmap.gui.music_lab import MusicLab
    root_repo=Path.cwd();out=root_repo/'.songmap/keys-guitars';out.mkdir(parents=True,exist_ok=True)
    gallery='http://127.0.0.1:8871/songs/keys_guitars/'
    with tempfile.TemporaryDirectory(prefix='songmap-keys-guitar-qa-') as directory:
        root=Path(directory);(root/'songs').mkdir();project.ROOT=server.ROOT=str(root);server._projects={}
        store=MusicLab(root);sessions=[]
        for part,a,b in [('keys','knight_piano','rhodes_mono'),('gtr','emily_clean','archtop_pickup')]:
            path=f'songs/{part}.sm'
            source=f'''song "{part} QA" 100 4/4 C seed=4 tail=.5
inst {part}=sampler/{a}
chords C
verse 1 | {part}:{{deg: "=p 0/4 2/8 4/8 2/4 r/4"}}
mix {part} -5
'''
            (root/path).write_text(source)
            s=store.create(path,source,part,None,0,2,'Fixture comparison; no preference vote')
            s=store.add_candidate(s['id'],{'use':'sampler/'+b,'params':{}},'Alternative recording','manual')
            store.render_pair(s['id']);store.prepare_focus(s['id']);sessions.append((s['id'],path,source))
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
                page=browser.new_page(viewport={'width':1440,'height':1050})
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(gallery)
                expect(page.locator('article')).to_have_count(54)
                page.get_by_label('Sound A',exact=True).select_option('native_piano')
                page.get_by_label('Sound B',exact=True).select_option('steinway_piano')
                page.get_by_role('button',name='Play A',exact=True).click()
                page.wait_for_function('!audio.a.paused && audio.a.currentTime > .25')
                page.locator('#position').evaluate('(el)=>{el.value=3;el.dispatchEvent(new Event("input",{bubbles:true}))}')
                page.get_by_role('button',name='Play B',exact=True).click()
                page.wait_for_function('!audio.b.paused && audio.b.currentTime >= 3')
                assert page.evaluate('audio.a.paused')
                expect(page.locator('#now')).to_contain_text('Steinway')
                page.get_by_role('button',name='Stop',exact=True).click()
                assert page.evaluate('audio.a.paused && audio.b.paused && pos===0')
                page.locator('#phrase').select_option('guitar')
                expect(page.locator('#a option')).to_have_count(10)
                page.get_by_label('Sound A',exact=True).select_option('native_guitar')
                page.get_by_label('Sound B',exact=True).select_option('nylon_finger')
                page.get_by_role('button',name='Play B',exact=True).click()
                page.wait_for_function('!audio.b.paused && audio.b.currentTime > .1')
                page.get_by_role('button',name='Stop',exact=True).click()
                page.locator('#family').select_option('Acoustic guitars')
                expect(page.locator('article:visible')).to_have_count(5)
                page.screenshot(path=str(out/'gallery-desktop.png'))
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.screenshot(path=str(out/'gallery-mobile.png'))
                page.set_viewport_size({'width':1440,'height':1050})
                for sid,path,source in sessions:
                    page.goto(f'http://127.0.0.1:{port}/?lab=1&comparison={sid}')
                    page.get_by_role('button',name='Shape this sound',exact=True).click()
                    slider=page.get_by_label('Sound brightness',exact=True)
                    expect(slider).to_be_enabled()
                    slider.focus()
                    for _ in range(30):slider.press('ArrowLeft')
                    assert abs(float(slider.input_value())+.3)<.001
                    page.get_by_label('Listening feedback',exact=True).fill('Fixture draft about attack and sustain')
                    page.get_by_role('button',name='Preview shape',exact=True).click()
                    page.get_by_role('button',name='Stop shape preview',exact=True).wait_for(timeout=30000)
                    page.screenshot(path=str(out/(path.split('/')[-1]+'.png')))
                    page.get_by_role('button',name='Stop shape preview',exact=True).click()
                    assert page.get_by_label('Listening feedback',exact=True).input_value()=='Fixture draft about attack and sustain'
                    assert not store.get(sid)['feedback'] and len(store.get(sid)['candidates'])==2
                    assert (root/path).read_text()==source
                page.goto(f'http://127.0.0.1:{port}/?song=songs/keys.sm')
                page.get_by_role('button',name='Instruments',exact=False).click()
                selector=page.get_by_role('combobox',name='sampled instrument',exact=True)
                expect(selector).to_have_value('knight_piano')
                with page.expect_response(lambda r:r.url.endswith('/api/op')) as pending:
                    selector.select_option('rhodes_mono')
                assert pending.value.json()['check']['ok']
                expect(selector).to_have_value('rhodes_mono')
                assert (root/'songs/keys.sm').read_text()==sessions[0][2]
                browser.close()
            # Check every linked playable file and source, plus sample credits.
            rows=json.loads((root_repo/'songs/keys_guitars/palette.json').read_text())
            for row in rows:
                paths=[row['source'],f'renders/{row["id"]}/song.mp3']
                if row.get('use','').startswith('sampler/') or row['benchmark'] is None:
                    paths.append(f'renders/{row["id"]}/LICENSES.md')
                for path in paths:
                    with urllib.request.urlopen(urllib.request.Request(gallery+path,method='HEAD')) as response:
                        assert response.status==200,path
            assert not errors,errors
            report={'checks':['54 gallery clips and source links','A/B switch preserves position','correct playback labels',
                              'keyboard and guitar benchmark separation','one source playing at a time','mobile layout',
                              'piano and guitar Lab shape previews','unsent feedback preserved','no votes or song writes',
                              'Studio instrument selector edit'],'browser_errors':errors,'fixture_lab_only':True}
            (out/'browser-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
        finally:
            application.should_exit=True;thread.join(timeout=15);sock.close()


if __name__=='__main__':main()
