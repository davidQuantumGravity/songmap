"""Browser QA against an isolated fixture database, never the creator's Lab data."""
from __future__ import annotations

import json
from pathlib import Path
import socket
import tempfile
import threading
import time


def main():
    import uvicorn
    from playwright.sync_api import sync_playwright
    from songmap.gui import project, server
    from songmap.gui.music_lab import MusicLab
    from songmap.instruments.dsp import SR

    out = Path(".songmap/instrument-lab").resolve()
    out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="songmap-sound-qa-") as directory:
        root = Path(directory)
        (root/"songs").mkdir()
        score = '''song "Sound controls QA" 120 4/4 C seed=4 tail=.3
chords C
inst bass=bass/sub keys=epiano
verse 1 | bass:eighths keys:hold drums:half
'''
        path = "songs/fixture.sm"
        (root/path).write_text(score)
        project.ROOT = server.ROOT = str(root)
        store = MusicLab(root)
        s = store.create(path,score,"bass",None,0,2,"Tone controls QA")
        s = store.add_candidate(s["id"],{"use":"bass/rubber","params":{}},"B","manual")
        store.render_pair(s["id"])
        store.prepare_focus(s["id"])
        sock = socket.socket()
        sock.bind(("127.0.0.1",0))
        port = sock.getsockname()[1]
        application = uvicorn.Server(uvicorn.Config(server.app,host="127.0.0.1",port=port,log_level="error"))
        thread = threading.Thread(target=application.run,kwargs={"sockets":[sock]},daemon=True)
        thread.start()
        deadline = time.monotonic()+15
        while not application.started:
            assert time.monotonic()<deadline,"QA server failed to start"
            time.sleep(.05)
        errors, requests = [], []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(channel="msedge",headless=True)
                page = browser.new_page(viewport={"width":1440,"height":1100})
                page.on("pageerror",lambda e: errors.append(str(e)))
                page.on("response",lambda r: requests.append((r.url,r.status)))
                page.add_init_script('''window.soundQA={starts:[],gains:[]};
const start=AudioBufferSourceNode.prototype.start;
AudioBufferSourceNode.prototype.start=function(...args){window.soundQA.starts.push(args[0]);return start.apply(this,args)};
const target=AudioParam.prototype.setTargetAtTime;
AudioParam.prototype.setTargetAtTime=function(...args){window.soundQA.gains.push(args[0]);return target.apply(this,args)};''')
                page.goto(f"http://127.0.0.1:{port}/?lab=1&comparison={s['id']}")
                page.get_by_role("button",name="Shape this sound",exact=True).click()
                slider = page.get_by_label("Sound brightness",exact=True)
                slider.wait_for()
                page.wait_for_function("!document.querySelector('[aria-label=\"Sound brightness\"]').disabled")
                page.get_by_label("Listening feedback",exact=True).fill("QA draft survives sound design")
                slider.focus()
                for _ in range(40):
                    slider.press("ArrowLeft")
                assert abs(float(slider.input_value())+.4)<.001
                page.get_by_role("button",name="Preview shape",exact=True).click()
                page.get_by_role("button",name="Stop shape preview",exact=True).wait_for(timeout=30000)
                assert page.get_by_role("button",name="Prefer B",exact=True).is_disabled()
                assert len(store.get(s["id"])["candidates"]) == 2
                page.screenshot(path=str(out/"sound-shape-desktop.png"))
                page.get_by_role("button",name="Stop shape preview",exact=True).click()
                page.get_by_role("button",name="Save shaped take",exact=True).click()
                page.get_by_role("article",name="B take 3",exact=True).wait_for(timeout=30000)
                page.wait_for_function("!document.querySelector('[aria-label=\"Sound brightness\"]').disabled")
                assert page.get_by_label("Listening feedback",exact=True).input_value()=="QA draft survives sound design"
                page.get_by_role("button",name="Blend A ↔ B",exact=True).click()
                page.get_by_role("button",name="Play blend",exact=True).click()
                page.get_by_role("button",name="Stop blend preview",exact=True).wait_for()
                assert page.get_by_label("Listening context").input_value()=="solo"
                assert page.get_by_role("button",name="Prefer A",exact=True).is_disabled()
                blend = page.get_by_label("A/B blend",exact=True)
                blend.focus()
                for _ in range(15):
                    blend.press("ArrowLeft")
                assert abs(float(blend.input_value())-.35)<.001
                starts = page.evaluate("window.soundQA.starts")
                gains = page.evaluate("window.soundQA.gains")
                assert len(starts)==2 and starts[0]==starts[1],starts
                assert any(abs(v-.35)<.001 for v in gains) and any(abs(v-.65)<.001 for v in gains),gains
                page.screenshot(path=str(out/"sound-blend-desktop.png"))
                page.locator(".lab-sound-designer").screenshot(path=str(out/"sound-controls.png"))
                page.get_by_role("button",name="Play B · Take 3",exact=True).click()
                page.get_by_role("button",name="Play blend",exact=True).wait_for()
                page.get_by_role("button",name="Pause B · Take 3",exact=True).click()
                page.get_by_role("button",name="Play blend",exact=True).click()
                page.get_by_role("button",name="Stop blend preview",exact=True).wait_for()
                page.set_viewport_size({"width":390,"height":844})
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
                page.screenshot(path=str(out/"sound-blend-mobile.png"))
                page.get_by_role("button",name="Save blended take",exact=True).click()
                page.get_by_role("article",name="B take 4",exact=True).wait_for(timeout=30000)
                deadline = time.monotonic()+30
                while store.get(s["id"])["status"] != "ready":
                    assert time.monotonic()<deadline,store.get(s["id"])["error"]
                    page.wait_for_timeout(200)
                saved = store.get(s["id"])
                assert len(saved["candidates"])==4 and saved["incumbent"]==s["incumbent"] and not saved["feedback"]
                assert saved["candidates"][-1]["design"]["amount"]==.35
                assert (root/path).read_text()==score
                assert not [r for r in requests if r[1]>=400 and "/favicon" not in r[0]],requests
                browser.close()
            assert not errors,errors
            report={"checks":["shape preview without a saved take","saved shape becomes a challenger","typed feedback preserved",
                              "two blend sources start together","blend gains update during playback","blend saves an editable take",
                              "no automatic votes or song edits","main transport stops design preview","votes wait for a saved take","mobile width"],"browser_errors":errors,"fixture_only":True,
                    "sample_rate":SR,"screenshots":["sound-shape-desktop.png","sound-blend-desktop.png","sound-blend-mobile.png"]}
            (out/"sound-design-verification.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
            print(json.dumps(report))
        finally:
            application.should_exit=True
            thread.join(timeout=15)
            sock.close()


if __name__=="__main__":
    main()
