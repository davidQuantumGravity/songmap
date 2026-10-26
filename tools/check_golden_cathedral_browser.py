"""Real-browser playback, note display, seeking, version switching and mobile QA."""
from pathlib import Path
import json
import hashlib
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:56855/songs/golden_cathedral/"
OUT = ROOT / "build/golden_cathedral_browser"
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel="msedge", headless=True, args=["--mute-audio"])
    page = browser.new_page(viewport={"width": 1440, "height": 1080})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    response = page.goto(BASE, wait_until="networkidle")
    assert response.status == 200
    page.wait_for_function("document.querySelector('#status').textContent.startsWith('Ready')")
    audio = page.locator("audio")
    page.wait_for_function("document.querySelector('audio').duration > 299")
    assert abs(audio.evaluate("a=>a.duration") - 300) < .1
    assert page.locator(".card").count() == 6
    page.locator('[data-time="80"]').click()
    page.wait_for_function("document.querySelector('audio').currentTime>81 && !document.querySelector('audio').seeking")
    audio.evaluate("a=>a.pause()")
    assert page.locator("#section").inner_text() == "First Ninth"
    assert "Golden ninth" in page.locator("#chord").inner_text()
    assert page.locator(".pair").count() == 5
    assert page.locator(".pair").evaluate_all("pp=>pp.every(p=>Math.abs(+p.dataset.difference*32-+p.dataset.center)<1e-8)")
    assert page.locator(".card.sounding").count() >= 3
    before = audio.evaluate("a=>a.currentTime")
    for version in ("binaural_pairs", "music_only", "song"):
        page.locator(f'[data-version="{version}"]').click()
        page.wait_for_function("([v,t])=>document.querySelector('audio').currentSrc.split('?')[0].endsWith('/'+v+'.mp3') && Math.abs(document.querySelector('audio').currentTime-t)<.1", arg=[version, before])
        assert audio.evaluate("a=>a.paused")
    page.locator('[data-time="240"]').click()
    page.wait_for_function("document.querySelector('audio').currentTime>240")
    audio.evaluate("a=>{a.pause();a.currentTime=244.3;}")
    page.wait_for_function("document.querySelector('#section').textContent==='Empyrean'")
    page.wait_for_function("!document.querySelector('audio').seeking")
    assert "C6" in page.locator("#instruments").inner_text()
    assert page.locator(".pair").count() == 5
    assert page.locator(".pair").evaluate_all("pp=>pp.every(p=>Math.abs(+p.dataset.difference*32-+p.dataset.center)<1e-8)")
    page.locator(".board").scroll_into_view_if_needed()
    page.screenshot(path=str(OUT / "performance_desktop.png"))
    page.evaluate("scrollTo(0,0)")
    page.screenshot(path=str(OUT / "player_desktop.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
    page.locator(".board").scroll_into_view_if_needed()
    page.screenshot(path=str(OUT / "performance_mobile.png"), full_page=True)
    page.locator('[data-time="272"]').click()
    page.wait_for_function("document.querySelector('#section').textContent==='Return To Silence'")
    audio.evaluate("a=>a.pause()")
    assert not errors, errors
    browser.close()

for filename in ("song", "music_only", "binaural_pairs"):
    with urlopen(Request(BASE + f"renders/as_above_so_below/{filename}.mp3", headers={"Range": "bytes=128-255"})) as response:
        assert response.status == 206 and len(response.read()) == 128
with urlopen("http://127.0.0.1:56855/textbook_site/chapters/songbook.html") as response:
    songbook = response.read().decode("utf-8")
    assert 'id="songs-golden-cathedral"' in songbook
    assert "Open the synchronized player" in songbook
collection = ROOT / "songs/golden_cathedral"
receipt = {"url": BASE, "seconds": 300, "instrument_cards": 6, "ninth_pairs": 5,
           "displayed_difference_is_center_divided_by_32": True,
           "versions": 3, "version_switch_preserves_time_and_pause": True,
           "mp3_byte_ranges": True, "landmark_seeking": True,
           "mobile_overflow": False, "page_errors": errors, "songbook_entry": True,
           "score_sha256": hashlib.sha256((collection / "as_above_so_below.sm").read_bytes()).hexdigest(),
           "page_sha256": hashlib.sha256((collection / "index.html").read_bytes()).hexdigest()}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
(collection / "browser_verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
