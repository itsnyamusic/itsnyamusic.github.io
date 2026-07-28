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
| `links/` | redirect to the homepage, kept because a lot of external records still point at it |
| `assets/` | shared images, icons, fonts, `fonts.css` |

## Rules worth knowing before editing

**The artist identity lives at one id.** Every page's structured data refers to
the artist as `https://itsnyamusic.com/#artist`, defined on the homepage. If you
add a page, reference that id, do not define a second artist entity. Two rival
entities is the thing this site is specifically built to avoid.

**No external requests.** Fonts are self-hosted and declared once in
`assets/fonts.css`. The privacy policy tells visitors the site makes no
third-party connections, so do not add a CDN, a Google Font, an analytics
snippet or a tracker. (Known exception: `promo/` embeds YouTube, which does
contact Google on load. That contradicts `datenschutz/` and is unresolved.)

**`press/` is generated.** Do not hand-edit the markup between the
`PRESS-LD` and `PRESS-LIST` markers, it gets overwritten. Edit `press.json`,
then run the generator and commit both:

```
python build-press.py            # rebuild
python build-press.py --check    # verify without writing, exits 1 if stale
```

**`links/` must keep redirecting.** Wikidata, MusicBrainz, Discogs and several
artist-profile bios still point at `/links/`. The redirect carries that
authority to the homepage. It intentionally has no `noindex`, so the signals
consolidate instead of being dropped. Same for the images kept at
`links/assets/`, which older shared link previews still request.

**Keep the sitemap honest.** `sitemap.xml` lists only canonical, indexable
pages. `press-kit/` is excluded on purpose because it is `noindex`, and
`links/` is excluded because it is a redirect.

## History

The site used to be three repos: `links` served the hub at `/links/`, `promo`
served `/promo/`, and this repo held little more than a redirect. They were
merged here on 2026-07-28 and both old repos are archived with Pages disabled.
