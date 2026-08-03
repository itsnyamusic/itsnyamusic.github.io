# itsnyamusic.com

The whole of itsnyamusic.com, in one repo. Static HTML on GitHub Pages, no build
step for the site itself, no framework, no dependencies.

Custom domain via `CNAME`. HTTPS is enforced. There is nothing to install.

## Layout

| Path | What it is |
|---|---|
| `index.html` | the homepage and link hub, the canonical artist page |
| `nyaverse/` | NYAVERSE album page |
| `nyaverse/lyrics/` | full lyrics, all 13 tracks |
| `press/` | press coverage, **generated, see below** |
| `press-kit/` | press kit, deliberately `noindex, nofollow` |
| `promo/` | longer bio, discography and videos |
| `datenschutz/` | privacy policy |
| `impressum/` | legal notice (§ 5 DDG) |
| `links/` | redirect to the homepage, kept because a lot of external records still point at it |
| `assets/` | shared images, icons, fonts, `fonts.css` |

## Rules worth knowing before editing

**The artist identity lives at one id.** Every page's structured data refers to
the artist as `https://itsnyamusic.com/#artist`, defined on the homepage. If you
add a page, reference that id, do not define a second artist entity. Two rival
entities is the thing this site is specifically built to avoid.

**No external requests, on any page, ever.** Loading any page must not contact
a third party. Fonts are self-hosted and declared once in `assets/fonts.css`.
Do not add a CDN, a Google Font, an analytics snippet or a tracker, and do not
add `preconnect`/`dns-prefetch` to a third party either, since those open a
connection on their own.

The one piece of third-party content, the video on `promo/`, is click-to-load:
the page ships a placeholder button and only inserts the YouTube iframe once
the visitor presses it. **Do not swap it back for a bare `<iframe>`.** That is
what `datenschutz/` promises, and a plain embed would contact Google before
anyone consented. If you add another video, copy the existing pattern.

To check, search the built pages for anything the browser fetches by itself
(`iframe`/`img`/`script`/`link rel=preconnect|stylesheet`/`url()`) pointing at
a host that is not `itsnyamusic.com`. There should be none.

**`press/` is generated.** Do not hand-edit the markup between the
`PRESS-LD` and `PRESS-LIST` markers, it gets overwritten. Edit `press.json`,
then run the generator and commit both:

```
python build-press.py            # rebuild
python build-press.py --check    # verify without writing, exits 1 if stale
```

**`credits/` is sorted newest first.** Every row in the list carries a
`data-date`, an ISO date at whatever precision the source actually gives:
a full date where the release has one, a bare year where the platform only
shows a year. Those sort against each other as plain strings, so nothing has
to be invented to fill a gap. Add a row wherever its date puts it, then:

```
python check-credits-order.py          # verify, exits 1 if out of order
python check-credits-order.py --fix    # reorder in place
```

Rows with the same `data-date` keep the order they are written in, so where two
releases only resolve to the same year, whichever you put first stays first.
Unlike `press/`, this page is hand-edited; the script only ever moves whole
rows, it does not generate them.

**`links/` must keep redirecting.** Wikidata, MusicBrainz, Discogs and several
artist-profile bios still point at `/links/`. The redirect carries that
authority to the homepage. It intentionally has no `noindex`, so the signals
consolidate instead of being dropped. Same for the images kept at
`links/assets/`, which older shared link previews still request.

**Keep the sitemap honest.** `sitemap.xml` lists only canonical, indexable
pages. `press-kit/`, `datenschutz/` and `impressum/` are excluded on purpose
because they are `noindex`, and `links/` is excluded because it is a redirect.

**The legal pages are `noindex, follow`, never blocked in `robots.txt`.**
§ 5 DDG wants the Impressum "leicht erkennbar, unmittelbar erreichbar und
ständig verfügbar", and GDPR Art. 12 wants the same of the privacy policy.
Both are about reachability from the site itself, which the footer link on
every page satisfies, so keeping them out of search results is fine. What is
not fine is a `Disallow` in `robots.txt`: a blocked page can still be indexed
as a bare URL, because the crawler never gets to read the `noindex` it is
blocked from fetching. Keep `follow` so the footer links still carry weight,
and keep both pages returning 200 to everyone.

## History

The site used to be three repos: `links` served the hub at `/links/`, `promo`
served `/promo/`, and this repo held little more than a redirect. They were
merged here on 2026-07-28 and both old repos are archived with Pages disabled.
