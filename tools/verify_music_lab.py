"""Exercise musical comparison controls against Studio without voting or applying.

Creates riff/arrangement audition sessions when --create is supplied. Saved score
files and human feedback are never changed. Screenshots and receipts stay local.
"""
from __future__ import annotations

import argparse
import http.client
import json
import time
from pathlib import Path
from urllib.request import urlopen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8865")
    ap.add_argument("--session", required=True)
    ap.add_argument("--create", action="store_true")
    args = ap.parse_args()
    root = args.url.rstrip("/")
    out = Path(".songmap/instrument-lab/music-browser-qa")
    out.mkdir(parents=True, exist_ok=True)
    def get(path):
        for attempt in range(3):
            try:
                with urlopen(root + path, timeout=60) as r:
                    return json.load(r)
            except (ConnectionError, http.client.IncompleteRead):
                if attempt == 2:
                    raise
                time.sleep(.3)
    session = get(f"/api/lab/sessions/{args.session}")
    deadline = time.time() + 90
    while session["status"] in {"queued", "rendering"} and time.time() < deadline:
        time.sleep(.5)
        session = get(f"/api/lab/sessions/{args.session}")
    assert session["status"] == "ready", session.get("error")
    pair = [next(c for c in session["candidates"] if c["id"] == cid) for cid in session["pair"]]
    assert [c["excerpt"]["start"] for c in pair] == [0, 27]
    for c in pair:
        with urlopen(root + c["audio"]["context"], timeout=60) as r:
            assert r.read(4) == b"RIFF"
    from playwright.sync_api import sync_playwright, expect
    errors, created = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True, args=[
            "--disk-cache-size=1048576", "--media-cache-size=1048576", "--disable-gpu-shader-disk-cache"])
        page = browser.new_page(viewport={"width":1440,"height":1000})
        page.on("pageerror", lambda e: errors.append(str(e)))
        url = f"{root}/?lab=1&comparison={args.session}"
        # Resume must work before inventory completes.
        held = []
        page.route("**/api/lab/inventory", lambda route: held.append(route))
        page.goto(url)
        play = page.get_by_role("button", name="Play B · Take 2", exact=True)
        expect(play).to_be_enabled(timeout=20000)
        expect(page.get_by_label("Listening context")).to_have_value("context")
        expect(page.locator(".lab-excerpt").nth(1)).to_contain_text("27.0–51.0s")
        expect(page.get_by_role("button", name="Develop favorite · Take 2", exact=True)).to_be_enabled()
        assert page.get_by_text("Apply the current favorite to saved scores", exact=True).count() == 0
        play.click()
        page.wait_for_timeout(700)
        expect(page.get_by_role("button", name="Pause B · Take 2", exact=True)).to_be_visible()
        slider = page.get_by_label("Comparison position")
        slider.fill("5")
        page.get_by_role("button", name="A · Take 1", exact=True).click()
        expect(page.get_by_role("button", name="Pause A · Take 1", exact=True)).to_be_visible()
        assert 4.9 <= float(slider.input_value()) < 7
        page.get_by_role("button", name="Pause A · Take 1", exact=True).click()
        feedback = page.get_by_label("Listening feedback")
        feedback.fill("QA unsent draft: keep the forward motion")
        for route in held:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(get("/api/lab/inventory")))
        page.unroute("**/api/lab/inventory")
        expect(feedback).to_have_value("QA unsent draft: keep the forward motion")
        page.get_by_role("button", name="＋ New comparison", exact=True).click()
        page.get_by_label("Comparison type").select_option("riff")
        expect(page.get_by_role("heading", name="New riff comparison")).to_be_visible()
        page.get_by_label("Comparison type").select_option("arrangement")
        expect(page.get_by_role("heading", name="New arrangement comparison")).to_be_visible()
        page.get_by_label("Comparison type").select_option("instrument")
        expect(page.get_by_role("button", name="Start instrument comparison")).to_be_visible(timeout=10000)
        page.get_by_label("Comparison type").select_option("snippet")
        expect(page.get_by_label("B source score")).to_be_visible()
        page.get_by_role("button", name="Close panel", exact=True).click()
        page.locator(".lab-workspace").screenshot(path=str(out / "snippet-desktop.png"))
        if args.create:
            source = session["path"]
            # Exercise real form creation, score validation and asynchronous renders.
            for scope in ("riff", "arrangement"):
                page.get_by_role("button", name="＋ New comparison", exact=True).click()
                page.get_by_label("Comparison type").select_option(scope)
                page.get_by_label("Source score", exact=True).select_option(source)
                if scope == "riff":
                    page.get_by_label("Riff part").select_option("melody")
                page.get_by_label("Audition passage first bar").select_option("0")
                page.get_by_label("Audition passage last bar").select_option("0")
                page.get_by_label("Musical direction").fill("Browser QA of saved musical alternatives; no taste judgment")
                old_url = page.url
                page.get_by_role("button", name=f"Start {scope} comparison", exact=True).click()
                page.wait_for_url(lambda u: str(u) != old_url, timeout=20000)
                expect(page.locator(".lab-eyebrow")).to_contain_text(scope.upper())
                page.get_by_role("button", name="Details", exact=True).click()
                editor = page.get_by_label("Challenger score")
                summary = page.get_by_text("Write a musical challenger", exact=True)
                if not summary.evaluate("el => el.parentElement.open"):
                    summary.click()
                expect(editor).to_be_visible()
                expect(editor).not_to_have_value("", timeout=15000)
                base = editor.input_value()
                if scope == "riff":
                    changed = base.replace("A_long_arch 8 | melody:melody_a", "A_long_arch 8 | melody:melody_b")
                else:
                    changed = base.replace("mix melody -3 ", "mix melody -6 ")
                assert base != changed
                editor.fill(changed)
                page.get_by_label("Musical take label").fill(f"QA {scope} alternative")
                button = page.get_by_role("button", name="Add and render musical challenger")
                expect(button).to_be_enabled(timeout=60000)
                button.click()
                page.get_by_role("button", name="Close panel", exact=True).click()
                play_b = page.get_by_role("button", name="Play B · Take 2", exact=True)
                expect(play_b).to_be_enabled(timeout=60000)
                play_b.click()
                expect(page.get_by_role("button", name="Pause B · Take 2", exact=True)).to_be_visible()
                page.get_by_role("button", name="Pause B · Take 2", exact=True).click()
                sid = page.url.split("comparison=")[-1].split("&")[0]
                saved = get(f"/api/lab/sessions/{sid}")
                assert saved["scope"] == scope and len(saved["pair"]) == 2
                assert not saved["feedback"] and not saved["applied"]
                assert page.get_by_label("Listening context").input_value() == ("solo" if scope == "riff" else "context")
                created.append({"scope":scope,"id":sid})
        page.goto(url)
        expect(page.get_by_role("button", name="Play B · Take 2", exact=True)).to_be_enabled(timeout=20000)
        page.set_viewport_size({"width":390,"height":844})
        page.locator(".lab-workspace").scroll_into_view_if_needed()
        page.screenshot(path=str(out / "snippet-mobile.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not errors, errors
        browser.close()
    receipt = {"session":args.session,"source_offsets":[0,27],"seconds":session["seconds"],
               "playback_switch_preserves_position":True,"resume_without_inventory":True,
               "scope_forms":4,"created_and_rendered":created,"mobile_width":390,
               "taste_votes_submitted":0,"scores_applied":0,"browser_errors":errors}
    (out / "verification.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
