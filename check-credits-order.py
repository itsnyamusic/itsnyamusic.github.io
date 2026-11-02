#!/usr/bin/env python3
"""
Verifies that the credit list on /credits/ is sorted newest first and that every
row has its cover.

Usage:  python check-credits-order.py           report, exit 1 if anything is off
        python check-credits-order.py --fix     reorder rows, add missing covers

Covers work like the ones on /releases/. The site makes no requests to other
servers, so --fix fetches each cover once from the row's own link (Spotify or
SoundCloud oEmbed, or the video frame for YouTube), shrinks it to 112px, stores
it in assets/credit-covers/ and writes the <img> into the row. Commit those with
the page, and delete a file and run --fix again to replace it. Fetching needs
Pillow (pip install pillow). Rows without a link stay plain and get no cover.

Every row in the .credits list carries data-date, an ISO date at whatever
precision the source gives: a full date where the release has one, a bare year
where the platform only shows a year. Both sort correctly as plain strings, so
no date parsing is needed and a bare year never has to be faked into a day.

Rows with equal data-date keep their existing order, so where two releases only
resolve to the same year, whatever order you put them in is what stays.
"""

import html
import io
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
TARGET = ROOT / "credits" / "index.html"
SITE = "https://itsnyamusic.com/"
COVER_DIR = ROOT / "assets" / "credit-covers"
COVER_PX = 112  # 56px in the list, twice that for sharp screens

LIST_RE = re.compile(r'(<div class="credits">)(.*?)(\n    </div>)', re.S)
ROW_RE = re.compile(r'\n        <(a|div) class="credit".*?</\1>', re.S)
DATE_RE = re.compile(r'data-date="([^"]+)"')
TITLE_RE = re.compile(r'<div class="credit-title">(.*?)</div>', re.S)
HREF_RE = re.compile(r'<a class="credit"[^>]*\shref="([^"]+)"')
OPEN_RE = re.compile(r'<a class="credit"[^>]*>')
YOUTUBE_RE = re.compile(r'[?&]v=([\w-]{11})')


def cover_path(title):
    plain = unicodedata.normalize("NFKD", html.unescape(title)).encode("ascii", "ignore").decode()
    return COVER_DIR / (re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-") + ".jpg")


def fetch_cover(link, path):
    try:
        from PIL import Image, ImageOps
    except ImportError:
        raise SystemExit("fetching a cover needs Pillow: pip install pillow")
    headers = {"User-Agent": "itsnyamusic.com check-credits-order.py"}

    def get(url):
        return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30)

    try:
        video = YOUTUBE_RE.search(link) if "youtu" in link else None
        if video:
            # maxresdefault is the full 16:9 frame; the oEmbed thumbnail is 4:3
            # with black bars, which a square crop would keep.
            art = f"https://i.ytimg.com/vi/{video.group(1)}/maxresdefault.jpg"
        else:
            api = ("https://open.spotify.com/oembed?url=" if "spotify" in link
                   else "https://soundcloud.com/oembed?format=json&url=") + urllib.parse.quote(link, safe="")
            with get(api) as resp:
                art = json.load(resp)["thumbnail_url"]
        with get(art) as resp:
            image = Image.open(io.BytesIO(resp.read())).convert("RGB")
    except Exception as e:
        raise SystemExit(f"could not fetch the cover from {link}: {e}")
    COVER_DIR.mkdir(parents=True, exist_ok=True)
    ImageOps.fit(image, (COVER_PX, COVER_PX), Image.LANCZOS).save(path, quality=85, optimize=True, progressive=True)
    print(f"  fetched  {path.relative_to(ROOT)}")


def add_cover(entry):
    """Writes the row's <img> in, fetching the file first if it is not stored yet."""
    path = cover_path(entry["title"])
    if not path.exists():
        fetch_cover(HREF_RE.search(entry["html"]).group(1), path)
    src = SITE + path.relative_to(ROOT).as_posix()
    img = f'\n            <img class="credit-cover" src="{src}" width="56" height="56" alt="" loading="lazy">'
    entry["html"] = OPEN_RE.sub(lambda m: m.group(0) + img, entry["html"], count=1)


def missing_cover(entry):
    if not HREF_RE.search(entry["html"]):
        return False
    return "credit-cover" not in entry["html"] or not cover_path(entry["title"]).exists()


def parse():
    text = TARGET.read_text(encoding="utf-8")
    block = LIST_RE.search(text)
    if not block:
        raise SystemExit(f"{TARGET}: could not find the .credits list")

    rows = list(ROW_RE.finditer(block.group(2)))
    if not rows:
        raise SystemExit(f"{TARGET}: the .credits list has no rows")

    entries = []
    for i, m in enumerate(rows):
        row = m.group(0)
        date = DATE_RE.search(row)
        if not date:
            title = TITLE_RE.search(row)
            name = title.group(1).strip() if title else f"row {i}"
            raise SystemExit(f"{TARGET}: credit '{name}' has no data-date")
        title = TITLE_RE.search(row)
        entries.append({
            "date": date.group(1),
            "title": re.sub(r"\s+", " ", title.group(1)).strip() if title else f"row {i}",
            "html": row,
        })

    # Splice against the first and last row rather than the whole list body, so
    # anything around the rows survives a --fix untouched.
    span = (block.start(2) + rows[0].start(), block.start(2) + rows[-1].end())
    return text, span, entries


def main():
    fix = "--fix" in sys.argv[1:]
    text, span, entries = parse()

    for e in entries:
        if not re.fullmatch(r"\d{4}(-\d{2}(-\d{2})?)?", e["date"]):
            raise SystemExit(
                f"{TARGET}: credit '{e['title']}' has data-date '{e['date']}', "
                "expected YYYY, YYYY-MM or YYYY-MM-DD"
            )

    # Stable sort, so equal dates keep the order they were written in.
    wanted = sorted(entries, key=lambda e: e["date"], reverse=True)
    in_order = [e["title"] for e in wanted] == [e["title"] for e in entries]
    no_cover = [e for e in entries if missing_cover(e)]

    if in_order and not no_cover:
        print(f"credits: {len(entries)} rows, newest first, all with covers, ok")
        return 0

    if not fix:
        if not in_order:
            print("credits: out of order. Current, then expected:\n")
            for label, rows in (("current ", entries), ("expected", wanted)):
                for e in rows:
                    print(f"  {label}  {e['date']:<10}  {e['title']}")
                print()
        for e in no_cover:
            print(f"credits: no cover for '{e['title']}'")
        print("Run with --fix to repair.")
        return 1

    for e in no_cover:
        if "credit-cover" not in e["html"]:
            add_cover(e)
        else:
            fetch_cover(HREF_RE.search(e["html"]).group(1), cover_path(e["title"]))

    # Each row match begins with its own newline, so joining on one more
    # newline keeps the blank line the rows are written with.
    rebuilt = "\n".join(e["html"] for e in wanted)
    TARGET.write_text(
        text[: span[0]] + rebuilt + text[span[1]:],
        encoding="utf-8",
    )
    print(f"credits: {len(entries)} rows in order, {len(no_cover)} cover(s) added")
    return 0


if __name__ == "__main__":
    sys.exit(main())
