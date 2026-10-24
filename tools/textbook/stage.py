"""Copy the built textbook site into a web project for deployment (no PDF, no print intermediates).

    python tools/textbook/stage.py "path/to/site/public/music_theory_of_golden_harmony"

The destination becomes a mirror of textbook_site/: changed files are copied, files that no longer exist in the
site are removed (only inside the destination folder), unchanged files are left alone. Every link in the site is
relative, so it works from any URL path (for example deeperresearch.ai/music_theory_of_golden_harmony/).
"""
from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SITE = os.path.join(ROOT, "textbook_site")
SKIP_DIRS = {"print"}
SKIP_EXT = {".pdf"}
MAX_BYTES = 25 * 1024 * 1024                    # Cloudflare Pages per-file limit (25 MiB)


def wanted(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    return parts[0] not in SKIP_DIRS and os.path.splitext(rel)[1].lower() not in SKIP_EXT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dest", help="destination folder (created if missing)")
    ap.add_argument("--dry", action="store_true", help="report what would change")
    args = ap.parse_args()
    dest = os.path.abspath(args.dest)
    if not os.path.isfile(os.path.join(SITE, "index.html")):
        sys.exit("textbook_site/ is not built: run tools/textbook/build.py first")
    if os.path.commonpath([dest, SITE]) == SITE:
        sys.exit("destination must be outside textbook_site/")
    src_files = {}
    for d, _, fs in os.walk(SITE):
        for f in fs:
            rel = os.path.relpath(os.path.join(d, f), SITE)
            if wanted(rel):
                src_files[rel] = os.path.join(d, f)
    too_big = [r for r, p in src_files.items() if os.path.getsize(p) > MAX_BYTES]
    if too_big:
        sys.exit(f"files over 25 MiB (Cloudflare Pages limit): {too_big}")
    copied = removed = 0
    for rel, src in src_files.items():
        dst = os.path.join(dest, rel)
        if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src) and filecmp.cmp(src, dst, shallow=False):
            continue
        copied += 1
        if not args.dry:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    if os.path.isdir(dest):
        for d, _, fs in os.walk(dest):
            for f in fs:
                rel = os.path.relpath(os.path.join(d, f), dest)
                if rel not in src_files:
                    removed += 1
                    if not args.dry:
                        os.remove(os.path.join(d, f))
    total = sum(os.path.getsize(p) for p in src_files.values())
    print(f"{'would copy' if args.dry else 'copied'} {copied}, {'would remove' if args.dry else 'removed'} {removed}; "
          f"site: {len(src_files)} files, {total / 1e6:.0f} MB -> {dest}")


if __name__ == "__main__":
    main()
