"""Print the whole textbook as one PDF: cover, front pages, contents with page numbers, every part and chapter.

    python tools/textbook/pdf.py                  # -> textbook_site/Music_Theory_of_Golden_Harmony.pdf
    python tools/textbook/pdf.py --chapters ch01 ch23 --out build/sample.pdf

Run tools/textbook/build.py first: the PDF uses its rendered video posters. Videos become their poster frame with
the caption and a link to the page online; audio-only examples are marked as such. All three layers are printed.
Printing uses Playwright with the installed Chrome (or Edge): page-number footers, internal links and a bookmark
outline. Two passes: the first finds the page of every chapter, the second writes the numbers into the contents.
"""
from __future__ import annotations

import argparse
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as B  # noqa: E402

PRINT_DIR = os.path.join(B.OUT, "print")
MARK = "§§{}§§"                                   # invisible page marker per chapter (found again in pass 1)

PRINT_CSS = """
@page { size: 7.5in 10in; margin: 0.75in 0.7in 0.8in; }
html, body { background: #fff !important; }
body { font-size: 10.6pt; line-height: 1.5; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
header.top, aside.side, .progress, .totop, .onpage, .pn, .layers, .cv-open { display: none !important; }
.wrap { display: block; } main { max-width: none; padding: 0; }
.mark { font-size: 1px; color: #fff; line-height: 0; height: 0; overflow: hidden; }
body.cover-only, body.cover-only main { margin: 0; padding: 0; }
.book-cover { break-after: page; width: 7.5in; height: 10in; min-height: 0; margin: 0; border-radius: 0; box-shadow: none; }
.cover-art { position: absolute; }
.book-sheet { break-after: page; border: 0; box-shadow: none; background: none; min-height: 8.2in; display: flex;
  flex-direction: column; justify-content: center; }
.copyright-page { justify-content: flex-end; }
.contents-print { break-after: page; border: 0 !important; background: none !important; padding: 0 !important; }
.contents-print h2 { border: 0; font-size: 26pt; margin: 0 0 14pt; }
.toc-part { font: 600 10.5pt var(--ui); text-transform: uppercase; letter-spacing: .06em; color: var(--pc-ink); margin: 12pt 0 4pt; break-after: avoid; }
.toc-line { display: flex; align-items: baseline; gap: 6pt; font-size: 10.5pt; margin: 2pt 0; }
.toc-line a { color: var(--fg); text-decoration: none; }
.toc-line .dots { flex: 1; border-bottom: 1px dotted #b7ad9c; transform: translateY(-3pt); }
.toc-line .pg { font-variant-numeric: tabular-nums; min-width: 22pt; text-align: right; color: var(--muted); }
.part-page { break-before: page; break-after: page; min-height: 8.2in; display: flex; flex-direction: column; justify-content: center;
  border-radius: 0; padding: 0 0.3in; background: linear-gradient(160deg, var(--pc-soft2), #fff 70%); }
.part-page .chip { font-size: 10pt; } .part-page h1 { font-size: 34pt; margin: 14pt 0 10pt; }
.part-page p { font: italic 13pt/1.5 var(--serif); color: var(--muted); max-width: 4.8in; }
.chapter { break-before: page; }
.hero { box-shadow: none; break-inside: avoid; grid-template-columns: 1fr 110px; padding: 18pt 20pt; }
h1 { font-size: 26pt; } h2 { font-size: 17pt; break-after: avoid; } h3 { font-size: 13pt; break-after: avoid; }
main > section:not(.partcard):not(.book-cover):not(.book-sheet) { box-shadow: none; padding: 2pt 14pt 10pt; border-radius: 12pt; margin: 14pt 0; }
aside, figure, table, pre, .katex-display, .tile { break-inside: avoid; }
.layer, .exercise { break-inside: auto; }
.layer::before { break-after: avoid; }
figure.print-media img { display: block; width: 100%; border-radius: 8pt; border: 1px solid var(--line); }
figure.print-media figcaption .online, .audio-only { font: 600 8pt var(--ui); color: var(--muted); }
.audio-only { display: inline-block; border: 1px solid var(--line); border-radius: 99px; padding: 1pt 7pt; margin-bottom: 3pt; }
a { color: inherit; text-decoration: none; } a.xref { color: var(--accent2); }
table { display: table; font-size: 9pt; } .fig { max-width: 100%; }
"""


def _ids(chid: str, frag: str) -> str:
    """Make ids unique across the book: id="x" -> id="chid--x"; local #x links follow."""
    frag = re.sub(r'\bid="([\w-]+)"', lambda m: f'id="{chid}--{m[1]}"', frag)
    frag = re.sub(r'href="#([\w-]+)"', lambda m: f'href="#{chid}--{m[1]}"', frag)
    frag = re.sub(r'url\(#([\w-]+)\)', lambda m: f'url(#{chid}--{m[1]})', frag)          # SVG gradients, markers
    return frag


def _links(frag: str) -> str:
    """Chapter links of the site (chXX.html#sec, ../chapters/chXX.html) become links inside the PDF."""
    def sub(m):
        ch, sec = m[1], m[2]
        return f'class="xref" href="#{ch}--{sec}"' if sec else f'class="xref" href="#{ch}"'
    return re.sub(r'href="(?:\.\./chapters/)?([\w-]+)\.html(?:#([\w-]+))?"', sub, frag)


def _media(chid: str, frag: str) -> str:
    def video(m):
        poster, cap = m[1], m[2]
        img = poster if os.path.exists(os.path.join(PRINT_DIR, poster)) else None
        body = (f'<img src="{img}" alt="">' if img else '<div class="audio-only">Video example</div>')
        cap = re.sub(r'\s*<a class="mp3"[^>]*>MP3</a>', "", cap)
        return (f'<figure class="audio print-media">{body}<figcaption>{cap} '
                f'<span class="online">▶ video online</span></figcaption></figure>')
    frag = re.sub(r'<figure class="audio video"><video[^>]*poster="([^"]+)"[^>]*></video><figcaption>(.*?)</figcaption></figure>',
                  video, frag, flags=re.S)
    frag = re.sub(r'<div class="player"><span class="ico">[^<]*</span><audio[^>]*></audio></div>',
                  '<div class="audio-only">♪ Audio example: listen online</div>', frag)
    return frag


def _chapter_html(ch, frag, chapters, idx) -> str:
    body = B.chapter_body(ch, frag, chapters, idx)
    body = re.sub(r'<nav class="onpage".*?</nav>', "", body, flags=re.S)
    body = re.sub(r'<nav class="pn">.*?</nav>', "", body, flags=re.S)
    body = _media(ch["id"], _links(_ids(ch["id"], body))).replace('<details class="answer">', '<details class="answer" open>')
    return (f'<article class="chapter" id="{ch["id"]}" data-part="{ch["part"]["id"]}">'
            f'<span class="mark">{MARK.format(ch["id"])}</span>{body}</article>')


def _contents(toc, chapters, pages) -> str:
    out = ['<section class="contents-print"><h2>Contents</h2>']
    for part in toc["parts"]:
        chip, name = B.part_bits(part)
        out.append(f'<div class="toc-part" data-part="{part["id"]}">{html.escape(chip + (". " + name if name else ""))}</div>')
        for c in part["chapters"]:
            if c["id"] not in pages:
                continue
            n = B.chap_num(c)[0]
            if n and c["title"].startswith(n + "."):           # appendix titles carry their letter already
                n = ""
            out.append(f'<div class="toc-line"><a href="#{c["id"]}">{(n + "  ") if n else ""}{html.escape(c["title"])}</a>'
                       f'<span class="dots"></span><span class="pg">{pages.get(c["id"]) or "000"}</span></div>')
    out.append("</section>")
    return "".join(out)


def _part_page(part) -> str:
    chip, name = B.part_bits(part)
    return (f'<section class="part-page" data-part="{part["id"]}"><span class="chip">{html.escape(chip)}</span>'
            f'<h1>{html.escape(name or part["title"])}</h1><p>{html.escape(part.get("summary", ""))}</p></section>')


COVER_CSS = "@page { size: 7.5in 10in; margin: 0; } html, body { margin: 0; background: #0c0b09; }"


def _front(toc) -> tuple[str, str]:
    """(cover, the other front pages)."""
    f = B.front_pages(toc)
    i = f.index("</section>") + len("</section>")
    return f[:i], f[i:]


def cover_page(toc, chapters) -> str:
    page = B.page(toc["title"], _front(toc)[0], toc, chapters, None, "../", layers=False)
    page = page.replace("<body ", '<body class="cover-only" ', 1)
    return page.replace("</head>", f"<style>{PRINT_CSS}{COVER_CSS}</style></head>", 1)


def assemble(toc, chapters, wanted, pages) -> str:
    problems, jobs, alist = [], [], []
    ids = {c["id"] for c in chapters}
    sec_ids = {c["id"]: {s["id"] for s in c.get("sections", [])} for c in chapters}
    frags = {}
    for idx, ch in enumerate(chapters):
        if wanted and ch["id"] not in wanted:
            continue
        path = os.path.join(B.CONTENT, ch["id"] + ".html")
        frag = open(path, encoding="utf-8").read() if os.path.exists(path) else B.placeholder(ch)
        frags[ch["id"]] = (idx, ch, B.process(ch["id"], frag, ids, sec_ids, problems, jobs, alist))
    rendered = B.render_tex([(t, d) for _, _, f in frags.values() for _, _, t, d in B.find_math(f)])
    if rendered is None:
        raise SystemExit("node/KaTeX unavailable: cd tools/textbook && npm install")
    for cid, (idx, ch, f) in list(frags.items()):
        frags[cid] = (idx, ch, B.apply_math(cid, f, rendered, problems))
    parts_seen, body = set(), [_front(toc)[1],
                               '<span id="toc"></span>', _contents(toc, chapters, pages or {c: None for c in frags})]
    for cid, (idx, ch, f) in frags.items():
        pid = ch["part"]["id"]
        if pid not in parts_seen and pid not in ("front", "appendices"):
            body.append(_part_page(ch["part"]))
        parts_seen.add(pid)
        if cid == "appG":
            f = f + "<p class='audio-only'>The audio index with players is online.</p>"
        body.append(_chapter_html(ch, f, chapters, idx))
    page = B.page(toc["title"], "".join(body), toc, chapters, None, "../", layers=False)
    page = page.replace("<html lang=\"en\">", "<html lang=\"en\" data-theme=\"light\">", 1)
    page = page.replace("</head>", f"<style>{PRINT_CSS}</style></head>", 1)
    for p in problems:
        print("PROBLEM", p)
    return page


def _print(src_html: str, out_pdf: str, title: str, footer_on: bool = True):
    from playwright.sync_api import sync_playwright
    footer = ('<div style="width:100%;font:8px Inter,Segoe UI,sans-serif;color:#8a8273;padding:0 0.7in;'
              'display:flex;justify-content:space-between"><span>' + html.escape(title) +
              '</span><span class="pageNumber"></span></div>')
    with sync_playwright() as p:
        browser = None
        for ch in ("chrome", "msedge"):
            try:
                browser = p.chromium.launch(channel=ch)
                break
            except Exception:                                          # noqa: BLE001
                continue
        if browser is None:
            browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("file:///" + os.path.abspath(src_html).replace("\\", "/"), wait_until="networkidle", timeout=180000)
        page.emulate_media(media="print")
        page.evaluate("document.fonts.ready")
        page.pdf(path=out_pdf, width="7.5in", height="10in", print_background=True, display_header_footer=footer_on,
                 header_template="<span></span>", footer_template=footer, prefer_css_page_size=True,
                 outline=True, tagged=True)
        browser.close()


def _chapter_pages(pdf_path: str, ids) -> dict:
    try:
        from pypdf import PdfReader
    except ImportError:
        return {}
    pages = {}
    for i, pg in enumerate(PdfReader(pdf_path).pages):
        text = pg.extract_text() or ""
        for cid in ids:
            if cid not in pages and MARK.format(cid) in text:
                pages[cid] = i + 1                      # the footer numbers the pages after the cover from 1
    return pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapters", nargs="*", help="only these chapter ids (default: the whole book)")
    ap.add_argument("--out", default=os.path.join(B.OUT, "Music_Theory_of_Golden_Harmony.pdf"))
    args = ap.parse_args()
    toc, chapters = B.load_toc()
    os.makedirs(PRINT_DIR, exist_ok=True)
    src = os.path.join(PRINT_DIR, "book.html")
    cover_html, cover_pdf, body_pdf = (os.path.join(PRINT_DIR, n) for n in ("cover.html", "cover.pdf", "body.pdf"))
    with open(cover_html, "w", encoding="utf-8") as f:
        f.write(cover_page(toc, chapters))
    _print(cover_html, cover_pdf, toc["title"], footer_on=False)
    # pass 1: lay out, find each chapter's page
    with open(src, "w", encoding="utf-8") as f:
        f.write(assemble(toc, chapters, args.chapters, None))
    _print(src, body_pdf, toc["title"])
    pages = _chapter_pages(body_pdf, [c["id"] for c in chapters])
    if pages:                                           # pass 2: page numbers in the contents
        with open(src, "w", encoding="utf-8") as f:
            f.write(assemble(toc, chapters, args.chapters, pages))
        _print(src, body_pdf, toc["title"])
    from pypdf import PdfReader, PdfWriter
    w = PdfWriter()
    w.append(PdfReader(cover_pdf), import_outline=False)
    w.append(PdfReader(body_pdf))
    w.add_metadata({"/Title": toc["title"], "/Author": toc.get("author", "")})
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "wb") as f:
        w.write(f)
    print(f"wrote {args.out} ({os.path.getsize(args.out) / 1e6:.1f} MB; contents page numbers: {'yes' if pages else 'no'})")


if __name__ == "__main__":
    main()
