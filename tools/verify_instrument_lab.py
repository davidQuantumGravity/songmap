"""Verify AI Lab's take identities, feedback submission, media and browser controls.

No taste votes or song edits are submitted. Requires the textbook Playwright extra.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import http.client
import time
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlparse, parse_qs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8866")
    parser.add_argument("--session", required=True)
    parser.add_argument("--out", default=".songmap/instrument-lab")
    args = parser.parse_args()
    root = args.url.rstrip("/")
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    def get(path):
        for attempt in range(3):
            try:
                with urlopen(root + path, timeout=90) as response:
                    return response.read()
            except (ConnectionError, http.client.IncompleteRead):
                if attempt == 2:
                    raise
                time.sleep(.3)
    session = json.loads(get(f"/api/lab/sessions/{args.session}"))
    candidates = [next(c for c in session["candidates"] if c["id"] == cid) for cid in session["pair"]]
    assert len(candidates) == 2 and session["status"] == "ready", session.get("error")
    media = []
    for candidate in candidates:
        for mode in ("solo", "context", "focus"):
            data = get(candidate["audio"][mode])
            assert data[:4] == b"RIFF" and len(data) > 48000
            media.append({"candidate": candidate["id"], "mode": mode, "bytes": len(data)})
    inventory = json.loads(get("/api/lab/inventory"))
    rows = list(csv.DictReader(io.StringIO(get("/api/lab/inventory.csv").decode("utf-8-sig"))))
    assert len(rows) == len(inventory["occurrences"])
    from playwright.sync_api import sync_playwright
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True, args=[
            "--disk-cache-size=1048576", "--media-cache-size=1048576", "--disable-gpu-shader-disk-cache"])
        page = browser.new_page(viewport={"width":1440,"height":1000})
        page.on("pageerror", lambda e: errors.append(str(e)))
        # A creator may be voting/generating in another tab during QA. Freeze only
        # this test client's session snapshot; audio and inventory remain real.
        page.route(f"**/api/lab/sessions/{args.session}", lambda route: route.fulfill(
            status=200, content_type="application/json", body=json.dumps(session)))
        # Hold the map indefinitely: saved comparisons must open independently.
        held_inventory = []
        page.route("**/api/lab/inventory", lambda route: held_inventory.append(route))
        page.goto(f"{root}/?lab=1&comparison={args.session}")
        play_b = f"Play B · Take {candidates[1]['take']}"
        play_a = f"Play A · Take {candidates[0]['take']}"
        page.get_by_role("button", name=play_b, exact=True).wait_for(timeout=8000)
        assert held_inventory
        assert page.get_by_role("button", name=play_b, exact=True).is_enabled()
        assert page.get_by_label("Saved comparisons").locator("option").count() > 1
        page.get_by_label("Listening feedback").fill("Draft survives the map loading")
        held_inventory[0].fulfill(status=200, content_type="application/json", body=json.dumps(inventory))
        page.unroute("**/api/lab/inventory")
        assert page.locator(".lab-workspace-header h2").is_visible()
        assert page.get_by_label("Listening context").input_value() == "solo"
        assert candidates[1]["display_name"] in page.locator("article.active").inner_text()
        page.get_by_role("button", name="＋ New comparison", exact=True).click()
        page.get_by_label("Comparison type").select_option("instrument")
        page.get_by_label("Find instrument or song").fill(session["use"])
        assert page.get_by_label("Listening feedback").input_value() == "Draft survives the map loading"
        piece = session["piece"] if session["piece"] is not None else "null"
        assert page.get_by_label("Song and part").input_value() == f"{session['path']}|{session['part']}|{piece}"
        page.get_by_role("button", name="Close panel", exact=True).click()
        page.get_by_role("button", name=play_b, exact=True).click()
        page.wait_for_function("parseFloat(document.querySelector('.lab-clock').textContent) > 0.8")
        page.get_by_role("button", name=f"A · Take {candidates[0]['take']}", exact=True).click()
        page.get_by_role("button", name=play_a.replace("Play", "Pause"), exact=True).wait_for()
        assert float(page.locator(".lab-clock").inner_text().split("/")[0]) > .5
        page.get_by_role("button", name=play_a.replace("Play", "Pause"), exact=True).click()
        # A failed refresh must keep the current pair and unsent text usable.
        page.route("**/api/lab/inventory?refresh=true", lambda route: route.fulfill(
            status=503, content_type="application/json", body=json.dumps({"detail":"QA unavailable map"})))
        page.get_by_role("button", name="＋ New comparison", exact=True).click()
        page.get_by_role("button", name="Refresh inventory", exact=True).click()
        page.get_by_role("button", name="Retry instrument map", exact=True).wait_for()
        assert page.locator(".lab-play").is_enabled()
        assert page.get_by_label("Listening feedback").input_value() == "Draft survives the map loading"
        page.get_by_role("button", name="Retry instrument map", exact=True).click()
        page.get_by_role("button", name="Retry instrument map", exact=True).wait_for(state="detached")
        page.get_by_role("button", name="Close panel", exact=True).click()
        page.get_by_label("Listening context").select_option("context")
        page.get_by_role("button", name=play_a, exact=True).wait_for()
        assert "Full mix" in page.locator(".lab-transport-options").inner_text()
        sent = []
        def capture(route):
            sent.append(route.request.post_data_json)
            route.fulfill(status=200, content_type="application/json", body=json.dumps(session))
        endpoint = f"**/api/lab/sessions/{args.session}/generate"
        page.route(endpoint, capture)
        page.get_by_label("Listening feedback").fill("QA unsent draft: preserve the attack")
        page.get_by_role("button", name="Try another", exact=True).click()
        page.wait_for_function("document.querySelector('[aria-label=\"Listening feedback\"]').value === ''")
        assert sent and sent[0]["feedback"]["text"] == "QA unsent draft: preserve the attack"
        assert sent[0]["feedback"]["mode"] == "context"
        page.unroute(endpoint)
        page.get_by_label("Listening context").select_option("solo")
        page.get_by_role("button", name=f"B · Take {candidates[1]['take']}", exact=True).click()
        page.locator(".lab-workspace").evaluate("el => el.scrollTop = 0")
        page.screenshot(path=str(out / "ai-lab-desktop.png"))
        page.set_viewport_size({"width":390,"height":844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(out / "ai-lab-mobile.png"))
        # Opening from a song offers its actual instruments and visible resumes.
        landing = browser.new_page(viewport={"width":1440,"height":1000})
        landing.goto(f"{root}/?lab=1&song=songs%2Fgolden%2F04_andalusian_gold.sm")
        landing.get_by_role("button", name="＋ New comparison", exact=True).click()
        landing.get_by_role("button", name="Refresh inventory", exact=True).wait_for()
        landing.locator(".lab-current").wait_for()
        assert landing.get_by_label("Inventory scope").input_value() == "current", {
            "scope":landing.get_by_label("Inventory scope").input_value(), "url":landing.url,
            "context":landing.locator(".instrument-lab").inner_text()[:1800]}
        assert landing.locator(".lab-nav button").count() > 2
        assert "04_andalusian_gold.sm" in landing.locator(".lab-current").inner_text()
        assert parse_qs(urlparse(landing.url).query).get("lab") == ["1"]
        landing.screenshot(path=str(out / "ai-lab-start.png"))
        landing.close()
        # An unavailable map on first entry still allows a saved session to open.
        recovery = browser.new_page(viewport={"width":1440,"height":1000})
        recovery.route("**/api/lab/inventory", lambda route: route.fulfill(
            status=503, content_type="application/json", body=json.dumps({"detail":"QA unavailable map"})))
        recovery.route(f"**/api/lab/sessions/{args.session}", lambda route: route.fulfill(
            status=200, content_type="application/json", body=json.dumps(session)))
        recovery.goto(f"{root}/?lab=1")
        recovery.get_by_role("button", name="＋ New comparison", exact=True).click()
        recovery.get_by_role("button", name="Retry instrument map", exact=True).wait_for()
        recovery.get_by_role("button", name="Close panel", exact=True).click()
        recovery.get_by_label("Saved comparisons").select_option(args.session)
        recovery.get_by_role("button", name=play_b, exact=True).wait_for(timeout=8000)
        assert recovery.get_by_role("button", name=play_b, exact=True).is_enabled()
        browser.close()
    assert not errors, errors
    report = {"source_files":len(inventory["sources"]),"played_voices":len(inventory["instruments"]),
              "source_errors":inventory["errors"],"csv_rows":len(rows),"media":media,
              "browser_errors":errors,"checks":["durable WAV media","CSV map","saved comparison before map","draft survives map load","failed refresh preserves playback and draft","current-song start and saved resumes","lab link survives song opening","saved resume despite initial map failure","stable take labels","new challenger selected","A/B position continuity","solo/context","unsent feedback submitted","mobile width"]}
    (out / "verification.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in {"source_errors","media"}}))


if __name__ == "__main__":
    main()
