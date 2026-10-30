#!/usr/bin/env python3
"""
Regenerates the release list on /releases/ from releases.json.

Usage:  python build-releases.py          rebuild
        python build-releases.py --check   verify pages are up to date, change nothing

Everything between the RELEASES-LD and RELEASES-LIST markers in
releases/index.html is generated. Nothing else in the page is touched, so
design changes are safe to make by hand. Run this after every edit to
releases.json. Same layout and same rules as build-press.py.

A release that is not out yet has a page but no streaming link, and its row
says "out <date>". After that date the build refuses until the Spotify or
SoundCloud link is added, so an announcement cannot go stale unnoticed.

Each release that has its own page also gets that page's accent colour from
its cover (the og:image): the build picks the cover's most vivid colour,
writes it between the ACCENT:START and ACCENT:END comments in the page's
<style> and into its theme-color meta. A page without that block, or with
the old purple still hard-coded in its CSS, stops the build. Needs Pillow.
"""

import colorsys
import html
import json
import re
import sys
from datetime import date
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit("build-releases.py needs Pillow for the cover accent colours: pip install pillow")

ROOT = Path(__file__).parent
SOURCE = ROOT / "releases.json"
TARGETS = [ROOT / "releases" / "index.html"]

ARTIST_ID = "https://itsnyamusic.com/#artist"
PAGE_URL = "https://itsnyamusic.com/releases/"

# The dot says where the row goes, same as on /credits/: purple for a page on
# this site, then the colour of the platform the row links out to.
PAGE_ACCENT = "#b967ff"
SPOTIFY_ACCENT = "#1ed760"
SOUNDCLOUD_ACCENT = "#ff5500"

RELEASE_TYPES = {
    "Album": "https://schema.org/AlbumRelease",
    "EP": "https://schema.org/EPRelease",
    "Single": "https://schema.org/SingleRelease",
}
SPOTIFY_RE = re.compile(r"https://open\.spotify\.com/album/[A-Za-z0-9]{22}")
SPOTIFY_ARTIST_RE = re.compile(r"https://open\.spotify\.com/artist/[A-Za-z0-9]{22}")
ISRC_RE = re.compile(r"[A-Z]{2}[A-Z0-9]{3}\d{7}")
UPC_RE = re.compile(r"\d{12,13}")
SOUNDCLOUD_RE = re.compile(r"https://soundcloud\.com/its_nya_music/(sets/)?[a-z0-9_-]+")
MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]

SITE = "https://itsnyamusic.com/"
ACCENT_RE = re.compile(r"(/\* ACCENT:START \*/\n).*?(\n[ \t]*/\* ACCENT:END \*/)", re.DOTALL)
# The site purple that release pages used before they took their colour from
# the cover. Only the NYAVERSE link dots may still use it.
OLD_ACCENT = re.compile(r"#b967ff|185,\s*103,\s*255", re.IGNORECASE)
DOT_RULE_RE = re.compile(r"\.d-(nyaverse|lyrics)\b")
PAGE_BG = (10, 10, 10)


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


def check_credits(r, name):
    for c in r.get("credits", []):
        track = c.get("track")
        if not isinstance(track, int) or not 1 <= track <= r["tracks"]:
            raise SystemExit(f"releases.json: '{name}' has a credit on track '{track}', must be 1 to {r['tracks']}")
        for field in ("title", "role"):
            if not c.get(field):
                raise SystemExit(f"releases.json: '{name}' track {track} credit is missing its {field}")
        names = c.get("names")
        if not isinstance(names, list) or not names or not all(isinstance(n, str) and n for n in names):
            raise SystemExit(f"releases.json: '{name}' track {track} credit names must be a list of names")


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
        for field in ("title", "type", "date", "tracks"):
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
        if not r.get("spotify") and not r.get("soundcloud"):
            # An announced release has no streaming link yet, only its own page.
            # Once its date has passed the build refuses, so the row cannot keep
            # saying "out" on a release that is already out.
            if not r.get("page"):
                raise SystemExit(f"releases.json: '{name}' needs a spotify or a soundcloud link, or a page if it is not out yet")
            if not is_upcoming(r):
                raise SystemExit(f"releases.json: '{name}' came out on {r['date']}, add its spotify or soundcloud link")
        if r.get("isrc") and not ISRC_RE.fullmatch(r["isrc"]):
            raise SystemExit(f"releases.json: '{name}' has isrc '{r['isrc']}', must be a 12-character ISRC without dashes")
        if r.get("isrc") and r["tracks"] != 1:
            raise SystemExit(f"releases.json: '{name}' has an isrc, which only fits a one-track release")
        if r.get("upc") and not UPC_RE.fullmatch(r["upc"]):
            raise SystemExit(f"releases.json: '{name}' has upc '{r['upc']}', must be 12 or 13 digits")
        if r.get("spotify") and not SPOTIFY_RE.fullmatch(r["spotify"]):
            raise SystemExit(f"releases.json: '{name}' has spotify '{r['spotify']}', must be a Spotify album URL")
        if r.get("soundcloud") and not SOUNDCLOUD_RE.fullmatch(r["soundcloud"]):
            raise SystemExit(f"releases.json: '{name}' has soundcloud '{r['soundcloud']}', must be a SoundCloud URL on its_nya_music")
        if r.get("page") and not r["page"].startswith("https://itsnyamusic.com/"):
            raise SystemExit(f"releases.json: '{name}' has page '{r['page']}', must be a page on itsnyamusic.com")
        if "with" in r:
            check_names(r["with"], artists, f"'{name}' with")
        check_features(r, artists, name)
        check_credits(r, name)
        for url in platform_links(r):
            if url in seen:
                raise SystemExit(f"releases.json: '{name}' repeats a link already listed ({url})")
            seen.add(url)

    # newest first; Python's sort is stable, so same-day releases keep file order
    return sorted(releases, key=lambda r: r["date"], reverse=True), artists


def is_upcoming(r):
    return r["date"] > date.today().isoformat()


def display_date(iso):
    year, month, day = iso.split("-")
    return f"{int(day)} {MONTHS[int(month) - 1]} {year}"


def build_meta(r):
    kind = r["type"]
    if r.get("with"):
        kind += " with " + " & ".join(r["with"])
    if is_upcoming(r):
        return f"{kind} - out {display_date(r['date'])}"
    return f"{kind} - {display_date(r['date'])}"


def platform_links(r):
    """The release's streaming links, Spotify first because it is canonical."""
    return [r[k] for k in ("spotify", "soundcloud") if r.get(k)]


def row_link(r):
    """Where a row points and which dot it gets: its own page on this site
    first, then Spotify, then SoundCloud for releases that are not on Spotify."""
    if r.get("page"):
        return r["page"], PAGE_ACCENT
    if r.get("spotify"):
        return r["spotify"], SPOTIFY_ACCENT
    return r["soundcloud"], SOUNDCLOUD_ACCENT


def page_path(r):
    if not r["page"].startswith(SITE + "releases/"):
        raise SystemExit(f"releases.json: '{r['title']}' has page '{r['page']}', release pages live under {SITE}releases/")
    return ROOT / r["page"][len(SITE):] / "index.html"


def page_cover(text, path):
    m = re.search(r'<meta property="og:image" content="https://itsnyamusic\.com/([^"]+)">', text)
    if not m:
        raise SystemExit(f"{path}: no og:image on this site, which is where the accent colour comes from")
    cover = ROOT / m.group(1)
    if not cover.exists():
        raise SystemExit(f"{path}: og:image {m.group(1)} is not in the repo")
    return cover


def thumbnail(cover):
    """The small version of a cover for the list, when there is one."""
    small = cover.with_name(cover.name.replace("-1200.", "-640."))
    return small if small.exists() else cover


def contrast(rgb, bg=PAGE_BG):
    def lum(c):
        r, g, b = ((v / 255) / 12.92 if v / 255 <= 0.03928 else ((v / 255 + 0.055) / 1.055) ** 2.4 for v in c)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    hi, lo = sorted((lum(rgb), lum(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def cover_accent(cover):
    """The cover's most vivid colour, pushed to neon and kept readable on the
    near-black page: the hue that carries the most saturated, bright pixels,
    averaged, then raised to full brightness at contrast 6:1 or better."""
    im = Image.open(cover).convert("RGB").resize((96, 96))
    bins = [0.0] * 36
    pixels = []
    for r, g, b in im.getdata():
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s >= 0.35 and v >= 0.35:
            k = int(h * 36) % 36
            bins[k] += s * v
            pixels.append((k, s * v, (r, g, b)))
    if not pixels:
        return (0xb9, 0x67, 0xff)
    best = max(range(36), key=lambda k: bins[k] + 0.5 * (bins[(k - 1) % 36] + bins[(k + 1) % 36]))
    near = {(best - 1) % 36, best, (best + 1) % 36}
    chosen = [(w, c) for k, w, c in pixels if k in near]
    total = sum(w for w, _ in chosen)
    r, g, b = (sum(w * c[i] for w, c in chosen) / total for i in range(3))
    h, s, _ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    s = max(s, 0.7)
    rgb = tuple(round(c * 255) for c in colorsys.hsv_to_rgb(h, s, 1.0))
    while contrast(rgb) < 6 and s > 0.2:
        s -= 0.05
        rgb = tuple(round(c * 255) for c in colorsys.hsv_to_rgb(h, s, 1.0))
    return rgb


def hex_colour(rgb):
    return "#%02x%02x%02x" % rgb


def apply_accent(text, rgb, path):
    if not ACCENT_RE.search(text):
        raise SystemExit(f"{path}: no ACCENT:START/ACCENT:END block in its <style>. "
                         "Copy it from another release page, see the README.")
    style = ACCENT_RE.sub("", text[text.index("<style>"):text.index("</style>")])
    for line in style.splitlines():
        if OLD_ACCENT.search(line) and not DOT_RULE_RE.search(line):
            raise SystemExit(f"{path}: the old purple is hard-coded in its CSS ({line.strip()}). "
                             "Use var(--accent) or rgba(var(--accent-rgb), <alpha>) so the cover colour applies.")
    block = f"        :root {{ --accent: {hex_colour(rgb)}; --accent-rgb: {rgb[0]}, {rgb[1]}, {rgb[2]}; }}"
    text = ACCENT_RE.sub(lambda m: m.group(1) + block + m.group(2), text)
    text, n = re.subn(r'<meta name="theme-color" content="[^"]*">',
                      f'<meta name="theme-color" content="{hex_colour(rgb)}">', text)
    if n != 1:
        raise SystemExit(f"{path}: expected exactly one theme-color meta, found {n}")
    return text


def build_html(releases, pages):
    """`pages` maps a release title to its page's (thumbnail URL, accent hex)."""
    out = []
    for r in releases:
        href, dot = row_link(r)
        target = "" if r.get("page") else ' target="_blank" rel="noopener"'
        thumb, accent = pages.get(r["title"], (None, PAGE_ACCENT))
        tag = (f'\n                <span class="release-tag" style="color: {accent}; border-color: {accent};">upcoming</span>'
               if is_upcoming(r) else "")
        cover = (f'\n            <img class="release-cover" src="{thumb}" width="56" height="56" alt="" loading="lazy">'
                 if thumb else '\n            <div class="release-cover release-cover-empty"></div>')
        out.append(
            f'''        <a href="{html.escape(href, quote=True)}" class="release"{target}>{cover}
            <div class="release-meta">
                <div class="release-dot" style="background: {dot};"></div>
                <span>{html.escape(build_meta(r))}</span>{tag}
            </div>
            <div class="release-title">{html.escape(r["title"])}</div>
        </a>'''
        )
    return "\n\n".join(out)


def other_artist(name, artists):
    # The Spotify profile is what tells a crawler which Naeyiwu or VAIN this is.
    return {"@type": "MusicGroup", "name": name, "sameAs": artists[name]}


def credited_person(name, artists):
    # A credited name that is also a listed artist gets their Spotify profile.
    person = {"@type": "Person", "name": name}
    if name in artists:
        person["sameAs"] = artists[name]
    return person


def build_tracks(r, artists):
    """The tracks with guests or credits on them. A track with guests is Nya
    first and the guests after, which is how the album page marks up the same
    tracks; a track with only credits carries the release's own artists. Only
    these tracks are listed; numTracks still carries the full count."""
    features = {f["track"]: f for f in r.get("features", [])}
    credits = {}
    for c in r.get("credits", []):
        credits.setdefault(c["track"], []).append(c)
    numbers = set(features) | set(credits)
    if r.get("isrc"):
        numbers.add(1)
    tracks = []
    for n in sorted(numbers):
        if n in features:
            title = features[n]["title"]
        elif n in credits:
            title = credits[n][0]["title"]
        else:
            title = r["title"]
        if n in features:
            by = [{"@id": ARTIST_ID}] + [other_artist(a, artists) for a in features[n]["artists"]]
        else:
            by = [other_artist(a, artists) for a in r.get("with", [])] + [{"@id": ARTIST_ID}]
        track = {"@type": "MusicRecording", "name": title, "position": n,
                 "byArtist": by if len(by) > 1 else by[0]}
        if r.get("isrc"):
            track["isrcCode"] = r["isrc"]
        roles = [
            # schema.org has no mixing-engineer property; a Role on contributor
            # is its documented way to say what someone did on a work.
            {"@type": "Role", "roleName": c["role"],
             "contributor": credited_person(person, artists)}
            for c in credits.get(n, []) for person in c["names"]
        ]
        if roles:
            track["contributor"] = roles if len(roles) > 1 else roles[0]
        tracks.append(track)
    return tracks


def build_album(r, artists):
    album = {"@type": "MusicAlbum"}
    # A release with its own page is fully described there, under this @id.
    # The entry here is a partial view of the same entity, not a second one.
    if r.get("page"):
        album["@id"] = r["page"] + "#album"
    album["name"] = r["title"]
    album["url"] = row_link(r)[0]
    album["datePublished"] = r["date"]
    album["albumProductionType"] = "https://schema.org/StudioAlbum"
    album["albumReleaseType"] = RELEASE_TYPES[r["type"]]
    album["numTracks"] = r["tracks"]
    main = [other_artist(n, artists) for n in r.get("with", [])] + [{"@id": ARTIST_ID}]
    album["byArtist"] = main if len(main) > 1 else main[0]
    if r.get("upc"):
        album["identifier"] = {"@type": "PropertyValue", "propertyID": "UPC", "value": r["upc"]}
    if r.get("features") or r.get("credits") or r.get("isrc"):
        album["track"] = build_tracks(r, artists)
    same = [u for u in platform_links(r) if u != album["url"]]
    if same:
        album["sameAs"] = same if len(same) > 1 else same[0]
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

    # Release pages first: each takes its accent colour from its own cover.
    updates = {}
    pages = {}
    for r in releases:
        if not r.get("page"):
            continue
        path = page_path(r)
        if not path.exists():
            raise SystemExit(f"releases.json: '{r['title']}' has page {r['page']}, but {path.relative_to(ROOT)} does not exist")
        original = path.read_text(encoding="utf-8")
        cover = page_cover(original, path)
        rgb = cover_accent(cover)
        updates[path] = (original, apply_accent(original, rgb, path))
        pages[r["title"]] = (SITE + thumbnail(cover).relative_to(ROOT).as_posix(), hex_colour(rgb))

    list_html = build_html(releases, pages)
    ldjson = build_ldjson(releases, artists)
    for path in TARGETS:
        original = path.read_text(encoding="utf-8")
        updated = replace_region(original, "RELEASES-LD", ldjson, path)
        updates[path] = (original, replace_region(updated, "RELEASES-LIST", list_html, path))

    stale = False
    for path, (original, updated) in updates.items():
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

    print("\nAccent colours, from each page's cover:")
    for title, (_, accent) in pages.items():
        print(f"  {accent}  {title}")

    if check_only and stale:
        print("\nPages are out of date. Run: python build-releases.py")
        sys.exit(1)
    if not check_only:
        print("\nDone. Remember to commit both releases.json and the rebuilt page(s).")


if __name__ == "__main__":
    main()
