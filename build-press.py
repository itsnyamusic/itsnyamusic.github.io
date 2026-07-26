#!/usr/bin/env python3
"""
Regenerates the press listing on /press/ from press.json.

Usage:  python build-press.py          rebuild
        python build-press.py --check   verify pages are up to date, change nothing

Everything between the PRESS-LD and PRESS-LIST markers in press/index.html is
generated. Nothing else in the page is touched, so design changes are safe to
make by hand. Run this after every edit to press.json.
"""

import html
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
SOURCE = ROOT / "press.json"
TARGETS = [ROOT / "press" / "index.html"]

DEFAULT_ACCENT = "#b967ff"
DEFAULT_TYPE = "NewsArticle"
# schema.org types we are willing to assert. NewsArticle for published articles,
# SocialMediaPosting for magazine coverage that only ever existed as a social post.
ALLOWED_TYPES = ("NewsArticle", "SocialMediaPosting")
MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


def load_articles():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    articles = data["articles"]

    for i, a in enumerate(articles):
        for field in ("outlet", "url", "headline", "description", "date"):
            if not a.get(field):
                raise SystemExit(f"press.json: article {i} is missing required field '{field}'")
        if not re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", a["date"]):
            raise SystemExit(
                f"press.json: article {i} has date '{a['date']}' "
                ", must be YYYY-MM-DD or YYYY-MM"
            )
        if a.get("type", DEFAULT_TYPE) not in ALLOWED_TYPES:
            raise SystemExit(
                f"press.json: article {i} has type '{a['type']}' "
                f", must be one of {', '.join(ALLOWED_TYPES)}"
            )
        if not isinstance(a.get("group", 0), int):
            raise SystemExit(
                f"press.json: article {i} has group '{a['group']}', must be a whole number"
            )

    # newest first inside a group, then groups in ascending order. Python's sort
    # is stable, so the date ordering survives the second pass.
    by_date = sorted(articles, key=lambda a: a["date"], reverse=True)
    return sorted(by_date, key=lambda a: a.get("group", 0))


def display_date(iso):
    parts = iso.split("-")
    month = MONTHS[int(parts[1]) - 1]
    if len(parts) == 3:
        return f"{int(parts[2])} {month} {parts[0]}"
    return f"{month} {parts[0]}"


def build_meta(a):
    bits = [a["outlet"], display_date(a["date"])]
    if a.get("author"):
        bits.append(a["author"])
    return " - ".join(bits)


def build_html(articles):
    out = []
    for a in articles:
        accent = a.get("accent") or DEFAULT_ACCENT
        out.append(
            f'''        <a href="{html.escape(a["url"], quote=True)}" class="press" target="_blank" rel="noopener">
            <div class="press-meta">
                <div class="press-dot" style="background: {html.escape(accent, quote=True)};"></div>
                <span>{html.escape(build_meta(a))}</span>
            </div>
            <div class="press-head">{html.escape(a.get("headline_en") or a["headline"])}</div>
            <div class="press-desc">{html.escape(a["description"])}</div>
        </a>'''
        )
    return "\n\n".join(out)


def build_ldjson(articles):
    items = []
    for i, a in enumerate(articles, start=1):
        article = {
            "@type": a.get("type", DEFAULT_TYPE),
            "headline": a["headline"],
            "url": a["url"],
        }
        # the visible page may show a translation, but `headline` stays the real
        # published title. The translation goes in alternativeHeadline instead.
        if a.get("headline_en"):
            article["alternativeHeadline"] = a["headline_en"]
        # only assert a publication date when the exact day is known
        if len(a["date"].split("-")) == 3:
            article["datePublished"] = a["date"]
        if a.get("author"):
            article["author"] = {"@type": "Person", "name": a["author"]}
        article["publisher"] = {"@type": "Organization", "name": a["outlet"]}
        article["about"] = {"@id": "https://itsnyamusic.com/links/#artist"}
        article["inLanguage"] = a.get("lang", "en")
        items.append({"@type": "ListItem", "position": i, "item": article})

    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": "https://itsnyamusic.com/press/#webpage",
                "url": "https://itsnyamusic.com/press/",
                "name": "NYAVERSE era press",
                "description": "Press coverage of German hyperpop artist Nya during the NYAVERSE album era.",
                "inLanguage": "en",
                "about": {"@id": "https://itsnyamusic.com/links/#artist"},
                "breadcrumb": {"@id": "https://itsnyamusic.com/press/#breadcrumb"},
                "mainEntity": {
                    "@type": "ItemList",
                    "numberOfItems": len(items),
                    "itemListElement": items,
                },
            },
            {
                "@type": "BreadcrumbList",
                "@id": "https://itsnyamusic.com/press/#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Nya",
                     "item": "https://itsnyamusic.com/links/"},
                    {"@type": "ListItem", "position": 2, "name": "Press",
                     "item": "https://itsnyamusic.com/press/"},
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
    articles = load_articles()
    list_html = build_html(articles)
    ldjson = build_ldjson(articles)

    stale = False
    for path in TARGETS:
        original = path.read_text(encoding="utf-8")
        updated = replace_region(original, "PRESS-LD", ldjson, path)
        updated = replace_region(updated, "PRESS-LIST", list_html, path)

        if original == updated:
            print(f"  up to date   {path.relative_to(ROOT)}")
            continue
        stale = True
        if check_only:
            print(f"  STALE        {path.relative_to(ROOT)}")
        else:
            path.write_text(updated, encoding="utf-8", newline="\n")
            print(f"  rebuilt      {path.relative_to(ROOT)}")

    print(f"\n{len(articles)} article(s), in page order:")
    for a in articles:
        print(f"  {display_date(a['date']):>16}  {a['outlet']}: {a['headline'][:58]}")

    if check_only and stale:
        print("\nPages are out of date. Run: python build-press.py")
        sys.exit(1)
    if not check_only:
        print(f"\nDone. Remember to commit both press.json and the rebuilt page(s).")


if __name__ == "__main__":
    main()
