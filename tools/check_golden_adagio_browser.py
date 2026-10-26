"""Verify the delivered illustrated player at the real browser/audio boundary."""
from pathlib import Path
import hashlib
import json
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:56855/songs/golden_adagio/"
OUT = ROOT / "build/golden_adagio_browser"
OUT.mkdir(parents=True, exist_ok=True)
collection = ROOT / "songs/golden_adagio"

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel="msedge", headless=True, args=["--mute-audio"])
    page = browser.new_page(viewport={"width": 1440, "height": 1080})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    response = page.goto(BASE, wait_until="networkidle")
    assert response.status == 200
    page.wait_for_function("document.querySelector('#status').textContent.startsWith('Ready')")
    audio = page.locator("audio")
    page.wait_for_function("document.querySelector('audio').duration>299")
    assert abs(audio.evaluate("a=>a.duration") - 300) < .1
    assert page.locator(".card").count() == 8
    page.wait_for_function("[...document.querySelectorAll('.portrait')].every(i=>i.complete&&i.naturalWidth>0)")
    assert page.locator(".portrait").count() == 8
    for t, quality in ((1.0, "Western ninth"), (9.5, "Golden seventh"), (54.5, "Golden ninth")):
        audio.evaluate("(a,t)=>{a.pause();a.currentTime=t;}", t)
        page.wait_for_function("([t,q])=>!document.querySelector('audio').seeking && Math.abs(document.querySelector('audio').currentTime-t)<.1 && document.querySelector('#chord').textContent.includes(q)", arg=[t, quality])
        assert page.locator(".card.sounding").count() >= 3
        assert page.locator(".mini-note.active").count() >= 3
        assert page.locator(".mini-note.active").evaluate_all("nn=>nn.every(n=>n.getBoundingClientRect().width>3)")
        assert page.locator(".pair").count() == (4 if t == 9.5 else 5)
        assert page.locator(".pair").evaluate_all("pp=>pp.every(p=>Math.abs(+p.dataset.difference*32-+p.dataset.center)<1e-8)")
    before = audio.evaluate("a=>a.currentTime")
    for version in ("binaural_pairs", "music_only", "song"):
        page.locator(f'[data-version="{version}"]').click()
        page.wait_for_function("([v,t])=>document.querySelector('audio').currentSrc.split('?')[0].endsWith('/'+v+'.mp3') && Math.abs(document.querySelector('audio').currentTime-t)<.1", arg=[version, before])
        assert audio.evaluate("a=>a.paused")
    page.locator('[data-time="192"]').click()
    page.wait_for_function("document.querySelector('audio').currentTime>192.2 && !document.querySelector('audio').paused")
    # Version switching also preserves a playing transport.
    before = audio.evaluate("a=>a.currentTime")
    page.locator('[data-version="music_only"]').click()
    page.wait_for_function("t=>document.querySelector('audio').currentSrc.split('?')[0].endsWith('/music_only.mp3') && !document.querySelector('audio').paused && document.querySelector('audio').currentTime>=t-.1", arg=before)
    audio.evaluate("a=>a.pause()")
    page.locator('[data-version="song"]').click()
    page.wait_for_function("document.querySelector('audio').currentSrc.split('?')[0].endsWith('/song.mp3')")
    audio.evaluate("a=>{a.pause();a.currentTime=241;}")
    page.wait_for_function("!document.querySelector('audio').seeking && document.querySelector('#section').textContent==='The great arch'")
    assert "D6" in page.locator('[data-part="melody"] .notes').inner_text()
    page.locator(".board").scroll_into_view_if_needed()
    page.screenshot(path=str(OUT / "performance_desktop.png"))
    page.evaluate("scrollTo(0,0)")
    page.screenshot(path=str(OUT / "player_desktop.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
    page.locator(".board").scroll_into_view_if_needed()
    page.screenshot(path=str(OUT / "performance_mobile.png"), full_page=True)
    audio.evaluate("a=>{a.pause();a.currentTime=295;}")
    page.wait_for_function("document.querySelector('#section').textContent==='Afterglow'")
    assert page.locator(".card.sounding").count() == 0
    assert not errors, errors
    browser.close()

for filename in ("song", "music_only", "binaural_pairs"):
    with urlopen(Request(BASE + f"renders/beyond_the_veil/{filename}.mp3", headers={"Range": "bytes=128-255"})) as response:
        assert response.status == 206 and len(response.read()) == 128
with urlopen("http://127.0.0.1:56855/textbook_site/chapters/songbook.html") as response:
    book = response.read().decode("utf-8")
    assert book.count('id="songs-golden-adagio"') == 1
    assert "Open the illustrated synchronized player" in book
    assert "Beyond the Veil" in book and book.count("<audio") >= 78
receipt = {"url": BASE, "seconds": 300, "instrument_cards": 8, "instrument_portraits_loaded": 8,
           "individual_notes_and_bar_timelines": True, "western_and_golden_chord_display": True,
           "displayed_difference_is_center_divided_by_32": True,
           "versions": 3, "switch_preserves_time_and_transport": True, "mp3_byte_ranges": True,
           "landmark_seeking": True, "mobile_overflow": False, "page_errors": errors, "songbook_entry": True,
           "score_sha256": hashlib.sha256((collection / "beyond_the_veil.sm").read_bytes()).hexdigest(),
           "page_sha256": hashlib.sha256((collection / "index.html").read_bytes()).hexdigest()}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
(collection / "browser_verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
