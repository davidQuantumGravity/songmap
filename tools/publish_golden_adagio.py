"""Publish only this collection; preserve other Songbook audio and content."""
from pathlib import Path
import json
import hashlib
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/textbook"))
import songbook

site = ROOT / "textbook_site"
page = site / "chapters/songbook.html"
collection = next(c for c in songbook.collections() if c["id"] == "songs-golden-adagio")
entries = {p: songbook.entry(p) for p in collection["songs"]}
renders = {p: str(ROOT / "songs/golden_adagio/renders" / Path(p).stem) for p in entries}
assert all(not e.get("error") for e in entries.values())
assert all((Path(r) / "song.mp3").exists() for r in renders.values())
assert all(Path(p).resolve() == Path(e["playback_path"]).resolve() for p, e in entries.items()), "Unexpected alternate edition"
media = songbook.publish(entries, renders, str(site))
fragment = songbook.fragment([collection], entries, renders, media)
marker = '<section id="songs-golden-adagio">'
fragment = fragment[fragment.index(marker):]
heading_end = fragment.index("</h2>") + len("</h2>")
fragment = fragment[:heading_end] + '<p><a href="../../songs/golden_adagio/">Open the illustrated synchronized player</a> · Selected theme: B, Forward Lilt.</p>' + fragment[heading_end:]
original = page.read_text(encoding="utf-8")
# Earlier one-collection incremental builds included the generator's global
# introduction again. Keep one introduction and retain their player links near
# the collection that follows, without rebuilding any other song article.
about_count = 0
def deduplicate_about(match):
    global about_count
    about_count += 1
    if about_count == 1:
        return match[0]
    return "\n".join(re.findall(r'<p><a href=.*?</p>', match[0]))
original = re.sub(r'<section id="about">.*?</section>', deduplicate_about, original, flags=re.S)
start = original.index(marker)
end = original.index("</section>", start) + len("</section>")
previous_audio = original[start:end].count("<audio")
updated = original[:start] + fragment + original[end:]
articles = re.findall(r'<article class="song".*?</article>', updated, flags=re.S)
waiting = sum(not re.search(r'<span class="badge"[^>]*>approved</span>', article) for article in articles)
updated = re.sub(r'(?:Every song in the repository, \d+ in all, \d+ waiting for a verdict\.|This page currently presents \d+ rendered songs, \d+ awaiting a verdict\.)',
                 f'This page currently presents {len(articles)} rendered songs, {waiting} awaiting a verdict.', updated, count=1)
assert updated.count("<audio") == original.count("<audio") - previous_audio + len(entries)
assert updated.count(marker) == 1
page.write_text(updated, encoding="utf-8")
print(json.dumps({"published_songs": [e["title"] for e in entries.values()], "songbook_players": updated.count("<audio"),
                  "songbook_sha256": hashlib.sha256(updated.encode()).hexdigest()}))
