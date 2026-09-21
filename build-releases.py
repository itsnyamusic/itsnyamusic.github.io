#!/usr/bin/env python3
"""
Regenerates the release list on /releases/ from releases.json.

Usage:  python build-releases.py          rebuild
        python build-releases.py --check   verify pages are up to date, change nothing

Everything between the RELEASES-LD and RELEASES-LIST markers in
releases/index.html is generated. Nothing else in the page is touched, so
design changes are safe to make by hand. Run this after every edit to
releases.json. Same layout and same rules as build-press.py.
"""

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SOURCE = ROOT / "releases.json"
TARGETS = [ROOT / "releases" / "index.html"]

ARTIST_ID = "https://itsnyamusic.com/#artist"
PAGE_URL = "https://itsnyamusic.com/releases/"

# The dot says where the row goes, same as on /credits/: purple for a page on
# this site, Spotify green for everything that links out to Spotify.
PAGE_ACCENT = "#b967ff"
SPOTIFY_ACCENT = "#1ed760"

RELEASE_TYPES = {
    "Album": "https://schema.org/AlbumRelease",
    "EP": "https://schema.org/EPRelease",
    "Single": "https://schema.org/SingleRelease",
}
SPOTIFY_RE = re.compile(r"https://open\.spotify\.com/album/[A-Za-z0-9]{22}")
SPOTIFY_ARTIST_RE = re.compile(r"https://open\.spotify\.com/artist/[A-Za-z0-9]{22}")
MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


def check_names(names, artists, where):
    """A list of artist names, each of which has a Spotify profile in `artists`."""
    if not isinstance(names, list) or not names or not all(isinstance(n, str) and n for n in names):
        raise SystemExit(f"releases.json: {where} must be a list of artist names")
    for n in names:
        if n not in artists:
            raise SystemExit(f"releases.json: {where} names '{n}', who is not listed under artists")


def check_features(r, artists, name):
    tracks = set()
    for f in r.get("features", []):
        track = f.get("track")
        if not isinstance(track, int) or not 1 <= track <= r["tracks"]:
            raise SystemExit(f"releases.json: '{name}' has a feature on track '{track}', must be 1 to {r['tracks']}")
        if track in tracks:
            raise SystemExit(f"releases.json: '{name}' lists track {track} twice under features")
        tracks.add(track)
        if not f.get("title"):
            raise SystemExit(f"releases.json: '{name}' track {track} feature is missing its title")
        check_names(f.get("artists"), artists, f"'{name}' track {track} artists")


def load_releases():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    releases = data["releases"]
    artists = data.get("artists", {})

    for n, url in artists.items():
        if not SPOTIFY_ARTIST_RE.fullmatch(url):
            raise SystemExit(f"releases.json: artist '{n}' has '{url}', must be a Spotify artist URL")

    seen = set()
    for i, r in enumerate(releases):
        name = r.get("title") or f"release {i}"
        for field in ("title", "type", "date", "tracks", "spotify"):
            if not r.get(field):
                raise SystemExit(f"releases.json: '{name}' is missing required field '{field}'")
        if r["type"] not in RELEASE_TYPES:
            raise SystemExit(
                f"releases.json: '{name}' has type '{r['type']}', "
                f"must be one of {', '.join(RELEASE_TYPES)}"
            )
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["date"]):
            raise SystemExit(f"releases.json: '{name}' has date '{r['date']}', must be YYYY-MM-DD")
        if not isinstance(r["tracks"], int) or r["tracks"] < 1:
            raise SystemExit(f"releases.json: '{name}' has tracks '{r['tracks']}', must be a whole number above 0")
        if not SPOTIFY_RE.fullmatch(r["spotify"]):
            raise SystemExit(f"releases.json: '{name}' has spotify '{r['spotify']}', must be a Spotify album URL")
        if r.get("page") and not r["page"].startswith("https://itsnyamusic.com/"):
            raise SystemExit(f"releases.json: '{name}' has page '{r['page']}', must be a page on itsnyamusic.com")
        if "with" in r:
            check_names(r["with"], artists, f"'{name}' with")
        check_features(r, artists, name)
        if r["spotify"] in seen:
            raise SystemExit(f"releases.json: '{name}' repeats a Spotify URL already listed")
        seen.add(r["spotify"])

    # newest first; Python's sort is stable, so same-day releases keep file order
    return sorted(releases, key=lambda r: r["date"], reverse=True), artists


def display_date(iso):
    year, month, day = iso.split("-")
    return f"{int(day)} {MONTHS[int(month) - 1]} {year}"


def build_meta(r):
    kind = r["type"]
    if r.get("with"):
        kind += " with " + " & ".join(r["with"])
    return f"{kind} - {display_date(r['date'])}"


def build_html(releases):
    out = []
    for r in releases:
        if r.get("page"):
            href, accent, target = r["page"], PAGE_ACCENT, ""
        else:
            href, accent, target = r["spotify"], SPOTIFY_ACCENT, ' target="_blank" rel="noopener"'
        out.append(
            f'''        <a href="{html.escape(href, quote=True)}" class="release"{target}>
            <div class="release-meta">
                <div class="release-dot" style="background: {accent};"></div>
                <span>{html.escape(build_meta(r))}</span>
            </div>
            <div class="release-title">{html.escape(r["title"])}</div>
        </a>'''
        )
    return "\n\n".join(out)


def other_artist(name, artists):
    # The Spotify profile is what tells a crawler which Naeyiwu or Vain this is.
    return {"@type": "MusicGroup", "name": name, "sameAs": artists[name]}


def build_tracks(r, artists):
    """The tracks with guests on them, Nya first and the guests after, which
    is how the album page marks up the same tracks. Only these are listed;
    numTracks still carries the full count."""
    return [
        {
            "@type": "MusicRecording",
            "name": f["title"],
            "position": f["track"],
            "byArtist": [{"@id": ARTIST_ID}] + [other_artist(n, artists) for n in f["artists"]],
        }
        for f in sorted(r.get("features", []), key=lambda f: f["track"])
    ]


def build_album(r, artists):
    album = {"@type": "MusicAlbum"}
    # A release with its own page is fully described there, under this @id.
    # The entry here is a partial view of the same entity, not a second one.
    if r.get("page"):
        album["@id"] = r["page"] + "#album"
    album["name"] = r["title"]
    album["url"] = r.get("page") or r["spotify"]
    album["datePublished"] = r["date"]
    album["albumProductionType"] = "https://schema.org/StudioAlbum"
    album["albumReleaseType"] = RELEASE_TYPES[r["type"]]
    album["numTracks"] = r["tracks"]
    main = [other_artist(n, artists) for n in r.get("with", [])] + [{"@id": ARTIST_ID}]
    album["byArtist"] = main if len(main) > 1 else main[0]
    if r.get("features"):
        album["track"] = build_tracks(r, artists)
    if r.get("page"):
        album["sameAs"] = r["spotify"]
    return album


def build_ldjson(releases, artists):
    items = [
        {"@type": "ListItem", "position": i, "item": build_album(r, artists)}
        for i, r in enumerate(releases, start=1)
    ]
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            # Pronoun node. Partial description of the artist entity defined on the
            # homepage, repeated here so a crawler that only sees this page still
            # gets the pronouns right.
            {
                "@type": ["MusicGroup", "Person"],
                "@id": ARTIST_ID,
                "name": "Nya",
                "url": "https://itsnyamusic.com/",
                "gender": "Female",
                "disambiguatingDescription":
                    "Nya's pronouns are she/her (German: sie/ihr).",
                "additionalProperty": [
                    {"@type": "PropertyValue", "name": "pronouns", "value": "she/her"},
                    {"@type": "PropertyValue", "name": "Pronomen", "value": "sie/ihr"},
                ],
            },
            {
                "@type": "CollectionPage",
                "@id": PAGE_URL + "#webpage",
                "url": PAGE_URL,
                "name": "Releases",
                "description": "Every release by German hyperpop and cyber-rap artist Nya: albums, EPs and singles, newest first.",
                "inLanguage": "en",
                "about": {"@id": ARTIST_ID},
                "breadcrumb": {"@id": PAGE_URL + "#breadcrumb"},
                "mainEntity": {
                    "@type": "ItemList",
                    "itemListOrder": "https://schema.org/ItemListOrderDescending",
                    "numberOfItems": len(items),
                    "itemListElement": items,
                },
            },
            {
                "@type": "BreadcrumbList",
                "@id": PAGE_URL + "#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Nya",
                     "item": "https://itsnyamusic.com/"},
                    {"@type": "ListItem", "position": 2, "name": "Releases",
                     "item": PAGE_URL},
                ],
            },
        ],
    }
    body = json.dumps(graph, indent=4, ensure_ascii=False)
    body = "\n".join("    " + line for line in body.splitlines())
    return f'    <script type="application/ld+json">\n{body}\n    </script>'


def replace_region(text, name, payload, path):
    pattern = re.compile(
        rf"(<!-- {name}:START -->\n).*?(\n[ \t]*<!-- {name}:END -->)",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise SystemExit(f"{path}: could not find the {name}:START/{name}:END markers")
    return pattern.sub(lambda m: m.group(1) + payload + m.group(2), text)


def main():
    check_only = "--check" in sys.argv
    releases, artists = load_releases()
    list_html = build_html(releases)
    ldjson = build_ldjson(releases, artists)

    stale = False
    for path in TARGETS:
        original = path.read_text(encoding="utf-8")
        updated = replace_region(original, "RELEASES-LD", ldjson, path)
        updated = replace_region(updated, "RELEASES-LIST", list_html, path)

        if original == updated:
            print(f"  up to date   {path.relative_to(ROOT)}")
            continue
        stale = True
        if check_only:
            print(f"  STALE        {path.relative_to(ROOT)}")
        else:
            path.write_text(updated, encoding="utf-8", newline="\n")
            print(f"  rebuilt      {path.relative_to(ROOT)}")

    print(f"\n{len(releases)} release(s), in page order:")
    for r in releases:
        guests = sorted({n for f in r.get("features", []) for n in f["artists"]})
        feat = f"  (feat. {', '.join(guests)})" if guests else ""
        print(f"  {display_date(r['date']):>17}  {build_meta(r).split(' - ')[0]:<20}  {r['title']}{feat}")

    if check_only and stale:
        print("\nPages are out of date. Run: python build-releases.py")
        sys.exit(1)
    if not check_only:
        print("\nDone. Remember to commit both releases.json and the rebuilt page(s).")


if __name__ == "__main__":
    main()
