"""Exercise the built Studio against temporary scores, never the user's open project."""
from __future__ import annotations

import json
from pathlib import Path
import socket
import tempfile
import threading
import time


def main():
    import uvicorn
    from playwright.sync_api import expect, sync_playwright
    from songmap.arrange.expand import expand
    from songmap.gui import project, server
    from songmap.gui.project import parse_text
    from songmap.parse.fmt import to_yaml

    score = '''song "Conductor study" 120 4/4 C seed=7 tail=.2
chords C
motif phrase deg "0/4 2 4 6"
intro 1 | lead:[phrase] bass:sub
odd 2 | lead:{deg: "0/8 1 2 3 4 5 6"} meter="7/8 2+2+3" tempo=90 key="D dorian"
outro 2 | lead:{deg: "0/4 1 2 3 4"} meter=5/4 tempo=accel90>120 key="E phrygian"
'''
    structured = '''song "Form" 120 4/4 C
verse = {lead: {deg: "0/1"}}
form:
  verse 1
  verse 1
'''
    out = Path(".songmap/conductor").resolve()
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="songmap-conductor-qa-") as directory:
        root = Path(directory)
        (root/"songs").mkdir()
        (root/"songs/study.sm").write_text(score)
        (root/"songs/study.yaml").write_text(to_yaml(parse_text(score,"a.sm")))
        (root/"songs/form.sm").write_text(structured)
        project.ROOT = server.ROOT = str(root)
        server._projects = {}
        sock = socket.socket(); sock.bind(("127.0.0.1",0))
        port = sock.getsockname()[1]
        application = uvicorn.Server(uvicorn.Config(server.app,host="127.0.0.1",port=port,log_level="error"))
        thread = threading.Thread(target=application.run,kwargs={"sockets":[sock]},daemon=True)
        thread.start()
        deadline = time.monotonic()+15
        while not application.started:
            assert time.monotonic()<deadline
            time.sleep(.05)
        errors, responses = [], []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(channel="msedge",headless=True)
                page = browser.new_page(viewport={"width":1600,"height":1100})
                page.on("pageerror",lambda e:errors.append(str(e)))
                page.on("response",lambda r:responses.append((r.url,r.status)))
                base = f"http://127.0.0.1:{port}"
                page.goto(base+"/?conductor=1&song=songs/study.sm")
                panel = page.get_by_label("Conductor editor",exact=True)
                panel.wait_for()
                page.get_by_role("button",name="Edit conductor odd",exact=True).click()
                expect(page.get_by_label("Time signature",exact=True)).to_have_value("7/8 2+2+3")
                assert page.get_by_label("Scale or mode",exact=True).input_value()=="dorian"
                page.get_by_label("Tempo behavior",exact=True).select_option("ramp")
                page.get_by_label("Tempo start BPM",exact=True).fill("130")
                page.get_by_label("Tempo end BPM",exact=True).fill("100")
                page.get_by_label("Time signature",exact=True).fill("7/8 3+2+2")
                page.get_by_label("Tonic",exact=True).fill("F#")
                page.get_by_label("Scale or mode",exact=True).select_option("harmonic_minor")
                with page.expect_response(lambda r:r.url.endswith("/api/op")) as pending:
                    page.get_by_role("button",name="Apply to score",exact=True).click()
                data = pending.value.json()
                assert data["check"]["ok"],data
                page.get_by_role("status").filter(has_text="Applied to the score").wait_for()
                expect(page.get_by_label("Current tempo",exact=True)).to_have_text("130 bpm")
                assert page.get_by_label("Current time signature",exact=True).inner_text()=="7/8 3+2+2"
                assert page.get_by_label("Current key and scale",exact=True).inner_text()=="F# harmonic_minor"
                assert (root/"songs/study.sm").read_text()==score
                assert page.get_by_role("button",name="Save",exact=True).is_enabled()
                page.screenshot(path=str(out/"conductor-studio.png"))

                # Seek to the midpoint in BEATS, verifying the exact ramp inverse in the transport.
                song = parse_text(data["text"],"a.sm"); tl = expand(song).timeline
                span = tl.sections[1]
                target_beat = (span.start+span.end)/2 + .25
                at = tl.beat_to_sec(target_beat)
                canvas = page.locator(".arr-inner canvas")
                box = canvas.bounding_box()
                pxs = (box["width"]-150-12)/data["check"]["summary"]["seconds"]
                canvas.click(position={"x":150+at*pxs,"y":155})
                # Browser pointer positions are pixel-rounded; compare within that seek precision.
                shown = float(page.get_by_label("Current tempo",exact=True).inner_text().split()[0])
                assert abs(shown-tl.bpm_at(target_beat))<.3,(shown,tl.bpm_at(target_beat))
                assert page.locator(".lcd > div").first.inner_text().startswith("3.1")
                # A conductor lane click selects its section without touching the source.
                canvas.click(position={"x":150+data["check"]["summary"]["sections"][2]["start"]*pxs+5,"y":90})
                expect(page.get_by_label("Conductor target",exact=True)).to_have_value("2")
                assert page.get_by_label("Current key and scale",exact=True).inner_text()=="E phrygian"
                canvas.click(position={"x":box["width"]-13,"y":155})
                assert page.locator(".lcd > div").first.inner_text().startswith("5.5")
                assert page.get_by_label("Current tempo",exact=True).inner_text()=="120 bpm"

                page.get_by_label("Time signature",exact=True).fill("7/8 2+2")
                page.get_by_role("button",name="Apply to score",exact=True).click()
                page.get_by_role("alert").wait_for()
                assert "7/8 2+2" in page.get_by_role("alert").inner_text()
                assert (root/"songs/study.sm").read_text()==score
                page.get_by_label("Time signature",exact=True).fill("5/4")
                # Song default edit leaves explicit overrides alone.
                page.get_by_label("Conductor target",exact=True).select_option("song")
                page.get_by_label("Tempo start BPM",exact=True).fill("108")
                with page.expect_response(lambda r:r.url.endswith("/api/op")) as pending:
                    page.get_by_role("button",name="Apply to score",exact=True).click()
                changed = pending.value.json()
                assert changed["check"]["summary"]["sections"][0]["tempo_start"]==108
                assert changed["check"]["summary"]["sections"][1]["tempo_start"]==130
                page.get_by_role("status").filter(has_text="Applied to the score").wait_for()
                page.get_by_role("button",name="Save",exact=True).click()
                page.wait_for_function("document.querySelector('header button:last-child').disabled")
                assert parse_text((root/"songs/study.sm").read_text(),"a.sm").tempo==108

                # YAML and repeated structured sections use the same visible edit workflow.
                for file in ("study.yaml","form.sm"):
                    page.goto(base+"/?conductor=1&song=songs/"+file)
                    panel.wait_for()
                    page.get_by_label("Conductor target",exact=True).select_option("1")
                    page.get_by_label("Tempo behavior",exact=True).select_option("constant")
                    page.get_by_label("Tempo start BPM",exact=True).fill("83")
                    with page.expect_response(lambda r:r.url.endswith("/api/op")) as pending:
                        page.get_by_role("button",name="Apply to score",exact=True).click()
                    result=pending.value.json()
                    assert result["check"]["ok"],result
                    assert result["check"]["summary"]["sections"][1]["tempo_start"]==83
                    if file=="form.sm":
                        assert structured.rstrip() in result["text"] and "set conductor=" in result["text"]
                    # Verify the inheritance controls really remove an override.
                    page.get_by_role("status").filter(has_text="Applied to the score").wait_for()
                    page.get_by_label("Tempo behavior",exact=True).select_option("inherit")
                    with page.expect_response(lambda r:r.url.endswith("/api/op")) as pending:
                        page.get_by_role("button",name="Apply to score",exact=True).click()
                    assert pending.value.json()["check"]["summary"]["sections"][1]["tempo_override"] is None
                    page.on("dialog",lambda d:d.accept())
                browser.close()
            assert not errors,errors
            # Invalid edit is the one deliberate 400.
            failures=[r for r in responses if r[1]>=400 and "/favicon" not in r[0]]
            assert len(failures)==1 and failures[0][0].endswith("/api/op"),failures
            report={"checks":["mixed and additive meter", "constant and ramp tempo", "tonic and scale edits",
                              "exact ramp playhead BPM and bar/beat", "clickable conductor lanes", "unsaved until Save",
                              "invalid edit preserves score", "defaults preserve overrides", "YAML editing",
                              "repeated-form instance editing", "reset to inherited defaults"],
                    "browser_errors":errors,"fixture_only":True,"screenshot":"conductor-studio.png"}
            (out/"verification.json").write_text(json.dumps(report,indent=2))
            print(json.dumps(report))
        finally:
            application.should_exit=True; thread.join(timeout=15); sock.close()


if __name__=="__main__":
    main()
