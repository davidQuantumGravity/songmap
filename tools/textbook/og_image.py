"""Render the social-preview image (Open Graph / Twitter card): the book cover at 1200 x 630.

    python tools/textbook/og_image.py        # -> tools/textbook/assets/og-cover.png (copied into the site by build.py)

Uses the cover art of build.py and Playwright with the installed Chrome (or Edge). Rerun only when the title or cover
changes; the PNG is committed.
"""
from __future__ import annotations

import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as B  # noqa: E402

OUT = os.path.join(B.ASSETS, "og-cover.png")
W, H = 1200, 630


def page(toc) -> str:
    t, sub, au = (html.escape(toc.get(k, "")) for k in ("title", "subtitle", "author"))
    return f"""<!doctype html><html><head><meta charset="utf-8">{B.FONTS}
<style>
html, body {{ margin: 0; width: {W}px; height: {H}px; overflow: hidden; background: #0c0b09; }}
.card {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; }}
.card svg {{ position: absolute; right: -60px; top: -40px; width: 760px; height: 720px; }}
.cv-sq {{ fill: none; stroke: #e3b54a; stroke-opacity: .22; stroke-width: 1.2; }}
.cv-spiral {{ fill: none; stroke: #f0c75e; stroke-width: 3.2; stroke-linecap: round; filter: drop-shadow(0 0 6px rgba(240,199,94,.55)); }}
.cv-ring {{ fill: none; stroke: #f3ead2; stroke-opacity: .25; stroke-width: 1.2; }}
.cv-dot.l0 {{ fill: #c9d3dd; }} .cv-dot.l1 {{ fill: #f0b543; }} .cv-dot.l2 {{ fill: #6cc9e6; }}
.cv-tri {{ fill-opacity: .10; stroke-width: 1.6; stroke-opacity: .85; }}
.cv-tri.l0 {{ fill: #c9d3dd; stroke: #c9d3dd; }} .cv-tri.l1 {{ fill: #f0b543; stroke: #f0b543; }} .cv-tri.l2 {{ fill: #6cc9e6; stroke: #6cc9e6; }}
.shade {{ position: absolute; inset: 0; background: linear-gradient(90deg, rgba(12,11,9,.96) 0%, rgba(12,11,9,.82) 48%, rgba(12,11,9,.15) 78%); }}
.text {{ position: absolute; left: 72px; top: 0; bottom: 0; width: 640px; display: flex; flex-direction: column; justify-content: center; }}
.k {{ font: 600 17px Inter, sans-serif; letter-spacing: .22em; text-transform: uppercase; color: #e3b54a; margin: 0 0 18px; }}
h1 {{ font: 700 76px/1.02 Fraunces, Georgia, serif; letter-spacing: -.02em; margin: 0 0 22px;
  background: linear-gradient(100deg, #fff4d6, #f0c75e 45%, #c98b1a); -webkit-background-clip: text; background-clip: text; color: transparent; }}
.s {{ font: italic 25px/1.4 "Source Serif 4", Georgia, serif; color: #e9dfc6; margin: 0 0 28px; }}
.a {{ font: 600 26px Fraunces, Georgia, serif; color: #fff; margin: 0; }}
</style></head><body><div class="card">{B.cover_art()}<div class="shade"></div>
<div class="text"><p class="k">A textbook</p><h1>{t}</h1><p class="s">{sub}</p><p class="a">{au}</p></div></div></body></html>"""


def main():
    from playwright.sync_api import sync_playwright
    toc, _ = B.load_toc()
    src = os.path.join(B.ROOT, "build", "og_cover.html")
    os.makedirs(os.path.dirname(src), exist_ok=True)
    with open(src, "w", encoding="utf-8") as f:
        f.write(page(toc))
    with sync_playwright() as p:
        browser = None
        for ch in ("chrome", "msedge"):
            try:
                browser = p.chromium.launch(channel=ch)
                break
            except Exception:                                          # noqa: BLE001
                continue
        browser = browser or p.chromium.launch()
        pg = browser.new_page(viewport={"width": W, "height": H})
        pg.goto("file:///" + os.path.abspath(src).replace("\\", "/"), wait_until="networkidle")
        pg.evaluate("document.fonts.ready")
        pg.screenshot(path=OUT, clip={"x": 0, "y": 0, "width": W, "height": H})
        browser.close()
    print(f"wrote {OUT} ({os.path.getsize(OUT) // 1024} KB)")


if __name__ == "__main__":
    main()
